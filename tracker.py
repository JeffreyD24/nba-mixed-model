"""
NBA live tracker (2026-27). One run = one morning update.

  python tracker.py WORKDIR [YYYY-MM-DD]

WORKDIR holds the tracker folder (this script, the model code, training data, state/).
Each run:
  1. downloads the latest 2026-27 results/box scores/schedule (Kaggle: eoinamoore dataset)
  2. downloads and parses any official NBA injury reports not yet in state/
  3. builds injury features (day-before report for today's games; pre-tip reports for past games)
  4. refits the official-reports mixed model on 2021-22..2025-26 and walks forward through 2026-27
  5. LOCKS predictions for today's games (timestamped, before tip). Locked picks are never changed.
  6. pulls opening/closing lines from ESPN when reachable, grades finished games
  7. writes state/picks_log.csv and NBA_Live_Tracker.xlsx (with notes and advice)
"""
import os, sys, json, subprocess, zipfile, warnings, datetime as dt
from concurrent.futures import ThreadPoolExecutor
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

W = os.path.abspath(sys.argv[1])
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
def now_et(): return pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None))
TODAY = pd.Timestamp(sys.argv[2]) if len(sys.argv) > 2 else now_et().normalize()
sys.path.insert(0, W)
from nba_mixed_model import run                                  # noqa: E402
from parse_injury_reports import parse as parse_pdf               # noqa: E402
import build_report_features as brf                               # noqa: E402

STATE = os.path.join(W, "state"); os.makedirs(STATE, exist_ok=True)
TMP = os.path.join(W, "_tmp"); os.makedirs(TMP, exist_ok=True)
SEASON = 2027; SEASON_START = pd.Timestamp("2026-10-01")
TRAIN = [2022, 2023, 2024, 2025, 2026]
RULE = dict(line="open", market="total", edge=4.0)                 # the pre-chosen rule
NAME2ABBR = {"Hawks": "atl", "Celtics": "bos", "Nets": "bkn", "Hornets": "cha", "Bulls": "chi", "Cavaliers": "cle",
             "Mavericks": "dal", "Nuggets": "den", "Pistons": "det", "Warriors": "gs", "Rockets": "hou", "Pacers": "ind",
             "Clippers": "lac", "Lakers": "lal", "Grizzlies": "mem", "Heat": "mia", "Bucks": "mil", "Timberwolves": "min",
             "Pelicans": "no", "Knicks": "ny", "Thunder": "okc", "Magic": "orl", "76ers": "phi", "Suns": "phx",
             "Trail Blazers": "por", "Kings": "sac", "Spurs": "sa", "Raptors": "tor", "Jazz": "utah", "Wizards": "wsh"}
GAMES2SZYM = {v: k for k, v in brf.ABBR2GAMES.items()}
log = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); log.append(s)


