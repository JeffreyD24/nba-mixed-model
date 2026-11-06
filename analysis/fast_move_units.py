"""Fast move toward the model: should those bets get more units? (NBA totals, Nov 6, 2026)

Jeffrey's question (after DAL-UTA over, Nov 5: alert at DK 223.5, model 233.9, line 226.5 fifteen minutes later when he bet):
when the DraftKings total has ALREADY moved 3+ points toward our number since the open AND there are still 3+ points of edge
left at the current line, do those bets win often enough to deserve more than 1 unit?

Data: DraftKings pregame total snapshots (The Odds API download, data/odds_history/nba/, ~5-15 min apart for the first hours,
then hourly), seasons 2023-24..2025-26 (labels 2024-2026), joined to the live totals number v4
(analysis/threshold_sweep_2026-11-04/nba_v4_preds.csv: Model 1 + luck + form, morning-lock lag 1), both teams 10+ games.
Graded at the line AND DraftKings price of the snapshot used (fallback -110). One bet per game per design.

Designs
  A  fixed check ~1 hour after the open (first snapshot 30-120 min after DK's first total): bucket by how far the line has
     moved toward the model; bet only if 3+ edge is left at that line.
  B  any time before tip: first snapshot where the line has moved 3+ toward the model with 3+ left (fast or slow).
  C  B split by how fast the 3+ move happened (within 1 h of the open vs later).
  Kelly: how many units the win rate supports relative to the plain 1-unit bet.
  Leave-one-season-out for the "3+ moved, 3+ left" group vs the rest.

  python analysis/fast_move_units.py .  -> analysis/fast_move_units_output.txt, analysis/fast_move_units_bets.csv
  Builds _tmp/dk_total_snaps.csv.gz (all DK pregame total snapshots 2021-26), saved under derived/ (RULE 4)."""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
sys.path.insert(0, W)
TMP = os.path.join(W, "_tmp"); os.makedirs(TMP, exist_ok=True)
try:
    import derived; derived.ensure(W, ["dk_total_snaps.csv.gz"])
except Exception:
    pass
from analysis.odds_openers import NAME  # noqa: E402  (team-name map)

