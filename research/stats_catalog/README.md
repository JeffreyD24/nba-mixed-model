# Statistics concept catalog: every course method applied to the NBA totals model

*Started Nov 4, 2026. Living document: add a row each time a new formula, test or model comes up (procedure at the bottom).*

**Model tested:** NBA totals v4 (the live model: Model 1 walk-forward + shooting-luck, recent-form and altitude adjustments), graded at DraftKings
openers, 2023-24 to 2025-26 seasons, both teams 10+ games: **3,204 games, 1,446 bets at edge 3+ (820-626, 56.7%, +119.5u)**.
Market-only checks use 18,695 games of closing lines (2011-12 to 2025-26) and, as an out-of-sample test, 9,591 regular-season games with
SportsbookReview openers 2011-12 to 2018-19 (before any season v4 was built on).

Why NBA totals first: it's the model with real day-ahead openers, the longest odds history, and the clearest record. The NHL version
(same 98 IDs) is in `nhl-mixed-model/research/stats_catalog/`.

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

## What came out of it

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
  total. **Tested (Nov 4, `edge_sd_test.py`, rule set in advance): it doesn't help.** The noise only grows from ~13.8 pts at a 200 total to
  ~15.0 at 240 (fit on 2011-19), too little to reorder bets: ranking by edge/noise picks 1,440 of the same 1,446 bets in 2023-26 (same
  +119.5u), and on 2013-22 Model 1 bets the top halves by each measure win 53.5% / 53.5%. Keep raw edge.
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

**10. Multiple testing (B64, B65).** 40 tests, 19 with p < 0.05, 13 survive Bonferroni. Several are the same question asked different ways (A38, B51, B54 and B69 all test v4's win rate), so the count overstates the independent findings. The survivors are the in-sample "Confirmed"
rows. Everything else is exploratory.

**Kelly note (A37 + B98).** At the observed 56.7%, full Kelly is 9.1% of bankroll. With the honest logistic probability for a 3-pt edge (53.7%),
it's 2.8%. The 1% flat unit is about a third of Kelly on typical bets: sensible, and no reason to size up.

### Out-of-sample check (2011-12 to 2018-19, SBR openers, regular season)
| Trend found in 2023-26 | 2011-19 result | Verdict |
|---|---|---|

| Spread of misses grows with the total | Error spread grows with the opener: Breusch-Pagan p=0.00046; SD by opener quintile 184:17.6, 198:16.8, 205:17.8, 212:18.2, 230:18.6. | Replicates |
| Right-skewed totals (mean > median) | (final - opener) skewness +0.295, mean +0.48, median +0.00; share beyond +30 5.33% vs below -30 3.36%. | Replicates |
| 'Over teams' regress | Team over% first 41 vs rest (vs opener): r=-0.05 (p=0.45, 240 team-seasons); top-20% teams 59.3% -> 48.8%. | Replicates |
| April over / January under | (final - opener) by month: Oct +1.07 (n=354), Nov -0.16 (n=1553), Dec +1.03 (n=1638), Jan +0.42 (n=1834), Feb +1.28 (n=1380), Mar -0.62 (n=1886), Apr +1.45 (n=946). Month ANOVA p=0.010. April vs rest +1.08, Welch p=0.074; April over the opener 50.8% (n=946). January vs rest -0.06, p=0.892. April by season: 2011-12 +0.4, 2012-13 -0.5, 2013-14 +4.2, 2014-15 +2.3, 2015-16 +1.0, 2016-17 +0.6, 2017-18 +0.2, 2018-19 +4.7 | April partly (mean only); January no |
| Altitude home games over the opener | Denver/Utah home games vs opener: -0.47 pts (SE 0.73, p=0.518); over rate 47.2% (n=638). By season: 2011-12 +1.4, 2012-13 -0.5, 2013-14 +1.4, 2014-15 -1.3, 2015-16 +0.5, 2016-17 +1.5, 2017-18 -1.6, 2018-19 -0.8 | Does **not** replicate before 2021 |
| Early-season games over the opener (A06) | Games where a team is in its first 10: -0.60 pts vs opener relative to later games (p=0.266); mean -0.05 (n=1255) vs +0.55. Opener MAE early 14.42 vs later 13.91. | Does not replicate |

## How to read each entry
**Formula**: from the course notes. **Paper**: a peer-reviewed paper that used the method, and how. **Applied to v4**: what we ran and what came out.
Scripts: `research/stats_catalog/run_all.py` (all in-sample tests), `oos.py` (2011-19 checks), `build.py` (rebuilds the per-game data).


## Study design and data collection

### A01. Population vs sample  ·  *Confirmed (in-sample)*
- **Formula / idea:** Population = all units of interest; sample = the subset observed. Statistic (e.g. x̄) estimates a parameter (μ).
- **Paper:** Gandar, J., Zuber, R., O'Brien, T., & Russo, B. (1988). Testing rationality in the point spread betting market. *The Journal of Finance, 43*(4), 995-1008. https://doi.org/10.2307/2328148
  - *How they used it:* They treated a sample of NFL seasons as evidence about the whole market of games. Standard regression tests on that sample did not reject that closing spreads are unbiased, but economic tests of betting rules found apparent inefficiencies.
  - *Lesson:* Your backtest seasons are a sample from the population of future games, so an edge found in one sample has to be shown to hold out of sample before you trust it.
- **Applied to v4:** Population = every NBA game the market prices; our 'sample' = 18,695 games 2011-12..2025-26. Mean (final total - closing total) = +0.48 pts (t=3.72, p=0.000); by season ranges -0.08 to +1.24. Seasons with the biggest misses: 2013-14 +1.2, 2019-20 +1.1, 2022-23 +1.0. The closing line is close to unbiased over the long run, but a single season can run 1+ pt high (league scoring rising faster than the market adjusts). Overs have a tiny long-run tailwind, far below the vig.

### A02. Observational study vs experiment; correlation is not causation  ·  *Confirmed (in-sample)*
- **Formula / idea:** Observational: we watch X and Y. Experiment: we assign X at random. Only randomization licenses 'X causes Y'.
- **Paper:** Levitt, S. D. (2004). Why are gambling markets organised so differently from financial markets? *The Economic Journal, 114*(495), 223-246. https://doi.org/10.1111/j.1468-0297.2004.00207.x
  - *How they used it:* He studied 19,770 observational bets by 285 bettors in an online-sportsbook NFL handicapping contest (2001-02), plus 21 seasons of results against the spread. Favourites drew about 61% of bets but covered less than half the time, and from this he inferred (rather than tested experimentally) that bookmakers shade lines to exploit bettor bias.
  - *Lesson:* A stat that is correlated with overs in historical data is not shown to cause overs. Without an experiment, treat such patterns as associations that may come from line-setting behaviour.
- **Applied to v4:** Everything here is observational (no one randomizes which games get a model edge). Example: bets whose line later moved our way (CLV>0) won 61.2% (n=919), moved against us 48.1% (n=418). Line movement doesn't CAUSE wins: both come from the same underlying information (injuries, sharp money). It's a marker, not a lever: we can't make the line move.

### A03. Confounding variables  ·  *Warning*  ⇄
- **Formula / idea:** A confounder Z is associated with both X and Y; the X–Y link can be partly or fully Z.
- **Paper:** Price, J., & Wolfers, J. (2010). Racial discrimination among NBA referees. *The Quarterly Journal of Economics, 125*(4), 1859-1887. https://doi.org/10.1162/qjec.2010.125.4.1859
  - *How they used it:* They used NBA box scores (1991-2004) to show that players get more fouls when the referee crew is of the opposite race. They controlled for player, referee and game characteristics so that playing style and matchup would not confound the race effect.
  - *Lesson:* Totals drivers such as pace, rest, altitude and referee crew are correlated with one another, so estimate them together (or with fixed effects) instead of crediting one variable with what another explains.
- **Applied to v4:** Denver/Utah home games: raw totals +8.6 pts vs other games (p=0.000); vs the opener +4.30 (p=0.001); vs v4 (which adds +3.8) -0.37 (p=0.775). The raw gap is confounded by who those teams are (pace, roster); the market already prices most of it, so the useful number is the residual after the line.
- **Carries over:** Effects that exist in one era and not another (structural breaks) are common in markets too.

### A04. Survivorship bias  ·  *Confirmed out of sample*  ⇄
- **Formula / idea:** Survivorship bias: analyzing only units that passed a filter (planes that returned, funds that survived).
- **Paper:** Brown, S. J., Goetzmann, W., Ibbotson, R. G., & Ross, S. A. (1992). Survivorship bias in performance studies. *The Review of Financial Studies, 5*(4), 553-580. https://ideas.repec.org/a/oup/rfinst/v5y1992i4p553-80.html (DOI not confirmed)
  - *How they used it:* Using numerical examples of mutual-fund returns, they showed that dropping funds that died makes past performance look like it predicts future performance even when it does not.
  - *Lesson:* Backtesting only systems, touts or player pools that "survived" to today overstates edge, so keep every model version and every game in the record.
- **Applied to v4:** Selection on past success: team-seasons in the top 20% for over% in their first 41 games (avg 59.2%) went over 49.8% the rest of the way; bottom 20% (41.0%) went 51.2%. First-half vs second-half correlation r=-0.07 (p=0.37, 150 team-seasons, 2021-26). 'Over teams' are the survivors of a noisy filter: almost all of it disappears. Same trap as only studying the systems that made money.
- **Carries over:** Hot streaks of an asset or manager regress the same way (fund-persistence studies).

### A05. Sampling designs / clustered standard errors  ·  *Tool*  ⇄
- **Formula / idea:** SRS: SE = s/√n. Cluster sampling: units within a cluster are correlated, inflating SE. Stratified: sample within strata.
- **Paper:** Moulton, B. R. (1990). An illustration of a pitfall in estimating the effects of aggregate variables on micro units. *The Review of Economics and Statistics, 72*(2), 334-338. https://doi.org/10.2307/2109724
  - *How they used it:* In a regression of individual workers' wages on state-level variables, OLS that ignored within-state error correlation understated standard errors badly.
  - *Lesson:* Games share teams, dates and referee crews, so cluster standard errors (for example by team-season or date) or your edge will look more significant than it is.
- **Applied to v4:** ROI per bet +8.26%. Standard error if every bet were a simple random sample: 2.49%; cluster bootstrap by game night (bets on one night share news/refs/league scoring): 2.57%; stratified by season: 2.47%. Ratio cluster/SRS = 1.03. If >1, same-night bets are correlated and naive confidence intervals are too narrow.
- **Carries over:** Same-day bets ≈ same-day trades: check clustered SEs before trusting a backtest.

### A06. Selection / nonresponse bias  ·  *Suggestive*
- **Formula / idea:** Selection / nonresponse bias: the units you observe differ systematically from those you don't (1936 Literary Digest).
- **Paper:** Squire, P. (1988). Why the 1936 Literary Digest poll failed. *Public Opinion Quarterly, 52*(1), 125-133. https://doi.org/10.1086/269085
  - *How they used it:* Using a 1937 Gallup survey that asked people whether they had received and returned the Digest ballot, he showed that the sampling frame was biased but that nonresponse bias (Landon supporters were more likely to reply) was the main cause of the error.
  - *Lesson:* Line archives or "public betting %" feeds that cover only some books or games are self-selected samples, so check which games are missing and why before fitting.
- **Applied to v4:** Of 3684 DraftKings-priced games 2023-26, 480 (13%) aren't in our test set (mostly the first ~10 games of each team's season). The opener misses those dropped games by 14.30 pts on average vs 14.69 in kept games, and their totals average +1.53 vs the opener (+0.42 kept). Like the Literary Digest poll, our results describe only the games we kept. The dropped early-season games weren't harder for the book, but they did run over the opener by ~1 pt more: a possible early-season over lean that our test set never sees.

### A07. Randomization / permutation test  ·  *Confirmed (in-sample)*  ⇄
- **Formula / idea:** Randomization: assign treatments by chance; the randomization (permutation) distribution gives an exact p-value.
- **Paper:** Ritzwoller, D. M., & Romano, J. P. (2022). Uncertainty in the hot hand fallacy: Detecting streaky alternatives to random Bernoulli sequences. *The Review of Economic Studies, 89*(2), 976-1007. https://doi.org/10.1093/restud/rdab020
  - *How they used it:* They built permutation tests that compare make rates after streaks with rates under reshuffled shot sequences, then applied them to four controlled basketball shooting experiments. Much larger datasets were needed to detect streakiness, and only one shooter's sequence significantly departed from randomness.
  - *Lesson:* To test whether "over streaks" or team totals runs are real, shuffle the outcome order many times and compare your streak statistic with that permutation distribution.
- **Applied to v4:** Randomization test: kept the same 3+ edge games but picked over/under by coin flip 5,000 times. Random sides averaged -4.54% ROI (the vig), 99th percentile +1.26%; v4's actual +8.26%. p = 0.0002. The model's side choice beats random far more than chance would.
- **Carries over:** Permutation test of a signal vs coin-flip sides works for any long/short rule.

### A08. Completely randomized vs randomized block design  ·  *No trend*
- **Formula / idea:** CRD: y_ij = μ + τ_i + ε_ij. RBD: y_ij = μ + τ_i + β_j + ε_ij (block β removes nuisance variation).
- **Paper:** Gadeken, D. L., & Casper, D. P. (2017). Evaluation of a high forage total mixed ration on the lactational performance of late lactation dairy cows. *Translational Animal Science, 1*(1), 108-115. https://doi.org/10.2527/tas2016.0011
  - *How they used it:* They blocked 20 Holstein cows by parity, milk yield and days in milk, then randomized two rations within blocks. The 80%-forage ration cut milk yield (24.1 vs 28.1 kg/d) and dry matter intake.
  - *Lesson:* Compare model variants within blocks of similar games (same season, same rest situation) so that block-to-block noise does not swamp the difference you want to measure.
- **Applied to v4:** Edge bucket as the 'treatment', points beaten the opener by as the response. CRD (no blocks): F=1.15, p=0.330. Blocking on season: bucket F=1.15, p=0.331; season block F=0.20, p=0.815. Mean points beaten by bucket: 3-4 +1.86, 4-5 +2.86, 5-6 +3.71, 6-8 +2.27, 8+ +5.03. Bigger edges don't beat the line by much more.

