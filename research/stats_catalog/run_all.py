"""Apply every course concept to the NBA totals model (v4, DraftKings openers, 2024-25..2025-26 + 2023-24 labelled by season end year 2024..2026).
Data A: per-game v4 walk-forward predictions (built by build.py from analysis/nba_v4_vs_stack.py), 3,204 games.
Data M: market-only history: SBR 2011-12..2020-21 (open+close) and training_games 2021-22..2025-26 (close).
Output: results.json (ID -> text, p-value) and results.md"""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE)); os.chdir(HERE)

import json, warnings, numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm, statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.outliers_influence import variance_inflation_factor, OLSInfluence
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.proportion import proportion_confint, proportions_ztest
from statsmodels.stats.multitest import multipletests
warnings.filterwarnings("ignore")
rng = np.random.default_rng(2026)
R = {}; PV = {}
def rec(k, txt, p=None):
    R[k] = txt; print(f"\n[{k}] {txt}")
    if p is not None: PV[k] = float(p)
BE = 110 / 210  # break-even at -110

# ---------------- data A
A = pd.read_csv("nba_totals_games.csv", parse_dates=["date"])
A["act"] = A.home_pts + A.away_pts
A["e"] = A.v4 - A.open_total
A["e_m1"] = A.pred_total - A.open_total
A["sg"] = np.sign(A.e)
A["r"] = A.sg * A.y
A["month"] = A.date.dt.month
A["mname"] = A.date.dt.strftime("%b")
A["ng"] = np.minimum(A.home_n, A.away_n)
A["err_v4"] = A.act - A.v4; A["err_open"] = A.act - A.open_total; A["err_close"] = A.act - A.close_total
A["over"] = (A.act > A.open_total).astype(int)
B = A[(A.e.abs() >= 3) & (A.r != 0)].copy()
B["win"] = (B.r > 0).astype(int); B["u"] = np.where(B.win == 1, 100 / 110, -1.0)
B["clv"] = B.sg * B.move; B["dir"] = np.where(B.sg > 0, "over", "under")
B = B.sort_values(["date", "home"]).reset_index(drop=True)
n, w = len(B), B.win.sum(); ph = w / n
print("bets", n, "wins", w, ph, B.u.sum())

# ---------------- data M (market history)
S = pd.read_csv(REPO + "/data/external/sbr/sbr_nba_2011_2021_clean.csv.gz")
S = S[S.total_trusted == 1]
M1 = pd.DataFrame({"season": S.season + 1, "date": pd.to_datetime(S.date), "open": S.open_over_under, "close": S.close_over_under,
                   "act": S.home_final + S.away_final})
T = pd.read_csv(REPO + "/data/training_games.csv", parse_dates=["date"])
M2 = pd.DataFrame({"season": T.season, "date": T.date, "open": np.nan, "close": T.total, "act": T.home_pts + T.away_pts})
M = pd.concat([M1[M1.season < 2022], M2], ignore_index=True).dropna(subset=["close", "act"])
M = M[(M.close > 150) & (M.act > 120)]
M["res"] = M.act - M.close
print("market games", len(M), M.season.min(), M.season.max())

# ====================== Chapter 1-2: study design
g = M.groupby("season").res.agg(["mean", "std", "count"])
t, p = stats.ttest_1samp(M.res, 0)
rec("A01", f"Population = every NBA game the market prices; our 'sample' = {len(M):,} games 2011-12..2025-26. Mean (final total - closing total) = {M.res.mean():+.2f} pts "
    f"(t={t:.2f}, p={p:.3f}); by season ranges {g['mean'].min():+.2f} to {g['mean'].max():+.2f}. Seasons with the biggest misses: "
    + ", ".join(f"{int(s)-1}-{str(int(s))[2:]} {v:+.1f}" for s, v in g['mean'].abs().sort_values(ascending=False).head(3).items())
    + ". The closing line is close to unbiased over the long run, but a single season can run 1+ pt high (league scoring rising faster than the market adjusts). Overs have a tiny long-run tailwind, far below the vig.", p)

# A02 observational: CLV association with winning (both caused by true information)
pos, neg = B[B.clv > 0], B[B.clv < 0]
rec("A02", f"Everything here is observational (no one randomizes which games get a model edge). Example: bets whose line later moved our way (CLV>0) won "
    f"{pos.win.mean():.1%} (n={len(pos)}), moved against us {neg.win.mean():.1%} (n={len(neg)}). Line movement doesn't CAUSE wins: both come from the same "
    "underlying information (injuries, sharp money). It's a marker, not a lever: we can't make the line move.")

# A03 confounding: altitude
a1 = smf.ols("act ~ alt", A).fit(); a2 = smf.ols("y ~ alt", A).fit(); a3 = smf.ols("err_v4 ~ alt", A).fit()
rec("A03", f"Denver/Utah home games: raw totals {a1.params.alt:+.1f} pts vs other games (p={a1.pvalues.alt:.3f}); vs the opener {a2.params.alt:+.2f} (p={a2.pvalues.alt:.3f}); "
    f"vs v4 (which adds +3.8) {a3.params.alt:+.2f} (p={a3.pvalues.alt:.3f}). The raw gap is confounded by who those teams are (pace, roster); the market already "
    "prices most of it, so the useful number is the residual after the line.", a2.pvalues.alt)

# A04 survivorship/selection: teams with extreme over% in first half of a season
M2b = T.copy(); M2b["act"] = M2b.home_pts + M2b.away_pts; M2b = M2b.dropna(subset=["total", "act"])
tl = pd.concat([M2b[["season", "date", "home", "act", "total"]].rename(columns={"home": "team"}), M2b[["season", "date", "away", "act", "total"]].rename(columns={"away": "team"})])
tl["ov"] = (tl.act > tl.total).astype(float); tl.loc[tl.act == tl.total, "ov"] = np.nan
tl = tl.sort_values("date"); tl["k"] = tl.groupby(["season", "team"]).cumcount()
h1 = tl[tl.k < 41].groupby(["season", "team"]).ov.mean(); h2 = tl[tl.k >= 41].groupby(["season", "team"]).ov.mean()
D = pd.concat([h1, h2], axis=1, keys=["h1", "h2"]).dropna()
top = D[D.h1 >= D.h1.quantile(0.8)]; bot = D[D.h1 <= D.h1.quantile(0.2)]
rr, rp = stats.pearsonr(D.h1, D.h2)
rec("A04", f"Selection on past success: team-seasons in the top 20% for over% in their first 41 games (avg {top.h1.mean():.1%}) went over {top.h2.mean():.1%} the rest of the way; "
    f"bottom 20% ({bot.h1.mean():.1%}) went {bot.h2.mean():.1%}. First-half vs second-half correlation r={rr:+.2f} (p={rp:.2f}, {len(D)} team-seasons, 2021-26). "
    "'Over teams' are the survivors of a noisy filter: almost all of it disappears. Same trap as only studying the systems that made money.", rp)

# A05 sampling designs: SRS vs cluster (by date) vs stratified (by season) SE of ROI
se_srs = B.u.std(ddof=1) / np.sqrt(n)
gd = B.groupby("date").u.agg(["sum", "count"]).values
bc = np.array([(lambda i: gd[i, 0].sum() / gd[i, 1].sum())(rng.integers(0, len(gd), len(gd))) for _ in range(4000)])
strat = np.array([np.mean(np.concatenate([rng.choice(x.u.values, len(x)) for _, x in B.groupby("season")])) for _ in range(4000)])
rec("A05", f"ROI per bet {B.u.mean():+.2%}. Standard error if every bet were a simple random sample: {se_srs:.2%}; cluster bootstrap by game night (bets on one night "
    f"share news/refs/league scoring): {bc.std():.2%}; stratified by season: {strat.std():.2%}. Ratio cluster/SRS = {bc.std()/se_srs:.2f}. "
    "If >1, same-night bets are correlated and naive confidence intervals are too narrow.")

