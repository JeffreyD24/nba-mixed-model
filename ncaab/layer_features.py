"""NCAAM pre-game layer features for the stale-line rule v2 (Nov 5, 2026). One code path for research and live:
the same logic as NCAAM repo ncaab/lineup_travel_features.py and ncaab/roster_features.py (definitions:
NCAAM ncaab/research/LINEUP_INJURY_TRAVEL_PREREG_2026-11-05.md and ROSTER_CONTINUITY_PREREG_2026-11-05.md), refactored into functions so the live job
can append today's scheduled games and get their features from exactly the same code. Verified against the saved research features
(ncaab/layer_features_check.py; see its output file).
  build(W, seasons, extra=None) -> one row per game of `seasons` (+ extra scheduled games):
     espn_id, h_/a_ lost_min_share, lost_pts_share, new_starters, travel_miles, tz_shift, rest_days, back_to_back, games_last_7, n_box, R1-R4
  extra: DataFrame of scheduled games: espn_id, season, date, hk, ak, neutral, city, state (venue from ESPN's scoreboard)."""
import os, math
from collections import Counter
import numpy as np, pandas as pd
import zipcodes

LF = ["lost_min_share", "lost_pts_share", "new_starters", "travel_miles", "tz_shift", "rest_days", "back_to_back", "games_last_7"]
RF = ["R1", "R2", "R3", "R4"]
MANUAL = {  # places the zip table misses; approximate city-center coordinates (same table as the research build)
    ("moon township", "PA"): (40.52, -80.21), ("homewood", "AL"): (33.48, -86.80), ("riverdale", "NY"): (40.90, -73.91),
    ("lawrenceville", "NJ"): (40.30, -74.73), ("nassau", "Bahamas"): (25.04, -77.35), ("ashwaubenon", "WI"): (44.49, -88.07),
    ("highland heights", "KY"): (39.03, -84.45), ("queens", "NY"): (40.73, -73.79), ("maui", "HI"): (20.80, -156.33),
    ("rosemont", "IL"): (41.99, -87.87), ("storrs", "CT"): (41.81, -72.25), ("saint thomas", "Virgin Islands"): (18.34, -64.93),
    ("cancun", "Mexico"): (21.16, -86.85), ("san juan", "Puerto Rico"): (18.47, -66.11), ("george town", "Cayman Islands"): (19.29, -81.37),
    ("lake buena vista", "FL"): (28.37, -81.52), ("sunrise", "FL"): (26.16, -80.26), ("hot springs", "AR"): (34.50, -93.05),
    ("college park", "GA"): (33.65, -84.45), ("laval", "PQ"): (45.57, -73.69), ("freeport", "Bahamas"): (26.53, -78.70),
    ("bimini", "Bahamas"): (25.73, -79.30), ("bayamon", "Puerto Rico"): (18.40, -66.16), ("montego bay", "Jamaica"): (18.47, -77.92),
}
_ZD = None
def place(c, s):
    global _ZD
    if _ZD is None:
        _ZD = {}
        for z in zipcodes.list_all():
            if z.get("lat") and z.get("long") and z["zip_code_type"] != "MILITARY":
                _ZD.setdefault((z["city"].lower(), z["state"]), []).append((float(z["lat"]), float(z["long"])))
    if not isinstance(c, str) or not isinstance(s, str): return (np.nan, np.nan)
    k = (c.lower().strip(), s.strip())
    for kk in (k, (k[0].replace("saint ", "st. "), k[1]), (k[0].replace("st. ", "saint "), k[1])):
        if kk in MANUAL: return MANUAL[kk]
        if kk in _ZD: return tuple(np.mean(_ZD[kk], axis=0))
    return (np.nan, np.nan)
def hav(a, b):
    if np.isnan(a[0]) or np.isnan(b[0]): return np.nan
    p1, p2 = math.radians(a[0]), math.radians(b[0]); dl = math.radians(b[1] - a[1]); dp = p2 - p1
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))
tz = lambda v: np.nan if np.isnan(v[0]) else round(-v[1] / 15)

