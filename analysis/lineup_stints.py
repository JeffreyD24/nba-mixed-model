"""
NBA stints: every stretch with the same ten players on the floor, with the score change during it, rebuilt from ESPN's
play-by-play using the same on-court logic as rotations.py (starters, substitutions, quarter-start inference).
Then player ratings from stints (regularized adjusted plus-minus, "RAPM": each player's effect on the score margin per
48 minutes while on the floor, holding the other nine players fixed, shrunk toward zero).
  python analysis/lineup_stints.py WORKDIR [CACHE_DIR]  -> data/nba_stints_hist.csv.gz, analysis/rapm_by_season.csv
"""
import os, sys, json, pickle, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
import espn
from rotations import _sec, PERIOD_SEC


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def stints(s, eid):
    ha = {c["team"]["id"]: c["homeAway"] for c in s["header"]["competitions"][0]["competitors"]}
    teams, info = {}, {}
    for tb in s["boxscore"]["players"]:
        tid = tb["team"]["id"]; teams[tid] = espn.ESPN2.get(tb["team"]["abbreviation"])
        for a in tb["statistics"][0]["athletes"]:
            ath = a.get("athlete") or {}; aid = ath.get("id") or f"name:{ath.get('displayName')}"
            info[aid] = dict(team_id=tid, starter=bool(a.get("starter")))
    plays = s.get("plays", [])
    nper = max([p["period"]["number"] for p in plays] + [4])
    prev_end = {tid: [a for a, v in info.items() if v["team_id"] == tid and v["starter"]] for tid in teams}
    hid = next(t for t, x in ha.items() if x == "home"); aid_ = next(t for t, x in ha.items() if x == "away")
    out, hs, as_ = [], 0, 0
    for per in range(1, nper + 1):
        L = PERIOD_SEC(per); pp = [p for p in plays if p["period"]["number"] == per]; on = {}
        for tid in teams:
            if per == 1: start = list(prev_end[tid])
            else:
                first = {}
                for p in pp:
                    is_sub = p.get("type", {}).get("text") == "Substitution"
                    for k, part in enumerate(p.get("participants", []) or []):
                        a = part.get("athlete", {}).get("id")
                        if a not in info or info[a]["team_id"] != tid or a in first: continue
                        first[a] = "in" if (is_sub and k == 0) else "on"
                start = [a for a, v in first.items() if v == "on"][:5]
                for a in prev_end[tid]:
                    if len(start) >= 5: break
                    if a not in first and a not in start: start.append(a)
                for a in prev_end[tid]:
                    if len(start) >= 5: break
                    if a not in start and first.get(a) != "in": start.append(a)
            on[tid] = set(start)
        t0, h0, a0 = L, hs, as_
        def close(t_end):
            if t0 - t_end > 0 or hs != h0 or as_ != a0:
                out.append(dict(espn_event_id=eid, period=per, start_left=t0, end_left=t_end, sec=t0 - t_end,
                                home_players="|".join(sorted(on[hid])), away_players="|".join(sorted(on[aid_])),
                                home_pts=hs - h0, away_pts=as_ - a0))
        for p in pp:
            if p.get("homeScore") is not None: hs, as_ = int(p["homeScore"]), int(p["awayScore"])
            if p.get("type", {}).get("text") == "Substitution":
                parts = [x.get("athlete", {}).get("id") for x in (p.get("participants") or [])]
                if len(parts) >= 2 and parts[0] in info:
                    t = _sec(p["clock"]["displayValue"])
                    if np.isnan(t): continue
                    close(t); t0, h0, a0 = t, hs, as_
                    tid = info[parts[0]]["team_id"]; on[tid].discard(parts[1]); on[tid].add(parts[0])
        close(0.0)
        for tid in teams: prev_end[tid] = list(on[tid])
    return out


