# Makefile for Phases 0–2 scaffolding
# Loads environment from .env if present

-include .env
export

.PHONY: phase0 phase1 phase2 clean run-phase0 run-phase0-10 run-phase0-50 conda-env conda-update conda-run

conda-env:
	@echo "Creating conda env chamber-wda from environment.yml"
	@conda env create -f environment.yml -n chamber-wda || conda env update -f environment.yml -n chamber-wda

conda-update:
	@echo "Updating conda env chamber-wda"
	@conda env update -f environment.yml -n chamber-wda

conda-run:
	@echo "Running in conda env chamber-wda (loading .env): $(CMD)"
	@conda run -n chamber-wda bash -lc "set -a; [ -f .env ] && . ./.env; set +a; $(CMD)"

phase0:
	@echo "[Phase 0] AOI ingest + hydrate + features + ranking"
	@mkdir -p data/raw data/interim data/prod data/prod/plots
	@printf "api10,score\n3503921577,0.85\n" > data/prod/ranked_candidates.csv
	@echo "Wrote data/prod/ranked_candidates.csv"

run-phase0:
	@echo "[Phase 0] Running OCC→WB pipeline (careful usage)"
	@$(MAKE) conda-run CMD='python -m src.pipelines.phase0_desktop --limit 100 --start 2000-01-01 --end 2024-12-31 --top 5' || true

run-phase0-10:
	@echo "[Phase 0] Running OCC→WB pipeline (10-well sample)"
	@$(MAKE) conda-run CMD='python -m src.pipelines.phase0_desktop --limit 10 --start 2000-01-01 --end 2024-12-31 --force-refresh --top 3' || true

run-phase0-50:
	@echo "[Phase 0] Running OCC→WB pipeline (50-well sample)"
	@$(MAKE) conda-run CMD='python -m src.pipelines.phase0_desktop --limit 50 --offset 1000 --start 1990-01-01 --end 2024-12-31 --force-refresh --top 5' || true

run-phase0-100:
	@echo "[Phase 0] Running OCC→WB pipeline (100-well sample; top 1%)"
	@$(MAKE) conda-run CMD='python -m src.pipelines.phase0_desktop --limit 100 --start 1990-01-01 --end 2024-12-31 --top-percent 1' || true

phase1:
	@echo "[Phase 1] field packet generation + title pre-screen + shortlists"
	@mkdir -p data/prod/field_packets
	@printf "api10\n3503921577\n" > data/prod/phase1_shortlist_primary.csv
	@printf "api10\n3503921578\n3503921579\n" > data/prod/phase1_shortlist_secondary.csv
	@echo "Wrote primary/secondary shortlists under data/prod/"

phase2:
	@echo "[Phase 2] decline metrics + red flags + go/no-go"
	@mkdir -p data/prod
	@printf "well_id,api10,county,q30,q90,q180,EUR_gas,risk_flags,rationale,decision\n" > data/prod/phase2_go_nogo.csv
	@echo "Wrote data/prod/phase2_go_nogo.csv"

clean:
	@echo "Cleaning data/interim and data/prod (keeping data/raw)"
	@rm -rf data/interim data/prod
