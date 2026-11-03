# External data library (index)

Everything we pulled from outside, in one place. Rule: **every folder has a README with source, license, quality problems and takeaways;
MANIFEST.csv lists every file with size and checksum.** Re-run `python3 -I make_manifest.py` after adding anything.

| Folder | What | Sports | Years | License | Status |
|---|---|---|---|---|---|
| `sbr/` | opening + closing lines, scores (cleaned + raw) | NBA NFL NHL MLB | 2011-2021 | scraper MIT; odds belong to SBR (private research) | in repo |
| `hockeyr/` | xG code, fitted xG objects, team-game xG table; script to re-fetch raw pbp | NHL | 2010-11 to 2022-23 | code MIT; raw pbp unlicensed (not stored) | in repo |
| `beatthebookie/` | strategy code; links to the odds data | soccer | 2005-2015 | code GPL-3.0; data unstated | code in repo, **data needs your browser** |

## Ground rules for adding more
1. Check the license first. No license = reference/link only, derived aggregates at most; never commit the raw files.
2. Raw files stay untouched; cleaned versions sit beside them with a flags column and a cleaning report.
3. Big files (over ~50 MB) go behind a fetch script and .gitignore, with the checksum recorded here.
4. Write the "personal note and takeaways" section in the README at the time you add it, while you remember why.

## Wish list (not yet obtained)
- BeatTheBookie odds zips (see `beatthebookie/DOWNLOAD_LINKS.md`)
- Reddit / X / 4chan sweep via the desktop-app browser (see research/community_notes/)