def main():
    cache = sys.argv[2] if len(sys.argv) > 2 else os.path.join(W, "_tmp", "nba_summary_cache"); os.makedirs(cache, exist_ok=True)
    H = pd.concat([pd.read_csv(os.path.join(W, "research", "minutes_history", f)) for f in sorted(os.listdir(os.path.join(W, "research", "minutes_history")))])
    games = H.drop_duplicates("espn_event_id")[["season", "espn_event_id", "date", "away", "home"]]

    def one(eid):
        pth = os.path.join(cache, f"{eid}.pkl")
        if os.path.exists(pth): return pickle.load(open(pth, "rb"))
        s = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={eid}")
        if not s: return None
        try: v = stints(s, int(eid))
        except Exception as e: v = []
        pickle.dump(v, open(pth, "wb")); return v
    with ThreadPoolExecutor(24) as ex: res = list(ex.map(one, games.espn_event_id))
    rows = []
    for (season, eid, date, away, home), r in zip(games.values, res):
        for x in r or []: x.update(season=season, date=date, home=home, away=away); rows.append(x)
    S = pd.DataFrame(rows); S.to_csv(os.path.join(W, "data", "nba_stints_hist.csv.gz"), index=False, compression="gzip")
    g = S.groupby("espn_event_id").agg(sec=("sec", "sum"), hp=("home_pts", "sum"))
    print(len(S), "stints in", S.espn_event_id.nunique(), "games; median game length", round(g.sec.median() / 60, 1), "min;",
          "games where every stint has 5 v 5:", round(((S.home_players.str.count(r"\|") == 4) & (S.away_players.str.count(r"\|") == 4)).groupby(S.espn_event_id).all().mean(), 3))
    # RAPM per season (all games of the season; for model testing use prior seasons only)
    from scipy.sparse import csr_matrix
    from scipy.sparse.linalg import lsqr
    names = H.drop_duplicates("athlete_id").set_index("athlete_id").player.to_dict()
    out = []
    for season, d in S[S.sec > 0].groupby("season"):
        hp = d.home_players.str.split("|"); ap = d.away_players.str.split("|")
        players = sorted(set(x for l in hp for x in l) | set(x for l in ap for x in l)); ix = {p: i for i, p in enumerate(players)}
        r, c, v = [], [], []
        for i, (h, a) in enumerate(zip(hp, ap)):
            for p in h: r.append(i); c.append(ix[p]); v.append(1.0)
            for p in a: r.append(i); c.append(ix[p]); v.append(-1.0)
        X = csr_matrix((v, (r, c)), shape=(len(d), len(players)))
        y = ((d.home_pts - d.away_pts) / d.sec * 2880).values                        # margin per 48 minutes
        w = np.sqrt(d.sec.values)
        lam = 2000.0
        Xw = csr_matrix(X.multiply(w[:, None])); yw = y * w
        b = lsqr(Xw, yw, damp=np.sqrt(lam))[0]
        mins = np.asarray(abs(X).multiply(d.sec.values[:, None]).sum(axis=0)).ravel() / 60
        out += [dict(season=season, athlete_id=p, player=names.get(int(p)) if str(p).isdigit() else p, rapm=round(b[ix[p]], 2),
                     minutes=round(mins[ix[p]], 0)) for p in players]
    R = pd.DataFrame(out).sort_values(["season", "rapm"], ascending=[True, False])
    R.to_csv(os.path.join(W, "analysis", "rapm_by_season.csv"), index=False)
    for s_, g_ in R[R.minutes >= 1000].groupby("season"):
        print(s_, "top:", ", ".join(f"{p} {v:+.1f}" for p, v in zip(g_.player.head(5), g_.rapm.head(5))))
    a = R.pivot_table(index="athlete_id", columns="season", values="rapm")
    m = R.pivot_table(index="athlete_id", columns="season", values="minutes")
    for s_ in sorted(R.season.unique())[:-1]:
        ok = (m.get(s_, 0) >= 800) & (m.get(s_ + 1, 0) >= 800)
        print(f"  year-to-year RAPM correlation {s_}->{s_ + 1}: {a.loc[ok, s_].corr(a.loc[ok, s_ + 1]):+.2f} ({int(ok.sum())} players)")


if __name__ == "__main__":
    main()
