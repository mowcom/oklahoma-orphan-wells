# Data Source Overview (OK Orphan Wells — Phases 0–2)

## 1) Oklahoma Corporation Commission (OCC) — Orphan Registry
- **What:** Official orphan/orphan-fund wells list (API, status, metadata).
- **Access:** ArcGIS/CSV export (mirrored internally if needed).
- **Cadence:** Weekly sync.
- **Fields (typical):** API10/14, well name, county, status, case #, coordinates.
- **Use:** AOI ground truth; join key for resolving to WellDatabase WellIds.
- **Notes:** Normalize API formats; keep both 10- and 14-digit forms.

### Fields / Features (expected)
- Identity
  - `api` (raw), `api_10`, `api_14`, `valid_oklahoma_api`
  - `well_name`, `operator` (if present), `county`
- Status / Type
  - `wellstatus` (e.g., OR orphan code)
  - `welltype` (e.g., GAS, OIL)
  - Optional: `wellstatusdesc`/descriptive status
- Regulatory / Case (when available)
  - `case_number`, `cause`, `order_no`
- Dates (when available)
  - `spud_date`, `completion_date`, `plug_date`
- Location
  - `latitude`, `longitude` (point geometry from GIS)
- Derived (our pipeline)
  - `api_raw`, `api_clean` (normalization helpers)

### Phase 0 Prefilter (OCC-only)
- **Status/type screen:** Keep “Orphaned - Shut In”, “Orphaned - Completed - Not Active” where available; drop Plugged/P&A/TA, Injection/Disposal/Water/Seismic/Unknown types. Trim ≈20–35%.
- **Identity/location hygiene:** Drop missing/invalid API10/14; drop dupes by API10; require valid lat/lon inside Oklahoma bounds. Trim ≈5–10%.
- Outputs: `data/interim/occ_prefiltered.csv` and `occ_prefilter_summary.json`.

## 2) WellDatabase (WB) — v2 API
- **Base:** `https://app.welldatabase.com/api/v2`
- **Auth:** `ApiKey` via query/header.
- **Core Endpoints:**
  - `/wells` or `/wells/export` — headers (Id, Api10/14, names, operator, status).
  - `/welllocation` (often embedded in wells).
  - `/production/search` (POST) — monthly production rows via Filters (InfinityIds, ReportDate).
  - `/files` `/filetags` — docs (permits, completions, P&A) when available.
- **Filters to know:** `ApiState=35 (Oklahoma)`, `ReportDate.Min/Max` for production.
- **Use:** Hydrate identity, monthly history, supporting docs.

### Fields / Features (expected)
- Wells (search)
  - `wellId`, `simpleId`, `api10`, `api14`, `wellName`, `operator`, `status`, `county`, `stateId`
  - `latitude`, `longitude` (if provided), `firstProd`, `lastProd` (if provided)
- Production (monthly; `/production/search`)
  - `id`, `wellId`, `reportDate`, `reportMonth`, `reportYear`, `days`
  - Gas: `wellGas`, `totalGas`, `wellDailyGas`
  - Oil: `wellOil`, `totalOil`, `wellDailyOil`
  - Water: `wellWater`
  - `operator` (reported)
- Files (when available)
  - `fileId`, `tags`, `fileName`, `url`, `date`

R&D callouts:
- Water volumes are inconsistently reported; treat `wellWater` as optional and plan Phase 1 validation.
- File/document coverage varies by operator; `has_completion_doc` and `has_permit_doc` may require tag mapping.
- `stateId` returned by WB may not match OCC expectations; rely on OCC API10 prefix (35) for OK validation.

## 3) OTC/OCC PUN (Authoritative Production — optional Phase 2)
- **What:** Official monthly production by lease/well (PUN).
- **Access:** Portal/CSV (account).
- **Use:** Validate WB monthly; fill legacy gaps; legal/royalty truth source.
- **Cadence:** Monthly.

### Fields / Features (typical)
- Identity
  - `pun` (production unit number), `lease_name`/`well_name`, `operator`, `county`
- Monthly production
  - `report_month`/`report_date`
  - `gas_mcf`, `oil_bbl`, `water_bbl`, `days`
  - Optional: `well_count`, `formation`

## 4) County Records (Washita, Beckham initially)
- **What:** Leases, assignments, pooling orders, SUAs, easements.
- **Access:** Clerk portals (e.g., okcountyrecords.com) — manual export.
- **Use:** Phase 1 pre-screen signals; Phase 3 deep title (reference only in 0–2).

### Fields / Features (typical)
- Document
  - `instrument_no`, `doc_type`, `file_date`, `book_page`
- Parties
  - `grantor`, `grantee` (or equivalent)
- Legal description
  - `section`, `township`, `range`, `quarter`
- Links
  - `pdf_url`/`image_url`

## 5) GIS Layers
- **PLSS & Counties:** Sections/Townships/Ranges for legal locators.
- **Roads (TIGER/OSM):** Access score; distance to improved road.
- **Power Infrastructure (EIA/utilities):** Lines/substations for generator interconnect risk.
- **Terrain (SRTM/DEM):** Site approach difficulty (slope).
- **Use:** Phase 0–1 access/infrastructure features; field maps.

### Fields / Features (derived in pipeline)
- PLSS / Counties
  - `state`, `county`, `section`, `township`, `range`, `meridian`
- Access
  - `dist_paved_km`, `road_class`
- Power
  - `dist_substation_km`, `kv_class_nearby` (if data available)
- Terrain
  - `slope_pct`, `elevation_m`

## 6) StrandedGas Internal Data
- **What:** Prospect leads, buyer requirements, historic notes.
- **Use:** Prioritize candidates aligned to buyer load (e.g., min site MCF/d, region).

### Fields / Features (example)
- Prospect
  - `prospect_id`, `notes`, `region`
- Buyer profile
  - `min_q90_mcf_d`, `county_whitelist`, `risk_tolerances`

## Data Contracts (Internal Tables)
- `ref_ok_orphan_registry(api10, api14, occ_case_no, status, lat, lon, county, updated_at)`
- `wb_wells_ok(well_id, api10, api14, name, operator, status, county, state_id, lat, lon, first_prod, last_prod, updated_at)`
- `wb_prod_monthly(well_id, report_month, oil_bbl, gas_mcf, water_bbl, days_prod)`
- `gis_access(well_id, dist_paved_km, dist_substation_km, slope_pct, road_class)`
- `signals_docs(well_id, has_pa_doc, has_completion_doc, has_permit_doc)`
