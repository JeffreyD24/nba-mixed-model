import os
"""
Pre-game projected lineups for every team-game (no lookahead). Used by Model 2.

For each game, team, and injury-report snapshot (open = night before, pretip = last report >= 60 min before tip):
  roster      players whose latest regular-season game (before today) was for this team, within the last
              45 days, plus anyone on this team's injury report. Before a team's first regular-season game,
              its preseason roster is used.
  base min    average minutes over his last 10 team games in which he was not out injured, resting, or away
              from the team (coach's-decision DNPs count as 0), shrunk toward last season's average
              (or his preseason average if he has nothing else) with the weight of 3 games.
  available   1 - p_miss(status) if he is on the report (p_miss measured on the training seasons), else 1.
  projected   base * available, rescaled so the team's projected minutes sum to 240.
  rating      his final EPM (offense, defense) from LAST season; unrated players get -1.0 / -0.5.

Output: lineups.pkl  {(row_index, side, kind): dict(pids, w=proj/48, s_off, s_def, n_unrated)}
"""
import re, pickle, unicodedata, sys
import numpy as np, pandas as pd

sys.path.insert(0, "/home/claude/nba-mixed-model")
from build_report_features import key, FULL2ABBR, ABBR2GAMES

W = "/home/claude/work/"
UNRATED_OFF, UNRATED_DEF = -1.0, -0.5
LAST_N, PRIOR_K, ROSTER_DAYS = 10, 3.0, 45
REG_TYPES = {"Regular Season", "NBA Emirates Cup", "Emirates NBA Cup", "NBA Cup", "in-season-knockout"}
ABSENT = re.compile(r"Injury|Illness|Rest|NWT|Suspension|G League|Personal|Not With Team", re.I)


def season_of(d):
    return d.year + 1 if d.month >= 8 else d.year


games = pd.read_csv(W + "games_v2.csv", parse_dates=["date"])
codes = pd.read_csv(W + "team_codes.csv", index_col=0).code.to_dict()          # tid -> code
code2tid = {c: t for t, c in codes.items()}
abbr2tid = {a: code2tid[c] for a, c in ABBR2GAMES.items()}

# ---------------- box score history
P = pd.read_parquet(W + "players_min.parquet")
P["date"] = pd.to_datetime(P.d.dt.date)
P["season"] = P.date.map(season_of)
P = P[P.playerteamId.isin(codes.keys())].copy()
P["reg"] = P.gameType.isin(REG_TYPES)
P["pre"] = P.gameType.eq("Preseason")
P = P[P.reg | P.pre]
P["k"] = (P.firstName.fillna("") + " " + P.lastName.fillna("")).map(key)
# absent = DNP reason says injury/rest/away, or (no reasons in some seasons) he was listed Out/Doubtful
# on that day's official injury report and did not play
_rep = pd.read_csv(W + "injury_reports_parsed.csv", usecols=["game_date", "team", "player", "status", "snapshot"])
_rep = _rep[_rep.status.isin(["Out", "Doubtful"]) & _rep.player.notna()]
_rep["gd"] = pd.to_datetime(_rep.game_date, format="%m/%d/%Y")
_rep = _rep[_rep.snapshot.str[:10] == _rep.gd.dt.strftime("%Y-%m-%d")]      # game-day reports only
_rep["tid"] = _rep.team.map(FULL2ABBR).map(ABBR2GAMES).map({c: t for t, c in codes.items()})
listed_out = set(zip(_rep.gd, _rep.tid, _rep.player.map(key)))
P["absent"] = P.comment.fillna("").str.contains(ABSENT) | (
    (P.MIN <= 0) & np.array([x in listed_out for x in zip(P.date, P.playerteamId, P.k)]))
print("absent rows by season:", P[P.reg].groupby("season").absent.mean().round(3).to_dict())
P = P.sort_values("date")
REG = P[P.reg]
PRE = P[P.pre]

# last-season average minutes per player (regular season, games he was available for)
avail_rows = REG[~REG.absent]
last_mpg = avail_rows.groupby(["personId", "season"]).MIN.mean().to_dict()
pre_mpg = PRE[PRE.MIN > 0].groupby(["personId", "season"]).MIN.mean().to_dict()

