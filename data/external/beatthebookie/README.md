# BeatTheBookie (Kaunitz, Zhong, Kreiner: "Beating the bookies with their own numbers")

Paper: arXiv 1710.02824. Code: github.com/Lisandro79/BeatTheBookie (**GPL-3.0**, kept here with its license, unmodified in `src/` and `sql/`). Retrieved Nov 3, 2026.

## What is NOT here, and why
The odds data (about 479,000 football/soccer games from 32 bookmakers, plus odds time series and ~1.8 GB of SQL dumps) is not in the GitHub repo.
The authors host it on Dropbox and Google Drive, which this assistant's workspace cannot reach. The data's license is not stated.
Soccer only, so it does not feed our NBA/NFL/NHL models directly; it is kept for the consensus-price method (see research/IDEAS_AND_CHECKLIST.md, section D).

## How to get it (you, in your own browser; takes a few minutes)
Links are in `DOWNLOAD_LINKS.md`. Save the files into `raw/` (git-ignored; do not commit the 1.8 GB SQL dumps).
Start with `closing_odds.zip`; the SQL dumps are optional. Then run `python3 -I ../make_manifest.py` from `data/external` to record sizes and checksums.

## Personal note and takeaways
- The strategy: average the bookmakers' odds as the "true" probability and bet any price that beats it by a margin. It made about 9.9% over five months of real bets, then bookmakers limited the accounts.
- For us the useful part is the method, not the soccer data: the same test can be run on our multi-book NBA/NHL/NFL snapshots (`research/books`, `data/odds_history`).
