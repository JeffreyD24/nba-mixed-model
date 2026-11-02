"""Where do the sharps bet, and can we follow them? NBA 2021-24, every snapshot of 10 books (The Odds API history).
Pinnacle is the sharp book (high limits, takes sharp action and moves first); DraftKings is where we bet.
  A. Lead-lag: when Pinnacle moves and DraftKings hasn't, does DraftKings follow? How fast?
  B. Follow the sharps: bet DraftKings when its line disagrees with Pinnacle's at the same moment (stale line)
  C. Does the close (the sharp consensus) beat the opener, and which book's opener is closest to it?
  python analysis/sharp_nba.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); SP = sys.argv[2] if len(sys.argv) > 2 else "nba"
O = pd.read_csv(os.path.join(W, "data", "odds_history", f"{SP}_snapshots.csv.gz"), parse_dates=["t", "tip"])
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))[["date", "home", "away", "home_pts", "away_pts"]]
O = O.merge(T, on=["date", "home", "away"], how="inner")
O["margin"] = O.home_pts - O.away_pts; O["pts"] = O.home_pts + O.away_pts
dec = lambda o: np.where(o > 0, 1 + o / 100, 1 + 100 / np.abs(o))
RETAIL = ["draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers"]
print(f"{O.event_id.nunique()} games with results")

# wide: one row per game x snapshot, a column per book
Wd = {m: O.pivot_table(index=["event_id", "t"], columns="book", values=m, aggfunc="first") for m in ("sp", "tot", "sp_px_h", "sp_px_a", "ov_px", "un_px")}
G = O.groupby("event_id")[["margin", "pts", "tip", "date"]].first()

def lead_lag(m, step):
    X = Wd[m][["pinnacle", "draftkings"]].dropna().reset_index().sort_values(["event_id", "t"])
    X["dp"] = X.groupby("event_id").pinnacle.diff(); X["dd"] = X.groupby("event_id").draftkings.diff()
    X["dt"] = X.groupby("event_id").t.diff().dt.total_seconds() / 60
    ev = X[(X.dp.abs() >= step) & (X.dd == 0) & (X.dt <= 75)]
    fol, mins = [], []
    for r in ev.itertuples():
        nx = X[(X.event_id == r.event_id) & (X.t > r.t) & (X.t <= r.t + pd.Timedelta(minutes=120))]
        mv = nx.draftkings - r.draftkings
        hit = mv[np.sign(mv) == np.sign(r.dp)]
        fol.append(len(hit) > 0); mins.append((nx.t[hit.index[0]] - r.t).total_seconds() / 60 if len(hit) else np.nan)
    # reverse: DraftKings moves, Pinnacle doesn't
    ev2 = X[(X.dd.abs() >= step) & (X.dp == 0) & (X.dt <= 75)]
    fol2 = []
    for r in ev2.itertuples():
        nx = X[(X.event_id == r.event_id) & (X.t > r.t) & (X.t <= r.t + pd.Timedelta(minutes=120))]
        mv = nx.pinnacle - r.pinnacle; fol2.append(bool((np.sign(mv) == np.sign(r.dd)).any()))
    print(f"  {m}: Pinnacle moved {step}+ and DraftKings didn't: {len(ev)} times; DraftKings followed within 2 h {np.mean(fol):.0%} "
          f"(median {np.nanmedian(mins):.0f} min). DraftKings moved first: {len(ev2)} times; Pinnacle followed {np.mean(fol2):.0%}")

print("\nA. Who moves first")
lead_lag("sp", 0.5); lead_lag("tot", 0.5)

print("\nB. Bet DraftKings when it disagrees with Pinnacle at the same moment (first time per game), at DraftKings' line and price")
res_rows = []
for m in ("sp", "tot"):
    X = Wd[m][["pinnacle", "draftkings"]].dropna().reset_index().join(G, on="event_id")
    pxh, pxa = Wd["sp_px_h" if m == "sp" else "ov_px"]["draftkings"], Wd["sp_px_a" if m == "sp" else "un_px"]["draftkings"]
    X = X.join(pxh.rename("px1"), on=["event_id", "t"]).join(pxa.rename("px2"), on=["event_id", "t"])
    X = X[X.t < X.tip - pd.Timedelta(minutes=5)]
    X["gap"] = X.draftkings - X.pinnacle                     # spread: + means Pinnacle likes home more; total: + means Pinnacle lower
    for k in (0.5, 1.0, 1.5, 2.0):
        s = X[X.gap.abs() >= k].sort_values("t").groupby("event_id").head(1)
        if m == "sp":
            side1 = s.gap > 0                                # bet home at DK
            r = np.where(side1, s.margin + s.draftkings, -(s.margin + s.draftkings)); px = np.where(side1, s.px1, s.px2)
        else:
            side1 = s.gap < 0                                # Pinnacle higher -> over at DK
            r = np.where(side1, s.pts - s.draftkings, s.draftkings - s.pts); px = np.where(side1, s.px1, s.px2)
        d = dec(px); u = np.where(r > 0, d - 1, np.where(r < 0, -1, 0))
        w, l = (r > 0).sum(), (r < 0).sum()
        hrs = ((s.tip - s.t).dt.total_seconds() / 3600).median()
        print(f"  {'spread' if m == 'sp' else 'total'} gap {k}+: {w + l} bets, won {w / max(w + l, 1):.1%}, {u.sum():+.1f}u at DK prices "
              f"(median {hrs:.1f} h before tip)")
        res_rows.append(dict(market=m, gap=k, bets=w + l, win=w / max(w + l, 1), units=u.sum()))

print("\nC. Which line is best? Mean absolute error vs the final result, same games")
for m, y in (("sp", "margin"), ("tot", "pts")):
    X = Wd[m].reset_index().join(G, on="event_id").sort_values("t")
    first = X.groupby("event_id").first(); last = X.groupby("event_id").last()
    yy = G[y]; sgn = -1 if m == "sp" else 1
    for b in ["pinnacle", "draftkings", "fanduel", "betonlineag", "bovada"]:
        e_o = (sgn * first[b] - yy).abs(); e_c = (sgn * last[b] - yy).abs()
        ok = e_o.notna() & e_c.notna()
        print(f"  {m} {b:12s}: opener MAE {e_o[ok].mean():.3f}, close MAE {e_c[ok].mean():.3f} ({ok.sum()} games)")
pd.DataFrame(res_rows).to_csv(os.path.join(W, "analysis", f"sharp_{SP}_follow.csv"), index=False)
