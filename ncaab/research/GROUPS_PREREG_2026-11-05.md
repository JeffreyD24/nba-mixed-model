# NCAAM team groups: does the closing line misjudge some kinds of teams? Pre-registration (Nov 5, 2026)

Pushed before any group result was computed. Jeffrey's idea: analyze the ~360 teams in groups (powerhouse programs, good coaches, power
conferences, ranked teams). With many groups some will look good by luck, so: groups and cells fixed here, a strict bar on old seasons,
then confirmation on held-out seasons.

## Data
- Lines: SportsbookReview archive 2007-08..2020-21 (`ncaab/clean_sbr.py`, close = SBR's closing number); Action Network consensus close
  2021-22..2022-23; DraftKings close 2023-24..2025-26 (`ncaab/data/games.csv`).
- Groups from ESPN's scoreboard for every date (`ncaab/espn_meta.py`): pre-game AP rank, conference, neutral site; matched to the line
  files by date and final score (games matching more than one game that day are dropped).
- Group definitions (fixed in advance, by season, end-year labels):
  - **Ranked** = AP top 25 going into the game.
  - **Power conference** = ESPN conference ids ACC 2, Big East 4, Big Ten 7, Big 12 8, Pac-12 21, SEC 23 (membership as ESPN lists it that season).
  - **Powerhouse program**: Kentucky, Kansas, Duke, North Carolina, UCLA, Indiana (blue bloods) + Michigan State, Villanova, Gonzaga,
    UConn, Louisville, Arizona, Syracuse, Florida.
  - **Elite coach** (proxy list, seasons coached there): Izzo (Michigan State), Self (Kansas), Few (Gonzaga), Drew (Baylor), all seasons;
    Krzyzewski (Duke) to 2022; Calipari (Kentucky) 2010-2024, (Arkansas) 2025-; Roy Williams (North Carolina) to 2021; Jay Wright
    (Villanova) to 2022; Boeheim (Syracuse) to 2023; Pitino (Louisville) to 2017, (St. John's) 2024-; Tony Bennett (Virginia) 2010-2024;
    Dan Hurley (UConn) 2019-; Kelvin Sampson (Houston) 2015-; Rick Barnes (Texas) to 2015, (Tennessee) 2016-; Bruce Pearl (Auburn) 2015-2025.

## The 12 cells (all graded against the CLOSING line; -110)
Spreads, betting ON the group team when exactly one team is in the group (either direction counts: a group the close overrates is a fade):
S1 ranked vs unranked · S2 ranked favored by 10+ vs unranked · S3 power-conference team vs non-power team · S4 powerhouse vs non-powerhouse ·
S5 elite-coach team vs others · S6 both ranked: home team.
Totals, over rate vs the close: T1 both power conference · T2 any ranked team · T3 any powerhouse · T4 any elite-coach team ·
T5 neither team power conference · T6 conference game.

## Rule
- **Discovery: 2007-08..2017-18.** A cell qualifies if its cover (or over) rate differs from 50% with |z| >= 2.64 (0.05 split across
  12 cells), pushes excluded. The direction found (back or fade the group; over or under) is then fixed.
- **Holdout: 2018-19..2025-26.** PASS = same direction, cover rate betting that direction >= 52.4% (pays -110), one-sided z >= 1.65,
  and the 2023-26 DraftKings seasons not below 50%. PASS -> a PROVISIONAL candidate (Fable review first); FAIL -> recorded, dropped.
- Descriptive only (decides nothing): Model 1's error vs the close by group (2022-26), and Model 1 bets at DraftKings' own opener by group.

## Addendum (Nov 5, written after the 12 cells, before this test): an honest, no-hindsight version of "teams the market underrates"
The elite-coach cell passed, but its coach list was written in 2026 (hindsight). Fair version, defined only from information before each season:
- For season s, rank teams (ESPN location name) by their cover rate vs the close over seasons s-2 and s-1 (min 40 decided games).
  **U25** = top 25 (market underrated them lately), **O25** = bottom 25 (overrated). Cells: back U25 vs a non-U25 opponent; fade O25 vs a non-O25 opponent.
- Discovery 2009-10..2017-18; holdout 2018-19..2025-26. Two cells: qualify at |z| >= 2.24 (0.05 split across 2); holdout rule as above.
