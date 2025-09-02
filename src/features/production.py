"""Production feature engineering utilities for Phase 0.

Computes:
- gas_12m/gas_24m/gas_36m
- last_prod_month, months_since_prod
- consistency metrics: cv_12m, nonzero_frac_12m, last_to_peak_ratio_12m, consistency_score
- simple DCA proxies: q90 (heuristic fallback if no robust fit)

Notes:
- Water-related features are optional; WB `wellWater` is inconsistently populated.
- Full decline curve fitting (hyperbolic) can be added later; we provide a safe fallback.
"""

from __future__ import annotations

from typing import Dict, Tuple
import pandas as pd
import numpy as np


def _ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    date_cols = ['reportDate']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    if 'reportYear' in df.columns and 'reportMonth' in df.columns and 'reportDate' not in df.columns:
        df['reportDate'] = pd.to_datetime(df[['reportYear', 'reportMonth']].assign(day=1), errors='coerce')
    return df


def _gas_series(df: pd.DataFrame) -> pd.Series:
    if 'wellGas' in df.columns:
        return pd.to_numeric(df['wellGas'], errors='coerce').fillna(0)
    if 'totalGas' in df.columns:
        return pd.to_numeric(df['totalGas'], errors='coerce').fillna(0)
    return pd.Series(np.zeros(len(df)))


def compute_recent_windows(df: pd.DataFrame, asof: pd.Timestamp | None = None) -> Dict[str, float]:
    if df.empty:
        return {k: 0.0 for k in ['gas_12m', 'gas_24m', 'gas_36m', 'cv_12m', 'nonzero_frac_12m', 'last_to_peak_ratio_12m']}
    df = df.sort_values('reportDate').copy()
    gas = _gas_series(df)
    df['gas_mcf'] = gas

    # Define the trailing 36-month window based on last reportDate
    last_date = df['reportDate'].max()
    window_start = (last_date - pd.DateOffset(months=36)) if pd.notna(last_date) else None
    recent = df[df['reportDate'] >= window_start] if window_start is not None else df.tail(36)
    gas_36m = float(recent['gas_mcf'].sum())
    gas_24m = float(recent.tail(24)['gas_mcf'].sum())
    gas_12m = float(recent.tail(12)['gas_mcf'].sum())

    last12 = recent.tail(12)
    last_vals = last12['gas_mcf']
    mean12 = last_vals.mean() if not last_vals.empty else 0.0
    std12 = last_vals.std(ddof=0) if not last_vals.empty else 0.0
    cv_12m = float(std12 / mean12) if mean12 > 0 else 0.0

    nonzero_frac_12m = float((last_vals > 0).mean()) if not last_vals.empty else 0.0
    peak12 = float(last_vals.max()) if not last_vals.empty else 0.0
    last_month_val = float(last_vals.iloc[-1]) if len(last_vals) > 0 else 0.0
    last_to_peak_ratio_12m = float(last_month_val / peak12) if peak12 > 0 else 0.0

    # Data quality coverage over trailing 36 months (fraction of months with any data)
    if not recent.empty and 'reportDate' in recent.columns:
        months = recent['reportDate'].dt.to_period('M').dropna().unique()
        dq_prod_cov = float(len(months)) / 36.0
        dq_prod_cov = float(np.clip(dq_prod_cov, 0.0, 1.0))
    else:
        dq_prod_cov = 0.0

    return {
        'gas_12m': gas_12m,
        'gas_24m': gas_24m,
        'gas_36m': gas_36m,
        'cv_12m': cv_12m,
        'nonzero_frac_12m': nonzero_frac_12m,
        'last_to_peak_ratio_12m': last_to_peak_ratio_12m,
        'dq_prod_cov': dq_prod_cov,
    }


def compute_recency_metrics(df: pd.DataFrame, asof: pd.Timestamp | None = None) -> Dict[str, float]:
    if df.empty or 'reportDate' not in df.columns:
        return {'last_prod_month': None, 'months_since_prod': 1e9}
    df = df.sort_values('reportDate')
    last_date = df['reportDate'].max()
    asof = asof or pd.Timestamp.today().normalize()
    months_since = (asof.year - last_date.year) * 12 + (asof.month - last_date.month)
    return {
        'last_prod_month': str(last_date.date()),
        'months_since_prod': float(months_since),
    }


def heuristic_q90(df: pd.DataFrame) -> Tuple[float, float]:
    """Heuristic short-term forecast q90 with fit quality proxy.

    Fallback method when robust DCA isn't available:
    - Take last 12 months, compute rolling 3-month average, use last value as q90 proxy.
    - Fit quality ~ number of non-zero months / 12.
    """
    if df.empty:
        return 0.0, 0.0
    df = df.sort_values('reportDate')
    gas = _gas_series(df)
    last12 = gas.tail(12)
    q90_proxy = float(last12.rolling(window=3, min_periods=1).mean().iloc[-1]) / 30.0  # MCF/d approx
    fit_quality = float((last12 > 0).mean())
    return q90_proxy, fit_quality


def compute_consistency_score(cv_12m: float, nonzero_frac_12m: float, last_to_peak_ratio_12m: float) -> float:
    # Lower CV is better; invert and cap
    cv_component = 1.0 - float(np.clip(cv_12m, 0.0, 1.5)) / 1.5
    # Weight components
    score = 0.5 * cv_component + 0.25 * float(np.clip(nonzero_frac_12m, 0.0, 1.0)) + 0.25 * float(np.clip(last_to_peak_ratio_12m, 0.0, 1.0))
    return float(np.clip(score, 0.0, 1.0))