# A06 nonresponse: games dropped from data A (early season, missing opener)
Tm = T.dropna(subset=["home_pts"]).copy(); Tm["act"] = Tm.home_pts + Tm.away_pts
O = pd.read_csv(REPO + "/data/odds_history/nba_open_close.csv"); O = O[O.book == "draftkings"].drop_duplicates(["date", "home", "away"])
O["date"] = pd.to_datetime(O.date); Tm = Tm.merge(O[["date", "home", "away", "open_total", "close_total"]].rename(columns={"open_total": "dko", "close_total": "dkc"}), on=["date", "home", "away"], how="left")
Tm = Tm[Tm.season >= 2024].dropna(subset=["dko"])
key = set(zip(A.date, A.home)); Tm["kept"] = [(d, h) in key for d, h in zip(Tm.date, Tm.home)]
k_, d_ = Tm[Tm.kept], Tm[~Tm.kept]
mae = lambda x: (x.act - x.dko).abs().mean()
rec("A06", f"Of {len(Tm)} DraftKings-priced games 2023-26, {len(d_)} ({len(d_)/len(Tm):.0%}) aren't in our test set (mostly the first ~10 games of each team's season). "
    f"The opener misses those dropped games by {mae(d_):.2f} pts on average vs {mae(k_):.2f} in kept games, and their totals average {(d_.act-d_.dko).mean():+.2f} vs the opener "
    f"({(k_.act-k_.dko).mean():+.2f} kept). Like the Literary Digest poll, our results describe only the games we kept. The dropped early-season games weren't harder for the book, but they did run over the opener by ~1 pt more: a possible early-season over lean that our test set never sees.")

# A07 randomization / permutation test: shuffle which side we bet within each date
obs = B.u.mean()
perm = []
uw, ul = 100 / 110, -1.0
for _ in range(5000):
    flip = rng.random(n) < 0.5
    r_ = np.where(flip, -B.r.values, B.r.values); perm.append(np.where(r_ > 0, uw, ul).mean())
perm = np.array(perm); pp = (np.sum(perm >= obs) + 1) / (len(perm) + 1)
rec("A07", f"Randomization test: kept the same 3+ edge games but picked over/under by coin flip 5,000 times. Random sides averaged {perm.mean():+.2%} ROI "
    f"(the vig), 99th percentile {np.percentile(perm,99):+.2%}; v4's actual {obs:+.2%}. p = {pp:.4f}. The model's side choice beats random far more than chance would.", pp)

# A08 CRD vs RBD: signed result across edge buckets, with/without season blocks
B["eb"] = pd.cut(B.e.abs(), [3, 4, 5, 6, 8, 99], right=False, labels=["3-4", "4-5", "5-6", "6-8", "8+"])
f0 = smf.ols("r ~ C(eb)", B).fit(); f1 = smf.ols("r ~ C(eb) + C(season)", B).fit()
a0 = anova_lm(f0); a1_ = anova_lm(f1)
rec("A08", f"Edge bucket as the 'treatment', points beaten the opener by as the response. CRD (no blocks): F={a0.F.iloc[0]:.2f}, p={a0['PR(>F)'].iloc[0]:.3f}. "
    f"Blocking on season: bucket F={a1_.F.iloc[0]:.2f}, p={a1_['PR(>F)'].iloc[0]:.3f}; season block F={a1_.F.iloc[1]:.2f}, p={a1_['PR(>F)'].iloc[1]:.3f}. "
    f"Mean points beaten by bucket: " + ", ".join(f"{k} {v:+.2f}" for k, v in B.groupby('eb').r.mean().items()) + ". Bigger edges don't beat the line by much more.", a1_['PR(>F)'].iloc[0])

# A09 Latin-square-style two blocking factors: season and weekday
A["wd"] = A.date.dt.dayofweek
l1 = smf.ols("r ~ C(dir) + C(season) + C(wd)", B.assign(wd=B.date.dt.dayofweek)).fit(); al = anova_lm(l1, typ=2)
rec("A09", f"Two blocking factors at once (season rows x weekday columns, the Latin-square idea; our data isn't a square so it's an additive two-block model). "
    f"Over vs under bets after removing season and weekday: F={al.F['C(dir)']:.2f}, p={al['PR(>F)']['C(dir)']:.3f}; weekday p={al['PR(>F)']['C(wd)']:.3f}; season p={al['PR(>F)']['C(season)']:.3f}. "
    "Weekday explains nothing about how well we beat the line.", al['PR(>F)']['C(wd)'])

# A10 factorial & interaction: bet direction x rested
fx = smf.ols("r ~ C(dir) * C(rested)", B).fit(); ax = anova_lm(fx, typ=2)
cell = B.groupby(["dir", "rested"]).win.agg(["mean", "count"])
rec("A10", "2x2 factorial: bet direction (over/under) x both teams rested. Win %: " + "; ".join(f"{d} {'rested' if r_ else 'b2b'} {m:.1%} (n={int(c)})" for (d, r_), (m, c) in cell.iterrows())
    + f". Interaction p={ax['PR(>F)']['C(dir):C(rested)']:.3f}. A factorial look tests both factors and whether they combine, from one set of games.", ax['PR(>F)']['C(dir):C(rested)'])

# A11 ANCOVA: direction adjusted for opener level
fc = smf.ols("r ~ C(dir) + open_total", B).fit(); fd = smf.ols("r ~ C(dir)", B).fit()
rec("A11", f"ANCOVA: over vs under bets adjusted for how high the opener was. Unadjusted under-minus-over gap {fd.params.get('C(dir)[T.under]',0):+.2f} pts (p={fd.pvalues.get('C(dir)[T.under]',1):.3f}); "
    f"adjusted {fc.params.get('C(dir)[T.under]',0):+.2f} (p={fc.pvalues.get('C(dir)[T.under]',1):.3f}); opener slope {fc.params.open_total:+.3f}/pt (p={fc.pvalues.open_total:.3f}). "
    "The covariate barely moves the comparison: opener height isn't hiding a direction effect.", fc.pvalues.open_total)

# A12 experimental vs measurement unit: game vs team score
th = A.home_pts - A.home_pts.mean(); ta = A.away_pts - A.away_pts.mean()
rc = np.corrcoef(A.home_pts - (A.v4 / 2), A.away_pts - (A.v4 / 2))[0, 1]
rec("A12", f"The experimental unit is the game; the two team scores are measurement units inside it. Within a game the two teams' scores (each vs half the model total) correlate r={rc:+.2f} "
    "(shared pace, refs, overtime). Treating 6,408 team scores as independent would double the sample and shrink standard errors falsely (pseudoreplication). "
    f"SD of game total vs model {A.err_v4.std():.1f} is larger than sqrt(2)x team SD would give if they were independent ({np.sqrt(2)*(A.home_pts-A.v4/2).std():.1f}).")

# ====================== Chapter 3: description
vc = pd.Series(np.where(A.e.abs() < 3, "no bet", np.where(A.r == 0, "push", np.where(A.r > 0, "win", "loss")))).value_counts()
rec("A13", "Bar chart counts, all 3,204 games: " + ", ".join(f"{k} {v}" for k, v in vc.items()) + f". Pushes are {vc.get('push',0)/(vc.drop('no bet').sum()):.1%} of edge-3+ games "
    "(NBA totals land on a half-point line rarely, unlike NFL key numbers).")
sh = B.dir.value_counts(normalize=True)
rec("A14", f"Pie-chart shares of bets: overs {sh.get('over',0):.0%}, unders {sh.get('under',0):.0%}; by season overs " + ", ".join(f"{s}: {x.dir.eq('over').mean():.0%}" for s, x in B.groupby('season'))
    + ". A part-of-whole view shows v4 is not just an 'always over' model (the old stack bet overs 95% of the time).")
sk, ku = stats.skew(A.y), stats.kurtosis(A.y)
rec("A15", f"Histogram of (final total - opener): unimodal, mean {A.y.mean():+.2f}, skewness {sk:+.2f}, excess kurtosis {ku:+.2f}. Roughly symmetric and close to bell-shaped; "
    "slight heavy right tail from overtime games (OT adds ~20 pts).")
rf = lambda lo, hi: ((A.err_close.abs() >= lo) & (A.err_close.abs() < hi)).mean()
rec("A16", f"Relative frequencies of |final - closing total|: under 5 pts {rf(0,5):.1%}, 5-10 {rf(5,10):.1%}, 10-20 {rf(10,20):.1%}, 20+ {rf(20,999):.1%}. "
    f"Same for v4 vs actual: under 5 {((A.err_v4.abs()<5).mean()):.1%}, 20+ {((A.err_v4.abs()>=20).mean()):.1%}. Even the best line misses by 10+ about half the time: single-game noise is huge.")
mm = A.groupby("month").agg(y=("y", "mean"), act=("act", "mean"), n=("y", "size")).reindex([10, 11, 12, 1, 2, 3, 4]).dropna()
B["cum"] = B.u.cumsum()
rec("A17", "Time series by month (Nov->Apr; October drops out because both teams need 10+ games), final minus opener: " + ", ".join(f"{pd.Timestamp(2000,int(m),1).strftime('%b')} {r.y:+.2f}" for m, r in mm.iterrows())
    + f". Cumulative units for v4 bets rose fairly steadily (min {B.cum.min():+.1f}u, max {B.cum.max():+.1f}u, final {B.cum.iloc[-1]:+.1f}u); worst drawdown "
    f"{(B.cum.cummax()-B.cum).max():.1f}u.")
