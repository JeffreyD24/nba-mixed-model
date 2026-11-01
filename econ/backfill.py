"""
Economics history download (runs on GitHub; read-only public data, no keys).
  - Kalshi: every settled market in the economics series below (archive + recent), with hourly bid/ask/price for the
    15 days before each market closed  -> econ/data/kalshi_markets.csv, econ/data/kalshi_hourly.csv.gz
  - Cleveland Fed inflation nowcast history (raw chart files)                 -> econ/data/cleveland_nowcast_*.json.gz
  - Atlanta Fed GDPNow history                                                -> econ/data/gdpnow.xlsx
  python econ/backfill.py [--series KXCPI,KXCPICORE]
"""
import os, sys, json, gzip, time, urllib.request, urllib.parse
import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"); os.makedirs(OUT, exist_ok=True)
K = "https://external-api.kalshi.com/trade-api/v2"
SERIES = ["KXCPI", "KXCPICORE", "KXCPIYOY", "KXPAYROLLS", "KXU3", "KXFEDDECISION", "KXFED", "KXGDP"]
DAYS_BEFORE = 15


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (econ research tracker)"})
            with urllib.request.urlopen(req, timeout=40) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(3 * (i + 1)); continue
            if e.code == 404: return None
            time.sleep(2)
        except Exception:
            time.sleep(2)
    return None


def markets(series):
    rows = []
    for base, extra in ((K + "/historical/markets", {}), (K + "/markets", {"status": "settled"})):
        cur = ""
        for _ in range(50):
            q = dict(series_ticker=series, limit=1000, **extra)
            if cur: q["cursor"] = cur
            b = get(base + "?" + urllib.parse.urlencode(q))
            if not b: break
            d = json.loads(b); m = d.get("markets", [])
            for x in m: x["_archive"] = "historical" in base; x["_series"] = series
            rows += m; cur = d.get("cursor")
            if not cur or not m: break
            time.sleep(0.2)
    return rows


def f(x):
    try: return float(str(x).replace(",", ""))
    except (TypeError, ValueError): return None


def candles(m):
    ct = pd.Timestamp(m["close_time"]); ot = pd.Timestamp(m.get("open_time") or m["close_time"])
    start = max(ot, ct - pd.Timedelta(days=DAYS_BEFORE))
    q = f"start_ts={int(start.timestamp())}&end_ts={int(ct.timestamp())}&period_interval=60"
    path = (f"/historical/markets/{m['ticker']}/candlesticks?" if m["_archive"]
            else f"/series/{m['_series']}/markets/{m['ticker']}/candlesticks?") + q
    b = get(K + path)
    if not b: return []
    out = []
    for c in json.loads(b).get("candlesticks", []):
        def px(d, k):        # archive uses "close", live uses "close_dollars"
            d = d or {}; return f(d.get(k + "_dollars", d.get(k)))
        out.append(dict(ticker=m["ticker"], ts=c["end_period_ts"], yes_bid=px(c.get("yes_bid"), "close"),
                        yes_ask=px(c.get("yes_ask"), "close"), last=px(c.get("price"), "close"),
                        mean=px(c.get("price"), "mean"), volume=f(c.get("volume_fp", c.get("volume"))),
                        open_interest=f(c.get("open_interest_fp", c.get("open_interest")))))
    return out


def main():
    series = SERIES
    if "--series" in sys.argv: series = sys.argv[sys.argv.index("--series") + 1].split(",")
    allm = []
    for s in series:
        m = markets(s); print(f"{s}: {len(m)} markets"); allm += m
    keep = ["_series", "ticker", "event_ticker", "title", "yes_sub_title", "no_sub_title", "strike_type", "floor_strike",
            "cap_strike", "custom_strike", "open_time", "close_time", "expected_expiration_time", "occurrence_datetime",
            "expiration_value", "result", "settlement_value_dollars", "volume_fp", "volume", "open_interest_fp", "_archive"]
    M = pd.DataFrame([{k: (json.dumps(x.get(k)) if isinstance(x.get(k), dict) else x.get(k)) for k in keep} for x in allm])
    M = M.drop_duplicates("ticker", keep="last").rename(columns={"_series": "series", "_archive": "archive"})
    M.to_csv(os.path.join(OUT, "kalshi_markets.csv"), index=False)
    hp = os.path.join(OUT, "kalshi_hourly.csv.gz")
    done = set(pd.read_csv(hp).ticker) if os.path.exists(hp) else set()
    rows, t0 = [], time.time()
    todo = [x for x in allm if x["ticker"] not in done and (f(x.get("volume_fp")) or f(x.get("volume")) or 0) > 0]
    seen = set()
    for i, x in enumerate(todo):
        if x["ticker"] in seen: continue
        seen.add(x["ticker"]); rows += candles(x); time.sleep(0.08)
        if i % 200 == 0: print(f"  candles {i}/{len(todo)} ({time.time() - t0:.0f}s)")
    if rows:
        H = pd.DataFrame(rows)
        if os.path.exists(hp): H = pd.concat([pd.read_csv(hp), H], ignore_index=True)
        H.to_csv(hp, index=False, compression="gzip")
    print(f"hourly rows added: {len(rows)}")
    for name in ("month", "quarter", "year"):
        b = get(f"https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_{name}.json")
        if b: gzip.open(os.path.join(OUT, f"cleveland_nowcast_{name}.json.gz"), "wb").write(b); print("cleveland", name, len(b))
    b = get("https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/research-and-data/data/gdpnow/GDPTrackingModelDataAndForecasts.xlsx")
    if b: open(os.path.join(OUT, "gdpnow.xlsx"), "wb").write(b); print("gdpnow", len(b))


if __name__ == "__main__":
    main()
