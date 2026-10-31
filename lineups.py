"""
Pre-game projected lineups (no lookahead). Used by Model 2, in the backtests and live.

For each game, team, and injury-report snapshot (open = night before, pretip = last report >= 60 min before tip):
  roster      players whose latest regular-season game (before today, this season) was for this team, within
              the last 45 days, plus anyone on this team's injury report. Before a team's first regular-season
              game, its preseason roster is used.
  base min    average minutes over his last 10 team games in which he wasn't out injured, resting or away from
              the team (coach's-decision DNPs count as 0), shrunk toward last season's average (or his preseason
              average if he has nothing else) with the weight of 3 games.
  available   1 - p_miss(status) if he is on the report (p_miss measured on the training seasons), else 1.
              If the team hasn't filed the night-before report, its previous game's pre-tip report is used.
  projected   base * available, rescaled so the team's projected minutes sum to 240 (no one above 42).
  rating      his final EPM (offense, defense) from LAST season; unrated players get -1.0 / -0.5.
"""
import re
import numpy as np, pandas as pd
from build_report_features import key, FULL2ABBR, ABBR2GAMES

UNRATED_OFF, UNRATED_DEF = -1.0, -0.5
LAST_N, PRIOR_K, ROSTER_DAYS, MAX_MIN = 10, 3.0, 45, 42.0
REG_TYPES = {"Regular Season", "NBA Emirates Cup", "Emirates NBA Cup", "NBA Cup", "in-season-knockout"}
ABSENT = re.compile(r"Injury|Illness|Rest|NWT|Suspension|G League|Personal|Not With Team", re.I)
SLOT_TIME = {"11AM": 11.5, "01PM": 13.5, "03PM": 15.5, "05PM": 17.5, "06PM": 18.5, "07PM": 19.5, "08PM": 20.5, "09PM": 21.5}


def season_of(d):
    return d.year + 1 if d.month >= 8 else d.year


def prepare_box(P, reports, code2tid):
    """P: player box rows with personId, playerteamId, date, MIN, comment, gameType, firstName, lastName.
    Adds season, reg/pre flags, name key and the 'absent' flag."""
    P = P.copy()
    P["date"] = pd.to_datetime(P.date).dt.normalize()
    P["season"] = P.date.map(season_of)
    P = P[P.playerteamId.isin(set(code2tid.values()))].copy()
    P["reg"] = P.gameType.isin(REG_TYPES); P["pre"] = P.gameType.eq("Preseason")
    P = P[P.reg | P.pre].copy()
    P["MIN"] = pd.to_numeric(P.MIN, errors="coerce").fillna(0.0)
    P["k"] = (P.firstName.fillna("") + " " + P.lastName.fillna("")).map(key)
    r = reports[reports.status.isin(["Out", "Doubtful"]) & reports.player.notna()].copy()
    r["gd"] = pd.to_datetime(r.game_date, format="%m/%d/%Y")
    r = r[r.snapshot.str[:10] == r.gd.dt.strftime("%Y-%m-%d")]
    abbr2tid = {a: code2tid[c] for a, c in ABBR2GAMES.items() if c in code2tid}
    r["tid"] = r.team.map(FULL2ABBR).map(abbr2tid)
    listed_out = set(zip(r.gd, r.tid, r.player.map(key)))
    P["absent"] = P.comment.fillna("").astype(str).str.contains(ABSENT) | (
        (P.MIN <= 0) & np.array([x in listed_out for x in zip(P.date, P.playerteamId, P.k)], dtype=bool))
    return P.sort_values("date")