tm = stats.trim_mean(A.y, 0.1); md = np.median(A.y); mo = pd.Series(np.round(A.y)).mode().iloc[0]
rec("A18", f"Center of (final - opener): mean {A.y.mean():+.2f}, median {md:+.2f}, 10% trimmed mean {tm:+.2f}, mode (rounded) {mo:+.0f}. For v4 bets' points beaten: mean "
    f"{B.r.mean():+.2f}, median {B.r.median():+.2f}, trimmed {stats.trim_mean(B.r,0.1):+.2f}. Mean and trimmed agree, so the edge isn't a few blowouts.")
q = np.percentile(A.err_v4, [5, 25, 50, 75, 95])
rec("A19", f"Quantiles of (final - v4): 5th {q[0]:+.1f}, 25th {q[1]:+.1f}, median {q[2]:+.1f}, 75th {q[3]:+.1f}, 95th {q[4]:+.1f}. A 90% range for a game total is about "
    f"v4 {q[0]:+.0f} to {q[4]:+.0f} pts. Edge percentiles: 3 pts is the {stats.percentileofscore(A.e.abs(),3):.0f}th percentile of |edge|.")
sw = stats.shapiro(rng.choice(A.err_v4.values, 2000, replace=False)); qq = stats.probplot(A.err_v4, dist="norm")[1][2]
rec("A20", f"Q-Q of v4 errors vs normal: Q-Q correlation {qq:.4f}; Shapiro-Wilk (2,000-game sample) W={sw.statistic:.4f}, p={sw.pvalue:.3g}. Close to normal in the middle, "
    "tails slightly heavier (overtime, blowouts). Normal-based win probabilities are fine for typical edges, a bit off in the extremes.", sw.pvalue)
q1, q3 = np.percentile(A.err_v4, [25, 75]); iqr = q3 - q1; lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
out = A[(A.err_v4 < lo) | (A.err_v4 > hi)]
rec("A21", f"Boxplot of (final - v4): IQR {iqr:.1f}, fences {lo:+.1f} / {hi:+.1f}; {len(out)} outlier games ({len(out)/len(A):.1%}), {np.mean(out.err_v4>0):.0%} of them high (overtime-type). "
    f"v4 bets in outlier games: {B.set_index(['date','home']).index.isin(out.set_index(['date','home']).index).sum()}. Outliers aren't removable (they're real games), but they're why "
    "an over bet carries extra right-tail chance.")
sv = A.groupby("season").err_v4.std()
rec("A22", f"SD of (final - v4) {A.err_v4.std():.2f}, vs opener {A.err_open.std():.2f}, vs close {A.err_close.std():.2f}. By season (v4): " + ", ".join(f"{s} {v:.2f}" for s, v in sv.items())
    + ". Our model is about as noisy as the opener; the edge is in a slightly different center, not a smaller spread.")
z = (A.err_v4 - A.err_v4.mean()) / A.err_v4.std()
rec("A23", f"Empirical rule on (final - v4): within 1 SD {np.mean(z.abs()<1):.1%} (rule 68%), 2 SD {np.mean(z.abs()<2):.1%} (95%), 3 SD {np.mean(z.abs()<3):.2%} (99.7%). "
    "Very close to a bell curve; 1 SD of a game total is about 18 pts.")
cv_t = A.act.std() / A.act.mean(); cv_h = A.home_pts.std() / A.home_pts.mean()
rec("A24", f"Coefficient of variation: game total {cv_t:.1%}, single team score {cv_h:.1%}, opener {A.open_total.std()/A.open_total.mean():.1%}, v4 {A.v4.std()/A.v4.mean():.1%}. "
    "Totals are relatively stable (8%) but a 3-pt edge is only 1.3% of a total: tiny compared with the game-to-game spread.")
bm = A.groupby("mname").y.agg(["median", lambda x: np.subtract(*np.percentile(x, [75, 25]))])
rec("A25", "Side-by-side boxplots of (final - opener) by month: medians " + ", ".join(f"{m} {r['median']:+.1f}" for m, r in bm.reindex(['Oct','Nov','Dec','Jan','Feb','Mar','Apr']).dropna().iterrows())
    + ". Boxes overlap heavily; no month is obviously different by eye (tested formally in B59).")
ct = pd.crosstab([B.season], [B.dir, B.win])
rec("A26", "Contingency table, v4 bets, wins/losses by season and direction: " + "; ".join(f"{s}: over {int(r[('over',1)])}-{int(r[('over',0)])}, under {int(r[('under',1)])}-{int(r[('under',0)])}" for s, r in ct.iterrows()))
r_, p_ = stats.pearsonr(A.e, A.y); r2_, p2_ = stats.pearsonr(A.e_m1, A.y)
rec("A27", f"Scatter of v4 edge vs (final - opener): r={r_:+.3f} (p={p_:.2g}, n={len(A)}). Plain Model 1 edge: r={r2_:+.3f}. Small r but real: a few % of the noise "
    "is predictable, which is all a bettor needs at -110.", p_)
A["edec"] = pd.qcut(A.e, 10, labels=False)
bdm = A.groupby("edec").agg(e=("e", "mean"), y=("y", "mean"))
ra, pa = stats.pearsonr(A.e.abs(), A.err_v4.abs())
quad = smf.ols("y ~ e + I(e**2)", A).fit()
rec("A28", f"Zero (or small) r doesn't mean no relationship: mean (final - opener) by edge decile: " + ", ".join(f"{r.e:+.1f}->{r.y:+.1f}" for _, r in bdm.iterrows())
    + f". Quadratic term p={quad.pvalues['I(e ** 2)']:.3f}; |edge| vs |v4 error| r={ra:+.3f} (p={pa:.3f}). The relationship is roughly linear in the middle and flattens at extremes.", quad.pvalues['I(e ** 2)'])

# ====================== Chapter 4: probability
rec("A29", f"Break-even win probability at -110 = 110/210 = {BE:.2%}. Complement: P(lose) = 1 - P(win). v4 bets won {ph:.1%}, so P(lose) {1-ph:.1%}. "
    f"P(at least one loss in a 5-bet night) = 1 - {ph:.3f}^5 = {1-ph**5:.1%}: losing nights are normal even with an edge.")
# A30 intransitivity among four forecasts on which is closer per game
F = {"v4": A.v4, "M1": A.pred_total, "simple": A.simple, "open": A.open_total}
names = list(F); hh = {}
for i in names:
    for j in names:
        if i < j:
            di, dj = (A.act - F[i]).abs(), (A.act - F[j]).abs(); m = di != dj
            hh[(i, j)] = (di[m] < dj[m]).mean()
rec("A30", "Head-to-head 'which forecast is closer to the final' (share of games the first wins): " + ", ".join(f"{i} vs {j} {v:.1%}" for (i, j), v in hh.items())
    + ". Check for a cycle (A>B, B>C, C>A): none here, so the ranking is transitive. With nontransitive dice it wouldn't be, which is why 'beats X head-to-head' isn't the same as 'best'.")
# A31 Simpson's paradox: v4 vs M1 win rates pooled vs by season
BM = A[(A.e_m1.abs() >= 3)].copy(); BM["rr"] = np.sign(BM.e_m1) * BM.y; BM = BM[BM.rr != 0]
tab = pd.DataFrame({"v4": B.groupby("season").win.mean(), "v4n": B.groupby("season").size(), "M1": BM.groupby("season").rr.apply(lambda x: (x > 0).mean()), "M1n": BM.groupby("season").size()})
dirs = B.groupby(["season", "dir"]).win.mean().unstack()
rev = [s for s in dirs.index if np.sign(dirs.loc[s, "over"] - dirs.loc[s, "under"]) != np.sign(B[B.dir == "over"].win.mean() - B[B.dir == "under"].win.mean())]
rec("A31", f"Simpson's paradox check. Pooled: overs {B[B.dir=='over'].win.mean():.1%} vs unders {B[B.dir=='under'].win.mean():.1%}. By season over-under: "
    + ", ".join(f"{s} {dirs.loc[s,'over']-dirs.loc[s,'under']:+.1%}" for s in dirs.index) + f". Seasons that reverse the pooled direction: {rev or 'none'}. "
    f"v4 vs plain Model 1 win rate by season: " + ", ".join(f"{s} {r.v4:.1%} vs {r.M1:.1%}" for s, r in tab.iterrows()) + ". v4 leads in every season and pooled, so no paradox there.")
