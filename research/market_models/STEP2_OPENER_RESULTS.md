# Step 2 results: opener models for NBA totals (Nov 5, 2026)

Pre-registration: `STEP2_OPENER_PREREG.md` (committed d08f49b before any fitting).
Code: `build_opener_data.py` (dataset), `opener_models.py` (models + pre-registered test), `opener_followups.py` (exploratory).
Outputs: `opener_data.csv.gz`, `opener_residuals.csv` (per-game predictions and residuals, 2024-25 and 2025-26), `opener_results.json`.

## Verdict
**The pre-registered bet fails. Do not bet opener residuals by themselves.** But the residual is a real,
repeatable predictor of **where the line moves**, so it goes into step 3 (movement model) as an input.

| DraftKings, bet against residual of 3+ pts | Bets | CLV (pts) | Break-even CLV | Units | Win % |
|---|---|---|---|---|---|
| 2024-25 (validation, exploratory) | 471 | **+2.12** | +1.07 | **+33.2** | 56.1% |
| **2025-26 (pre-registered test)** | 381 | +1.00 | +1.07 | **-18.5** | 49.9% |

Written rule: pass needs CLV > 0 **and** units > 0. CLV was positive, units were not, so it fails. It also fails the stricter
bar this project now uses (CLV above break-even, +1.07 pts for full-game totals: result sd 18.0 pts around the DK close,
so -110 needs about 1.07 pts). That break-even line should have been in the pre-registration and was left out by mistake; it
would not have changed the verdict. Pinnacle and FanDuel (information only) show the same pattern: CLV +0.5 to +1.5, units
positive in 2024-25 and negative in 2025-26 at every threshold.

## How well each book's opener can be predicted (mean absolute error, points)
Validation on 2024-25 picked the model; 2025-26 was scored once. Refit every 14 days within a season on earlier games only.

| Book | Naive (recent closes) | Linear | Boosted trees | **Mixed (chosen)** |
|---|---|---|---|---|
| DraftKings 2025-26 | 3.50 | 2.49 | 2.66 | **2.41** |
| Pinnacle 2025-26 | 3.75 | 2.59 | 2.85 | **2.52** |
| FanDuel 2025-26 | 3.66 | 2.60 | 2.76 | **2.50** |

The mixed model (linear + a shrunk team-by-season "total tendency" effect, BLUP) won for every book in both seasons. Boosted
trees were second in validation but fell to third on the test season, the usual sign of overfitting.

**What each part does**
- `fund_total`: expected pace x both teams' offensive and defensive efficiency (box scores, weighted to recent games). The biggest input for every book.
- `mkt_total`: average of each team's recent DraftKings closing totals. Second biggest: books anchor on where the market has recently closed these teams.
- `league_lvl`: league-wide scoring level from earlier dates (books track scoring trends).
- Team-season effects: whatever a team's totals run high or low on beyond those numbers (style, defensive scheme), learned and shrunk as the season goes.
- Injuries at open, rest, back-to-backs, previous opener errors, hours before tip: small corrections.

## What we learned
1. **Books open about 2.4-2.5 points from a public-data formula.** DraftKings' first total sits within 2.4 points of a
   model built only from box scores, recent closing lines and injury reports. Pinnacle and FanDuel are the same.
2. **When DraftKings opens off that formula, the line comes back.** Residual vs (close - first seen): correlation
   -0.39 (2024-25) and -0.18 (2025-26). Bets against a 3+ point residual had positive CLV 56-67% of the time, in both seasons. That is the opener
   inefficiency the plan was looking for, and it is real.
3. **But it doesn't win at the final score.** Residual vs (final - first seen): -0.12 in 2024-25, +0.04 in 2025-26. The
   close fixes the opener; the opener's miss isn't a miss on the game. So it's a CLV signal, not a result signal, and in 2025-26
   the CLV was not big enough to pay the vig.
4. **DraftKings and Pinnacle "go off formula" together** (residual correlation 0.87). When both books deviate the same way,
   it's information our features don't have (late injury news, lineup reports), not a book mistake. Those bets did worst
   (2025-26: 346 bets, CLV +0.79, -19.7u).
5. **The best-looking split can't be bet as is.** Bets where DraftKings is off formula but Pinnacle isn't: CLV +5.2 (2024-25)
   and +2.8 (2025-26). But Pinnacle's first line is seen hours **later** than DraftKings' (step 1), so this uses information that
   didn't exist when DraftKings' first line was there. Same timing trap as step 1. It has to be re-tested with both books at
   the same moment, which is exactly step 3's job.

## Personal note and takeaways
- **Not a bet, but a building block.** I wouldn't bet opener residuals on their own: one good season, one bad, and the bad one
  was the pre-registered test. What it does give us is a strong input for the movement model: "DraftKings opened 3+ off its
  usual process" predicted the direction of the move both seasons.
- **This answers part of goal #1** ("how do bookmakers create opening lines"): mostly pace x efficiency plus where the
  market has recently closed each team, nudged by league scoring trends and injuries. Nothing exotic.
- **Why the seasons differ** is worth one look: 2025-26 snapshots were every 20 minutes (vs 30) so the "first seen" line is
  closer to the true opener and has less room to move. The live 2026-27 tracker catches true openers within 5 minutes, which
  will settle whether the residual is bigger at the real open.
- **Caveats.** Injury features are from the night-before report, roughly when DraftKings' first line shows up (median 24 h
  before tip), not matched to the minute. 27 team-games with broken box scores were left out of the averages; 15 games with
  two API event IDs were merged.

## Next (step 3: movement model)
Target: close - current line at each snapshot. Inputs: this opener residual (DK and Pinnacle, **at the same snapshot time**),
the DK-Pinnacle gap at that moment, hours to tip, splits (2026-27 only), injury news since open, and our model's edge.
Pre-register with a break-even CLV line. Shadow-track the opener residual in 2026-27 (no alerts) so the live true-opener
version gets its own record.
