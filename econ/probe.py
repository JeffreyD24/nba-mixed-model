"""One-off check: forecast data files and Kalshi price history depth."""
import json, urllib.request, urllib.parse, re, time

def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (econ research tracker)", "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=25) as r:
            b = r.read(); print(f"OK {r.status} {len(b)}B {url}"); return b
    except Exception as e:
        print(f"FAIL {url}: {type(e).__name__} {str(e)[:120]}"); return None

for u in ["https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json",
          "https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_quarter.json",
          "https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/cqer/researchcq/gdpnow/GDPTrackingModelDataAndForecasts.xlsx",
          "https://www.atlantafed.org/research-and-data/data/gdpnow",
          "https://www.atlantafed.org/cqer/research/gdpnow.aspx"]:
    b = get(u)
    if b: print("   ", b[:700])
b = get("https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting")
if b:
    for l in sorted(set(re.findall(rb'(?:src|href|data-[a-z-]+)=["\']([^"\']+)["\']', b)))[:400]:
        if re.search(rb'nowcast|json|chart|\.js', l, re.I): print("   cf link:", l.decode(errors="ignore")[:200])
b = get("https://www.newyorkfed.org/research/policy/nowcast")
if b:
    for l in sorted(set(re.findall(rb'["\']([^"\']*(?:json|csv|xlsx|api)[^"\']*)["\']', b)))[:60]: print("   ny link:", l.decode(errors="ignore")[:200])

K = "https://external-api.kalshi.com/trade-api/v2"
for s in ["KXCPI", "KXCPICORE", "KXCPIYOY", "KXPAYROLLS", "KXU3", "KXFEDDECISION", "KXGDP", "CPI", "FED", "PAYROLLS", "U3", "GDP", "CPIYOY", "CPICORE"]:
    cur, n, ev = "", 0, set()
    for _ in range(20):
        q = dict(series_ticker=s, status="settled", limit=1000)
        if cur: q["cursor"] = cur
        b = get(K + "/markets?" + urllib.parse.urlencode(q))
        if not b: break
        d = json.loads(b); m = d.get("markets", []); n += len(m); ev |= {x["event_ticker"] for x in m}
        cur = d.get("cursor")
        if not cur or not m: break
        time.sleep(0.3)
    print(f"  {s}: {n} settled markets, {len(ev)} events, oldest: {sorted(ev)[:3]} newest: {sorted(ev)[-2:]}")
# price history for one settled CPI market
b = get(K + "/markets?" + urllib.parse.urlencode(dict(series_ticker="KXCPI", status="settled", limit=3)))
if b:
    m = json.loads(b)["markets"][0]; t = m["ticker"]
    end = int(time.time()); start = end - 60 * 86400
    for path in [f"/series/KXCPI/markets/{t}/candlesticks?start_ts={start}&end_ts={end}&period_interval=60",
                 f"/markets/trades?ticker={t}&limit=5", f"/historical/markets/{t}/candlesticks?start_ts={start}&end_ts={end}&period_interval=60"]:
        b = get(K + path)
        if b: print("   ", b[:900])
