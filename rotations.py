"""
Who played when: each player's minutes by quarter, rebuilt from ESPN's play-by-play.

Starters come from the box score; every substitution ("A enters the game for B") has its quarter and clock.
Players who start a later quarter are found from the plays (a player whose first action in a quarter isn't
coming in off the bench was already on the floor). Totals are checked against the box score's minutes.
"""
import numpy as np, pandas as pd
import espn

PERIOD_SEC = lambda p: 720 if p <= 4 else 300


def _sec(clock):
    try:
        if ":" in clock:
            m, s = clock.split(":"); return int(m) * 60 + float(s)
        return float(clock)
    except Exception:
        return np.nan


def game_minutes(event_id):
    """returns (rows, check): rows = one dict per player with minutes by period; check = max |our total - box score| in minutes"""
    s = espn._get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={event_id}")
    teams, info = {}, {}
    for tb in s["boxscore"]["players"]:
        tid = tb["team"]["id"]; code = espn.ESPN2.get(tb["team"]["abbreviation"])
        st = tb["statistics"][0]; names = st["names"]
        for a in st["athletes"]:
            ath = a.get("athlete") or {}
            aid = ath.get("id") or f"name:{ath.get('displayName') or ath.get('shortName')}"   # a few deep-bench entries have no ID
            mins = a["stats"][names.index("MIN")] if a.get("stats") and "MIN" in names else None
            info[aid] = dict(team_id=tid, team=code, athlete_id=aid, player=ath.get("displayName") or ath.get("shortName"), starter=bool(a.get("starter")),
                             box_min=float(mins) if mins not in (None, "", "--") else 0.0, dnp=bool(a.get("didNotPlay")))
        teams[tid] = code
    plays = s.get("plays", [])
    nper = max([p["period"]["number"] for p in plays] + [4])
    secs = {aid: {} for aid in info}
    prev_end = {tid: [a for a, v in info.items() if v["team_id"] == tid and v["starter"]] for tid in teams}
    for per in range(1, nper + 1):
        L = PERIOD_SEC(per)
        pp = [p for p in plays if p["period"]["number"] == per]
        on = {}
        for tid in teams:
            if per == 1:
                start = set(prev_end[tid])
            else:
                first = {}
                for p in pp:
                    is_sub = p.get("type", {}).get("text") == "Substitution"
                    for k, part in enumerate(p.get("participants", []) or []):
                        aid = part.get("athlete", {}).get("id")
                        if aid not in info or info[aid]["team_id"] != tid or aid in first: continue
                        first[aid] = "in" if (is_sub and k == 0) else "on"
                start = [a for a, v in first.items() if v == "on"][:5]     # earliest-seen first; never more than 5
                for a in prev_end[tid]:              # quiet players: carry over from the end of the last quarter
                    if len(start) >= 5: break
                    if a not in first and a not in start: start.append(a)
                for a in prev_end[tid]:              # still short: anyone from the last lineup not seen coming in
                    if len(start) >= 5: break
                    if a not in start and first.get(a) != "in": start.append(a)
            on[tid] = set(start)
        t_prev = L
        for p in pp + [None]:
            t = 0.0 if p is None else _sec(p["clock"]["displayValue"])
            if np.isnan(t): continue
            dt = max(0.0, t_prev - t)
            for tid in teams:
                for a in on[tid]: secs[a][per] = secs[a].get(per, 0.0) + dt
            t_prev = t
            if p is not None and p.get("type", {}).get("text") == "Substitution":
                parts = [x.get("athlete", {}).get("id") for x in (p.get("participants") or [])]
                if len(parts) >= 2 and parts[0] in info:
                    tid = info[parts[0]]["team_id"]
                    on[tid].discard(parts[1]); on[tid].add(parts[0])
        for tid in teams: prev_end[tid] = list(on[tid])
    rows, worst = [], 0.0
    for aid, v in info.items():
        r = dict(v); total = 0.0
        for per in range(1, nper + 1):
            m = round(secs[aid].get(per, 0.0) / 60, 2)
            r[f"q{per}" if per <= 4 else f"ot{per - 4}"] = m; total += m
        r["h1"] = round(r.get("q1", 0) + r.get("q2", 0), 2)
        r["h2"] = round(r.get("q3", 0) + r.get("q4", 0), 2)
        r["total_min"] = round(total, 2)
        r["diff_vs_box"] = round(total - v["box_min"], 2)
        if not v["dnp"]: worst = max(worst, abs(total - v["box_min"]))
        rows.append(r)
    return rows, round(worst, 2)
