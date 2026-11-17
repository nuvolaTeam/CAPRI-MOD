# Development notes

This folder holds the notes written while building capri-mod: plans, inventories, reviews, audits and logs. They
record how the code got to its present form and what was checked on the way. They are not needed to run the model or
read its results; for that, see the documents one level up (`docs/`), the registers there (`KNOWN_ISSUES.md`,
`DEPARTURES_FROM_CAPRI.md`, `CAPRI_DEPARTURES_REGISTER.md`) and `CHANGELOG.md` at the repository root.

| Kind | Files |
|---|---|
| Plans and designs | `*_PLAN.md`, `*_DESIGN.md`, `MARKET_SYSTEM.md`, `MANURE_POOL_PORT.md`, `MARKET_TRQ_PORT.md`, `CAPTRD_MOD.md` |
| Inventories and maps | `*_INVENTORY.*`, `SETTINGS_INVENTORY.csv` (every setting, with CAPRI's equivalent), `CAPTRD_MAP.md`, `SUPPLY_CODE_TABLES.md`, `HARDCODED_TABLES.md` |
| Data layout | `DATA_LAYOUT.md`, `DATA_SCHEMA_DUCKDB.md`, `DATA_PIPELINE_DOIT.md`, `DATA_FIXES.md` |
| Reviews, audits and checks | `MODULE_COUPLING_REVIEW.md`, `MARKET_NLP_REVIEW_2026-11-01.md`, `PROXY_AUDIT.md`, `SYNTHETIC_DATA_AUDIT.md`, `MARKET_SOLVE_CHECK.md`, `TARV_COMPARISON.md`, `audit/` |
| Logs | `COUPLING_SPRINTS.md`, `KNOWN_ISSUES_REGISTRY_LOG.md`, `REGIONAL_UNITS_REBUILD_LOG.md`, `REFACTOR_BEHAVIOUR_CHANGES.md` |
| State of the art | `sota/` |
| Superseded | `archive/` |
