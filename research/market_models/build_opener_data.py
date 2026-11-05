"""Market models step 2a: build one row per game with each book's first-seen total, close, and
features known BEFORE the line was first seen (earlier-date games only).
Output: research/market_models/opener_data.csv.gz
Run from the repo root: python research/market_models/build_opener_data.py
"""
import glob, sys, os
import numpy as np, pandas as pd
NAME = {"Atlanta Hawks": "atl", "Brooklyn Nets": "bkn", "Boston Celtics": "bos", "Charlotte Hornets": "cha", "Chicago Bulls": "chi",
        "Cleveland Cavaliers": "cle", "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det",
        "Golden State Warriors": "gs", "Houston Rockets": "hou", "Indiana Pacers": "ind", "Los Angeles Clippers": "lac", "LA Clippers": "lac",
        "Los Angeles Lakers": "lal", "Memphis Grizzlies": "mem", "Miami Heat": "mia", "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min",
        "New Orleans Pelicans": "no", "New York Knicks": "ny", "Oklahoma City Thunder": "okc", "Orlando Magic": "orl",
        "Philadelphia 76ers": "phi", "Phoenix Suns": "phx", "Portland Trail Blazers": "por", "San Antonio Spurs": "sa",
        "Sacramento Kings": "sac", "Toronto Raptors": "tor", "Utah Jazz": "utah", "Washington Wizards": "wsh"}  # full team name -> code (copied from analysis/odds_openers.py)

BOOKS = ["draftkings", "pinnacle", "fanduel"]
OUT = "research/market_models/opener_data.csv.gz"

# ---------- 1. odds: first-seen and close per game and book ----------
fs = sorted(glob.glob("data/odds_history/nba/*.csv.gz"))
d = pd.concat([pd.read_csv(f, usecols=["snapshot_utc", "event_id", "commence_et", "home", "away", "book",
                                      "market", "outcome", "price", "point"]) for f in fs])
d = d[(d.market == "totals") & d.book.isin(BOOKS)]
d["snap"] = pd.to_datetime(d.snapshot_utc).dt.tz_convert("America/New_York").dt.tz_localize(None)
d["tip"] = pd.to_datetime(d.commence_et)
d["lead_h"] = (d.tip - d.snap).dt.total_seconds() / 3600
d = d[d.lead_h > 0]
ov = d[d.outcome == "Over"][["event_id", "book", "snap", "lead_h", "point", "price"]].rename(columns={"price": "over_px"})
un = d[d.outcome == "Under"][["event_id", "book", "snap", "price"]].rename(columns={"price": "under_px"})
x = ov.merge(un, on=["event_id", "book", "snap"], how="left").sort_values("snap")
# the API sometimes gives one game two event IDs (an early one, then a replacement): merge them by date + teams,
# so first-seen is the earliest line under either ID and close is the latest
ev = d.drop_duplicates("event_id").set_index("event_id")
key = ev.tip.dt.strftime("%Y-%m-%d") + "|" + ev.home + "|" + ev.away
main_id = ev.assign(k=key).sort_values("tip").groupby("k").apply(lambda z: z.index[-1])
x["event_id"] = x.event_id.map(key).map(main_id)
x = x.sort_values("snap")
g = x.groupby(["event_id", "book"])
first = g.first()[["lead_h", "point", "over_px", "under_px"]].add_prefix("open_")
last = g.last()[["lead_h", "point"]].rename(columns={"lead_h": "close_lead_h", "point": "close_point"})
fl = first.join(last).reset_index()
wide = fl.pivot(index="event_id", columns="book")
wide.columns = [f"{b[:2]}_{c}" for c, b in wide.columns]  # dr_, pi_, fa_
wide = wide.rename(columns=lambda c: c.replace("dr_", "dk_").replace("pi_", "pin_").replace("fa_", "fd_"))
meta = ev.loc[main_id.values, ["tip", "home", "away"]]
games = meta.join(wide).reset_index()
games["home"] = games.home.map(NAME); games["away"] = games.away.map(NAME)
games["date"] = games.tip.dt.strftime("%Y-%m-%d")
games = games.dropna(subset=["home", "away"])

# ---------- 2. team game logs from box scores (pace, efficiency) ----------
ps = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("data/player_stats/season_*.csv.gz"))])
ps = ps.drop_duplicates(["game_id", "player_id"])  # some games have every player row twice
tg = ps.groupby(["game_id", "date", "season", "team", "home"])[["pts", "fga", "oreb", "tov", "fta"]].sum().reset_index()
tg["poss"] = tg.fga - tg.oreb + tg.tov + 0.44 * tg.fta
opp = tg[["game_id", "team", "pts", "poss"]].rename(columns={"team": "opp", "pts": "opp_pts", "poss": "opp_poss"})
tg = tg.merge(opp, on="game_id"); tg = tg[tg.team != tg.opp]
tg["pace"] = (tg.poss + tg.opp_poss) / 2
tg["ortg"] = 100 * tg.pts / tg.pace; tg["drtg"] = 100 * tg.opp_pts / tg.pace
tg["tot"] = tg.pts + tg.opp_pts
# official scores from training_games; box-score games that don't match (partial or broken box) are left out of the averages
tr0 = pd.read_csv("data/training_games.csv")
sc = pd.concat([tr0[["date", "home", "home_pts"]].rename(columns={"home": "team", "home_pts": "off_pts"}),
                tr0[["date", "away", "away_pts"]].rename(columns={"away": "team", "away_pts": "off_pts"})])
