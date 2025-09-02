#!/usr/bin/env python3
"""
Phase 0 Desktop Pipeline: OCC → WellDatabase hydration (careful usage)

Steps:
1) Fetch OCC orphan registry and normalize API numbers
2) Resolve to WellDatabase wells via `/wells/search` by Api10 in small batches
3) Fetch limited monthly production using `/production/search` for matched wells
4) Write stable outputs under data/interim and data/prod

Usage:
  python -m src.pipelines.phase0_desktop --limit 50 --start 2000-01-01 --end 2024-12-31
"""

import os
import sys
import argparse
import time
from pathlib import Path
from typing import List, Dict
import json

import pandas as pd

from src.data.occ_api_client import OCCAPIClient
from src.api.client import WellDatabaseClient
from src.config.constants import OKLAHOMA_STATE_ID
from src.features.production import engineer_features
from src.analysis.reactivation import ReactivationAnalyzer


def chunked(iterable: List[str], size: int) -> List[List[str]]:
    return [iterable[i:i+size] for i in range(0, len(iterable), size)]


def _in_oklahoma_bounds(lat: float, lon: float) -> bool:
    try:
        if lat is None or lon is None:
            return False
        # Rough Oklahoma bounding box
        return 33.5 <= float(lat) <= 37.5 and -103.5 <= float(lon) <= -94.0
    except Exception:
        return False


