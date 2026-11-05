"""Exchange history downloads (Nov 5, 2026; betting-goals SHARP_MONEY.md). Free public APIs, run from GitHub Actions.
  Kalshi:     python sharp/exchange_history.py WORKDIR kalshi --series KXNBAGAME [--max-events N]
              -> sharp/data/kalshi/{series}_markets.csv.gz (every settled market: event, team, result, times)
                 sharp/data/kalshi/{series}_candles.csv.gz (hourly candles per market: yes bid/ask close, price, volume, open interest)
  Polymarket: python sharp/exchange_history.py WORKDIR poly --series 10345 [--max-events N]
              -> sharp/data/poly/{series}_markets.csv.gz (closed game events and their markets, outcomes, winner)
                 sharp/data/poly/{series}_trades.csv.gz (every trade: wallet, side, outcome, size, price, time)
Settled Kalshi markets before /historical/cutoff are read from the historical tier."""
import os, sys, json, time, urllib.request, urllib.error
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
    G, D = "https://gamma-api.polymarket.com", "https://data-api.polymarket.com/v2"
    evs, off = [], 0
    while len(evs) < MAXE:
        d = get(f"{G}/events?series_id={SER}&closed=true&limit=100&offset={off}&order=startDate&ascending=true"); time.sleep(0.2)
        if not isinstance(d, list) or not d: break
        evs += d; off += 100
    evs = evs[:MAXE]; mk, tr = [], []
    for i, e in enumerate(evs):
        for m in e.get("markets") or []:
            try: outs, prices = json.loads(m.get("outcomes") or "[]"), json.loads(m.get("outcomePrices") or "[]")
            except Exception: outs, prices = [], []
            mk.append(dict(event_id=e.get("id"), event=e.get("title"), slug=e.get("slug"), start=e.get("startDate"), game_start=m.get("gameStartTime") or e.get("endDate"),
                           condition_id=m.get("conditionId"), question=m.get("question"), market_type=m.get("sportsMarketType") or m.get("groupItemTitle"),
                           line=m.get("line"), outcomes="|".join(outs), final_prices="|".join(map(str, prices)), volume=m.get("volumeNum") or m.get("volume")))
            cid, offset, cursor, seen = m.get("conditionId"), 0, None, 0
            while cid:
                q = f"{D}/trades?condition_id={cid}&limit=500" + (f"&cursor={cursor}" if cursor else f"&offset={offset}")
                t = get(q); time.sleep(0.15); rows = t.get("data", []) if isinstance(t, dict) else []
                for x in rows:
                    tr.append(dict(condition_id=cid, wallet=x.get("proxy_wallet"), side=x.get("side"), outcome=x.get("outcome"), outcome_index=x.get("outcome_index"),
                                   size=x.get("size"), price=x.get("price"), ts=x.get("timestamp"), tx=x.get("transaction_hash")))
                seen += len(rows); cursor = t.get("next_cursor") or t.get("cursor") if isinstance(t, dict) else None
                if not rows or len(rows) < 500 or seen >= 200000: break
                if not cursor: offset += 500
        if i % 50 == 0: print("poly", SER, i, len(evs), "trades", len(tr), flush=True)
    save(pd.DataFrame(mk), f"{SER}_markets.csv.gz"); save(pd.DataFrame(tr).drop_duplicates(), f"{SER}_trades.csv.gz")