def _load(W, seasons, extra):
    D = os.path.join(W, "ncaab", "data"); box = os.path.join(D, "box")
    G = pd.read_csv(os.path.join(D, "all_games.csv"), low_memory=False, usecols=["season", "date", "espn_id", "hk", "ak", "neutral", "home_pts", "away_pts"])
    G["neutral"] = G["neutral"].astype(str).str.lower().isin(["true", "1", "1.0"])
    allS = sorted(G.season.unique())
    TM = pd.concat([pd.read_csv(os.path.join(box, f"teams_{s}.csv.gz"), usecols=["espn_id", "city", "state"]) for s in allS
                    if os.path.exists(os.path.join(box, f"teams_{s}.csv.gz"))]).drop_duplicates("espn_id")
    if extra is not None and len(extra):
        X = extra.copy(); X["neutral"] = X["neutral"].astype(bool); X["home_pts"] = np.nan; X["away_pts"] = np.nan
        G = pd.concat([G[~G.espn_id.isin(X.espn_id)], X[G.columns]], ignore_index=True)
        TM = pd.concat([TM[~TM.espn_id.isin(X.espn_id)], X[["espn_id", "city", "state"]]], ignore_index=True)
    G["date"] = pd.to_datetime(G["date"]); G["espn_id"] = G["espn_id"].astype("int64"); G["hk"] = G.hk.astype(str); G["ak"] = G.ak.astype(str)
    TM["espn_id"] = TM.espn_id.astype("int64")
    pc = {k: place(*k) for k in set(zip(TM.city, TM.state))}
    TM["vlat"] = [pc[k][0] for k in zip(TM.city, TM.state)]; TM["vlon"] = [pc[k][1] for k in zip(TM.city, TM.state)]
    G = G.merge(TM[["espn_id", "vlat", "vlon"]], on="espn_id", how="left")
    need = sorted(set(seasons) | {s - 1 for s in seasons})
    PB = {}
    for s in need:
        f = os.path.join(box, f"players_{s}.csv.gz")
        if os.path.exists(f):
            p = pd.read_csv(f, usecols=["espn_id", "team_id", "athlete_id", "starter", "min", "pts"])
            p["min"] = p["min"].fillna(0.0); p["pts"] = p["pts"].fillna(0.0); p["team_id"] = p.team_id.astype(str); PB[s] = p
    return G, PB

def _lineup_travel(G, PB, seasons):
    L = pd.concat([G.assign(team=G.hk, opp=G.ak, is_home=True), G.assign(team=G.ak, opp=G.hk, is_home=False)], ignore_index=True)
    L = L.sort_values(["team", "season", "date", "espn_id"]).reset_index(drop=True)
    def modal(df):
        pts = [(round(a, 2), round(b, 2)) for a, b in zip(df.vlat, df.vlon) if not (np.isnan(a) or np.isnan(b))]
        return Counter(pts).most_common(1)[0][0] if pts else (np.nan, np.nan)
    H = L[L.is_home & ~L.neutral]
    base_ts = {k: modal(g) for k, g in H.groupby(["team", "season"])}; base_t = {k: modal(g) for k, g in H.groupby("team")}
    def base(team, season):
        b = base_ts.get((team, season), (np.nan, np.nan)); return b if not np.isnan(b[0]) else base_t.get(team, (np.nan, np.nan))
    def venue(lat, lon, is_home, neutral, team, opp, season):
        if not np.isnan(lat): return (lat, lon)
        if neutral: return (np.nan, np.nan)
        return base(team if is_home else opp, season)
    BX = {}
    for s in seasons:
        if s not in PB: continue
        for (e, t), g in PB[s].groupby(["espn_id", "team_id"]):
            BX[(int(e), str(t))] = (dict(zip(g.athlete_id, g["min"])), dict(zip(g.athlete_id, g.pts)), set(g.athlete_id[g.starter == 1]))
    def lineup(prior):
        win = prior[-10:]; n = len(win); tm, tp, pl = Counter(), Counter(), Counter()
        for m, p, _ in win:
            for a, v in m.items(): tm[a] += v; tp[a] += p.get(a, 0.0); pl[a] += v > 0
        avg = {a: tm[a] / n for a in tm}
        reg = [a for a in sorted(avg, key=lambda a: -avg[a])[:8] if avg[a] >= 15 and pl[a] >= 6]
        den = sum(avg[a] for a in reg); pden = sum(tp[a] / n for a in reg)
        lastm = win[-1][0]; lost = [a for a in reg if lastm.get(a, 0.0) <= 0]
        A = sum(avg[a] for a in lost) / den if den > 0 else 0.0; B = sum(tp[a] / n for a in lost) / pden if pden > 0 else 0.0
        cnt = Counter(a for _, _, st in prior[-11:-1] for a in st); top5 = {a for a, _ in cnt.most_common(5)}
        return A, B, len(win[-1][2] - top5)
    rows = []
    for (team, season), g in L[L.season.isin(seasons)].groupby(["team", "season"], sort=False):
        bs = base(team, season); prior = []; sched = []
        for r in g.itertuples(index=False):
            v = venue(r.vlat, r.vlon, r.is_home, r.neutral, team, r.opp, season)
            rec = dict(espn_id=r.espn_id, team=team, is_home=r.is_home, n_box=len(prior))
            if sched:
                pd_, pv = sched[-1]; rest = min((r.date - pd_).days, 7); pv = pv if not np.isnan(pv[0]) else bs
            else:
                rest, pv = 7, bs
            rec["rest_days"] = rest; rec["back_to_back"] = int(rest <= 1); rec["games_last_7"] = sum((r.date - d).days <= 7 for d, _ in sched)
            mi = hav(pv, v); rec["travel_miles"] = np.log1p(mi) if not np.isnan(mi) else np.nan
            rec["tz_shift"] = abs(tz(pv) - tz(v)) if not (np.isnan(pv[0]) or np.isnan(v[0])) else np.nan
            if len(prior) >= 5:
                A, B, C = lineup(prior); rec.update(lost_min_share=A, lost_pts_share=B, new_starters=C)
            sched.append((r.date, v)); this = BX.get((int(r.espn_id), str(team)))
            if this is not None: prior.append(this)
            rows.append(rec)
    if not rows: return pd.DataFrame(columns=["espn_id", "team", "is_home", "n_box"] + LF).astype({"espn_id": "int64", "team": str})   # Nov 6, 2026 (Fable): no rows -> NaN columns
    return pd.DataFrame(rows)

