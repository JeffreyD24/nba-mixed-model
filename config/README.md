# Threshold register (started Nov 3, 2026)
`thresholds.csv` lists every number that decides a bet: its value, where it lives, when it was set, which data it was chosen on,
how (in-sample, out of season, not tuned, user rule), and the evidence. `tools/check_thresholds.py` (run each morning) prints a
MISMATCH line if a constant in alert.py no longer matches the register.
**When a threshold changes:** update its row (value, set_on, chosen_on, how_chosen) in the same commit, and add a row to
state/bet_versions.csv so later bets start a new record.
"in-sample" means the record quoted for that rule was measured on the same seasons used to choose it: expect less live.