# ------------------------------------------------------------------ 1. results, box scores, schedule
def load_season_data():
    z = os.path.join(TMP, "eoin.zip")
    r = subprocess.run(["curl", "-sL", "-m", "1200", "-o", z, "-w", "%{http_code}",
                        "https://www.kaggle.com/api/v1/datasets/download/eoinamoore/historical-nba-data-and-player-box-scores"],
                       capture_output=True, text=True)
    if r.stdout != "200": raise RuntimeError(f"box-score download failed (HTTP {r.stdout})")
    with zipfile.ZipFile(z) as zf:
        for f in ("Games.csv", "LeagueSchedule26_27.csv", "PlayerStatistics.csv"):
            zf.extract(f, TMP)
    os.remove(z)
    g = pd.read_csv(os.path.join(TMP, "Games.csv"), low_memory=False)
    g["dt"] = pd.to_datetime(g.gameDateTimeEst.astype(str).str[:19], errors="coerce")       # clock time is ET
    g = g[(g.dt >= SEASON_START) & (g.gameType == "Regular Season")].copy()
    sch = pd.read_csv(os.path.join(TMP, "LeagueSchedule26_27.csv"))
    sch["dt"] = pd.to_datetime(sch.gameDateTimeEst.astype(str).str[:19], errors="coerce")
    sch = sch[sch.gameId.astype(str).str.startswith("226")]                                   # regular season
    games = pd.DataFrame({"game_id": sch.gameId.astype(int), "date": sch.dt.dt.normalize(), "tip_et": sch.dt,
                          "home": sch.homeTeamName.map(NAME2ABBR), "away": sch.awayTeamName.map(NAME2ABBR)})
    res = g.set_index(g.gameId.astype(int))[["homeScore", "awayScore"]]
    games["home_pts"] = games.game_id.map(res.homeScore); games["away_pts"] = games.game_id.map(res.awayScore)
    games["season"] = SEASON
    games = games.dropna(subset=["home", "away"]).sort_values(["date", "tip_et"]).reset_index(drop=True)
    p = pd.read_csv(os.path.join(TMP, "PlayerStatistics.csv"), low_memory=False,
                    usecols=["firstName", "lastName", "personId", "gameId", "gameDateTimeEst", "playerteamName", "numMinutes", "gameType"])
    p["dt"] = pd.to_datetime(p.gameDateTimeEst.astype(str).str[:19], errors="coerce")
    p = p[(p.dt >= SEASON_START) & (p.gameType == "Regular Season")]
    box = pd.DataFrame({"date": p.dt.dt.normalize(), "playerid": p.personId, "player": p.firstName.fillna("") + " " + p.lastName.fillna(""),
                        "team": p.playerteamName.map(NAME2ABBR).map(GAMES2SZYM), "MIN": pd.to_numeric(p.numMinutes, errors="coerce").fillna(0),
                        "season": SEASON})
    for f in ("Games.csv", "LeagueSchedule26_27.csv", "PlayerStatistics.csv"): os.remove(os.path.join(TMP, f))
    played = games.dropna(subset=["home_pts"])
    say(f"Schedule: {len(games)} regular-season games; {len(played)} finished, results through {played.date.max().date() if len(played) else 'none'}.")
    return games, box


# ------------------------------------------------------------------ 2. injury reports
BASE = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_"
SLOTS = ["11AM", "01PM", "03PM", "05PM", "06PM", "07PM", "08PM", "09PM"]


def fetch_report(day, slot):
    dest = os.path.join(TMP, f"{day}_{slot}.pdf")
    hh, ap = slot[:2], slot[2:]
    for v in (f"{day}_{slot}", f"{day}_{hh}_30{ap}", f"{day}_{hh}_00{ap}"):
        r = subprocess.run(["curl", "-s", "-m", "40", "--retry", "2", "-o", dest, "-w", "%{http_code}", BASE + v + ".pdf"],
                           capture_output=True, text=True)
        if r.stdout == "200" and os.path.getsize(dest) > 1000: return dest
    if os.path.exists(dest): os.remove(dest)
    return None


def update_reports(games):
    path = os.path.join(STATE, "injury_reports_2026_27.csv")
    have = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["snapshot"])
    have_snaps = set(have.snapshot.unique()) if len(have) else set()
    done_path = os.path.join(STATE, "report_snapshots_checked.json")
    checked = set(json.load(open(done_path))) if os.path.exists(done_path) else set()
    now = now_et()
    jobs = set()
    for d in sorted(games.date.unique()):
        d = pd.Timestamp(d)
        if d > TODAY: break
        jobs.add(((d - pd.Timedelta(days=1)).date().isoformat(), "08PM")); jobs.add(((d - pd.Timedelta(days=1)).date().isoformat(), "09PM"))
        for s in SLOTS:
            slot_dt = d + pd.Timedelta(hours=int(s[:2]) % 12 + (12 if s.endswith("PM") else 0), minutes=30)
            if slot_dt <= now: jobs.add((d.date().isoformat(), s))
    jobs = sorted(j for j in jobs if f"{j[0]}_{j[1]}" not in have_snaps and f"{j[0]}_{j[1]}" not in checked)
    with ThreadPoolExecutor(12) as ex:
        files = list(ex.map(lambda j: fetch_report(*j), jobs))
    rows = []
    for (day, slot), f in zip(jobs, files):
        key = f"{day}_{slot}"
        if f:
            rows += parse_pdf(f); os.remove(f)
        if pd.Timestamp(day) < TODAY - pd.Timedelta(days=1): checked.add(key)            # don't retry old misses forever
    new = pd.DataFrame(rows, columns=["snapshot", "as_of", "game_date", "game_time_et", "matchup", "team", "player", "status"])
    allr = pd.concat([have, new], ignore_index=True) if len(have) else new
    allr.to_csv(path, index=False); json.dump(sorted(checked), open(done_path, "w"))
    say(f"Injury reports: {len(jobs)} snapshots requested, {sum(f is not None for f in files)} new, {allr.snapshot.nunique()} on file.")
    return path


