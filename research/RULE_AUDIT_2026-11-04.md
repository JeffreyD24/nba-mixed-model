# Rule audit: are the alert gates costing us bets? (Nov 4, 2026)

Same file in all three repos (research/RULE_AUDIT_2026-11-04.md). Prompted by the ATL @ WSH under (Nov 4): the model liked the
under at DraftKings' 234.5 opener (4:40 PM Nov 3), but no bet alert went out until 8:45 AM the next day at 233.5.
**Nothing live was changed by this audit.** Every proposed change below needs approval and would start a new version record.

Scripts and outputs:
- NBA: `nba-mixed-model analysis/rule_audit_injury_timing.py`, `analysis/rule_audit_line_rules.py` (+ `_output.txt`)
- NFL: `nba-mixed-model analysis/rule_audit_nfl.py` (+ `_output.txt`)
- NHL: `nhl-mixed-model analysis/rule_audit_nhl.py` (+ `_output.txt`; needs the rebuilt `box_hist.csv` / `shots_hist.csv`, which are gitignored)

Method: every bet is graded at a DraftKings line or price that existed at the moment of the bet, using only information known
then (hourly DK snapshots for the NBA and NHL; ~3-hour snapshots for the NFL). Units at -110 unless real prices were available.

## The big one, in all three sports: the backtests graded bets at the opener using information that came later

| Sport | What the backtest assumed | Reality | Honest record at a bettable time |
|---|---|---|---|
| NBA totals | opener + 8 PM night-before injury report | **74%** of DK openers post before 8 PM (mostly 2-7 PM) | opener with the info already out: **+109.3u** (1,565 bets, 56.0%) vs +126.7u as backtested |
| NFL totals v2 | opener + an "early number" built from last week's games and final report | **98%** of openers post ~6.7 days before that number exists | Tuesday 10 AM line: **+11.6u** (332, 54.2%) vs +20.3u (no weather) |
| NHL moneyline | opener filtered by Pinnacle's first price | Pinnacle posts a median 10.6 h after DK for these bets | betting every opener: +133.9u; the Pinnacle follow-up removes ~break-even bets (+9.1u as coded) |

The edges are still real (all three keep beating the closing line), just a bit smaller than the headline numbers.

## NBA (totals; tested on the live totals number, morning lock, 2023-24..2025-26)

### 1. "Current injury report" gate: CHANGE
Live this season it blocked 29 of 84 alert rows (21 "no current report", 8 "a team has not filed"). Because the opener is then 1+ h
old by the time the report lands, an unmoved line becomes OPTIONAL (not pushed). So in practice the opener can almost never be bet.

| Bet timing | Bets | Win % | Units | per 100 |
|---|---|---|---|---|
| Opener + previous game's report (**bettable as the line posts**) | 1,565 | 56.0% | **+109.3u** | +7.0 |
| Opener + 8 PM report (the backtest; not bettable for 74%) | 1,559 | 56.6% | +126.7u | +8.1 |
| ~9 PM line + 8 PM report, minus lines moved against (closest to "wait, then follow the rule") | 934 | 56.4% | +72.1u | +7.7 |
| ~9 PM line, only lines that moved toward the model (**what live pushes now**) | 265 | 55.8% | +17.5u | +6.6 |
| ~9 AM game-day line + 8 PM report | 1,536 | 53.6% | +37.1u | +2.4 |

- The previous game's report is a conservative stand-in (live you'd also have any 5-7 PM report). It moves the model total only
  0.6 pts on average (correlation 0.99). The 8 PM report is worth ~4u over three seasons; the opener price is worth ~70u+.
- Openers post 2-7 PM, while you're awake. Waiting for 8 PM pushes the bet past your bedtime, so in practice you bet the next
  morning, the worst timing in the table.
- Safety net: if the 8 PM report later drops an opener bet below 3 or flips it, those bets were about break-even (159 bets, -2.5u).
  A DON'T BET for those (if not yet placed) is harmless; no need to hedge ones already placed.
