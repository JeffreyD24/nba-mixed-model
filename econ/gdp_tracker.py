"""
GDP paper tracker (background research, never trades). Runs every 6 hours on GitHub (econ-gdp.yml).

Each run:
  1. Kalshi's open GDP contracts ("Above X%" on BEA's advance estimate) with best bid / ask (public API, no key).
  2. The Atlanta Fed's latest GDPNow for that quarter (public workbook).
  3. A probability for each contract from GDPNow plus GDPNow's own past misses at the same number of days before the
     release (all past quarters, BEA rounding to 0.1). Same method as econ/backtest_gdp.py.
  4. Saves every contract's price and model number (econ/live/gdp_snapshots.csv).
  5. FIXED RULE (same as the backtest; don't change it after seeing results): a paper trade of 1 contract when expected value
     after Kalshi's taker fee is 5%+, the price is 5-95 cents and the bid/ask spread is 10 cents or less. At most one trade
     per contract in each window before the release (7 days, 3 days, 1 day, 6 hours), like the backtest's checkpoints.
  6. Grades trades once Kalshi settles them and rewrites econ/live/REPORT.md.
  python econ/gdp_tracker.py [--offline]   (--offline: use econ/data files instead of the internet, for testing)
"""
import os, sys, io, json, time, urllib.request, urllib.parse
import datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.join(HERE, "live"); os.makedirs(LIVE, exist_ok=True)
K = "https://external-api.kalshi.com/trade-api/v2"
GDPNOW = "https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/research-and-data/data/gdpnow/GDPTrackingModelDataAndForecasts.xlsx"
ET = ZoneInfo("America/New_York")
NOW = pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None))
EDGE, PRICE_RANGE, MAX_SPREAD, MIN_HISTORY = 0.05, (0.05, 0.95), 0.10, 16
WINDOWS_H = [168, 72, 24, 6]
OFFLINE = "--offline" in sys.argv
SNAP, PAPER, REPORT = (os.path.join(LIVE, f) for f in ("gdp_snapshots.csv", "gdp_paper.csv", "REPORT.md"))


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (econ research tracker)"})
            with urllib.request.urlopen(req, timeout=60) as r: return r.read()
        except Exception as e:
            err = e; time.sleep(3 * (i + 1))
    print("Fetch failed:", url[:90], type(err).__name__); return None


def num(x):
    try: return float(str(x).replace(",", "").replace("%", ""))
    except (TypeError, ValueError): return np.nan


def fee(p): return 0.07 * p * (1 - p)        # Kalshi taker fee per contract
def r1(x): return np.round(np.asarray(x) + 1e-9, 1)


def gdpnow():
    if OFFLINE: b = open(os.path.join(HERE, "data", "gdpnow.xlsx"), "rb").read()
    else: b = get(GDPNOW)
    if not b: return None, None
    x = pd.ExcelFile(io.BytesIO(b))
    TA = pd.concat([x.parse("TrackingDeepArchives"), x.parse("TrackingArchives")], ignore_index=True)
    TA = TA[["Forecast Date", "Quarter being forecasted", "GDP Nowcast"]].dropna()
    TA.columns = ["date", "quarter", "nowcast"]; TA["date"] = pd.to_datetime(TA.date); TA["quarter"] = pd.to_datetime(TA.quarter)
    TA = TA.drop_duplicates(["date", "quarter"], keep="last").sort_values("date")
    TR = x.parse("TrackRecord").iloc[:, :4]; TR.columns = ["quarter", "final_nowcast", "advance", "release"]
    TR = TR.dropna(subset=["quarter", "advance"]); TR["quarter"] = pd.to_datetime(TR.quarter); TR["release"] = pd.to_datetime(TR.release)
    return TA, TR


