# College model tournament: pre-registration (Nov 5, 2026)

Pushed before any tournament model was compared with a line. Applies to NCAA men's basketball (NCAAM) and college football (NCAAF).
Code: `ncaab/tournament.py` (one script, both sports).

## Entrants (all walk-forward, refit every game date, same base settings: ridge 5, carryover 0.8)
1. **M1** Model 1 as it is (team points, flat league scoring level per season).
2. **M2 moving level**: the league scoring level is a recency-weighted average of points scored before each date (half-life H);
   team effects are fitted relative to the level at the time of each game. Knob H in {14, 30, 60} days.
3. **M3 regulation only** (NCAAM only): fitted on regulation points (overtime scaled out by 40/(40+5 x OT periods)); predicted totals
   put overtime back with the season-to-date average ratio of actual to regulation points.
4. **M4 multiplicative**: the same model on log points (offense x defense instead of offense + defense), predictions exp(.).
   Knob: ridge in {2, 5, 10, 20} on the log scale.
5. **M5 everything**: M2 + M3 (NCAAM) + M4 combined, using each one's chosen knob.
6. **M6 average** of M1-M4 predictions (no knob).
Knobs are chosen **only** by prediction error vs results (margin MSE + total MSE, each relative to the best) on the tuning season
(NCAAM 2022-23, NCAAF 2022), as Model 1 was. No line is used to choose them.

## Comparison (lines)
Same fixed thresholds and filters as Model 1 (NCAAM spreads 5+, totals 6+; NCAAF spreads 2+, totals 2+), bets vs the Open,
CLV = Open to DK close. Seasons: NCAAM 2023-24, 2024-25, 2025-26; NCAAF 2023, 2024, 2025.
- **Winner per sport and market = highest average CLV per bet over those seasons** (CLV is the primary measure: in all four leagues
  the line's move from open to close predicts results about one-for-one, slope 0.85-1.14, Nov 5 check).
  If two are within 0.10 pts, the one with more units at the DK close wins.
- Also reported: units at the Open, units at the DK close, accuracy (RMSE vs results), by season.
- The winner goes PROVISIONAL only if, on the same seasons and grading, it clears the Model 1 pass rule (CLV >= break-even, CLV low
  end > 0, units at the Open > 0, DK-close ROI > -2%) **and** is positive at the Open in every season; then a Fable review.
  Caveat written now: these seasons were seen by Model 1 (thresholds were chosen on the first one), so a winner is still
  confirmed on 2026-27 TEST records before any upgrade beyond PROVISIONAL.
