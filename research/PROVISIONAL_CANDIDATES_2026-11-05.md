# Review: tracked-but-not-bet ideas, which to bet as PROVISIONAL (Nov 5, 2026)

Jeffrey (Nov 5): widen the bets placed with money; ideas that beat the close but miss a hard rule go live as PROVISIONAL
(labeled, own record, stop lines in research/PROVISIONAL_BETS.md). This is the sweep of everything tracked but not bet in
the NBA, NHL and NFL repos (and ncaab/), with the evidence each one has. CLV first, units second.

## Going live today (NBA, PROVISIONAL)
| Rule | Evidence | Why |
|---|---|---|
| NBA totals line-movement (market models v1-an) | 2025-26, honest timing (Fable): 385 bets, CLV +1.31 (break-even +1.07), -10.8u | Pre-registered addendum; live on CLV |
| NBA totals blend v4 + market (market models blend v1) | 2025-26, honest timing: 257 bets, CLV +1.44, +1.8u; beats v4's CLV per bet (+0.79) | Pre-registered step 4; passes, units thin |

## Recommended next (needs work in the NHL / NFL repos)
| Idea | Evidence | Recommendation |
|---|---|---|
| **NHL: back the rested team vs a team on a back-to-back** (opening moneyline, no model) | 2024-26 DK: 538 bets, +41.9u (+7.8%); 2016-22 holdout: 1,832 bets, +2.0%. Price CLV vs the no-vig close is about zero (+0.3% at DK 2024-26; -1.6% on 2016-22 consensus prices). **But the close itself underprices rested teams:** they won 57.7% vs 55.3% the no-vig close implied (2016-22, ~2 se) and 59.7% vs 55.8% (2024-26, ~1.9 se). Exploratory, not pre-registered. | This is a closing-line blind spot, not a CLV edge, so it fails the CLV-first rule but has two independent periods behind it. Bet as PROVISIONAL in the NHL repo with a pre-registered stop rule, graded on units **and** "won vs no-vig close". Needs NHL code + Fable check. |
| **NFL second-half totals** (TESTED Nov 5: FAILED, alerts stopped; nfl-mixed-model research/halves/H2_TOTALS_RESULTS.md) | Already being bet with money (3 bets in state/my_bets.csv) though alerts are labeled TEST. Backtest 52-35, best of ~100 slices; CLV not measured. | Tested and stopped Nov 5: 2023 (unseen) 66 bets, 26-39, -15.4u; no beat-the-close in 2023 or 2018-21. Alerts TEST-only. |

## Not promoted (and why)
| Idea | Evidence | Why not |
|---|---|---|
| NBA totals stack (side-by-side record) | Lockbox 2023-26: 1,647 bets, CLV +1.38, +42.5u | Most of its bets are v4's bets (already live). Its **extra** bets, the ones that would be added, had CLV +0.43 to +0.85 and -23.5u to -5.5u on 2024-26 (analysis/nba_v4_vs_stack_output.txt). The v4-vs-stack decision at the All-Star break stays. |
| NBA opener residual (step 2) | 2025-26 CLV +1.00, -18.5u | Below break-even; already the strongest input of the live movement rule. |
| NBA report watcher (news within minutes) | Upper bound CLV +1.17 (2+ pt daytime news); honest version 20 bets CLV +0.23 | Its own pre-set check (100 events or Dec 15) decides. Its totals bar should use +1.07, not +0.33 (fix noted). |
| NCAAM M2 totals; Model 3 totals; Model 1 spreads | CLV +1.21 / +1.17 / +0.62 vs break-even 1.02 / 1.02 / 0.67, units negative | Pre-set live checks already decide (Fable review at ~300 bets; 150 bets). |
| NFL player model totals | SBR 2016-19 CLV +1.00 to +1.10, +10-12%; 2020-21 CLV +1.38, -0.5u | NFL totals break-even CLV not measured yet; measure it, then re-grade 2020-25 at DK openers. |
| NBA team totals | CLV +0.64 (break-even +0.67) | Same edge as full-game totals, split in two; bet the full total. |
| Everything with CLV at or below 0 or look-ahead (props v1b, 1-pt-against totals, 1H/1Q, NHL goalie re-check, NHL PL 6-9%, NFL spreads, NFL home dogs, NCAAF, NCAAM conference totals) | see the source files | Stays tracking-only (standing rule: CLV <= 0 needs more evaluations first). |

## Personal note
Two of the borderline ideas turned out weaker than their headline: the stack's lockbox numbers come mostly from bets we
already make, and the NFL 2H totals have no CLV at all. The one genuinely new lead is the NHL rest rule: it doesn't beat the
close, it beats the **result** the close predicts, in two separate periods. That's rarer and worth a proper test.
