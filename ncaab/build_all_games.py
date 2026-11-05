"""One NCAAM game file for every season (ncaab/research/MODEL2_PREREG_2026-11-05.md): ESPN scoreboard rows (team ids, conference, neutral,
conference game) + lines. 2007-21: SportsbookReview open/close (matched by date and score, orientation fixed). 2021-26: Action Network
Open, consensus (2021-23) / DraftKings (2023-26) close, and the books' own openers (ESPN feed: DraftKings else ESPN BET, flipped signs dropped).
Spreads are home-perspective (negative = home favored).  python ncaab/build_all_games.py WORKDIR -> ncaab/data/all_games.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); D = os.path.join(W, "ncaab", "data")
M = pd.read_csv(os.path.join(D, "espn_meta.csv"), low_memory=False).dropna(subset=["home_pts", "away_pts", "home_espn_team", "away_espn_team"])
M = M.drop_duplicates("espn_id"); M["home_pts"] = M.home_pts.astype(int); M["away_pts"] = M.away_pts.astype(int)
M = M[M.home_pts + M.away_pts > 60]
d = pd.to_datetime(M.date); M["season"] = d.dt.year + (d.dt.month >= 8).astype(int)
M["hk"], M["ak"] = M.home_espn_team.astype(int).astype(str), M.away_espn_team.astype(int).astype(str)
for c in ("open_sp", "close_sp", "open_tot", "close_tot", "book_sp", "book_tot"): M[c] = np.nan
M["line_src"] = ""
# --- SBR 2007-21
S = pd.read_csv(os.path.join(D, "sbr_games.csv")); S = S[S.season <= 2021]
key = lambda dd, a, b: (dd, min(a, b), max(a, b))
S["k"] = [key(x, int(a), int(b)) for x, a, b in zip(S.date, S.home_pts, S.away_pts)]
M["k"] = [key(x, a, b) for x, a, b in zip(M.date, M.home_pts, M.away_pts)]
S = S[~S.k.duplicated(keep=False)].set_index("k"); okm = ~M.k.duplicated(keep=False) & (M.season <= 2021)
J = M.loc[okm, ["k", "home_pts"]].join(S[["home_pts", "open_spread", "close_spread", "open_total", "close_total"]], on="k", rsuffix="_s", how="inner")
sgn = np.where(J.home_pts == J.home_pts_s, 1, -1)       # SBR home = ESPN away -> flip the spread sign
for c_m, c_s, sp in (("open_sp", "open_spread", True), ("close_sp", "close_spread", True), ("open_tot", "open_total", False), ("close_tot", "close_total", False)):
    M.loc[J.index, c_m] = J[c_s] * (sgn if sp else 1)
M.loc[J.index, "line_src"] = "SBR"
# --- Action Network + book openers 2021-26
A = pd.read_csv(os.path.join(D, "games.csv"), low_memory=False); A = A[A.espn_id.notna() & (A.season >= 2022)].drop_duplicates("espn_id")
A["espn_id"] = A.espn_id.astype(int); A = A.set_index("espn_id")
M["eid"] = M.espn_id.astype(int); idx = M.index[M.eid.isin(A.index)]; a = A.loc[M.loc[idx, "eid"]]
same = (a.home_pts.values == M.loc[idx, "home_pts"].values)
f = np.where(same, 1, -1)
M.loc[idx, "open_sp"] = a.open_spread.values * f; M.loc[idx, "open_tot"] = a.open_total.values
cs = np.where(a.season.values >= 2024, a.dk_spread.values, a.cons_spread.values); ct = np.where(a.season.values >= 2024, a.dk_total.values, a.cons_total.values)
M.loc[idx, "close_sp"] = cs * f; M.loc[idx, "close_tot"] = ct; M.loc[idx, "line_src"] = np.where(a.season.values >= 2024, "AN open / DK close", "AN open / consensus close")
E = pd.read_csv(os.path.join(D, "espn_openers.csv"))
pk = pd.concat([E[E.provider == "DraftKings"].assign(pr=0), E[E.provider == "ESPN BET"].assign(pr=1)]).dropna(subset=["open_spread"]).sort_values("pr").drop_duplicates("espn_id").set_index("espn_id")
j = M.index[M.eid.isin(pk.index)]; b = pk.loc[M.loc[j, "eid"]]
M.loc[j, "book_sp"] = b.open_spread.values; M.loc[j, "book_tot"] = b.open_total.values; M.loc[j, "book"] = b.provider.values
fl = M.book_sp.notna() & M.close_sp.notna() & M.open_sp.notna() & (np.sign(M.book_sp) != np.sign(M.close_sp)) & \
     ((M.book_sp + M.close_sp).abs() < (M.book_sp - M.close_sp).abs()) & (M.close_sp.abs() >= 1.5) & (np.sign(M.book_sp) != np.sign(M.open_sp))
M.loc[fl | ((M.book_sp - M.close_sp).abs() > 10), "book_sp"] = np.nan; M.loc[(M.book_tot - M.close_tot).abs() > 15, "book_tot"] = np.nan
M["h"] = np.where(M.neutral.astype(str) == "True", 0.0, 0.5)
POWER = {2, 4, 7, 8, 21, 23}
M["both_power"] = M.home_conf_id.isin(POWER) & M.away_conf_id.isin(POWER)
M["conf_game"] = M.conf_game.astype(str) == "True"
M["start"] = M.date
keep = ["season", "date", "start", "espn_id", "hk", "ak", "home_name", "away_name", "home_conf_id", "away_conf_id", "h", "neutral", "conf_game", "both_power",
        "tournament", "home_rank", "away_rank", "home_pts", "away_pts", "open_sp", "close_sp", "open_tot", "close_tot", "book_sp", "book_tot", "book", "line_src"]
M = M.sort_values(["date", "espn_id"])[keep]; M.to_csv(os.path.join(D, "all_games.csv"), index=False)
g = M.groupby("season").agg(games=("espn_id", "size"), open=("open_sp", lambda x: x.notna().sum()), close=("close_sp", lambda x: x.notna().sum()), book=("book_sp", lambda x: x.notna().sum()))
print(g.T.to_string())
m = M.home_pts - M.away_pts; k = M.close_sp.notna(); print("sanity RMSE close", np.sqrt(np.mean((m[k] + M.close_sp[k]) ** 2)).round(2), "open", np.sqrt(np.mean((m[k & M.open_sp.notna()] + M.open_sp[k & M.open_sp.notna()]) ** 2)).round(2))
