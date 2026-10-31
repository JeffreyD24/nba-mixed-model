# Who covers each NBA team (`nba_media_list.csv`)

Built Oct 31, 2026 from public sources. One row per person (or station):
`category` (National insider / news account, Beat writer / team reporter, Team broadcaster, Local sports radio station),
`team`, `name`, `role`, `outlet`, `x_handle`, `status` (how current: confirmed, listed for 2026-27, older list only, or not re-checked),
`source`, `source_url`, `notes`, `last_checked`.

- Beat writers: the Oct 26, 2026 "NBA Beat Writers for Every Team" list (Fiddle's Picks), plus its 2025 and 2024 versions (marked
  "Older list only: may have moved") and news reports on moves (Dan Woike, James Edwards III, Anthony Slater, Jovan Buha).
- National insiders: outlets confirmed from 2025-26 reports where linked; others from Claude's knowledge to mid-2026 (not re-checked).
- Broadcasters: Wikipedia's "List of current NBA broadcasters" for 2026-27 (TV, radio, Spanish, French).
- Sports radio stations: Claude's knowledge to mid-2026 (not re-checked). Hosts not listed yet.

Not a credential list: teams and the league don't publish who holds credentials.
Planned use: watch the beat writers' and insiders' public accounts for injury news, and compare when they post against when the
line moves (`research/injury_decisions.csv`, `research/timeline/`).
