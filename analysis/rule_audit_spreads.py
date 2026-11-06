"""Rule audit part 3 (Nov 4, 2026): re-test the NBA spread rules with bettable timing.
The live spread number = Model 1 margin + 0.11 x (last-10 margin form, home minus away) + 0.57 x (roster strength delta, home minus
away), both teams 10+ games. Live rules: Oct-Jan only, no home underdogs; Feb-Apr only outside three traps (betting a tanking team,
betting against a playoff-spot 5-10 team, our team added a player in 30 days). Edge 3+.
The documented record (+42u, Oct-Jan 355 bets 58% + Feb-Apr 87 bets) graded the opener with the 8 PM night-before injury report and
results through the night before. Here: morning-lock lag 1 throughout, and
  S0 opener + 8 PM report        S1 opener + previous game's report (bettable when the opener posts)
  S2 ~9 PM line + 8 PM report    S3 ~9 AM game-day line + 8 PM report, with line-move groups.
Reads _tmp/rule_audit_R8.csv from analysis/rule_audit_injury_timing.py.
  python analysis/rule_audit_spreads.py WORKDIR -> analysis/rule_audit_spreads_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
R = pd.read_csv(os.path.join(W, "_tmp", "rule_audit_R8.csv"))
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
FORM_W, ROSTER_W = 0.11, 0.57

# ---- last-10 margin form vs season to date, games before the previous night (lag 1)
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
R["adj"] = FORM_W * R.fm.fillna(0) + ROSTER_W * (R.home_rd - R.away_rd).fillna(0)
ready = R.fm.notna() & (R.home_rg >= 10) & (R.away_rg >= 10)
R["m8"] = R.pred_margin + R.adj; R["ms"] = R.pm_stale + R.adj
R["mg"] = R.home_pts - R.away_pts

# ---- Feb-Apr traps (standings / arrivals before the game, from analysis/late_season.py)
G = pd.read_csv(os.path.join(W, "analysis", "late_season_games.csv"))[["date", "home", "away", "h_cat", "a_cat", "h_arr", "a_arr"]]
R = R.merge(G, on=["date", "home", "away"], how="left")
late = R.d.dt.month.isin([2, 3, 4])

out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

def live_ok(model, line):
    e = model + line; home = e > 0
    dog = home & (line > 0)
    us_cat = np.where(home, R.h_cat, R.a_cat); them_cat = np.where(home, R.a_cat, R.h_cat); us_arr = np.where(home, R.h_arr, R.a_arr)
    trap = (us_cat == "tanking") | (them_cat == "middle") | (pd.Series(us_arr).fillna(0).values > 0)
    # Nov 6, 2026 fix (RULE 11): the live alert (alert.py 862-873) excludes home underdogs in EVERY month, not only Oct-Jan.
    # Before this fix this audit let Feb-Apr home dogs through; numbers before the fix are in git history (commit 1ae29c3).
    return ready & ~dog & (~late | ~trap)

def g(model, line, mask, label):
    e = model + line; m = mask & (e.abs() >= 3) & line.notna() & model.notna()
    r = np.sign(e[m]) * (R.mg[m] + line[m]); w, l = int((r > 0).sum()), int((r < 0).sum())
    by = []
    for s in (2024, 2025, 2026):
        rs = r[R.season[m] == s]; by.append(f"{int((rs > 0).sum()) * 100 / 110 - int((rs < 0).sum()):+.1f}")
    say(f"  {label:<60} {w + l:5d} bets {w / max(w + l, 1):6.1%} {w * 100 / 110 - l:+7.1f}u ({(w * 100 / 110 - l) / max(w + l, 1) * 100:+5.1f}/100; {', '.join(by)})")

say("NBA live spread number at DraftKings 2023-24..2025-26, edge 3+, morning-lock lag 1, units at -110 (by season 24, 25, 26)")
say("\nS0 opener + 8 PM report (as documented)")
g(R.m8, R.open_spread, live_ok(R.m8, R.open_spread) & ~late, "Oct-Jan live rules")
g(R.m8, R.open_spread, live_ok(R.m8, R.open_spread) & late, "Feb-Apr outside traps")
g(R.m8, R.open_spread, live_ok(R.m8, R.open_spread), "all live-rule bets")
g(R.m8, R.open_spread, live_ok(R.m8, R.open_spread) & R.open_before_8pm, "  of which opener posted before 8 PM (not bettable)")
say("\nS1 opener + previous game's report (bettable as the opener posts)")
g(R.ms, R.open_spread, live_ok(R.ms, R.open_spread) & ~late, "Oct-Jan live rules")
g(R.ms, R.open_spread, live_ok(R.ms, R.open_spread) & late, "Feb-Apr outside traps")
g(R.ms, R.open_spread, live_ok(R.ms, R.open_spread), "all live-rule bets")
g(R.ms, R.open_spread, ready, "no month / home-dog / trap rules (both teams 10+)")
for col, lab in [("sp-3.0", "S2 ~9 PM night before"), ("sp0.0", "midnight"), ("sp9.0", "S3 ~9 AM game day"), ("sp12.0", "noon"), ("sp15.0", "3 PM")]:
    say(f"\n{lab}, 8 PM report, live rules")
    ln = R[col]; e = R.m8 + ln; mv = ln - R.open_spread        # home-perspective spread; move > 0 = line went toward the away side
    # toward the model: home bet (e>0) and the home spread got smaller (mv<0), or away bet and it got bigger
    tw = (mv.abs() >= 0.5) & (np.sign(mv) == -np.sign(e)); ag = (mv.abs() >= 0.5) & ~tw; un = mv.abs() < 0.5
    ok = live_ok(R.m8, ln)
    g(R.m8, ln, ok, "every 3+ edge")
    g(R.m8, ln, ok & ag, "moved AGAINST 0.5+")
    g(R.m8, ln, ok & un, "unmoved")
    g(R.m8, ln, ok & tw, "moved TOWARD 0.5+")
say("\nedge size at the opener, previous-game report, live rules")
e = R.ms + R.open_spread; ok = live_ok(R.ms, R.open_spread)
for lo, hi in [(2.0, 3.0), (3.0, 4.0), (4.0, 5.0), (5.0, 99)]:
    g(R.ms, R.open_spread, ok & (e.abs() >= lo) & (e.abs() < hi) | (ok & (e.abs() >= lo) & (e.abs() < hi) & False), f"edge {lo}-{hi if hi < 99 else '+'}") if lo >= 3 else None
m = ok & (e.abs() >= 2) & (e.abs() < 3); r = np.sign(e[m]) * (R.mg[m] + R.open_spread[m]); w, l = int((r > 0).sum()), int((r < 0).sum())
say(f"  edge 2-3 (below the bar)                                     {w + l:5d} bets {w / max(w + l, 1):6.1%} {w * 100 / 110 - l:+7.1f}u")
say("\nCLV, S1 live-rule opener bets: avg move toward the bet by the 3 PM line (pts)")
m = ok & (e.abs() >= 3) & R["sp15.0"].notna()
say(f"  {(np.sign(e[m]) * -(R['sp15.0'][m] - R.open_spread[m])).mean():+.2f} over {int(m.sum())} bets")
open(os.path.join(W, "analysis", "rule_audit_spreads_output.txt"), "w").write("\n".join(out) + "\n")
