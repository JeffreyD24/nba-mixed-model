"""Exchange history downloads (Nov 5, 2026; betting-goals SHARP_MONEY.md). Free public APIs, run from GitHub Actions.
  Kalshi:     python sharp/exchange_history.py WORKDIR kalshi --series KXNBAGAME [--max-events N]
              -> sharp/data/kalshi/{series}_markets.csv.gz (every settled market: event, team, result, times)
                 sharp/data/kalshi/{series}_candles.csv.gz (hourly candles per market: yes bid/ask close, price, volume, open interest)
  Polymarket: python sharp/exchange_history.py WORKDIR poly --series 10345 [--max-events N]
              -> sharp/data/poly/{series}_markets.csv.gz (closed game events and their markets, outcomes, winner)
                 sharp/data/poly/{series}_trades.csv.gz (every trade: wallet, side, outcome, size, price, time)
Settled Kalshi markets before /historical/cutoff are read from the historical tier."""
import os, sys, json, time, urllib.request, urllib.error, urllib.parse
import pandas as pd
W = os.path.abspath(sys.argv[1]); SRC = sys.argv[2]; ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
SER = ARG("--series"); MAXE = int(ARG("--max-events", "100000"))
def get(u, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "research-script", "Accept": "application/json"}), timeout=40) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 * (i + 1)); continue
            if e.code in (400, 404): return {"_error": e.code}
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return {"_error": "failed"}
def save(df, name):
    d = os.path.join(W, "sharp", "data", SRC); os.makedirs(d, exist_ok=True); p = os.path.join(d, name)
    df.to_csv(p, index=False, compression="gzip"); print("saved", p, len(df), flush=True)
if SRC == "kalshi":
    K = "https://api.elections.kalshi.com/trade-api/v2"
    cut = pd.Timestamp(get(f"{K}/historical/cutoff").get("market_settled_ts", "2000-01-01"))
    evs, cur = [], ""
    while len(evs) < MAXE:
        d = get(f"{K}/events?series_ticker={SER}&status=settled&limit=200&with_nested_markets=true" + (f"&cursor={cur}" if cur else "")); time.sleep(0.3)
        evs += d.get("events", []); cur = d.get("cursor")
        if not cur or not d.get("events"): break
    evs = evs[:MAXE]; mk, cd = [], []
    for i, e in enumerate(evs):
        for m in e.get("markets") or []:
            mk.append(dict(event=e["event_ticker"], title=e.get("title"), sub=e.get("sub_title"), ticker=m["ticker"], yes_sub=m.get("yes_sub_title"),
                           strike=m.get("floor_strike"), result=m.get("result"), open_time=m.get("open_time"), close_time=m.get("close_time"),
                           volume=m.get("volume_fp") or m.get("volume")))
            ct = pd.Timestamp(m.get("close_time") or m.get("expiration_time")); ot = pd.Timestamp(m.get("open_time") or (ct - pd.Timedelta(days=7)))
            base = f"{K}/historical/markets/{m['ticker']}" if ct < cut else f"{K}/series/{SER}/markets/{m['ticker']}"
            c = get(f"{base}/candlesticks?start_ts={int(ot.timestamp())}&end_ts={int(ct.timestamp()) + 3600}&period_interval=60"); time.sleep(0.12)
            for k in c.get("candlesticks", []):
                yb, ya, pr = k.get("yes_bid") or {}, k.get("yes_ask") or {}, k.get("price") or {}
                cd.append(dict(ticker=m["ticker"], ts=k.get("end_period_ts"), bid=yb.get("close_dollars", yb.get("close")), ask=ya.get("close_dollars", ya.get("close")),
                               price=pr.get("close_dollars", pr.get("close")), volume=k.get("volume_fp", k.get("volume")), oi=k.get("open_interest_fp", k.get("open_interest"))))
        if i % 100 == 0: print(SER, i, len(evs), "candles", len(cd), flush=True)
    save(pd.DataFrame(mk), f"{SER}_markets.csv.gz"); save(pd.DataFrame(cd), f"{SER}_candles.csv.gz")
elif SRC == "poly":
    # Fixed Nov 5, 2026 (probe-poly.yml): v2 trades take condition=, cursor paging, taker_only=false returns both sides of every fill.
    # One trades file per month of game start, so files stay small and a timed-out job resumes where it stopped.
    G, D = "https://gamma-api.polymarket.com", "https://data-api.polymarket.com/v2"
    T0, BUDGET = time.time(), float(ARG("--minutes", "320")) * 60
    evs, off = [], 0
    while len(evs) < MAXE:
        d = get(f"{G}/events?series_id={SER}&closed=true&limit=100&offset={off}&order=startDate&ascending=true"); time.sleep(0.2)
        if not isinstance(d, list) or not d: break
        evs += d; off += 100
    evs = evs[:MAXE]; mk = []
    for e in evs:
        for m in e.get("markets") or []:
            try: outs, prices = json.loads(m.get("outcomes") or "[]"), json.loads(m.get("outcomePrices") or "[]")
            except Exception: outs, prices = [], []
            mk.append(dict(event_id=e.get("id"), event=e.get("title"), slug=e.get("slug"), start=e.get("startDate"), game_start=m.get("gameStartTime") or e.get("endDate"),
                           condition_id=m.get("conditionId"), question=m.get("question"), market_type=m.get("sportsMarketType") or m.get("groupItemTitle"),
                           line=m.get("line"), outcomes="|".join(outs), final_prices="|".join(map(str, prices)), volume=m.get("volumeNum") or m.get("volume")))
    mk = pd.DataFrame(mk); save(mk, f"{SER}_markets.csv.gz")
    mk["month"] = pd.to_datetime(mk.game_start, utc=True, errors="coerce", format="mixed").dt.strftime("%Y-%m").fillna("unknown")
    outdir = os.path.join(W, "sharp", "data", SRC)
    for mon, grp in mk.groupby("month"):
        name = f"{SER}_trades_{mon}.csv.gz"
        if os.path.exists(os.path.join(outdir, name)) and MAXE >= 100000: print("have", name); continue
        if time.time() - T0 > BUDGET: print("TIME BUDGET reached before", mon, "- rerun to resume"); break
        tr, first = [], True
        for cid in grp.condition_id.dropna().unique():
            cursor, seen = None, 0
            while True:
                t = get(f"{D}/trades?condition={cid}&limit=1000&taker_only=false" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")); time.sleep(0.05)
                rows = t.get("data", []) if isinstance(t, dict) else []
                for x in rows:
                    tr.append((cid, x.get("proxy_wallet"), x.get("side"), x.get("outcome_index"), x.get("size"), x.get("price"), x.get("timestamp"), x.get("transaction_hash")))
                seen += len(rows); pg = (t.get("pagination") or {}) if isinstance(t, dict) else {}; cursor = pg.get("next_cursor") if pg.get("has_more") else None
                if not rows or not cursor or cursor in ("LTE=", "") or seen >= 500000: break
        df = pd.DataFrame(tr, columns=["condition_id", "wallet", "side", "outcome_index", "size", "price", "ts", "tx"]).drop_duplicates()
        save(df.drop(columns="tx"), name); print(SER, mon, "markets", grp.condition_id.nunique(), "fills", len(df), "minutes", round((time.time() - T0) / 60), flush=True)