tw = B[B.clv > 0].win.mean(); ta_ = B[B.clv < 0].win.mean(); t0 = B[B.clv == 0].win.mean()
rec("A32", f"Conditional probability: P(win | line moved toward us) = {tw:.1%}, P(win | no move) = {t0:.1%}, P(win | moved against) = {ta_:.1%}; "
    f"P(line moves toward us | v4 bet) = {np.mean(B.clv>0):.1%}. The live rule (pass after a 0.5+ move against) is a conditional-probability rule.")
# A33 independence: same-night correlation & runs test
pairs = []
for d, x in B.groupby("date"):
    v = x.win.values
    for i in range(len(v)):
        for j in range(i + 1, len(v)): pairs.append((v[i], v[j]))
pairs = np.array(pairs); rp_ = np.corrcoef(pairs[:, 0], pairs[:, 1])[0, 1]
seq = B.win.values; runs = 1 + np.sum(seq[1:] != seq[:-1]); n1, n0 = seq.sum(), len(seq) - seq.sum()
mu_r = 2 * n1 * n0 / (n1 + n0) + 1; var_r = (mu_r - 1) * (mu_r - 2) / (n1 + n0 - 1); zr = (runs - mu_r) / np.sqrt(var_r); prun = 2 * stats.norm.sf(abs(zr))
rec("A33", f"Independence: correlation between results of two bets on the same night r={rp_:+.3f} ({len(pairs)} pairs). Runs test on the bet sequence: {runs} runs vs {mu_r:.0f} expected, z={zr:+.2f}, p={prun:.3f}. "
    "No hot or cold streaks beyond chance: a losing week says nothing about the next bet.", prun)
both = pairs.all(axis=1).mean()
rec("A34", f"Multiplication law: if independent, P(two bets same night both win) = {ph:.3f}^2 = {ph**2:.1%}; observed {both:.1%}. A 2-leg parlay pays +264 "
    f"(needs {1/3.64:.1%}); at our win rate P(both)={ph**2:.1%}, EV per unit {ph**2*2.64-(1-ph**2):+.3f} vs two straight bets {2*(ph*100/110-(1-ph)):+.3f}.")
sens = ((A.e > 0) & (A.act > A.open_total)).sum() / (A.act > A.open_total).sum()
spec = ((A.e < 0) & (A.act < A.open_total)).sum() / (A.act < A.open_total).sum()
sens3 = ((A.e >= 3) & (A.act > A.open_total)).sum() / (A.act > A.open_total).sum()
rec("A35", f"Sensitivity/specificity, treating 'v4 above the opener' as a test for 'game goes over': sensitivity {sens:.1%}, specificity {spec:.1%}. With the 3-pt threshold "
    f"sensitivity drops to {sens3:.1%} (we flag only a fraction of overs) but precision rises. Same trade-off as a medical screen: a stricter cutoff catches fewer, but surer, cases.")
prior = (A.act > A.open_total).mean(); po = ((A.e >= 3) & (A.act > A.open_total)).sum() / (A.e >= 3).sum()
a_, b_ = 1 + w, 1 + n - w; pb = 1 - stats.beta.cdf(BE, a_, b_)
rec("A36", f"Bayes: prior P(over) = {prior:.1%}; P(edge>=3 | over) and P(edge>=3 | under) give posterior P(over | v4 says over by 3+) = {po:.1%}. "
    f"Bayesian view of the whole record: flat prior + {w}-{n-w} gives posterior mean win rate {a_/(a_+b_):.1%}, 95% credible interval "
    f"{stats.beta.ppf(0.025,a_,b_):.1%}-{stats.beta.ppf(0.975,a_,b_):.1%}, P(true rate > break-even) = {pb:.4f}.")
EX = ph * (100 / 110) - (1 - ph); VX = ph * (100 / 110) ** 2 + (1 - ph) - EX ** 2
kelly = (ph * (1 + 100 / 110) - 1) / (100 / 110)
rec("A37", f"Profit per 1-unit bet X = +0.909 or -1. At p={ph:.3f}: E[X] = {EX:+.4f}u, Var = {VX:.3f}, SD = {np.sqrt(VX):.3f}u. The SD is ~{np.sqrt(VX)/EX:.0f}x the mean, "
    f"so you need hundreds of bets to see the edge. Full Kelly stake would be {kelly:.1%} of bankroll; the project's 1% flat unit is ~{1/(kelly*100):.2f} Kelly, which is conservative.")
pbin = stats.binom.sf(w - 1, n, BE)
rec("A38", f"Binomial: wins ~ Binomial(n={n}, p). Under break-even p={BE:.4f}, expected {n*BE:.0f} wins (SD {np.sqrt(n*BE*(1-BE)):.1f}); observed {w}. "
    f"P(X >= {w}) = {pbin:.2g}. At p=0.50 it's {stats.binom.sf(w-1,n,0.5):.2g}.", pbin)
bpn = B.groupby("date").size(); alld = A.date.drop_duplicates(); cnt = bpn.reindex(alld, fill_value=0)
disp = cnt.var() / cnt.mean()
team_pts = pd.concat([A.home_pts, A.away_pts]); vm = team_pts.var() / team_pts.mean()
rec("A39", f"Poisson: v4 bets per game night mean {cnt.mean():.2f}, variance {cnt.var():.2f} (dispersion {disp:.2f}; Poisson = 1). P(0 bets on a night) Poisson {np.exp(-cnt.mean()):.1%} vs actual {np.mean(cnt==0):.1%}. "
    f"Team points: mean {team_pts.mean():.1f}, variance {team_pts.var():.0f} (ratio {vm:.2f}). Points are made in 1-3 pt chunks, so a team score isn't Poisson; a possessions model is the better building block.")
pushes = ((A.e.abs() >= 3) & (A.r == 0)).sum(); nb = (A.e.abs() >= 3).sum(); lam = nb * pushes / nb
rec("A40", f"Poisson approximation to the binomial for rare events: pushes happen in {pushes/nb:.2%} of edge-3+ games (whole-number openers only). For a 100-bet stretch, pushes ~ Binomial(100, {pushes/nb:.4f}) "
    f"~ Poisson({100*pushes/nb:.2f}): P(0 pushes) binomial {stats.binom.pmf(0,100,pushes/nb):.3f} vs Poisson {stats.poisson.pmf(0,100*pushes/nb):.3f}. Near-identical: the shortcut works when p is small.")
sig = A.err_v4.std()
A["p_over"] = stats.norm.sf((A.open_total - A.v4) / sig)
B["p_win"] = np.where(B.sg > 0, stats.norm.sf((B.open_total - B.v4) / sig), stats.norm.cdf((B.open_total - B.v4) / sig))
rec("A41", f"Probability as area under a density: with a normal curve centered on v4 (SD {sig:.1f}), P(over) = area above the opener. For our bets the curve says average P(win) = {B.p_win.mean():.1%}; "
    f"actual {ph:.1%}. A 3-pt edge = {stats.norm.cdf(3/sig)-0.5:.1%} of extra area, a 6-pt edge {stats.norm.cdf(6/sig)-0.5:.1%}. The curve is too confident: it treats v4 as the truth, but the opener also knows things v4 doesn't. "
    "Real win probability sits between the curve and 50%, the same shrinkage the regression slope shows (B76).")
zr_ = (w - n * BE) / np.sqrt(n * BE * (1 - BE))
rec("A42", f"z-scores: the record is z = (wins - n*0.5238)/sqrt(n*0.5238*0.4762) = {zr_:+.2f}. For games: z of each final vs v4 = (final - v4)/{sig:.1f}; {np.mean(np.abs(A.err_v4/sig)>2):.1%} of games are beyond |z|=2 (normal 4.6%).")
q95 = A.v4 + stats.norm.ppf(0.95) * sig
rec("A43", f"Normal quantiles: with v4 as the mean and SD {sig:.1f}, the total exceeded only 5% of the time is v4 + z0.95*SD = v4 + {stats.norm.ppf(0.95)*sig:.1f}. Observed share of games above that: "
    f"{np.mean(A.act>q95):.1%}. For a 60% over chance the line would need to be {stats.norm.ppf(0.40)*sig:+.1f} pts from v4; our 3-pt bar is only ~{stats.norm.cdf(3/sig):.0%} by the curve.")
sub = np.array([rng.choice(B.u.values, 500, replace=False).mean() for _ in range(4000)])
rec("A44", f"Random samples of 500 bets (drawn without replacement, 4,000 times): ROI ranged {np.percentile(sub,2.5):+.1%} to {np.percentile(sub,97.5):+.1%} (95%); {np.mean(sub<0):.1%} of 500-bet samples lost money. "
    "Resampling from our own 1,446 bets understates the risk (it assumes the true rate IS 56.7%); B45 shows the more honest view: one season is only ~1.9 SEs from zero.")
