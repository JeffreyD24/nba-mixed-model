# NFL mixed model: full handoff (as of 2026-10-31)

Everything from the "NFL Mixed Model" project, condensed. Repo: **github.com/JeffreyD24/nfl-mixed-model** (built Oct 30, 2026 as a replica of github.com/JeffreyD24/nba-mixed-model). One chat: "NFL mixed model replication" (Oct 30–31, 2026).

## Bottom line
- The NFL model has **not beaten the market** in any backtest. It's run as a **tracking test + research database, not a betting system**.
- Every upgrade tried (QB quality, EPA per play, blend, first-half, second-half) showed **no edge**.
- One slice is being forward-tested: **second-half totals at the opening line** (rule fixed, ~4 seasons to judge).
- Live in-game line recording started; **first real test Sunday 2026-11-01**.

## The model (`nfl_mixed_model.py`)
Same machinery as the NBA model: two rows per game (each team's points), Henderson's mixed model equations, REML variance components, team-season offense/defense random effects carried over from last season (`rho`), walk-forward using only games already played. Trains on 2021–2025.

NFL-specific fixed effects: home field, **short week** (single effect — the separate short-rest effects blew up on Thursday games since both teams are short, e.g. a −3 total for CAR@GB), coming off a bye, indoor (dome/closed roof), neutral site.

Injuries: each listed player counts `p_miss(status) × expected snap share`, split into `qb_missing`, `missing_offense`, `missing_opp_defense`. p_miss on the final report: Out 99.9%, Doubtful 99.5%, Questionable 34%. Source: NFL official final injury report via nflverse; ESPN injury list as fallback until nflverse posts it (Picks sheet notes which source).

### Two locked numbers per game (key design decision)
NFL openers go up ~a week ahead, before injury reports. The first NFL build graded final-report numbers vs openers, which produced a fake 54.4% (117-98) opening-spread result. Fix:
- **Early number** (`pred_margin`, `pred_total`): locked in the Tuesday morning run once the prior week is final, using **last week's** reports weighted by how often that status still misses the next game (Out 67%, Doubtful 44%, Questionable 22%). **Graded at the opening line. This is the scorecard.**
- **Final number** (`final_margin`, `final_total`): locked the evening before the game from the official final report. **Graded at the closing line.** Alerts use this, updated with ESPN injuries each check.

## Backtests (3+ pt edge, -110, break-even 52.4%)
| Line | Market | Seasons | Record | Win % | Units |
|---|---|---|---|---|---|
| Opening (early) | Spread | 2023-25 | 103-104 | 49.8% | -10.4 |
| Opening (early) | Total | 2023-25 | 128-129 | 49.8% | -12.6 |
| Closing (final) | Spread | 2018-25 | 357-339 | 51.3% | -14.5 |
| Closing (final) | Total | 2018-25 | 301-322 | 48.3% | -48.4 |

Model error is 0.1–0.5 pts/game worse than the line every season (NBA model is within ~0.15 of the opener). 4+ edge is no better: open spreads 54-58, open totals 82-78; close spreads 214-194, close totals 168-190. Opening lines only exist for 2023–25 (ESPN), so that test is small.

### Upgrades tested (Oct 30) — no improvement; live tracker keeps current model
Test seasons 2021–25, 3+ edge:
| Variant | Open spr | Open tot | Close spr | Close tot | Margin err vs opener |
|---|---|---|---|---|---|
| Current | 103-104 | 128-129 | 229-217 | 201-228 | +0.39 |
| QB quality (snap share × shrunk EPA/play gap over backup; replacement ≈ −0.11 vs starter +0.07) | 102-102 | 137-130 | 225-219 | 201-230 | +0.38 |
| EPA per play as response, mapped to points | 115-106 | 143-129 | 255-240 | 234-261 | +0.39 |
| Blend points + EPA | 92-108 | 113-116 | 204-208 | 178-214 | +0.40 |
Code: `blend.py`, `compare_models.py`, `compare_blend.py`; results `backtests/compare*.csv`.

### Half lines (`backtest_halves.py h1|h2`) — no edge
Action Network pregame half lines (2023 close only, 2024, 2025 wks 11–18, 2026 so far; 746 games vs close, ~475 vs open). 1.5+ edge, dedicated half model:
| Half | Line | Spreads | Game totals | Team totals | Err vs line |
|---|---|---|---|---|---|
| 1st | Open | 117-128 | 109-119 | 209-192 | +0.28 |
| 1st | Close | 185-212 | 179-178 | 274-264 | +0.27 |
| 2nd | Open | 153-142 | 113-116 | 110-102 | +0.27 |
| 2nd | Close | 216-222 | 184-198 | 225-218 | +0.30 |
- Full-game model scaled to 1H (×0.56 margin, ×0.50 total) also lost. 1H bets often priced worse than -110.
- By team: win-rate spread 12.7% vs 12.3% expected by chance → no team the model reads better (e.g. CHI 18-8, TB 13-6 are luck).
- 2H lines in this data are pregame, don't react to 1H score (NO led CAR 30-3 at half, line unchanged).

## Second-half totals watch (forward test, started 2026-10-30)
User wanted to keep watching the one good slice. **Fixed rule** (`half_watch.py`): 2H model's EARLY number for the 2H total (Q3+Q4+OT), locked with full-game early numbers, vs Action Network's OPENING 2H total; 3+ edge = bet at opening line.
- Backtest when set: 52-35 (2024 26-15, 2025 wks 11–18 16-13, 2026 wks 1–8 10-7). 80 of 88 were overs.
- Caveat: best of ~100 slices, and same market loses at 1–1.5 edges → a hypothesis.
- ~35–40 bets/season → ~4 seasons to 150 bets. **Don't bet it or change the rule before then.** CLV gives an earlier read (real edge → overs close higher than they open).
- Output: `state/h2_totals_watch.csv`, **2H Totals Watch** sheet, record on Notes sheet. No phone alerts.
- Action Network fills 2H open only around kickoff; DK/FanDuel 2H totals post days earlier, so the first DK/FD values seen are recorded too.

## Live (in-game) line recording (started 2026-10-30)
No free historical live-line source exists (ESPN keeps none), so live betting can't be backtested — only collected forward. `live.py` + `live_loop.sh` + `.github/workflows/live.yml`: runs every 30 min through game windows, polls every minute while a game is in progress, into `research/live/YYYY-MM-DD/`. Records score, quarter, clock, possession, down/distance, field position, ESPN win probability, ESPN odds feeds, Action Network full-game/1H/2H lines at 8 books with an `is_live` flag. Records only, no alerts.
- **To do Sunday 11/1 after the 1 PM games:** verify live lines actually appear (`is_live` True rows in books.csv, or a live ESPN provider). If not, find another source.
- Expectation: no edge likely (lines move every play, alerts lag 5 min, higher vig, books' live models know more).

## What runs, when (GitHub Actions)
| Workflow | Schedule | Job |
|---|---|---|
| Morning run (`morning.yml`) | 15:41 UTC = 11:41 AM EDT / **10:41 AM EST from Nov 1** | Results, grading, refit, walk-forward 2026, **locks early numbers** (Tuesday run), refreshes line-check model, rebuilds `NFL_Live_Tracker.xlsx` |
| Evening run (`evening.yml`) | 02:33 UTC = 10:33 PM EDT / **9:33 PM EST** | **Locks final numbers** for next day's games (Wed night → Thu, Sat night → Sun, Sun night → Mon) |
| Line check + alerts (`alerts.yml`) | every 5 min (`alert_loop.sh`, ~50 min/run) | Games in next 7 days: ESPN injuries + DraftKings lines, re-predict, ntfy push when model vs line ≥ 3 pts |
| Live recorder (`live.yml`) | game windows | see above |
| Log a bet | on issue | records bets |
GitHub often starts scheduled runs 10–30 min late. Times were reviewed and kept as-is (evening timing is the one that matters). Optional idea not done: extra Tuesday ~5 AM ET run.

## Alerts
- Content: model number, current DK line (and open), edge now, edge at open, line history, latest reporter injury news. Football-tagged.
- **CAUTION** alerts when: final injury report not out yet (due 4 PM ET two days before; day before for Thursday — so early-week alerts are always cautions), ESPN injury list unreadable, or line moved 3+ against the bet since open.
- "Market agrees" when line moves 3+ toward the model; line-jump alerts for 3+ moves within an hour (1.5+ logged).
- All logged to `state/alerts.csv` / Alerts sheet and graded (regular and caution separately). Settings at top of `alert.py`: `THRESHOLD`, `MAX_LINE_MOVE`, `JUMP_*`, `WINDOW`.

## Scorecard & bet logging
- Scorecard: every spread/total where the **opening line** differs from the locked **early** number by 3+ counts as a bet at the opening line (even if the line moved). Highlighted on Summary sheet. Pre-tracking games backfilled with no-lookahead walk-forward, marked "backfilled". ~100–200 bets/season → more than one season to judge; CLV shows sooner. **Don't change thresholds mid-season.**
- Log bets: "Log this bet" button on an alert, or Issues → New issue → Log a bet (teams as codes or names). Workflow writes `state/my_bets.csv`, confirms, closes the issue. Morning run grades at your line/odds/stake → **My Bets** sheet.

## Research database (`research/`)
Every 5-min check: full DK market with prices/moneylines, ESPN matchup predictor, bet/money splits and 9-book lines (Action Network), every injury note with first-seen time, model number whenever it changes. CLV on every graded pick, alert, bet. Columns in `research/DATA_DICTIONARY.md`.

## Files
`tracker.py` (morning/evening), `alert.py`, `espn.py`, `research.py`, `log_bet.py`, `nfl_mixed_model.py`, `build_injury_features.py`, `build_history.py` (data from nflverse/ESPN, incl. QB quality + team EPA), `backtest.py`, `backtest_halves.py`, `half_watch.py`, `blend.py`, `compare_models.py`, `compare_blend.py`, `live.py`, `build_tracker_workbook.py`. `data/` = training games 2013–2025, `p_miss.csv`, snap counts, player IDs. `state/` = picks_log, alerts, my_bets, line_history, model_YYYY-MM-DD.json, h2_totals_watch.

## Setup status
Done by user: `bet` issue label created (github.com/JeffreyD24/nfl-mixed-model/labels). Steps given: add repo secret `NTFY_TOPIC` (same as NBA repo for one channel, or new), then Actions → Line check and phone alerts → Run workflow → "Send a test notification" (sidebar collapsed on phone: tap "All workflows"). Workflows confirmed enabled. GitHub pauses scheduled workflows after 60 days of inactivity → **re-enable in September** after the offseason.

## Lessons
- EPA per play has almost no home-field effect; any EPA→points map needs a home term (an earlier version without it falsely showed 146-122 on opening totals).
- Fitting a blend weight on one validation season is unstable; use several prior seasons of out-of-sample predictions.
- Action Network's NFL scoreboard ignores the date; query by season + week.
- Why NBA did better: softer NBA openers (gain ~0.3 pts accuracy by close vs ~0.1 NFL), NBA model about as accurate as the opener, 82 vs 17 games/team, NBA injury reports often precede the opener.

## Ideas not started
- Market-informed priors: start each season from preseason win totals/power ratings instead of last season's effects.
- After a few weeks of live data: study live/halftime line reactions (do halftime 2H lines overreact to the 1H score?).