# ------------------------------------------------------------------ 3. features
def build_features(games, box, reports_path):
    gpath = os.path.join(TMP, "games_2027.csv"); bpath = os.path.join(TMP, "box.csv"); fpath = os.path.join(TMP, "games_2027_feat.csv")
    g2 = games[["date", "season", "home", "away", "home_pts", "away_pts"]].copy(); g2["date"] = g2.date.dt.strftime("%Y-%m-%d")
    g2.to_csv(gpath, index=False)
    prior = pd.read_csv(os.path.join(W, "data", "box_2025_26.csv"))
    b2 = box.copy(); b2["date"] = pd.to_datetime(b2.date).dt.strftime("%Y-%m-%d")
    pd.concat([prior, b2], ignore_index=True).to_csv(bpath, index=False)
    brf.main(gpath, bpath, os.path.join(W, "data", "player_epm_2025_26.csv"), reports_path, fpath, os.path.join(W, "data", "p_miss.csv"))
    f = pd.read_csv(fpath, parse_dates=["date"])
    for c in f.columns:
        if "miss_" in c or "n_out" in c or c.startswith("snap_"): games[c] = f[c].values
    return games


# ------------------------------------------------------------------ 4/5. model + locked picks
def predict(games):
    tr = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
    games = games[(games.date == TODAY) | games.home_pts.notna()].reset_index(drop=True)   # skip past games whose scores are not in yet
    cur = games.drop(columns=["game_id", "tip_et"]).copy()
    for c in ("spread", "total", "open_spread", "open_total"): cur[c] = np.nan
    df = pd.concat([tr, cur], ignore_index=True)
    summ, P_open = run(df, TRAIN, SEASON, today_suffix="_open")
    P_open = P_open.sort_values(["date", "home"]).reset_index(drop=True)
    g = games.sort_values(["date", "home"]).reset_index(drop=True)
    g["pred_margin"] = P_open.pred_margin.values; g["pred_total"] = P_open.pred_total.values
    return g, summ


def lock_picks(g, games_through):
    path = os.path.join(STATE, "picks_log.csv")
    logdf = pd.read_csv(path, parse_dates=["date", "tip_et", "locked_at_et"]) if os.path.exists(path) else pd.DataFrame()
    locked = set(logdf.game_id) if len(logdf) else set()
    now = now_et()
    new = g[~g.game_id.isin(locked) & (g.date <= TODAY)].copy()
    live_mask = (new.date == TODAY) & (new.tip_et > now)
    new["pick_type"] = np.where(live_mask, "live", "backfilled")
    new = new[(new.pick_type == "live") | new.home_pts.notna()]                  # never lock an unfinished past game
    new["locked_at_et"] = now; new["results_through"] = games_through
    keep = ["game_id", "date", "tip_et", "home", "away", "pick_type", "locked_at_et", "results_through",
            "pred_margin", "pred_total", "home_n_out_open", "away_n_out_open", "snap_open_home"]
    new = new[keep]
    logdf = pd.concat([logdf, new], ignore_index=True) if len(logdf) else new
    say(f"Locked {int((new.pick_type == 'live').sum())} live picks for {TODAY.date()} and {int((new.pick_type == 'backfilled').sum())} backfilled.")
    return logdf


