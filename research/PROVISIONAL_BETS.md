# Provisional bets: bet it while we prove it (rule set Nov 4, 2026, Jeffrey)

Some ideas look profitable on past seasons but are not proven (CLV short of break-even, few bets, or chosen on the same seasons
they were tested on). Instead of waiting seasons, we **bet them as PROVISIONAL**, keep a separate record, review them on a fixed
schedule, and **stop them by a rule written before the first bet**. A provisional bet is never quietly folded into a proven rule.

## Rules for every provisional bet
1. **Entry:** past seasons show positive units with an honest test (only information known at bet time), but it fails or is short of
   the pre-registered bar. Jeffrey approves it. It gets a row in the registry below with its backtest numbers.
   **If its backtest CLV is at or below 0** (added Nov 5, 2026, Jeffrey): it isn't ruled out, but it must pass ALL of these extra
   checks before entry, each written down before it is run:
   - **Unseen seasons:** units > 0 in every season not used to build or choose it (at least two such seasons), and the pooled
     ROI's 90% CI above 0.
   - **Explain the negative CLV, and test the explanation on separate data:** e.g. if the close itself is biased (prop closes lean
     to overs), measure that bias out of sample and show CLV adjusted for it is ≥ 0; or show the model predicts the result beyond
     the close in a held-out season.
   - **Beats the simple version:** it must beat the simplest rule that could explain its profit (e.g. blind unders at the best book)
     on the same games, otherwise the simple rule is what goes in instead.
   - **Fable review** of the evidence, as for every live change.
   Once live, CLV can't be its stop signal, so the units stop lines in rule 3 apply with one addition: after 50 graded bets, units
   below 0 stops it even if CLV has improved.
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
| **NBA props v1b at FanDuel openers** — three tiers, each its own record and its own stop lines (`props_shadow.py live`, params `data/props_v1b_open_params.json`, rows in `state/props_live.csv` with `tier` = provisional_early / _late / _stale; logged props get the matching version in bet_record.py). Common rule: FanDuel, line unchanged since FanDuel's opener and price within 5 cents of it, line ≥ 0.5, EV ≥ 5% at both the opening and current price, prices 100-1000, no April, no result from the opener's own day in the features, 1h+ before tip. Alerts 24 hours a day. **early** = opener first seen ≤ 40 min ago and verified by an earlier snapshot, posted 4h+ before tip (the backtested slice). **late** = same but posted 1-4h before tip. **stale** = still at the opener but not a fresh/verified opener (e.g. caught later). | Nov 6, 2026 (approved by Jeffrey Nov 5; late and stale tiers added by him the same day) | Clean re-test 2023-24 + 2024-25 at BettingPros openers: all DK/FD 1,649 bets +83.7u (+5.1% [+1.3, +9.1]). FanDuel 4h+: 605 bets +23.3u (+3.9%), raw close-EV +2.24%, lines move our way +0.29. FanDuel 1-4h: 241 bets +53.7u (+22%), CLV ~0, 55% of the test profit from 132 bets in 2023-24. Stale: not tested (BettingPros has no in-between snapshots). April −53u in 3 of 4 seasons. Fable reviews in research/props/reviews/. `analysis/props_v1b_opener_clean_output.txt`. | early ~1/day, late ~0.5/day, stale unknown | live from Nov 6, provisional (3 records) |
| **NBA totals line-movement bets, market models v1-an** (`market_models_live.py`, alerts in `state/market_models/movement_alerts.csv`, tier `provisional_movement`): every 5-minute check fetches Action Network's current full-game totals (DraftKings, FanDuel, Caesars, BetMGM, BetRivers) and predicts where DraftKings' total will close vs now (book gaps at that moment, DK price lean, move so far, the opener-formula residual). BET the first time the predicted move is 1.5+ pts, on the side the line should move toward, at DK now; games 0.5-48 h from tip. Not pushed when the main totals model already has a BET on the game (same side: not sent twice; other side: conflict), or the price is worse than -120 and FanDuel is no better; those are still graded in the rule's record. DON'T BET follow-up when the predicted move drops under 0.5 pts. | Nov 5, 2026 (Jeffrey: alerts with money) | Pre-registered step 3 (research/market_models/STEP3_MOVEMENT_PREREG.md, fd8a220) and its feed addendum (7f40f5e): the Odds API live feed with Pinnacle paused Nov 5 (credits), so the live model uses only books Action Network carries. 2025-26 test 505 bets, CLV +1.41, +5.4u, but 144 of those used a box score from a game not yet played (Fable check). **Bets the live code could actually make (after the morning run following both teams' previous games, 48 h or less): 385 bets, CLV +1.31 ± 0.16 (break-even +1.07), -10.8u, 51.2%**; 2024-25 519 bets, CLV +1.59, +19.4u. Live on CLV (the addendum's live bar), units unproven. CLV check: 1 pt of CLV = +2.2% wins in NBA totals every season 2021-26, so +1.31 is worth roughly +0.5% per bet before luck. `research/market_models/STEP3_MOVEMENT_RESULTS.md`. | ~2-4 triggers a day (~500 a season), fewer pushed | live, provisional |
| **NBA totals blend v4 + market, market models blend v1** (`market_models_live.py`, `state/market_models/blend_alerts.csv`, tier `provisional_blend`): one decision per game at the first 5-minute check at or after 9 PM ET the night before (or when DraftKings first posts): fair total = -14.0 + 0.31 × v4 + 0.76 × (DK now + expected move from the movement model); BET when |fair - DK now| >= 2 pts, at DK now. Not sent twice when v4 or the movement rule already has a BET on the same side; skipped on a conflict; price rule as above. DON'T BET follow-up when the edge at DK now falls under +1.07 (judgment). | Nov 5, 2026 (Jeffrey: provisional bets go live with money) | Pre-registered step 4 (research/market_models/STEP4_BLEND_PREREG.md, c0f08c4): First run 314 bets, CLV +1.79, +23.3u, but its 9 PM decision could use a box score not played yet (Fable check). **Honest timing (decision after both teams' box scores are in): 2025-26 257 bets, CLV +1.44 ± 0.18 (break-even +1.07), +1.8u, 52.9%**, vs v4 alone at the same moment 598 bets CLV +0.79, +18.4u. Still passes all three conditions; units thin. 89% overs. v4 is partly in-sample on 2023-26. `research/market_models/STEP4_BLEND_RESULTS.md`. | ~300 a season, fewer pushed (overlap with v4) | live, provisional |

