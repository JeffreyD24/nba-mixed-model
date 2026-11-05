"""Clean the SportsbookReview college basketball archive (data/external/sbr_ncaab/*.xlsx, 2007-08 to 2020-21) into one row per game.
SBR format: two rows per game (V/H, or N/N for neutral sites), Date = MMDD; in Open/Close the larger number on the pair is the total and
the smaller one is the spread, on the favorite's row ('pk' = 0). Opener source is not named (one market number, not DraftKings).
  python ncaab/clean_sbr.py WORKDIR -> ncaab/data/sbr_games.csv (season = END year, like our other files)"""
import os, sys, glob, re
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); rows = []; bad = 0
def num(x):
    s = str(x).strip().lower()
    if s in ("pk", "p", "pick", "0"): return 0.0
    try: return float(s)
    except ValueError: return np.nan
for f in sorted(glob.glob(os.path.join(W, "data", "external", "sbr_ncaab", "*.xlsx"))):
    y0 = int(re.search(r"(\d{4})-\d{2}", f).group(1)); X = pd.read_excel(f)
    X = X[X.VH.isin(["V", "H", "N"])].reset_index(drop=True)
    for i in range(0, len(X) - 1, 2):
        a, h = X.iloc[i], X.iloc[i + 1]
        if not ((a.VH == "V" and h.VH == "H") or (a.VH == "N" and h.VH == "N")) or a.Date != h.Date: bad += 1; continue
        md = int(a.Date); m, d = md // 100, md % 100; yr = y0 if m >= 8 else y0 + 1
        try: date = pd.Timestamp(yr, m, d)
        except Exception: bad += 1; continue
        r = dict(season=y0 + 1, date=str(date.date()), away=str(a.Team), home=str(h.Team), neutral=a.VH == "N",
                 away_pts=num(a.Final), home_pts=num(h.Final), away_1h=num(a["1st"]), home_1h=num(h["1st"]))
        for k in ("Open", "Close"):
            va, vh = num(a[k]), num(h[k])
            if np.isnan(va) or np.isnan(vh): r[f"{k.lower()}_spread"] = r[f"{k.lower()}_total"] = np.nan; continue
            if va > vh: tot, sp = va, -vh      # home row holds the spread -> home favored
            else: tot, sp = vh, va             # away row holds the spread -> away favored (home +sp)
            if tot < 80 or abs(sp) > 60: tot = sp = np.nan
            r[f"{k.lower()}_spread"], r[f"{k.lower()}_total"] = sp, tot   # home perspective: negative = home favored
        rows.append(r)
G = pd.DataFrame(rows); G = G[G.home_pts.notna() & G.away_pts.notna()]
G.to_csv(os.path.join(W, "ncaab", "data", "sbr_games.csv"), index=False)
print(f"{len(G)} games ({bad} malformed pairs skipped); by season {G.groupby('season').size().to_dict()}")
print("with open+close spread:", int(G[["open_spread", "close_spread"]].notna().all(axis=1).sum()), " totals:", int(G[["open_total", "close_total"]].notna().all(axis=1).sum()))
m = G.home_pts - G.away_pts; k = G.close_spread.notna()
print(f"sanity: home favorite (close) wins {((m > 0) == (G.close_spread < 0))[k & (G.close_spread != 0)].mean():.1%}; RMSE close spread {np.sqrt(np.mean((m[k] + G.close_spread[k]) ** 2)):.2f}, open {np.sqrt(np.mean((m[k] + G.open_spread[k]) ** 2)):.2f}")