SN = os.path.join(TMP, "dk_total_snaps.csv.gz")
if not os.path.exists(SN):
    parts = []
    for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", "nba", "*.csv.gz"))):
        d = pd.read_csv(f)
        d = d[(d.book == "draftkings") & (d.market == "totals")]
        if not len(d): continue
        parts.append(d[["snapshot_utc", "event_id", "commence_et", "home", "away", "outcome", "price", "point"]])
    S = pd.concat(parts, ignore_index=True)
    S["t"] = pd.to_datetime(S.snapshot_utc)
    S["tip"] = pd.to_datetime(S.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    S = S[S.t < S.tip]
    ov = S[S.outcome == "Over"][["event_id", "t", "tip", "home", "away", "point", "price"]].rename(columns={"price": "p_over"})
    un = S[S.outcome == "Under"][["event_id", "t", "point", "price"]].rename(columns={"price": "p_under", "point": "pt_u"})
    S = ov.merge(un, on=["event_id", "t"], how="left")
    S = S[S.pt_u.isna() | (S.pt_u == S.point)].drop(columns="pt_u").drop_duplicates(["event_id", "t"]).sort_values(["event_id", "t"])
    S["home"] = S.home.map(NAME); S["away"] = S.away.map(NAME)
    S["date"] = S.tip.dt.tz_convert("America/New_York").dt.date.astype(str)
    S.to_csv(SN, index=False, compression="gzip")
S = pd.read_csv(SN, parse_dates=["t", "tip"])

P = pd.read_csv(os.path.join(W, "analysis", "threshold_sweep_2026-11-04", "nba_v4_preds.csv"))
P = P[P.min_games >= 10].copy(); P["act"] = P.home_pts + P.away_pts
S = S.merge(P[["season", "date", "home", "away", "v4", "act"]], on=["date", "home", "away"], how="inner")
S["open"] = S.groupby("event_id").point.transform("first")
S["t0"] = S.groupby("event_id").t.transform("first")
S["mins"] = (S.t - S.t0).dt.total_seconds() / 60
S["side"] = np.sign(S.v4 - S.open)                    # side the model likes at the open
S["mv"] = (S.point - S.open) * S.side                  # + = toward the model
S["left"] = (S.v4 - S.point) * S.side                  # edge left on the opener's side
S["e0"] = (S.v4 - S.open).abs()

def dec(am):
    am = am.fillna(-110)
    return np.where(am > 0, 1 + am / 100, 1 + 100 / -am)
def grade(G, at_open=False):
    line = G.open if at_open else G.point
    r = G.side * (G.act - line)
    pr = np.where(G.side > 0, G.p_over, G.p_under)
    if at_open: pr = np.full(len(G), -110.0)
    d = dec(pd.Series(pr, index=G.index))
    u = np.where(r > 0, d - 1, np.where(r < 0, -1.0, 0.0))
    return r, u
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
def line(G, lab, at_open=False):
    if not len(G): say(f"  {lab:44s}    0 bets"); return
    r, u = grade(G, at_open); w, l = int((r > 0).sum()), int((r < 0).sum())
    by = []
    for s in (2024, 2025, 2026):
        m = (G.season == s).values; ws, ls = int((r[m] > 0).sum()), int((r[m] < 0).sum())
        by.append(f"{s}: {ws}-{ls} {u[m].sum():+.1f}u")
    say(f"  {lab:44s} {w + l:4d} bets {w / max(w + l, 1):6.1%} {u.sum():+7.1f}u ({u.sum() / max(w + l, 1) * 100:+5.1f}/100)  [{'; '.join(by)}]")
    return w, l, u

say("NBA totals, DraftKings, live totals number v4 (morning lock lag 1), both teams 10+ games, 2023-24..2025-26")
say(f"games with DK snapshots and a model number: {S.event_id.nunique()}; snapshots per game median {S.groupby('event_id').size().median():.0f}")
g0 = S.groupby("event_id").first()
say(f"opener edge 2.5+: {(g0.e0 >= 2.5).sum()} games, 3+: {(g0.e0 >= 3).sum()}")

say("\nBaseline: bet at DK's first total (1 unit at -110), edge at the open")
G0 = g0.reset_index()
for lo in (2.5, 3.0):
    line(G0[G0.e0 >= lo], f"edge {lo}+ at the open", at_open=True)

say("\nA. Line ~1 hour after the open (first snapshot 30-120 min after DK's first total); 3+ edge LEFT at that line")
A = S[(S.mins >= 30) & (S.mins <= 120)].groupby("event_id").first().reset_index()
A = A[A.left >= 3]
for lab, m in [("moved AGAINST 0.5+", A.mv <= -0.5), ("unmoved", A.mv.abs() < 0.5), ("moved toward 0.5-1.5", (A.mv >= 0.5) & (A.mv < 2)),
               ("moved toward 2-2.5", (A.mv >= 2) & (A.mv < 3)), ("moved toward 3+", A.mv >= 3), ("moved toward 4+", A.mv >= 4)]:
    line(A[m], lab)
say("  same games, graded at the OPENER instead (what betting right away would have paid):")
for lab, m in [("  moved toward 3+ -> at open", A.mv >= 3), ("  unmoved -> at open", A.mv.abs() < 0.5)]:
    line(A[m], lab, at_open=True)

say("\nB. Any time before tip: first snapshot where the line moved 3+ toward the model with 3+ still left")
B = S[(S.mv >= 3) & (S.left >= 3)].groupby("event_id").first().reset_index()
line(B, "moved 3+ toward, 3+ left (graded at that line)")
line(B, "  same games at the opener", at_open=True)
for lo, hi in [(3, 4), (4, 6), (6, 99)]:
    line(B[(B.left >= lo) & (B.left < hi)], f"  edge left {lo}-{hi if hi < 99 else '+'}")
say("  rest of the bettable pool for comparison: any time, line moved toward 0.5-2.5 with 3+ left (first such snapshot)")
Bs = S[(S.mv >= 0.5) & (S.mv < 3) & (S.left >= 3)]
Bs = Bs[~Bs.event_id.isin(B.event_id)].groupby("event_id").first().reset_index()
line(Bs, "moved toward 0.5-2.5, 3+ left, never 3+")

say("\nC. How fast did the 3+ move happen?")
for lab, m in [("within 30 min of the open", B.mins <= 30), ("30-60 min", (B.mins > 30) & (B.mins <= 60)),
               ("1-3 h", (B.mins > 60) & (B.mins <= 180)), ("3 h+", B.mins > 180)]:
    line(B[m], lab)

say("\nD. Leave-one-season-out: 'moved 3+ toward, 3+ left' (design B) vs bets at the opener with edge 3+")
for s in (2024, 2025, 2026):
    rb, ub = grade(B[B.season == s]); ro, uo = grade(G0[(G0.e0 >= 3) & (G0.season == s)], at_open=True)
    rest = B[B.season != s]; rr, ur = grade(rest)
    say(f"  {s}: fast-move group {int((rb > 0).sum())}-{int((rb < 0).sum())} {ub.sum():+.1f}u ({ub.mean() * 100:+.1f}/100)"
        f" | opener 3+ {int((ro > 0).sum())}-{int((ro < 0).sum())} {uo.mean() * 100:+.1f}/100"
        f" | other two seasons' fast-move win% {(rr > 0).sum() / max((rr != 0).sum(), 1):.1%}")

say("\nE. Kelly check (what the win rate supports, relative to a plain opener bet at -110)")
def kelly(p, dec_=1.909):
    b = dec_ - 1; return max((p * b - (1 - p)) / b, 0)
r, _ = grade(G0[G0.e0 >= 3], at_open=True); p0 = (r > 0).sum() / (r != 0).sum()
rb, _ = grade(B); pb = (rb > 0).sum() / (rb != 0).sum(); n = int((rb != 0).sum())
se = np.sqrt(pb * (1 - pb) / n)
say(f"  opener edge 3+: win {p0:.1%} -> Kelly {kelly(p0):.3f}")
say(f"  moved 3+ toward, 3+ left: win {pb:.1%} (SE {se:.1%}, n={n}) -> Kelly {kelly(pb):.3f}; ratio {kelly(pb) / max(kelly(p0), 1e-9):.2f}x")
say(f"  at the low end of its 1-SE range ({pb - se:.1%}) -> ratio {kelly(pb - se) / max(kelly(p0), 1e-9):.2f}x")
B.assign(design="B").to_csv(os.path.join(W, "analysis", "fast_move_units_bets.csv"), index=False)
open(os.path.join(W, "analysis", "fast_move_units_output.txt"), "w").write("\n".join(out) + "\n")
