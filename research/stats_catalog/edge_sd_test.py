"""Follow-up to catalog B84/B87: does ranking NBA totals bets by edge / expected noise beat raw edge?
Rule fixed BEFORE looking at results (Nov 4, 2026):
  noise(line) = a + b * opener, fit by least squares of |final - opener| on the opener, on SBR 2011-12..2018-19 only.
  z-edge = edge / noise(opener).
  Test 1 (2023-26, v4 at DraftKings openers): bet the same NUMBER of games as the live rule (|edge| >= 3) but chosen by largest |z-edge|.
          Compare win %, units, CLV with the live rule. Also logistic AIC: over ~ edge vs over ~ z-edge.
  Test 2 (2013-14..2021-22, Model 1 at SBR openers, research/old_seasons_sbr_bets.csv, totals with |edge| >= 3):
          within those bets, does the top half by |z-edge| win more than the top half by |edge|? And logistic AIC as above.
  Verdict: "better" only if z-edge wins on BOTH tests (more units in test 1, lower AIC in both). Otherwise keep raw edge.
  python research/stats_catalog/edge_sd_test.py   (from the repo root; needs research/stats_catalog/nba_totals_games.csv)"""
import os, sys, numpy as np, pandas as pd, statsmodels.formula.api as smf
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "analysis"))
src = open(os.path.join(REPO, "analysis", "old_seasons_sbr.py")).read()
ns = {}; exec(src[src.index("NICK = "):src.index("REG_END")], ns); NICK = ns["NICK"]
out = []
def say(s): out.append(s); print(s)
S = pd.read_csv(os.path.join(REPO, "data/external/sbr/sbr_nba_2011_2021_clean.csv.gz"))
S = S[(S.total_trusted == 1) & (S.open_ok == 1)].copy(); S["date"] = pd.to_datetime(S.date)
S["act"] = S.home_final + S.away_final; S = S[(S.open_over_under > 150) & (S.act > 120)]
S["home"] = S.home_team.map(NICK); S["away"] = S.away_team.map(NICK); S["season_end"] = S.season + 1
fit = S[S.season_end.between(2012, 2019)]
nf = smf.ols("ae ~ open_over_under", fit.assign(ae=(fit.act - fit.open_over_under).abs())).fit()
a, b = nf.params.Intercept, nf.params.open_over_under
noise = lambda line: a + b * line
say(f"Noise model (SBR 2011-19, {len(fit)} games): mean |miss| = {a:.2f} + {b:.4f} x opener (slope p={nf.pvalues.open_over_under:.2g}); "
    f"at 200: {noise(200):.1f}, 220: {noise(220):.1f}, 240: {noise(240):.1f}")

# ---- test 1: v4, DraftKings openers 2023-26
A = pd.read_csv(os.path.join(HERE, "nba_totals_games.csv"))
A["e"] = A.v4 - A.open_total; A["z"] = A.e / noise(A.open_total); A["r"] = np.sign(A.e) * A.y
def grade(D):
    D = D[D.r != 0]; u = np.where(D.r > 0, 100 / 110, -1.0)
    return len(D), (D.r > 0).mean(), u.sum(), (np.sign(D.e) * D.move).mean()
k = int((A.e.abs() >= 3).sum())
live = A[A.e.abs() >= 3]; zsel = A.loc[A.z.abs().sort_values(ascending=False).index[:k]]
for lab, D in (("live rule |edge|>=3", live), (f"top {k} by |z-edge|", zsel)):
    n, wr, u, clv = grade(D); say(f"  2023-26 {lab:22s} {n} bets {wr:.1%} {u:+.1f}u CLV {clv:+.2f}")
only_z = zsel[~zsel.index.isin(live.index)]; only_e = live[~live.index.isin(zsel.index)]
for lab, D in (("bets only z-edge makes", only_z), ("bets only raw edge makes", only_e)):
    n, wr, u, clv = grade(D); say(f"  2023-26 {lab:22s} {n} bets {wr:.1%} {u:+.1f}u CLV {clv:+.2f}")
L = A[A.y != 0].assign(ov=lambda d: (d.y > 0).astype(int))
m_e = smf.logit("ov ~ e", L).fit(disp=0); m_z = smf.logit("ov ~ z", L).fit(disp=0)
say(f"  2023-26 logistic AIC: raw edge {m_e.aic:.2f}, z-edge {m_z.aic:.2f} (lower is better; difference {m_z.aic - m_e.aic:+.2f})")
t1 = grade(zsel)[2] > grade(live)[2]; t1b = m_z.aic < m_e.aic

# ---- test 2: Model 1 at SBR openers, older seasons
O = pd.read_csv(os.path.join(REPO, "analysis", "old_seasons_sbr_bets.csv")); O = O[(O.market == "total") & (O.trusted == 1)].copy()
O["date"] = pd.to_datetime(O.date)
O = O.merge(S[["date", "home", "away", "open_over_under"]], on=["date", "home", "away"], how="left").dropna(subset=["open_over_under"])
O = O[O.result != 0]; O["z"] = O.edge / noise(O.open_over_under); O["win"] = (O.result > 0).astype(int)
say(f"\nOlder seasons (Model 1 at SBR openers, totals, |edge|>=3): {len(O)} bets with an opener matched, win {O.win.mean():.1%}")
half = len(O) // 2
te = O.loc[O.edge.abs().sort_values(ascending=False).index[:half]]; tz = O.loc[O.z.abs().sort_values(ascending=False).index[:half]]
say(f"  top half by |edge|: {te.win.mean():.1%}; top half by |z-edge|: {tz.win.mean():.1%} ({half} bets each, {len(set(te.index) & set(tz.index))} shared)")
O["sabs_e"] = O.edge.abs(); O["sabs_z"] = O.z.abs()
l_e = smf.logit("win ~ sabs_e", O).fit(disp=0); l_z = smf.logit("win ~ sabs_z", O).fit(disp=0)
say(f"  logistic win ~ size: AIC |edge| {l_e.aic:.2f} (slope p={l_e.pvalues.sabs_e:.2f}), |z-edge| {l_z.aic:.2f} (p={l_z.pvalues.sabs_z:.2f})")
by = O.groupby("season").apply(lambda g: (g.loc[g.z.abs().sort_values(ascending=False).index[:len(g)//2]].win.mean() - g.loc[g.edge.abs().sort_values(ascending=False).index[:len(g)//2]].win.mean()))
say("  z-half minus edge-half win % by season: " + ", ".join(f"{s}: {v:+.1%}" for s, v in by.items()))
t2 = l_z.aic < l_e.aic
say(f"\nVerdict (rule set in advance): test 1 units {'z' if t1 else 'raw'}, test 1 AIC {'z' if t1b else 'raw'}, test 2 AIC {'z' if t2 else 'raw'} -> "
    + ("z-edge is better: worth a pre-registered live test." if (t1 and t1b and t2) else "keep raw edge."))
open(os.path.join(HERE, "edge_sd_output.txt"), "w").write("\n".join(out) + "\n")
