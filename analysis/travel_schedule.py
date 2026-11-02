"""
Home stands, road trips, travel distance and time zones (NBA 2021-22..2025-26, NHL 2021-22..2025-26).
For every game: home stand length so far, road trip length so far, the away team's travel (km from its previous game's arena),
time-zone change since its previous game and vs its home time zone, rest, 3-in-4 nights, the home team's first game back from a
trip, altitude. Then:
  1. MARKET: does the line already price these? (NBA: home cover margin vs the closing spread, over margin vs the closing total;
     NHL: home win vs the closing moneyline's no-vig chance)
  2. OUR BETS: win rate of the live models' bets by group (NBA totals and spreads at the DK opener; NHL shot model at the opener)
  python analysis/travel_schedule.py WORKDIR NHL_REPO
"""
import os, sys
import numpy as np, pandas as pd
from zoneinfo import ZoneInfo
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
NY, CH, DE, LA, PH = "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Phoenix"
NBA = {"atl": (33.757, -84.396, NY), "bos": (42.366, -71.062, NY), "bkn": (40.683, -73.976, NY), "cha": (35.225, -80.839, NY),
       "chi": (41.881, -87.674, CH), "cle": (41.496, -81.688, NY), "dal": (32.790, -96.810, CH), "den": (39.749, -105.008, DE),
       "det": (42.341, -83.055, NY), "gs": (37.768, -122.388, LA), "hou": (29.751, -95.362, CH), "ind": (39.764, -86.156, NY),
       "lac": (33.945, -118.341, LA), "lal": (34.043, -118.267, LA), "mem": (35.138, -90.051, CH), "mia": (25.781, -80.187, NY),
       "mil": (43.045, -87.917, CH), "min": (44.979, -93.276, CH), "no": (29.949, -90.082, CH), "ny": (40.751, -73.993, NY),
       "okc": (35.463, -97.515, CH), "orl": (28.539, -81.384, NY), "phi": (39.901, -75.172, NY), "phx": (33.446, -112.071, PH),
       "por": (45.532, -122.667, LA), "sac": (38.580, -121.500, LA), "sa": (29.427, -98.437, CH), "tor": (43.643, -79.379, NY),
       "utah": (40.768, -111.901, DE), "wsh": (38.898, -77.021, NY)}
NHL = {"ana": (33.808, -117.877, LA), "bos": (42.366, -71.062, NY), "buf": (42.875, -78.876, NY), "car": (35.803, -78.722, NY),
       "cbj": (39.969, -83.006, NY), "cgy": (51.037, -114.052, DE), "chi": (41.881, -87.674, CH), "col": (39.749, -105.008, DE),
       "dal": (32.790, -96.810, CH), "det": (42.341, -83.055, NY), "edm": (53.547, -113.498, DE), "fla": (26.158, -80.326, NY),
       "la": (34.043, -118.267, LA), "min": (44.945, -93.101, CH), "mtl": (45.496, -73.569, NY), "nj": (40.734, -74.171, NY),
       "nsh": (36.159, -86.779, CH), "nyi": (40.712, -73.726, NY), "nyr": (40.751, -73.993, NY), "ott": (45.297, -75.927, NY),
       "phi": (39.901, -75.172, NY), "pit": (40.440, -79.989, NY), "sea": (47.622, -122.354, LA), "sj": (37.333, -121.901, LA),
       "stl": (38.627, -90.203, CH), "tb": (27.943, -82.452, NY), "tor": (43.643, -79.379, NY), "van": (49.278, -123.109, LA),
       "vgk": (36.103, -115.178, LA), "wpg": (49.893, -97.144, CH), "wsh": (38.898, -77.021, NY),
       "uta_ari": (33.426, -111.932, PH), "uta": (40.768, -111.901, DE)}
ALT = {"den", "utah", "col", "uta"}


def km(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (a[0], a[1], b[0], b[1]))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(h))


def tzoff(tz, d):
    return pd.Timestamp(d).tz_localize(ZoneInfo(tz)).utcoffset().total_seconds() / 3600 - \
           pd.Timestamp(d).tz_localize(ZoneInfo(NY)).utcoffset().total_seconds() / 3600


