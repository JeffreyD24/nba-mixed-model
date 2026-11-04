"""Spread opener timing (Nov 4, 2026): bet at the opener vs wait for the 8 PM report, by opener edge size. Needs _tmp/rule_audit_R8.csv
from analysis/rule_audit_injury_timing.py.  python analysis/spread_opener_timing.py WORKDIR -> research/spreads/SPREAD_OPENER_TIMING_2026-11-04.md"""
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
    return ready & ((~late & ~dog) | (late & ~trap))

def g(model, line, mask, label):
    e = model + line; m = mask & (e.abs() >= 3) & line.notna() & model.notna()
    r = np.sign(e[m]) * (R.mg[m] + line[m]); w, l = int((r > 0).sum()), int((r < 0).sum())
    by = []
    for s in (2024, 2025, 2026):
        rs = r[R.season[m] == s]; by.append(f"{int((rs > 0).sum()) * 100 / 110 - int((rs < 0).sum()):+.1f}")
    say(f"  {label:<60} {w + l:5d} bets {w / max(w + l, 1):6.1%} {w * 100 / 110 - l:+7.1f}u ({(w * 100 / 110 - l) / max(w + l, 1) * 100:+5.1f}/100; {', '.join(by)})")


def rec(r):
    w,l=int((r>0).sum()),int((r<0).sum()); return f"{w+l:4d} {w/max(w+l,1):6.1%} {w*100/110-l:+7.1f}u"
def res(model,line,m): e=model+line; return np.sign(e[m])*(R.mg[m]+line[m])
eo=R.ms+R.open_spread                       # opener edge with previous report
base=live_ok(R.ms,R.open_spread)&R.open_spread.notna()&R.ms.notna()
ln=R["sp-3.0"]; e9=R.m8+ln; mv=ln-R.open_spread
tw=(mv.abs()>=0.5)&(np.sign(mv)==-np.sign(e9)); ag=(mv.abs()>=0.5)&~tw
for lo,hi in [(3,4),(4,5),(5,99),(3,99)]:
    m=base&(eo.abs()>=lo)&(eo.abs()<hi)
    print(f"\nopener edge {lo}-{hi} (prev report), live rules")
    print("  A bet at opener               ",rec(res(R.ms,R.open_spread,m)))
    # wait: same games, 9PM line + 8PM report, still 3+ same side, not moved against
    w9=m&ln.notna()&(e9.abs()>=3)&(np.sign(e9)==np.sign(eo))&~ag&live_ok(R.m8,ln)
    print("  B wait: 9PM, still 3+, not against",rec(res(R.m8,ln,w9)), f"(kept {w9.sum()}/{m.sum()})")
    keep=m&(np.sign(R.m8+R.open_spread)==np.sign(eo))&((R.m8+R.open_spread).abs()>=3)
    print("  C opener, 8PM report keeps 3+ ",rec(res(R.ms,R.open_spread,keep)))
    print("  D opener, 8PM drops/flips     ",rec(res(R.ms,R.open_spread,m&~keep)))
    for s in (2024,2025,2026):
        ms_=m&(R.season==s); print(f"     season {s}: opener",rec(res(R.ms,R.open_spread,ms_)))
# combined policy: opener if 5+, else wait
m5=base&(eo.abs()>=5); mw=live_ok(R.m8,ln)&ln.notna()&(e9.abs()>=3)&~ag&~m5.fillna(False)
print("\nPOLICY 5+ at opener, rest wait to 9PM:",rec(pd.concat([res(R.ms,R.open_spread,m5),res(R.m8,ln,mw)])))
mw_all=live_ok(R.m8,ln)&ln.notna()&(e9.abs()>=3)&~ag
print("CURRENT (wait to 9PM, PASS if against):",rec(res(R.m8,ln,mw_all)))
for s in (2024,2025,2026):
    q=R.season==s
    print(s,"policy",rec(pd.concat([res(R.ms,R.open_spread,m5&q),res(R.m8,ln,mw&q)])),"| current",rec(res(R.m8,ln,mw_all&q)))
