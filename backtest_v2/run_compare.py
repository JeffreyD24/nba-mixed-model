"""
Fit and backtest all three models on identical games and seasons.
  Test:  train 2021-22..2024-25, test 2025-26
  Check: train 2021-22..2023-24, test 2024-25
Closing lines use the last injury report before tip (+ referees for Model 3);
opening lines use the night-before report and no referees (crews are announced the morning of the game).
Usage: python3 run_compare.py [models...]   e.g.  run_compare.py 1 3
"""
import sys, json, time
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/work")
from models_v2 import load, PlayerModel, PaceModel, tune_and_test, score, run_model1, evaluate

W = "/home/claude/work/"
SPLITS = [([2022, 2023, 2024, 2025], 2026), ([2022, 2023, 2024], 2025)]
which = sys.argv[1:] or ["1", "2", "3"]
G, lu = load()
results = json.load(open(W + "results.json")) if len(sys.argv) > 1 and __import__("os").path.exists(W + "results.json") else {}

for train, test in SPLITS:
    for mid in which:
        t0 = time.time()
        print(f"=== Model {mid}: train {train} test {test}", flush=True)
        if mid == "1":
            # Model 1 exactly as in the repo, on the same games (the 6 games without box scores dropped)
            cols = ["date", "season", "home", "away", "home_pts", "away_pts", "spread", "total", "open_spread", "open_total",
                    "home_miss_off", "home_miss_def", "away_miss_off", "away_miss_def",
                    "home_miss_off_open", "home_miss_def_open", "away_miss_off_open", "away_miss_def_open"]
            df = G[cols].copy()
            summ, Pc = run_model1(df, train, test)
            _, Po = run_model1(df, train, test, today_suffix="_open")
            info = dict(chosen_halflife=summ["chosen_halflife"], fixed_effects=summ["fixed_effects"])
            Pc = Pc.rename(columns={})
            Po = Po
        else:
            M = (PlayerModel if mid == "2" else PaceModel)(G, lu).fit(train)
            hl, tune, Pc, Po = tune_and_test(M, train, test)
            info = dict(chosen_halflife=hl, tuning=tune, **M.summary)
        res, Pc2, Po2 = score(Pc, Po)
        Pc2.to_csv(W + f"pred_m{mid}_{test}_close.csv", index=False)
        Po2.to_csv(W + f"pred_m{mid}_{test}_open.csv", index=False)
        results[f"m{mid}_{test}"] = dict(info=info, **res)
        a = res["close"]["accuracy"]
        print(f"  margin MAE {a['model_margin_mae']:.3f} (line {a['line_margin_mae']:.3f})  "
              f"total MAE {a['model_total_mae']:.3f} (line {a['line_total_mae']:.3f})", flush=True)
        for k in ("close", "open"):
            for mk in ("spread", "total"):
                r = [x for x in res[k][mk] if x["threshold"] == 3][0]
                print(f"  {k:5s} {mk:6s} edge>=3: {r['bets']} bets {r['win_pct']} roi {r['roi']}", flush=True)
        print(f"  ({time.time() - t0:.0f}s)", flush=True)
        json.dump(results, open(W + "results.json", "w"), indent=1, default=float)