tg = tg.merge(sc, on=["date", "team"], how="left")
bad = (tg.off_pts.notna() & (tg.off_pts != tg.pts)) | (tg.tot < 160)
print("box-score team games dropped from averages:", int(bad.sum()))
tg.loc[bad, ["pace", "ortg", "drtg", "pts", "opp_pts", "tot"]] = np.nan
tg = tg.sort_values(["team", "date"])

HL = 12  # half-life in games
def pre_ewm(df, cols, hl):
    # value entering each game = EWMA of strictly earlier games
    return df.groupby("team")[cols].transform(lambda s: s.ewm(halflife=hl, min_periods=1, ignore_na=True).mean().shift(1))
for c, v in zip(["pace", "ortg", "drtg", "pts", "opp_pts"], ["pace", "ortg", "drtg", "pf", "pa"]):
    tg[f"e_{v}"] = pre_ewm(tg, [c], HL)[c]
tg["prev_date"] = tg.groupby("team").date.shift(1)
tg["rest"] = (pd.to_datetime(tg.date) - pd.to_datetime(tg.prev_date)).dt.days.clip(upper=5)
tg["gp_season"] = tg.groupby(["team", "season"]).cumcount()
team_feat = tg[["date", "team", "e_pace", "e_ortg", "e_drtg", "e_pf", "e_pa", "rest", "gp_season"]]

# league scoring level from earlier dates only
lg = (tr0.home_pts + tr0.away_pts).groupby(tr0.date).mean().sort_index()
lg_pre = lg.ewm(halflife=60).mean().shift(1)  # ~60 game-days

# ---------- 3. join results and team features ----------
res = tr0[["date", "home", "away", "home_pts", "away_pts"]]
G = games.merge(res, on=["date", "home", "away"], how="inner")
G["final_total"] = G.home_pts + G.away_pts
for side in ["home", "away"]:
    f = team_feat.rename(columns={c: f"{side[0]}_{c}" for c in team_feat.columns if c not in ("date", "team")})
    G = G.merge(f.rename(columns={"team": side}), on=["date", side], how="left")
G["league_lvl"] = G.date.map(lg_pre)

# ---------- 4. market memory and previous opener errors (team level, earlier dates) ----------
G = G.sort_values("tip").reset_index(drop=True)
long = pd.concat([G[["date", "tip", "home", "dk_close_point", "dk_open_point", "final_total"]].rename(columns={"home": "team"}),
                  G[["date", "tip", "away", "dk_close_point", "dk_open_point", "final_total"]].rename(columns={"away": "team"})])
long = long.sort_values(["team", "tip"])
long["dk_err"] = long.final_total - long.dk_open_point   # how wrong DK's first-seen line was
long["dk_mv"] = long.dk_close_point - long.dk_open_point  # how far it moved
for c, hl in [("dk_close_point", 5), ("dk_err", 10), ("dk_mv", 10)]:
    long[f"m_{c}"] = long.groupby("team")[c].transform(lambda s: s.ewm(halflife=hl, ignore_na=True).mean().shift(1))
mem = long[["date", "team", "m_dk_close_point", "m_dk_err", "m_dk_mv"]].drop_duplicates(["date", "team"])
for side in ["home", "away"]:
    G = G.merge(mem.rename(columns={"team": side, "m_dk_close_point": f"{side[0]}_mkt",
                                    "m_dk_err": f"{side[0]}_operr", "m_dk_mv": f"{side[0]}_opmv"}),
                on=["date", side], how="left")

# ---------- 5. injuries known at open ----------
tr = pd.read_csv("data/training_games.csv")
inj = [c for c in tr.columns if c.endswith("_open") and c not in ("open_spread", "open_total")]
G = G.merge(tr[["date", "home", "away"] + inj], on=["date", "home", "away"], how="left")

# ---------- 6. derived ----------
G["season"] = G.tip.apply(lambda t: t.year + 1 if t.month >= 8 else t.year)
G["exp_pace"] = (G.h_e_pace + G.a_e_pace) / 2
G["fund_total"] = G.exp_pace * (G.h_e_ortg + G.a_e_drtg + G.a_e_ortg + G.h_e_drtg) / 200
G["mkt_total"] = (G.h_mkt + G.a_mkt) / 2
G["b2b_h"] = (G.h_rest == 1).astype(int); G["b2b_a"] = (G.a_rest == 1).astype(int)
G["gp_min"] = G[["h_gp_season", "a_gp_season"]].min(axis=1)
G["month"] = G.tip.dt.month
G = G[G.season.between(2022, 2026)]
G.to_csv(OUT, index=False, compression="gzip")
print("rows", len(G), "by season", G.season.value_counts().sort_index().to_dict())
print("non-missing first-seen:", {b: int(G[f"{b}_open_point"].notna().sum()) for b in ["dk", "pin", "fd"]})
print("missing injury-at-open:", int(G[inj[0]].isna().sum()), "missing fundamentals:", int(G.fund_total.isna().sum()),
      "missing market memory:", int(G.mkt_total.isna().sum()))
