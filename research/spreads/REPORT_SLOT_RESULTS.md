# Every game-day injury report vs the DraftKings spread — results (Nov 4, 2026)

Pre-registration: `REPORT_SLOT_PREREG.md` (commit 19a0106; script 3e23b1a; both pushed before the data finished and before any result).
Output: `analysis/report_slot_test_output.txt`; events: `analysis/report_slot_events.csv.gz`. Exploratory: `analysis/report_slot_speed_explore_output.txt`.
Data: `research/injury_history/` (new): every official report 2021-22..2025-26, 15,286 report files, ~2.3 million player rows.

## Verdict: PARTIAL. The news is real, but DraftKings prices most of it within ~25 minutes of the report.

4,253 report events (a team's injury value changed 0.5+ pts), ~850 per season; player-name match 98.8%. Report times are printed in the
PDF: the hourly files of 2021-25 are stamped :30 (the "5 PM" file = 5:30 PM); 2025-26 has reports every 15 min.

| Window (news of 1+ pt) | Line move per point of news | Share of the whole move |
|---|---|---|
| open -> report time | +0.15 | 33% |
| **report -> first line after (~26 min)** | **+0.25** | **55%** |
| ~26 min -> close | +0.05 | 12% |

Daytime reports are the clearest: for reports between noon and 6 PM, only 16-23% of the move is in the line before the report, 64-71% lands
in the next ~26 minutes, and 7-20% is left. Morning reports (before noon, n 163) leave 34% for later. Evening reports are half-priced before
they post (reporters and earlier reports beat them).

Pre-registered bets (first line at least 15 min after the report, which in the hourly history is ~26 min): test 2023-26, 20 bets, CLV +0.23,
-3.7u. CLV is positive (2 of 3 seasons) but small, so **PARTIAL**. Note: the pre-registered break-even estimate came out at +4.49 pts, which is
not credible (CLV in this window is tiny for most games, so the fit is flat); using the step-1 break-even of +0.77 gives the same verdict.

## Exploratory (after results): the prize for speed
Betting the news side at the last DK line *before* the report time (needs a reaction of minutes; an upper bound, since the history's "before"
line can be up to an hour old):

| News size | Before the report | ~26 min after |
|---|---|---|
| 1+ pt (1,818 bets) | CLV +0.58, -35.4u (-1.9%) | CLV +0.10, -87.9u (-4.8%) |
| 1.5+ pts (1,090) | CLV +0.86, +2.1u (+0.2%) | CLV +0.19, -41.0u |
| 2+ pts (688) | CLV +1.00, +12.4u (+1.8%) | CLV +0.21, -18.2u |
| 2+ pts, daytime reports only (382) | **CLV +1.17, +27.0u (+7.1%)** | |

## Personal note and takeaways
- **This is the "needs speed" answer from the handoff.** Most of the move happens in the first half hour after a report posts. Being 26 minutes
  late turns a CLV of about +1 into +0.2. Being first is the whole edge.
- **Where to aim:** big news (2+ pts) on daytime reports (noon-6 PM). Those reports post on a fixed clock (:30, now every 15 min), so a watcher
  can be waiting for them. Evening reports and small news aren't worth chasing.
- **Even instant reaction is only a modest edge** (+7% on 382 bets over five seasons, about 75 a season, and that's an upper bound). Worth
  testing live, not worth betting yet.
- **Proposed next (needs approval):** a 1-minute report watcher that grabs each report the moment it posts, rates the changes, and records
  the DK line at that minute, +5, +15 and +30 min, logged as a TEST bucket (no phone pushes). That measures what we could really get. It
  also feeds Part A of the news-model handoff with hundreds of events by December.
- New data asset: every official game-day report since 2021-22, parsed; useful for any future injury work (totals need offense/defense
  ratings, which we only have for 2025-26).
- Carry-over to other markets: scheduled releases get priced in minutes; an edge from public news is a speed edge, and it decays fast.
