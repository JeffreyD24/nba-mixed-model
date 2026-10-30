"""
Parse official NBA injury report PDFs into one row per (snapshot, game, team, player, status).

Uses pdftotext -layout. Game date / time / matchup / team are only printed on the first row of
each block, so they are carried forward. Multi-line reasons are ignored (status is what matters).
"""
import os, re, sys, subprocess
from concurrent.futures import ProcessPoolExecutor
import pandas as pd

TEAMS = ["Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", "Chicago Bulls", "Cleveland Cavaliers",
         "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
         "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat", "Milwaukee Bucks", "Minnesota Timberwolves",
         "New Orleans Pelicans", "New York Knicks", "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
         "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz", "Washington Wizards"]
TEAM_RE = re.compile("(" + "|".join(re.escape(t) for t in TEAMS + ["Los Angeles Clippers"]) + ")")
DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
TIME_RE = re.compile(r"\b(\d{1,2}:\d{2}) ?\(ET\)")
MATCH_RE = re.compile(r"\b([A-Z]{2,3})@([A-Z]{2,3})\b")
PLAYER_RE = re.compile(r"([A-Z][A-Za-z\.\'\-]+(?: [A-Za-z\.\'\-]+)*, [A-Z][A-Za-z\.\'\- ]*?)\s{2,}(Out|Questionable|Doubtful|Probable|Available)\b")
HEAD_RE = re.compile(r"Injury Report: (\d{2}/\d{2}/\d{2}) (\d{2}:\d{2}) ?(AM|PM)")


def parse(path):
    txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
    snap = os.path.basename(path)[:-4]                      # e.g. 2025-11-08_05PM
    asof = None
    m = HEAD_RE.search(txt)
    if m: asof = pd.to_datetime(f"{m.group(1)} {m.group(2)} {m.group(3)}", format="%m/%d/%y %I:%M %p")
    rows, date, time, match, team = [], None, None, None, None
    for line in txt.splitlines():
        if "Game Date" in line and "Player Name" in line: continue
        d = DATE_RE.search(line); t = TIME_RE.search(line); mm = MATCH_RE.search(line); tm = TEAM_RE.search(line)
        if d: date = d.group(1)
        if t: time = t.group(1)
        if mm: match = mm.group(0)
        if tm: team = tm.group(1)
        if "NOT YET SUBMITTED" in line:
            rows.append((snap, asof, date, time, match, team, None, "NOT YET SUBMITTED")); continue
        for p in PLAYER_RE.finditer(line):
            rows.append((snap, asof, date, time, match, team, p.group(1).strip(), p.group(2)))
    return rows


if __name__ == "__main__":
    folder, out = sys.argv[1], sys.argv[2]
    files = sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".pdf"))
    with ProcessPoolExecutor(8) as ex:
        allrows = [r for rows in ex.map(parse, files, chunksize=20) for r in rows]
    df = pd.DataFrame(allrows, columns=["snapshot", "as_of", "game_date", "game_time_et", "matchup", "team", "player", "status"])
    df.to_csv(out, index=False)
    print(len(files), "files ->", len(df), "rows"); print(df.status.value_counts().to_dict())
    print("rows missing team/date/matchup:", df[["team", "game_date", "matchup"]].isna().any(axis=1).sum())
