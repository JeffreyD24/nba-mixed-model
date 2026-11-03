"""Model 1 shrunk: a side-by-side record (started Nov 3, 2026). Model 1 itself is unchanged.
For every game in state/picks_log.csv (Model 1's locked number and DraftKings' opener):
    shrunk number = opener + w x (Model 1 - opener),  w from data/shrink_weights.json (analysis/shrink_weights.py)
    bet when the shrunk edge is big enough to beat -110 (shrunk edge >= threshold in the same file), graded at the opener.
Because shrinking keeps the order of bets, the bets are a subset of Model 1's; what changes is the cutoff and the honest
estimate of each bet's edge and win chance. Writes state/picks_log_shrunk.csv and prints the record.
  python shrunk_record.py WORKDIR"""
import os, sys, json
import numpy as np, pandas as pd
from scipy.stats import norm
W = os.path.abspath(sys.argv[1]); STATE = os.path.join(W, "state")
cfg = json.load(open(os.path.join(W, "data", "shrink_weights.json")))
P = pd.read_csv(os.path.join(STATE, "picks_log.csv"))
rows = []
for mk, col in (("spread", "open_spread"), ("total", "open_total")):
    c = cfg[mk]; w, thr, sd = c["weight"], c["shrunk_edge_threshold"], c["resid_sd"]
    raw = P[f"{col}_edge"]
    shr = w * raw
    d = pd.DataFrame(dict(game_id=P.game_id, date=P.date, home=P.home, away=P.away, pick_type=P.pick_type, market=mk,
                          line=P[col], model1=P.pred_margin if mk == "spread" else P.pred_total,
                          shrunk=(-P[col] + w * (P.pred_margin + P[col])) if mk == "spread" else (P[col] + w * (P.pred_total - P[col])),
                          raw_edge=raw, shrunk_edge=shr, win_chance=norm.cdf(shr / sd).round(4), side=P[f"{col}_bet"],
                          bet=(shr >= thr) & P[col].notna(), result=P[f"{col}_result"], weight=w, threshold=thr))
    rows.append(d)
S = pd.concat(rows, ignore_index=True).sort_values(["date", "game_id", "market"])
S.to_csv(os.path.join(STATE, "picks_log_shrunk.csv"), index=False)
for mk in ("spread", "total"):
    for lab, sub in (("all", S), ("live only", S[S.pick_type != "backfilled"])):
        b = sub[(sub.market == mk) & sub.bet & sub.result.isin(["W", "L"])]
        w_, l_ = int((b.result == "W").sum()), int((b.result == "L").sum())
        print(f"Model 1 shrunk {mk:6s} ({lab}): {w_}-{l_}, {w_ * 100 / 110 - l_:+.1f}u"
              f" (w={cfg[mk]['weight']}, bet at shrunk edge >= {cfg[mk]['shrunk_edge_threshold']}, raw >= {cfg[mk]['raw_edge_equivalent']})")
