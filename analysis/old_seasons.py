"""Older NBA seasons (2009-10 .. 2020-21) to test the Feb-Apr spread traps: Model 1 without injury features (the original
model), walk-forward with two training seasons, graded at the CLOSING spread (no openers before 2021). Standings categories as
in late_season.py (recent arrivals need player logs, not available this far back).
  python analysis/old_seasons.py WORKDIR -> _tmp/old_preds_{season}.csv, analysis/old_seasons_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
from nba_mixed_model import run
K = pd.read_csv("/home/claude/data/cviaxmiwnptr_nba-betting-data-october-2007-to-june-2024/nba_2008-2026.csv")
K = K[K.regular & ~K.playoffs].copy()
K["spread_h"] = np.where(K.whos_favored == "home", -K.spread, K.spread)
D = pd.DataFrame(dict(date=K.date, season=K.season, home=K.home, away=K.away, home_pts=K.score_home, away_pts=K.score_away,
                      spread=K.spread_h, total=K.total)).dropna()
print(sorted(set(D.home)))
for test in range(2010, 2022):
    out = os.path.join(W, "_tmp", f"old_preds_{test}.csv")
    if os.path.exists(out): continue
    s, P = run(D[D.season.isin([test - 2, test - 1, test])], [test - 2, test - 1], test)
    P.to_csv(out, index=False)
    r = [x for x in s["test"]["spread"] if x["threshold"] == 3][0]
    print(test, "spread edge 3+ at close:", r["bets"], r["win_pct"], r["units"], flush=True)