**Break-even correction (Nov 5, 2026):** NBA full-game totals break-even CLV is **+1.07 pts**, not +0.33. The +0.33 was an
"at the act line" figure from the line-move model test. The direct check (1 pt of CLV = +2.2% win rate, every season 2021-26)
gives +1.07. `provisional_review.py` now uses +1.07 for every totals rule; the 2.5-3 pt totals rule's backtest CLV (+1.10) is
therefore right at break-even, not three times above it.

| **NCAAM stale-line spreads** (`ncaab/live_alert.py`): BET DraftKings' first college basketball spread when it is 0.5+ pts off the predicted close (BLEND-C: opener + lagged market-implied ratings + M2 + M8). Both teams 3+ games and a conference id, no UConn / Connecticut-hosted games, price -115 or better. Alerts only on a DraftKings opener first seen within 20 minutes. | Nov 5, 2026 | DraftKings' own opener 2023-24 + 2025-26 (ESPN feed, pre-game filters only, Fable-corrected): 623 bets 57.9%, +65.5u, CLV +1.27 (break-even 0.63); ESPN BET 2024-25 57.1% +34.2u; other books' later openers flat (the edge is in the FIRST number). `ncaab/research/MODEL3_RESULTS_2026-11-05.md`. Stops: -15u any time; at 100 graded bets stop if CLV < +0.63 or units < 0 (CLV near +0.6 = we are not getting the opener). | ~6-7 a day in season | live, provisional |
Volume note: this first rule is small, so its 25/50-bet checkpoints will take most of a season or more. The weekly review is mostly a
scoreboard until then; the -10u line is the safety net in the meantime.

The whole news-bet group (provisional plus the ones v3 already bets on unmoved/toward lines) is tracked through `news_bet` on every
alert row, so we also learn whether injury-news bets in general beat the close (the test bucket approved Nov 4).
