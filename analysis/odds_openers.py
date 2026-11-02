"""DraftKings (and Pinnacle) opening and closing NBA lines from the historical odds download (data/odds_history/nba/).
Opener = the book's first spread/total seen for the game; close = its last snapshot before tip. Home-team perspective.
  python analysis/odds_openers.py WORKDIR  -> data/odds_history/nba_open_close.csv"""
import os, sys, glob
import pandas as pd, numpy as np
W = os.path.abspath(sys.argv[1])
NAME = {"Atlanta Hawks": "atl", "Brooklyn Nets": "bkn", "Boston Celtics": "bos", "Charlotte Hornets": "cha", "Chicago Bulls": "chi",
        "Cleveland Cavaliers": "cle", "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det",
        "Golden State Warriors": "gs", "Houston Rockets": "hou", "Indiana Pacers": "ind", "Los Angeles Clippers": "lac", "LA Clippers": "lac",
        "Los Angeles Lakers": "lal", "Memphis Grizzlies": "mem", "Miami Heat": "mia", "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min",
        "New Orleans Pelicans": "no", "New York Knicks": "ny", "Oklahoma City Thunder": "okc", "Orlando Magic": "orl",
        "Philadelphia 76ers": "phi", "Phoenix Suns": "phx", "Portland Trail Blazers": "por", "San Antonio Spurs": "sa",
        "Sacramento Kings": "sac", "Toronto Raptors": "tor", "Utah Jazz": "utah", "Washington Wizards": "wsh"}
rows = []
for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", "nba", "*.csv.gz"))):
    d = pd.read_csv(f)
    d["t"] = pd.to_datetime(d.snapshot_utc); d["tip"] = pd.to_datetime(d.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    d = d[d.t < d.tip]
    for (eid, book), g in d[d.book.isin(["draftkings", "pinnacle"])].groupby(["event_id", "book"]):
        h = NAME.get(g.home.iloc[0]); a = NAME.get(g.away.iloc[0])
        sp = g[(g.market == "spreads") & (g.outcome == g.home.iloc[0])].sort_values("t")
        to = g[(g.market == "totals") & (g.outcome == "Over")].sort_values("t")
        r = dict(date=str(g.tip.iloc[0].tz_convert("America/New_York").date()), home=h, away=a, book=book)
        if len(sp): r.update(open_spread=sp.point.iloc[0], open_spread_t=str(sp.t.iloc[0]), close_spread=sp.point.iloc[-1])
        if len(to): r.update(open_total=to.point.iloc[0], open_total_t=str(to.t.iloc[0]), close_total=to.point.iloc[-1])
        rows.append(r)
O = pd.DataFrame(rows); O.to_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"), index=False)
print(len(O), "game-books;", O.groupby("book").size().to_dict())
