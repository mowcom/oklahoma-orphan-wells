# Phase 0 — Oklahoma Orphaned Well Reactivation (Consolidated)

## Summary
- OCC prefilter → WB production search → feature engineering → ranking → top-N reports.
- Production retrieval is via `/production/search` with Filters (InfinityIds, ReportDate) and paging.

## Workflow
1) OCC Orphan Identification & Prefilter
- Type screen: keep `welltype` ∈ {GAS, OIL, O&G, OIL & GAS}
- Identity/location: valid `api_10` (starts with 35), dedupe by `api_10`, lat/lon in OK bounds
- Outputs: `data/interim/occ_prefiltered.csv`, `occ_prefilter_summary.json`

2) WB Resolution & Production
- Resolve API10s → `wellId` via `/wells/search`
- Pull monthly production via `/production/search` with paging; cache to `wb_production_sample.csv`

3) Feature Engineering & Ranking
- Recent windows: `gas_12m/24m/36m`, `cv_12m`, `nonzero_frac_12m`, `dq_prod_cov`
- Pre-shut-in metrics: `pre_stop_q90_mcf_d`, `pre_stop_peak_mcf`, `pre_stop_cv`, `pre_stop_nonzero_frac`, `abrupt_stop_flag`
- Score emphasizes pre-shut-in strength/consistency and abrupt stop

4) Outputs
- `data/prod/ranked_candidates.csv` (sorted by `score`)
- Adds `rank_index` and `rank_percentile` columns and writes `top_candidates.csv` when `--top` or `--top-percent` used.
- Top-N JSON reports in `reactivation/reports/`

## Make targets
- `make run-phase0-10` / `run-phase0-50` (loads .env via conda-run)

## Notes
- See `docs/data-sources.md` for field inventories
- See `docs/business-logic.md` for scoring details
