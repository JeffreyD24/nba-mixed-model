"""
Backtest: Kalshi GDP contracts ("Above X%" on BEA's advance estimate of real GDP growth) vs the Atlanta Fed's GDPNow.
Same method as backtest_cpi.py: GDPNow from the day before each snapshot, turned into a probability with GDPNow's own past
misses at the same distance from the release (walk-forward, quarters already released), BEA rounding to 0.1, paper trades at
5%+ expected value after Kalshi's taker fee.
  python econ/backtest_gdp.py   -> econ/results/gdp_trades.csv, gdp_markets.csv
"""
import os, re
import numpy as np, pandas as pd
from backtest_cpi import kalshi_fee, strike, r1, HORIZONS_H, EDGE, PRICE_RANGE, MAX_SPREAD, D, OUT

MIN_HISTORY = 16


def main():
    x = pd.ExcelFile(os.path.join(D, "gdpnow.xlsx"))
    TA = pd.concat([x.parse("TrackingDeepArchives"), x.parse("TrackingArchives")], ignore_index=True)
    TA = TA[["Forecast Date", "Quarter being forecasted", "GDP Nowcast"]].dropna()
    TA.columns = ["date", "quarter", "nowcast"]; TA["date"] = pd.to_datetime(TA.date); TA["quarter"] = pd.to_datetime(TA.quarter)
    TA = TA.drop_duplicates(["date", "quarter"], keep="last").sort_values("date")
    TR = x.parse("TrackRecord").iloc[:, :4]; TR.columns = ["quarter", "final_nowcast", "advance", "release"]
    TR = TR.dropna(subset=["quarter", "advance"]); TR["quarter"] = pd.to_datetime(TR.quarter); TR["release"] = pd.to_datetime(TR.release)
    NC = {q: g.set_index("date").nowcast for q, g in TA.groupby("quarter")}

    M = pd.read_csv(os.path.join(D, "kalshi_markets.csv")); M = M[M.series == "KXGDP"].copy()
    M["strike"] = M.yes_sub_title.map(strike)
    M["close"] = pd.to_datetime(M.close_time, utc=True, format="ISO8601").dt.tz_convert("America/New_York").dt.tz_localize(None)
    M["settled"] = pd.to_numeric(M.expiration_value.astype(str).str.replace("%", ""), errors="coerce")
    M = M.dropna(subset=["strike", "settled"])
    M["yes_won"] = M.settled > M.strike + 1e-9
    # which quarter: the one released within a week of the market's close (BEA moved some releases, e.g. Feb 2026)
    def quarter_for(t):
        d = (TR.release - t.normalize()).abs()
        return TR.quarter[d.idxmin()] if d.min() <= pd.Timedelta(days=8) else pd.NaT
    M["quarter"] = M.close.map(quarter_for)
    M = M.dropna(subset=["quarter"])
    H = pd.read_csv(os.path.join(D, "kalshi_hourly.csv.gz"))
    H = H[H.ticker.isin(M.ticker)]
    H["t"] = pd.to_datetime(H.ts, unit="s", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    Hg = dict(tuple(H.sort_values("t").groupby("ticker")))
    rel = dict(zip(TR.quarter, TR.release)); adv = dict(zip(TR.quarter, TR.advance))
    rows = []
    for r in M.itertuples():
        nc = NC.get(r.quarter); h = Hg.get(r.ticker)
        if nc is None or h is None: continue
        for hb in HORIZONS_H:
            snap = r.close - pd.Timedelta(hours=hb)
            q = h[(h.t <= snap) & (h.t > snap - pd.Timedelta(hours=4))]
            if not len(q): continue
            q = q.iloc[-1]; bid, ask = q.yes_bid, q.yes_ask
            if pd.isna(bid) or pd.isna(ask) or ask <= 0 or bid >= 1: continue
            ncv = nc[nc.index <= snap.normalize() - pd.Timedelta(days=1)]
            if not len(ncv): continue
            now = float(ncv.iloc[-1]); days_left = (r.close.normalize() - ncv.index[-1]).days
            errs = []
            for q2, n2 in NC.items():
                if q2 not in rel or rel[q2] >= snap or q2 >= r.quarter: continue
                xx = n2[n2.index <= rel[q2] - pd.Timedelta(days=days_left)]
                if len(xx): errs.append(adv[q2] - float(xx.iloc[-1]))
            if len(errs) < MIN_HISTORY: continue
            p = min(max(float(np.mean(r1(now + np.array(errs)) > r.strike + 1e-9)), 0.005), 0.995)
            rows.append(dict(ticker=r.ticker, quarter=str(r.quarter.date()), strike=r.strike, hours_before=hb, bid=bid, ask=ask,
                             mid=(bid + ask) / 2, spread=ask - bid, nowcast=round(now, 2), n_errs=len(errs), model_p=round(p, 3),
                             yes_won=bool(r.yes_won), settled=r.settled))
    X = pd.DataFrame(rows); X.to_csv(os.path.join(OUT, "gdp_markets.csv"), index=False)
    print(f"{len(X)} snapshots, {X.quarter.nunique()} quarters, {X.ticker.nunique()} contracts")
    ok = X[(X.spread <= MAX_SPREAD) & X.mid.between(*PRICE_RANGE)]
    print("Brier (lower is better):")
    for hb, g in ok.groupby("hours_before"):
        y = g.yes_won.astype(float)
        print(f"  {hb:>3}h: n={len(g):3d}  market {np.mean((g.mid - y) ** 2):.4f}  GDPNow model {np.mean((g.model_p - y) ** 2):.4f}")
    T = []
    for r in ok.itertuples():
        c_yes = r.ask + kalshi_fee(r.ask); c_no = (1 - r.bid) + kalshi_fee(1 - r.bid)
        ev_yes = (r.model_p - c_yes) / c_yes; ev_no = ((1 - r.model_p) - c_no) / c_no
        if ev_yes >= EDGE and ev_yes >= ev_no: side, cost, win = "yes", c_yes, r.yes_won
        elif ev_no >= EDGE: side, cost, win = "no", c_no, not r.yes_won
        else: continue
        T.append(dict(quarter=r.quarter, ticker=r.ticker, hours_before=r.hours_before, side=side, cost=cost, won=win,
                      profit=(1 - cost) if win else -cost, ev=max(ev_yes, ev_no)))
    T = pd.DataFrame(T); T.to_csv(os.path.join(OUT, "gdp_trades.csv"), index=False)
    print("Paper trades:")
    for hb, g in T.groupby("hours_before"):
        print(f"  {hb:>3}h: {len(g):3d} trades in {g.quarter.nunique():2d} quarters, won {g.won.mean():.0%}, "
              f"return {g.profit.sum() / g.cost.sum():+.1%}, EV claimed {g.ev.mean():+.0%}")
    print(f"  all: {len(T)} trades, return {T.profit.sum() / T.cost.sum():+.1%}")


if __name__ == "__main__":
    main()
