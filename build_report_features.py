"""
Injury features from OFFICIAL pre-game injury reports (no lookahead).

For each game and team, two snapshots:
  open   = report from 8 PM ET the day before (fallback: 11 AM game day if the team had not submitted)
  pretip = latest game-day report posted at least 60 minutes before tip
           (fallback: latest earlier report where the team had submitted)
Each listed player contributes  p_miss(status) * (expected minutes / 48) * prior-season EPM.
p_miss(status) = share of players with that pre-tip status who did not play, measured on the
training seasons only. Expected minutes = his minutes per game this season before the game
(any team), else last season's, else 0. EPM = last season's (unrated players get a small negative).
"""
import re, sys, unicodedata
import numpy as np, pandas as pd

TRAIN_SEASONS = [2022, 2023, 2024, 2025]
UNRATED_OFF, UNRATED_DEF = -1.0, -0.5
FULL2ABBR = {"Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN", "Charlotte Hornets": "CHA",
             "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN",
             "Detroit Pistons": "DET", "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
             "LA Clippers": "LAC", "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
             "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP",
             "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
             "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
             "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS"}
ABBR2GAMES = {"ATL": "atl", "BKN": "bkn", "BOS": "bos", "CHA": "cha", "CHI": "chi", "CLE": "cle", "DAL": "dal", "DEN": "den",
              "DET": "det", "GSW": "gs", "HOU": "hou", "IND": "ind", "LAC": "lac", "LAL": "lal", "MEM": "mem", "MIA": "mia",
              "MIL": "mil", "MIN": "min", "NOP": "no", "NYK": "ny", "OKC": "okc", "ORL": "orl", "PHI": "phi", "PHX": "phx",
              "POR": "por", "SAC": "sac", "SAS": "sa", "TOR": "tor", "UTA": "utah", "WAS": "wsh"}
SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")


def key(name):
    """normalize 'Last, First' or 'First Last' to a comparable key"""
    if not isinstance(name, str): return None
    if "," in name:
        last, first = name.split(",", 1); name = f"{first} {last}"
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = SUFFIX.sub("", re.sub(r"[^a-z ]", " ", s))
    return " ".join(s.split())


def season_of(d):
    return d.year + 1 if d.month >= 8 else d.year


