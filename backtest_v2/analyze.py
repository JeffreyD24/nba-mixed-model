"""Comparison tables for the three models + paired accuracy tests + referee ablation for Model 3."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/work")
from models_v2 import load, PaceModel, score

W = "/home/claude/work/"
R = json.load(open(W + "results.json"))
rows = []
for test in (2026, 2025):
    for mid in ("1", "2", "3"):
        r = R[f"m{mid}_{test}"]
        a = r["close"]["accuracy"]
        rec = dict(test_season=f"{test - 1}-{str(test)[2:]}", model=mid, margin_mae=a["model_margin_mae"],
                   total_mae=a["model_total_mae"], line_margin_mae=a["line_margin_mae"], line_total_mae=a["line_total_mae"])
        for line in ("open", "close"):
            for mk in ("spread", "total"):
                for t in (3, 4, 5):
                    x = [z for z in r[line][mk] if z["threshold"] == t][0]
                    rec[f"{line}_{mk}_e{t}_bets"] = x["bets"]; rec[f"{line}_{mk}_e{t}_win"] = x["win_pct"]; rec[f"{line}_{mk}_e{t}_roi"] = x["roi"]
        rows.append(rec)
T = pd.DataFrame(rows)
T.to_csv(W + "comparison_table.csv", index=False)

# ---- paired accuracy: is model k more accurate than Model 1 on the same games?
acc = []
for test in (2026, 2025):
    P = {m: pd.read_csv(W + f"pred_m{m}_{test}_close.csv", parse_dates=["date"]).set_index(["date", "home", "away"]) for m in "123"}
    idx = P["1"].index.intersection(P["2"].index).intersection(P["3"].index)
    for m in "23":
        for kind, pc, truth in (("margin", "pred_margin", "margin"), ("total", "pred_total", "tot")):
            e1 = (P["1"].loc[idx, pc] - P["1"].loc[idx, truth]).abs(); ek = (P[m].loc[idx, pc] - P[m].loc[idx, truth]).abs()
            d = ek - e1
            acc.append(dict(test=test, model=m, target=kind, games=len(d), mae_diff_vs_m1=d.mean(),
                            se=d.std() / np.sqrt(len(d)), z=d.mean() / (d.std() / np.sqrt(len(d)))))
A = pd.DataFrame(acc); A.to_csv(W + "accuracy_tests.csv", index=False)
print(A.round(3).to_string())

# ---- Model 3 referee ablation (closing line, same fit, no referee adjustment for the predicted game)
G, lu = load()
abl = []
for train, test in (([2022, 2023, 2024, 2025], 2026), ([2022, 2023, 2024], 2025)):
    M = PaceModel(G).fit(train)
    hl = R[f"m3_{test}"]["info"]["chosen_halflife"]
    hl = None if hl in (None, "None") else int(hl)
    P_on = M.walk(test, hl, "pretip", use_refs=True); P_off = M.walk(test, hl, "pretip", use_refs=False)
    for lab, P in (("with refs", P_on), ("without refs", P_off)):
        res, _, _ = score(P, P_on)
        x = [z for z in res["close"]["total"] if z["threshold"] == 3][0]
        abl.append(dict(test=test, version=lab, total_mae=res["close"]["accuracy"]["model_total_mae"],
                        close_total_e3_bets=x["bets"], close_total_e3_win=x["win_pct"]))
    d = (P_on.pred_total - P_off.pred_total)
    abl.append(dict(test=test, version="ref adjustment size (sd, pts)", total_mae=float(d.std())))
B = pd.DataFrame(abl); B.to_csv(W + "referee_ablation.csv", index=False)
print(B.round(3).to_string())