# per-player arrays of regular-season rows: dates, team, minutes, absent
hist = {pid: (g.date.values, g.playerteamId.values, g.MIN.values, g.absent.values)
        for pid, g in REG.groupby("personId")}
# team regular-season rosters by date: for each team, players and their latest row date with that team
team_days = {t: np.sort(g.date.unique()) for t, g in REG.groupby("playerteamId")}

# ---------------- ratings: final EPM of each season
E = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/external/kaggle/deocheng_epm/public.player_epm.csv.gz"), usecols=["nba_player_id", "season", "game_dt", "epm_off", "epm_def"])
E = E.sort_values("game_dt").groupby(["nba_player_id", "season"]).tail(1)
rating = {(r.nba_player_id, r.season): (r.epm_off, r.epm_def) for r in E.itertuples()}

# ---------------- name -> id
ids_team = P.groupby(["k", "season", "playerteamId"]).personId.agg(lambda s: s.mode()[0]).to_dict()
ids_any = P.groupby("k").personId.agg(lambda s: s.mode()[0]).to_dict()

# ---------------- injury reports and snapshot choice (same rules as build_report_features.py)
rep = pd.read_csv(W + "injury_reports_parsed.csv")
rep["gd"] = pd.to_datetime(rep.game_date, format="%m/%d/%Y")
rep["tid"] = rep.team.map(FULL2ABBR).map(abbr2tid)
rep["snap_day"] = pd.to_datetime(rep.snapshot.str[:10]); rep["slot"] = rep.snapshot.str[11:]
rep["as_of"] = pd.to_datetime(rep.as_of)
slot_time = {"11AM": 11.5, "01PM": 13.5, "03PM": 15.5, "05PM": 17.5, "06PM": 18.5, "07PM": 19.5, "08PM": 20.5, "09PM": 21.5}
rep["as_of"] = rep.as_of.fillna(rep.snap_day + pd.to_timedelta(rep.slot.map(slot_time), unit="h"))
rep["k"] = rep.player.map(key)
tip = rep.dropna(subset=["game_time_et"]).groupby(["gd", "tid"]).game_time_et.agg(lambda s: s.mode()[0]).to_dict()
nys = set(map(tuple, rep[rep.status == "NOT YET SUBMITTED"][["gd", "tid", "snapshot"]].values))
snaps_by_day = {d: g[["snapshot", "as_of"]].drop_duplicates() for d, g in rep.groupby("gd")}
listed = {k: list(zip(g.k, g.status)) for k, g in rep[rep.player.notna()].groupby(["gd", "tid", "snapshot"])}
p_miss = pd.read_csv("/home/claude/nba-mixed-model/data/p_miss.csv", index_col=0).iloc[:, 0].dropna().to_dict()
p_miss = {k: v for k, v in p_miss.items() if isinstance(k, str)}
print("p_miss:", {k: round(v, 3) for k, v in p_miss.items()})


def pick(d, t, kind):
    g = snaps_by_day.get(d)
    if g is None: return None
    have = set(g.snapshot)
    ok = lambda s: (d, t, s) not in nys
    if kind == "open":
        for s in [f"{(d - pd.Timedelta(days=1)).date()}_08PM", f"{(d - pd.Timedelta(days=1)).date()}_09PM",
                  f"{d.date()}_11AM", f"{d.date()}_01PM"]:
            if s in have and ok(s): return s
        return None
    tt = tip.get((d, t))
    if tt is None: return None
    hh, mm = map(int, tt.split(":")); hh = hh + 12 if hh < 11 else hh
    tip_dt = d + pd.Timedelta(hours=hh, minutes=mm)
    g2 = g[g.as_of <= tip_dt - pd.Timedelta(minutes=60)].sort_values("as_of")
    for s in reversed(g2.snapshot.tolist()):
        if ok(s): return s
    return None


def base_minutes(pid, d, s):
    h = hist.get(pid)
    prior = last_mpg.get((pid, s - 1))
    if prior is None: prior = pre_mpg.get((pid, s))
    if h is not None:
        dates, teams, mins, absent = h
        n = np.searchsorted(dates, np.datetime64(d), side="left")
        lo = np.searchsorted(dates, np.datetime64(pd.Timestamp(year=s - 1, month=8, day=1)), side="left")
        idx = [i for i in range(n - 1, lo - 1, -1) if not absent[i]][:LAST_N]
        if idx:
            tot = float(mins[idx].sum()); k = len(idx)
            if prior is None: return tot / k
            return (tot + PRIOR_K * prior) / (k + PRIOR_K)
    return 0.0 if prior is None else prior