def prefilter_occ_for_gpu(occ_df: pd.DataFrame) -> Dict[str, int]:
    """Prefilter OCC orphan wells before WellDatabase resolution.

    Rules:
    - Status/type screen: drop injection/disposal/water/seismic/unknown types when present.
    - Identity/location hygiene: drop missing/invalid API, drop duplicates by api_10, require valid lat/lon in OK bounds.
    - If a descriptive status column exists, keep specific statuses; otherwise rely on OCC orphan codes already applied upstream.

    Writes filtered CSV to data/interim/occ_prefiltered.csv and returns counts summary.
    """
    total = len(occ_df)

    df = occ_df.copy()

    # Type screen (if column present)
    before_type = len(df)
    type_col = None
    for c in ['welltype', 'well_type', 'WELLTYPE', 'WellType']:
        if c in df.columns:
            type_col = c
            break
    if type_col:
        # Keep explicit production well types; drop everything else
        keep_types = {'GAS', 'OIL', 'O&G', 'OIL & GAS', 'OIL AND GAS'}
        s = df[type_col].astype(str).str.upper().str.strip()
        df = df[s.isin(keep_types)]
    after_type = len(df)

    # Optional descriptive status filter (if present)
    before_status = len(df)
    status_desc_col = None
    for c in ['wellstatusdesc', 'well_status_desc', 'status_desc']:
        if c in df.columns:
            status_desc_col = c
            break
    if status_desc_col:
        keep_statuses = [
            'ORPHANED - SHUT IN',
            'ORPHANED - COMPLETED - NOT ACTIVE'
        ]
        s = df[status_desc_col].astype(str).str.upper()
        df = df[s.isin(keep_statuses)]
    after_status = len(df)

    # Identity hygiene via normalization outputs if present
    before_identity = len(df)
    if 'api_10' in df.columns:
        df = df[df['api_10'].astype(str).str.len() == 10]
        df = df.drop_duplicates(subset=['api_10'], keep='last')
    if 'valid_oklahoma_api' in df.columns:
        df = df[df['valid_oklahoma_api'] == True]

    # Location hygiene using geometry added in occ client
    if 'latitude' in df.columns and 'longitude' in df.columns:
        df = df[df.apply(lambda r: _in_oklahoma_bounds(r.get('latitude'), r.get('longitude')), axis=1)]
    after_identity = len(df)

    # Persist filtered set
    out_interim = Path('data/interim'); out_interim.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_interim / 'occ_prefiltered.csv', index=False)

    summary = {
        'total_occ': int(total),
        'after_type_screen': int(after_type),
        'after_status_screen': int(after_status),
        'after_identity_location': int(after_identity)
    }
    with open(out_interim / 'occ_prefilter_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def resolve_wb_wells(client: WellDatabaseClient, api10_list: List[str], batch_size: int = 100, delay_s: float = 0.2, cache_path: Path | None = None) -> pd.DataFrame:
    """Resolve OCC API10s to WellDatabase wells using batched /wells/search calls."""
    # Load cache
    cache_df = None
    if cache_path and cache_path.exists():
        try:
            cache_df = pd.read_csv(cache_path)
        except Exception:
            cache_df = None
    records: List[Dict] = []

    for batch in chunked(api10_list, batch_size):
        # Use cache for any pre-resolved API10
        uncached = batch
        if cache_df is not None and 'api10' in cache_df.columns:
            cached_rows = cache_df[cache_df['api10'].isin(batch)]
            for _, r in cached_rows.iterrows():
                records.append(r.to_dict())
            uncached = [a for a in batch if a not in set(cached_rows['api10'].tolist())]
        if not uncached:
            continue
        try:
            filters = {'Api10': uncached}
            resp = client.search_wells(filters=filters, page_size=len(uncached), page_offset=0)
            wells = resp.get('data', []) or []

            # Index wells by api10 if present
            by_api10: Dict[str, Dict] = {}
            for w in wells:
                api_value = w.get('api10') or w.get('api_10') or ''
                if isinstance(api_value, str):
                    by_api10[api_value] = w

            for api10 in uncached:
                w = by_api10.get(api10)
                if w:
                    records.append({
                        'api10': api10,
                        'welldatabase_found': True,
                        'wellId': w.get('wellId'),
                        'simpleId': w.get('simpleId'),
                        'wellName': w.get('wellName'),
                        'operator': w.get('operator'),
                        'status': w.get('status'),
                        'county': w.get('county'),
                        'stateId': w.get('stateId'),
                    })
                else:
                    records.append({'api10': api10, 'welldatabase_found': False})
        except Exception:
            for api10 in uncached:
                records.append({'api10': api10, 'welldatabase_found': False})
        time.sleep(delay_s)

    df_out = pd.DataFrame(records)
    # Write back to cache
    if cache_path:
        try:
            # Combine with existing cache, drop duplicates by api10
            combined = pd.concat([cache_df if cache_df is not None else pd.DataFrame(), df_out], ignore_index=True)
            combined = combined.drop_duplicates(subset=['api10'], keep='last')
            combined.to_csv(cache_path, index=False)
        except Exception:
            pass
    return df_out


def fetch_monthly_production(client: WellDatabaseClient, well_ids: List[str], start: str, end: str, max_wells: int = 25, batch_size: int = 25, cache_path: Path | None = None) -> pd.DataFrame:
    """Fetch monthly production for a limited set of wells using minimal batched calls."""
    cached = None
    if cache_path and cache_path.exists():
        try:
            cached = pd.read_csv(cache_path)
        except Exception:
            cached = None
    rows: List[Dict] = []
    for batch in chunked(well_ids[:max_wells], batch_size):
        # Use cache for any wellIds already fetched
        to_fetch = batch
        if cached is not None and 'wellId' in cached.columns:
            cached_wells = set(cached['wellId'].astype(str).unique().tolist())
            to_fetch = [w for w in batch if str(w) not in cached_wells]
            # add cached rows for this batch
            rows.extend(cached[cached['wellId'].astype(str).isin([str(w) for w in batch])].to_dict('records'))
        if not to_fetch:
            continue
        try:
            # Page through results to ensure all rows are collected
            page_offset = 0
            page_size = 1000
            while True:
                resp = client.get_production_data(to_fetch, start, end, page_size=page_size, page_offset=page_offset)
                data = resp.get('data', [])
                if not data:
                    break
                rows.extend(data)
                if len(data) < page_size:
                    break
                page_offset += page_size
        except Exception:
            pass
        time.sleep(0.2)
    df_out = pd.DataFrame(rows)
    if cache_path:
        try:
            if cached is not None:
                combined = pd.concat([cached, df_out], ignore_index=True)
            else:
                combined = df_out
            combined.drop_duplicates(subset=['id'], inplace=True)
            combined.to_csv(cache_path, index=False)
        except Exception:
            pass
    return df_out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=100, help='Max OCC APIs to process per batch')
    parser.add_argument('--offset', type=int, default=0, help='Row offset into OCC registry slice')
    parser.add_argument('--start', type=str, default='2000-01-01')
    parser.add_argument('--end', type=str, default='2024-12-31')
    parser.add_argument('--force-refresh', action='store_true')
    parser.add_argument('--top', type=int, default=5, help='Number of top wells to generate reports for')
    args = parser.parse_args()

    out_interim = Path('data/interim'); out_interim.mkdir(parents=True, exist_ok=True)
    out_prod = Path('data/prod'); out_prod.mkdir(parents=True, exist_ok=True)

    occ_client = OCCAPIClient()
    # Download all and then limit locally for sample
    occ_df = occ_client.get_all_orphan_wells(force_refresh=args.force_refresh)
    occ_df = occ_client.normalize_api_numbers(occ_df)
    # Prefilter before slicing to avoid sampling bias
    summary = prefilter_occ_for_gpu(occ_df)
    # Now slice a window for the run
    occ_df = pd.read_csv('data/interim/occ_prefiltered.csv')
    occ_df = occ_df.iloc[args.offset: args.offset + args.limit].copy()
    occ_df.to_csv(out_interim / 'occ_orphan_registry_sample.csv', index=False)

    wb_client = WellDatabaseClient()
    # If API key is missing, skip WB hydration to avoid 401s
    if not wb_client.headers.get('Api-Key'):
        print('Warning: WBD_API_KEY not set. Skipping WellDatabase hydration.')
        resolved = pd.DataFrame({'api10': occ_df['api_10'].dropna().unique().tolist(), 'welldatabase_found': False})
    else:
        resolved = resolve_wb_wells(
            wb_client,
            occ_df['api_10'].dropna().unique().tolist(),
            cache_path=out_interim / 'occ_to_wb_resolution.csv'
        )
    resolved.to_csv(out_interim / 'occ_to_wb_resolution.csv', index=False)

    # Filter matched wells (skip stateId check; rely on OCC-sourced API10 starting with '35')
    if 'welldatabase_found' in resolved.columns and 'wellId' in resolved.columns:
        # Normalize possible string booleans from cache
        resolved['welldatabase_found'] = resolved['welldatabase_found'].astype(str).str.lower().isin(['true', '1', 'yes'])
        matched_ok = resolved[resolved['welldatabase_found'] == True]
        well_ids = matched_ok['wellId'].dropna().astype(str).unique().tolist()
    else:
        matched_ok = pd.DataFrame()
        well_ids = []

    # Fallback: if no matches found in this slice, try resolving a few APIs directly (including known sample)
    if not well_ids:
        try:
            seed_api10s = []
            if 'api_10' in occ_df.columns:
                seed_api10s.extend(occ_df['api_10'].dropna().astype(str).unique().tolist()[:10])
            # Always include the validated sample well
            if '3503921577' not in seed_api10s:
                seed_api10s.append('3503921577')

            fallback_records: List[Dict] = []
            for api10 in seed_api10s:
                try:
                    w = wb_client.get_well_by_api(api10)
                    if w and w.get('wellId'):
                        fallback_records.append({
                            'api10': api10,
                            'welldatabase_found': True,
                            'wellId': w.get('wellId'),
                            'simpleId': w.get('simpleId'),
                            'wellName': w.get('wellName'),
                            'operator': w.get('operator'),
                            'status': w.get('status'),
                            'county': w.get('county'),
                            'stateId': w.get('stateId'),
                        })
                except Exception:
                    continue

            if fallback_records:
                fb_df = pd.DataFrame(fallback_records)
                # Merge with resolved for continuity
                if not resolved.empty:
                    resolved = pd.concat([resolved, fb_df], ignore_index=True)
                    resolved = resolved.drop_duplicates(subset=['api10'], keep='last')
                else:
                    resolved = fb_df
                resolved.to_csv(out_interim / 'occ_to_wb_resolution.csv', index=False)

                matched_ok = fb_df
                well_ids = matched_ok['wellId'].dropna().astype(str).unique().tolist()
        except Exception:
            pass

    prod = pd.DataFrame()
    if wb_client.headers.get('Api-Key') and well_ids:
        prod = fetch_monthly_production(
            wb_client,
            well_ids,
            args.start,
            args.end,
            max_wells=min(50, len(well_ids)),
            batch_size=25,
            cache_path=out_interim / 'wb_production_sample.csv'
        )
        prod.to_csv(out_interim / 'wb_production_sample.csv', index=False)

    # Feature engineering and simple ranking (if production data exists)
    if not prod.empty:
        feats = engineer_features(prod)
        # Keep wells with any gas in last 36 months or positive q90 or any nonzero historically
        keep_mask = (
            (feats.get('gas_36m', 0) > 0) |
            (feats.get('q90_mcf_d', 0) > 0) |
            (feats.get('nonzero_months_all', 0) > 0)
        )
        feats = feats[keep_mask]
        # Normalize helpers
        def norm(s: pd.Series) -> pd.Series:
            q10, q90 = s.quantile(0.1), s.quantile(0.9)
            return ((s - q10) / max(q90 - q10, 1e-9)).clip(0, 1)

        # Compute composite score emphasizing pre-shut-in strength & consistency
        feats['score'] = (
            0.35 * norm(feats.get('pre_stop_q90_mcf_d', 0)) +
            0.20 * norm(feats.get('pre_stop_peak_mcf', 0)) +
            0.10 * feats.get('pre_stop_nonzero_frac', 0).clip(0, 1.0) +
            0.10 * (1.0 - feats.get('pre_stop_cv', 0).clip(0, 1.5) / 1.5) +
            0.10 * norm(feats.get('gas_24m', 0)) +
            0.05 * feats.get('consistency_score', 0) +
            0.05 * feats.get('dq_prod_cov', 0) +
            0.05 * feats.get('abrupt_stop_flag', 0)
        )

        # Penalties
        feats['penalty_long_shutin'] = (feats['months_since_prod'] > 120).astype(float) * 0.15
        feats['penalty_erratic'] = (feats['cv_12m'] > 0.5).astype(float) * 0.05
        feats['score'] = (feats['score'] - feats['penalty_long_shutin'] - feats['penalty_erratic']).clip(0, 1)

        # Join basic well info
        if 'wellId' in resolved.columns:
            rank = feats.merge(resolved[['api10', 'wellId', 'wellName']], on='wellId', how='left')
        else:
            rank = feats.copy()
        cols = ['api10', 'wellId', 'wellName', 'q90_mcf_d', 'gas_24m', 'consistency_score', 'months_since_prod', 'dq_prod_cov', 'gas_all_time', 'nonzero_months_all', 'score']
        rank = rank[[c for c in cols if c in rank.columns]].sort_values('score', ascending=False)
        rank.to_csv(out_prod / 'ranked_candidates.csv', index=False)

        # Generate detailed JSON reports for top N
        reports_dir = Path('reactivation/reports'); reports_dir.mkdir(parents=True, exist_ok=True)
        analyzer = ReactivationAnalyzer()
        topN = rank.head(max(1, int(args.top)))
        for _, r in topN.iterrows():
            wid = str(r.get('wellId', ''))
            api10 = str(r.get('api10', ''))
            wellname = str(r.get('wellName', ''))
            well_prod = prod[prod['wellId'].astype(str) == wid].to_dict('records')
            well_info = {'api10': api10, 'name': wellname, 'wellId': wid}
            analysis = analyzer.analyze_well(well_prod, well_info)
            try:
                import json
                with open(reports_dir / f"reactivation_analysis_{api10 or wid}.json", 'w') as f:
                    json.dump(analysis, f, indent=2, default=str)
            except Exception:
                pass

    else:
        print('No production rows available; consider increasing offset/limit or adjusting date range.')

    print('Phase 0 pipeline completed.')


if __name__ == '__main__':
    main()


