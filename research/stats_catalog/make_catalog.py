import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import json, re
J = json.load(open("results.json")); R = J["results"]; PV = J["pvalues"]; O = json.load(open("oos.json"))
NT = len(PV); NR = sum(p < 0.05 for p in PV.values()); NB = sum(p < 0.05 / NT for p in PV.values())
P = {}
for f in ("papers_A.md", "papers_B.md"):
    for line in open(f):
        if re.match(r"^\| [AB]\d\d ", line):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            P[c[0]] = dict(name=c[1], cite=c[2], url=c[3], how=c[4], lesson=c[5], ver=c[6])
FORM = {
"A01": "Population = all units of interest; sample = the subset observed. Statistic (e.g. x̄) estimates a parameter (μ).",
"A02": "Observational: we watch X and Y. Experiment: we assign X at random. Only randomization licenses 'X causes Y'.",
"A03": "A confounder Z is associated with both X and Y; the X–Y link can be partly or fully Z.",
"A04": "Survivorship bias: analyzing only units that passed a filter (planes that returned, funds that survived).",
"A05": "SRS: SE = s/√n. Cluster sampling: units within a cluster are correlated, inflating SE. Stratified: sample within strata.",
"A06": "Selection / nonresponse bias: the units you observe differ systematically from those you don't (1936 Literary Digest).",
"A07": "Randomization: assign treatments by chance; the randomization (permutation) distribution gives an exact p-value.",
"A08": "CRD: y_ij = μ + τ_i + ε_ij. RBD: y_ij = μ + τ_i + β_j + ε_ij (block β removes nuisance variation).",
"A09": "Latin square: two blocking factors (rows, columns), each treatment once per row and column.",
"A10": "Factorial: all combinations of factor levels; interaction = effect of A depends on level of B.",
"A11": "ANCOVA: y = μ + τ_i + β(x − x̄) + ε; compares groups after adjusting for a covariate x.",
"A12": "Experimental unit = what gets the treatment; measurement unit = what is measured. Treating sub-measurements as independent = pseudoreplication.",
"A13": "Bar chart: counts or percentages per category.",
"A14": "Pie chart: category shares of a whole (sum to 100%).",
"A15": "Histogram; shape: modality, skewness, tails.",
"A16": "Relative frequency = count / n; relative frequency histogram approximates the density.",
"A17": "Time-series plot: value vs time to show trend, seasonality, drift.",
"A18": "Mean x̄ = Σx/n; median = middle value; mode = most common; trimmed mean drops top/bottom k%.",
"A19": "pth percentile: p% of data at or below it; quartiles Q1, Q2, Q3.",
"A20": "Q-Q plot: sample quantiles vs normal quantiles; straight line = normal. Shapiro-Wilk W tests it.",
"A21": "IQR = Q3 − Q1; inner fences Q1 − 1.5·IQR, Q3 + 1.5·IQR; points outside = potential outliers.",
"A22": "s² = Σ(x − x̄)²/(n − 1); s = √s².",
"A23": "Mound-shaped data: ~68% within x̄ ± s, ~95% within ± 2s, ~99.7% within ± 3s.",
"A24": "CV = s / x̄ (relative variability).",
"A25": "Side-by-side boxplots compare center and spread across groups.",
"A26": "Contingency table: counts for two categorical variables; stacked/grouped bar charts.",
"A27": "r = Σ(x − x̄)(y − ȳ) / √[Σ(x − x̄)² Σ(y − ȳ)²], −1 ≤ r ≤ 1.",
"A28": "r measures only LINEAR association; r ≈ 0 can hide a strong curved pattern.",
"A29": "0 ≤ P(E) ≤ 1; P(Eᶜ) = 1 − P(E); P(A ∪ B) = P(A) + P(B) − P(A ∩ B).",
"A30": "Nontransitive dice: A beats B, B beats C, C beats A (pairwise 'better' need not be transitive).",
"A31": "Simpson's paradox: a relationship within every group reverses when groups are pooled.",
"A32": "P(A | B) = P(A ∩ B) / P(B).",
"A33": "Independent iff P(A ∩ B) = P(A)P(B), i.e. P(A | B) = P(A).",
"A34": "Multiplication law: P(A ∩ B) = P(A | B)P(B); = P(A)P(B) if independent.",
"A35": "Sensitivity = P(+ | condition); specificity = P(− | no condition).",
"A36": "Bayes: P(A | B) = P(B | A)P(A) / [P(B | A)P(A) + P(B | Aᶜ)P(Aᶜ)].",
"A37": "E[X] = Σ x·p(x); Var(X) = Σ (x − μ)²·p(x).",
"A38": "Binomial: P(X = k) = C(n,k)pᵏ(1 − p)ⁿ⁻ᵏ; μ = np, σ² = np(1 − p).",
"A39": "Poisson: P(Y = k) = e^(−λ)λᵏ/k!; μ = σ² = λ; rate scaling λ = r·(t/t₀).",
"A40": "Binomial(n, p) ≈ Poisson(λ = np) when n large and p small.",
"A41": "Continuous X: P(a ≤ X ≤ b) = area under the density f(x) between a and b.",
"A42": "X ~ N(μ, σ²); Z = (X − μ)/σ ~ N(0, 1).",
"A43": "Quantile x_p = μ + z_p·σ, where P(Z ≤ z_p) = p.",
"A44": "Random sample: every subset of size n equally likely.",
"A45": "Sampling distribution of x̄: mean μ, standard error σ/√n.",
"A46": "CLT: x̄ (and sums) approximately normal for large n (n ≥ 30), whatever the population shape.",
"A47": "Normal approx to binomial if np ≥ 10, n(1 − p) ≥ 10: P(X ≤ k) ≈ P(Z ≤ (k + 0.5 − np)/√(np(1 − p))).",
"B48": "Point estimate: a single number (x̄, p̂) for a parameter.",
"B49": "CI for μ: x̄ ± t(n−1, 1−α/2)·s/√n.",
"B50": "n ≈ (z_(α/2)·σ / E)², round up.",
"B51": "Test: H0, Ha, test statistic, rejection region, conclusion. One-sided vs two-sided Ha.",
"B52": "Type I (reject true H0, rate α); Type II (miss false H0, rate β); power = 1 − β.",
"B53": "p-value = P(statistic at least as extreme as observed | H0); reject if p ≤ α.",
"B54": "t = (x̄ − μ0)/(s/√n), df = n − 1; heavier tails than Z for small n.",
"B55": "Pooled t = (x̄1 − x̄2)/(s_p√(1/n1 + 1/n2)), s_p² = [(n1−1)s1² + (n2−1)s2²]/(n1 + n2 − 2).",
"B56": "Welch t = (x̄1 − x̄2)/√(s1²/n1 + s2²/n2), Satterthwaite df.",
"B57": "Paired: d_i = x1i − x2i; t = d̄/(s_d/√n), df = n − 1.",
"B58": "F = s1²/s2², df (n1 − 1, n2 − 1).",
"B59": "One-way ANOVA: SST = SSB + SSW; F = MSB/MSW, df (t − 1, N − t).",
"B60": "ANOVA assumes normal errors with equal variance; check by Q-Q plots and residual-vs-fitted spread (Levene/Brown-Forsythe, Bartlett).",
"B61": "Transform y (log, √, power) to fix skew or unequal variance.",
"B62": "Contrast L = Σc_iμ_i with Σc_i = 0; SE = √(MSE·Σc_i²/n_i).",
"B63": "Orthogonal contrasts: Σc_i d_i/n_i = 0; their SS partition SSB.",
"B64": "Familywise error: P(≥ 1 false rejection) = 1 − (1 − α)^m for m independent tests.",
"B65": "Bonferroni: test each at α/m.",
"B66": "Fisher LSD: unadjusted pairwise t-tests, only after a significant overall F.",
"B67": "Tukey HSD: all pairwise differences, familywise α via the studentized range q.",
"B68": "Scheffé: any (incl. unplanned) contrast; reject if t² > (t − 1)·F(α; t − 1, N − t).",
"B69": "π̂ ± z·√(π̂(1 − π̂)/n) (Wilson/Agresti-Coull better); z = (π̂ − π0)/√(π0(1 − π0)/n).",
"B70": "n = z²·π(1 − π)/E².",
"B71": "z = (π̂1 − π̂2)/√(π̂(1 − π̂)(1/n1 + 1/n2)) with pooled π̂.",
"B72": "Fisher's exact test: hypergeometric probability of tables with fixed margins.",
"B73": "χ² = Σ(O − E)²/E, df = k − 1 − (estimated parameters).",
"B74": "Independence: E_ij = (row_i·col_j)/n; χ² with df (r − 1)(c − 1).",
"B75": "Odds = p/(1 − p); OR = odds1/odds2; log(OR) SE = √(Σ1/n_ij).",
"B76": "y = β0 + β1x + ε; b1 = Sxy/Sxx, b0 = ȳ − b1x̄ minimizes SSE = Σ(y − ŷ)².",
"B77": "R² = 1 − SSE/SST = share of variation explained.",
"B78": "Regression F = MSR/MSE; tests all slopes = 0.",
"B79": "Prediction interval (one new y) is wider than CI for the mean; extrapolation = predicting outside the observed x range.",
"B80": "Cook's D_i = (r_i²/p)·h_ii/(1 − h_ii)²; flag if D > 4/n or > 1.",
"B81": "y = β0 + β1x1 + … + βkxk + ε; each β = effect holding the others fixed.",
"B82": "Studentized residual = e_i / (s_(i)√(1 − h_ii)); |t| > 2–3 flags outliers; Bonferroni outlier test.",
"B83": "Q-Q plot of residuals checks normal errors.",
"B84": "Constant variance (Breusch-Pagan / ncvTest) and independent errors (Durbin-Watson ≈ 2).",
"B85": "Component + residual (partial residual) plot: e + b_j·x_j vs x_j checks linearity of x_j.",
"B86": "Added-variable plot: residuals of y on others vs residuals of x_j on others; slope = b_j.",
"B87": "Spread-level plot: log|resid spread| vs log(fitted); power transform ≈ 1 − slope.",
"B88": "VIF_j = 1/(1 − R_j²); > 5–10 = problem collinearity.",
"B89": "Box-Cox: y^(λ) = (y^λ − 1)/λ (log if λ = 0); choose λ by likelihood.",
"B90": "Box-Tidwell: test x^α for a predictor via the x·log(x) term.",
"B91": "Deleting observations: refit without flagged points to check robustness (only drop for real errors).",
"B92": "Interaction: y = β0 + β1x1 + β2x2 + β3x1x2; slope of x1 is β1 + β3x2.",
"B93": "Polynomial: y = β0 + β1x + β2x² + β3x³ + ε.",
"B94": "Nested F = [(SSE_r − SSE_f)/q] / [SSE_f/(n − p)].",
"B95": "AIC = 2k − 2 log L; BIC = k log n − 2 log L; lower is better.",
"B96": "Standardized β = b·(s_x/s_y); ranks predictors on a common scale.",
"B97": "Adjusted R² = 1 − (1 − R²)(n − 1)/(n − p − 1).",
"B98": "Logistic: log[p/(1 − p)] = β0 + β1x; e^β1 = odds ratio per unit x.",
}
ST = {k: "Tool" for k in R}
for k in "A01 A07 A27 A38 B51 B54 B69 B76 B78 B94 B98".split(): ST[k] = "Confirmed (in-sample)"
for k in "A02 A32 B75".split(): ST[k] = "Confirmed (in-sample)"
for k in "A04 B84 B87 B73 A15".split(): ST[k] = "Confirmed out of sample"
for k in "B59 B67 B68 A17 A25".split(): ST[k] = "Suggestive (partly replicates)"
for k in "A03".split(): ST[k] = "Warning"
for k in "A06 B62 B81 B86 A20 B92".split(): ST[k] = "Suggestive"
for k in "A08 A09 A10 A11 A28 A31 A33 B55 B56 B57 B58 B60 B71 B72 B74 B90 B93 A30".split(): ST[k] = "No trend"
for k in "B41 A41 B79 B88 B52 B50 A45 B64 B65".split(): ST[k] = "Warning"
CARRY = {"A04": "Hot streaks of an asset or manager regress the same way (fund-persistence studies).",
         "A05": "Same-day bets ≈ same-day trades: check clustered SEs before trusting a backtest.",
         "A07": "Permutation test of a signal vs coin-flip sides works for any long/short rule.",
         "A33": "Test any strategy for streakiness before sizing on 'hot' runs.",
         "A41": "Normal-curve win probabilities centered on your own forecast overstate confidence whenever the market also has information.",
         "B50": "Required sample sizes for small edges are in the thousands: true for any market strategy.",
         "B52": "Power analysis before testing a filter applies to any backtest.",
         "B64": "Multiple testing on one dataset is the #1 reason 'discovered' market anomalies fail (Harvey-Liu-Zhu).",
         "B65": "Bonferroni / FDR before believing any scanned-for trend.",
         "B75": "Price moving toward your position after entry (CLV) as a skill marker carries directly to trading.",
         "B76": "Regress outcomes on your edge: slope < 1 tells you how much to shrink any forecast toward the market price.",
         "B84": "Noise that scales with the level (volatility rises with price/total): size by edge in SD units.",
         "B87": "Same as B84.",
         "B73": "Right-skewed outcomes: mean ≠ median, so 'average beats the line' ≠ 'wins more than half'. Same for skewed returns.",
         "A03": "Effects that exist in one era and not another (structural breaks) are common in markets too.",
         "B98": "Logistic calibration maps any edge to a probability for EV/Kelly sizing.",
         "A37": "Kelly / EV math for any repeated favorable bet."}