def schedule_features(G, ARENA, venue_key=lambda t, s: t):
    """G: date, season, home, away (sorted). Adds travel / stand / trip / rest features."""
    G = G.sort_values("date").reset_index(drop=True)
    last = {}            # (season, team) -> (date, venue, was_home, run)
    feats = []
    for r in G.itertuples():
        v = ARENA[venue_key(r.home, r.season)]; f = {}
        for side, team in (("h", r.home), ("a", r.away)):
            home_arena = ARENA[venue_key(team, r.season)]
            prev = last.get((r.season, team))
            is_home = side == "h"
            if prev is None:
                pv, rest, run, prev_home, hist = home_arena, 7, 1, True, []
            else:
                pdate, pv, prev_home, run, hist = prev
                rest = (pd.Timestamp(r.date) - pd.Timestamp(pdate)).days
                run = run + 1 if prev_home == is_home else 1
            hist = [d for d in (hist or []) if (pd.Timestamp(r.date) - pd.Timestamp(d)).days <= 3]
            f[f"{side}_run"] = run                          # home stand length (home team) / road trip length (away team) incl. today
            f[f"{side}_rest"] = rest
            f[f"{side}_3in4"] = int(len(hist) >= 2)         # two other games in the previous 3 days
            f[f"{side}_km"] = km(pv, v)
            f[f"{side}_tz_move"] = tzoff(v[2], r.date) - tzoff(pv[2], r.date)          # + = moved east (lost hours)
            f[f"{side}_tz_home"] = tzoff(v[2], r.date) - tzoff(home_arena[2], r.date)  # + = playing east of home
            f[f"{side}_back_from_trip"] = int(is_home and prev is not None and not prev_home)
            f[f"{side}_trip_len_before"] = (prev[3] if (prev is not None and not prev_home and is_home) else 0)
            last[(r.season, team)] = (r.date, v, is_home, run, hist + [r.date])
        f["altitude"] = int(r.home in ALT)
        feats.append(f)
    return pd.concat([G, pd.DataFrame(feats)], axis=1)


