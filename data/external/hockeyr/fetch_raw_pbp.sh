#!/usr/bin/env bash
# Re-download hockeyR-data play-by-play (about 2 GB, NO license stated by the author) into ./raw_pbp (git-ignored). Do not commit it.
# Usage: bash fetch_raw_pbp.sh [season_start_year ...]   e.g. 2015 2016   (default: all)
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p raw_pbp
# Pinned (Nov 5, 2026 data-source audit) to the upstream commit our derived tables were built from; UPSTREAM_PIN.csv lists
# each file's git blob hash so a re-download can be checked byte-for-byte (git hash-object <file>).
PIN=333b1ee2d30c35652ae08fddc3502f14d1068ec0
git clone --filter=blob:none --sparse https://github.com/danmorse314/hockeyR-data raw_pbp/_repo
cd raw_pbp/_repo; git sparse-checkout set data; git checkout -q "$PIN"
echo "Files are in raw_pbp/_repo/data (use the *_lite.csv.gz files; read with encoding latin-1)."
echo "Then rebuild the derived table: python3 -I ../../build_hockeyr_team_game.py raw_pbp/_repo/data team_game_xg_2010_2023.csv.gz"