def compute_pre_shutin_metrics(df: pd.DataFrame) -> Dict[str, float | int | str]:
    """Compute pre-shut-in strength and consistency metrics.

    Focuses on the 12 months leading up to the last non-zero production month.
    If fewer than 12 months are available, uses whatever exists prior to shut-in.
    """
    if df.empty:
        return {
            'pre_stop_avg_mcf': 0.0,
            'pre_stop_peak_mcf': 0.0,
            'pre_stop_cv': 0.0,
            'pre_stop_nonzero_frac': 0.0,
            'pre_stop_last_to_peak_ratio': 0.0,
            'pre_stop_q90_mcf_d': 0.0,
            'abrupt_stop_flag': 0.0,
            'last_nonzero_date': None,
        }

    df = df.sort_values('reportDate').copy()
    gas = _gas_series(df)
    nonzero_mask = gas > 0
    if not nonzero_mask.any():
        return {
            'pre_stop_avg_mcf': 0.0,
            'pre_stop_peak_mcf': 0.0,
            'pre_stop_cv': 0.0,
            'pre_stop_nonzero_frac': 0.0,
            'pre_stop_last_to_peak_ratio': 0.0,
            'pre_stop_q90_mcf_d': 0.0,
            'abrupt_stop_flag': 0.0,
            'last_nonzero_date': None,
        }

    last_nz_idx = np.where(nonzero_mask.values)[0][-1]
    last_nz_date = pd.to_datetime(df.iloc[last_nz_idx]['reportDate']) if 'reportDate' in df.columns else None

    # Window: 12 months leading to last non-zero month
    window_end = last_nz_date
    window_start = (window_end - pd.DateOffset(months=12)) if pd.notna(window_end) else None
    pre = df[(df['reportDate'] <= window_end) & (df['reportDate'] >= window_start)].copy() if window_start is not None else df.iloc[:last_nz_idx+1].tail(12).copy()
    pre_gas = _gas_series(pre)

    # Basic stats
    pre_nonzero = pre_gas[pre_gas > 0]
    avg_mcf = float(pre_nonzero.mean()) if not pre_nonzero.empty else 0.0
    peak_mcf = float(pre_nonzero.max()) if not pre_nonzero.empty else 0.0
    mean_pre = float(pre_nonzero.mean()) if not pre_nonzero.empty else 0.0
    std_pre = float(pre_nonzero.std(ddof=0)) if not pre_nonzero.empty else 0.0
    cv_pre = float(std_pre / mean_pre) if mean_pre > 0 else 0.0
    nonzero_frac = float((pre_gas > 0).mean()) if len(pre_gas) > 0 else 0.0
    last_val = float(pre_gas.iloc[-1]) if len(pre_gas) > 0 else 0.0
    last_to_peak = float(last_val / peak_mcf) if peak_mcf > 0 else 0.0

    # q90 proxy before shut-in: average of last up-to-3 nonzero months / 30
    nz_tail = pre_nonzero.tail(3)
    pre_q90_mcf_d = float(nz_tail.mean()) / 30.0 if not nz_tail.empty else 0.0

    # Abrupt stop: after last nonzero there are no further nonzero months
    post = df.iloc[last_nz_idx+1:]
    abrupt_stop_flag = 1.0 if (not post.empty and (_gas_series(post) <= 0).all()) else 0.0

    return {
        'pre_stop_avg_mcf': avg_mcf,
        'pre_stop_peak_mcf': peak_mcf,
        'pre_stop_cv': cv_pre,
        'pre_stop_nonzero_frac': nonzero_frac,
        'pre_stop_last_to_peak_ratio': last_to_peak,
        'pre_stop_q90_mcf_d': pre_q90_mcf_d,
        'abrupt_stop_flag': abrupt_stop_flag,
        'last_nonzero_date': str(last_nz_date.date()) if pd.notna(last_nz_date) else None,
    }


def engineer_features(production_df: pd.DataFrame) -> pd.DataFrame:
    """Engineer per-well features from monthly production rows.

    Expects columns including `wellId`, `reportDate`, `wellGas` or `totalGas`.
    Returns one row per `wellId` with engineered features.
    """
    if production_df.empty:
        return pd.DataFrame()
    df = production_df.copy()
    df = _ensure_datetime(df)
    df['gas_mcf'] = _gas_series(df)
    features: list[dict] = []
    for well_id, group in df.groupby('wellId'):
        group = group[group['reportDate'].notna()]
        rec = {'wellId': well_id}
        rec.update(compute_recent_windows(group))
        rec.update(compute_recency_metrics(group))
        rec.update(compute_pre_shutin_metrics(group))
        q90, fit_q = heuristic_q90(group)
        rec['q90_mcf_d'] = q90
        rec['dca_fit_quality'] = fit_q
        rec['consistency_score'] = compute_consistency_score(rec['cv_12m'], rec['nonzero_frac_12m'], rec['last_to_peak_ratio_12m'])
        gas_series = _gas_series(group)
        rec['gas_all_time'] = float(gas_series.sum())
        rec['nonzero_months_all'] = int((gas_series > 0).sum())
        features.append(rec)
    return pd.DataFrame(features)