# ------------------------------------------------------------------ 6. lines (ESPN) + grading
def espn_lines(dates):
    import espn
    return espn.lines(dates, when=("open", "close"))


def attach_lines_and_grade(logdf, games):
    res = games.set_index("game_id")[["home_pts", "away_pts"]]
    logdf["home_pts"] = logdf.game_id.map(res.home_pts); logdf["away_pts"] = logdf.game_id.map(res.away_pts)
    for c in ("open_spread", "open_total", "close_spread", "close_total"):
        if c not in logdf: logdf[c] = np.nan
    need = logdf[logdf.open_spread.isna() | (logdf.close_spread.isna() & logdf.home_pts.notna())]
    if len(need):
        try:
            L = espn_lines(sorted(need.date.dt.normalize().unique()))
            if len(L) and "open_spread" in L:
                m = logdf.merge(L, on=["date", "home", "away"], how="left", suffixes=("", "_new"))
                finished = logdf.home_pts.notna().values
                for c in ("open_spread", "open_total", "close_spread", "close_total"):
                    new = pd.Series(m[f"{c}_new"].values, index=logdf.index)
                    if c.startswith("close"): new = new.where(finished)        # a closing line only exists once the game is over
                    logdf[c] = logdf[c].fillna(new)
                say(f"Lines: pulled DraftKings lines from ESPN for {len(L)} games.")
            else:
                say("Lines: ESPN returned no odds.")
        except Exception as e:
            say(f"Lines: ESPN not reachable ({type(e).__name__}); picks are still locked and will be graded once lines are available.")
    m = logdf.home_pts - logdf.away_pts; t = logdf.home_pts + logdf.away_pts
    for line in ("open", "close"):
        sp, tt = logdf[f"{line}_spread"], logdf[f"{line}_total"]
        e = logdf.pred_margin + sp
        logdf[f"{line}_spread_edge"] = e.abs(); logdf[f"{line}_spread_bet"] = np.where(e.isna(), None, np.where(e > 0, "home", "away"))
        logdf[f"{line}_spread_result"] = np.select([m.isna() | e.isna(), np.sign(m + sp) * np.sign(e) > 0, np.sign(m + sp) * np.sign(e) < 0], [None, "W", "L"], "P")
        e = logdf.pred_total - tt
        logdf[f"{line}_total_edge"] = e.abs(); logdf[f"{line}_total_bet"] = np.where(e.isna(), None, np.where(e > 0, "over", "under"))
        logdf[f"{line}_total_result"] = np.select([t.isna() | e.isna(), np.sign(t - tt) * np.sign(e) > 0, np.sign(t - tt) * np.sign(e) < 0], [None, "W", "L"], "P")
    return logdf


