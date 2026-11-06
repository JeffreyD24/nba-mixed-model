"""NFL spreads (test-only live rule): do "moved toward the model" bets lose? (Nov 6, 2026)

Pre-registered: betting-goals/models/tests/NFL_SPREAD_MOVED_TOWARD_PREREG.md (pushed 655f304 before grading).
DK spread snapshots 2020-25; number in force as in nfl-mixed-model/alert.py: pred_margin_early from Monday 10 AM ET of game week
(early_bet_from, copied) until the final injury report (build_injury_features.final_report_due), pred_margin after it.
Per game: first snapshot from Monday 10 AM to kickoff with 3+ edge; T = moved 0.5+ toward since DK's opener, U = unmoved,
A = moved 0.5+ against (PASS, reference). Graded at the snapshot line and DK price.
  python analysis/nfl_spread_moved_toward_test.py .   (run from nba-mixed-model; ../nfl-mixed-model next to it)
  -> analysis/nfl_spread_moved_toward_test_output.txt, analysis/nfl_spread_moved_toward_test_bets.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
NFL = os.path.join(os.path.dirname(W), "nfl-mixed-model")
sys.path.insert(0, W); sys.path.insert(0, NFL)
try:
    import derived; derived.ensure(W, ["dk_nfl_snaps_2020-08-01.csv.gz"])
except Exception:
    pass
import build_injury_features as bif  # noqa: E402
import ast  # noqa: E402
_src = open(os.path.join(W, "analysis", "move_cap_test.py")).read()       # team-name map, read without running that script
NFL_NAME = ast.literal_eval(next(n.value for n in ast.parse(_src).body
                                 if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "NFL_NAME"))
BOOT, SEED, THR = 10000, 20261106, 3.0
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

def early_bet_from(game_day):     # copied from nfl-mixed-model/alert.py (EARLY_BET_WEEKDAY = 0, EARLY_BET_HOUR = 10)
    d = pd.Timestamp(game_day).normalize()
    return d - pd.Timedelta(days=((d.dayofweek - 0) % 7) or 7) + pd.Timedelta(hours=10)

S = pd.read_csv(os.path.join(W, "_tmp", "dk_nfl_snaps_2020-08-01.csv.gz"))
S = S[S.market == "spreads"]
S["t"] = pd.to_datetime(S.snapshot_utc, utc=True)
S["tip"] = pd.to_datetime(S.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
S = S[S.t < S.tip]
h = S[S.outcome == S.home][["event_id", "t", "tip", "home", "away", "point", "price"]].rename(columns={"point": "hs", "price": "p_home"})
a = S[S.outcome == S.away][["event_id", "t", "point", "price"]].rename(columns={"point": "as_", "price": "p_away"})
S = h.merge(a, on=["event_id", "t"]); S = S[S.hs == -S.as_].drop(columns="as_").drop_duplicates(["event_id", "t"]).sort_values(["event_id", "t"])
S["home"] = S.home.map(NFL_NAME); S["away"] = S.away.map(NFL_NAME)
S["open_hs"] = S.groupby("event_id").hs.transform("first")
S["t_et"] = S.t.dt.tz_convert("America/New_York").dt.tz_localize(None)
S["d"] = S.tip.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()

Q = pd.concat([pd.read_csv(os.path.join(NFL, "backtests", f"predictions_{y}.csv")) for y in range(2020, 2026)], ignore_index=True)
Q = Q[["season", "week", "date", "home", "away", "pred_margin_early", "pred_margin", "home_pts", "away_pts"]].dropna(subset=["home_pts"])
Q["gd"] = pd.to_datetime(Q.date)
S = S.merge(Q, on=["home", "away"], how="inner")
S = S[(S.d - S.gd).abs() <= pd.Timedelta(days=1)].copy()
S["from_"] = [early_bet_from(g) for g in S.gd]
S["due"] = [bif.final_report_due(g) for g in S.gd]
S["after_report"] = S.t_et >= S.due
S["M"] = np.where(S.after_report, S.pred_margin, S.pred_margin_early)
S["mg"] = S.home_pts - S.away_pts
S["e"] = S.M + S.hs; S["side"] = np.sign(S.e)
S["mv"] = (S.open_hs - S.hs) * S.side

say("NFL spreads (test-only rule), DK snapshots 2020-25, early number Mon 10 AM -> final report, final number after; edge 3+")
say(f"games with snapshots + model numbers: {S.event_id.nunique()}; snapshots/game median {S.groupby('event_id').size().median():.0f}")
F = S[(S.t_et >= S.from_) & (S.e.abs() >= THR)].groupby("event_id").first().reset_index()
F["grp"] = np.where(F.mv >= 0.5, "T", np.where(F.mv <= -0.5, "A", "U"))
say(f"games with a 3+ edge snapshot from Monday 10 AM of game week: {len(F)}")

def dec(am):
    am = pd.Series(am).fillna(-110).values
    return np.where(am > 0, 1 + am / 100, 1 + 100 / -am)
def grade(X, at_open=False):
    line = X.open_hs if at_open else X.hs
    r = (X.side * (X.mg + line)).values
    d = dec(np.full(len(X), -110.0)) if at_open else dec(np.where(X.side > 0, X.p_home, X.p_away))
    return r, np.where(r > 0, d - 1, np.where(r < 0, -1.0, 0.0))
SEAS = list(range(2020, 2026))
def row(X, lab, at_open=False):
    if not len(X): say(f"  {lab:46s}    0 bets"); return np.array([])
    r, u = grade(X, at_open); w, l = int((r > 0).sum()), int((r < 0).sum())
    by = " ".join(f"{s % 100}:{u[(X.season == s).values].sum():+.1f}" for s in SEAS)
    say(f"  {lab:46s} {w + l:4d} bets {w / max(w + l, 1):6.1%} {u.sum():+7.1f}u ({u.mean() * 100:+5.1f}/100)  [{by}]")
    return u
say("\nFirst bettable snapshot, graded at that line and DK price")
uT = row(F[F.grp == "T"], "T moved toward 0.5+ (BET)")
row(F[(F.grp == "T") & (F.mv < 3)], "   T, move 0.5-2.5")
row(F[(F.grp == "T") & (F.mv >= 3)], "   T, move 3+")
row(F[(F.grp == "T") & ~F.after_report], "   T, before the final report (early number)")
row(F[(F.grp == "T") & F.after_report], "   T, after the final report")
row(F[F.grp == "T"], "   same T games at the opener (-110)", at_open=True)
row(F[F.grp == "U"], "U unmoved (BET)")
row(F[F.grp == "A"], "A moved against 0.5+ (PASS; reference)")
row(F[F.grp != "A"], "T + U (what the rule bets)")

rng = np.random.default_rng(SEED)
bt = np.array([rng.choice(uT, len(uT)).mean() for _ in range(BOOT)]) if len(uT) else np.array([np.nan])
roiT = uT.mean() if len(uT) else np.nan
say("\nPRIMARY TEST: ROI per bet of T")
say(f"  T {len(uT)} bets, ROI {roiT * 100:+.1f}/100; bootstrap 90% range {np.percentile(bt, 5) * 100:+.1f} to {np.percentile(bt, 95) * 100:+.1f}; "
    f"90th percentile {np.percentile(bt, 90) * 100:+.1f}")
v = "REJECTED" if roiT >= 0 else ("CONFIRMED" if len(uT) >= 50 and np.percentile(bt, 90) < 0 else "INCONCLUSIVE")
say(f"  VERDICT (pre-registered rule): {v}")
F.to_csv(os.path.join(W, "analysis", "nfl_spread_moved_toward_test_bets.csv"), index=False)
open(os.path.join(W, "analysis", "nfl_spread_moved_toward_test_output.txt"), "w").write("\n".join(out) + "\n")
