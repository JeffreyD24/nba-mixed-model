"""One-off check: Kalshi historical archive and the GDPNow file link."""
import json, urllib.request, urllib.parse, re, time

def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (econ research tracker)", "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=30) as r:
            b = r.read(); print(f"OK {r.status} {len(b)}B {url}"); return b
    except Exception as e:
        print(f"FAIL {url}: {type(e).__name__} {str(e)[:160]}"); return None

K = "https://external-api.kalshi.com/trade-api/v2"
b = get(K + "/historical/cutoff")
if b: print("   ", b[:500])
for s in ["KXCPI", "KXCPICORE", "KXCPIYOY", "KXPAYROLLS", "KXU3", "KXFEDDECISION", "KXFED", "KXGDP"]:
    cur, n, ev = "", 0, set(); first = None
    for _ in range(30):
        q = dict(series_ticker=s, limit=1000)
        if cur: q["cursor"] = cur
        b = get(K + "/historical/markets?" + urllib.parse.urlencode(q))
        if not b: break
        d = json.loads(b); m = d.get("markets", []); n += len(m); ev |= {x["event_ticker"] for x in m}
        if m and first is None: first = m[0]
        cur = d.get("cursor")
        if not cur or not m: break
        time.sleep(0.3)
    print(f"  HIST {s}: {n} markets, {len(ev)} events: {sorted(ev)[:2]} .. {sorted(ev)[-2:]}")
    if first: print("    sample:", json.dumps({k: first.get(k) for k in ("ticker", "event_ticker", "floor_strike", "cap_strike", "strike_type", "expiration_value", "result", "close_time", "volume_fp", "settlement_value_dollars")})[:600])
    if first and s == "KXCPI":
        t = first["ticker"]; ct = int(time.mktime(time.strptime(first["close_time"][:19], "%Y-%m-%dT%H:%M:%S")))
        for path in [f"/historical/markets/{t}/candlesticks?start_ts={ct-40*86400}&end_ts={ct}&period_interval=60",
                     f"/historical/trades?ticker={t}&limit=3"]:
            bb = get(K + path)
            if bb: print("    ", bb[:700])
b = get("https://www.atlantafed.org/research-and-data/data/gdpnow")
if b:
    for l in sorted(set(re.findall(rb'["\']([^"\']*\.(?:xlsx|csv|json)[^"\']*)["\']', b)))[:40]: print("   gdpnow link:", l.decode(errors="ignore")[:220])