def main(games_csv, box_csv, epm_csv, reports_csv, out_csv, p_miss_csv=None):
    games = pd.read_csv(games_csv, parse_dates=["date"]); games = games[games.season >= 2022].copy()
    box = pd.read_csv(box_csv, usecols=["date", "playerid", "player", "team", "MIN", "season"])
    box = box[box.season >= 2021].copy(); box["date"] = pd.to_datetime(box.date); box["k"] = box.player.map(key)
    epm = pd.read_csv(epm_csv, usecols=["nba_player_id", "season", "game_dt", "epm_off", "epm_def"])
    epm = epm.sort_values("game_dt").groupby(["nba_player_id", "season"]).tail(1)
    rating = {(r.nba_player_id, r.season): (r.epm_off, r.epm_def) for r in epm.itertuples()}

    rep = pd.read_csv(reports_csv)
    rep["gd"] = pd.to_datetime(rep.game_date, format="%m/%d/%Y")
    rep["abbr"] = rep.team.map(FULL2ABBR)
    rep["snap_day"] = pd.to_datetime(rep.snapshot.str[:10]); rep["slot"] = rep.snapshot.str[11:]
    rep["as_of"] = pd.to_datetime(rep.as_of)
    slot_time = {"11AM": 11.5, "01PM": 13.5, "03PM": 15.5, "05PM": 17.5, "06PM": 18.5, "07PM": 19.5, "08PM": 20.5, "09PM": 21.5}
    rep["as_of"] = rep.as_of.fillna(rep.snap_day + pd.to_timedelta(rep.slot.map(slot_time), unit="h"))
    rep["k"] = rep.player.map(key)
    tip = rep.dropna(subset=["game_time_et"]).groupby(["gd", "abbr"]).game_time_et.agg(lambda s: s.mode()[0])

    # ---- player id lookup by name key (prefer same team-season)
    ids = box.groupby(["k", "season", "team"]).playerid.agg(lambda s: s.mode()[0])
    ids_any = box.groupby("k").playerid.agg(lambda s: s.mode()[0])

    # ---- expected minutes as of each date (season to date, any team), and last season's mpg
    box = box.sort_values("date")
    played = box[box.MIN > 0]
    last_mpg = played.groupby(["playerid", "season"]).MIN.mean()

    hist = {}
    for (pid, ss), g in played.groupby(["playerid", "season"]):
        hist[(pid, ss)] = (g.date.values, np.cumsum(g.MIN.values))

    def exp_minutes(pid, d, s):
        h = hist.get((pid, s))
        if h is not None:
            n = np.searchsorted(h[0], np.datetime64(d), side="left")
            if n: return h[1][n - 1] / n
        return last_mpg.get((pid, s - 1), 0.0)

    # ---- choose snapshots per (game day, team)
    snaps = rep[["gd", "abbr", "snapshot", "snap_day", "slot", "as_of"]].drop_duplicates()
    nys = set(map(tuple, rep[rep.status == "NOT YET SUBMITTED"][["gd", "abbr", "snapshot"]].values))
    by_day = {d: grp for d, grp in rep.groupby("gd")}

    snaps_by_day = {d: g for d, g in snaps.groupby("gd")}

    def pick(d, t, kind):
        g = snaps_by_day.get(d, snaps.iloc[:0])
        ok = lambda s: (d, t, s) not in nys
        if kind == "open":
            cand = [f"{(d - pd.Timedelta(days=1)).date()}_08PM", f"{(d - pd.Timedelta(days=1)).date()}_09PM",
                    f"{d.date()}_11AM", f"{d.date()}_01PM"]
            for s in cand:
                if s in set(g.snapshot) and ok(s): return s
            return None
        tt = tip.get((d, t))
        if tt is None: return None
        hh, mm = map(int, tt.split(":")); hh = hh + 12 if hh < 11 else hh        # times are PM except 11:xx/12:xx
        tip_dt = d + pd.Timedelta(hours=hh, minutes=mm)
        g2 = g[(g.as_of <= tip_dt - pd.Timedelta(minutes=60))].sort_values("as_of")
        for s in reversed(g2.snapshot.tolist()):
            if ok(s): return s
        return None

    rows = []
    for gm in games.itertuples():
        d = gm.date; s = gm.season
        for side in ("home", "away"):
            tg = getattr(gm, side)
            t = next(k for k, v in ABBR2GAMES.items() if v == tg)
            rec = {"gi": gm.Index, "side": side}
            for kind in ("open", "pretip"):
                sn = pick(d, t, kind)
                rec[f"snap_{kind}"] = sn
                lst = by_day.get(d)
                lst = lst[(lst.abbr == t) & (lst.snapshot == sn) & lst.player.notna()] if (lst is not None and sn) else pd.DataFrame()
                rec[f"players_{kind}"] = [(r.k, r.status) for r in lst.itertuples()] if len(lst) else []
            rec["season"], rec["date"], rec["team"] = s, d, t
            rows.append(rec)
    R = pd.DataFrame(rows)
    # opening-line fallback: if the team had not filed in time, use its report from its previous game
    R = R.sort_values(["team", "date"])
    prev = None
    for i in R.index:
        if prev is not None and R.at[i, "team"] == R.at[prev, "team"] and pd.isna(R.at[i, "snap_open"]):
            R.at[i, "players_open"] = R.at[prev, "players_pretip"]; R.at[i, "snap_open"] = "previous game"
        prev = i

    # ---- p_miss by status, measured on training seasons with the pretip snapshot (or loaded, for live use)
    if p_miss_csv:
        p_miss = pd.read_csv(p_miss_csv, index_col=0).iloc[:, 0].dropna().to_dict()
        p_miss = {k: v for k, v in p_miss.items() if isinstance(k, str)}
    else:
        p_miss = None
    playset = played.groupby(["date", "team"]).k.apply(set).to_dict()
    cnt = {}
    for r in (R[R.season.isin(TRAIN_SEASONS)].itertuples() if p_miss is None else []):
        ps = playset.get((r.date, r.team), set())
        for k_, st in r.players_pretip:
            a = cnt.setdefault(st, [0, 0]); a[0] += 1; a[1] += (k_ not in ps)
    if p_miss is None:
        p_miss = {st: v[1] / v[0] for st, v in cnt.items()}
        print("p_miss (training seasons):", {k: (round(v, 3), cnt[k][0]) for k, v in p_miss.items()})

    # ---- features
    feat = {}
    for r in R.itertuples():
        for kind in ("open", "pretip"):
            mo = md = 0.0; n_out = 0
            for k_, st in getattr(r, f"players_{kind}"):
                pm = p_miss.get(st, 0.0)
                if pm <= 0: continue
                pid = ids.get((k_, r.season, r.team), ids_any.get(k_))
                if pid is None: continue
                m = exp_minutes(pid, r.date, r.season)
                if m <= 0: continue
                eo, ed = rating.get((pid, r.season - 1), (UNRATED_OFF, UNRATED_DEF))
                w = pm * m / 48
                mo += w * eo; md += w * ed; n_out += st == "Out"
            feat[(r.gi, r.side, kind)] = (mo, md, n_out)
    for kind, suf in (("pretip", ""), ("open", "_open")):
        for side in ("home", "away"):
            games[f"{side}_miss_off{suf}"] = [feat[(i, side, kind)][0] for i in games.index]
            games[f"{side}_miss_def{suf}"] = [feat[(i, side, kind)][1] for i in games.index]
            games[f"{side}_n_out{suf}"] = [feat[(i, side, kind)][2] for i in games.index]
    snapinfo = R.pivot_table(index="gi", columns="side", values=["snap_open", "snap_pretip"], aggfunc="first")
    games["snap_open_home"] = snapinfo[("snap_open", "home")].reindex(games.index).values
    games["snap_pretip_home"] = snapinfo[("snap_pretip", "home")].reindex(games.index).values
    games.to_csv(out_csv, index=False)
    print("games", len(games), "missing pretip snapshot", games.snap_pretip_home.isna().sum(),
          "missing open snapshot", games.snap_open_home.isna().sum())
    print(games.groupby("season")[["home_n_out", "home_miss_off", "home_miss_def", "home_miss_off_open"]].mean().round(3))
    if not p_miss_csv: pd.Series(p_miss).to_csv(out_csv.replace(".csv", "_p_miss.csv"))


if __name__ == "__main__":
    main(*sys.argv[1:7])
