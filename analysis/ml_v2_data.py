"""NBA moneyline v2, step 1: one row per game 2011-12..2025-26 with results, market prices and schedule features.
Pre-registration: research/MONEYLINE_V2_PREREG_2026-11-04.md.   python3 analysis/ml_v2_data.py  -> analysis/ml_v2_games.csv.gz
Seasons are labelled by the year they END (2012 = 2011-12). Regular season only (playoffs dropped: DK history has none)."""
import os, numpy as np, pandas as pd
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(W, *p)

SBR_CODE = {"Bucks": "mil", "Bulls": "chi", "Cavaliers": "cle", "Celtics": "bos", "Clippers": "lac", "Golden State": "gs", "Warriors": "gs",
            "Grizzlies": "mem", "Hawks": "atl", "Heat": "mia", "Hornets": "cha", "Jazz": "utah", "Kings": "sac", "Knicks": "ny", "Lakers": "lal",
            "Magic": "orl", "Mavericks": "dal", "Nets": "bkn", "NewJersey": "bkn", "Nuggets": "den", "Pacers": "ind", "Pelicans": "no",
            "Pistons": "det", "Raptors": "tor", "Rockets": "hou", "Seventysixers": "phi", "Spurs": "sa", "Suns": "phx", "Thunder": "okc",
            "Timberwolves": "min", "Trailblazers": "por", "Wizards": "wsh"}
# arena coordinates (lat, lon, elevation m) for travel and altitude
CITY = {"atl": (33.76, -84.40, 300), "bos": (42.37, -71.06, 5), "bkn": (40.68, -73.98, 10), "cha": (35.23, -80.84, 230), "chi": (41.88, -87.67, 180),
        "cle": (41.50, -81.69, 200), "dal": (32.79, -96.81, 140), "den": (39.75, -105.01, 1600), "det": (42.34, -83.06, 190), "gs": (37.77, -122.39, 5),
        "hou": (29.75, -95.36, 15), "ind": (39.76, -86.16, 220), "lac": (34.04, -118.27, 90), "lal": (34.04, -118.27, 90), "mem": (35.14, -90.05, 80),
        "mia": (25.78, -80.19, 2), "mil": (43.04, -87.92, 190), "min": (44.98, -93.28, 260), "no": (29.95, -90.08, 1), "ny": (40.75, -73.99, 10),
        "okc": (35.46, -97.52, 360), "orl": (28.54, -81.38, 30), "phi": (39.90, -75.17, 10), "phx": (33.45, -112.07, 330), "por": (45.53, -122.67, 15),
        "sac": (38.58, -121.50, 10), "sa": (29.43, -98.44, 200), "tor": (43.64, -79.38, 80), "utah": (40.77, -111.90, 1300), "wsh": (38.90, -77.02, 10)}

def km(a, b):
    (la1, lo1, _), (la2, lo2, _) = CITY[a], CITY[b]
    la1, lo1, la2, lo2 = map(np.radians, (la1, lo1, la2, lo2))
    return 6371 * 2 * np.arcsin(np.sqrt(np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2))

# ---- results
S = pd.read_csv(J("data", "external", "sbr", "sbr_nba_2011_2021_clean.csv.gz"))
S = S[S.season <= 2020]                                   # 2021-22 onward comes from training_games (same games, DK prices)
S = pd.DataFrame(dict(season=S.season + 1, date=S.date, home=S.home_team.map(SBR_CODE), away=S.away_team.map(SBR_CODE),
                      home_pts=S.home_final, away_pts=S.away_final, sbr_ml_h=S.home_close_ml, sbr_ml_a=S.away_close_ml))
T = pd.read_csv(J("data", "training_games.csv"))[["season", "date", "home", "away", "home_pts", "away_pts"]]
G = pd.concat([S, T], ignore_index=True).dropna(subset=["home", "away", "home_pts"])
G["date"] = pd.to_datetime(G.date); G = G.sort_values(["date", "home"]).drop_duplicates(["date", "home", "away"]).reset_index(drop=True)

