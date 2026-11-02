"""
NBA shots from ESPN play-by-play, for the shot-quality (expected points) model. One row per field-goal attempt:
game, date, team, shooter, period, clock, court x/y (feet; x 0-50 across, y from the baseline), distance (from the play
text), 2 or 3 points, made, ESPN's shot type (Jump Shot, Pullup Jump Shot, Driving Layup Shot, Cutting Dunk Shot...).
Plus free throws per team-game.
  python nba_shots.py WORKDIR [CACHE_DIR]      every game in research/minutes_history -> data/nba_shots_hist.csv(.gz)
"""
import os, sys, re, json, pickle, urllib.request, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event="
DIST = re.compile(r"(\d+)-foot")


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def game_shots(eid, team_of):
    d = get(ESPN + str(eid))
    if not d: return None
    out, ft = [], {}
    for p in d.get("plays", []):
        if not p.get("shootingPlay"): continue
        tid = str((p.get("team") or {}).get("id")); team = team_of.get(tid)
        typ = (p.get("type") or {}).get("text") or ""
        if typ.startswith("Free Throw"):
            f = ft.setdefault(team, [0, 0]); f[0] += 1; f[1] += int(bool(p.get("scoringPlay"))); continue
        c = p.get("coordinate") or {}; m = DIST.search(p.get("text") or "")
        clock = (p.get("clock") or {}).get("displayValue", "0:00")
        try: mm, ss = clock.split(":"); sec_left = int(mm) * 60 + float(ss)
        except ValueError: sec_left = None
        parts = p.get("participants") or []
        out.append(dict(espn_event_id=int(eid), team=team, shooter_id=(parts[0].get("athlete") or {}).get("id") if parts else None,
                        period=(p.get("period") or {}).get("number"), sec_left=sec_left,
                        x=c.get("x") if abs(c.get("x") or 0) < 1000 else None, y=c.get("y") if abs(c.get("y") or 0) < 1000 else None,
                        dist=int(m.group(1)) if m else (0 if re.search(r"dunk|layup|tip", typ, re.I) else None),
                        value=p.get("pointsAttempted"), made=int(bool(p.get("scoringPlay"))), shot_type=typ,
                        text=(p.get("text") or "")[:120]))
    return out, ft


def main():
    W = os.path.abspath(sys.argv[1]); cache = sys.argv[2] if len(sys.argv) > 2 else os.path.join(W, "_tmp", "nba_shots_cache")
    os.makedirs(cache, exist_ok=True)
    H = pd.concat([pd.read_csv(os.path.join(W, "research", "minutes_history", f)) for f in sorted(os.listdir(os.path.join(W, "research", "minutes_history")))])
    games = H.drop_duplicates("espn_event_id")[["season", "espn_event_id", "date", "away", "home"]]
    team_of = {str(int(t)): c for t, c in H.drop_duplicates("team_id")[["team_id", "team"]].values}

    def one(eid):
        pth = os.path.join(cache, f"{eid}.pkl")
        if os.path.exists(pth): return pickle.load(open(pth, "rb"))
        v = game_shots(eid, team_of)
        if v is not None: pickle.dump(v, open(pth, "wb"))
        return v
    with ThreadPoolExecutor(24) as ex:
        res = list(ex.map(one, games.espn_event_id))
    shots, fts = [], []
    for (s_, e, d, a, h), r in zip(games.values, res):
        if not r: continue
        sh, ft = r
        for x in sh: x.update(season=s_, date=d, away=a, home=h)
        shots += sh
        for t, (fta, ftm) in ft.items(): fts.append(dict(season=s_, espn_event_id=e, date=d, team=t, fta=fta, ftm=ftm))
    S = pd.DataFrame(shots); F = pd.DataFrame(fts)
    S.to_csv(os.path.join(W, "data", "nba_shots_hist.csv.gz"), index=False, compression="gzip")
    F.to_csv(os.path.join(W, "data", "nba_free_throws_hist.csv"), index=False)
    print(len(S), "field-goal attempts in", S.espn_event_id.nunique(), "of", len(games), "games;", len(F), "team free-throw rows")


if __name__ == "__main__":
    main()