def groups(D, y, lab_y, extra=None):
    """print mean of y (and n) by each schedule group"""
    defs = [("Home stand game #", pd.cut(D.h_run, [0, 1, 2, 3, 4, 30], labels=["1st", "2nd", "3rd", "4th", "5th+"])),
            ("Home team's first game back from a road trip of N", pd.cut(D.h_trip_len_before, [-1, 0, 2, 4, 30], labels=["not back from trip", "1-2", "3-4", "5+"])),
            ("Away team's road trip game #", pd.cut(D.a_run, [0, 1, 2, 3, 4, 30], labels=["1st", "2nd", "3rd", "4th", "5th+"])),
            ("Away team's travel since last game", pd.cut(D.a_km, [-1, 50, 800, 1600, 2800, 9000], labels=["<50 km", "50-800", "800-1600", "1600-2800", "2800+"])),
            ("Away team's time-zone move since last game", pd.cut(D.a_tz_move, [-4, -1.5, -0.5, 0.5, 1.5, 4], labels=["moved 2-3 west", "1 west", "same", "1 east", "moved 2-3 east"])),
            ("Away team playing vs its home time", pd.cut(D.a_tz_home, [-4, -1.5, -0.5, 0.5, 1.5, 4], labels=["2-3 h west of home", "1 west", "same", "1 east", "2-3 h east of home"])),
            ("Rest: home vs away", np.where(D.h_rest == 1, "home b2b", "") + np.where(D.a_rest == 1, " away b2b", "")),
            ("3 games in 4 nights", np.where(D.h_3in4 == 1, "home 3in4", "") + np.where(D.a_3in4 == 1, " away 3in4", "")),
            ("Altitude (DEN/UTA/COL)", D.altitude)]
    for lab, key in defs:
        print(f"  {lab}")
        for k, g in D.groupby(key, observed=True):
            yy = y[g.index]
            if yy.notna().sum() < 25: continue
            se = yy.std() / np.sqrt(yy.notna().sum())
            ex = f" | {extra(g)}" if extra else ""
            print(f"    {str(k):24s} n={yy.notna().sum():5d}  {lab_y} {yy.mean():+6.2f} (+/- {se:.2f}){ex}")


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    # ---------------- NBA
    T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
    D = schedule_features(T[["date", "season", "home", "away", "home_pts", "away_pts", "spread", "total"]].copy(), NBA)
    D.to_csv(os.path.join(W, "analysis", "travel_nba_games.csv"), index=False)
    D["cover"] = D.home_pts - D.away_pts + D.spread; D["over"] = D.home_pts + D.away_pts - D.total
    print("=" * 30, "NBA: MARKET (closing line), 2021-22..2025-26 -- home cover margin vs the close (pts)")
    groups(D, D.cover, "home covers by")
    print("\n  over margin vs the closing total (pts), same groups")
    groups(D, D.over, "over by")
    # our bets: half_compare (spreads) and total_autopsy (totals) bet files
    for name, f in (("NBA SPREAD BETS (live spread model, DK openers)", "half_compare_bets.csv"), ("NBA TOTALS BETS (live model)", "total_autopsy_bets.csv")):
        B = pd.read_csv(os.path.join(W, "analysis", f))
        B = B.merge(D.drop(columns=["season", "home_pts", "away_pts", "spread", "total"]), on=["date", "home", "away"], how="left").reset_index(drop=True)
        if "home_bet" not in B: B["home_bet"] = B.side.eq("over")         # placeholder for totals
        print("\n" + "=" * 30, name, f"{len(B)} bets, {B.won.mean():.1%}")
        units = lambda g: f"{g.won.mean():.1%} {g.won.sum() * 100 / 110 - (~g.won).sum():+.1f}u"
        groups(B, B.won.astype(float) * 100, "win %", extra=units)
    # ---------------- NHL
    T2 = pd.read_csv(os.path.join(N, "data", "training_games.csv"))
    T2 = T2[T2.season >= 2022]
    D2 = schedule_features(T2[["date", "season", "home", "away", "home_goals", "away_goals", "close_home_ml", "close_away_ml"]].copy(), NHL,
                           venue_key=lambda t, s: "uta_ari" if (t == "uta" and s <= 2024) else t)
    D2.to_csv(os.path.join(W, "analysis", "travel_nhl_games.csv"), index=False)
    dec = lambda o: np.where(o > 0, 1 + o / 100, 1 + 100 / np.abs(o))
    ih, ia = 1 / dec(D2.close_home_ml), 1 / dec(D2.close_away_ml)
    D2["home_vs_mkt"] = 100 * ((D2.home_goals > D2.away_goals).astype(float) - ih / (ih + ia))
    print("\n" + "=" * 30, "NHL: MARKET (closing moneyline), 2021-22..2025-26 -- home wins above the market's chance (win-% pts)")
    groups(D2, D2.home_vs_mkt, "home above market")
    B = pd.read_csv(os.path.join(N, "_tmp", "autopsy_bets_shot.csv"))
    B = B[B.season >= 2022].merge(D2.drop(columns=["season", "home_goals", "away_goals", "close_home_ml", "close_away_ml"]), on=["date", "home", "away"], how="left").reset_index(drop=True)
    print("\n" + "=" * 30, f"NHL SHOT MODEL BETS (moneyline + puck line, opener, EV 6%+): {len(B)} bets, {B.profit.sum():+.1f}u")
    groups(B, B.profit * 100, "ROI %", extra=lambda g: f"{g.profit.sum():+.1f}u, bets on home {(g.side == 'home').mean():.0%}")
    B["bet_side"] = np.where(B.side == "home", "bet HOME", "bet AWAY")
    print("\n  NHL shot model, split by the side we bet:")
    for k, g in B.groupby("bet_side"):
        print(f"   {k}"); groups(g, g.profit * 100, "ROI %", extra=lambda gg: f"{gg.profit.sum():+.1f}u")
