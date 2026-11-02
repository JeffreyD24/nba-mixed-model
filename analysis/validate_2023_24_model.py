import sys, pandas as pd, numpy as np
sys.path.insert(0, ".")
from nba_mixed_model import run
T = pd.read_csv("data/training_games.csv")
O = pd.read_csv("data/odds_history/nba_open_close.csv"); dk = O[O.book == "draftkings"][["date", "home", "away", "open_spread", "open_total"]]
T = T.merge(dk.rename(columns={"open_spread": "dk_os", "open_total": "dk_ot"}), on=["date", "home", "away"], how="left")
m = T.season == 2024
T.loc[m, "open_spread"] = T.loc[m, "dk_os"]; T.loc[m, "open_total"] = T.loc[m, "dk_ot"]
s, P = run(T.drop(columns=["dk_os", "dk_ot"]), [2022, 2023], 2024, today_suffix="_open")
P["season"] = 2024
P.to_csv("_tmp/model1_open_preds_2024.csv", index=False)
o = s["test"]["open"]
for mk in ("spread", "total"):
    r = [x for x in o[mk] if x["threshold"] == 3][0]; print("2023-24 at DK opener, edge 3+", mk, r["bets"], r["win_pct"], r["units"])
