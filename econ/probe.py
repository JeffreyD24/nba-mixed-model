"""One-off check of which economics data sources GitHub can reach (prices and free forecasts)."""
import json, urllib.request, urllib.parse, re

def get(url, n=400):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (econ research tracker)", "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=25) as r:
            b = r.read(); print(f"OK {r.status} {len(b)}B {url}"); return b
    except Exception as e:
        print(f"FAIL {url}: {type(e).__name__} {str(e)[:120]}"); return None

K = "https://external-api.kalshi.com/trade-api/v2"
b = get(K + "/series?category=Economics")
if b:
    s = json.loads(b).get("series", [])
    print(len(s), "economics series")
    for x in s[:400]:
        print("  SERIES", x.get("ticker"), "|", x.get("title"), "|", x.get("frequency"))
for t in ["KXCPI", "KXCPICORE", "KXCPIYOY", "KXPAYROLLS", "KXU3", "KXFED", "KXFEDDECISION", "KXGDP", "KXJOBLESSCLAIMS", "KXPCE"]:
    b = get(K + "/markets?" + urllib.parse.urlencode(dict(series_ticker=t, status="open", limit=200)))
    if b:
        m = json.loads(b).get("markets", [])
        print(f"  {t}: {len(m)} open markets")
        for x in m[:3]: print("   ", json.dumps({k: x.get(k) for k in list(x)[:40]})[:1500])
b = get(K + "/markets?" + urllib.parse.urlencode(dict(series_ticker="KXCPI", status="settled", limit=5)))
if b: print("  settled sample:", json.dumps(json.loads(b).get("markets", [])[:1])[:1500])

for u in ["https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting",
          "https://www.atlantafed.org/-/media/documents/cqer/researchcq/gdpnow/GDPTrackingModelDataAndForecasts.xlsx",
          "https://www.atlantafed.org/cqer/research/gdpnow",
          "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL",
          "https://fred.stlouisfed.org/graph/fredgraph.csv?id=PAYEMS",
          "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE",
          "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARU",
          "https://api.bls.gov/publicAPI/v1/timeseries/data/CUSR0000SA0",
          "https://www.bls.gov/schedule/news_release/cpi.htm",
          "https://www.newyorkfed.org/research/policy/nowcast",
          "https://gateway.polymarket.us/v1/events?limit=5&category=economics"]:
    b = get(u)
    if b and ("clevelandfed" in u or "gdpnow" in u and u.endswith("gdpnow") or "nowcast" in u):
        links = sorted(set(re.findall(rb'["\'](https?://[^"\']+?\.(?:json|csv|xlsx)|/[^"\']+?\.(?:json|csv|xlsx))["\']', b)))
        for l in links[:30]: print("   link:", l.decode(errors="ignore"))
    elif b and len(b) < 5000: print("   ", b[:600].decode(errors="ignore"))
    elif b: print("   ", b[:200])