# regular season only: a game is a playoff game when either team already has its full schedule
NREG = {2012: 66, 2020: 75, 2021: 72}
long = pd.concat([G[["season", "date", "home"]].rename(columns={"home": "team"}).assign(i=G.index),
                  G[["season", "date", "away"]].rename(columns={"away": "team"}).assign(i=G.index)]).sort_values(["date", "i"])
long["n"] = long.groupby(["season", "team"]).cumcount() + 1
cap = long.season.map(lambda s: NREG.get(s, 82))
G["playoff"] = False; G.loc[long[long.n > cap].i.unique(), "playoff"] = True
# 2020 bubble: seeding games after the hiatus are excluded (COVID season is excluded from grading anyway)
G = G[~G.playoff].drop(columns="playoff").reset_index(drop=True)

# ---- schedule features (known in advance)
long = pd.concat([pd.DataFrame(dict(i=G.index, date=G.date, team=G.home, site=G.home, side="h")),
                  pd.DataFrame(dict(i=G.index, date=G.date, team=G.away, site=G.home, side="a"))]).sort_values(["team", "date"])
long["prev_date"] = long.groupby("team").date.shift(); long["prev_site"] = long.groupby("team").site.shift()
long["rest"] = (long.date - long.prev_date).dt.days.clip(upper=4).fillna(4)
long["travel"] = [km(a, b) / 1000 if isinstance(a, str) else 0.0 for a, b in zip(long.prev_site, long.site)]
long.loc[long.rest >= 4, "travel"] = 0.0                  # long breaks: travel does not matter
for side in ("h", "a"):
    L = long[long.side == side].set_index("i")
    G[f"rest_{side}"] = L.rest; G[f"b2b_{side}"] = (L.rest == 1).astype(int); G[f"travel_{side}"] = L.travel
G["alt_home"] = G.home.isin(["den", "utah"]).astype(int)
G["hw"] = (G.home_pts > G.away_pts).astype(int); G["margin"] = G.home_pts - G.away_pts

# ---- market: DraftKings first / last-before-tip and Pinnacle first moneyline (Odds API), 2021-22..2025-26
O = pd.read_csv(J("data", "odds_history", "nba_snapshots.csv.gz"), usecols=["home", "away", "tip", "t", "book", "ml_h", "ml_a", "date"])
O = O.dropna(subset=["ml_h", "ml_a"]); O["t"] = pd.to_datetime(O.t, utc=True); O["tip"] = pd.to_datetime(O.tip, utc=True)
O = O[O.t <= O.tip].sort_values("t")
def pick(book, how):
    d = O[O.book == book].groupby(["date", "home", "away"]); d = d.head(1) if how == "first" else d.tail(1)
    return d[["date", "home", "away", "ml_h", "ml_a", "t"]]
M = pick("draftkings", "first").rename(columns={"ml_h": "dk_o_h", "ml_a": "dk_o_a", "t": "dk_o_t"})
M = M.merge(pick("draftkings", "last").rename(columns={"ml_h": "dk_c_h", "ml_a": "dk_c_a", "t": "dk_c_t"}), on=["date", "home", "away"], how="left")
M = M.merge(pick("pinnacle", "first").rename(columns={"ml_h": "pn_o_h", "ml_a": "pn_o_a", "t": "pn_o_t"}), on=["date", "home", "away"], how="left")
M["date"] = pd.to_datetime(M.date)
G = G.merge(M, on=["date", "home", "away"], how="left")

G["split"] = np.select([G.season.between(2012, 2019), G.season.isin([2022, 2023]), G.season.between(2024, 2026)],
                       ["build", "choose", "lockbox"], "none")          # 2020, 2021 (COVID) = none: used for ratings only
G.to_csv(J("analysis", "ml_v2_games.csv.gz"), index=False)
print(G.groupby("season").agg(games=("hw", "size"), sbr_ml=("sbr_ml_h", "count"), dk_open=("dk_o_h", "count"), dk_close=("dk_c_h", "count"),
                                pin=("pn_o_h", "count"), home_win=("hw", "mean")).to_string())
