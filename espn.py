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


def injury_news(hours=24, now_utc=None):
    """Latest reporter-sourced injury updates from ESPN, by team code: {code: [(time_et, text), ...]} newest first."""
    from zoneinfo import ZoneInfo
    FULL = {"Atlanta Hawks": "atl", "Boston Celtics": "bos", "Brooklyn Nets": "bkn", "Charlotte Hornets": "cha", "Chicago Bulls": "chi",
            "Cleveland Cavaliers": "cle", "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det",
            "Golden State Warriors": "gs", "Houston Rockets": "hou", "Indiana Pacers": "ind", "LA Clippers": "lac",
            "Los Angeles Clippers": "lac", "Los Angeles Lakers": "lal", "Memphis Grizzlies": "mem", "Miami Heat": "mia",
            "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min", "New Orleans Pelicans": "no", "New York Knicks": "ny",
            "Oklahoma City Thunder": "okc", "Orlando Magic": "orl", "Philadelphia 76ers": "phi", "Phoenix Suns": "phx",
            "Portland Trail Blazers": "por", "Sacramento Kings": "sac", "San Antonio Spurs": "sa", "Toronto Raptors": "tor",
            "Utah Jazz": "utah", "Washington Wizards": "wsh"}
    d = _get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries")
    now = pd.Timestamp.now(tz="UTC") if now_utc is None else now_utc
    out = {}
    for t in d.get("injuries", []):
        code = FULL.get(t.get("displayName"))
        if not code: continue
        items = []
        for i in t.get("injuries", []):
            when = pd.to_datetime(i.get("date"), utc=True, errors="coerce")
            text = (i.get("shortComment") or "").strip()
            if text and when is not pd.NaT and now - when <= pd.Timedelta(hours=hours):
                items.append((when.tz_convert(ZoneInfo("America/New_York")), text))
        out[code] = sorted(items, key=lambda x: x[0], reverse=True)
    return out


def news_text(news, teams, per_team=3, max_chars=700):
    """short block for a notification body"""
    lines = []
    for t in teams:
        for when, text in news.get(t, [])[:per_team]:
            lines.append(f"- {t.upper()} {when:%a %-I:%M %p}: {text}")
    if not lines: return "Latest news: nothing reported for either team in the last 24 hours."
    s = "Latest news:\n" + "\n".join(lines)
    return s if len(s) <= max_chars else s[:max_chars - 1] + "…"
