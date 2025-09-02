# Business Logic — Phases 0–2 (Selection, Ranking, Go/No-Go)

## Objective
Produce a **ranked list (~100)** in Phase 0, a **field-ready shortlist (10–15 primary + ~40 secondary)** in Phase 1, and **Phase-2 Go/No-Go** decisions that together can achieve **≥300 MCF/d aggregate** when activated.

---

## Phase 0 — Desktop Targeting

### 0.1 Inclusion Rules
- In **OCC orphan registry** (API10/14 match).
- Located in **Oklahoma (ApiState=35)**.
- Valid coordinates or resolvable legal (PLSS).

### 0.2 Feature Engineering (Signals)
**Production (from WB monthly):**
- `gas_12m`, `gas_24m`, `gas_36m` — sum gas (MCF).
- `last_prod_month`, `months_since_prod`.
- Quick decline approximations:
  - Fit `q(t) = qi / (1 + b*Di*t)^(1/b)` (hyperbolic) **or** exponential fallback on last 24–36 months.
  - Derive `q90` (predicted 90-day average MCF/d) and `b` sanity bounds.
- `consistency_score` — stability of recent production (e.g., last-12 mean ÷ last-12 peak, or 1 − CV).
- `nonzero_frac_12m` — fraction of non-zero months in last 12.
- `last_to_peak_ratio_12m` — last-month ÷ peak-month in last 12.

New (pre-shut-in window):
- `pre_stop_q90_mcf_d` — 90-day avg proxy from last 3 nonzero months before shut-in.
- `pre_stop_peak_mcf` — peak MCF in 12 months before shut-in.
- `pre_stop_cv` — CV of nonzero months pre-shut-in (lower is better).
- `pre_stop_nonzero_frac` — fraction of nonzero months pre-shut-in.
- `pre_stop_last_to_peak_ratio` — last pre-stop ÷ peak pre-stop.
- `abrupt_stop_flag` — 1 if production stops to 0 after last nonzero month.

**Access/Infrastructure (GIS):**
- `dist_paved_km`, `dist_road_km`, `slope_pct`.
- `dist_substation_km` or `dist_powerline_km` (proxy for logistics).
- `access_score` ∈ [0,1] via min-max of distances & slope.

**Risk/Legal Proxies:**
- `has_pa_doc`, `has_completion_doc`, `has_permit_doc` (WB files/tags).
- `operator_trail_score` (1 if operator aliased/reported present; 0 otherwise).
- `long_shutin_flag` (`months_since_prod` > threshold, e.g., 48).

**Data Quality:**
- `dq_prod_cov` = fraction of months with data in trailing 36 months.
- `dq_loc` = 1 if lat/lon precise; else 0 (PLSS only).
 - `dca_fit_quality` — goodness of fit metric for decline (e.g., R² on exponential tail).

### 0.3 Ranking Score (refined)
```

score =
0.35 * norm(pre_stop_q90_mcf_d) +
0.20 * norm(pre_stop_peak_mcf) +
0.10 * pre_stop_nonzero_frac +
0.10 * (1 − min(pre_stop_cv,1.5)/1.5) +
0.10 * norm(gas_24m) +
0.05 * consistency_score +
0.05 * dq_prod_cov +
0.05 * abrupt_stop_flag  # prefers strong, consistent production that stopped abruptly

```
**Penalties:**
- −0.15 if `long_shutin_flag` true.
- −0.10 if `dq_loc` == 0.
- −0.05 to −0.10 if highly erratic production (e.g., last-12 CV > 0.5).
- Hard drop if `months_since_prod` > 120 **and** no completion/permit history.

Notes:
- Cap `q90` to a reasonable multiple of recent observed rates to avoid optimistic fits.
- If DCA fit quality is poor or data coverage is too low, fallback to simpler heuristics (e.g., average of last 3 months) and down-weight score.

> `norm(x)` = robust scaling by AOI quantiles (e.g., (x − Q10)/(Q90 − Q10), clipped 0–1).