def _roster(G, PB, seasons):
    L = pd.concat([G.assign(t=G.hk, mg=G.home_pts - G.away_pts), G.assign(t=G.ak, mg=G.away_pts - G.home_pts)])
    STR = L.groupby(["season", "t"]).mg.mean().to_dict(); date_of = dict(zip(G.espn_id, G.date)); rows = []
    for s in seasons:
        if s - 1 not in PB or s not in PB: continue
        q = PB[s - 1]; pa = q.groupby(["athlete_id", "team_id"]).agg(mn=("min", "sum"), pt=("pts", "sum")).reset_index()
        main = pa.sort_values("mn").drop_duplicates("athlete_id", keep="last").set_index("athlete_id").team_id.to_dict()
        apts = pa.groupby("athlete_id").pt.sum().to_dict(); tpts = q.groupby("team_id").pts.sum().to_dict()
        cur = PB[s][PB[s]["min"] > 0].copy(); cur["date"] = cur.espn_id.map(date_of)
        app = cur.groupby(["team_id", "date"]).athlete_id.apply(set).to_dict()
        Gs = G[G.season == s]
        for team, g in pd.concat([Gs.assign(t=Gs.hk), Gs.assign(t=Gs.ak)]).groupby("t"):
            dts = sorted(g.date.unique()); known = set(); n = 0; tp = tpts.get(team, 0.0); st = STR.get((s - 1, team), np.nan)
            for d in dts:
                ids = g[g.date == d].espn_id.values
                if tp > 0 and known:
                    rp = sum(apts.get(a, 0) for a in known if main.get(a) == team)
                    inc_ids = [a for a in known if a in main and main[a] != team]; ip = sum(apts.get(a, 0) for a in inc_ids)
                    sw = [(apts.get(a, 0), STR.get((s - 1, main[a]), np.nan)) for a in inc_ids]; sw = [(w, v) for w, v in sw if w > 0 and np.isfinite(v)]
                    strin = sum(w * v for w, v in sw) / sum(w for w, _ in sw) if sw else 0.0; ret, inc = min(rp / tp, 1.0), min(ip / tp, 2.0)
                else:
                    ret = inc = strin = np.nan
                for e in ids: rows.append(dict(espn_id=e, team=team, n=n, ret=ret, inc=inc, str=st, strin=strin))
                for e in ids: known |= app.get((team, pd.Timestamp(d)), set())
                n += len(ids)
    if not rows:   # Nov 6, 2026 (Fable): first days of a season or a missing players_{season}.csv.gz -> NaN roster columns, not an error
        return pd.DataFrame(columns=["espn_id", "team", "n", "ret", "inc", "str", "strin"] + RF).astype({"espn_id": "int64", "team": str})
    F = pd.DataFrame(rows)
    early = ((15 - F.n) / 15).where((F.n >= 1) & (F.n <= 14))
    F["R1"] = early * (1 - F.ret); F["R2"] = early * F.inc; F["R3"] = early * (1 - F.ret) * F["str"]; F["R4"] = early * F.inc * F.strin
    return F

def build(W, seasons, extra=None):
    G, PB = _load(W, seasons, extra)
    A = _lineup_travel(G, PB, seasons); R = _roster(G, PB, seasons)
    Gs = G[G.season.isin(seasons)][["espn_id", "hk", "ak"]]
    out = Gs[["espn_id"]].copy()
    for side, key in (("h", "hk"), ("a", "ak")):
        a = Gs.merge(A.rename(columns={"team": key}), on=["espn_id", key], how="left")
        r = Gs.merge(R.rename(columns={"team": key}), on=["espn_id", key], how="left")
        for c in LF[:3] + LF[3:] + ["n_box"]: out[f"{side}_{c}"] = a[c].values if c in a else np.nan
        for c in RF + ["n"]: out[f"{side}_{c}"] = r[c].values if c in r else np.nan
    return out.reset_index(drop=True)

def diffs(F):
    """home - away feature differences in the order the v2 coefficients use (missing -> 0, as in the backtest)."""
    return np.column_stack([(F["h_" + f] - F["a_" + f]).fillna(0).values for f in LF + RF])
