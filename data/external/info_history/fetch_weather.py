"""
NFL game-time weather AS FORECAST at different lead times (not what actually happened), from Open-Meteo.

    python3 -I fetch_weather.py [first_season]        default 2022 (earlier archives of forecasts do not exist)

Why: the Nov 3 audit found NFL totals v2 used ACTUAL game-time wind/temp against a week-early opener. This table lets a backtest
use the forecast that existed 6-7 days before kickoff (when the opener posts) instead.

Sources (free, no key):
  previous-runs-api.open-meteo.com   forecast issued N days before the valid time: *_previous_day1 .. *_previous_day7
                                     (lead 0 = the plain variable, i.e. the latest run). Coverage by model starts around 2022-2024;
                                     older dates come back empty (NaN), which is recorded, not hidden.
  historical-forecast-api.open-meteo.com   stitched short-lead forecasts since 2022 (lead about 0-1 day). Saved as *_hf columns.

Per game: the 4 hours starting at kickoff (a game lasts about 3 h): mean temperature F, mean wind mph, max gust mph, total precip inch.
Skips dome / closed-roof games. Stadium coordinates are the current home stadium of each team (good to a few km),
plus neutral-site venues by name; anything unmatched is logged to weather/unmatched.csv.
Writes weather/nfl_forecasts.csv (resumable) and weather/samples/.
"""
import csv, json, os, sys, time, urllib.request, urllib.parse
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "weather"); os.makedirs(os.path.join(OUT, "samples"), exist_ok=True)
GAMES = os.path.join(HERE, "nfl", "games_2009_2026.csv.gz")

TEAM = {"ARI": (33.5276, -112.2626), "ATL": (33.7554, -84.4009), "BAL": (39.2780, -76.6227), "BUF": (42.7738, -78.7870),
        "CAR": (35.2258, -80.8528), "CHI": (41.8623, -87.6167), "CIN": (39.0954, -84.5160), "CLE": (41.5061, -81.6995),
        "DAL": (32.7473, -97.0945), "DEN": (39.7439, -105.0201), "DET": (42.3400, -83.0456), "GB": (44.5013, -88.0622),
        "HOU": (29.6847, -95.4107), "IND": (39.7601, -86.1639), "JAX": (30.3239, -81.6373), "KC": (39.0489, -94.4839),
        "LV": (36.0909, -115.1833), "OAK": (37.7516, -122.2005), "LAC": (33.9535, -118.3392), "LA": (33.9535, -118.3392),
        "MIA": (25.9580, -80.2389), "MIN": (44.9738, -93.2577), "NE": (42.0909, -71.2643), "NO": (29.9511, -90.0812),
        "NYG": (40.8135, -74.0745), "NYJ": (40.8135, -74.0745), "PHI": (39.9008, -75.1675), "PIT": (40.4468, -80.0158),
        "SF": (37.4030, -121.9700), "SEA": (47.5952, -122.3316), "TB": (27.9759, -82.5033), "TEN": (36.1665, -86.7713),
        "WAS": (38.9078, -76.8645)}
NEUTRAL = {"wembley": (51.5560, -0.2796), "tottenham": (51.6043, -0.0663), "twickenham": (51.4559, -0.3417),
           "azteca": (19.3029, -99.1505), "estadio banorte": (19.3029, -99.1505), "deutsche bank": (50.0686, 8.6455),
           "frankfurt": (50.0686, 8.6455), "allianz": (48.2188, 11.6247), "munich": (48.2188, 11.6247),
           "corinthians": (-23.5453, -46.4742), "bernab": (40.4530, -3.6883), "croke": (53.3609, -6.2510),
           "melbourne": (-37.8200, 144.9834), "mcg": (-37.8200, 144.9834), "maracana": (-22.9121, -43.2302),
           "stade de france": (48.9245, 2.3601)}
VARS = ["temperature_2m", "wind_speed_10m", "wind_gusts_10m", "precipitation"]
LEADS = list(range(1, 8))
COLS = ["game_id", "season", "week", "home_team", "roof", "kickoff_utc", "lat", "lon"] + \
       [f"{v}_d{k}" for v in ("temp", "wind", "gust", "precip") for k in [0] + LEADS] + \
       [f"{v}_hf" for v in ("temp", "wind", "gust", "precip")] + ["actual_temp", "actual_wind", "note"]
