# CAPRI's sugar quota data (CAPTRD's policy stage)

CAPRI's `sugar/load_quotas.gms` reads `%datdir%\sugar\squotas.gms`, `sqrenounce.gms`, `sqcbuyback.gms` and
`sqwithdraw.gms` and stores them as `input_load_sugar_quotas.gdx` (p_SQuotas, p_PPSQRenounce, p_PPSQCBuyBack,
p_PPSQWithdraw). The three CSVs here are that GDX's symbols as the project's parquet mirror of CAPRI's dat folder holds
them (dat/sugar/input_load_sugar_quotas/*.parquet, converted 29 October 2026 without change; columns renamed):

| File | Symbol | Columns |
|---|---|---|
| p_SQuotas.csv | p_SQuotas(MSALL, QUOTAS, year) | region, quota, year, value (1000 t white sugar) |
| p_PPSQRenounce.csv | p_PPSQRenounce(MSALL, year) | region, year, value |
| p_PPSQCBuyBack.csv | p_PPSQCBuyBack(MSALL, year) | region, year, value |

p_PPSQWithdraw is not in the mirror. It is declared in the GDX's unload; a symbol without records is not written by
the mirror's converter, so it is taken as empty (no withdrawal), which the parity of CAPTRD's sugar quotas checks.
