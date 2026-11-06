"""NCAAM pre-game layer features for today's and the next 3 days' games (stale-line rule v2, Nov 5, 2026).
ESPN's scoreboard gives the scheduled D-I games with their venue city/state; ncaab/layer_features.py (verified identical to the research features,
ncaab/research/layer_features_check_output.txt) computes each team's lineup / inferred-injury / travel / rest and early-season roster features from
games before that date. Runs in the morning job after ncaab/box_daily.py.
  python ncaab/live_features.py WORKDIR -> ncaab/state/live_features.csv (one row per scheduled game; h_/a_ by ESPN's home/away)"""
import os, sys, json, time, importlib.util, urllib.request
import pandas as pd
W = os.path.abspath(sys.argv[1]); ST = os.path.join(W, "ncaab", "state"); os.makedirs(ST, exist_ok=True)
spec = importlib.util.spec_from_file_location("lf", os.path.join(W, "ncaab", "layer_features.py")); lf = importlib.util.module_from_spec(spec); spec.loader.exec_module(lf)
def get(u):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r: return json.loads(r.read())
        except Exception: time.sleep(2 + 2 * i)
    return None
today = pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None)
G = pd.read_csv(os.path.join(W, "ncaab", "data", "all_games.csv"), low_memory=False, usecols=["season", "date"]); cur = int(G.season.max())
last = pd.to_datetime(G.date).max()
if last < today - pd.Timedelta(days=1):   # Fable fix, Nov 6, 2026: m2_daily failed -> rest_days / back_to_back would be wrong; keep the old file (live_alert ignores it after 1 day)
    print(f"all_games.csv ends {last.date()}, before yesterday ({(today - pd.Timedelta(days=1)).date()}): the daily update failed; features NOT written"); sys.exit(0)
if today.month >= 8 and today.year + 1 > cur: cur = today.year + 1
rows = []
for k in range(4):
    d = today + pd.Timedelta(days=k)
    js = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={d:%Y%m%d}&groups=50&limit=500")
    if js is None: print("ESPN scoreboard unavailable for", d.date(), "- features file not updated"); sys.exit(0)
    for e in js.get("events", []):
        c = e["competitions"][0]; t = {x["homeAway"]: x for x in c["competitors"]}
        if "home" not in t or "away" not in t: continue
        ad = (c.get("venue") or {}).get("address") or {}
        rows.append(dict(espn_id=int(e["id"]), season=cur, date=str(d.date()), hk=str(t["home"]["team"]["id"]), ak=str(t["away"]["team"]["id"]),
                         neutral=bool(c.get("neutralSite")), city=ad.get("city"), state=ad.get("state")))
X = pd.DataFrame(rows).drop_duplicates("espn_id")
F = lf.build(W, [cur], extra=X); F = F[F.espn_id.isin(X.espn_id)]
out = X[["espn_id", "date", "hk", "ak", "neutral"]].merge(F, on="espn_id", how="left")
out["made_at_et"] = str(pd.Timestamp.now(tz="America/New_York"))[:16]
out.to_csv(os.path.join(ST, "live_features.csv"), index=False)
print(f"NCAAM live features: {len(out)} scheduled games {X.date.min()}..{X.date.max()}, season {cur}; "
      f"lineup features for {int(out.h_lost_min_share.notna().sum())} home teams, roster features for {int(out.h_R1.notna().sum())}")
