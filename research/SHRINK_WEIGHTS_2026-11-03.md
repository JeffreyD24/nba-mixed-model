# Shrink weights and thresholds, all three sports (Nov 3, 2026)

Job 3 of research/HANDOFF_TO_OPUS.md. Same file in all three repos. Question: how much of the model's disagreement with the
opening line is real? Weight w in `shrunk = line + w x (model - line)`: 0 = the opener already knows it, 1 = trust the model fully.
Every weight is fit with the leaks from research/LEAKAGE_AUDIT_2026-11-03.md removed where possible, and every bet rule here is
**not tuned**: bet when the shrunk number beats the price (-110 break-even for points, EV > 0 for prices). Each test season uses a
weight fit on the other seasons.

## Results
| Sport, market | Weight vs opener | vs close | Untuned shrunk rule, out of season | Current rule, same games |
|---|---|---|---|---|
| NBA spreads, Model 1 | **0.15** (+/-0.07) | -0.05 | 346 bets 46.8% -36.7u | edge 3+: 1,226 bets 50.8% -36.6u |
| NBA totals, Model 1 | **0.32** (+/-0.07) | -0.08 | 1,334 bets 53.1% **+19.5u** | edge 3+: 1,552 bets 52.6% +7.7u |
| NHL moneyline (team-only model, SBR 2015-22) | **0.29** (+/-0.09) | | 2,821 bets +2.5% | 55/45 blend EV 4%+: 2,430 bets +2.5% |
| NHL overs (same) | **0.40** (+/-0.09) | | 473 bets +12.4% | EV 6%+: 532 bets +11.5% |
| NFL totals v2, no weather | **0.55** (+/-0.20) | | 431 bets 57.5% **+42.5u** | edge 2+: 288 bets 56.2% +21.3u |
| NFL totals v2, game-time weather (leaks) | 0.59 (+/-0.16) | | 537 bets 57.2% +49.1u | edge 2+: 375 bets 58.4% +43.1u |
| NFL spreads, team model | **0.06** (+/-0.11) | | 25 bets -7.8u | edge 3+: 453 bets 50.8% -13.9u |
NBA: DraftKings openers 2023-26 with the one-day lag. NFL: DraftKings openers 2020-25, totals weeks 5-14. NHL: SBR openers, eight
seasons the model never saw, without goalies (the live model has them, so its weight is probably higher; the live 55/45 blend
was fit at 0.51-0.61 on 2021-26 with goalies). This season's live NHL picks: 0.30 (+/-0.60, 235 games): too few to say.

Weights against the CLOSE are about zero everywhere they could be measured: nothing is left once the market finishes moving.

## What was added
- **NBA "Model 1 shrunk" side-by-side record** (`shrunk_record.py`, `state/picks_log_shrunk.csv`, morning run). Model 1 is unchanged.
  w = 0.147 spreads / 0.318 totals (`data/shrink_weights.json`); bet when the shrunk edge beats -110: 0.83 pts spreads (raw 5.6+),
  1.09 pts totals (raw 3.4+). Each row also carries the shrunk win chance. So far this season (mostly backfilled): spreads 12-6,
  totals 14-16. Note: shrinking keeps the order of bets, so this equals Model 1 with a different cutoff; the value is that the
  cutoff comes from the data, not a choice, and each bet gets an honest win chance.
- **Threshold register** `config/thresholds.csv` in each repo: every number that decides a bet, its date, the data it was chosen on,
  how (in-sample, out of season, untuned, user rule) and the evidence. `tools/check_thresholds.py` runs each morning and prints a
  MISMATCH line if alert.py drifts from the register. See config/README.md.
- Weights: nba-mixed-model `data/shrink_weights.json`, `analysis/shrink_weights.py`; nhl-mixed-model `data/shrink_weights.json`,
  `dev/shrink_weights.py`; nfl-mixed-model `data/shrink_weights.json` (fit by nba-mixed-model `analysis/nfl_shrink_weights.py`).
- Nothing in any live alert rule changed.

## Personal note and takeaways
- **The model is worth 15-55% of its own opinion, depending on the market.** A "3-point edge" on NBA spreads is really about half a
  point; on NBA totals about 1 point; on NFL totals (week-early openers) about 1.6 points. That is the cleanest single explanation
  for why spreads lose and totals win in both sports.
- **NFL totals are the most interesting result.** With no weather at all, the untuned rule (bet at about 1.1 raw points of edge)
  made +42.5u out of season, double the live 2-point rule. The weight is noisy (0.09 to 1.45 by season), so I would not change the
  live rule now; I'd track it side by side for a season the way NBA Model 1 shrunk is now tracked. Your call.
- **NHL: the live rules hold up.** The untuned rule earns the same as the hand-picked ones on unseen seasons, which is a good sign
  they weren't over-fit.
- **Spreads in both NBA and NFL carry almost no information against the opener** (0.15 and 0.06). That fits every spread test so far.
- The edge-statistics work (edge_stats.py, Nov 3) already gives bootstrap ranges and Pinnacle CLV per rule; the shrunk record feeds
  through the same picks files, so it can be added there once it has a few hundred bets.