class LineupBuilder:
    def __init__(self, box, reports, rating, p_miss, code2tid, extra_last_mpg=None):
        """box from prepare_box; reports = parsed official reports; rating {(pid, season): (off, def)};
        extra_last_mpg {(pid, season): mpg} for seasons not covered by box (live: last season)."""
        self.code2tid = code2tid
        abbr2tid = {a: code2tid[c] for a, c in ABBR2GAMES.items() if c in code2tid}
        self.rating, self.p_miss = rating, p_miss
        REG, PRE = box[box.reg], box[box.pre]
        self.last_mpg = dict(extra_last_mpg or {})
        self.last_mpg.update(REG[~REG.absent].groupby(["personId", "season"]).MIN.mean().to_dict())
        self.pre_mpg = PRE[PRE.MIN > 0].groupby(["personId", "season"]).MIN.mean().to_dict()
        self.hist = {pid: (g.date.values, g.playerteamId.values, g.MIN.values, g.absent.values) for pid, g in REG.groupby("personId")}
        self.team_days = {t: np.sort(g.date.unique()) for t, g in REG.groupby("playerteamId")}
        self.REG = REG[["personId", "playerteamId", "date"]]
        self.PRE = PRE[["personId", "playerteamId", "date", "season"]]
        self.ids_team = box.groupby(["k", "season", "playerteamId"]).personId.agg(lambda s: s.mode()[0]).to_dict()
        self.ids_any = box.groupby("k").personId.agg(lambda s: s.mode()[0]).to_dict()
        rep = reports.copy()
        rep["gd"] = pd.to_datetime(rep.game_date, format="%m/%d/%Y")
        rep["tid"] = rep.team.map(FULL2ABBR).map(abbr2tid)
        rep["snap_day"] = pd.to_datetime(rep.snapshot.str[:10]); rep["slot"] = rep.snapshot.str[11:]
        rep["as_of"] = pd.to_datetime(rep.as_of, errors="coerce")
        rep["as_of"] = rep.as_of.fillna(rep.snap_day + pd.to_timedelta(rep.slot.map(SLOT_TIME), unit="h"))
        rep["k"] = rep.player.map(key)
        self.tip = rep.dropna(subset=["game_time_et"]).groupby(["gd", "tid"]).game_time_et.agg(lambda s: s.mode()[0]).to_dict()
        self.nys = set(map(tuple, rep[rep.status == "NOT YET SUBMITTED"][["gd", "tid", "snapshot"]].values))
        self.snaps_by_day = {d: g[["snapshot", "as_of"]].drop_duplicates() for d, g in rep.groupby("gd")}
        self.listed = {k: list(zip(g.k, g.status)) for k, g in rep[rep.player.notna()].groupby(["gd", "tid", "snapshot"])}

    def pick(self, d, t, kind):
        g = self.snaps_by_day.get(d)
        if g is None: return None
        have = set(g.snapshot)
        ok = lambda s: (d, t, s) not in self.nys
        if kind == "open":
            for s in [f"{(d - pd.Timedelta(days=1)).date()}_08PM", f"{(d - pd.Timedelta(days=1)).date()}_09PM",
                      f"{d.date()}_11AM", f"{d.date()}_01PM"]:
                if s in have and ok(s): return s
            return None
        tt = self.tip.get((d, t))
        if tt is None: return None
        hh, mm = map(int, tt.split(":")); hh = hh + 12 if hh < 11 else hh
        tip_dt = d + pd.Timedelta(hours=hh, minutes=mm)
        g2 = g[g.as_of <= tip_dt - pd.Timedelta(minutes=60)].sort_values("as_of")
        for s in reversed(g2.snapshot.tolist()):
            if ok(s): return s
        return None

    def base_minutes(self, pid, d, s):
        h = self.hist.get(pid)
        prior = self.last_mpg.get((pid, s - 1))
        if prior is None: prior = self.pre_mpg.get((pid, s))
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

    def roster(self, t, d, s):
        start = np.datetime64(pd.Timestamp(year=s - 1, month=8, day=1)); dd = np.datetime64(d)
        days = self.team_days.get(t, np.array([], dtype="datetime64[ns]"))
        out = set()
        if ((days >= start) & (days < dd)).any():
            R = self.REG
            cand = R[(R.playerteamId == t) & (R.date >= d - pd.Timedelta(days=ROSTER_DAYS)) & (R.date < d)].personId.unique()
            for pid in cand:
                dates, teams, _, _ = self.hist[pid]
                n = np.searchsorted(dates, dd, side="left")
                if n and teams[n - 1] == t: out.add(pid)
        else:
            pre = self.PRE[(self.PRE.season == s) & (self.PRE.date < d)]
            last_team = pre.groupby("personId").playerteamId.last()
            out = set(last_team[last_team == t].index)
        return out

    def project(self, pids, status, d, s):
        base = np.array([self.base_minutes(p, d, s) for p in pids])
        avail = np.array([1.0 - self.p_miss.get(status.get(p, ""), 0.0) if p in status else 1.0 for p in pids])
        proj = base * avail; tot = float(proj.sum())
        if tot > 0:
            for _ in range(10):
                proj = proj * 240.0 / proj.sum()
                if proj.max() <= MAX_MIN + 1e-9: break
                capped = proj >= MAX_MIN; proj[capped] = MAX_MIN
                rest = 240.0 - proj[capped].sum()
                if proj[~capped].sum() > 0:
                    proj[~capped] *= rest / proj[~capped].sum()
                    if proj.max() <= MAX_MIN + 1e-9: break
                else:
                    break
        return proj, tot

    def build(self, games, kinds=("pretip", "open"), last_pretip_status=None):
        """games: DataFrame with date, season, home, away (codes); returns {(index, side, kind): lineup dict}"""
        out = {}
        last = dict(last_pretip_status or {})
        for gm in games.sort_values("date").itertuples():
            d, s = pd.Timestamp(gm.date), gm.season
            for side in ("home", "away"):
                t = self.code2tid[getattr(gm, side)]
                base_roster = self.roster(t, d, s)
                pretip_status = {}
                for kind in ("pretip", "open"):
                    if kind not in kinds and kind != "pretip": continue
                    sn = self.pick(d, t, kind)
                    status = {}
                    for k_, st in (self.listed.get((d, t, sn), []) if sn else []):
                        pid = self.ids_team.get((k_, s, t), self.ids_any.get(k_))
                        if pid is not None: status[pid] = st
                    if kind == "pretip":
                        pretip_status = status
                    elif sn is None and t in last:
                        status, sn = last[t], "previous game"
                    pids = sorted(base_roster | set(status))
                    proj, tot = self.project(pids, status, d, s)
                    keep = proj > 0.05
                    pids = np.array(pids, dtype=np.int64)[keep]; w = proj[keep] / 48.0
                    r = np.array([self.rating.get((p, s - 1), (UNRATED_OFF, UNRATED_DEF)) for p in pids]).reshape(-1, 2)
                    if kind in kinds:
                        out[(gm.Index, side, kind)] = dict(pids=pids, w=w, s_off=float(w @ r[:, 0]), s_def=float(w @ r[:, 1]),
                                                           n_unrated=int(sum((p, s - 1) not in self.rating for p in pids)),
                                                           snap=sn, base_total=tot)
                last[t] = pretip_status
        self.last_pretip_status = last
        return out