ORDER = list(R)
grp = {"A0": "Study design (Ch 1-2)", "A1": None}
def section(k):
    i = int(k[1:]) if k[0] == "A" else int(k[1:])
    if k[0] == "A":
        return "Study design and data collection" if i <= 12 else ("Describing data" if i <= 28 else "Probability and sampling distributions")
    return ("Estimation and tests for one or two populations" if i <= 58 else "ANOVA and multiple comparisons" if i <= 68 else
            "Categorical data" if i <= 75 else "Regression, diagnostics and model choice")
L = []
L.append("""# Statistics concept catalog: every course method applied to the NBA totals model

*Started Nov 4, 2026. Living document: add a row each time a new formula, test or model comes up (procedure at the bottom).*

**Model tested:** NBA totals v4 (the live model: Model 1 walk-forward + shooting-luck, recent-form and altitude adjustments), graded at DraftKings
openers, 2023-24 to 2025-26 seasons, both teams 10+ games: **3,204 games, 1,446 bets at edge 3+ (820-626, 56.7%, +119.5u)**.
Market-only checks use 18,695 games of closing lines (2011-12 to 2025-26) and, as an out-of-sample test, 9,591 regular-season games with
SportsbookReview openers 2011-12 to 2018-19 (before any season v4 was built on).

Why NBA totals first: it's the model with real day-ahead openers, the longest odds history, and the clearest record. NHL is next.

**Read this first.** These 3 seasons were used to build and choose v4, so every in-sample test below is *descriptive*. A trend only counts as
real if it (a) survives the multiple-testing correction in B65 *and* (b) shows up again in seasons the model never saw.

## Status key
- **Confirmed out of sample**: also shows up in 2011-19.
- **Confirmed (in-sample)**: passes Bonferroni across all the tests here, but only on the seasons that built v4.
- **Suggestive**: p < 0.05 but fails Bonferroni, or only partly replicates.
- **No trend**: tested, nothing there (recorded so we don't re-test it by accident).
- **Warning**: a result that limits how we should read or use the model.
- **Tool**: a description or method with no yes/no test.
- ⇄ marks findings that should carry over to other markets (stocks, prediction markets).
""")
L.append("""## What came out of it

**1. v4's edges are only about 55% real (B76, B98, A41).** Regressing (final - opener) on v4's edge gives slope 0.55: a 3-pt edge is worth
about 1.65 pts in results. The logistic fit turns edges into honest win probabilities: **3 pts -> 53.7%, 6 pts -> 57.4%**, well calibrated across
quintiles. The normal curve centered on v4 says 61.8% for the average bet; the truth is 56.7%. Use the logistic map for EV and Kelly.

**2. The line moving toward us is the strongest marker of a winner (A32, B75).** Win rate 61.2% when the total moved our way by close,
52.3% no move, 48.1% against. Odds ratio 1.70 (95% CI 1.37-2.11). This backs the live rule (bet the opener; pass after a 0.5+ move against).

**3. The edge is not luck, and not streaky (A07, A33, A38, A05).** Coin-flip sides on the same games average -4.5% ROI; v4's +8.3% beats all
but 1 in 5,000 random draws. Results on the same night are independent (r = +0.015), runs test p = 0.96, and clustering by night barely widens
the error bars (x1.03).

**4. But a season is too short to judge anything (A45, B52, B50).** One season's ROI is only ~1.9 standard errors from zero. Detecting a true
55% bettor with 80% power takes ~2,300 bets (~5 seasons of v4 volume). Any new filter tested on 100-300 bets will usually "fail" even if it works.

**5. Two market facts replicate in 2011-19 and are worth building on (B84/B87, B73).**
- *Noise grows with the total* (Breusch-Pagan p = 0.008 here, p = 0.0005 in 2011-19). A 3-pt edge on a 240 total is worth less than on a 215
  total. **Idea to test next:** rank bets by edge / expected SD instead of raw points.
- *Totals are right-skewed* (overtime): mean above median in both eras (2011-19 skew +0.30, mean +0.48, median 0.00). Big overs happen more
  than big unders, but the over doesn't win more than half the time. When "average beats the line" and "wins more than half" disagree,
  the win rate is what pays.

**6. April runs over the opener; January runs under (B59, B67, B68).** 2023-26: April +3.4 pts vs opener, January -1.6; the April-vs-January gap
clears Scheffé's after-the-fact bar (t = 4.04 vs 3.33), though the overall month ANOVA (p = 0.001) just misses Bonferroni. In 2011-19 April is again the highest month (+1.45, p = 0.07 vs the rest) but **only 50.8% of April games went
over**, so it's a tail effect (blowouts, garbage time, tanking), not a bettable lean. January did not replicate. v4's own bets showed no month
effect (p = 0.17), so the model isn't hurt by it.

**7. Warning: the altitude bonus is era-specific (A03).** Denver/Utah home games beat the opener by +4.3 in 2023-26 (v4 adds +3.8, which fixes
it), and beat the close in 4 of 5 seasons 2021-26 (+2.8 overall, p = 0.002). In 2011-19 the same games went **-0.5** vs the opener (p = 0.52).
The effect is real in the current era but didn't exist before 2021. Keep the +3.8, but watch it: if it fades, it's the first term to cut.

**8. "Over teams" are a mirage (A04, confirmed out of sample).** Teams in the top 20% for over% in their first 41 games (59%) go 49-50% the
rest of the way, in both 2021-26 and 2011-19. Never bet a team's over/under record.

**9. What v4 doesn't need (A08-A11, B55-B57, B71, B74, B92, B93, B95).** Bigger edges don't win more (edge-bucket ANOVA p = 0.33). Overs and
unders win alike (57.2% vs 56.1%). There's no edge-by-early-season or edge-by-direction interaction, and no curve in the edge (polynomial terms
n.s.). Rest/back-to-back adds nothing beyond the line (AIC and BIC both get worse). v4 is no more accurate than the opener in absolute error
(paired t p = 0.47) and less accurate than the close (p < 0.001): **the profit comes from direction at the open, not from a better total.**

**10. Multiple testing (B64, B65).** {NT} tests, {NR} with p < 0.05, {NB} survive Bonferroni. Several are the same question asked different ways (A38, B51, B54 and B69 all test v4's win rate), so the count overstates the independent findings. The survivors are the in-sample "Confirmed"
rows. Everything else is exploratory.

**Kelly note (A37 + B98).** At the observed 56.7%, full Kelly is 9.1% of bankroll. With the honest logistic probability for a 3-pt edge (53.7%),
it's 2.8%. The 1% flat unit is about a third of Kelly on typical bets: sensible, and no reason to size up.

### Out-of-sample check (2011-12 to 2018-19, SBR openers, regular season)
| Trend found in 2023-26 | 2011-19 result | Verdict |
|---|---|---|
""")
L.append(f"| Spread of misses grows with the total | {O['spread']} | Replicates |")
L.append(f"| Right-skewed totals (mean > median) | {O['skew']} | Replicates |")
L.append(f"| 'Over teams' regress | {O['over_teams']} | Replicates |")
L.append(f"| April over / January under | {O['month']} {O['april_by_season']} | April partly (mean only); January no |")
L.append(f"| Altitude home games over the opener | {O['altitude']} | Does **not** replicate before 2021 |")
L.append(f"| Early-season games over the opener (A06) | {O['early']} | Does not replicate |")
L.append("")
L.append("""## How to read each entry
**Formula**: from the course notes. **Paper**: a peer-reviewed paper that used the method, and how. **Applied to v4**: what we ran and what came out.
Scripts: `research/stats_catalog/run_all.py` (all in-sample tests), `oos.py` (2011-19 checks), `build.py` (rebuilds the per-game data).
""")
cur = None
for k in ORDER:
    if k in ("B64", "B65"): pass
    sec = section(k)
    if sec != cur: L.append(f"\n## {sec}\n"); cur = sec
    p = P.get(k, {})
    nm = p.get("name", k)
    L.append(f"### {k}. {nm}  ·  *{ST[k]}*{'  ⇄' if k in CARRY else ''}")
    L.append(f"- **Formula / idea:** {FORM.get(k,'')}")
    if p:
        ver = "" if p["ver"].lower().startswith("yes") else " *(citation details partly unverified)*"
        L.append(f"- **Paper:** {p['cite']} {p['url']}{ver}")
        L.append(f"  - *How they used it:* {p['how']}")
        L.append(f"  - *Lesson:* {p['lesson']}")
    L.append(f"- **Applied to v4:** {R[k]}")
    if k in CARRY: L.append(f"- **Carries over:** {CARRY[k]}")
    L.append("")
L.append("""## Adding a new concept (do this every time)
1. Add the formula/idea with the next ID (A48+, B99+, or a new letter for a new course/source).
2. Find one peer-reviewed paper from a mainstream journal that applied it; verify the citation and DOI.
3. Add a block to `run_all.py` that applies it to the same v4 data (`build.py` output), calling `rec(ID, text, p)` with a p-value if it's a test.
4. Rerun. The multiple-testing count in B64/B65 updates automatically: a new trend has to clear the new, stricter bar.
5. Anything that passes: add it to `oos.py` and check it on 2011-19 (and NHL / other markets) before calling it real. Mark ⇄ if it should carry over.
6. Update the status, the summary above, and `analysis/FINDINGS.md`.
""")
txt = "\n".join(L).replace("{NT}", str(NT)).replace("{NR}", str(NR)).replace("{NB}", str(NB))
open("README.md", "w").write(txt)
print(len("\n".join(L)), sum(1 for k in R))
