# NBA spreads: bet at the opener or wait for the 8 PM injury report? (Nov 4, 2026)

Script: `analysis/spread_opener_timing.py` (same data and live spread number as `analysis/rule_audit_spreads.py`:
DraftKings 2023-24..2025-26, live rules, morning-lock lag 1, units at -110). Opener edge uses each team's previous-game report.

| Opener edge | Bet at the opener | Wait: ~9 PM line + 8 PM report, still 3+, not moved against |
|---|---|---|
| 3-4 | 162 bets 46.3% -18.8u | 72 bets 50.0% -3.3u |
| 4-5 | 103 bets 54.4% +3.9u | 53 bets 52.8% +0.5u |
| 5+ | 152 bets 61.8% +27.5u (+3.9, +12.0, +11.5 by season) | 92 bets 64.1% +20.6u |

- Opener bets the 8 PM report later drops below 3 / flips: 3-4 edge 33.3% -19.6u; 5+ edge 9 bets +4.4u.
- Policy "5+ at the opener, everything else waits": 307 bets 59.0% +38.5u vs waiting for everything 247 bets 59.1% +31.7u.
  By season: 2024 +3.9u vs +3.1u, 2025 +19.1u vs +16.3u, 2026 +15.5u vs +12.4u.
- Live from Nov 4, 2026 as NBA spreads v3.2 (`SPREAD_OPENER_EDGE = 5.0` in alert.py). The usual spread rules (Oct-Jan only, both teams
  10+ games, no home underdogs, Feb-Apr traps, Pinnacle rule, PASS on 0.5+ against) still apply. DON'T BET if the report later drops
  the edge under 3 or flips it before the bet is logged.
