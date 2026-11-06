"""Keep a copy in git of every Kaggle table the NBA models use (added Nov 5, 2026, data-source audit).

Why: tracker.py downloads the eoinamoore box-score dataset every day and deletes it after use, and several
backtests read Kaggle files that only ever lived on a scratch disk. If a dataset changes or disappears, the
inputs behind the models could not be rebuilt. This script saves the tables we use into data/external/kaggle/.

Sources (all public Kaggle datasets, no key needed):
  eoinamoore/historical-nba-data-and-player-box-scores   (updated daily; used by tracker.py, models_live.py, backtest_v2)
  cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024 (spreads/totals 2007-2026; used by analysis/old_seasons.py)
  deocheng/nba-data-1946-2026                             (player EPM; used by analysis/roster_strength.py, backtest_v2)

Files are written as gzip with a fixed timestamp, so a re-run that finds no new data changes nothing in git.

Usage:  python tools/archive_kaggle.py <repo_root> [--only eoin] [--zip-dir DIR]
"""
import argparse, datetime as dt, gzip, hashlib, io, os, subprocess, sys, zipfile
import pandas as pd

DATASETS = {
    "eoin": "eoinamoore/historical-nba-data-and-player-box-scores",
    "betting": "cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024",
    "epm": "deocheng/nba-data-1946-2026",
}
SLICE_FROM = "2011-08-01"   # PlayerStatistics is ~390 MB for all history; we keep 2011-12 on (~1 MB a season gzipped).
                            # Nov 6, 2026: was 2021-10-01; extended because ESPN box scores for Chicago and New Orleans 2012-13..2017-18
                            # are blank (data/external/nba_box/checks.txt), which the older-season spread tests (recent-arrival trap) need.


def download(key, zdir):
    z = os.path.join(zdir, f"{key}.zip")
    if os.path.exists(z): return z
    url = f"https://www.kaggle.com/api/v1/datasets/download/{DATASETS[key]}"
    r = subprocess.run(["curl", "-sL", "-m", "1500", "-o", z, "-w", "%{http_code}", url], capture_output=True, text=True)
    if r.stdout != "200": sys.exit(f"{key}: download failed (HTTP {r.stdout})")
    return z


def write_gz(df, path):
    buf = io.StringIO(); df.to_csv(buf, index=False)
    raw = buf.getvalue().encode()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0, compresslevel=9) as g: g.write(raw)
    return len(df), hashlib.sha256(raw).hexdigest()[:16]


def member_date(zf, name):
    d = zf.getinfo(name).date_time
    return dt.datetime(*d).strftime("%Y-%m-%d")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("--only"); ap.add_argument("--zip-dir")
    a = ap.parse_args()
    out = os.path.join(a.root, "data", "external", "kaggle")
    zdir = a.zip_dir or os.path.join(a.root, "_tmp"); os.makedirs(zdir, exist_ok=True)
    keys = [a.only] if a.only else list(DATASETS)
    rows = []

    for key in keys:
        zf = zipfile.ZipFile(download(key, zdir))
        if key == "eoin":
            d = os.path.join(out, "eoinamoore")
            for name in ["Games.csv", "TeamStatistics.csv", "Players.csv", "TeamHistories.csv"] + \
                        sorted(n for n in zf.namelist() if n.startswith("LeagueSchedule")):
                df = pd.read_csv(zf.open(name), low_memory=False)
                n, h = write_gz(df, os.path.join(d, name + ".gz"))
                rows.append((key, name, "all rows", member_date(zf, name), n, h))
            p = pd.read_csv(zf.open("PlayerStatistics.csv"), low_memory=False)
            t = pd.to_datetime(p.gameDateTimeEst.astype(str).str[:19], errors="coerce")
            keep = t >= SLICE_FROM
            p, t = p[keep], t[keep]
            for season_start in sorted(set(t.apply(lambda x: x.year if x.month >= 8 else x.year - 1))):
                part = p[(t >= f"{season_start}-08-01") & (t < f"{season_start + 1}-08-01")]
                tag = f"{season_start}_{str(season_start + 1)[2:]}"
                n, h = write_gz(part, os.path.join(d, f"PlayerStatistics_{tag}.csv.gz"))
                rows.append((key, f"PlayerStatistics.csv ({tag})", f"games {season_start}-08-01 to {season_start + 1}-07-31",
                             member_date(zf, "PlayerStatistics.csv"), n, h))
        elif key == "betting":
            df = pd.read_csv(zf.open("nba_2008-2026.csv"))
            n, h = write_gz(df, os.path.join(out, "nba_betting_2008_2026", "nba_2008-2026.csv.gz"))
            rows.append((key, "nba_2008-2026.csv", "all rows", member_date(zf, "nba_2008-2026.csv"), n, h))
        elif key == "epm":
            for name in ("csv/public.player_epm.csv", "csv/public.player_epm_actual.csv"):
                df = pd.read_csv(zf.open(name), low_memory=False)
                n, h = write_gz(df, os.path.join(out, "deocheng_epm", os.path.basename(name) + ".gz"))
                rows.append((key, name, "all rows", member_date(zf, name), n, h))
        zf.close()

    # manifest: one line per saved table; keep lines for datasets not refreshed this run
    mpath = os.path.join(out, "MANIFEST.csv")
    new = pd.DataFrame(rows, columns=["dataset", "file", "kept", "kaggle_file_date", "rows", "sha256_16"])
    new.insert(1, "kaggle_slug", new.dataset.map(DATASETS))
    if os.path.exists(mpath):
        old = pd.read_csv(mpath); new = pd.concat([old[~old.dataset.isin(keys)], new])
    new.sort_values(["dataset", "file"]).to_csv(mpath, index=False)
    print(new.to_string(index=False))
    print("done")


if __name__ == "__main__":
    main()