def open_markets():
    if OFFLINE:
        M = pd.read_csv(os.path.join(HERE, "data", "kalshi_markets.csv")); M = M[M.series == "KXGDP"].tail(8).copy()
        M["yes_bid"], M["yes_ask"] = 0.40, 0.48; return M
    b = get(K + "/markets?" + urllib.parse.urlencode(dict(series_ticker="KXGDP", status="open", limit=200)))
    if not b: return pd.DataFrame()
    rows = []
    for m in json.loads(b).get("markets", []):
        rows.append(dict(ticker=m["ticker"], event_ticker=m["event_ticker"], yes_sub_title=m.get("yes_sub_title"),
                         close_time=m.get("close_time"), yes_bid=num(m.get("yes_bid_dollars", m.get("yes_bid"))),
                         yes_ask=num(m.get("yes_ask_dollars", m.get("yes_ask"))), volume=num(m.get("volume_fp", m.get("volume"))),
                         open_interest=num(m.get("open_interest_fp"))))
    return pd.DataFrame(rows)


def settlement(ticker):
    b = get(K + f"/markets/{ticker}")
    if not b: return None
    m = json.loads(b).get("market", {})
    if m.get("status") not in ("settled", "finalized") and not m.get("result"): return None
    return m.get("result"), m.get("expiration_value")


def main():
    TA, TR = gdpnow()
    M = open_markets()
    if TA is None or not len(M):
        print("GDP tracker: no data this run (GDPNow or Kalshi unavailable)."); grade(); return
    M["strike"] = M.yes_sub_title.str.extract(r"(-?\d+(?:\.\d+)?)%")[0].astype(float)
    M["close"] = pd.to_datetime(M.close_time, utc=True, format="ISO8601").dt.tz_convert("America/New_York").dt.tz_localize(None)
    NC = {q: g.set_index("date").nowcast for q, g in TA.groupby("quarter")}
    rel = dict(zip(TR.quarter, TR.release)); adv = dict(zip(TR.quarter, TR.advance))
    snaps, trades = [], []
    P = pd.read_csv(PAPER) if os.path.exists(PAPER) else pd.DataFrame(columns=["ticker", "window_h"])
    have = set(zip(P.ticker, P.window_h.astype(int))) if len(P) else set()
    for r in M.itertuples():
        if pd.isna(r.strike) or r.close <= NOW: continue
        # the quarter being released: the latest quarter that ended before the contract closes, released ~30 days later
        qs = [q for q in NC if q < r.close and (r.close - q).days <= 75]
        if not qs: continue
        q = max(qs); nc = NC[q]
        ncv = nc[nc.index <= NOW.normalize()]
        if not len(ncv): continue
        now = float(ncv.iloc[-1]); days_left = (r.close.normalize() - ncv.index[-1]).days
        errs = []
        for q2, n2 in NC.items():
            if q2 not in rel or rel[q2] >= NOW or q2 >= q: continue
            xx = n2[n2.index <= rel[q2] - pd.Timedelta(days=days_left)]
            if len(xx): errs.append(adv[q2] - float(xx.iloc[-1]))
        if len(errs) < MIN_HISTORY: continue
        p = min(max(float(np.mean(r1(now + np.array(errs)) > r.strike + 1e-9)), 0.005), 0.995)
        bid, ask = r.yes_bid, r.yes_ask
        hours_left = (r.close - NOW).total_seconds() / 3600
        c_yes = ask + fee(ask) if ask > 0 else np.nan; c_no = (1 - bid) + fee(1 - bid) if bid < 1 else np.nan
        ev_yes = (p - c_yes) / c_yes if c_yes == c_yes else np.nan; ev_no = ((1 - p) - c_no) / c_no if c_no == c_no else np.nan
        snaps.append(dict(seen_at_et=str(NOW)[:16], quarter=str(q.date()), ticker=r.ticker, strike=r.strike, close_et=str(r.close)[:16],
                          hours_left=round(hours_left, 1), yes_bid=bid, yes_ask=ask, volume=r.volume, gdpnow=round(now, 2),
                          gdpnow_date=str(ncv.index[-1].date()), model_p=round(p, 3), ev_yes=round(ev_yes, 3), ev_no=round(ev_no, 3)))
        win = next((w for w in sorted(WINDOWS_H) if hours_left <= w), None)
        if win is None or (r.ticker, win) in have: continue
        mid, spread = (bid + ask) / 2, ask - bid
        if not (PRICE_RANGE[0] <= mid <= PRICE_RANGE[1]) or spread > MAX_SPREAD: continue
        if ev_yes >= EDGE and ev_yes >= (ev_no if ev_no == ev_no else -9): side, cost, ev = "yes", c_yes, ev_yes
        elif ev_no >= EDGE: side, cost, ev = "no", c_no, ev_no
        else: continue
        trades.append(dict(logged_at_et=str(NOW)[:16], quarter=str(q.date()), ticker=r.ticker, strike=r.strike, window_h=win,
                           hours_left=round(hours_left, 1), side=side, price=ask if side == "yes" else round(1 - bid, 4),
                           cost=round(cost, 4), model_p=round(p, 3), gdpnow=round(now, 2), ev=round(ev, 3),
                           result=None, settled_value=None, won=None, profit=None))
    if snaps:
        S = pd.DataFrame(snaps); S.to_csv(SNAP, mode="a", header=not os.path.exists(SNAP), index=False)
    if trades:
        P = pd.concat([P, pd.DataFrame(trades)], ignore_index=True); P.to_csv(PAPER, index=False)
    print(f"GDP tracker: {len(snaps)} contracts priced, {len(trades)} new paper trades.")
    for t in trades: print("  PAPER:", t["ticker"], t["side"], f"at {t['price']:.2f}", f"model {t['model_p']:.0%}", f"EV {t['ev']:+.0%}")
    grade()


