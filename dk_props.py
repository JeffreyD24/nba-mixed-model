"""DraftKings player over/under props, straight from DraftKings' own feed (Nov 6, 2026, Jeffrey: prop alerts get DraftKings + FanDuel links
and say which book is the better bet). Uses odds_feed's Chrome-fingerprint client. One league call + one category call per stat per run
(cached for 60 s). Only the main 'Points / Rebounds / Assists / Three Pointers O/U' markets; DraftKings often posts these for only the
bigger names, so 'no line' is common. Bet-slip link layout (event id + selection id) is the same as dk_direct.slip_link; not yet tested by tapping."""
import re, time, unicodedata
from urllib.parse import quote as quote_url
import odds_feed as F

LEAGUE = 42648
CAT = {"pts": "Player Points", "reb": "Player Rebounds", "ast": "Player Assists", "fg3m": "Player Threes"}
MT = {"pts": "Points O/U", "reb": "Rebounds O/U", "ast": "Assists O/U", "fg3m": "Three Pointers Made O/U"}
_cache = {}


def norm(n):
    n = unicodedata.normalize("NFKD", str(n)).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"[.'`]", "", n).replace("-", " "); n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", n)
    return re.sub(r"\s+", " ", n).strip()


def _fetch(stat):
    hit = _cache.get(stat)
    if hit and time.time() - hit[0] < 60: return hit[1]
    rows = []
    st, root = F.http_get(f"{F.DKB}/leagues/{LEAGUE}")
    if st == 200:
        cats, subs = F.dk_maps(root)
        cid = next((c["id"] for c in root.get("categories", []) if c["name"] == CAT[stat]), None)
        if cid is not None:
            st, j = F.http_get(f"{F.DKB}/leagues/{LEAGUE}/categories/{cid}")
            if st == 200: rows = F.dk_rows(j, "nba", "", subs, cats)
    _cache[stat] = (time.time(), rows); return rows


def quote(stat, name):
    """{'line', 'over', 'under', 'over_link', 'under_link'} for the player's main O/U, or None if DraftKings has none posted"""
    try:
        g = [r for r in _fetch(stat) if r["market_type"] == MT[stat] and norm(r["player"]) == norm(name) and r["outcome"] in ("Over", "Under")]
    except Exception as ex:
        print("dk_props failed:", type(ex).__name__, str(ex)[:80]); return None
    if not g: return None
    o = next((r for r in g if r["outcome"] == "Over"), None); u = next((r for r in g if r["outcome"] == "Under"), None)
    if not o or not u: return None
    lk = lambda r: f"https://sportsbook.draftkings.com/event/{r['event_id']}?outcomes={quote_url(r['sel_id'], safe='')}"
    return dict(line=float(o["points"]), over=o["price"], under=u["price"], over_link=lk(o), under_link=lk(u))
