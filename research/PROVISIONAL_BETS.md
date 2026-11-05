# Provisional bets: bet it while we prove it (rule set Nov 4, 2026, Jeffrey)

Some ideas look profitable on past seasons but are not proven (CLV short of break-even, few bets, or chosen on the same seasons
they were tested on). Instead of waiting seasons, we **bet them as PROVISIONAL**, keep a separate record, review them on a fixed
schedule, and **stop them by a rule written before the first bet**. A provisional bet is never quietly folded into a proven rule.

## Rules for every provisional bet
1. **Entry:** past seasons show positive units with an honest test (only information known at bet time), but it fails or is short of
   the pre-registered bar. Jeffrey approves it. It gets a row in the registry below with its backtest numbers.
2. **Labeled everywhere:** alerts say PROVISIONAL, alert rows carry `tier=provisional`, and `bet_record.py` gives logged bets their
   own version line ("PROVISIONAL: ..."), so they never mix with a proven record. 1 unit per bet, same as everything else.
3. **Stop rule (any one, checked at every review; fixed in advance, not adjusted after seeing results):**
   - at any point: -10 units or worse;
   - after 25 graded bets: -5 units or worse;
   - after 50 graded bets: CLV at or below 0, OR units below 0.
4. **Promote to a normal rule** (needs Jeffrey's approval, new version row): at 100+ graded bets, CLV at or above that market's
   break-even (NBA spreads +0.77 pts) and units > 0.
5. **Still undecided at 150 bets** (no stop, no promotion): stop it. Not proven after that many bets means the edge, if any, is too
   small to tell from the vig.
6. Measures are the same as everywhere: CLV first, units second, accuracy alongside. Each provisional rule is graded on every alert
   the rule called a BET (whether or not it was placed) and, separately, on the bets actually logged.

## Review schedule
- **Weekly (Monday ~8 AM ET), scheduled task:** `python provisional_review.py .` prints each provisional rule's scoreboard and which
  stop/promote line, if any, it has crossed. Short note to Jeffrey; anything crossing a stop line is flagged for a decision.
- **Daily:** the same script runs in the health check, so a stop line crossed mid-week is caught the next morning.
- **Monthly (first Monday):** the weekly review also re-reads this registry: still worth running? anything to add or retire?

## Registry
| Rule | Since | Backtest evidence | Expected volume | Status |
|---|---|---|---|---|
| **NBA spread injury-news bets** (`PROVISIONAL_NEWS_SPREADS` in alert.py): after the 8 PM night-before report, a 3+ edge on a side the pre-report model did not have at the opener, bet even if the line moved 0.5+ against since the open (normally a PASS). v2/v3 filters, price and Pinnacle rules still apply. | Nov 4, 2026 (v3.1) | 2023-26 at the 7 AM line: 51 bets 60.8% +8.2u, positive all 3 seasons, **CLV +0.19** (weak). All news bets incl. the ones v3 already bets: 75 bets 65.3% +18.5u, CLV +0.42. `research/spreads/STEP3A_NBA_RESULTS.md`. Leakage audit Nov 4 (`research/spreads/STEP3A_LEAK_AUDIT_RESULTS.md`): no leak found, but this provisional slice (news bet AND line moved against) overlaps the no-report "stale model fades an overnight move" bets, which also won (65.5%) with CLV -0.18; treat its wins as weak evidence, CLV decides. Stop lines unchanged. | ~15-20 bets a season (news bets in total ~25) | live, provisional |
| **NBA totals 2.5-3 pt edges** (`TOTAL_THRESHOLD` = 2.5 in alert.py; alert rows `tier=provisional_totals`): totals with 2.5-3.0 pts of edge, same timing, price and line-move rules as the proven 3+ totals. | Nov 4, 2026 (totals v6) | 2023-26 at DK openers, live v4 model: 309 bets 55.3% +17.5u, **CLV +1.10** (break-even +0.33). In-sample: luck/form/altitude weights were fit on these seasons. The 2.0-2.5 band was flat (302 bets +1.5u, CLV +0.88) and was not added. Sweep: claude/threshold_sweep_shopping_roadmap_2026-11-04.md. | ~100 bets a season | live, provisional |

Volume note: this first rule is small, so its 25/50-bet checkpoints will take most of a season or more. The weekly review is mostly a
scoreboard until then; the -10u line is the safety net in the meantime.

The whole news-bet group (provisional plus the ones v3 already bets on unmoved/toward lines) is tracked through `news_bet` on every
alert row, so we also learn whether injury-news bets in general beat the close (the test bucket approved Nov 4).
