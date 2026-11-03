# Hand-off for Opus (written Nov 3, 2026, end of the web-sweep session)

## Goal
Make the NBA / NHL / NFL mixed models (repos JeffreyD24/nba-mixed-model, nhl-mixed-model, nfl-mixed-model, all public, branch main) make money consistently. The user bets in Connecticut (DraftKings, FanDuel, Fanatics), so account limits cap profit. Judge everything by closing line value (CLV) and intervals, not win/loss. Be honest with the user; they want the truth over hype.

## Rules from the user
- Do not change Model 1. A new version gets its own record.
- Everything collected must be legal and organized (see data/external/INDEX.md). No raw files with unclear licenses in the repos.
- Commit messages must end with the Co-Authored-By and Claude-Session lines the harness gives. Repos get automated pushes too: `git pull --rebase origin main` before pushing.

## What was done this session (all pushed)
1. Web sweep (GitHub, Substack, papers, X, four r/algobetting threads pasted by the user). Verdict: no verified winning public record anywhere; pick sellers are affiliate marketing; honest posters report ~3% ROI; settled lines are very hard to beat; limits are the real ceiling. Notes: `research/community_notes/`, summary and checklist: `research/IDEAS_AND_CHECKLIST.md` (same file in all 3 repos).
2. Free data in `data/external/` (NBA repo has all; NHL has sbr+hockeyr; NFL has sbr): `sbr/` = SportsbookReview 2011-2021 openers + closers for NBA/NFL/NHL/MLB, cleaned with flags (read its README first: swapped spread/total columns repaired, use `spread_trusted` / `total_trusted`, season label = START year while our NBA files use END year, team names are nicknames); `hockeyr/` = MIT xG code + fitted objects + a derived team-game xG table 2010-11 to 2022-23 (hockeyR xG runs ~4% under actual goals; 2023-24 file lacks xG; raw 2 GB play-by-play stays out of git, fetch script provided); `beatthebookie/` = GPL-3.0 soccer code only (data is on Dropbox/Google Drive, not downloaded; links in DOWNLOAD_LINKS.md). `MANIFEST.csv` has checksums (`python3 -I make_manifest.py` rebuilds).
3. NBA market-shrink test (`analysis/market_shrink_test.py`, `analysis/FINDINGS.md`): vs OPENING lines the model deserves ~0.25 weight on its disagreement for spreads and ~0.39 for totals; vs CLOSING lines about 0.

## Open jobs for Opus (do these; they need judgment)
1. **NHL out-of-sample test (best next step).** Join `data/external/hockeyr/team_game_xg_2010_2023.csv.gz` with SBR NHL opening/closing moneylines and totals (2011-2021). Build the NHL model from xG only on early seasons, freeze rules, test on later seasons. Needs team-name mapping (SBR nicknames to NHL codes) and game matching by date + teams. Report CLV and ROI with bootstrap intervals; compare all rows vs trusted rows. Check that hockeyR xG and our own NHL xG agree in 2021-23 before mixing them.
2. **Independent leakage audit** of all three models: injury-report timing vs when openers were seen, any feature from after bet time, closing lines in training, thresholds tuned on the test season.
3. **Shrink weights and thresholds for NHL and NFL** (and a "Model 1 shrunk" side-by-side record for NBA: line + w x (model - line), w = 0.25 spreads / 0.39 totals), chosen without overfitting, plus one config file recording each threshold with date and data used.
4. **NBA old-seasons rerun using SBR openers** (`old_seasons.py` grades closes only). Needs NBA nickname-to-code mapping and the season-label conversion.
5. **How the three models combine** (redesign question), including the idea of a stack that takes model number AND market number as inputs, fit on earlier seasons and scored on a later one.
6. Consensus-price test (best price vs de-vigged consensus at the opener): needs a few months of multi-book snapshots; limits will cap it.

## Smaller jobs (Sonnet is fine)
Bootstrap intervals on ROI and CLV for every logged rule; calibration table (predicted vs realized by bucket); CLV in price terms vs Pinnacle's de-vigged close; log which book each bet is placed at and limit cuts; MLB file stored for later.

## Tool and access notes
- Reddit is blocked for every tool (browser pane, fetch); the user pastes threads. X works through the user's Chrome via the Claude extension (signed in, read-only); searches mostly return sellers, so target specific handles. Shell network is limited to package registries and GitHub; clone repos via GitHub. Check that Claude in Chrome is connected before relying on it.
- BeatTheBookie data needs the user's own download (soccer only; low value for these sports).
- The user is on Sonnet now and plans to switch to Opus for the jobs above.
