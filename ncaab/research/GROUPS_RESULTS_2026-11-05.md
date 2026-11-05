# NCAAM team groups: results (Nov 5, 2026)

Pre-registration `ncaab/research/GROUPS_PREREG_2026-11-05.md` (12 cells + a no-hindsight addendum, both pushed before results).
Data: 75,900 games 2007-08..2025-26 with a closing line: SportsbookReview archive 2007-21 (newly downloaded: `data/external/sbr_ncaab`,
cleaned by `ncaab/clean_sbr.py`), Action Network consensus 2021-23, DraftKings 2023-26; groups from ESPN scoreboards for every date
(`ncaab/espn_meta.py`: pre-game AP rank, conference, neutral site). Outputs `ncaab/research/groups_output.txt`, `groups_momentum_output.txt`.

## Does the closing line misjudge kinds of teams? Almost never.
| Cell (vs the close) | 2007-18 | 2018-26 holdout | Decision |
|---|---|---|---|
| Ranked vs unranked | 50.9% | 49.2% | not qualified |
| Ranked favored by 10+ | 51.8% | 49.6% | not qualified |
| Power-conference vs non-power | 52.7% (z +3.8) | 50.5% | FAIL (faded) |
| Powerhouse programs | 53.2% (z +4.0) | 50.8% | FAIL (faded) |
| Elite-coach teams | 53.7% (z +4.2) | 53.4% | passed on paper, **rejected: hindsight** |
| Both ranked, home team | 51.7% | 52.0% | not qualified |
| Six totals cells (power, ranked, powerhouse, coach, low-major, conference) | 49.0-50.0% | 48.7-50.4% | none qualified |
**Elite coaches:** the list was written in 2026. Coaches already elite by 2018 covered only **51.2% on 2018-26 (1,559 bets, -35.5u)**;
the ones added with hindsight (Hurley, Sampson, Drew, Pearl, Barnes, Pitino) carried it (55.5%). The big-name edge was real through
2019 (61% that season) and has been gone since 2020.
**No-hindsight version** (teams that covered most / least over the previous two seasons): back the top 25 -> 50.0% in the holdout;
fade the bottom 25 -> 49.2%. Past ATS form does not carry over; the close adjusts fully.

## What it means
1. The 2008-2018 closing line underrated power-conference, powerhouse and big-name-coach teams (52.7-53.7%). The market has fixed it:
   none of it survives after 2018. Same story as conference totals: old college edges are gone.
2. Groups do not beat the close. Where groups may still help is inside our own model (descriptive: Model 1 totals did better in
   conference games and both-power-conference games, worse in Nov-Dec non-conference games) -> candidate features for a Model 2,
   to be tested the usual way.
3. Data: the SBR archive adds 55,354 games (2007-21) with scores and open/close lines; usable for any future college test at the close.
