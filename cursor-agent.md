# Cursor Agent — Ch4mber × StrandedGas (Phases 0–2)

## Mission
Automate as much of Phases 0–2 as possible:
- **Phase 0 (Desktop Targeting):** build an AOI-wide pipeline to fetch orphan wells, hydrate with WellDatabase (WB) data, engineer features, and rank ~100 candidates.
- **Phase 1 (Field & Initial Title):** generate field packs (maps, checklists), draft land/title pre-screens from public signals, and output a shortlist (10–15 primary + ~40 secondary).
- **Phase 2 (Initial Reservoir Validation):** compute decline metrics, flag red flags, and produce Go/No-Go with rationale against the ≥300 MCF/d aggregate goal.

## Success Criteria
- Reproducible `ranked_candidates.csv` + `field_packets/` (maps) + `phase2_go_nogo.csv`.
- End-to-end run with `make phase0`, `make phase1`, `make phase2`.
- Clear logs, data lineage, and cached inputs to avoid rate limits.

---

## Guardrails & Coding Standards
- Python 3.11+, **pandas**, **pyproj/shapely**, **geopandas**, **duckdb** (or Postgres), **pydantic** for configs.
- No secrets in code. Read from environment variables.
- All network I/O behind `src/io/` with retries + backoff.
- Deterministic outputs (stable seeds), idempotent ETL (upserts by natural keys).
- Unit tests for feature engineering and scoring functions.

---

## Repository Layout (suggested)
```

/src
/configs
aoi_oklahoma.yaml
/io
welldatabase.py
occ_orphans.py
otc_pun.py
geospatial.py
/features
identity.py
production.py
access_infra.py
risk_legal.py
scoring.py
/pipelines
phase0_desktop.py
phase1_field.py
phase2_reservoir.py
/viz
maps.py
reports.py
/data
/raw      (read-only cache)
/interim  (normalized tables)
/prod     (final reports)
/notebooks  (ad hoc EDA)
/tests
Makefile
.env.example

```

---

## Environment Variables
```

WBD_API_KEY=...
WBD_BASE_URL=https://app.welldatabase.com/api/v2
OCC_ORPHAN_CSV_URL=...   # ArcGIS/CSV or internal mirror
OTC_PUN_EXPORT_PATH=...  # monthly pull location if used
MAPBOX_TOKEN=...         # optional for maps
DB_URL=duckdb:///data/ch4mber.duckdb  # or postgres://...

```

---

## Primary Tasks (Agent)
1. **Fetch AOI**
   - Download OCC orphan list; normalize API10/14; dedupe.
   - Resolve to WB `WellId`/`SimpleId` via `/wells` search.
2. **Hydrate WB**
   - Pull **Well headers/locations**; **Production (monthly)** via `/production/search` using `Filters.InfinityIds` and `ReportDate` window (use `/production/export` only for bulk CSV downloads); **Files** (tags: permits, completions, P&A) when available.
3. **Engineer Features (Phase 0)**
   - Production signals (12/24/36-mo sums, last_prod_date, decline).
   - Consistency metrics (CV, nonzero_frac_12m, last_to_peak_ratio_12m).
   - Access/infrastructure (road proximity, power lines, substation distance) from GIS.
   - Basic risk/legal proxies (operator trail existence, P&A presence, missing docs).
4. **Rank**
   - Score each well (see `docs/business-logic.md`); output `ranked_candidates.csv` (~100).
5. **Phase 1 Outputs**
   - Generate **field packets**: static maps (PLSS, roads, access), photo placeholders, checklists.
   - Draft **title pre-screen** from public hints (operator of record, spacing order IDs if known).
   - Output `phase1_shortlist_primary.csv` (10–15) + `phase1_shortlist_secondary.csv` (~40).
6. **Phase 2 Metrics**
   - Decline curve approximations (exponential/hyperbolic quick fit) on monthly production.
   - Red-flag detection (water cut surge, long shut-in, missing integrity docs).
   - Output `phase2_go_nogo.csv` with rationale.

---

## Key Commands
```

make phase0     # AOI ingest + hydrate + features + ranking (placeholder)
make run-phase0 # Run OCC→WB cautious pipeline (env-driven)
make run-phase0-10 # 10-well sample to quickly validate pipeline
make phase1     # field packet generation + title pre-screen + shortlists
make phase2     # decline metrics + red flags + go/no-go
make clean      # clear /interim and /prod (keep /raw)

```

---

## API Usage (WB v2)
- **/wells** or **/wells/export** → headers/locations (filter ApiState=35).
- **/production/search** (POST) → monthly rows using `Filters.InfinityIds` and `ReportDate`.
- **/production/export** (POST) → bulk CSVs using `Filters.InfinityIds` (fallback/batch).
- **/files**/**/export** (optional) → P&A / completion docs.
- Pagination/backoff handled in client with retries.

---

## Output Contracts
- `/prod/ranked_candidates.csv` (Phase 0)
  - Includes: `q90`, `gas_24m`, `consistency_score`, `dq_prod_cov`, penalties applied.
- `/prod/field_packets/<API10>_packet.pdf` (Phase 1)
- `/prod/phase1_shortlist_primary.csv` + `/prod/phase1_shortlist_secondary.csv`
- `/prod/phase2_go_nogo.csv` (+ plots per well in `/prod/plots/`)

---

## Review Checklist (per PR)
- [ ] Secrets only in env
- [ ] Tests pass
- [ ] Outputs reproduce on sample AOI (10 wells)
- [ ] Docs updated (`docs/data-sources.md`, `docs/business-logic.md`)