def roster(t, d, s):
    """players whose latest regular-season row (any team, this season, before d) is with team t"""
    start = np.datetime64(pd.Timestamp(year=s - 1, month=8, day=1)); dd = np.datetime64(d)
    days = team_days.get(t, np.array([], dtype="datetime64[ns]"))
    played_this_season = ((days >= start) & (days < dd)).any()
    out = set()
    if played_this_season:
        cand = REG[(REG.playerteamId == t) & (REG.date >= d - pd.Timedelta(days=ROSTER_DAYS)) & (REG.date < d)].personId.unique()
        for pid in cand:
            dates, teams, _, _ = hist[pid]
            n = np.searchsorted(dates, dd, side="left")
            if n and teams[n - 1] == t: out.add(pid)
    else:
        pre = PRE[(PRE.season == s) & (PRE.date < d)]
        last_team = pre.groupby("personId").playerteamId.last()
        out = set(last_team[last_team == t].index)
    return out


# speed: restrict REG to the needed columns for the roster query
REG = REG[["personId", "playerteamId", "date"]].copy()

out = {}
last_pretip_status = {}          # team -> statuses from its previous game's pre-tip report (open-line fallback)
games = games.sort_values("date")
for n_done, gm in enumerate(games.itertuples()):
    d, s = gm.date, gm.season
    for side in ("home", "away"):
        t = getattr(gm, f"{side}_tid")
        base_roster = roster(t, d, s)
        for kind in ("pretip", "open"):
            sn = pick(d, t, kind)
            lst = listed.get((d, t, sn), []) if sn else []
            status = {}
            for k_, st in lst:
                pid = ids_team.get((k_, s, t), ids_any.get(k_))
                if pid is not None: status[pid] = st
            if kind == "pretip":
                pretip_status = status
            elif sn is None and t in last_pretip_status:          # no report filed yet: use previous game's
                status, sn = last_pretip_status[t], "previous game"
            pids = sorted(base_roster | set(status))
            base = np.array([base_minutes(p, d, s) for p in pids])
            avail = np.array([1.0 - p_miss.get(status.get(p, ""), 0.0) if p in status else 1.0 for p in pids])
            proj = base * avail
            tot = proj.sum()
            if tot > 0:
                for _ in range(10):                    # rescale to 240, no one above 42 minutes
                    proj = proj * 240.0 / proj.sum()
                    if proj.max() <= 42.0 + 1e-9: break
                    capped = proj >= 42.0
                    proj[capped] = 42.0
                    rest = 240.0 - proj[capped].sum()
                    if proj[~capped].sum() > 0:
                        proj[~capped] *= rest / proj[~capped].sum()
                        if proj.max() <= 42.0 + 1e-9: break
                    else:
                        break
            keep = proj > 0.05
            pids = np.array(pids)[keep]; w = proj[keep] / 48.0
            r = np.array([rating.get((p, s - 1), (UNRATED_OFF, UNRATED_DEF)) for p in pids]).reshape(-1, 2)
            out[(gm.Index, side, kind)] = dict(pids=pids, w=w, s_off=float(w @ r[:, 0]), s_def=float(w @ r[:, 1]),
                                               n_unrated=int(sum((p, s - 1) not in rating for p in pids)),
                                               snap=sn, base_total=float(tot))
        last_pretip_status[t] = pretip_status
    if n_done % 1000 == 0: print(n_done, flush=True)

pickle.dump(out, open(W + "lineups.pkl", "wb"))
df = pd.DataFrame([(k[0], k[1], k[2], v["s_off"], v["s_def"], len(v["pids"]), v["n_unrated"], v["base_total"], v["snap"])
                   for k, v in out.items()], columns=["gi", "side", "kind", "s_off", "s_def", "n_players", "n_unrated", "base_total", "snap"])
df.to_csv(W + "lineup_summary.csv", index=False)
print(df.groupby("kind")[["s_off", "s_def", "n_players", "n_unrated", "base_total"]].describe().T.round(2).to_string())
print("missing snapshot:", df.snap.isna().groupby(df.kind).mean().round(3).to_dict())