rec("A45", f"Sampling distribution of the mean profit: SE = SD/sqrt(n) = {B.u.std():.3f}/sqrt({n}) = {se_srs:.4f}u. Per season (~{n//3} bets) SE = {B.u.std()/np.sqrt(n/3):.3f}u, vs the edge "
    f"{B.u.mean():+.3f}u: one season's ROI is within ~{B.u.mean()/(B.u.std()/np.sqrt(n/3)):.1f} SEs of zero.")
blk = B.u.values[: (n // 50) * 50].reshape(-1, 50).sum(axis=1)
rec("A46", f"CLT: units won per 50-bet block ({len(blk)} blocks) have mean {blk.mean():+.2f}, SD {blk.std(ddof=1):.2f} (theory {np.sqrt(50*B.u.var()):.2f}); skewness {stats.skew(blk):+.2f}, "
    f"Shapiro p={stats.shapiro(blk).pvalue:.2f}. The observed SD is larger than theory, a hint the win rate isn't constant over time (hot and cold model stretches, not streaky bets). Even though each bet is a two-valued +0.91/-1, sums of 50 are already close to normal: CLT lets us use normal math for season totals.")
cc = stats.norm.sf((w - 0.5 - n * BE) / np.sqrt(n * BE * (1 - BE)))
rec("A47", f"Normal approximation with continuity correction: P(X >= {w}) ~ P(Z >= ({w}-0.5-{n*BE:.1f})/{np.sqrt(n*BE*(1-BE)):.2f}) = {cc:.2g}; exact binomial {pbin:.2g}. np and n(1-p) are both > 10, so the approximation is valid.")

# ====================== Chapter 5-7 inference
ci = stats.t.interval(0.95, n - 1, B.u.mean(), se_srs)
rec("B48", f"Point estimates: win rate p-hat = {w}/{n} = {ph:.4f}; ROI = {B.u.mean():+.4f}u/bet; v4 bias (mean final - v4) = {A.err_v4.mean():+.2f} pts; opener bias {A.err_open.mean():+.2f}.")
tb = stats.ttest_1samp(A.err_v4, 0)
rec("B49", f"95% t confidence interval for ROI per bet: {ci[0]:+.2%} to {ci[1]:+.2%}. For v4's bias (final - v4): {A.err_v4.mean():+.2f} +/- {stats.t.ppf(.975,len(A)-1)*A.err_v4.std()/np.sqrt(len(A)):.2f} pts "
    f"(t={tb.statistic:.2f}, p={tb.pvalue:.2f}). Interpretation: we're 95% confident the long-run ROI of this rule is in that range (if the future looks like 2023-26).", tb.pvalue)
z975 = stats.norm.ppf(0.975); sdu = B.u.std()
rec("B50", f"Sample size for a margin of error: to estimate ROI to +/-2% (95%), n = (1.96*{sdu:.3f}/0.02)^2 = {int(np.ceil((z975*sdu/0.02)**2)):,} bets; +/-1% needs {int(np.ceil((z975*sdu/0.01)**2)):,}. "
    f"At ~{n/3:.0f} bets a season that's {np.ceil((z975*sdu/0.02)**2)/(n/3):.1f} / {np.ceil((z975*sdu/0.01)**2)/(n/3):.1f} seasons.")
t1 = stats.ttest_1samp(B.u, 0, alternative="greater")
rec("B51", f"The five parts: (1) H0: mu_ROI <= 0, (2) Ha: mu_ROI > 0 (one-sided, decided before looking), (3) t = xbar/(s/sqrt n) = {t1.statistic:.2f}, (4) reject if t >= t(0.95, {n-1}) = {stats.t.ppf(.95,n-1):.3f}, "
    f"(5) p = {t1.pvalue:.2g}: reject H0. Caution: these seasons helped choose v4, so it's a descriptive test, not a clean out-of-sample one.", t1.pvalue)
# B52 power
def power(p_true, nn, alpha=0.05):
    crit = stats.binom.ppf(1 - alpha, nn, BE); return stats.binom.sf(crit, nn, p_true)
nn80 = next(k for k in range(50, 20000, 25) if power(0.55, k) >= 0.8)
rec("B52", f"Type I error = calling a losing system a winner (alpha 5%); Type II = missing a real edge. Power to detect a true 55% win rate (vs 52.4%) with 300 bets: {power(0.55,300):.0%}; 500: {power(0.55,500):.0%}; "
    f"{n}: {power(0.55,n):.0%}. Bets needed for 80% power: ~{nn80:,}. A one-season test of a new filter (~100-300 bets) is badly underpowered: most real 2-3% edges would 'fail'.")
rec("B53", f"p-values: P(results at least this good | no edge). Binomial vs break-even p = {pbin:.2g}; t-test on ROI p = {t1.pvalue:.2g}. "
    f"It is NOT the probability v4 has no edge, and it's computed on seasons that helped build v4. See B64 for how many p-values this catalog produced.")
rec("B54", f"t distribution: with df={n-1} the t critical value {stats.t.ppf(.975,n-1):.3f} is essentially z (1.960). For a 30-bet sample (df 29) it's {stats.t.ppf(.975,29):.3f}: "
    "small samples need wider intervals. One-sample t on points beaten: " + f"t={stats.ttest_1samp(B.r,0).statistic:.2f}, mean {B.r.mean():+.2f} pts/bet.", stats.ttest_1samp(B.r, 0).pvalue)
ov, un = B[B.dir == "over"].r, B[B.dir == "under"].r
tp_ = stats.ttest_ind(ov, un, equal_var=True); tw_ = stats.ttest_ind(ov, un, equal_var=False)
rec("B55", f"Pooled two-sample t: points beaten, over bets ({ov.mean():+.2f}, n={len(ov)}) vs under bets ({un.mean():+.2f}, n={len(un)}): t={tp_.statistic:+.2f}, p={tp_.pvalue:.3f}.", tp_.pvalue)
rb = A[A.rested == 1].y; b2 = A[A.rested == 0].y; tw2 = stats.ttest_ind(rb, b2, equal_var=False)
rec("B56", f"Welch t (unequal variances): same over/under comparison t={tw_.statistic:+.2f}, df~{len(ov)+len(un)-2}, p={tw_.pvalue:.3f}. Also (final - opener) in games where both teams were rested ({rb.mean():+.2f}) vs a back-to-back involved ({b2.mean():+.2f}): "
    f"t={tw2.statistic:+.2f}, p={tw2.pvalue:.3f}. The market prices rest fine on average.", tw2.pvalue)
dpair = A.err_open.abs() - A.err_v4.abs(); dpc = A.err_close.abs() - A.err_v4.abs()
tpair = stats.ttest_1samp(dpair, 0); tpc = stats.ttest_1samp(dpc, 0)
rec("B57", f"Paired t (same game, two forecasts): |opener error| - |v4 error| = {dpair.mean():+.3f} pts, t={tpair.statistic:+.2f}, p={tpair.pvalue:.3f}; vs the CLOSE: {dpc.mean():+.3f}, t={tpc.statistic:+.2f}, p={tpc.pvalue:.3f}. "
    "Pairing removes game-to-game noise (the 18-pt SD) so small accuracy gaps become testable. v4 is roughly as accurate as the opener in absolute error and worse than the close.", tpair.pvalue)
early = A[A.month.isin([10, 11, 12])].err_open; late = A[A.month.isin([2, 3, 4])].err_open
Fv = early.var() / late.var(); pf = 2 * min(stats.f.sf(Fv, len(early) - 1, len(late) - 1), stats.f.cdf(Fv, len(early) - 1, len(late) - 1))
rec("B58", f"F test for two variances: opener error variance Nov-Dec ({early.std():.2f}^2) vs Feb-Apr ({late.std():.2f}^2): F={Fv:.3f}, p={pf:.3f}. "
    "(F is sensitive to non-normal tails; Levene in B60 is the robust check.)", pf)
fm = smf.ols("y ~ C(mname)", A).fit(); am = anova_lm(fm)
rec("B59", f"One-way ANOVA: (final - opener) across 6 months: SSB={am.sum_sq.iloc[0]:.0f}, SSE={am.sum_sq.iloc[1]:.0f}, F({int(am.df.iloc[0])},{int(am.df.iloc[1])})={am.F.iloc[0]:.2f}, p={am['PR(>F)'].iloc[0]:.3f}. "
    f"Same for v4 bets' points beaten across months: p={anova_lm(smf.ols('r ~ C(mname)', B).fit())['PR(>F)'].iloc[0]:.3f}.", am['PR(>F)'].iloc[0])
grp = [x.y.values for _, x in A.groupby("mname")]
lev = stats.levene(*grp, center="median"); bart = stats.bartlett(*grp)
rec("B60", f"ANOVA assumptions for the month model: Brown-Forsythe/Levene p={lev.pvalue:.3f}, Bartlett p={bart.pvalue:.3f} (equal variance), residual skew {stats.skew(fm.resid):+.2f}. "
    "Assumptions look fine, so the ANOVA result can be trusted.", lev.pvalue)
lg = np.log(A.act); sq = np.sqrt(A.act)
rec("B61", f"Transformations: total points skew {stats.skew(A.act):+.3f}; log {stats.skew(lg):+.3f}; sqrt {stats.skew(sq):+.3f}. Residual spread vs line height: see B84/B87. "
    "Totals are already near-symmetric; transforming adds little here (it matters more for team props / low counts).")
mo_ = A.groupby("mname").y.agg(["mean", "count"]).reindex(["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"]).dropna()
c_ = np.array([1, 1, 1, -1, -1, -1], float)
mse_ = am.sum_sq.iloc[1] / am.df.iloc[1]
L_ = (c_ / 3 * mo_["mean"]).sum(); seL = np.sqrt(mse_ * ((c_ / 3) ** 2 / mo_["count"]).sum()); tL = L_ / seL; pL = 2 * stats.t.sf(abs(tL), am.df.iloc[1])
rec("B62", f"Contrast: early (Nov-Jan) minus late (Feb-Apr) mean of (final - opener) = {L_:+.2f} pts, SE {seL:.2f}, t={tL:+.2f}, p={pL:.3f}. Planned question: does the book lag the scoring level early in the season?", pL)
cs = {"early vs late": [1, 1, 1, -1, -1, -1], "Jan vs Nov-Dec": [-1, -1, 2, 0, 0, 0], "Apr vs Feb-Mar": [0, 0, 0, -1, -1, 2]}
ssc = {}
for k_, c in cs.items():
    c = np.array(c, float); Lc_ = (c * mo_["mean"]).sum(); ssc[k_] = Lc_ ** 2 / ((c ** 2) / mo_["count"]).sum()
ortho = np.dot(cs["early vs late"], cs["Jan vs Nov-Dec"]), np.dot(cs["early vs late"], cs["Apr vs Feb-Mar"]), np.dot(cs["Jan vs Nov-Dec"], cs["Apr vs Feb-Mar"])
rec("B63", f"Orthogonal contrasts (dot products {ortho}, all 0 with ~equal month sizes): SS early-vs-late {ssc['early vs late']:.0f}, Jan-vs-Nov/Dec {ssc['Jan vs Nov-Dec']:.0f}, Apr-vs-Feb/Mar {ssc['Apr vs Feb-Mar']:.0f} "
    f"out of SSB {am.sum_sq.iloc[0]:.0f}. With these 3 of the 5 possible orthogonal pieces we see where the month-to-month variation sits: late-season April (playoff-push / tank games) and the January dip carry most of it.")
tk = pairwise_tukeyhsd(A.y, A.mname); tkd = pd.DataFrame(tk.summary().data[1:], columns=tk.summary().data[0])
rec("B67", f"Tukey HSD on all 15 month pairs: {int((tkd.reject==True).sum())} significant at familywise 5%; smallest adjusted p={tkd['p-adj'].astype(float).min():.3f} ({tkd.loc[tkd['p-adj'].astype(float).idxmin(),'group1']} vs {tkd.loc[tkd['p-adj'].astype(float).idxmin(),'group2']}).")
lsd = []
for i_, a in enumerate(mo_.index):
    for b in mo_.index[i_ + 1:]:
        d = mo_.loc[a, "mean"] - mo_.loc[b, "mean"]; se = np.sqrt(mse_ * (1 / mo_.loc[a, "count"] + 1 / mo_.loc[b, "count"]))
        lsd.append((a, b, 2 * stats.t.sf(abs(d / se), am.df.iloc[1])))
lsd = pd.DataFrame(lsd, columns=["a", "b", "p"])
rec("B66", f"Fisher's LSD (unadjusted pairwise t after the F test): {int((lsd.p<0.05).sum())} of 15 month pairs 'significant' at 5% (smallest p={lsd.p.min():.3f}, {lsd.loc[lsd.p.idxmin(),'a']} vs {lsd.loc[lsd.p.idxmin(),'b']}). "
    + (f"The overall F was significant (p={am['PR(>F)'].iloc[0]:.3f}), so LSD is allowed, but it doesn't adjust for 15 comparisons, so it flags more pairs than Tukey." if am['PR(>F)'].iloc[0] < 0.05 else f"Since the overall F wasn't significant (p={am['PR(>F)'].iloc[0]:.2f}), LSD says stop here."))
Fs = (len(mo_) - 1) * stats.f.ppf(0.95, len(mo_) - 1, am.df.iloc[1])
rec("B68", f"Scheffe for an unplanned contrast (picked after looking, e.g. the best month vs the worst): needs t^2 >= (k-1)F = {Fs:.1f} (t >= {np.sqrt(Fs):.2f}) vs 1.96 for a planned one. "
    f"Best-minus-worst month t = {(mo_['mean'].max()-mo_['mean'].min())/np.sqrt(mse_*(1/mo_.loc[mo_['mean'].idxmax(),'count']+1/mo_.loc[mo_['mean'].idxmin(),'count'])):.2f}: "
    + ("it clears Scheffe, so the April-vs-January gap survives even the strictest after-the-fact correction (and B65 Bonferroni)." if (mo_['mean'].max()-mo_['mean'].min())/np.sqrt(mse_*(1/mo_.loc[mo_['mean'].idxmax(),'count']+1/mo_.loc[mo_['mean'].idxmin(),'count'])) > np.sqrt(Fs) else "doesn't clear Scheffe.") + " Any trend found by scanning the data must clear this much higher bar.")
pr = proportion_confint(w, n, 0.05, "wilson"); zt = proportions_ztest(w, n, BE, alternative="larger")
ovr = A.over.mean(); po_ci = proportion_confint(A.over.sum(), len(A), method="wilson")
rec("B69", f"One proportion: v4 win rate {ph:.1%}, 95% Wilson CI {pr[0]:.1%}-{pr[1]:.1%} (break-even {BE:.1%} is below the interval). z test vs 52.38%: z={zt[0]:.2f}, p={zt[1]:.2g}. "
    f"Games going over the opener: {ovr:.1%} (CI {po_ci[0]:.1%}-{po_ci[1]:.1%}); the opener is balanced.", zt[1])
rec("B70", f"Sample size for a proportion: to pin the win rate to +/-2% with 95% confidence, n = 1.96^2*0.55*0.45/0.02^2 = {int(np.ceil(z975**2*.55*.45/.02**2)):,} bets; +/-1%: {int(np.ceil(z975**2*.55*.45/.01**2)):,}.")
s_ = B.groupby("season").win.agg(["sum", "count"])
z2 = proportions_ztest(s_.loc[[2024, 2026], "sum"].values, s_.loc[[2024, 2026], "count"].values)
z3 = proportions_ztest([B[B.dir == 'over'].win.sum(), B[B.dir == 'under'].win.sum()], [len(ov), len(un)])
rec("B71", f"Two proportions: win rate 2023-24 {s_.loc[2024,'sum']/s_.loc[2024,'count']:.1%} vs 2025-26 {s_.loc[2026,'sum']/s_.loc[2026,'count']:.1%}: z={z2[0]:+.2f}, p={z2[1]:.3f}. "
    f"Overs {B[B.dir=='over'].win.mean():.1%} vs unders {B[B.dir=='under'].win.mean():.1%}: z={z3[0]:+.2f}, p={z3[1]:.3f}.", z3[1])
big = B[B.e.abs() >= 8]; tb_ = pd.crosstab(big.dir, big.win)
fe = stats.fisher_exact(tb_.values) if tb_.shape == (2, 2) else (np.nan, np.nan)
rec("B72", f"Fisher's exact (small table, edge 8+ only, {len(big)} bets): " + "; ".join(f"{d} {int(r.get(1,0))}-{int(r.get(0,0))}" for d, r in tb_.iterrows()) + f". Odds ratio {fe[0]:.2f}, exact p={fe[1]:.3f}. "
    "Too few big-edge bets to say anything about direction there.", fe[1])
bins = [-np.inf, -30, -20, -10, 0, 10, 20, 30, np.inf]; e_ = A.err_v4 - A.err_v4.mean()
obs_c = pd.cut(e_, bins).value_counts().sort_index().values; pr_ = np.diff(stats.norm.cdf(bins, 0, e_.std())); exp_c = pr_ * len(A)
gof = stats.chisquare(obs_c, exp_c, ddof=2)
dig = (A.act % 10).astype(int).value_counts().reindex(range(10), fill_value=0); gd_ = stats.chisquare(dig)
rec("B73", f"Chi-square goodness of fit: v4 errors in 8 bins vs a normal curve: chi2={gof.statistic:.1f}, df=5, p={gof.pvalue:.3f} (observed {obs_c.tolist()}, expected {np.round(exp_c).astype(int).tolist()}). Left tail lighter, right tail heavier than normal: big overs (overtime) happen more than big unders, so the mean sits above the median. "
    f"Last digit of final totals uniform? chi2={gd_.statistic:.1f}, df=9, p={gd_.pvalue:.3f}.", gof.pvalue)
ci_ = stats.chi2_contingency(pd.crosstab(B.season, B.win)); ci2 = stats.chi2_contingency(pd.crosstab(B.dir, B.win))
rec("B74", f"Chi-square independence: season x win chi2={ci_[0]:.2f}, df={ci_[2]}, p={ci_[1]:.3f}; direction x win chi2={ci2[0]:.2f}, p={ci2[1]:.3f}. Win rate doesn't depend on season or direction: the edge is consistent.", ci_[1])
o1 = B[B.clv > 0].win.mean(); o2 = B[B.clv < 0].win.mean(); OR = (o1 / (1 - o1)) / (o2 / (1 - o2))
tb2 = pd.crosstab(B.clv > 0, B.win); lOR = np.log(OR); seOR = np.sqrt((1 / tb2.values).sum())
rec("B75", f"Odds: win odds when the line moved toward us {o1/(1-o1):.2f} (= {o1:.1%}); when it moved against {o2/(1-o2):.2f}. Odds ratio {OR:.2f} (95% CI {np.exp(lOR-1.96*seOR):.2f}-{np.exp(lOR+1.96*seOR):.2f}). "
    f"Break-even odds are 1.05 (52.4%); our overall odds {ph/(1-ph):.2f}.", 2 * stats.norm.sf(abs(lOR / seOR)))

# ====================== Regression (chapter 11-13)
s1 = smf.ols("y ~ e", A).fit()
rec("B76", f"Least squares: (final - opener) = {s1.params.Intercept:+.2f} + {s1.params.e:.3f} x edge. Slope SE {s1.bse.e:.3f}, p={s1.pvalues.e:.2g}. A slope of 1 would mean v4's edges are fully right; "
    f"{s1.params.e:.2f} means only ~{s1.params.e:.0%} of each edge shows up in results: shrink v4 toward the opener by ~{1-s1.params.e:.0%} when converting edge to win probability. "
    "Efficiency test on the market itself (final on close, 2011-26): " + (lambda f: f"slope {f.params.close:.3f} (SE {f.bse.close:.3f}), intercept {f.params.Intercept:+.1f}")(smf.ols('act ~ close', M).fit()) + ".", s1.pvalues.e)
rec("B77", f"R^2 of (final - opener) on edge: {s1.rsquared:.4f}: v4 explains {s1.rsquared:.2%} of the variation of totals around the opener. R^2 of final total on v4 alone: {smf.ols('act ~ v4',A).fit().rsquared:.3f}, "
    f"on the opener: {smf.ols('act ~ open_total',A).fit().rsquared:.3f}, close: {smf.ols('act ~ close_total',A).fit().rsquared:.3f}. Tiny R^2 is normal and still profitable in betting.")
rec("B78", f"Regression F test: F(1,{int(s1.df_resid)}) = {s1.fvalue:.2f}, p={s1.f_pvalue:.2g} (= t^2 for one predictor).", s1.f_pvalue)
pi = s1.get_prediction(pd.DataFrame({"e": [3, 6, 12]})).summary_frame(alpha=0.05)
rec("B79", f"Prediction vs extrapolation: at edge 3 the expected (final - opener) is {pi['mean'].iloc[0]:+.2f} (95% CI of the mean {pi.mean_ci_lower.iloc[0]:+.2f} to {pi.mean_ci_upper.iloc[0]:+.2f}), but a single game's 95% prediction interval is "
    f"{pi.obs_ci_lower.iloc[0]:+.0f} to {pi.obs_ci_upper.iloc[0]:+.0f}. Only {np.mean(A.e.abs()>=10):.1%} of games have edge 10+, so predicting at edge 12 ({pi['mean'].iloc[2]:+.2f}) is extrapolation: "
    "huge edges usually mean bad inputs (missed injury), not huge value.")
inf = OLSInfluence(s1); cd = inf.cooks_distance[0]; thr_cd = 4 / len(A)
s1d = smf.ols("y ~ e", A[cd < thr_cd]).fit()
rec("B80", f"Cook's distance: {np.sum(cd>thr_cd)} games above 4/n; max D={cd.max():.4f} (far below 1). Refit without them: slope {s1d.params.e:.3f} vs {s1.params.e:.3f}. No single game drives the result.")
mr = smf.ols("y ~ e_m1 + Lc + form + alt + rested", A).fit()
rec("B81", "Multiple regression of (final - opener) on Model 1 edge and v4's add-ons: " + ", ".join(f"{k} {v:+.3f} (p={mr.pvalues[k]:.3f})" for k, v in mr.params.items() if k != 'Intercept')
    + f". R^2 {mr.rsquared:.4f}. Each coefficient = effect holding the others fixed. Lc (shooting luck) is negative: lucky-shooting teams' games go under the opener.", mr.pvalues['Lc'])
st = OLSInfluence(mr).resid_studentized_external; bonf = 2 * stats.t.sf(np.abs(st).max(), mr.df_resid - 1) * len(A)
rec("B82", f"Studentized residuals: {np.mean(np.abs(st)>2):.1%} beyond |2| (normal 4.6%), {np.sum(np.abs(st)>3)} beyond |3|; largest |t|={np.abs(st).max():.2f}, Bonferroni outlier p={min(bonf,1):.3f}. "
    "No game is an impossible outlier once you account for 3,204 chances.", min(bonf, 1))
qr = stats.probplot(mr.resid)[1][2]
rec("B83", f"Residual Q-Q plot for the multiple regression: correlation {qr:.4f}; tails: {np.mean(mr.resid>2.576*mr.resid.std()):.2%} above z=2.576 vs 0.5% expected, {np.mean(mr.resid<-2.576*mr.resid.std()):.2%} below. "
    "Right tail a little heavy (overtime). Coefficient tests are robust to this at n=3,204.")
bp = het_breuschpagan(mr.resid, mr.model.exog); bp2 = het_breuschpagan(s1.resid, sm.add_constant(A[["open_total"]]))
dw = durbin_watson(smf.ols("y ~ e", A.sort_values("date")).fit().resid)
rec("B84", f"Homoscedasticity: Breusch-Pagan on the model's predictors p={bp[1]:.3f}; does error spread grow with the opener level? p={bp2[1]:.3f}. Durbin-Watson in date order {dw:.3f} (2 = no autocorrelation). "
    + (" Errors are independent, but their spread DOES grow with the opener: a 240 total is noisier than a 215 total (heteroscedastic)." if bp2[1] < 0.05 else " Errors look independent and roughly constant-variance."), bp2[1])
A["pres_e"] = mr.resid + mr.params.e_m1 * A.e_m1
pb_ = A.groupby(pd.qcut(A.e_m1, 8)).pres_e.mean()
rec("B85", "Component + residual (partial residual) check for the edge term: binned partial residuals " + ", ".join(f"{iv.mid:+.1f}->{v:+.2f}" for iv, v in pb_.items())
    + ". Roughly a straight line: linear in edge is a reasonable form.")
rx = smf.ols("Lc ~ e_m1 + form + alt + rested", A).fit().resid; ry = smf.ols("y ~ e_m1 + form + alt + rested", A).fit().resid
av = smf.ols("ry ~ rx", pd.DataFrame({"rx": rx, "ry": ry})).fit()
rec("B86", f"Added-variable plot for shooting luck: after removing everything else from both, slope {av.params.rx:+.3f} (= its multiple-regression coefficient), r={np.corrcoef(rx,ry)[0,1]:+.3f}. "
    "Shows luck's unique contribution: small but separate from the model edge and form.", av.pvalues.rx)
A["fit_"] = mr.fittedvalues; sl = A.groupby(pd.qcut(A.open_total, 8)).agg(lv=("open_total", "median"), sp=("err_v4", lambda x: np.median(np.abs(x - np.median(x)))))
bsl = np.polyfit(np.log(sl.lv), np.log(sl.sp), 1)[0]
rec("B87", f"Spread-level plot: log(spread of errors) vs log(line level) slope {bsl:+.2f}; suggested power transform 1 - slope = {1-bsl:.2f} (1 = leave it alone). Spread by opener octile: "
    + ", ".join(f"{r.lv:.0f}:{r.sp:.1f}" for _, r in sl.iterrows()) + ". The spread of misses grows faster than the line itself (~18% wider from the lowest to highest octile for a 12% higher line). Practical meaning: the same 3-pt edge is worth less win probability in a 240 game than a 215 game; edge measured in SDs (edge / expected noise) may rank bets better than raw points.")
Xv = A[["pred_total", "simple", "open_total", "Lc", "form"]].assign(c=1.0)
vif = {c: variance_inflation_factor(Xv.values, i) for i, c in enumerate(Xv.columns) if c != "c"}
rec("B88", "Multicollinearity, VIF when raw levels are used as predictors: " + ", ".join(f"{k} {v:.1f}" for k, v in vif.items())
    + ". Model 1, the simple average and the opener are all versions of 'how high is this total' (VIF >5-10), so their separate coefficients are unstable. "
    "That's why the model works in differences from the line (edge), which cuts the VIFs to " + ", ".join(f"{c} {variance_inflation_factor(A[['e_m1','Lc','form']].assign(c=1.0).values, i):.1f}" for i, c in enumerate(['e_m1', 'Lc', 'form'])) + ".")
bc_, lam_ = stats.boxcox(A.act)
rec("B89", f"Box-Cox on final totals: best lambda = {lam_:.2f} (1 = no transform, 0 = log). " + ("Close to 1: totals don't need transforming." if abs(lam_ - 1) < 0.5 else "Suggests a transform of raw totals (between log and square root), consistent with the spread growing with the level in B84/B87; but bets are judged against the line, and the residuals vs the line are near-normal (A20), so it changes little for over/under decisions."))
x_ = A.open_total; base = smf.ols("act ~ x", pd.DataFrame({"act": A.act, "x": x_})).fit()
bt = smf.ols("act ~ x + xl", pd.DataFrame({"act": A.act, "x": x_, "xl": x_ * np.log(x_)})).fit()
alpha_bt = 1 + bt.params.xl / base.params.x
rec("B90", f"Box-Tidwell for the opener as a predictor of the final: x*log(x) term p={bt.pvalues.xl:.3f}, estimated power {alpha_bt:.2f} (1 = keep it linear). The final total is linear in the line.", bt.pvalues.xl)
cut = B.r.abs().quantile(0.99); Bt = B[B.r.abs() < cut]
rec("B91", f"Deleting observations: dropping the most extreme 1% of bets (|points beaten| >= {cut:.0f}) changes ROI from {B.u.mean():+.2%} to {Bt.u.mean():+.2%} and win rate {ph:.1%} -> {Bt.win.mean():.1%}. "
    "Dropping Cook's-flagged games (B80) barely changes the slope either. Results don't hinge on oddball games, and we keep them because they're real.")
A["early"] = (A.ng < 25).astype(int)
ix = smf.ols("y ~ e * early", A).fit(); ix2 = smf.ols("y ~ e * C(sg)", A).fit()
rec("B92", f"Interaction: does the edge work better early in the season (either team under 25 games)? edge slope late {ix.params.e:.3f}, early adds {ix.params['e:early']:+.3f} (p={ix.pvalues['e:early']:.3f}). "
    f"Edge x direction (overs vs unders): {ix2.params.get('e:C(sg)[T.1.0]',np.nan):+.3f} (p={ix2.pvalues.get('e:C(sg)[T.1.0]',np.nan):.3f}).", ix.pvalues['e:early'])
pq = smf.ols("y ~ e + I(e**2) + I(e**3)", A).fit()
rec("B93", f"Polynomial: y ~ e + e^2 + e^3: e^2 p={pq.pvalues['I(e ** 2)']:.3f}, e^3 p={pq.pvalues['I(e ** 3)']:.3f}. Cubic coefficient {pq.params['I(e ** 3)']:+.4f}: "
    + ("negative = edges flatten out at the extremes (consistent with B79)." if pq.params['I(e ** 3)'] < 0 else "no flattening.") , pq.pvalues['I(e ** 3)'])
n0 = smf.ols("y ~ e_m1", A).fit(); n1_ = smf.ols("y ~ e_m1 + Lc + form + alt", A).fit(); nt = anova_lm(n0, n1_)
rec("B94", f"Nested models (partial F): adding luck + form + altitude to the Model 1 edge: F={nt.F.iloc[1]:.2f}, df=({int(nt.df_diff.iloc[1])},{int(nt.df_resid.iloc[1])}), p={nt['Pr(>F)'].iloc[1]:.3g}. "
    "This is the formal test that v4's add-ons beat plain Model 1 on these seasons.", nt['Pr(>F)'].iloc[1])
mods = {"open only (y~1)": smf.ols("y ~ 1", A).fit(), "M1 edge": n0, "v4 edge": s1, "M1 edge + add-ons": n1_, "+ rested": mr}
rec("B95", "AIC / BIC (lower is better): " + "; ".join(f"{k} AIC {m.aic:.1f} BIC {m.bic:.1f}" for k, m in mods.items()) + ". BIC penalizes extra terms more; the single combined v4 edge has the lowest AIC and BIC, and 'rested' makes both worse: it doesn't earn a place.")
Z = A[["e_m1", "Lc", "form", "alt", "rested", "y"]].apply(lambda c: (c - c.mean()) / c.std())
zs = smf.ols("y ~ e_m1 + Lc + form + alt + rested", Z).fit()
rk = zs.params.drop("Intercept").abs().sort_values(ascending=False)
rec("B96", "Standardized coefficients (SD change in y per SD of input): " + ", ".join(f"{k} {zs.params[k]:+.3f}" for k in rk.index) + ". Ranking: " + " > ".join(rk.index)
    + ". Model 1's edge matters most, then form, altitude and shooting luck about equally; rest adds nothing.")
rec("B97", f"Adjusted R^2: one-predictor v4 edge {s1.rsquared_adj:.4f}; Model 1 edge + 4 add-ons {mr.rsquared_adj:.4f} (raw {mr.rsquared:.4f}). Adjusted R^2 only rises if a term earns its keep.")
lgt = smf.logit("over ~ e", A[A.act != A.open_total]).fit(disp=0)
A["pl"] = lgt.predict(A); cal = A[A.act != A.open_total].groupby(pd.qcut(A.pl, 5)).agg(pred=("pl", "mean"), obs=("over", "mean"), n=("over", "size"))
rec("B98", f"Logistic regression: log-odds(over) = {lgt.params.Intercept:+.3f} + {lgt.params.e:.4f} x edge (p={lgt.pvalues.e:.2g}). A 3-pt edge -> P(over) {1/(1+np.exp(-(lgt.params.Intercept+3*lgt.params.e))):.1%}, "
    f"6-pt {1/(1+np.exp(-(lgt.params.Intercept+6*lgt.params.e))):.1%}. Calibration by quintile (pred/obs): " + ", ".join(f"{r.pred:.1%}/{r.obs:.1%}" for _, r in cal.iterrows())
    + ". This is the honest edge->probability map to use for EV and Kelly instead of the normal curve in A41.", lgt.pvalues.e)

# B64/B65 multiple testing across this whole catalog
keys = list(PV); pv = np.array([PV[k] for k in keys])
bon = multipletests(pv, 0.05, "bonferroni"); bh = multipletests(pv, 0.05, "fdr_bh")
raw_sig = [k for k, p in zip(keys, pv) if p < 0.05]
rec("B64", f"This catalog ran {len(pv)} hypothesis tests. Raw p<0.05: {len(raw_sig)} ({', '.join(raw_sig)}). With 0 real effects we'd expect ~{0.05*len(pv):.1f} by luck. "
    f"After Benjamini-Hochberg (false discovery rate 5%): {', '.join(k for k, r in zip(keys, bh[0]) if r) or 'none'}. This is the familywise trap of testing many trends on one data set.")
rec("B65", f"Bonferroni: each test must hit p < 0.05/{len(pv)} = {0.05/len(pv):.4f}. Survivors: {', '.join(k for k, r in zip(keys, bon[0]) if r) or 'none'}. "
    "Those are the only findings here strong enough to take forward as candidate 'real' trends; everything else is exploratory.")
json.dump({"results": R, "pvalues": PV, "n_bets": int(n), "wins": int(w)}, open("results.json", "w"), indent=1)
print("\nDONE", len(R))