SHORT = {"temperature_2m": "temp", "wind_speed_10m": "wind", "wind_gusts_10m": "gust", "precipitation": "precip"}


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "sports-research"}), timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            if getattr(e, "code", None) == 400 or k == tries - 1: raise
            time.sleep(4 * (k + 1))


def pick(resp, var, start_idx, n=4):
    """4-hour summary of one hourly series: mean (max for gusts, sum for precip). None when the model had no data."""
    s = (resp.get("hourly") or {}).get(var)
    if not s: return None
    w = [x for x in s[start_idx:start_idx + n] if x is not None]
    if not w: return None
    return round(max(w) if "gust" in var else (sum(w) if "precip" in var else sum(w) / len(w)), 2)


def kickoff_utc(day, hhmm):
    t = dt.datetime.strptime(f"{day} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("America/New_York"))
    return t.astimezone(dt.timezone.utc)


def locate(g):
    st = str(g.get("stadium") or "").lower()
    for key, ll in NEUTRAL.items():
        if key in st: return ll
    if str(g.get("location")) != "Neutral" and g["home_team"] in TEAM: return TEAM[g["home_team"]]
    return None


def fetch_game(g, ll, ko):
    lat, lon = ll; day = ko.strftime("%Y-%m-%d"); idx = ko.hour
    unit = "wind_speed_unit=mph&temperature_unit=fahrenheit&precipitation_unit=inch&timezone=UTC"
    prev = ",".join(VARS + [f"{v}_previous_day{k}" for v in VARS for k in LEADS])
    row = {}
    try:
        r = get(f"https://previous-runs-api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly={prev}&start_date={day}&end_date={day}&{unit}")
        p = os.path.join(OUT, "samples", "previous_runs_sample.json")
        if not os.path.exists(p): json.dump(r, open(p, "w"))
        for v in VARS:
            row[f"{SHORT[v]}_d0"] = pick(r, v, idx)
            for k in LEADS: row[f"{SHORT[v]}_d{k}"] = pick(r, f"{v}_previous_day{k}", idx)
    except Exception as e:
        row["note"] = f"previous_runs: {type(e).__name__} {str(e)[:50]}"
    try:
        r = get(f"https://historical-forecast-api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly={','.join(VARS)}&start_date={day}&end_date={day}&{unit}")
        p = os.path.join(OUT, "samples", "historical_forecast_sample.json")
        if not os.path.exists(p): json.dump(r, open(p, "w"))
        for v in VARS: row[f"{SHORT[v]}_hf"] = pick(r, v, idx)
    except Exception as e:
        row["note"] = (row.get("note", "") + f" hist_forecast: {type(e).__name__} {str(e)[:50]}").strip()
    return row


def main():
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 2022
    g = pd.read_csv(GAMES, low_memory=False)
    g = g[(g.season >= first) & (g.game_type == "REG") & (~g.roof.isin(["dome", "closed"]))].copy()
    path = os.path.join(OUT, "nfl_forecasts.csv")
    done = set(pd.read_csv(path).game_id) if os.path.exists(path) else set()
    new = not os.path.exists(path); unmatched = []
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new: w.writeheader()
        for _, x in g.iterrows():
            if x.game_id in done or pd.isna(x.gametime): continue
            ll = locate(x)
            if ll is None: unmatched.append(dict(game_id=x.game_id, stadium=x.get("stadium"), home=x.home_team)); continue
            ko = kickoff_utc(x.gameday, x.gametime)
            row = dict(game_id=x.game_id, season=x.season, week=x.week, home_team=x.home_team, roof=x.roof, kickoff_utc=ko.strftime("%Y-%m-%d %H:%M"),
                       lat=ll[0], lon=ll[1], actual_temp=x.get("temp"), actual_wind=x.get("wind"))
            row.update(fetch_game(x, ll, ko)); w.writerow(row); f.flush(); time.sleep(0.25)
    if unmatched:
        pd.DataFrame(unmatched).to_csv(os.path.join(OUT, "unmatched.csv"), index=False)
        print(len(unmatched), "games with no stadium match: weather/unmatched.csv")


if __name__ == "__main__":
    main()
