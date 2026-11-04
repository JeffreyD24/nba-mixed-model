# Altitude tripwire for NBA totals v5 (set Nov 4, 2026, before any 2026-27 decision data)

**What it guards:** `alert.py` adds `ALT_W = +3.8` points to the model total for games at Denver and Utah.

**Why a tripwire:** the statistics catalog (A03) found the altitude over is real in the current era but not before it.
- 2023-26, vs the DraftKings opener: +4.3 pts (v4 adds +3.8, leaving -0.4).
- 2021-26, vs the close: +2.8 pts overall (p = 0.002), positive in 4 of 5 seasons.
- 2011-19, vs SBR openers: -0.5 pts (p = 0.52). No effect at all.

A pattern that appeared recently can disappear just as fast, and +3.8 is a big adjustment. This rule decides in advance when to cut it.

**Measure:** diff = mean(final total - DK opening total) at Denver/Utah home games, minus the same mean for all other games, this season.
Subtracting the league-wide number removes season-wide scoring drift. The tracker computes it every morning (`tracker.py altitude_watch`)
and writes it to `state/altitude_watch.json`; the daily health check watches that file.

**Rule:**
- **All-Star break:** drop the +3.8 to 0 only if diff < -2.0 (a clear reversal). Otherwise no change: ~45 games is too few to justify a
  smaller cut (standard error ~3 pts).
- **Season end:** diff >= +2.0, keep +3.8. Between 0 and +2.0, halve to +1.9. Below 0, drop to 0.
- Any change starts a new NBA totals version record, gets checked by Fable before it goes live, and gets reported to you.

**What to expect:** if the true effect is still ~+4, the season-end rule keeps the +3.8 about 80% of the time (~80 games, SE ~2.2). If the effect
is gone (true 0), it halves or drops the adjustment about 80% of the time.
