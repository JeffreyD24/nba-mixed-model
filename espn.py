"""DraftKings lines from ESPN's public feeds (home-team perspective for spreads)."""
import json, urllib.request
import numpy as np, pandas as pd

ESPN2 = {"ATL": "atl", "BOS": "bos", "BKN": "bkn", "CHA": "cha", "CHI": "chi", "CLE": "cle", "DAL": "dal", "DEN": "den",
         "DET": "det", "GS": "gs", "GSW": "gs", "HOU": "hou", "IND": "ind", "LAC": "lac", "LAL": "lal", "MEM": "mem", "MIA": "mia",
         "MIL": "mil", "MIN": "min", "NO": "no", "NOP": "no", "NY": "ny", "NYK": "ny", "OKC": "okc", "ORL": "orl", "PHI": "phi",
         "PHX": "phx", "POR": "por", "SAC": "sac", "SA": "sa", "SAS": "sa", "TOR": "tor", "UTAH": "utah", "UTA": "utah",
         "WSH": "wsh", "WAS": "wsh"}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _num(x):
    try: return float(str(x).replace("+", "").replace("PK", "0").replace("pk", "0").replace("EVEN", "0"))
    except Exception: return np.nan


def lines(dates, when=("open", "close", "current")):
    """one row per game: date, home, away, book, {open,close,current}_{spread,total}"""
    out = []
    for d in dates:
        sb = _get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={pd.Timestamp(d):%Y%m%d}")
        for ev in sb.get("events", []):
            comp = ev["competitions"][0]
            teams = {c["homeAway"]: ESPN2.get(c["team"]["abbreviation"]) for c in comp["competitors"]}
            rec = dict(date=pd.Timestamp(d).normalize(), home=teams.get("home"), away=teams.get("away"),
                       state=comp.get("status", {}).get("type", {}).get("state"))
            try:
                od = _get(f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{ev['id']}/competitions/{comp['id']}/odds")
                items = od.get("items", [])
                it = next((i for i in items if "draftkings" in str(i.get("provider", {}).get("name", "")).lower()), items[0] if items else None)
                if it:
                    rec["book"] = it.get("provider", {}).get("name")
                    hto = it.get("homeTeamOdds") or {}
                    for w in when:
                        rec[f"{w}_spread"] = _num(((hto.get(w) or {}).get("pointSpread") or {}).get("american"))
                        rec[f"{w}_total"] = _num((((it.get(w) or {}).get("total")) or {}).get("american"))
                    if np.isnan(rec.get("current_spread", np.nan)): rec["current_spread"] = _num(it.get("spread"))
                    if np.isnan(rec.get("current_total", np.nan)): rec["current_total"] = _num(it.get("overUnder"))
            except Exception as e:
                rec["error"] = str(e)[:80]
            out.append(rec)
    return pd.DataFrame(out)
