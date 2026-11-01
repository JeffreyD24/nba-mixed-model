"""
Backtest: Kalshi monthly CPI contracts (headline and core, month-over-month) vs the Cleveland Fed inflation nowcast.

For every past release, at several times before Kalshi closes trading (7 days, 3 days, 1 day, 6 hours, 1 hour):
  - the market: Kalshi's best bid/ask for each "Above X%" contract (hourly prices from econ/data/kalshi_hourly.csv.gz)
  - the model: the Cleveland Fed nowcast published the day before, turned into a probability using the nowcast's own
    past misses at the same distance from the release (walk-forward: only months already released), with the BLS
    rounding to 0.1 built in
  - a paper trade when the model's expected value after Kalshi's taker fee is at least EDGE (5%) of the cost
Graded on Kalshi's settlement value. No lookahead: nowcasts are from the day before the snapshot, misses only from
months released before it.
  python econ/backtest_cpi.py            -> econ/results/cpi_trades.csv, cpi_markets.csv, printed summary
"""
import os, re, json, gzip
import numpy as np, pandas as pd

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"); os.makedirs(OUT, exist_ok=True)
HORIZONS_H = [168, 72, 24, 6, 1]
EDGE = 0.05                     # expected value per dollar needed for a paper trade
PRICE_RANGE = (0.05, 0.95)      # skip contracts priced like near-certainties (tiny payoffs, stale quotes)
MAX_SPREAD = 0.10               # skip contracts whose bid/ask are more than 10 cents apart (no real market)
MIN_HISTORY = 24                # months of past nowcast misses needed before the model trades
MON = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
SERIES = {"KXCPI": "CPI Inflation", "KXCPICORE": "Core CPI Inflation"}


def kalshi_fee(p):
    return 0.07 * p * (1 - p)           # taker fee per contract (Kalshi's general schedule, before rounding up per order)


def nowcasts():
    """{(series name, 'YYYY-MM'): (DataFrame date->nowcast, actual unrounded, last nowcast date)}"""
    out = {}
    for e in json.loads(gzip.open(os.path.join(D, "cleveland_nowcast_month.json.gz")).read()):
        ty, tm = map(int, e["chart"]["subcaption"].split("-"))
        labels = [c["label"] for c in e["categories"][0]["category"]]
        dates = []
        for lb in labels:                    # a few labels mark releases ("PCE Jul") instead of dates
            m_ = re.fullmatch(r"(\d\d)/(\d\d)", lb.strip())
            if not m_: dates.append(pd.NaT); continue
            mm, dd = int(m_.group(1)), int(m_.group(2))
            yy = ty if mm >= tm else ty + 1
            dates.append(pd.Timestamp(yy, mm, dd))
        ser = {s["seriesname"]: [float(v["value"]) if v.get("value") not in ("", None) else np.nan for v in s["data"]] for s in e["dataset"]}
        for name in SERIES.values():
            if name not in ser: continue
            v = ser[name][:len(dates)]
            nc = pd.Series(v, index=dates[:len(v)])
            nc = nc[nc.index.notna()].dropna()
            nc = nc[~nc.index.duplicated(keep="last")].sort_index()
            act = [x for x in ser.get("Actual " + name, []) if not np.isnan(x)]
            out[(name, f"{ty}-{tm:02d}")] = (nc, act[-1] if act else np.nan)
    return out


def event_month(ev):
    m = re.search(r"-(\d\d)([A-Z]{3})$", ev)
    return f"20{m.group(1)}-{MON[m.group(2)]:02d}" if m else None


def strike(sub):
    m = re.search(r"(-?\d+(?:\.\d+)?)%", str(sub))
    return float(m.group(1)) if m else np.nan


def r1(x):
    return np.round(np.asarray(x) + 1e-9, 1)