def grade():
    if not os.path.exists(PAPER): report(None); return
    P = pd.read_csv(PAPER)
    for c in ("result", "settled_value", "won"): P[c] = P[c].astype(object)
    if not OFFLINE:
        for i in P.index[P.result.isna()]:
            s = settlement(P.at[i, "ticker"])
            if not s or s[0] not in ("yes", "no"): continue
            P.at[i, "result"], P.at[i, "settled_value"] = s
            won = (s[0] == P.at[i, "side"]); P.at[i, "won"] = won
            P.at[i, "profit"] = round((1 - P.at[i, "cost"]) if won else -P.at[i, "cost"], 4)
            time.sleep(0.2)
    P.to_csv(PAPER, index=False); report(P)


def report(P):
    lines = ["# GDP paper tracker", "", f"Updated {NOW:%Y-%m-%d %H:%M} ET. Background research: Kalshi GDP contracts vs the Atlanta Fed's "
             "GDPNow, fixed rule from `econ/backtest_gdp.py` (5%+ value after fees). Paper only.", "",
             "Backtest when the tracker started (16 quarters, 2022-2026): 139 trades, +19.3% return, but a 90% range of -15% to +43% "
             "and one quarter made 59% of the profit. Needs many more quarters before it means anything.", ""]
    if P is None or not len(P):
        lines.append("No paper trades yet."); open(REPORT, "w").write("\n".join(lines) + "\n"); return
    g = P[P.won.notna()]
    lines += [f"Paper trades: {len(P)} ({len(g)} graded, {len(P) - len(g)} open).", ""]
    if len(g):
        g = g.assign(won=g.won.astype(str).isin(["True", "1", "1.0"]))
        lines += [f"Graded: won {g.won.mean():.0%}, profit ${g.profit.sum():+.2f} on ${g.cost.sum():.2f} risked "
                  f"({g.profit.sum() / g.cost.sum():+.1%}).", "", "| Quarter | Trades | Won | Profit | Return |", "|---|---|---|---|---|"]
        for q, x in g.groupby("quarter"):
            lines.append(f"| {q} | {len(x)} | {x.won.mean():.0%} | ${x.profit.sum():+.2f} | {x.profit.sum() / x.cost.sum():+.1%} |")
        lines += ["", "| Window before release | Trades | Won | Return |", "|---|---|---|---|"]
        for w, x in g.groupby("window_h"):
            lines.append(f"| {int(w)} h | {len(x)} | {x.won.mean():.0%} | {x.profit.sum() / x.cost.sum():+.1%} |")
    open(REPORT, "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