### 0.4 Outputs
- `ranked_candidates.csv` with all features & `score`, sorted desc.
- Keep top ~100 for Phase 1.

---

## Phase 1 — Field Survey & Initial Title

### 1.1 Field Packet (per candidate)
- Static map: PLSS grid, roads, slope, access routes, nearby power.
- One-pager: header info, production sparkline, access notes, known risks.
- Checklist: wellhead integrity visual cues, equipment present, neighbor proximity.

### 1.2 Initial Title Signals (desk)
- Operator of record present? (`operators_aliased`/`reported`).
- Spacing/pooling order numbers referenced in docs (if any).
- Recent county filings existence (binary; details Phase 3).

### 1.3 Shortlisting Rules
- **Primary (10–15):** top rank **AND** `q90` above site-specific floor (e.g., ≥50–75 MCF/d), `access_score ≥ 0.5`, no major red flags.
- **Secondary (~40):** good rank **OR** promising with a single remediable gap (e.g., long shut-in but strong history or easy access).

### 1.4 Outputs
- `phase1_shortlist_primary.csv`, `phase1_shortlist_secondary.csv`
- `/field_packets/` (PDFs or HTML) for site visits.

---

## Phase 2 — Initial Reservoir Validation

### 2.1 Decline & Forecast (quick)
- Fit exponential & hyperbolic; choose best by RMSE.
- Produce `q30`, `q90`, `q180` (MCF/d) and `EUR_gas` rough cut.
- Flag **water risk** if water fraction rising > X% over last N months.

### 2.2 Red Flags
- **Mechanical:** inconsistent production + known P&A work; missing wellhead equipment.
- **Reservoir:** steep decline (`b<0.2` & high initial), high water cut trend.
- **Operational:** months_since_prod > 60 with no evidence of rehab path.

### 2.3 Portfolio Gate (≥300 MCF/d)
- Choose combination of **primary** wells such that Σ`q90_selected` ≥ 300.
- Prefer diversity (county/operator spread) to reduce correlated risk.
- Keep alternates to swap if field checks downgrade candidates.

### 2.4 Go/No-Go Output
- `phase2_go_nogo.csv` with columns:
  - `well_id, api10, county, q30, q90, q180, EUR_gas, risk_flags, rationale, decision`
- Plots per well: monthly gas, fitted curve, residuals, water cut (if available).

---

## Pseudocode (pipeline blueprint)
```python
# Phase 0
orphans = load_occ_orphan_list()
wb_ids = resolve_wb_ids(orphans.api10_14)
wells = wb_fetch_wells(wb_ids)
prod = wb_fetch_production_monthly(wb_ids, start="1990-01-01")
features = make_features(wells, prod, gis_layers, wb_files)
scores = rank_candidates(features)
write_csv(scores.sort_values("score", ascending=False), "ranked_candidates.csv")

# Phase 1
primary, secondary = shortlist(scores)
build_field_packets(primary + secondary, wells, gis_layers)
write_csv(primary, "phase1_shortlist_primary.csv")
write_csv(secondary, "phase1_shortlist_secondary.csv")

# Phase 2
decline = fit_decline_curves(prod[prod.well_id.isin(primary.ids)])
go_nogo = evaluate(decisions=decline, rules=portfolio_rules)
write_csv(go_nogo, "phase2_go_nogo.csv")
```

---

## Data Quality & QC

* Assert monthly completeness windows; impute only with documented rules.
* Cross-check WB production against OTC/PUN on a sample for drift.
* Log all drops with reasons (e.g., missing coords, unresolved IDs).
* Keep run metadata (inputs’ hashes, API call counts, durations).

---

## Deliverables by Phase

* **P0:** `ranked_candidates.csv`
* **P1:** `phase1_shortlist_primary.csv`, `phase1_shortlist_secondary.csv`, `/field_packets/`
* **P2:** `phase2_go_nogo.csv`, `/plots/`
