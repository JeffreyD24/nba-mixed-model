"""Nov 5, 2026: can a browser-impersonating client (curl_cffi: Chrome's TLS fingerprint) read DraftKings' own CT feed from GitHub's servers?
Plain requests got HTTP 403 from the runner (probe_markets.py) and from Jeffrey's home PowerShell. Writes research/probes/dk_cffi_probe.md."""
import sys, json, datetime as dt
from curl_cffi import requests as R
W = sys.argv[1] if len(sys.argv) > 1 else "."
BASE = "https://sportsbook-nash.draftkings.com/api/sportscontent"
URLS = {"NBA dkusct": f"{BASE}/dkusct/v1/leagues/42648", "NHL dkusct": f"{BASE}/dkusct/v1/leagues/42133",
        "NBA dkusnj": f"{BASE}/dkusnj/v1/leagues/42648", "NBA page": "https://sportsbook.draftkings.com/leagues/basketball/nba"}
out = [f"# DraftKings via curl_cffi probe, {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC (GitHub runner)\n", "| target | impersonate | HTTP | bytes | note |", "|---|---|---|---|---|"]
for name, url in URLS.items():
    for imp in ("chrome124", "chrome131", "safari17_0"):
        try:
            r = R.get(url, impersonate=imp, timeout=30, headers={"Accept": "application/json", "Referer": "https://sportsbook.draftkings.com/"})
            note = ""
            if r.status_code == 200 and "leagues/" in url and "nash" in url:
                try:
                    j = r.json(); ev = j.get("events", []); note = f"events {len(ev)}: " + "; ".join(str(e.get("name")) for e in ev[:6])
                except Exception as e: note = "not JSON: " + str(e)[:60]
            else: note = r.text[:90].replace("\n", " ").replace("|", "/")
            out.append(f"| {name} | {imp} | {r.status_code} | {len(r.content)} | {note} |")
        except Exception as e:
            out.append(f"| {name} | {imp} | error | 0 | {type(e).__name__}: {str(e)[:80]} |")
# raw NBA reply + a readable look at the layout (Nov 5: first run showed it works; this one is to learn the fields)
try:
    r = R.get(URLS["NBA dkusct"], impersonate="chrome124", timeout=30, headers={"Accept": "application/json", "Referer": "https://sportsbook.draftkings.com/"})
    j = r.json(); json.dump(j, open(f"{W}/research/probes/dk_nba_dkusct_sample.json", "w"))
    out += ["", "## NBA dkusct layout", f"top-level keys: {list(j.keys())}", f"counts: " + ", ".join(f"{k}={len(v)}" for k, v in j.items() if isinstance(v, list))]
    for k, v in j.items():
        if isinstance(v, list) and v: out.append(f"first {k}: " + json.dumps(v[0])[:700])
except Exception as e:
    out.append(f"layout dump failed: {type(e).__name__}: {str(e)[:100]}")
open(f"{W}/research/probes/dk_cffi_probe.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
