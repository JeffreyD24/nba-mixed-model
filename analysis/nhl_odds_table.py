"""DraftKings and Pinnacle NHL prices from the historical odds download, per game, at: the opener (first snapshot with the
moneyline), +15/+30/+60 minutes, halfway between open and tip, and the close (last snapshot before the start). Moneyline,
puck line (home point and both prices) and total (line and both prices). Team codes match nhl-mixed-model.
  python analysis/nhl_odds_table.py WORKDIR -> data/odds_history/nhl_prices.csv.gz"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
NAME = {"Anaheim Ducks": "ana", "Arizona Coyotes": "uta", "Utah Hockey Club": "uta", "Utah Mammoth": "uta", "Boston Bruins": "bos",
        "Buffalo Sabres": "buf", "Carolina Hurricanes": "car", "Columbus Blue Jackets": "cbj", "Calgary Flames": "cgy",
        "Chicago Blackhawks": "chi", "Colorado Avalanche": "col", "Dallas Stars": "dal", "Detroit Red Wings": "det",
        "Edmonton Oilers": "edm", "Florida Panthers": "fla", "Los Angeles Kings": "la", "Minnesota Wild": "min",
        "Montréal Canadiens": "mtl", "Montreal Canadiens": "mtl", "New Jersey Devils": "nj", "Nashville Predators": "nsh",
        "New York Islanders": "nyi", "New York Rangers": "nyr", "Ottawa Senators": "ott", "Philadelphia Flyers": "phi",
        "Pittsburgh Penguins": "pit", "Seattle Kraken": "sea", "San Jose Sharks": "sj", "St Louis Blues": "stl", "St. Louis Blues": "stl",
        "Tampa Bay Lightning": "tb", "Toronto Maple Leafs": "tor", "Vancouver Canucks": "van", "Vegas Golden Knights": "vgk",
        "Winnipeg Jets": "wpg", "Washington Capitals": "wsh"}
rows, unk = [], set()
LABS = ("open", "m15", "m30", "m60", "mid", "close")
for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", "nhl", "*.csv.gz"))):
    d = pd.read_csv(f); d = d[d.book.isin(["draftkings", "pinnacle"])]
    if not len(d): continue
    d["t"] = pd.to_datetime(d.snapshot_utc); d["tip"] = pd.to_datetime(d.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    d = d[d.t < d.tip].sort_values("t")
    unk |= (set(d.home) | set(d.away)) - set(NAME)
    d = d[d.home.isin(NAME) & d.away.isin(NAME)]
    d["oc"] = np.where(d.market == "totals", d.outcome, np.where(d.outcome == d.home, "home", "away"))
    k = ["event_id", "book"]
    t0 = d[d.market == "h2h"].groupby(k).t.min().rename("t0"); tc = d[d.market == "h2h"].groupby(k).t.max().rename("tc")
    d = d.join(t0, on=k).join(tc, on=k).dropna(subset=["t0"])
    base = d.groupby(k).agg(home=("home", "first"), away=("away", "first"), tip=("tip", "first"), t0=("t0", "first")).reset_index()
    for lab in LABS:
        lim = {"open": d.t0, "m15": d.t0 + pd.Timedelta(minutes=15), "m30": d.t0 + pd.Timedelta(minutes=30),
               "m60": d.t0 + pd.Timedelta(minutes=60), "mid": d.t0 + (d.tip - d.t0) / 2, "close": d.tc}[lab]
        s = d[d.t <= lim].groupby(k + ["market", "oc"]).tail(1)
        pv = s.pivot_table(index=k, columns=["market", "oc"], values=["price", "point"], aggfunc="first")
        out = pd.DataFrame(index=pv.index)
        g = lambda v, mk, oc: pv[(v, mk, oc)] if (v, mk, oc) in pv.columns else np.nan
        out[f"{lab}_home_ml"] = g("price", "h2h", "home"); out[f"{lab}_away_ml"] = g("price", "h2h", "away")
        out[f"{lab}_home_pl"] = g("point", "spreads", "home"); out[f"{lab}_home_pl_odds"] = g("price", "spreads", "home")
        out[f"{lab}_away_pl_odds"] = g("price", "spreads", "away")
        out[f"{lab}_total"] = g("point", "totals", "Over"); out[f"{lab}_over_odds"] = g("price", "totals", "Over")
        out[f"{lab}_under_odds"] = np.where(g("point", "totals", "Under") == out[f"{lab}_total"], g("price", "totals", "Under"), np.nan)
        base = base.merge(out.reset_index(), on=k, how="left")
    base["date"] = base.tip.dt.tz_convert("America/New_York").dt.date.astype(str)
    base["home"] = base.home.map(NAME); base["away"] = base.away.map(NAME)
    rows.append(base)
O = pd.concat(rows, ignore_index=True)
O.to_csv(os.path.join(W, "data", "odds_history", "nhl_prices.csv.gz"), index=False, compression="gzip")
print(len(O), "game-books", O.groupby("book").size().to_dict(), "unknown names:", unk)
