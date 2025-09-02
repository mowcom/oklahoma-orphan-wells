# Changelog

All notable changes to this repository.

## 2025-09-02
- Switched production retrieval to `/production/search` with Filters (InfinityIds, ReportDate); removed export-based methods from client and examples.
- Added pagination for production search (PageSize=1000, increment PageOffset until exhausted).
- Implemented caching of resolved wells and production rows in `data/interim/`.
- Added pre-shut-in metrics and reweighted scoring to prioritize strong, consistent production before abrupt stop.
- Added `--top` to Phase 0 to generate top-N reports; updated Makefile targets to pass `--top`.
- Cleaned documentation to reflect current method; marked export usage as deprecated (reference only).
- Added OCC prefilter in Phase 0 (status/type screen; identity/location hygiene) producing `occ_prefiltered.csv` and summary JSON.