- **Proposed:** alert at the opener as soon as it's seen, using the latest report available (same rule for spreads in their live
  window). Keep the 8 PM recheck as a DON'T BET for unplaced bets it flips.

### 2. OPTIONAL for an unmoved line older than 60 min ("unmoved for hours ~49%"): DROP
The 49% figure didn't reproduce for totals. With 3+ edge at the line at that time, lines that had not moved since the open won at
every check time: 9 PM 56.7% (+54.5u, 669 bets), midnight 56.6%, 9 AM 57.0%, noon 60.6%, 3 PM 58.1%. They're the best group of the
three, positive in 13 of 15 season-by-checkpoint cells. **Proposed:** treat an unmoved line with 3+ edge as BET (pushed) at any time.

### 3. PASS when the line moved 0.5+ against: KEEP
At night it's right: against-moved lines lost (9 PM 49.8% -15.8u; midnight 51.2% -13.7u). During game day it's mixed (9 AM +16.6u,
3 PM -10.9u, 6 PM -22.8u). By size (9 AM): 3+ pts against 48.9% -21.7u; small moves 0.5-2 pts were positive (+39.5u, 369 bets).
Weaker evidence than the "43%" quoted in alerts, but there's no case for removing it; a "1.5+ pts" version is a candidate to watch.

### 4. BET when moved toward with 3+ left: KEEP
Positive at night (9-10 PM +17.5u / +23.9u), mixed during the day. Fine as is.

### 5. 3-point edge threshold: KEEP
Edges 2-3 at the opener were +11u (8 PM report) or +47u (previous report) on ~500 bets; inconsistent, so not a basis to lower it.
Worth tracking 2.5-3 as a test bucket.

### 6. Spreads re-test (analysis/rule_audit_spreads.py): the injury report DOES matter for spreads
Live spread number (Model 1 + 0.11 x last-10 margin form + 0.57 x roster delta), live windows (Oct-Jan no home dogs; Feb-Apr outside traps):
| Bet timing | Bets | Win % | Units |
|---|---|---|---|
| Opener + 8 PM report (as documented; 73% not bettable) | 402 | 59.2% | +52.4u |
| Opener + previous game's report | 417 | 54.0% | **+12.5u** |
| ~9 PM line + 8 PM report | 311 | 59.8% | **+44.1u** (+36.5u excluding games whose "8 PM" report was really a game-day report) |
| ~9 AM game-day line + 8 PM report | 349 | 57.0% | +30.9u |
After the report: unmoved 9 PM 58.9% +23.1u; moved toward +8.6u; moved against fine at 9 PM but negative by 9 AM-3 PM. Who plays matters
far more for a margin than a total, so **spreads keep the report gate**; unmoved lines become BETs like totals.

## NFL (full table: analysis/rule_audit_nfl_output.txt)
| Rule | Verdict | Key numbers |
|---|---|---|
| No BET before Friday's final injury report | **CHANGE**: allow BET early in the week on the locked early number | Tue 10 AM +11.6u (332) vs live rule +3.5u (132); Fable's review: the early number in that test still knew the same week's Thursday game, the honest cut is **+7.6u** (no weather) / +6.1u (forecast weather). Still better than waiting |
| PASS on 0.5+ against | KEEP | weak, right direction (Tue: against +2.1u, toward +6.0u); NBA "unmoved best" pattern does not repeat |
| Totals edge 2.0 | KEEP | below 2 loses at Tue (-17.1u) |
| Weeks 1-4 and 15+ test-only | KEEP | -16.2u and -34.5u at Tue |
| Spreads test-only | KEEP | -3.2u at Tue |
| MAX_PRICE, DON'T BET, 2H totals rule | KEEP / untestable | 2H has only open/close lines |
- **Bug:** the test-only branch re-logs the same game every check (CHI-SEA written 119 times, all graded L), inflating the
  "Caution alerts so far" count. The alert text also still quotes the pre-audit +21.3u record.

