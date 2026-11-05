"""EXPLORATORY (after the pre-registered result): the prize for speed. Bet the side the report's news favors at the last DK line BEFORE
the report's printed time (an upper bound: needs a reaction of a few minutes, not reachable at hourly history resolution), vs at the
first line ~26 min after. One bet per game (first event), |N| >= threshold, -110."""
import os, numpy as np, pandas as pd
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = pd.read_csv(os.path.join(W, "analysis", "report_slot_events.csv.gz"), parse_dates=["t0"])
out = []; say = lambda s: (print(s), out.append(s))
for th in (1.0, 1.5, 2.0):
    for when in ("pre", "act"):
        g = E[E.N.abs() >= th].sort_values("t0").drop_duplicates(["date", "home"]); side = np.sign(g.N); line = g[f"L_{when}"]
        clv = side * (g.L_close - line); res = side * (g.margin - line); u = np.where(res > 0, 100/110, np.where(res < 0, -1.0, 0.0))
        per = pd.DataFrame(dict(s=g.season, u=u)).groupby("s").u.sum().round(1).to_dict()
        say(f"|N|>={th} at {'just before report' if when=='pre' else '~26 min after  '}: {len(g)} bets, CLV {clv.mean():+.2f}, "
            f"{u.sum():+.1f}u ({u.mean()*100:+.1f}%), win {((res>0).sum()/max(1,(res!=0).sum()))*100:.1f}% | by season {per}")
    g = E[E.N.abs() >= th].sort_values("t0").drop_duplicates(["date", "home"])
    for lab, m in (("daytime reports (before 6 PM)", g.hour < 18), ("evening (6 PM+)", g.hour >= 18)):
        h = g[m]; side = np.sign(h.N); res = side * (h.margin - h.L_pre); u = np.where(res > 0, 100/110, np.where(res < 0, -1.0, 0.0))
        say(f"    {lab}, before the report: {len(h)} bets, CLV {(side*(h.L_close-h.L_pre)).mean():+.2f}, {u.sum():+.1f}u ({u.mean()*100:+.1f}%)")
open(os.path.join(W, "analysis", "report_slot_speed_explore_output.txt"), "w").write("\n".join(out) + "\n")
