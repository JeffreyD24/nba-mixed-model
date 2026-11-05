"""Re-grade NCAAM Model 1 and tournament M5 at real sportsbooks' own openers (ncaab/research/BOOK_OPENER_PREREG_2026-11-05.md).
Per game: DraftKings' opener when ESPN lists it, else ESPN BET's.  python ncaab/book_opener_test.py WORKDIR -> ncaab/research/book_opener_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
P = pd.read_csv(os.path.join(W, "ncaab", "data", "tourn_preds.csv"), low_memory=False); P["date"] = pd.to_datetime(P.date)
long = pd.concat([P[["season", "date", "hk"]].rename(columns={"hk": "t"}), P[["season", "date", "ak"]].rename(columns={"ak": "t"})]).sort_values("date")
long["n"] = long.groupby(["season", "t"]).cumcount(); fg = long.groupby(["season", "t", "date"]).n.min()
P["hn"] = [fg.get((s, t, d), 0) for s, t, d in zip(P.season, P.hk, P.date)]; P["an"] = [fg.get((s, t, d), 0) for s, t, d in zip(P.season, P.ak, P.date)]
ok = P.home_d1 & P.away_d1 & P.neutral_ok & (np.minimum(P.hn, P.an) >= 3) & P.espn_id.notna()
E = pd.read_csv(os.path.join(W, "ncaab", "data", "espn_openers.csv"))
pick = pd.concat([E[E.provider == "DraftKings"].assign(pr=0), E[E.provider == "ESPN BET"].assign(pr=1)]).dropna(subset=["open_spread", "open_total"], how="all")
pick = pick.sort_values("pr").drop_duplicates("espn_id").set_index("espn_id")
D = P[ok].copy(); D["eid"] = D.espn_id.astype(int); D = D.join(pick[["provider", "open_spread", "open_total"]].rename(columns={"open_spread": "b_sp", "open_total": "b_tot"}), on="eid", how="inner")
say(f"{len(D)} eligible games with a book opener; book by season: {D.groupby(['season', 'provider']).size().to_dict()}")
say(f"(descriptive) |book opener - AN Open|: spreads {(D.b_sp - D.open_spread).abs().mean():.2f} pts, totals {(D.b_tot - D.open_total).abs().mean():.2f} pts")
BE = {"spread": 0.67, "total": 0.99}; TH = {"spread": 5, "total": 6}; rng = np.random.default_rng(3)
for mk in ("spread", "total"):
    for mod in ("M1", "M5"):
        for lab, line_src in (("AN Open (as before)", "an"), ("book's own opener", "book")):
            if mk == "spread":
                line = -(D.b_sp if line_src == "book" else D.open_spread); close = -D.dk_spread; res = D.home_pts - D.away_pts; m = D[f"{mod}_m"]
                bad = (D.b_sp - D.dk_spread).abs() > 10
            else:
                line = D.b_tot if line_src == "book" else D.open_total; close = D.dk_total; res = D.home_pts + D.away_pts; m = D[f"{mod}_t"]
                bad = (D.b_tot - D.dk_total).abs() > 15
            e = m - line; k = line.notna() & close.notna() & ~bad & (e.abs() >= TH[mk]) & m.notna()
            sg = np.sign(e[k]); clv = sg * (close[k] - line[k]); r = sg * (res[k] - line[k]); u = np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0))
            bys = {s: float(u[(D.season[k] == s).values].sum()) for s in sorted(D.season[k].unique())}; w, l = int((r > 0).sum()), int((r < 0).sum())
            passed = clv.mean() >= BE[mk] and u.sum() > 0 and min(bys.values()) >= -5
            say(f"  {mk:6s} {mod} {lab:20s} {int(k.sum()):4d} bets {w}-{l} {w / max(w + l, 1):.1%} {u.sum():+6.1f}u  CLV {clv.mean():+.2f} (b/e {BE[mk]})  by season "
                + " ".join(f"{s % 100:02d}:{v:+.1f}" for s, v in bys.items()) + (f"  -> {'PASS' if passed else 'FAIL'}" if line_src == "book" else ""))
open(os.path.join(W, "ncaab", "research", "book_opener_output.txt"), "w").write("\n".join(out) + "\n")