## NHL (full table: nhl-mixed-model analysis/rule_audit_nhl_output.txt; moneyline / puck line / overs, 2021-22..2025-26)
| Rule | Verdict | Key numbers |
|---|---|---|
| Back-to-back skip, puck line | KEEP | blocked 137 bets 35%, -37.3u, negative 4/5 seasons |
| Back-to-back skip, moneyline | CHANGE: puck line only | blocked bets +0.9u under the live blend (old -40u figure was the puck line / raw model) |
| Pinnacle already posted at alert | KEEP | blocks 27 bets -8.8u (small) |
| Pinnacle DON'T BET follow-up | **CHANGE or DROP** | quoted -42u was look-ahead; bettably it blocks +9.1u as coded (+0.2u vs DK's current price) |
| Overs only, ML EV 4%, overs EV 6% | KEEP | unders -6.0u; ML 2-4% band mixed |
| Puck line EV 6% | CHANGE to 9% (re-test after 2026-27) | 6-9% band 514 bets -11.1u, negative 4/5; 9%+ +90.2u |
| Opener-only moneyline (moved prices info-only) | CHANGE: push moved moneylines at EV 9%+ | 50 bets +18.5u, 0/5 negative (small) |
| DON'T BET when ML EV dips under 4% | CHANGE: not while price is within 1.5 pts of the alert | those bets 113, +26.0u, 4/5 positive |
| One bet per game | **CHANGE**: prefer the moneyline (or bet both) | compares blended ML EV to raw puck-line EV; dropped ML legs +57.3u (0/5 neg) |
- Stale explanations: alert.py comments, alert text and config/thresholds.csv still quote pre-blend numbers (-42u, -40u, +67.5u).

## Takeaways and advice
- **The single most valuable fix is timing, in every sport: get the alert out when the opener posts.** NBA openers land 2-7 PM
  while you're up; the current injury gate is turning ~+36u/season of NBA totals at the opener into next-morning bets worth about a third
  of that (~+12u/season at 9 AM lines).
- The injury report rules were built to avoid betting on stale news, but the measurements say stale news costs ~0.6 pts of model
  total while waiting costs the whole opener price. Re-check after the report and send DON'T BET if it flips; don't wait for it.
- Several rules were justified with figures that had look-ahead or came from an older model. The verdicts above replace them;
  the alert text should quote the honest numbers.
- Every record reported so far was a little optimistic. Plan bankroll and expectations on the honest numbers (NBA totals
  ~+7u/100 at the opener; NFL totals ~+3.5u/100 at Tuesday; NHL moneyline ~+12%).
- Small-sample changes (NHL moved-price ML, puck line 9%, NBA 2.5-3 bucket) should start as tracked tests, not live bets.

## Changes made (Nov 4, 2026, approved by the user; independently reviewed by Fable before/after going live)
| Sport | Change | Version record |
|---|---|---|
| NBA | Totals alert at the opener on the latest injury info (no 8 PM wait); spreads keep the wait | NBA totals v5 (12:47 ET) |
| NBA | Unmoved line with 3+ edge = BET at any time (was OPTIONAL, not pushed); no bet alert after tip | NBA totals v5 / NBA spreads v3 |
| NFL | BET from early in game week on the locked early number (Tue 10 AM; another session then moved it to Mon 10 AM, NFL totals v4); test-only logging deduped; 2H total display fix; honest numbers in alert text | NFL totals v3 -> v4 |
| NHL | Puck line EV 9% (6-9% logged as TEST); prefer moneyline when both qualify; ML b2b skip removed (puck line keeps it); Pinnacle post-alert DON'T BET dropped; no ML DON'T BET for price-only dips within 1.5 pts while EV >= 0 and the model's win chance is unchanged | NHL v4 |

Fable review notes kept for later: ~10% of NBA openers post before the 11:40 AM run saves tomorrow's model (caught later by the unmoved
rule); the audit replays a v3-like totals number (no shrink/altitude); roster strength and late-season standings use data through the
night before (lag 0) while the model is lag 1 (small); an unlogged NBA alert sent mid-afternoon the day before can produce ~25
reminders before tip at the 30-min cadence.