### A09. Latin square design  ·  *No trend*
- **Formula / idea:** Latin square: two blocking factors (rows, columns), each treatment once per row and column.
- **Paper:** Zanton, G. I. (2019). Effect of experimental design on responses to 2 concentrations of metabolizable protein in multiparous dairy cows. *Journal of Dairy Science, 102*(6), 5094-5108. https://doi.org/10.3168/jds.2018-15730
  - *How they used it:* The same two protein diets were tested on 54 cows with either a Latin square (16 cows, switched across periods) or a continuous randomized complete block design (38 cows). Most production results agreed between designs, but the Latin square showed carryover effects on milk fat.
  - *Lesson:* Designs that rotate treatments across periods (like reusing the same teams across stretches of a season) can leak carryover, so check whether effects persist from one period into the next.
- **Applied to v4:** Two blocking factors at once (season rows x weekday columns, the Latin-square idea; our data isn't a square so it's an additive two-block model). Over vs under bets after removing season and weekday: F=0.31, p=0.579; weekday p=0.668; season p=0.949. Weekday explains nothing about how well we beat the line.

### A10. Factorial design and interaction  ·  *No trend*
- **Formula / idea:** Factorial: all combinations of factor levels; interaction = effect of A depends on level of B.
- **Paper:** ISIS-2 (Second International Study of Infarct Survival) Collaborative Group. (1988). Randomised trial of intravenous streptokinase, oral aspirin, both, or neither among 17,187 cases of suspected acute myocardial infarction: ISIS-2. *The Lancet, 332*(8607), 349-360. https://doi.org/10.1016/S0140-6736(88)92833-4
  - *How they used it:* A 2x2 factorial trial randomized 17,187 patients to streptokinase or placebo and to aspirin or placebo, estimating both drugs and their combination in one trial. Each drug cut vascular mortality, and the combination did better than either alone.
  - *Lesson:* Test two model features together in a factorial grid (for example rest adjustment x pace adjustment), because their effects on totals may interact rather than simply add.
- **Applied to v4:** 2x2 factorial: bet direction (over/under) x both teams rested. Win %: over b2b 59.2% (n=294); over rested 56.0% (n=498); under b2b 56.6% (n=175); under rested 55.9% (n=479). Interaction p=0.303. A factorial look tests both factors and whether they combine, from one set of games.

### A11. ANCOVA / covariates  ·  *No trend*
- **Formula / idea:** ANCOVA: y = μ + τ_i + β(x − x̄) + ε; compares groups after adjusting for a covariate x.
- **Paper:** Vickers, A. J., & Altman, D. G. (2001). Analysing controlled trials with baseline and follow up measurements. *BMJ, 323*(7321), 1123. https://doi.org/10.1136/bmj.323.7321.1123
  - *How they used it:* Using a 52-patient trial of acupuncture for shoulder pain, they showed that ANCOVA (follow-up score adjusted for baseline) handles baseline imbalance and has more power than analysing change scores or follow-up scores alone.
  - *Lesson:* Regress the game total on the closing total as a covariate plus your features, rather than modelling raw totals or differences from the line alone.
- **Applied to v4:** ANCOVA: over vs under bets adjusted for how high the opener was. Unadjusted under-minus-over gap -0.53 pts (p=0.583); adjusted -0.06 (p=0.957); opener slope -0.047/pt (p=0.425). The covariate barely moves the comparison: opener height isn't hiding a direction effect.

### A12. Experimental unit vs measurement unit / pseudoreplication  ·  *Tool*
- **Formula / idea:** Experimental unit = what gets the treatment; measurement unit = what is measured. Treating sub-measurements as independent = pseudoreplication.
- **Paper:** Hurlbert, S. H. (1984). Pseudoreplication and the design of ecological field experiments. *Ecological Monographs, 54*(2), 187-211. https://doi.org/10.2307/1942661
  - *How they used it:* He reviewed 176 published ecological experiments and found that many (about half of those that used inferential statistics) treated repeated measurements on the same unit as independent replicates.
  - *Lesson:* Each game is one unit, so quarter-level or possession-level rows from the same game are not independent replicates of your total edge.
- **Applied to v4:** The experimental unit is the game; the two team scores are measurement units inside it. Within a game the two teams' scores (each vs half the model total) correlate r=+0.13 (shared pace, refs, overtime). Treating 6,408 team scores as independent would double the sample and shrink standard errors falsely (pseudoreplication). SD of game total vs model 18.4 is larger than sqrt(2)x team SD would give if they were independent (17.3).


## Describing data

### A13. Bar charts / categorical summaries  ·  *Tool*
- **Formula / idea:** Bar chart: counts or percentages per category.
- **Paper:** Cleveland, W. S., & McGill, R. (1984). Graphical perception: Theory, experimentation, and application to the development of graphical methods. *Journal of the American Statistical Association, 79*(387), 531-554. https://www.jstor.org/stable/2288400
  - *How they used it:* In perception experiments, they ranked how accurately people decode graphs. Position along a common scale (as in bar and dot charts) was judged best, ahead of angle, area and shading.
  - *Lesson:* Show over/under hit rates by category (rest, month, line bucket) as dot or bar charts on a common axis, not pies or colour maps.
- **Applied to v4:** Bar chart counts, all 3,204 games: no bet 1756, win 820, loss 626, push 2. Pushes are 0.1% of edge-3+ games (NBA totals land on a half-point line rarely, unlike NFL key numbers).

### A14. Pie charts  ·  *Tool*
- **Formula / idea:** Pie chart: category shares of a whole (sum to 100%).
- **Paper:** Spence, I., & Lewandowsky, S. (1991). Displaying proportions and percentages. *Applied Cognitive Psychology, 5*(1), 61-77. https://doi.org/10.1002/acp.2350050106
  - *How they used it:* In experiments where people judged proportions from pie charts, bar charts and tables, pies did about as well as bars for part-to-whole judgments, contrary to common advice.
  - *Lesson:* A pie is acceptable for one part-of-whole split (such as the share of bets on overs), but use bars to compare that split across many games.
- **Applied to v4:** Pie-chart shares of bets: overs 55%, unders 45%; by season overs 2024: 58%, 2025: 50%, 2026: 55%. A part-of-whole view shows v4 is not just an 'always over' model (the old stack bet overs 95% of the time).

### A15. Histogram & distribution shape (skewness, kurtosis)  ·  *Confirmed out of sample*
- **Formula / idea:** Histogram; shape: modality, skewness, tails.
- **Paper:** Mandelbrot, B. (1963). The variation of certain speculative prices. *The Journal of Business, 36*(4), 394-419. https://doi.org/10.1086/294632
  - *How they used it:* Using histograms of cotton price changes, he showed that they are far more peaked and fat-tailed than a normal distribution, and proposed stable Paretian laws instead.
  - *Lesson:* Plot the histogram of (actual total - closing total) and check its tails, because overtime and blowouts create more extreme misses than a normal curve predicts.
- **Applied to v4:** Histogram of (final total - opener): unimodal, mean +0.42, skewness +0.15, excess kurtosis +0.03. Roughly symmetric and close to bell-shaped; slight heavy right tail from overtime games (OT adds ~20 pts).

### A16. Relative frequency histogram / density  ·  *Tool*
- **Formula / idea:** Relative frequency = count / n; relative frequency histogram approximates the density.
- **Paper:** Freedman, D., & Diaconis, P. (1981). On the histogram as a density estimator: L2 theory. *Zeitschrift für Wahrscheinlichkeitstheorie und Verwandte Gebiete, 57*(4), 453-476. https://doi.org/10.1007/BF01025868
  - *How they used it:* They derived the bin width that minimizes integrated squared error when a histogram estimates a density. This gives the rule of a bin width of about 2·IQR·n^(-1/3).
  - *Lesson:* Choose histogram bins for total residuals with a rule such as Freedman-Diaconis, so the shape you read is not an artefact of the bin width.
- **Applied to v4:** Relative frequencies of |final - closing total|: under 5 pts 21.4%, 5-10 19.5%, 10-20 32.6%, 20+ 26.5%. Same for v4 vs actual: under 5 21.9%, 20+ 26.7%. Even the best line misses by 10+ about half the time: single-game noise is huge.

### A17. Time-series plot / trends  ·  *Suggestive (partly replicates)*
- **Formula / idea:** Time-series plot: value vs time to show trend, seasonality, drift.
- **Paper:** Berry, S. M., Reese, C. S., & Larkey, P. D. (1999). Bridging different eras in sports. *Journal of the American Statistical Association, 94*(447), 661-676. https://www.vanderbilt.edu/psychological_sciences/graduate/programs/quantitative-methods/quantitative-content/berry_reese_larkey_1999.pdf (author-hosted copy; DOI not confirmed)
  - *How they used it:* They modelled hockey, golf and baseball careers (for example NHL forwards 1948-1996) and plotted estimated year effects over time. NHL scoring rose after 1969, peaked in the 1970s and early 1980s, and declined from 1983.
  - *Lesson:* Plot league-average totals by season and month before modelling, because NBA scoring levels drift (pace and 3-point eras), so old seasons need an era adjustment.
- **Applied to v4:** Time series by month (Nov->Apr; October drops out because both teams need 10+ games), final minus opener: Nov +0.41, Dec +1.42, Jan -1.63, Feb -0.35, Mar +0.82, Apr +3.42. Cumulative units for v4 bets rose fairly steadily (min -22.4u, max +120.8u, final +119.5u); worst drawdown 21.4u.

### A18. Mean, median, mode, trimmed mean  ·  *Tool*
- **Formula / idea:** Mean x̄ = Σx/n; median = middle value; mode = most common; trimmed mean drops top/bottom k%.
- **Paper:** Stigler, S. M. (1977). Do robust estimators work with real data? *The Annals of Statistics, 5*(6), 1055-1098. https://doi.org/10.1214/aos/1176343997
  - *How they used it:* He compared 11 location estimators on historical scientific data sets (solar parallax, mean density of the earth, speed of light) with known true values. Light trimming beat the mean slightly, but the plain mean held up well against newer estimators.
  - *Lesson:* A lightly trimmed mean of recent team scoring can resist one overtime or garbage-time outlier without throwing away much information.
- **Applied to v4:** Center of (final - opener): mean +0.42, median +0.50, 10% trimmed mean +0.16, mode (rounded) -4. For v4 bets' points beaten: mean +2.89, median +3.00, trimmed +2.92. Mean and trimmed agree, so the edge isn't a few blowouts.

### A19. Percentiles / quantiles  ·  *Tool*
- **Formula / idea:** pth percentile: p% of data at or below it; quartiles Q1, Q2, Q3.
- **Paper:** Koenker, R., & Bassett, G., Jr. (1978). Regression quantiles. *Econometrica, 46*(1), 33-50. https://www.jstor.org/stable/1913643
  - *How they used it:* They extended sample quantiles to linear models (regression quantiles). The resulting estimators are nearly as efficient as least squares under normal errors and much better under heavy-tailed errors.
  - *Lesson:* Model the median and other quantiles of the total, not just the mean, because the over/under bet turns on the median relative to the line.
- **Applied to v4:** Quantiles of (final - v4): 5th -29.1, 25th -12.8, median -0.4, 75th +12.3, 95th +31.3. A 90% range for a game total is about v4 -29 to +31 pts. Edge percentiles: 3 pts is the 55th percentile of |edge|.

### A20. Q-Q plot / normality (Shapiro-Wilk)  ·  *Suggestive*
- **Formula / idea:** Q-Q plot: sample quantiles vs normal quantiles; straight line = normal. Shapiro-Wilk W tests it.
- **Paper:** Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality (complete samples). *Biometrika, 52*(3-4), 591-611. https://doi.org/10.1093/biomet/52.3-4.591
  - *How they used it:* They introduced the W statistic, which measures how closely ordered sample values line up with expected normal order statistics (the Q-Q plot idea). In comparisons with other normality tests it had good power.
  - *Lesson:* Check whether total residuals are normal with a Q-Q plot first. With thousands of games, Shapiro-Wilk will flag trivial departures, so judge by the size of the departure.
- **Applied to v4:** Q-Q of v4 errors vs normal: Q-Q correlation 0.9992; Shapiro-Wilk (2,000-game sample) W=0.9979, p=0.0116. Close to normal in the middle, tails slightly heavier (overtime, blowouts). Normal-based win probabilities are fine for typical edges, a bit off in the extremes.

### A21. IQR, boxplot, outlier fences  ·  *Tool*
- **Formula / idea:** IQR = Q3 − Q1; inner fences Q1 − 1.5·IQR, Q3 + 1.5·IQR; points outside = potential outliers.
- **Paper:** Hoaglin, D. C., Iglewicz, B., & Tukey, J. W. (1986). Performance of some resistant rules for outlier labeling. *Journal of the American Statistical Association, 81*(396), 991-999. https://doi.org/10.2307/2289073
  - *How they used it:* They worked out how often the boxplot fence rule (quartiles ± k·IQR) labels points "outside" in clean normal samples of different sizes, so analysts know the false-alarm rate.
  - *Lesson:* Flag games outside 1.5·IQR of residuals for review (overtime, injuries, data errors), but expect some flags by chance alone and do not delete them automatically.
- **Applied to v4:** Boxplot of (final - v4): IQR 25.1, fences -50.5 / +50.0; 24 outlier games (0.7%), 79% of them high (overtime-type). v4 bets in outlier games: 13. Outliers aren't removable (they're real games), but they're why an over bet carries extra right-tail chance.

### A22. Variance and standard deviation  ·  *Tool*
- **Formula / idea:** s² = Σ(x − x̄)²/(n − 1); s = √s².
- **Paper:** Markowitz, H. (1952). Portfolio selection. *The Journal of Finance, 7*(1), 77-91. https://doi.org/10.1111/j.1540-6261.1952.tb01525.x
  - *How they used it:* He defined investment risk as the variance of portfolio return and showed how covariances between assets set the trade-off between expected return and variance.
  - *Lesson:* Track the variance of your bankroll returns, not only the win rate, because correlated bets on the same night raise variance.
- **Applied to v4:** SD of (final - v4) 18.40, vs opener 18.45, vs close 17.94. By season (v4): 2024 18.34, 2025 18.08, 2026 18.78. Our model is about as noisy as the opener; the edge is in a slightly different center, not a smaller spread.

