"""Out-of-sample full-game predictions for the derivatives backtest (2024-26): totals v4 (as analysis/nba_v4_vs_stack.py, Model 1 with
injuries at the opener, lag 1, luck/form/altitude adjustments) -> _tmp/deriv_v4_preds.csv.  Spread margin comes from
analysis/spreads_step1_nba_bets.csv (variant B, the honest v2 model).
  python analysis/derivatives_preds.py WORKDIR"""
import os, sys
W = os.path.abspath(sys.argv[1])
src = open(os.path.join(W, "analysis", "nba_v4_vs_stack.py")).read().split('say(f"games:')[0]
# drop the stack-only input (no-injury tournament predictions), which the v4 number does not use
src = src.replace('NI = pd.concat([pd.read_csv(os.path.join(W, "_tmp", f"old_sbr_preds_{s}.csv")) for s in TESTS], ignore_index=True)\n', "")
src = src.replace('NI["date"] = pd.to_datetime(NI.date)\n', "")
src = src.replace('P = P.merge(NI[["date", "home", "away", "pred_total"]].rename(columns={"pred_total": "m1_noinj"}), on=["date", "home", "away"], how="left")\n', "")
src = src.replace(" & P.m1_noinj.notna()", "")
assert "NI[" not in src and "m1_noinj" not in src
exec(compile(src, "v4_part", "exec"))
P[["date", "season", "home", "away", "pred_margin", "pred_total", "v4", "home_n", "away_n"]].to_csv(os.path.join(W, "_tmp", "deriv_v4_preds.csv"), index=False)
print("saved", len(P), P.season.value_counts().sort_index().to_dict())
