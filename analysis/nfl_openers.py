"""DraftKings and Pinnacle NFL opening/closing spread and total (home perspective) from the odds history, team codes as in
nfl-mixed-model.  python analysis/nfl_openers.py WORKDIR -> data/odds_history/nfl_open_close.csv"""
import os, sys, glob
import pandas as pd
W = os.path.abspath(sys.argv[1])
NAME = {"Arizona Cardinals": "ari", "Atlanta Falcons": "atl", "Baltimore Ravens": "bal", "Buffalo Bills": "buf", "Carolina Panthers": "car",
        "Chicago Bears": "chi", "Cincinnati Bengals": "cin", "Cleveland Browns": "cle", "Dallas Cowboys": "dal", "Denver Broncos": "den",
        "Detroit Lions": "det", "Green Bay Packers": "gb", "Houston Texans": "hou", "Indianapolis Colts": "ind", "Jacksonville Jaguars": "jax",
        "Kansas City Chiefs": "kc", "Los Angeles Chargers": "lac", "Los Angeles Rams": "lar", "Las Vegas Raiders": "lv", "Oakland Raiders": "lv",
        "Miami Dolphins": "mia", "Minnesota Vikings": "min", "New England Patriots": "ne", "New Orleans Saints": "no", "New York Giants": "nyg",
        "New York Jets": "nyj", "Philadelphia Eagles": "phi", "Pittsburgh Steelers": "pit", "Seattle Seahawks": "sea", "San Francisco 49ers": "sf",
        "Tampa Bay Buccaneers": "tb", "Tennessee Titans": "ten", "Washington Football Team": "wsh", "Washington Commanders": "wsh", "Washington Redskins": "wsh"}
rows = []
for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", "nfl", "*.csv.gz"))):
    d = pd.read_csv(f); d = d[d.book.isin(["draftkings", "pinnacle"])]
    d["t"] = pd.to_datetime(d.snapshot_utc); d["tip"] = pd.to_datetime(d.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    d = d[d.t < d.tip]
    for (eid, book), g in d.groupby(["event_id", "book"]):
        H = g.home.iloc[0]; A = g.away.iloc[0]
        sp = g[(g.market == "spreads") & (g.outcome == H)].sort_values("t"); to = g[(g.market == "totals") & (g.outcome == "Over")].sort_values("t")
        r = dict(date=str(g.tip.iloc[0].tz_convert("America/New_York").date()), home=NAME.get(H), away=NAME.get(A), book=book)
        if len(sp): r.update(open_spread=sp.point.iloc[0], open_spread_t=str(sp.t.iloc[0]), close_spread=sp.point.iloc[-1])
        if len(to): r.update(open_total=to.point.iloc[0], close_total=to.point.iloc[-1])
        rows.append(r)
O = pd.DataFrame(rows); O.to_csv(os.path.join(W, "data", "odds_history", "nfl_open_close.csv"), index=False)
print(len(O), O.groupby("book").size().to_dict(), "unmapped", O.home.isna().sum())