### A23. Empirical rule (68-95-99.7)  ·  *Tool*
- **Formula / idea:** Mound-shaped data: ~68% within x̄ ± s, ~95% within ± 2s, ~99.7% within ± 3s.
- **Paper:** Pukelsheim, F. (1994). The three sigma rule. *The American Statistician, 48*(2), 88-91. https://doi.org/10.2307/2684253
  - *How they used it:* Using the Vysochanskii-Petunin inequality, he proved that any unimodal distribution keeps at least about 95% of its mass within 3 standard deviations, so the 3-sigma rule holds well beyond the normal case.
  - *Lesson:* If residual SD is about 18 points, nearly all games should land within ±54 of your projection whatever the shape, but the 68% and 95% bands are exact only if residuals are normal.
- **Applied to v4:** Empirical rule on (final - v4): within 1 SD 69.2% (rule 68%), 2 SD 95.3% (95%), 3 SD 99.59% (99.7%). Very close to a bell curve; 1 SD of a game total is about 18 pts.

### A24. Coefficient of variation  ·  *Tool*
- **Formula / idea:** CV = s / x̄ (relative variability).
- **Paper:** Hopkins, W. G., Hawley, J. A., & Burke, L. M. (1999). Design and analysis of research on sport performance enhancement. *Medicine & Science in Sports & Exercise, 31*(3), 472-485. https://doi.org/10.1097/00005768-199903000-00018
  - *How they used it:* They expressed an elite athlete's competition-to-competition variability as a within-athlete coefficient of variation. They set the smallest worthwhile performance gain as a fraction (about 0.4-0.7) of that variation and derived the sample sizes needed to detect it.
  - *Lesson:* Express a team's game-to-game scoring variability as a CV, so you can compare teams of different pace and judge whether a projected edge is large relative to normal noise.
- **Applied to v4:** Coefficient of variation: game total 8.8%, single team score 11.2%, opener 3.8%, v4 3.4%. Totals are relatively stable (8%) but a 3-pt edge is only 1.3% of a total: tiny compared with the game-to-game spread.

### A25. Side-by-side boxplots comparing groups  ·  *Suggestive (partly replicates)*
- **Formula / idea:** Side-by-side boxplots compare center and spread across groups.
- **Paper:** McGill, R., Tukey, J. W., & Larsen, W. A. (1978). Variations of box plots. *The American Statistician, 32*(1), 12-16. https://doi.org/10.2307/2683468
  - *How they used it:* They introduced variable-width box plots (width showing group size) and notched box plots (notches giving a rough test of whether two medians differ) for comparing several groups side by side.
  - *Lesson:* Put residuals side by side by rest category or by referee crew in notched box plots, to see whether medians really differ before adding a feature.
- **Applied to v4:** Side-by-side boxplots of (final - opener) by month: medians Nov +0.0, Dec +1.5, Jan -2.5, Feb +0.5, Mar -0.5, Apr +3.0. Boxes overlap heavily; no month is obviously different by eye (tested formally in B59).

### A26. Contingency tables / stacked bar  ·  *Tool*
- **Formula / idea:** Contingency table: counts for two categorical variables; stacked/grouped bar charts.
- **Paper:** Nevill, A. M., Balmer, N. J., & Williams, A. M. (2002). The influence of crowd noise and experience upon refereeing decisions in football. *Psychology of Sport and Exercise, 3*(4), 261-272. https://wlv.openrepository.com/items/2a37e72f-d492-4e51-aaec-76f45dcba34f (DOI not confirmed)
  - *How they used it:* Qualified referees judged videotaped soccer challenges with or without crowd noise, and the authors cross-tabulated decisions by condition (then used logistic regression). Referees hearing crowd noise called about 15.5% fewer fouls against the home team.
  - *Lesson:* Cross-tabulate over/under results by a categorical factor (home crowd, referee crew, back-to-back) and test the table before believing a split.
- **Applied to v4:** Contingency table, v4 bets, wins/losses by season and direction: 2024: over 186-148, under 133-107; 2025: over 128-94, under 117-101; 2026: over 139-97, under 117-79

### A27. Scatterplot & Pearson correlation  ·  *Confirmed (in-sample)*
- **Formula / idea:** r = Σ(x − x̄)(y − ȳ) / √[Σ(x − x̄)² Σ(y − ȳ)²], −1 ≤ r ≤ 1.
- **Paper:** Hall, S., Szymanski, S., & Zimbalist, A. (2002). Testing causality between team performance and payroll: The cases of Major League Baseball and English soccer. *Journal of Sports Economics, 3*(2), 149-168. https://doi.org/10.1177/152700250200300204
  - *How they used it:* Using MLB payrolls (1980-2000) and English soccer wage data, they found that the payroll-win correlation in MLB rose in the 1990s, yet Granger tests showed no causality from payroll to performance in MLB (unlike soccer).
  - *Lesson:* A strong correlation between a team stat and totals does not tell you direction or predictiveness, so test whether the stat predicts future totals.
- **Applied to v4:** Scatter of v4 edge vs (final - opener): r=+0.125 (p=1.3e-12, n=3204). Plain Model 1 edge: r=+0.083. Small r but real: a few % of the noise is predictable, which is all a bettor needs at -110.

### A28. Zero/low correlation does not mean no relationship (Anscombe)  ·  *No trend*
- **Formula / idea:** r measures only LINEAR association; r ≈ 0 can hide a strong curved pattern.
- **Paper:** Anscombe, F. J. (1973). Graphs in statistical analysis. *The American Statistician, 27*(1), 17-21. https://doi.org/10.1080/00031305.1973.10478966
  - *How they used it:* He built four data sets with identical means, variances, correlations and regression lines whose scatterplots look completely different (linear, curved, outlier-driven).
  - *Lesson:* Always plot each feature against total residuals, because a near-zero r can hide a curved effect (for example extreme pace at both ends).
- **Applied to v4:** Zero (or small) r doesn't mean no relationship: mean (final - opener) by edge decile: -7.0->-3.6, -3.9->-1.6, -2.5->-1.9, -1.3->+0.8, -0.3->-0.2, +0.8->+0.2, +1.8->+1.5, +3.0->+1.9, +4.6->+3.9, +7.8->+3.3. Quadratic term p=0.510; |edge| vs |v4 error| r=+0.016 (p=0.360). The relationship is roughly linear in the middle and flattens at extremes.


## Probability and sampling distributions

### A29. Probability rules, complement, break-even probability  ·  *Tool*
- **Formula / idea:** 0 ≤ P(E) ≤ 1; P(Eᶜ) = 1 − P(E); P(A ∪ B) = P(A) + P(B) − P(A ∩ B).
- **Paper:** Vergin, R. C., & Scriabin, M. (1978). Winning strategies for wagering on National Football League games. *Management Science, 24*(8), 809-818. https://doi.org/10.1287/mnsc.24.8.809
  - *How they used it:* Using NFL point spreads from 1969-1974, they tested betting rules for biases and found some that won often enough to exceed the break-even rate required after the bookmaker's fee.
  - *Lesson:* At -110 you must win at least 110/210 ≈ 52.4% of over/under bets to break even, so judge any edge against that bar, not 50%.
- **Applied to v4:** Break-even win probability at -110 = 110/210 = 52.38%. Complement: P(lose) = 1 - P(win). v4 bets won 56.7%, so P(lose) 43.3%. P(at least one loss in a 5-bet night) = 1 - 0.567^5 = 94.1%: losing nights are normal even with an edge.

