"""NBA spreads: do the live rule's "moved toward the model" bets lose? (Nov 6, 2026)

Pre-registered: betting-goals/models/tests/NBA_SPREAD_MOVED_TOWARD_PREREG.md (pushed 6cbca4f before grading).
Live spread number as in analysis/rule_audit_spreads.py (Model 1 + 8 PM report, lag 1, + 0.11 form + 0.57 roster; live filters),
DraftKings spread snapshots 2023-24..2025-26. Per game: first snapshot from 8:55 PM ET the night before to tip with 3+ edge and the
live filters passed; T = moved 0.5+ toward the model since DK's opener, U = unmoved, A = moved 0.5+ against (PASS, reference).
  python analysis/rule_audit_injury_timing.py .   (builds _tmp/rule_audit_R8.csv; saved in derived/)
  python analysis/spread_moved_toward_test.py .   -> analysis/spread_moved_toward_test_output.txt, _bets.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
sys.path.insert(0, W)
try:
    import derived; derived.ensure(W, ["rule_audit_R8.csv", "dk_nba_snaps_2023-10-01.csv.gz"])
except Exception:
    pass
from analysis.odds_openers import NAME  # noqa: E402
BOOT, SEED, THR = 10000, 20261106, 3.0
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

# ---- live spread number per game (copied from rule_audit_spreads.py)
R = pd.read_csv(os.path.join(W, "_tmp", "rule_audit_R8.csv"))
R["date"] = pd.to_datetime(R.date).dt.strftime("%Y-%m-%d")
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
rows = []
for r in T.itertuples():
    rows += [dict(season=r.season, date=r.date, team=r.home, mg=r.home_pts - r.away_pts),
             dict(season=r.season, date=r.date, team=r.away, mg=r.away_pts - r.home_pts)]
L = pd.DataFrame(rows); L["d"] = pd.to_datetime(L.date)
hist = {k: g.sort_values("d") for k, g in L.groupby(["season", "team"])}
def form(season, team, d):
    g = hist.get((season, team)); g = g[g.d < d - pd.Timedelta(days=1)]
    return (g.mg.tail(10).mean() - g.mg.mean()) if len(g) >= 10 else np.nan
R["d"] = pd.to_datetime(R.date)
R["fm"] = [form(s, h, d) - form(s, a, d) for s, h, a, d in zip(R.season, R.home, R.away, R.d)]
RS = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))[["date", "team", "delta", "games"]]
for side in ("home", "away"):
    R = R.merge(RS.rename(columns={"team": side, "delta": f"{side}_rd", "games": f"{side}_rg"}), on=["date", side], how="left")
R["adj"] = 0.11 * R.fm.fillna(0) + 0.57 * (R.home_rd - R.away_rd).fillna(0)
R["ready"] = R.fm.notna() & (R.home_rg >= 10) & (R.away_rg >= 10)
R["m8"] = R.pred_margin + R.adj
R["mg"] = R.home_pts - R.away_pts
G = pd.read_csv(os.path.join(W, "analysis", "late_season_games.csv"))[["date", "home", "away", "h_cat", "a_cat", "h_arr", "a_arr"]]
R = R.merge(G, on=["date", "home", "away"], how="left")
R["late"] = R.d.dt.month.isin([2, 3, 4])
# the Nov 6 move-cap number (Model 1 + 8 PM report, from spread_autopsy_bets.csv) for the exploratory ladder
A = pd.read_csv(os.path.join(W, "analysis", "spread_autopsy_bets.csv"))[["date", "home", "away", "pred_margin"]]
A["date"] = pd.to_datetime(A.date).dt.strftime("%Y-%m-%d")
R = R.merge(A.rename(columns={"pred_margin": "m_auto"}).drop_duplicates(["date", "home", "away"]), on=["date", "home", "away"], how="left")
keep = ["season", "date", "home", "away", "mg", "m8", "m_auto", "pred_margin", "ready", "late", "h_cat", "a_cat", "h_arr", "a_arr"]

# ---- DK spread snapshots
S = pd.read_csv(os.path.join(W, "_tmp", "dk_nba_snaps_2023-10-01.csv.gz"))
S = S[S.market == "spreads"]
S["t"] = pd.to_datetime(S.snapshot_utc, utc=True)
S["tip"] = pd.to_datetime(S.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
S = S[S.t < S.tip]
h = S[S.outcome == S.home][["event_id", "t", "tip", "home", "away", "point", "price"]].rename(columns={"point": "hs", "price": "p_home"})
a = S[S.outcome == S.away][["event_id", "t", "point", "price"]].rename(columns={"point": "as_", "price": "p_away"})
S = h.merge(a, on=["event_id", "t"]); S = S[S.hs == -S.as_].drop(columns="as_").drop_duplicates(["event_id", "t"]).sort_values(["event_id", "t"])
S["home"] = S.home.map(NAME); S["away"] = S.away.map(NAME)
S["date"] = S.tip.dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
S["open_hs"] = S.groupby("event_id").hs.transform("first")
S["t_et"] = S.t.dt.tz_convert("America/New_York").dt.tz_localize(None)
S["win_start"] = pd.to_datetime(S.date) - pd.Timedelta(hours=3, minutes=5)     # 8:55 PM ET the night before
S = S.merge(R[keep], on=["date", "home", "away"], how="inner")

def dec(am):
    am = pd.Series(am).fillna(-110).values
    return np.where(am > 0, 1 + am / 100, 1 + 100 / -am)
def state(X, model):
    """edge (home view: model margin + home spread), side, move toward the model (pts), filters at this line"""
    e = model + X.hs; side = np.sign(e)
    mv = (X.open_hs - X.hs) * side                    # home spread falling = market moving toward home
    home = e > 0; dog = home & (X.hs > 0)
    us_cat = np.where(home, X.h_cat, X.a_cat); them_cat = np.where(home, X.a_cat, X.h_cat); us_arr = np.where(home, X.h_arr, X.a_arr)
    trap = (us_cat == "tanking") | (them_cat == "middle") | (pd.Series(us_arr).fillna(0).values > 0)
    # Nov 6, 2026 fix (RULE 11): home underdogs are excluded in every month, as in alert.py 862-873. The pre-registered run
    # (commit 1ae29c3) used Oct-Jan only; both are reported in betting-goals models/tests/NBA_SPREAD_MOVED_TOWARD_RESULTS.md.
    ok = X.ready & ~dog & (~X.late | ~trap)
    return e, side, mv, ok
def grade(X, side, at_open=False):
    line = X.open_hs if at_open else X.hs
    r = side * (X.mg + line)
    d = dec(np.full(len(X), -110.0)) if at_open else dec(np.where(side > 0, X.p_home, X.p_away))
    return r.values, np.where(r > 0, d - 1, np.where(r < 0, -1.0, 0.0))
def row(X, lab, at_open=False):
    if not len(X): say(f"  {lab:46s}    0 bets"); return np.array([])
    r, u = grade(X, X.side, at_open); w, l = int((r > 0).sum()), int((r < 0).sum())
    by = "; ".join(f"{s}: {int((r[(X.season == s).values] > 0).sum())}-{int((r[(X.season == s).values] < 0).sum())} {u[(X.season == s).values].sum():+.1f}u"
                   for s in (2024, 2025, 2026))
    say(f"  {lab:46s} {w + l:4d} bets {w / max(w + l, 1):6.1%} {u.sum():+7.1f}u ({u.mean() * 100:+5.1f}/100)  [{by}]")
    return u

say("NBA spreads, live spread number (Model 1 + 8 PM report + form + roster, lag 1), live filters, DK snapshots 2023-24..2025-26")
say(f"games with snapshots + live number: {S.event_id.nunique()}; snapshots/game median {S.groupby('event_id').size().median():.0f}")
X = S.copy(); X["e"], X["side"], X["mv"], X["ok"] = state(X, X.m8)
F = X[(X.t_et >= X.win_start) & (X.e.abs() >= THR) & X.ok].groupby("event_id").first().reset_index()
F["grp"] = np.where(F.mv >= 0.5, "T", np.where(F.mv <= -0.5, "A", "U"))
say(f"games with a bettable 3+ edge snapshot after 8:55 PM the night before: {len(F)}")
say("\nFirst bettable snapshot, graded at that line and DK price")
uT = row(F[F.grp == "T"], "T moved toward 0.5+ (BET)")
row(F[(F.grp == "T") & (F.mv < 3)], "   T, move 0.5-2.5")
row(F[(F.grp == "T") & (F.mv >= 3)], "   T, move 3+")
row(F[F.grp == "T"], "   same T games at the opener (-110)", at_open=True)
row(F[F.grp == "U"], "U unmoved (BET)")
row(F[F.grp == "A"], "A moved against 0.5+ (PASS; reference)")

rng = np.random.default_rng(SEED)
bt = np.array([rng.choice(uT, len(uT)).mean() for _ in range(BOOT)]) if len(uT) else np.array([np.nan])
roiT = uT.mean() if len(uT) else np.nan
say("\nPRIMARY TEST: ROI per bet of T")
say(f"  T {len(uT)} bets, ROI {roiT * 100:+.1f}/100; bootstrap 90% range {np.percentile(bt, 5) * 100:+.1f} to {np.percentile(bt, 95) * 100:+.1f}; "
    f"90th percentile {np.percentile(bt, 90) * 100:+.1f}")
if roiT >= 0: v = "REJECTED"
elif len(uT) >= 50 and np.percentile(bt, 90) < 0: v = "CONFIRMED"
else: v = "INCONCLUSIVE"
say(f"  VERDICT (pre-registered rule): {v}")

# ---- exploratory: which live ingredient separates this from the Nov 6 move-cap number (labeled)
say("\nEXPLORATORY (not pre-registered): first snapshot moved 0.5-2.5 toward with 3+ left, adding live ingredients one at a time")
def ladder(model, filters, window, lab):
    Y = S[S[model].notna()].copy(); Y["e"], Y["side"], Y["mv"], Y["ok"] = state(Y, Y[model])
    Y["left"] = Y.e.abs()
    m = (Y.mv >= 0.5) & (Y.left >= THR)
    if filters: m &= Y.ok
    if window: m &= Y.t_et >= Y.win_start
    Z = Y[m]
    big = Y[(Y.mv >= 3) & (Y.left >= THR) & (Y.ok if filters else True) & ((Y.t_et >= Y.win_start) if window else True)].event_id.unique()
    Z = Z[(Z.mv < 3) & ~Z.event_id.isin(big)].groupby("event_id").first().reset_index()
    row(Z, lab)
ladder("m_auto", False, False, "(1) move-cap number, no filters, any time")
ladder("m_auto", True, False, "(2) + live filters")
ladder("m8", True, False, "(3) + form and roster (live number)")
ladder("m8", True, True, "(4) + after 8:55 PM night before only")
ladder("m8", False, False, "(3b) live number, no filters, any time")

F.to_csv(os.path.join(W, "analysis", "spread_moved_toward_test_bets.csv"), index=False)
open(os.path.join(W, "analysis", "spread_moved_toward_test_output.txt"), "w").write("\n".join(out) + "\n")