def main():
    NC = nowcasts()
    M = pd.read_csv(os.path.join(D, "kalshi_markets.csv"))
    M = M[M.series.isin(SERIES)].copy()
    M["month"] = M.event_ticker.map(event_month); M["strike"] = M.yes_sub_title.map(strike)
    M["close"] = pd.to_datetime(M.close_time, utc=True, format="ISO8601").dt.tz_convert("America/New_York").dt.tz_localize(None)
    M["settled"] = pd.to_numeric(M.expiration_value.astype(str).str.replace("%", ""), errors="coerce")
    M = M.dropna(subset=["month", "strike", "settled"])
    M["yes_won"] = M.settled > M.strike + 1e-9
    H = pd.read_csv(os.path.join(D, "kalshi_hourly.csv.gz"))
    H["t"] = pd.to_datetime(H.ts, unit="s", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    H = H.sort_values("t"); Hg = dict(tuple(H.groupby("ticker")))

    # release-day misses for every month: nowcast k days before the release vs the actual
    rel = {}
    for (name, mo), (nc, act) in NC.items():
        rel[(name, mo)] = nc.index.max() if len(nc) else None
    agree = []
    rows = []
    for r in M.itertuples():
        name = SERIES[r.series]
        if (name, r.month) not in NC: continue
        nc, act = NC[(name, r.month)]
        if not np.isnan(act): agree.append(float(r1(act)) == round(r.settled, 1))
        h = Hg.get(r.ticker)
        if h is None: continue
        for hb in HORIZONS_H:
            snap = r.close - pd.Timedelta(hours=hb)
            q = h[(h.t <= snap) & (h.t > snap - pd.Timedelta(hours=4))]
            if not len(q): continue
            q = q.iloc[-1]; bid, ask = q.yes_bid, q.yes_ask
            if pd.isna(bid) or pd.isna(ask) or ask <= 0 or bid >= 1: continue
            day = snap.normalize() - pd.Timedelta(days=1)
            ncv = nc[nc.index <= day]
            if not len(ncv): continue
            now = float(ncv.iloc[-1]); days_left = (r.close.normalize() - ncv.index[-1]).days
            # past misses at the same distance from the release, only months released before this snapshot
            errs = []
            for (n2, mo2), (nc2, act2) in NC.items():
                if n2 != name or np.isnan(act2) or mo2 >= r.month: continue
                rd = rel[(n2, mo2)]
                if rd is None or rd >= snap: continue
                x = nc2[nc2.index <= rd - pd.Timedelta(days=days_left)]
                if len(x): errs.append(act2 - float(x.iloc[-1]))
            if len(errs) < MIN_HISTORY: continue
            p = float(np.mean(r1(now + np.array(errs)) > r.strike + 1e-9))
            p = min(max(p, 0.005), 0.995)
            rows.append(dict(series=r.series, month=r.month, ticker=r.ticker, strike=r.strike, hours_before=hb, snap=snap,
                             bid=bid, ask=ask, mid=(bid + ask) / 2, spread=ask - bid, nowcast=round(now, 3), days_left=days_left,
                             n_errs=len(errs), model_p=round(p, 3), yes_won=bool(r.yes_won), settled=r.settled,
                             volume=r.volume_fp))
    X = pd.DataFrame(rows)
    X.to_csv(os.path.join(OUT, "cpi_markets.csv"), index=False)
    print(f"Cleveland actual (rounded) matches Kalshi settlement: {np.mean(agree):.1%} of {len(agree)} markets")
    print(f"{len(X)} market snapshots, {X.month.nunique()} months, {X.ticker.nunique()} contracts")

    # accuracy: market mid vs model (only two-sided markets inside the price range)
    ok = X[(X.spread <= MAX_SPREAD) & X.mid.between(*PRICE_RANGE)]
    y = ok.yes_won.astype(float)
    print("\nAccuracy (Brier score, lower is better), contracts priced 5-95c with a real market:")
    for hb, g in ok.groupby("hours_before"):
        yy = g.yes_won.astype(float)
        print(f"  {hb:>3}h before: n={len(g):4d}  market {np.mean((g.mid - yy) ** 2):.4f}  nowcast model "
              f"{np.mean((g.model_p - yy) ** 2):.4f}  50/50 blend {np.mean(((g.mid + g.model_p) / 2 - yy) ** 2):.4f}")

    # paper trades
    T = []
    for r in ok.itertuples():
        c_yes = r.ask + kalshi_fee(r.ask); c_no = (1 - r.bid) + kalshi_fee(1 - r.bid)
        ev_yes = (r.model_p - c_yes) / c_yes; ev_no = ((1 - r.model_p) - c_no) / c_no
        if ev_yes >= EDGE and ev_yes >= ev_no:
            side, cost, win = "yes", c_yes, r.yes_won
        elif ev_no >= EDGE:
            side, cost, win = "no", c_no, not r.yes_won
        else:
            continue
        T.append(dict(**r._asdict(), side=side, cost=round(cost, 4), ev=round(max(ev_yes, ev_no), 3), won=win,
                      profit=round((1 - cost) if win else -cost, 4)))
    T = pd.DataFrame(T).drop(columns=["Index"])
    T.to_csv(os.path.join(OUT, "cpi_trades.csv"), index=False)
    print(f"\nPaper trades (EV >= {EDGE:.0%} after fees, 1 contract each):")
    for hb, g in T.groupby("hours_before"):
        print(f"  {hb:>3}h before: {len(g):4d} trades in {g.month.nunique():2d} months, won {g.won.mean():.1%}, "
              f"profit ${g.profit.sum():+.2f} on ${g.cost.sum():.2f} risked ({g.profit.sum() / g.cost.sum():+.1%}), "
              f"avg EV claimed {g.ev.mean():+.1%}")
    print("\nBy series (all horizons):")
    for s, g in T.groupby("series"):
        print(f"  {s}: {len(g)} trades, {g.month.nunique()} months, {g.profit.sum() / g.cost.sum():+.1%} return, won {g.won.mean():.1%}")
    print("\nBy year (all horizons):")
    T["year"] = T.month.str[:4]
    for yv, g in T.groupby("year"):
        print(f"  {yv}: {len(g):4d} trades, {g.profit.sum() / g.cost.sum():+.1%} return, won {g.won.mean():.1%}")
    print("\nBy side and price:")
    T["band"] = pd.cut(T.cost, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    for (sd, b), g in T.groupby(["side", "band"], observed=True):
        print(f"  {sd:3s} cost {str(b):11s}: {len(g):4d} trades, {g.profit.sum() / g.cost.sum():+.1%} return, won {g.won.mean():.1%}")
    # month-level: one month's contracts are tied together, so count months that made money
    mm = T[T.hours_before == 24].groupby("month").profit.sum()
    print(f"\n24h-before trades by month: {int((mm > 0).sum())} months up, {int((mm < 0).sum())} down, total ${mm.sum():+.2f}")


if __name__ == "__main__":
    main()