### A30. Intransitive (nontransitive) dice / rankings  ·  *No trend*
- **Formula / idea:** Nontransitive dice: A beats B, B beats C, C beats A (pairwise 'better' need not be transitive).
- **Paper:** Savage, R. P., Jr. (1994). The paradox of nontransitive dice. *The American Mathematical Monthly, 101*(5), 429-436. DOI not confirmed (citation confirmed via reference list at https://www.math.uci.edu/~mfinkels/dice9.pdf)
  - *How they used it:* He analysed sets of dice where A beats B, B beats C and C beats A, each with probability above 1/2, and explained when such cycles arise.
  - *Lesson:* "Team A beats B and B beats C" does not mean A beats C, because matchup-specific pace and style effects can make power ratings non-transitive.
- **Applied to v4:** Head-to-head 'which forecast is closer to the final' (share of games the first wins): M1 vs v4 48.3%, M1 vs simple 56.1%, M1 vs open 49.8%, simple vs v4 44.3%, open vs v4 48.5%, open vs simple 54.2%. Check for a cycle (A>B, B>C, C>A): none here, so the ranking is transitive. With nontransitive dice it wouldn't be, which is why 'beats X head-to-head' isn't the same as 'best'.

### A31. Simpson's paradox  ·  *No trend*
- **Formula / idea:** Simpson's paradox: a relationship within every group reverses when groups are pooled.
- **Paper:** Bickel, P. J., Hammel, E. A., & O'Connell, J. W. (1975). Sex bias in graduate admissions: Data from Berkeley. *Science, 187*(4175), 398-404. https://doi.org/10.1126/science.187.4175.398
  - *How they used it:* Aggregate fall-1973 Berkeley admissions seemed to favour men, but department-by-department tables showed no bias against women. The aggregate gap came from women applying to more selective departments.
  - *Lesson:* An over trend in pooled data can reverse within seasons or line ranges, so check your edge within strata (such as total buckets) and not only overall.
- **Applied to v4:** Simpson's paradox check. Pooled: overs 57.2% vs unders 56.1%. By season over-under: 2024 +0.3%, 2025 +4.0%, 2026 -0.8%. Seasons that reverse the pooled direction: [2026]. v4 vs plain Model 1 win rate by season: 2024 55.6% vs 53.5%, 2025 55.7% vs 50.8%, 2026 59.3% vs 56.1%. v4 leads in every season and pooled, so no paradox there.

### A32. Conditional probability  ·  *Confirmed (in-sample)*
- **Formula / idea:** P(A | B) = P(A ∩ B) / P(B).
- **Paper:** Stern, H. (1991). On the probability of winning a football game. *The American Statistician, 45*(3), 179-183. https://doi.org/10.1080/00031305.1991.10475798 *(citation details partly unverified)*
  - *How they used it:* Using NFL games, he estimated P(favourite wins \
  - *Lesson:* point spread) both empirically and by treating margin minus spread as normal (SD about 14 points), producing a table converting spreads to win probabilities.
- **Applied to v4:** Conditional probability: P(win | line moved toward us) = 61.2%, P(win | no move) = 52.3%, P(win | moved against) = 48.1%; P(line moves toward us | v4 bet) = 63.6%. The live rule (pass after a 0.5+ move against) is a conditional-probability rule.

### A33. Independence of events / hot hand  ·  *No trend*  ⇄
- **Formula / idea:** Independent iff P(A ∩ B) = P(A)P(B), i.e. P(A | B) = P(A).
- **Paper:** Miller, J. B., & Sanjurjo, A. (2018). Surprised by the hot hand fallacy? A truth in the law of small numbers. *Econometrica, 86*(6), 2019-2047. https://doi.org/10.3982/ECTA14943
  - *How they used it:* They showed that the standard measure (hit rate after streaks within finite sequences) is biased toward finding independence. After correcting this bias in the Gilovich et al. shooting data, the evidence reversed toward a hot hand.
  - *Lesson:* Testing whether over results are independent from game to game has subtle finite-sample biases, so simulate the null rather than trusting naive streak rates.
- **Applied to v4:** Independence: correlation between results of two bets on the same night r=+0.015 (2535 pairs). Runs test on the bet sequence: 710 runs vs 711 expected, z=-0.05, p=0.958. No hot or cold streaks beyond chance: a losing week says nothing about the next bet.
- **Carries over:** Test any strategy for streakiness before sizing on 'hot' runs.

### A34. Multiplication law (joint probability, parlays)  ·  *Tool*
- **Formula / idea:** Multiplication law: P(A ∩ B) = P(A | B)P(B); = P(A)P(B) if independent.
- **Paper:** Snowberg, E., & Wolfers, J. (2010). Explaining the favorite-long shot bias: Is it risk-love or misperceptions? *Journal of Political Economy, 118*(4), 723-746. https://doi.org/10.1086/655844
  - *How they used it:* Using US horse-race data, they built prices for compound bets (exacta, quinella, trifecta) from win-pool probabilities multiplied through. Comparing these with actual exotic prices showed that probability misperception, not risk-love, explains the favourite-longshot bias.
  - *Lesson:* A two-leg over parlay pays as if legs were independent (p1·p2). If legs are correlated (same night or same team pace) or your p is mis-estimated, the multiplication law amplifies the error.
- **Applied to v4:** Multiplication law: if independent, P(two bets same night both win) = 0.567^2 = 32.2%; observed 32.2%. A 2-leg parlay pays +264 (needs 27.5%); at our win rate P(both)=32.2%, EV per unit +0.171 vs two straight bets +0.165.

### A35. Sensitivity and specificity  ·  *Tool*
- **Formula / idea:** Sensitivity = P(+ | condition); specificity = P(− | no condition).
- **Paper:** Altman, D. G., & Bland, J. M. (1994). Diagnostic tests 1: Sensitivity and specificity. *BMJ, 308*(6943), 1552. https://www.bmj.com/content/308/6943/1552 (DOI not confirmed)
  - *How they used it:* Using liver scan results checked against pathology as the true diagnosis, they showed how to compute the proportion of true positives detected (sensitivity) and true negatives detected (specificity).
  - *Lesson:* Treat a "bet signal" like a diagnostic test: how many true overs it flags (sensitivity), and how often it stays quiet on unders (specificity).
- **Applied to v4:** Sensitivity/specificity, treating 'v4 above the opener' as a test for 'game goes over': sensitivity 57.4%, specificity 52.7%. With the 3-pt threshold sensitivity drops to 28.2% (we flag only a fraction of overs) but precision rises. Same trade-off as a medical screen: a stricter cutoff catches fewer, but surer, cases.

### A36. Bayes' formula / Bayesian updating  ·  *Tool*
- **Formula / idea:** Bayes: P(A | B) = P(B | A)P(A) / [P(B | A)P(A) + P(B | Aᶜ)P(Aᶜ)].
- **Paper:** Glickman, M. E., & Stern, H. S. (1998). A state-space model for National Football League scores. *Journal of the American Statistical Association, 93*(441), 25-35. https://doi.org/10.2307/2669599
  - *How they used it:* They fitted a Bayesian state-space model to NFL scores (1988-1993) in which team strengths evolve week to week and season to season, updating posteriors by simulation. Out-of-sample predictions for late-1993 games were competitive with the Las Vegas line.
  - *Lesson:* Update team offensive and defensive ratings with Bayes as games arrive, shrinking early-season results toward priors instead of overreacting to a few games.
- **Applied to v4:** Bayes: prior P(over) = 50.2%; P(edge>=3 | over) and P(edge>=3 | under) give posterior P(over | v4 says over by 3+) = 57.1%. Bayesian view of the whole record: flat prior + 820-626 gives posterior mean win rate 56.7%, 95% credible interval 54.1%-59.2%, P(true rate > break-even) = 0.9995.

### A37. Expected value & variance of a discrete random variable (EV of a bet)  ·  *Tool*  ⇄
- **Formula / idea:** E[X] = Σ x·p(x); Var(X) = Σ (x − μ)²·p(x).
- **Paper:** Kelly, J. L., Jr. (1956). A new interpretation of information rate. *Bell System Technical Journal, 35*(4), 917-926. https://archive.org/details/bstj35-4-917 (DOI not confirmed)
  - *How they used it:* He modelled a gambler with a private information edge and showed that betting a fixed fraction of wealth, set by the edge and the odds, maximizes expected log growth of the bankroll.
  - *Lesson:* A positive-EV over still has high variance per bet, so size stakes from your estimated edge (fractional Kelly) rather than flat-betting on feel.
- **Applied to v4:** Profit per 1-unit bet X = +0.909 or -1. At p=0.567: E[X] = +0.0826u, Var = 0.895, SD = 0.946u. The SD is ~11x the mean, so you need hundreds of bets to see the edge. Full Kelly stake would be 9.1% of bankroll; the project's 1% flat unit is ~0.11 Kelly, which is conservative.
- **Carries over:** Kelly / EV math for any repeated favorable bet.

### A38. Binomial distribution  ·  *Confirmed (in-sample)*
- **Formula / idea:** Binomial: P(X = k) = C(n,k)pᵏ(1 − p)ⁿ⁻ᵏ; μ = np, σ² = np(1 − p).
- **Paper:** Mosteller, F. (1952). The World Series competition. *Journal of the American Statistical Association, 47*(259), 355-380. DOI not confirmed (citation confirmed via JASA reference lists)
  - *How they used it:* He modelled World Series games as independent trials with a fixed win probability and used binomial-based series probabilities on historical Series results to ask how often the better team wins a 7-game series.
  - *Lesson:* Over a 100-bet sample the number of wins is roughly Binomial(100, p), so a 56-44 record is well within what a 52.4% bettor can produce by luck.
- **Applied to v4:** Binomial: wins ~ Binomial(n=1446, p). Under break-even p=0.5238, expected 757 wins (SD 19.0); observed 820. P(X >= 820) = 0.00053. At p=0.50 it's 1.9e-07.

### A39. Poisson distribution / overdispersion  ·  *Tool*
- **Formula / idea:** Poisson: P(Y = k) = e^(−λ)λᵏ/k!; μ = σ² = λ; rate scaling λ = r·(t/t₀).
- **Paper:** Maher, M. J. (1982). Modelling association football scores. *Statistica Neerlandica, 36*(3), 109-118. https://doi.org/10.1111/j.1467-9574.1982.tb00782.x
  - *How they used it:* He fitted independent Poisson models with team attack and defence parameters to English league scores and checked goodness of fit. Poisson fitted reasonably well, and a bivariate Poisson (correlation about 0.2) improved it.
  - *Lesson:* NBA points are not Poisson, since their variance exceeds the mean and the two teams' scores are correlated through pace, so model the variance and the correlation directly.
- **Applied to v4:** Poisson: v4 bets per game night mean 3.39, variance 3.80 (dispersion 1.12; Poisson = 1). P(0 bets on a night) Poisson 3.4% vs actual 4.4%. Team points: mean 114.5, variance 168 (ratio 1.47). Points are made in 1-3 pt chunks, so a team score isn't Poisson; a possessions model is the better building block.

### A40. Poisson approximation to binomial (rare events)  ·  *Tool*
- **Formula / idea:** Binomial(n, p) ≈ Poisson(λ = np) when n large and p small.
- **Paper:** Hanley, J. A., & Bhatnagar, S. (2022). The "Poisson" distribution: History, reenactments, adaptations. *The American Statistician, 76*(4), 363-371. https://doi.org/10.1080/00031305.2022.2046159
  - *How they used it:* They traced the Poisson law from its derivation as a limit of the binomial for rare events through original biological and physical applications, and showed how to handle extra-Poisson variation in counts of human behaviour.
  - *Lesson:* Rare in-game events (technical fouls, overtime periods, ejections) can be treated as approximately Poisson, but check for extra variation by team or referee.
- **Applied to v4:** Poisson approximation to the binomial for rare events: pushes happen in 0.14% of edge-3+ games (whole-number openers only). For a 100-bet stretch, pushes ~ Binomial(100, 0.0014) ~ Poisson(0.14): P(0 pushes) binomial 0.871 vs Poisson 0.871. Near-identical: the shortcut works when p is small.

### A41. Continuous densities, probability as area  ·  *Warning*  ⇄
- **Formula / idea:** Continuous X: P(a ≤ X ≤ b) = area under the density f(x) between a and b.
- **Paper:** Stern, H. S. (1994). A Brownian motion model for the progress of sports scores. *Journal of the American Statistical Association, 89*(427), 1128-1134. https://doi.org/10.1080/01621459.1994.10476851
  - *How they used it:* He modelled the home-minus-away score as Brownian motion with drift and fitted it to 493 NBA games from 1991-92. The win probability at any moment is the area under a normal density beyond the current lead.
  - *Lesson:* Your probability of an over is the area under the predicted density of the total above the line, so the spread of that density matters as much as its centre.
- **Applied to v4:** Probability as area under a density: with a normal curve centered on v4 (SD 18.4), P(over) = area above the opener. For our bets the curve says average P(win) = 61.8%; actual 56.7%. A 3-pt edge = 6.5% of extra area, a 6-pt edge 12.8%. The curve is too confident: it treats v4 as the truth, but the opener also knows things v4 doesn't. Real win probability sits between the curve and 50%, the same shrinkage the regression slope shows (B76).
- **Carries over:** Normal-curve win probabilities centered on your own forecast overstate confidence whenever the market also has information.

### A42. Normal distribution / z-scores of game outcomes  ·  *Tool*
- **Formula / idea:** X ~ N(μ, σ²); Z = (X − μ)/σ ~ N(0, 1).
- **Paper:** Harville, D. (1980). Predictions for National Football League games via linear-model methodology. *Journal of the American Statistical Association, 75*(371), 516-524. https://doi.org/10.1080/01621459.1980.10477504
  - *How they used it:* He predicted NFL score differences (1,320 games, 1971-1977) with a mixed linear model that had team-year effects (autoregressive across years) and home advantage. Mean absolute error was 10.68 versus 10.49 for bookmakers.
  - *Lesson:* Standardize residuals as z = (actual total - projected total)/SD. If the z-scores are not roughly standard normal, your probability conversions are off.
- **Applied to v4:** z-scores: the record is z = (wins - n*0.5238)/sqrt(n*0.5238*0.4762) = +3.29. For games: z of each final vs v4 = (final - v4)/18.4; 4.6% of games are beyond |z|=2 (normal 4.6%).

### A43. Normal quantiles  ·  *Tool*
- **Formula / idea:** Quantile x_p = μ + z_p·σ, where P(Z ≤ z_p) = p.
- **Paper:** Jorion, P. (1996). Risk2: Measuring the risk in value at risk. *Financial Analysts Journal, 52*(6), 47-56. https://doi.org/10.2469/faj.v52.n6.2039
  - *How they used it:* He analysed value at risk, a loss quantile computed (under normality) as a normal quantile times portfolio SD, and showed that VaR estimates carry sampling error that must be measured.
  - *Lesson:* A 95% band for a total is projection ± 1.96·SD only if residuals are normal, and SD is itself estimated with error, so the band is wider than it looks.
- **Applied to v4:** Normal quantiles: with v4 as the mean and SD 18.4, the total exceeded only 5% of the time is v4 + z0.95*SD = v4 + 30.3. Observed share of games above that: 5.7%. For a 60% over chance the line would need to be -4.7 pts from v4; our 3-pt bar is only ~56% by the curve.

### A44. Random sampling / bootstrap resampling  ·  *Tool*
- **Formula / idea:** Random sample: every subset of size n equally likely.
- **Paper:** Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *The Annals of Statistics, 7*(1), 1-26. https://doi.org/10.1214/aos/1176344552
  - *How they used it:* He introduced the bootstrap: resample the observed data with replacement to approximate the sampling distribution of a statistic, and showed that it generalizes the jackknife.
  - *Lesson:* Bootstrap your backtest by resampling games (or whole days, to keep correlation) to get a confidence interval on ROI.
- **Applied to v4:** Random samples of 500 bets (drawn without replacement, 4,000 times): ROI ranged +1.6% to +15.3% (95%); 0.9% of 500-bet samples lost money. Resampling from our own 1,446 bets understates the risk (it assumes the true rate IS 56.7%); B45 shows the more honest view: one season is only ~1.9 SEs from zero.

### A45. Sampling distribution of the mean / standard error  ·  *Warning*
- **Formula / idea:** Sampling distribution of x̄: mean μ, standard error σ/√n.
- **Paper:** Tversky, A., & Kahneman, D. (1971). Belief in the law of small numbers. *Psychological Bulletin, 76*(2), 105-110. https://doi.org/10.1037/h0031322
  - *How they used it:* Surveying research psychologists, they found that people treat small samples as highly representative of the population, underestimating sampling variability and overestimating the odds that a result replicates.
  - *Lesson:* The standard error of a hit rate is about √(p(1-p)/n), roughly ±5 points at n = 100, so do not read a 10-game run as signal.
- **Applied to v4:** Sampling distribution of the mean profit: SE = SD/sqrt(n) = 0.946/sqrt(1446) = 0.0249u. Per season (~482 bets) SE = 0.043u, vs the edge +0.083u: one season's ROI is within ~1.9 SEs of zero.

### A46. Central limit theorem  ·  *Tool*
- **Formula / idea:** CLT: x̄ (and sums) approximately normal for large n (n ≥ 30), whatever the population shape.
- **Paper:** Fama, E. F. (1965). The behavior of stock-market prices. *The Journal of Business, 38*(1), 34-105. https://doi.org/10.1086/294743
  - *How they used it:* Using daily returns of the 30 Dow Jones stocks, he found fat-tailed, leptokurtic distributions consistent with stable Paretian laws. This is the case where the finite-variance CLT does not give normal sums.
  - *Lesson:* The CLT makes average ROI over many bets roughly normal only if per-bet outcomes have finite variance and are not heavily dependent, so check before using normal intervals on profit.
- **Applied to v4:** CLT: units won per 50-bet block (28 blocks) have mean +4.14, SD 8.17 (theory 6.69); skewness -0.63, Shapiro p=0.22. The observed SD is larger than theory, a hint the win rate isn't constant over time (hot and cold model stretches, not streaky bets). Even though each bet is a two-valued +0.91/-1, sums of 50 are already close to normal: CLT lets us use normal math for season totals.

### A47. Normal approximation to binomial with continuity correction  ·  *Tool*
- **Formula / idea:** Normal approx to binomial if np ≥ 10, n(1 − p) ≥ 10: P(X ≤ k) ≈ P(Z ≤ (k + 0.5 − np)/√(np(1 − p))).
- **Paper:** Emura, T., & Liao, Y. T. (2018). Critical review and comparison of continuity correction methods: The normal approximation to the binomial distribution. *Communications in Statistics - Simulation and Computation, 47*(8), 2266-2285. https://doi.org/10.1080/03610918.2017.1341527
  - *How they used it:* They compared Yates' ±0.5 continuity correction with Cressie's finely tuned correction for approximating binomial probabilities and confidence limits, with industrial and medical data examples. Yates' correction performed poorly in extreme tails.
  - *Lesson:* When testing whether a W-L record beats 52.4%, use the ±0.5 correction (or an exact binomial test), especially for small samples or tail p-values.
- **Applied to v4:** Normal approximation with continuity correction: P(X >= 820) ~ P(Z >= (820-0.5-757.4)/18.99) = 0.00054; exact binomial 0.00053. np and n(1-p) are both > 10, so the approximation is valid.


## Estimation and tests for one or two populations

### B48. Point estimation  ·  *Tool*
- **Formula / idea:** Point estimate: a single number (x̄, p̂) for a parameter.
- **Paper:** Efron, B., & Morris, C. (1975). Data analysis using Stein's estimator and its generalizations. *Journal of the American Statistical Association, 70*(350), 311-319. https://doi.org/10.1080/01621459.1975.10479864
  - *How they used it:* Took the batting averages of 18 MLB players after their first 45 at-bats of 1970 and predicted their rest-of-season averages. Shrinking each player toward the group mean (James-Stein) cut total squared prediction error from 17.56 (raw averages) to 5.01, and it beat the raw average for 15 of 18 players.
  - *Lesson:* Early-season team pace and efficiency numbers are noisy point estimates, so shrink them toward the league mean (or a prior) before you compare a projected total to the line.
- **Applied to v4:** Point estimates: win rate p-hat = 820/1446 = 0.5671; ROI = +0.0826u/bet; v4 bias (mean final - v4) = +0.12 pts; opener bias +0.42.

### B49. Confidence interval for a mean (t)  ·  *Tool*
- **Formula / idea:** CI for μ: x̄ ± t(n−1, 1−α/2)·s/√n.
- **Paper:** Hopkins, W. G. (2000). Measures of reliability in sports medicine and science. *Sports Medicine, 30*(1), 1-15. https://doi.org/10.2165/00007256-200030010-00001
  - *How they used it:* Showed how to report test-retest data in sport science as a within-athlete "typical error" and a mean change between trials, each with t-based confidence limits, so readers can see how precisely the mean change is estimated rather than just whether it is significant.
  - *Lesson:* Report your model's mean error against the closing total (e.g., +0.8 points) with a t-based 95% CI. If the interval comfortably includes 0, you have no demonstrated bias to bet on.
- **Applied to v4:** 95% t confidence interval for ROI per bet: +3.38% to +13.14%. For v4's bias (final - v4): +0.12 +/- 0.64 pts (t=0.36, p=0.72). Interpretation: we're 95% confident the long-run ROI of this rule is in that range (if the future looks like 2023-26).

### B50. Sample size for a margin of error  ·  *Warning*  ⇄
- **Formula / idea:** n ≈ (z_(α/2)·σ / E)², round up.
- **Paper:** Lenth, R. V. (2001). Some practical guidelines for effective sample size determination. *The American Statistician, 55*(3), 187-193. https://doi.org/10.1198/000313001317098149
  - *How they used it:* Methods/practice paper (no single dataset). It argues that sample size should come from a scientifically meaningful effect size or margin of error and realistic variance inputs, and it criticises "canned" standardized effect sizes and retrospective power calculations.
  - *Lesson:* Pick in advance how precisely you need to know your mean edge (e.g., +/-0.5 points when game-total SD is about 18-20 points), then solve for the number of games. That number usually runs into the thousands, i.e. several seasons.
- **Applied to v4:** Sample size for a margin of error: to estimate ROI to +/-2% (95%), n = (1.96*0.946/0.02)^2 = 8,599 bets; +/-1% needs 34,396. At ~482 bets a season that's 17.8 / 71.4 seasons.
- **Carries over:** Required sample sizes for small edges are in the thousands: true for any market strategy.

### B51. Hypothesis test framework / one- vs two-sided  ·  *Confirmed (in-sample)*
- **Formula / idea:** Test: H0, Ha, test statistic, rejection region, conclusion. One-sided vs two-sided Ha.
- **Paper:** Pankoff, L. D. (1968). Market efficiency and football betting. *The Journal of Business, 41*(2), 203-214. https://doi.org/10.1086/295077
  - *How they used it:* An early efficiency test of the NFL point-spread market. It asked whether spreads were unbiased forecasts of game margins and whether published experts could beat them, setting the null as "the line is efficient" against inefficiency alternatives, and found little exploitable inefficiency.
  - *Lesson:* State H0 ("my over/under picks win 50%", or "win at or below the 52.38% break-even") before looking. A one-sided test against break-even is the claim you actually care about, so don't switch sidedness after you see the results.
- **Applied to v4:** The five parts: (1) H0: mu_ROI <= 0, (2) Ha: mu_ROI > 0 (one-sided, decided before looking), (3) t = xbar/(s/sqrt n) = 3.32, (4) reject if t >= t(0.95, 1445) = 1.646, (5) p = 0.00046: reject H0. Caution: these seasons helped choose v4, so it's a descriptive test, not a clean out-of-sample one.

### B52. Type I / Type II error and power  ·  *Warning*  ⇄
- **Formula / idea:** Type I (reject true H0, rate α); Type II (miss false H0, rate β); power = 1 − β.
- **Paper:** Button, K. S., Ioannidis, J. P. A., Mokrysz, C., Nosek, B. A., Flint, J., Robinson, E. S. J., & Munafo, M. R. (2013). Power failure: Why small sample size undermines the reliability of neuroscience. *Nature Reviews Neuroscience, 14*(5), 365-376. https://doi.org/10.1038/nrn3475
  - *How they used it:* Pooled meta-analyses across neuroscience and estimated a median statistical power of about 20%. Low power both misses real effects and means that the significant results that do appear tend to be false positives or overstated (the "winner's curse").
  - *Lesson:* A 300-bet backtest has little power to detect a real 2-3 point edge, and any "significant" edge it shows is probably inflated. Size the backtest for power and expect live results to shrink.
- **Applied to v4:** Type I error = calling a losing system a winner (alpha 5%); Type II = missing a real edge. Power to detect a true 55% win rate (vs 52.4%) with 300 bets: 23%; 500: 31%; 1446: 62%. Bets needed for 80% power: ~2,300. A one-season test of a new filter (~100-300 bets) is badly underpowered: most real 2-3% edges would 'fail'.
- **Carries over:** Power analysis before testing a filter applies to any backtest.

### B53. p-values  ·  *Tool*
- **Formula / idea:** p-value = P(statistic at least as extreme as observed | H0); reject if p ≤ α.
- **Paper:** Brodeur, A., Le, M., Sangnier, M., & Zylberberg, Y. (2016). Star Wars: The empirics strike back. *American Economic Journal: Applied Economics, 8*(1), 1-32. https://doi.org/10.1257/app.20150044
  - *How they used it:* Replaces the ASA statement candidate (a policy statement, not a standard peer-reviewed study). Collected about 50,000 test statistics from AER, JPE and QJE and found a two-humped distribution: too few p-values between 0.10 and 0.25 and an excess just below 0.05. They attribute 10-20% of marginally significant results to specification searching.
  - *Lesson:* A feature that only gets to p = 0.04 after you try several rolling windows is likely p-hacked. Pre-register the feature set and the evaluation seasons before checking p-values.
- **Applied to v4:** p-values: P(results at least this good | no edge). Binomial vs break-even p = 0.00053; t-test on ROI p = 0.00046. It is NOT the probability v4 has no edge, and it's computed on seasons that helped build v4. See B64 for how many p-values this catalog produced.

### B54. Student t distribution / one-sample t test  ·  *Confirmed (in-sample)*
- **Formula / idea:** t = (x̄ − μ0)/(s/√n), df = n − 1; heavier tails than Z for small n.
- **Paper:** Student. (1908). The probable error of a mean. *Biometrika, 6*(1), 1-25. https://doi.org/10.1093/biomet/6.1.1
  - *How they used it:* Derived the small-sample distribution of (mean - mu)/(s/sqrt(n)), checked it empirically, and applied it to Cushny and Peebles' paired data on the extra hours of sleep gained from two hypnotic drugs (10 patients), showing how to judge a mean difference when n is tiny.
  - *Lesson:* For a one-sample t test of mean (actual total - closing total), the t reference only matters with small samples, but the logic carries over: the uncertainty comes from s/sqrt(n), not from s.
- **Applied to v4:** t distribution: with df=1445 the t critical value 1.962 is essentially z (1.960). For a 30-bet sample (df 29) it's 2.045: small samples need wider intervals. One-sample t on points beaten: t=5.99, mean +2.89 pts/bet.

### B55. Pooled two-sample t test (comparing two group means)  ·  *No trend*
- **Formula / idea:** Pooled t = (x̄1 − x̄2)/(s_p√(1/n1 + 1/n2)), s_p² = [(n1−1)s1² + (n2−1)s2²]/(n1 + n2 − 2).
- **Paper:** Edmans, A., Garcia, D., & Norli, O. (2007). Sports sentiment and stock returns. *The Journal of Finance, 62*(4), 1967-1998. https://doi.org/10.1111/j.1540-6261.2007.01262.x
  - *How they used it:* Compared mean next-day national stock-market returns after international soccer losses vs wins (1,162 matches in 39 countries). Losses averaged -18.4 bp and wins +5.0 bp. The formal test is a dummy-variable regression, equivalent to a two-sample mean comparison, with panel-corrected rather than pooled-variance SEs. Loss days showed significant negative abnormal returns (-21 bp, t = -3.3); win days showed none.
  - *Lesson:* To test whether totals errors differ between two groups (e.g., back-to-back vs rested games), a two-sample t test (or regression on a dummy) is the tool. Only pool the variances if the two groups' error SDs really are similar.
- **Applied to v4:** Pooled two-sample t: points beaten, over bets (+3.13, n=792) vs under bets (+2.59, n=654): t=+0.55, p=0.583.

### B56. Welch t test  ·  *No trend*
- **Formula / idea:** Welch t = (x̄1 − x̄2)/√(s1²/n1 + s2²/n2), Satterthwaite df.
- **Paper:** Welch, B. L. (1947). The generalization of "Student's" problem when several different population variances are involved. *Biometrika, 34*(1-2), 28-35. https://doi.org/10.1093/biomet/34.1-2.28
  - *How they used it:* Canonical methods source. It derived the approximate degrees of freedom for comparing means when the groups have unequal variances, which is the basis of the Welch t test that R's `t.test()` uses by default.
  - *Lesson:* Error variance on high totals (around 240) and low totals (around 210) need not be equal, so compare subgroup mean errors with Welch rather than a pooled t.
- **Applied to v4:** Welch t (unequal variances): same over/under comparison t=+0.55, df~1444, p=0.584. Also (final - opener) in games where both teams were rested (+0.30) vs a back-to-back involved (+0.68): t=-0.53, p=0.597. The market prices rest fine on average.

### B57. Paired t test / comparing forecast accuracy  ·  *No trend*
- **Formula / idea:** Paired: d_i = x1i − x2i; t = d̄/(s_d/√n), df = n − 1.
- **Paper:** Diebold, F. X., & Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics, 13*(3), 253-263. https://doi.org/10.1080/07350015.1995.10524599 (RePEc: https://econpapers.repec.org/RePEc:bes:jnlbes:v:13:y:1995:i:3:p:253-63)
  - *How they used it:* Proposed testing whether two forecasts are equally accurate by treating the per-period loss differential as a paired series and testing its mean, with a long-run variance correction for serial correlation. Size and power were checked by Monte Carlo.
  - *Lesson:* Score each game's absolute (or squared) error for your model and for the closing total, take the per-game differences, and test their mean (paired/DM test). That is the honest test of "my model beats the line".
- **Applied to v4:** Paired t (same game, two forecasts): |opener error| - |v4 error| = +0.052 pts, t=+0.73, p=0.465; vs the CLOSE: -0.320, t=-4.30, p=0.000. Pairing removes game-to-game noise (the 18-pt SD) so small accuracy gaps become testable. v4 is roughly as accurate as the opener in absolute error and worse than the close.

### B58. F test / ratio of two variances  ·  *No trend*
- **Formula / idea:** F = s1²/s2², df (n1 − 1, n2 − 1).
- **Paper:** Lo, A. W., & MacKinlay, A. C. (1988). Stock market prices do not follow random walks: Evidence from a simple specification test. *The Review of Financial Studies, 1*(1), 41-66. https://doi.org/10.1093/rfs/1.1.41 (RePEc: https://ideas.repec.org/a/oup/rfinst/v1y1988i1p41-66.html)
  - *How they used it:* Used a variance-ratio statistic (variance of q-week returns over q times the variance of 1-week returns) on CRSP weekly returns from 1962 to 1985. Ratios well above 1 rejected the random walk, especially for small-stock portfolios, showing positive autocorrelation. (A ratio-of-variances test rather than the textbook two-sample F.)
  - *Lesson:* Comparing variances is a test in its own right: check whether residual variance against the line is larger early in the season or for certain teams before you assume one sigma for every game.
- **Applied to v4:** F test for two variances: opener error variance Nov-Dec (18.83^2) vs Feb-Apr (18.12^2): F=1.080, p=0.183. (F is sensitive to non-normal tails; Levene in B60 is the robust check.)


## ANOVA and multiple comparisons

### B59. One-way ANOVA  ·  *Suggestive (partly replicates)*
- **Formula / idea:** One-way ANOVA: SST = SSB + SSW; F = MSB/MSW, df (t − 1, N − t).
- **Paper:** Gibbons, M. R., & Hess, P. (1981). Day of the week effects and asset returns. *The Journal of Business, 54*(4), 579-596. https://doi.org/10.1086/296147
  - *How they used it:* Tested whether mean daily returns on stock indices (S&P 500, CRSP) and Treasury bills are equal across the five weekdays (one factor, five levels). They rejected equality, driven by strongly negative Monday means.
  - *Lesson:* To test "does the mean over/under error differ by day of week (or by rest category)?", run a one-way ANOVA before you build features for each level.
- **Applied to v4:** One-way ANOVA: (final - opener) across 6 months: SSB=6770, SSE=1083220, F(5,3198)=4.00, p=0.001. Same for v4 bets' points beaten across months: p=0.173.

### B60. Equal-variance assumption (Levene / Brown-Forsythe)  ·  *No trend*
- **Formula / idea:** ANOVA assumes normal errors with equal variance; check by Q-Q plots and residual-vs-fitted spread (Levene/Brown-Forsythe, Bartlett).
- **Paper:** Brown, M. B., & Forsythe, A. B. (1974). Robust tests for the equality of variances. *Journal of the American Statistical Association, 69*(346), 364-367. https://doi.org/10.1080/01621459.1974.10482955
  - *How they used it:* Used Monte Carlo to compare Levene-type tests and showed that the median-centred version keeps its nominal size under skewed and heavy-tailed data, where Bartlett's test fails.
  - *Lesson:* Totals residuals have fat tails (overtimes, blowouts with walk-on minutes), so check equal variance with Brown-Forsythe (`car::leveneTest`, center = median), not Bartlett.
- **Applied to v4:** ANOVA assumptions for the month model: Brown-Forsythe/Levene p=0.604, Bartlett p=0.549 (equal variance), residual skew +0.15. Assumptions look fine, so the ANOVA result can be trusted.

### B61. Transformations (log, sqrt)  ·  *Tool*
- **Formula / idea:** Transform y (log, √, power) to fix skew or unequal variance.
- **Paper:** Bartlett, M. S. (1947). The use of transformations. *Biometrics, 3*(1), 39-52. https://doi.org/10.2307/3001536
  - *How they used it:* Reviewed variance-stabilising transformations (square root for Poisson-like counts, log for multiplicative data, angular for proportions) with worked examples, showing when they make ANOVA assumptions hold.
  - *Lesson:* Counts such as 3-point attempts or free throws have variance that grows with the mean, so a square-root or log transform (or a count model) can stabilise the variance before the counts enter a totals regression.
- **Applied to v4:** Transformations: total points skew +0.192; log -0.085; sqrt +0.054. Residual spread vs line height: see B84/B87. Totals are already near-symmetric; transforming adds little here (it matters more for team props / low counts).

### B62. Contrasts  ·  *Suggestive*
- **Formula / idea:** Contrast L = Σc_iμ_i with Σc_i = 0; SE = √(MSE·Σc_i²/n_i).
- **Paper:** French, K. R. (1980). Stock returns and the weekend effect. *Journal of Financial Economics, 8*(1), 55-69. https://doi.org/10.1016/0304-405X(80)90021-5
  - *How they used it:* Used daily S&P 500 returns (1953-1977) to test planned comparisons: Monday vs other days under a "calendar-time" hypothesis (Monday should be about 3x a normal day) and a "trading-time" hypothesis (all days equal). Monday's mean was significantly negative, rejecting both.
  - *Lesson:* Write the question you care about as a specific contrast, e.g. "second night of a back-to-back vs all other games", and test that one contrast. It has far more power than an omnibus F.
- **Applied to v4:** Contrast: early (Nov-Jan) minus late (Feb-Apr) mean of (final - opener) = -1.23 pts, SE 0.68, t=-1.82, p=0.070. Planned question: does the book lag the scoring level early in the season?

### B63. Orthogonal contrasts (incl. orthogonal polynomials)  ·  *Tool*
- **Formula / idea:** Orthogonal contrasts: Σc_i d_i/n_i = 0; their SS partition SSB.
- **Paper:** Lowry, S. R. (1992). Use and misuse of multiple comparisons in animal experiments. *Journal of Animal Science, 70*(6), 1971-1977. https://doi.org/10.2527/1992.7061971x
  - *How they used it:* Re-analysed data from three *Journal of Animal Science* papers. It showed that structured or factorial treatments should be broken into planned orthogonal contrasts, and quantitative dose levels into orthogonal polynomial (linear/quadratic) contrasts, instead of running all-pairs multiple-comparison tests.
  - *Lesson:* For an ordered factor such as days of rest (0, 1, 2, 3+), test linear and quadratic orthogonal contrasts. That tells you whether the effect on totals is a trend or a threshold.
- **Applied to v4:** Orthogonal contrasts (dot products (np.int64(0), np.int64(0), np.int64(0)), all 0 with ~equal month sizes): SS early-vs-late 1116, Jan-vs-Nov/Dec 2578, Apr-vs-Feb/Mar 2533 out of SSB 6770. With these 3 of the 5 possible orthogonal pieces we see where the month-to-month variation sits: late-season April (playoff-push / tank games) and the January dip carry most of it.

### B67. Tukey HSD  ·  *Suggestive (partly replicates)*
- **Formula / idea:** Tukey HSD: all pairwise differences, familywise α via the studentized range q.
- **Paper:** Kramer, C. Y. (1956). Extension of multiple range tests to group means with unequal numbers of replications. *Biometrics, 12*(3), 307-310. https://doi.org/10.2307/3001469
  - *How they used it:* Replaces the Tukey (1949) candidate: Tukey 1949 is the gap-straggling procedure, and HSD itself first appeared in an unpublished 1953 manuscript. Kramer extended Tukey's studentized-range test to unequal group sizes (Tukey-Kramer), which is what R's `TukeyHSD()` computes.
  - *Lesson:* Comparing mean totals errors across all 30 arenas is an all-pairs problem with unequal game counts, so use Tukey-Kramer. Expect few pairs to survive.
- **Applied to v4:** Tukey HSD on all 15 month pairs: 3 significant at familywise 5%; smallest adjusted p=0.001 (Apr vs Jan).

### B66. Fisher LSD  ·  *Tool*
- **Formula / idea:** Fisher LSD: unadjusted pairwise t-tests, only after a significant overall F.
- **Paper:** Carmer, S. G., & Swanson, M. R. (1973). An evaluation of ten pairwise multiple comparison procedures by Monte Carlo methods. *Journal of the American Statistical Association, 68*(341), 66-74. https://doi.org/10.1080/01621459.1973.10481335
  - *How they used it:* Simulated Type I, Type III and correct-decision rates for ten pairwise procedures. They recommended the restricted (protected) LSD, i.e. unadjusted pairwise t tests run only after a significant ANOVA F, over the Scheffe, Tukey and SNK tests on power grounds.
  - *Lesson:* LSD only offers protection when the omnibus F is significant and the groups are few (about 3). With many team or arena groups its familywise error grows quickly.
- **Applied to v4:** Fisher's LSD (unadjusted pairwise t after the F test): 6 of 15 month pairs 'significant' at 5% (smallest p=0.000, Jan vs Apr). The overall F was significant (p=0.001), so LSD is allowed, but it doesn't adjust for 15 comparisons, so it flags more pairs than Tukey.

### B68. Scheffe method  ·  *Suggestive (partly replicates)*
- **Formula / idea:** Scheffé: any (incl. unplanned) contrast; reject if t² > (t − 1)·F(α; t − 1, N − t).
- **Paper:** Scheffe, H. (1953). A method for judging all contrasts in the analysis of variance. *Biometrika, 40*(1-2), 87-110. https://doi.org/10.1093/biomet/40.1-2.87
  - *How they used it:* Derived simultaneous intervals, based on the F distribution, that remain valid for every possible contrast, including ones chosen after seeing the data, at the cost of wider intervals.
  - *Lesson:* If you go hunting for an interesting contrast after seeing the data (e.g., "West Coast teams in the first half of the season"), only a Scheffe-level threshold makes that post-hoc claim honest.
- **Applied to v4:** Scheffe for an unplanned contrast (picked after looking, e.g. the best month vs the worst): needs t^2 >= (k-1)F = 11.1 (t >= 3.33) vs 1.96 for a planned one. Best-minus-worst month t = 4.04: it clears Scheffe, so the April-vs-January gap survives even the strictest after-the-fact correction (and B65 Bonferroni). Any trend found by scanning the data must clear this much higher bar.


## Categorical data

### B69. One-proportion CI (Wilson / Agresti-Coull)  ·  *Confirmed (in-sample)*
- **Formula / idea:** π̂ ± z·√(π̂(1 − π̂)/n) (Wilson/Agresti-Coull better); z = (π̂ − π0)/√(π0(1 − π0)/n).
- **Paper:** Agresti, A., & Coull, B. A. (1998). Approximate is better than "exact" for interval estimation of binomial proportions. *The American Statistician, 52*(2), 119-126. https://doi.org/10.1080/00031305.1998.10480550
  - *How they used it:* Compared coverage of the Wald, Clopper-Pearson "exact" and score intervals for a binomial p. The Wald interval undercovers badly, while the Wilson score and "add 2 successes and 2 failures" intervals have near-nominal coverage and are shorter than exact.
  - *Lesson:* Report your over/under hit rate with a Wilson or Agresti-Coull interval. A 55% record over 200 bets gives roughly 48-62%, which still includes the 52.4% break-even.
- **Applied to v4:** One proportion: v4 win rate 56.7%, 95% Wilson CI 54.1%-59.2% (break-even 52.4% is below the interval). z test vs 52.38%: z=3.32, p=0.00045. Games going over the opener: 50.2% (CI 48.4%-51.9%); the opener is balanced.

### B70. Sample size for a proportion  ·  *Tool*
- **Formula / idea:** n = z²·π(1 − π)/E².
- **Paper:** Lachin, J. M. (1981). Introduction to sample size determination and power analysis for clinical trials. *Controlled Clinical Trials, 2*(2), 93-113. https://doi.org/10.1016/0197-2456(81)90001-5
  - *How they used it:* Gave the standard normal-approximation formulas, with worked clinical-trial examples, for the sample size and power needed to detect differences in proportions (and in means and survival) at a given alpha and power.
  - *Lesson:* Detecting a true 55% hit rate against 52.4% (one-sided alpha 0.05, 80% power) takes roughly 2,000+ bets. Plan backtests and staking around that number.
- **Applied to v4:** Sample size for a proportion: to pin the win rate to +/-2% with 95% confidence, n = 1.96^2*0.55*0.45/0.02^2 = 2,377 bets; +/-1%: 9,508.

### B71. Two-proportion z test  ·  *No trend*
- **Formula / idea:** z = (π̂1 − π̂2)/√(π̂(1 − π̂)(1/n1 + 1/n2)) with pooled π̂.
- **Paper:** Pope, D. G., & Schweitzer, M. E. (2011). Is Tiger Woods loss averse? Persistent bias in the face of experience, competition, and high stakes. *American Economic Review, 101*(1), 129-157. https://doi.org/10.1257/aer.101.1.129 (RePEc: https://econpapers.repec.org/RePEc:aea:aecrev:v:101:y:2011:i:1:p:129-57)
  - *How they used it:* Compared make rates for PGA Tour par putts vs birdie putts of the same distance using about 2.5 million laser-measured putts. Par putts were made about 2-3 percentage points more often, a difference in two proportions that held up with controls (distance, player and hole effects).
  - *Lesson:* To ask whether overs hit more often in one setting than another (e.g., totals set above 235 vs below), compare two proportions, and control for the confounder (here the size of the total) as they did.
- **Applied to v4:** Two proportions: win rate 2023-24 55.6% vs 2025-26 59.3%: z=-1.17, p=0.242. Overs 57.2% vs unders 56.1%: z=+0.41, p=0.680.

### B72. Fisher's exact test  ·  *No trend*
- **Formula / idea:** Fisher's exact test: hypergeometric probability of tables with fixed margins.
- **Paper:** Henriksson, R. D., & Merton, R. C. (1981). On market timing and investment performance. II. Statistical procedures for evaluating forecasting skills. *The Journal of Business, 54*(4), 513-533. https://doi.org/10.1086/296144
  - *How they used it:* Built a nonparametric test of market-timing skill. Under no skill, the number of correct "up" calls given the totals in a 2x2 table follows a hypergeometric distribution, which is Fisher's exact test, and they applied it to evaluate fund managers' and forecasters' calls.
  - *Lesson:* With a small sample of directional calls (e.g., 40 over/under picks in one month), use the exact hypergeometric test on the 2x2 table of predicted vs actual direction rather than a z approximation.
- **Applied to v4:** Fisher's exact (small table, edge 8+ only, 184 bets): over 60-43; under 47-34. Odds ratio 0.99, exact p=1.000. Too few big-edge bets to say anything about direction there.

### B73. Chi-square goodness of fit  ·  *Confirmed out of sample*  ⇄
- **Formula / idea:** χ² = Σ(O − E)²/E, df = k − 1 − (estimated parameters).
- **Paper:** Reep, C., & Benjamin, B. (1968). Skill and chance in association football. *Journal of the Royal Statistical Society. Series A (General), 131*(4), 581-585. https://doi.org/10.2307/2343726 (JSTOR: https://www.jstor.org/stable/2343726)
  - *How they used it:* Fitted a negative binomial distribution to the frequencies of passing-move lengths recorded in English League and World Cup matches and compared observed with expected counts. The fit was close, implying that a large share of football outcomes behaves like a chance process.
  - *Lesson:* Before assuming team scores or game totals are normal (or Poisson), compare binned observed and expected frequencies with a chi-square GOF test. The tails (overtime games) are usually where the fit fails.
- **Applied to v4:** Chi-square goodness of fit: v4 errors in 8 bins vs a normal curve: chi2=13.8, df=5, p=0.017 (observed [147, 281, 537, 679, 637, 493, 244, 186], expected [165, 279, 496, 662, 662, 496, 279, 165]). Left tail lighter, right tail heavier than normal: big overs (overtime) happen more than big unders, so the mean sits above the median. Last digit of final totals uniform? chi2=14.9, df=9, p=0.094.
- **Carries over:** Right-skewed outcomes: mean ≠ median, so 'average beats the line' ≠ 'wins more than half'. Same for skewed returns.

### B74. Chi-square test of independence  ·  *No trend*
- **Formula / idea:** Independence: E_ij = (row_i·col_j)/n; χ² with df (r − 1)(c − 1).
- **Paper:** Pesaran, M. H., & Timmermann, A. (1992). A simple nonparametric test of predictive performance. *Journal of Business & Economic Statistics, 10*(4), 561-565. https://doi.org/10.1080/07350015.1992.10509922 (RePEc: https://econpapers.repec.org/RePEc:bes:jnlbes:v:10:y:1992:i:4:p:561-65)
  - *How they used it:* Proposed a test of whether a forecast predicts the direction of change, based on the predicted-vs-actual contingency table, and related it to the chi-square test of independence (which it shows is more conservative). It was applied to CBI and INSEE survey expectations of price and demand changes.
  - *Lesson:* Tabulate model call (over/under) against outcome (over/under). If you can't reject independence, your model has no directional skill against the line, however good its RMSE looks.
- **Applied to v4:** Chi-square independence: season x win chi2=1.63, df=2, p=0.442; direction x win chi2=0.13, p=0.719. Win rate doesn't depend on season or direction: the edge is consistent.

### B75. Odds and odds ratios  ·  *Confirmed (in-sample)*  ⇄
- **Formula / idea:** Odds = p/(1 − p); OR = odds1/odds2; log(OR) SE = √(Σ1/n_ij).
- **Paper:** Bland, J. M., & Altman, D. G. (2000). Statistics notes: The odds ratio. *BMJ, 320*(7247), 1468. https://doi.org/10.1136/bmj.320.7247.1468
  - *How they used it:* Explained odds and the odds ratio with a 2x2 table of hay fever and eczema in 11-year-old children. It showed why the OR is symmetric and is the natural output of logistic regression, and how it differs from the relative risk.
  - *Lesson:* -110 odds imply p = 110/210 = 0.524. Convert both your model probability and the market price to odds, and read logistic-model coefficients as odds ratios, not probability changes.
- **Applied to v4:** Odds: win odds when the line moved toward us 1.57 (= 61.2%); when it moved against 0.93. Odds ratio 1.70 (95% CI 1.37-2.11). Break-even odds are 1.05 (52.4%); our overall odds 1.31.
- **Carries over:** Price moving toward your position after entry (CLV) as a skill marker carries directly to trading.


## Regression, diagnostics and model choice

### B76. Simple linear regression / least squares  ·  *Confirmed (in-sample)*  ⇄
- **Formula / idea:** y = β0 + β1x + ε; b1 = Sxy/Sxx, b0 = ȳ − b1x̄ minimizes SSE = Σ(y − ŷ)².
- **Paper:** Paul, R. J., & Weinbach, A. P. (2008). Price setting in the NBA gambling market: Tests of the Levitt model of sportsbook behavior. *International Journal of Sport Finance, 3*(3), 137-145. https://ideas.repec.org/a/jsf/intjsf/v3y2008i3p137-145.html
  - *How they used it:* Used betting-percentage data from four sportsbooks for the 2004-05 to 2006-07 NBA seasons. An OLS regression of the share of bets on the over against the posted total gave a slope of about 0.12 (t of about 5.6): the public bets the over more as totals rise. Simple "bet the under" rules were then tested against a 50% win rate and the 52.38% break-even, and none were significant.
  - *Lesson:* Regress outcome (or bet share) on the posted total. A positive slope for public over-betting does not mean the under is profitable, so test the betting rule separately against break-even.
- **Applied to v4:** Least squares: (final - opener) = +0.25 + 0.549 x edge. Slope SE 0.077, p=1.3e-12. A slope of 1 would mean v4's edges are fully right; 0.55 means only ~55% of each edge shows up in results: shrink v4 toward the opener by ~45% when converting edge to win probability. Efficiency test on the market itself (final on close, 2011-26): slope 0.991 (SE 0.008), intercept +2.3.
- **Carries over:** Regress outcomes on your edge: slope < 1 tells you how much to shrink any forecast toward the market price.

### B77. R squared  ·  *Tool*
- **Formula / idea:** R² = 1 − SSE/SST = share of variation explained.
- **Paper:** Berri, D. J. (1999). Who is "most valuable"? Measuring the player's production of wins in the National Basketball Association. *Managerial and Decision Economics, 20*(8), 411-427. https://doi.org/10.1002/1099-1468(199912)20:8<411::AID-MDE957>3.0.CO;2-G
  - *How they used it:* Regressed NBA team wins on team box-score statistics (points, possessions, rebounds, turnovers, etc.). The high R-squared showed the box score explains most of the variation in team wins, and the coefficients were then used to assign wins to individual players.
  - *Lesson:* High R-squared in explaining what happened (box-score inputs) is not forecasting skill. Pre-game totals models typically explain only a modest share of game-total variance, and that is normal.
- **Applied to v4:** R^2 of (final - opener) on edge: 0.0156: v4 explains 1.56% of the variation of totals around the opener. R^2 of final total on v4 alone: 0.172, on the opener: 0.167, close: 0.212. Tiny R^2 is normal and still profitable in betting.

### B78. Regression F test (joint test)  ·  *Confirmed (in-sample)*
- **Formula / idea:** Regression F = MSR/MSE; tests all slopes = 0.
- **Paper:** Zuber, R. A., Gandar, J. M., & Bowers, B. D. (1985). Beating the spread: Testing the efficiency of the gambling market for National Football League games. *Journal of Political Economy, 93*(4), 800-806. https://doi.org/10.1086/261332
  - *How they used it:* Regressed actual NFL point differentials on the point spread (alongside a team-statistics forecasting model) and used an F test of the joint restriction intercept = 0, slope = 1 to test market efficiency. They argued their model identified profitable deviations, which prompted a well-known comment-and-reply debate in JPE.
  - *Lesson:* Test line efficiency for totals with the joint F test (intercept 0, slope 1) of actual total on closing total. Slope-only or intercept-only t tests can miss the joint failure.
- **Applied to v4:** Regression F test: F(1,3202) = 50.67, p=1.3e-12 (= t^2 for one predictor).

### B79. Prediction intervals  ·  *Warning*
- **Formula / idea:** Prediction interval (one new y) is wider than CI for the mean; extrapolation = predicting outside the observed x range.
- **Paper:** Christoffersen, P. F. (1998). Evaluating interval forecasts. *International Economic Review, 39*(4), 841-862. https://doi.org/10.2307/2527341
  - *How they used it:* Developed likelihood-ratio tests of unconditional coverage, independence of interval "hits", and conditional coverage, then applied them to interval forecasts of exchange rates used in risk management.
  - *Lesson:* If your model gives 80% prediction intervals for game totals, check that about 80% of games land inside, and that misses don't cluster (e.g., all in one month or with one team).
- **Applied to v4:** Prediction vs extrapolation: at edge 3 the expected (final - opener) is +1.90 (95% CI of the mean +1.15 to +2.65), but a single game's 95% prediction interval is -34 to +38. Only 2.1% of games have edge 10+, so predicting at edge 12 (+6.84) is extrapolation: huge edges usually mean bad inputs (missed injury), not huge value.

### B80. Cook's distance / influential observations  ·  *Tool*
- **Formula / idea:** Cook's D_i = (r_i²/p)·h_ii/(1 − h_ii)²; flag if D > 4/n or > 1.
- **Paper:** Cook, R. D. (1977). Detection of influential observation in linear regression. *Technometrics, 19*(1), 15-18. https://doi.org/10.1080/00401706.1977.10489493
  - *How they used it:* Introduced the distance D_i, which measures how far the fitted coefficients move when observation i is deleted, combining residual size and leverage. It was demonstrated on a small published regression dataset in which one point dominated the fit.
  - *Lesson:* Overtime games and garbage-time blowouts can dominate a totals regression. Compute Cook's D, and refit with and without the top points to see whether your edge survives.
- **Applied to v4:** Cook's distance: 160 games above 4/n; max D=0.0109 (far below 1). Refit without them: slope 0.523 vs 0.549. No single game drives the result.

### B81. Multiple linear regression  ·  *Suggestive*
- **Formula / idea:** y = β0 + β1x1 + … + βkxk + ε; each β = effect holding the others fixed.
- **Paper:** Scully, G. W. (1974). Pay and performance in Major League Baseball. *American Economic Review, 64*(6), 915-930. https://www.jstor.org/stable/1815242
  - *How they used it:* Regressed MLB team winning percentage on team slugging average and strikeout-to-walk ratio (with league and contention controls), then revenue on win percentage. This gave each player's marginal revenue product, which was well above salary under the reserve clause.
  - *Lesson:* A totals model is a multiple regression (pace, offensive and defensive efficiency, rest, injuries). Interpret each coefficient as a partial effect holding the others fixed, not as a raw correlation.
- **Applied to v4:** Multiple regression of (final - opener) on Model 1 edge and v4's add-ons: e_m1 +0.496 (p=0.000), Lc -0.183 (p=0.004), form +0.129 (p=0.001), alt +3.818 (p=0.004), rested +0.006 (p=0.993). R^2 0.0158. Each coefficient = effect holding the others fixed. Lc (shooting luck) is negative: lucky-shooting teams' games go under the opener.

### B82. Studentized residuals / outlier tests  ·  *Tool*
- **Formula / idea:** Studentized residual = e_i / (s_(i)√(1 − h_ii)); |t| > 2–3 flags outliers; Bonferroni outlier test.
- **Paper:** Beckman, R. J., & Cook, R. D. (1983). Outlier..........s. *Technometrics, 25*(2), 119-149. https://doi.org/10.1080/00401706.1983.10487840
  - *How they used it:* Canonical review, with discussion, of outlier detection in samples and regression. It covers internally vs externally studentized residuals, Bonferroni-bounded outlier tests (the basis of `car::outlierTest`) and masking/swamping, illustrated with classic datasets.
  - *Lesson:* Flag games with large externally studentized residuals (e.g., quadruple-overtime games) using a Bonferroni-adjusted cutoff instead of eyeballing them, then decide on principle whether to keep them.
- **Applied to v4:** Studentized residuals: 4.4% beyond |2| (normal 4.6%), 14 beyond |3|; largest |t|=3.44, Bonferroni outlier p=1.000. No game is an impossible outlier once you account for 3,204 chances.

### B83. Residual / normal Q-Q plots  ·  *Tool*
- **Formula / idea:** Q-Q plot of residuals checks normal errors.
- **Paper:** Fama, E. F. (1965). The behavior of stock-market prices. *The Journal of Business, 38*(1), 34-105. https://doi.org/10.1086/294743
  - *How they used it:* Plotted daily price changes for each of the 30 Dow Jones stocks (about 1957-1962) on normal probability paper (a Q-Q plot). The S-shaped departures showed tails much fatter than normal, supporting stable-Paretian (Mandelbrot) models.
  - *Lesson:* Q-Q plot your totals residuals. Fat tails mean normal-theory tail probabilities (e.g., P(total > line + 15)) are understated, which matters for alternate totals and for staking.
- **Applied to v4:** Residual Q-Q plot for the multiple regression: correlation 0.9992; tails: 0.81% above z=2.576 vs 0.5% expected, 0.37% below. Right tail a little heavy (overtime). Coefficient tests are robust to this at n=3,204.

### B84. Homoscedasticity test (Breusch-Pagan) and error independence  ·  *Confirmed out of sample*  ⇄
- **Formula / idea:** Constant variance (Breusch-Pagan / ncvTest) and independent errors (Durbin-Watson ≈ 2).
- **Paper:** Breusch, T. S., & Pagan, A. R. (1979). A simple test for heteroscedasticity and random coefficient variation. *Econometrica, 47*(5), 1287-1294. https://doi.org/10.2307/1911963 (JSTOR: https://www.jstor.org/stable/1911963)
  - *How they used it:* Derived a Lagrange-multiplier test for heteroscedasticity computed from OLS residuals (regress squared residuals on candidate variables) and gave finite-sample evidence on its behaviour. (For serial independence, the companion classic is Durbin & Watson, 1950, *Biometrika*.)
  - *Lesson:* Totals error variance plausibly rises with pace or with the posted total. Run Breusch-Pagan (`car::ncvTest`/`lmtest::bptest`) and use robust SEs or weights if it rejects.
- **Applied to v4:** Homoscedasticity: Breusch-Pagan on the model's predictors p=0.486; does error spread grow with the opener level? p=0.008. Durbin-Watson in date order 1.994 (2 = no autocorrelation).  Errors are independent, but their spread DOES grow with the opener: a 240 total is noisier than a 215 total (heteroscedastic).
- **Carries over:** Noise that scales with the level (volatility rises with price/total): size by edge in SD units.

### B85. Component + residual (partial residual) plots  ·  *Tool*
- **Formula / idea:** Component + residual (partial residual) plot: e + b_j·x_j vs x_j checks linearity of x_j.
- **Paper:** Larsen, W. A., & McCleary, S. J. (1972). The use of partial residual plots in regression analysis. *Technometrics, 14*(3), 781-790. https://doi.org/10.2307/1267305
  - *How they used it:* Introduced plots of each predictor's component plus the residual against that predictor, to reveal nonlinearity in one predictor after the others are accounted for, with worked regression examples.
  - *Lesson:* Use C+R plots (`car::crPlots`) on pace or rest days. A curved pattern tells you a linear term is mis-specifying how that input moves the total.
- **Applied to v4:** Component + residual (partial residual) check for the edge term: binned partial residuals -11.5->-3.34, -3.3->-1.74, -1.8->-1.11, -0.5->-0.10, +0.7->+1.10, +2.0->+2.86, +3.7->+0.91, +11.6->+2.27. Roughly a straight line: linear in edge is a reasonable form.

### B86. Added-variable plots  ·  *Suggestive*
- **Formula / idea:** Added-variable plot: residuals of y on others vs residuals of x_j on others; slope = b_j.
- **Paper:** Johnson, B. W., & McCulloch, R. E. (1987). Added-variable plots in linear regression. *Technometrics, 29*(4), 427-433. https://doi.org/10.1080/00401706.1987.10488270
  - *How they used it:* Reviewed three graphical methods for judging what an extra explanatory variable adds to a linear regression (including the added-variable / partial-regression plot) and proposed a new variant.
  - *Lesson:* Before adding a feature (e.g., referee-crew foul rate), check its added-variable plot. If its residualised relation to the total is flat, it adds nothing beyond the features you already have.
- **Applied to v4:** Added-variable plot for shooting luck: after removing everything else from both, slope -0.183 (= its multiple-regression coefficient), r=-0.050. Shows luck's unique contribution: small but separate from the model edge and form.

### B87. Spread-level plot  ·  *Confirmed out of sample*  ⇄
- **Formula / idea:** Spread-level plot: log|resid spread| vs log(fitted); power transform ≈ 1 − slope.
- **Paper:** Emerson, J. D., & Stoto, M. A. (1982). Exploratory methods for choosing power transformations. *Journal of the American Statistical Association, 77*(377), 103-108. UNVERIFIED DOI; record: https://scilit.com/publications/9d66efb6a394f9649018dd9a424da9cd *(citation details partly unverified)*
  - *How they used it:* Extended Tukey's diagnostic plots, including the spread-vs-level plot for batches at different levels. When log(spread) vs log(level) is roughly linear with slope b, the suggested power transformation is p = 1 - b. (The title and abstract were confirmed. Volume/issue/pages are from recall and the DOI was not confirmed.)
  - *Lesson:* Group games by projected total, plot log(residual spread) against log(level), and use the slope to decide whether the error variance needs a transformation or weights.
- **Applied to v4:** Spread-level plot: log(spread of errors) vs log(line level) slope +1.33; suggested power transform 1 - slope = -0.33 (1 = leave it alone). Spread by opener octile: 216:11.3, 222:12.8, 225:12.1, 228:12.1, 230:12.7, 234:13.4, 236:13.0, 242:13.3. The spread of misses grows faster than the line itself (~18% wider from the lowest to highest octile for a 12% higher line). Practical meaning: the same 3-pt edge is worth less win probability in a 240 game than a 215 game; edge measured in SDs (edge / expected noise) may rank bets better than raw points.
- **Carries over:** Same as B84.

### B88. Multicollinearity / VIF  ·  *Warning*
- **Formula / idea:** VIF_j = 1/(1 − R_j²); > 5–10 = problem collinearity.
- **Paper:** O'Brien, R. M. (2007). A caution regarding rules of thumb for variance inflation factors. *Quality & Quantity, 41*(5), 673-690. https://doi.org/10.1007/s11135-006-9018-6
  - *How they used it:* Showed that the "VIF > 10 (or > 4) means trouble" rules are arbitrary. Inflated variance can be offset by larger samples or more variable predictors, and dropping variables to reduce VIF can bias the remaining estimates.
  - *Lesson:* Offensive rating, pace and points per game are highly collinear. Check VIFs, but don't drop a variable just because its VIF is high when the goal is prediction rather than interpreting coefficients.
- **Applied to v4:** Multicollinearity, VIF when raw levels are used as predictors: pred_total 10.8, simple 8.3, open_total 5.5, Lc 1.3, form 1.4. Model 1, the simple average and the opener are all versions of 'how high is this total' (VIF >5-10), so their separate coefficients are unstable. That's why the model works in differences from the line (edge), which cuts the VIFs to e_m1 1.2, Lc 1.0, form 1.2.

### B89. Box-Cox transformation  ·  *Tool*
- **Formula / idea:** Box-Cox: y^(λ) = (y^λ − 1)/λ (log if λ = 0); choose λ by likelihood.
- **Paper:** Box, G. E. P., & Cox, D. R. (1964). An analysis of transformations. *Journal of the Royal Statistical Society: Series B (Methodological), 26*(2), 211-252. https://doi.org/10.1111/j.2517-6161.1964.tb00553.x
  - *How they used it:* Estimated the power lambda by maximum likelihood. Animal survival times in a 3x4 poison-by-treatment experiment gave lambda of about -0.75 (near reciprocal, a "rate of dying"), and a 3^3 textile experiment gave lambda of about 0, a log transform that removed second-order terms.
  - *Lesson:* Game totals are positive and fairly symmetric, so Box-Cox will likely give lambda near 1 (no transform). Use it on skewed inputs such as minutes lost to injury, not on the response.
- **Applied to v4:** Box-Cox on final totals: best lambda = 0.31 (1 = no transform, 0 = log). Suggests a transform of raw totals (between log and square root), consistent with the spread growing with the level in B84/B87; but bets are judged against the line, and the residuals vs the line are near-normal (A20), so it changes little for over/under decisions.

### B90. Box-Tidwell transformation  ·  *No trend*
- **Formula / idea:** Box-Tidwell: test x^α for a predictor via the x·log(x) term.
- **Paper:** Box, G. E. P., & Tidwell, P. W. (1962). Transformation of the independent variables. *Technometrics, 4*(4), 531-550. https://doi.org/10.1080/00401706.1962.10490038
  - *How they used it:* Developed an iterative linearisation method to estimate power transformations of the predictors (rather than the response) in least-squares regression, with worked examples (implemented in `car::boxTidwell`).
  - *Lesson:* If the effect of rest days or travel distance on totals is curved, Box-Tidwell estimates the power to use (e.g., sqrt of distance) instead of guessing.
- **Applied to v4:** Box-Tidwell for the opener as a predictor of the final: x*log(x) term p=0.242, estimated power 2.77 (1 = keep it linear). The final total is linear in the line.

### B91. Deleting observations / robustness  ·  *Tool*
- **Formula / idea:** Deleting observations: refit without flagged points to check robustness (only drop for real errors).
- **Paper:** Knez, P. J., & Ready, M. J. (1997). On the robustness of size and book-to-market in cross-sectional regressions. *The Journal of Finance, 52*(4), 1355-1382. https://ideas.repec.org/a/bla/jfinan/v52y1997i4p1355-82.html (DOI not located)
  - *How they used it:* Re-ran Fama-French cross-sectional regressions with a robust (least trimmed squares) estimator. Trimming the most extreme 1% of observations each month made the size premium vanish, and the negative average size coefficient came entirely from 16 extreme months.
  - *Lesson:* If your totals edge disappears when you drop the 1% most extreme games, it was outliers, not signal. Always report a trimmed or robust refit.
- **Applied to v4:** Deleting observations: dropping the most extreme 1% of bets (|points beaten| >= 50) changes ROI from +8.26% to +8.40% and win rate 56.7% -> 56.8%. Dropping Cook's-flagged games (B80) barely changes the slope either. Results don't hinge on oddball games, and we keep them because they're real.

### B92. Interaction terms  ·  *Suggestive*
- **Formula / idea:** Interaction: y = β0 + β1x1 + β2x2 + β3x1x2; slope of x1 is β1 + β3x2.
- **Paper:** Brambor, T., Clark, W. R., & Golder, M. (2006). Understanding interaction models: Improving empirical analyses. *Political Analysis, 14*(1), 63-82. https://doi.org/10.1093/pan/mpi014 (RePEc: https://ideas.repec.org/a/cup/polals/v14y2006i01p63-82_00.html)
  - *How they used it:* Surveyed articles in the top three political science journals (1998-2002) and found widespread errors in multiplicative interaction models: omitted constitutive terms, and main effects read as unconditional. Only about 10% followed their checklist, and they showed how to plot conditional marginal effects with CIs.
  - *Lesson:* If you model pace x back-to-back, keep both main effects in the model and report the conditional effect of rest at each pace level. The "main effect" of rest is no longer a standalone number.
- **Applied to v4:** Interaction: does the edge work better early in the season (either team under 25 games)? edge slope late 0.573, early adds -0.126 (p=0.530). Edge x direction (overs vs unders): -0.149 (p=0.552).

### B93. Polynomial regression  ·  *No trend*
- **Formula / idea:** Polynomial: y = β0 + β1x + β2x² + β3x³ + ε.
- **Paper:** Fair, R. C. (2008). Estimated age effects in baseball. *Journal of Quantitative Analysis in Sports, 4*(1), Article 1. https://doi.org/10.2202/1559-0410.1074
  - *How they used it:* Fitted a fixed-effects model in which MLB performance (players with 10+ seasons, 1921-2004) rises quadratically to an estimated peak age and then declines quadratically at a separate rate. Peak age was in the late 20s, and aging effects were larger for pitchers than batters.
  - *Lesson:* Quadratic terms suit curved relationships such as roster age or minutes load vs efficiency. Keep the polynomial low-order and don't extrapolate it beyond the observed range.
- **Applied to v4:** Polynomial: y ~ e + e^2 + e^3: e^2 p=0.283, e^3 p=0.150. Cubic coefficient +0.0020: no flattening.

### B94. Nested model F test  ·  *Confirmed (in-sample)*
- **Formula / idea:** Nested F = [(SSE_r − SSE_f)/q] / [SSE_f/(n − p)].
- **Paper:** Chow, G. C. (1960). Tests of equality between sets of coefficients in two linear regressions. *Econometrica, 28*(3), 591-605. https://doi.org/10.2307/1910133 (JSTOR: https://www.jstor.org/stable/1910133)
  - *How they used it:* Derived the F test comparing a restricted model (one set of coefficients for both samples) with an unrestricted one (separate coefficients), the basis of the Chow structural-break test, illustrated with economic demand regressions.
  - *Lesson:* Use a nested F test (`anova(m_small, m_big)`) to check whether a block of new features improves fit, or whether coefficients changed after a rule change (e.g., the 2018-19 shot-clock reset rule).
- **Applied to v4:** Nested models (partial F): adding luck + form + altitude to the Model 1 edge: F=9.69, df=(3,3199), p=2.29e-06. This is the formal test that v4's add-ons beat plain Model 1 on these seasons.

### B95. AIC (and BIC)  ·  *Tool*
- **Formula / idea:** AIC = 2k − 2 log L; BIC = k log n − 2 log L; lower is better.
- **Paper:** Akaike, H. (1974). A new look at the statistical model identification. *IEEE Transactions on Automatic Control, 19*(6), 716-723. https://doi.org/10.1109/TAC.1974.1100705
  - *How they used it:* Introduced AIC = -2 log L + 2k as an estimate of expected predictive (Kullback-Leibler) discrepancy, and applied it to choosing the order of time-series (autoregressive / ARMA) models in place of sequential hypothesis tests.
  - *Lesson:* Compare candidate totals models (e.g., with or without team random effects) by AIC on the training data, but confirm the winner on held-out seasons against the closing line.
- **Applied to v4:** AIC / BIC (lower is better): open only (y~1) AIC 27772.4 BIC 27778.4; M1 edge AIC 27752.3 BIC 27764.4; v4 edge AIC 27724.0 BIC 27736.2; M1 edge + add-ons AIC 27729.3 BIC 27759.6; + rested AIC 27731.3 BIC 27767.7. BIC penalizes extra terms more; the single combined v4 edge has the lowest AIC and BIC, and 'rested' makes both worse: it doesn't earn a place.

### B96. Standardized coefficients / relative importance  ·  *Tool*
- **Formula / idea:** Standardized β = b·(s_x/s_y); ranks predictors on a common scale.
- **Paper:** Johnson, J. W., & LeBreton, J. M. (2004). History and use of relative importance indices in organizational research. *Organizational Research Methods, 7*(3), 238-257. https://doi.org/10.1177/1094428104266510
  - *How they used it:* Reviewed indices for apportioning R-squared among correlated predictors (standardized betas, structure coefficients, dominance analysis, relative weights) and showed that standardized betas mislead when predictors are correlated, as is common in organizational data.
  - *Lesson:* To say which input drives your totals projections (pace vs defense vs rest), use dominance analysis or relative weights rather than comparing standardized betas of collinear features.
- **Applied to v4:** Standardized coefficients (SD change in y per SD of input): e_m1 +0.110, form +0.067, alt +0.051, Lc -0.050, rested +0.000. Ranking: e_m1 > form > alt > Lc > rested. Model 1's edge matters most, then form, altitude and shooting luck about equally; rest adds nothing.

### B97. Adjusted R squared  ·  *Tool*
- **Formula / idea:** Adjusted R² = 1 − (1 − R²)(n − 1)/(n − p − 1).
- **Paper:** Fama, E. F., & French, K. R. (1993). Common risk factors in the returns on stocks and bonds. *Journal of Financial Economics, 33*(1), 3-56. https://doi.org/10.1016/0304-405X(93)90023-5 (RePEc: https://econpapers.repec.org/RePEc:eee:jfinec:v:33:y:1993:i:1:p:3-56)
  - *How they used it:* Ran time-series regressions of 25 size/book-to-market portfolios on market, SMB and HML factors and reported degrees-of-freedom-adjusted R-squared. Adding SMB and HML raised it from the market-only level to above 0.9 for most portfolios, which was the paper's evidence that the factors add explanatory power.
  - *Lesson:* When comparing totals models with different numbers of features, compare adjusted R-squared (or, better, out-of-sample error), since raw R-squared always rises when you add a variable.
- **Applied to v4:** Adjusted R^2: one-predictor v4 edge 0.0153; Model 1 edge + 4 add-ons 0.0143 (raw 0.0158). Adjusted R^2 only rises if a term earns its keep.

### B98. Logistic regression (calibrated win probabilities)  ·  *Confirmed (in-sample)*  ⇄
- **Formula / idea:** Logistic: log[p/(1 − p)] = β0 + β1x; e^β1 = odds ratio per unit x.
- **Paper:** Lopez, M. J., & Matthews, G. J. (2015). Building an NCAA men's basketball predictive model and quantifying its success. *Journal of Quantitative Analysis in Sports, 11*(1), 5-12. https://doi.org/10.1515/jqas-2014-0058
  - *How they used it:* Fitted logistic regressions combining Las Vegas point spreads with possession-based efficiency ratings to give game-win probabilities for the 2014 NCAA tournament. The model ranked first by log loss among about 400 Kaggle entries, and simulations showed even the best model had only about a 12% chance of winning the contest.
  - *Lesson:* Model P(over) with logistic regression that includes the market total as an input, judge it by log loss or Brier score, and bet only when the calibrated probability is above 52.4%.
- **Applied to v4:** Logistic regression: log-odds(over) = -0.004 + 0.0506 x edge (p=3.8e-09). A 3-pt edge -> P(over) 53.7%, 6-pt 57.4%. Calibration by quintile (pred/obs): 43.0%/44.1%, 47.5%/45.7%, 50.2%/49.9%, 52.9%/54.0%, 57.7%/57.6%. This is the honest edge->probability map to use for EV and Kelly instead of the normal curve in A41.
- **Carries over:** Logistic calibration maps any edge to a probability for EV/Kelly sizing.


## ANOVA and multiple comparisons

### B64. Familywise error / multiple testing  ·  *Warning*  ⇄
- **Formula / idea:** Familywise error: P(≥ 1 false rejection) = 1 − (1 − α)^m for m independent tests.
- **Paper:** Harvey, C. R., Liu, Y., & Zhu, H. (2016). ... and the cross-section of expected returns. *The Review of Financial Studies, 29*(1), 5-68. https://doi.org/10.1093/rfs/hhv059
  - *How they used it:* Catalogued 316 published return "factors" and applied Bonferroni, Holm and BHY (FDR) adjustments. They argue a new factor today needs a t-statistic above about 3.0, not 2.0, and that many published factors are probably false discoveries.
  - *Lesson:* If you screened 50 candidate features or betting angles, a single t = 2.1 means nothing. Adjust for every feature you tried, or hold out an untouched season.
- **Applied to v4:** This catalog ran 40 hypothesis tests. Raw p<0.05: 19 (A01, A03, A07, A20, A27, A38, B51, B54, B59, B69, B73, B75, B76, B78, B81, B84, B86, B94, B98). With 0 real effects we'd expect ~2.0 by luck. After Benjamini-Hochberg (false discovery rate 5%): A01, A03, A07, A20, A27, A38, B51, B54, B59, B69, B73, B75, B76, B78, B81, B84, B86, B94, B98. This is the familywise trap of testing many trends on one data set.
- **Carries over:** Multiple testing on one dataset is the #1 reason 'discovered' market anomalies fail (Harvey-Liu-Zhu).

### B65. Bonferroni  ·  *Warning*  ⇄
- **Formula / idea:** Bonferroni: test each at α/m.
- **Paper:** Dunn, O. J. (1961). Multiple comparisons among means. *Journal of the American Statistical Association, 56*(293), 52-64. https://www.jstor.org/stable/2282330
  - *How they used it:* Canonical source of the Bonferroni (Dunn) t-intervals for m pre-planned comparisons. Applied to two-way layouts, the t-intervals were shorter than Scheffe's whenever m was modest, but Tukey's were shorter for pure pairwise differences.
  - *Lesson:* For a handful of pre-planned subgroup checks (e.g., 5 situational angles), test each at alpha/5. It is simple, conservative and assumes nothing about how the checks are correlated.
- **Applied to v4:** Bonferroni: each test must hit p < 0.05/40 = 0.0013. Survivors: A01, A03, A07, A27, A38, B51, B54, B69, B75, B76, B78, B94, B98. Those are the only findings here strong enough to take forward as candidate 'real' trends; everything else is exploratory.
- **Carries over:** Bonferroni / FDR before believing any scanned-for trend.

## Adding a new concept (do this every time)
1. Add the formula/idea with the next ID (A48+, B99+, or a new letter for a new course/source).
2. Find one peer-reviewed paper from a mainstream journal that applied it; verify the citation and DOI.
3. Add a block to `run_all.py` that applies it to the same v4 data (`build.py` output), calling `rec(ID, text, p)` with a p-value if it's a test.
4. Rerun. The multiple-testing count in B64/B65 updates automatically: a new trend has to clear the new, stricter bar.
5. Anything that passes: add it to `oos.py` and check it on 2011-19 (and NHL / other markets) before calling it real. Mark ⇄ if it should carry over.
6. Update the status, the summary above, and `analysis/FINDINGS.md`.