# ------------------------------------------------------------------ for the intraday alert checks
def export_today_model(g, summ, box):
    """Save what alert.py needs to re-predict today's games from a newer injury report without refitting:
    each team's no-injury baseline points, the injury coefficients, and every player's value."""
    fe = summ["fixed_effects"]; c_off, c_def = fe["missing_offense"], fe["missing_opp_defense"]
    today = g[g.date == TODAY]
    games_out = []
    for r in today.itertuples():
        ph = (r.pred_total + r.pred_margin) / 2; pa = (r.pred_total - r.pred_margin) / 2
        games_out.append(dict(game_id=int(r.game_id), home=r.home, away=r.away, tip_et=str(r.tip_et),
                              base_home=ph - c_off * r.home_miss_off_open - c_def * r.away_miss_def_open,
                              base_away=pa - c_off * r.away_miss_off_open - c_def * r.home_miss_def_open,
                              morning_margin=r.pred_margin, morning_total=r.pred_total))
    # player values: (expected minutes / 48) x last season's EPM, keyed by normalized name
    prior = pd.read_csv(os.path.join(W, "data", "box_2025_26.csv"))
    epm = pd.read_csv(os.path.join(W, "data", "player_epm_2025_26.csv")).sort_values("game_dt").groupby("nba_player_id").tail(1)
    rating = {r.nba_player_id: (r.epm_off, r.epm_def) for r in epm.itertuples()}
    cur = box[box.MIN > 0]; old = prior[prior.MIN > 0]
    mpg = cur.groupby("playerid").MIN.mean().to_dict(); mpg_old = old.groupby("playerid").MIN.mean().to_dict()
    names = pd.concat([cur[["playerid", "player"]], old[["playerid", "player"]]]).drop_duplicates("playerid")
    players = {}
    for r in names.itertuples():
        m = mpg.get(r.playerid, mpg_old.get(r.playerid, 0.0))
        eo, ed = rating.get(r.playerid, (brf.UNRATED_OFF, brf.UNRATED_DEF))
        k = brf.key(r.player)
        if k and m > 0: players[k] = [round(m / 48 * eo, 4), round(m / 48 * ed, 4)]
    p_miss = pd.read_csv(os.path.join(W, "data", "p_miss.csv"), index_col=0).iloc[:, 0].dropna()
    json.dump(dict(date=str(TODAY.date()), c_off=c_off, c_def=c_def, p_miss={k: float(v) for k, v in p_miss.items() if isinstance(k, str)},
                   games=games_out, players=players), open(os.path.join(STATE, "today_model.json"), "w"))
    say(f"Saved today's model for intraday checks ({len(games_out)} games, {len(players)} players).")


def grade_alerts(games):
    path = os.path.join(STATE, "alerts.csv")
    if not os.path.exists(path): return
    a = pd.read_csv(path)
    res = games.set_index("game_id")[["home_pts", "away_pts"]]
    a["home_pts"] = a.game_id.map(res.home_pts); a["away_pts"] = a.game_id.map(res.away_pts)
    m = a.home_pts - a.away_pts; t = a.home_pts + a.away_pts
    out = []
    for r, mm, tt in zip(a.itertuples(), m, t):
        if np.isnan(mm): out.append(None); continue
        if r.market == "spread":
            v = (mm + r.line) * (1 if r.side == "home" else -1)
        else:
            v = (tt - r.line) * (1 if r.side == "over" else -1)
        out.append("W" if v > 0 else ("L" if v < 0 else "P"))
    a["result"] = out
    a.to_csv(path, index=False)
    g = a[a.result.isin(["W", "L"])]
    if len(g):
        w, l = int((g.result == "W").sum()), int((g.result == "L").sum())
        say(f"Alerts graded so far: {w}-{l} ({w / (w + l):.1%}), {w * 100 / 110 - l:+.1f} units at -110.")


# ------------------------------------------------------------------ main
def main():
    say(f"NBA tracker run for {TODAY.date()} (ET).")
    games, box = load_season_data()
    games = games[games.date <= TODAY].reset_index(drop=True)          # only past games and today's games are needed
    if not ((games.date >= TODAY).any()):
        say("No regular-season games remain. Nothing to predict.");
    rp = update_reports(games)
    games = build_features(games, box, rp)
    g, summ = predict(games)
    export_today_model(g, summ, box)
    played = games.dropna(subset=["home_pts"])
    logdf = lock_picks(g, str(played.date.max().date()) if len(played) else "none")
    logdf = attach_lines_and_grade(logdf, games)
    grade_alerts(games)
    logdf.sort_values(["date", "tip_et"]).to_csv(os.path.join(STATE, "picks_log.csv"), index=False)
    today = logdf[(logdf.date == TODAY) & (logdf.pick_type == "live")]
    json.dump({"today": [dict(home=r.home, away=r.away, tip=str(r.tip_et), pred_margin=round(r.pred_margin, 1),
                              pred_total=round(r.pred_total, 1)) for r in today.itertuples()], "log": log},
              open(os.path.join(STATE, "last_run.json"), "w"), indent=1)
    import build_tracker_workbook
    build_tracker_workbook.build(os.path.join(STATE, "picks_log.csv"), os.path.join(W, "NBA_Live_Tracker.xlsx"), RULE, log)
    say("Done.")


if __name__ == "__main__":
    main()
