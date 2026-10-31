"""
One-time check: which reporters in research/media/nba_media_list.csv have an active Bluesky account?
Uses Bluesky's public API (no login). Writes research/media/bluesky_check.csv.
  python tools/bluesky_check.py .
"""
import os, sys, json, time, re, urllib.request, urllib.parse
import pandas as pd

W = os.path.abspath(sys.argv[1])
API = "https://public.api.bsky.app/xrpc/"
L = pd.read_csv(os.path.join(W, "research", "media", "nba_media_list.csv")).fillna("")
P = L[L.category.isin(["Beat writer / team reporter", "National insider / news account"])]

NBA_WORDS = re.compile(r"\b(nba|basketball|hoops|celtics|nets|knicks|76ers|sixers|raptors|bulls|cavs|cavaliers|pistons|pacers|bucks|hawks|"
                       r"hornets|heat|magic|wizards|nuggets|wolves|timberwolves|thunder|blazers|jazz|warriors|clippers|lakers|suns|kings|"
                       r"mavericks|mavs|rockets|grizzlies|pelicans|spurs|espn|athletic|stein|beat|reporter|writer|insider)\b", re.I)


def get(method, **q):
    url = API + method + "?" + urllib.parse.urlencode(q)
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nba-mixed-model research"}), timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:
            if k == 2: return {"error": str(e)[:100]}
            time.sleep(2 * (k + 1))


def norm(s): return re.sub(r"[^a-z]", "", s.lower())


rows = []
for r in P.itertuples():
    name = re.sub(r"\s*\(.*\)", "", r.name).strip()
    res = get("app.bsky.actor.searchActors", q=name, limit=10)
    best = None
    for a in res.get("actors", []) or []:
        dn = a.get("displayName") or ""; desc = a.get("description") or ""; handle = a.get("handle", "")
        score = 0
        if norm(dn) == norm(name): score += 3
        elif norm(name) in norm(dn) or norm(name.split()[-1]) in norm(handle): score += 1
        xh = r.x_handle.lstrip("@").lower()
        if xh and xh in handle.lower(): score += 2
        if NBA_WORDS.search(desc + " " + dn): score += 2
        if score >= 4 and (best is None or score > best[0]): best = (score, a)
    out = dict(team=r.team, name=r.name, x_handle=r.x_handle, category=r.category, bluesky_handle="", bluesky_name="", followers="",
               posts="", last_post_utc="", posts_last_14d="", match_score="", bio="")
    if best:
        a = best[1]
        prof = get("app.bsky.actor.getProfile", actor=a["did"])
        feed = get("app.bsky.feed.getAuthorFeed", actor=a["did"], limit=50, filter="posts_no_replies")
        dates = [pd.Timestamp(i["post"]["record"]["createdAt"]) for i in feed.get("feed", []) if i.get("post", {}).get("record", {}).get("createdAt")]
        now = pd.Timestamp.now(tz="UTC")
        dates = [d if d.tzinfo else d.tz_localize("UTC") for d in dates]
        out.update(bluesky_handle=a.get("handle"), bluesky_name=a.get("displayName"), followers=prof.get("followersCount", ""),
                   posts=prof.get("postsCount", ""), last_post_utc=str(max(dates))[:16] if dates else "",
                   posts_last_14d=sum(1 for d in dates if now - d <= pd.Timedelta(days=14)), match_score=best[0],
                   bio=(a.get("description") or "").replace("\n", " ")[:160])
    rows.append(out); time.sleep(0.3)
    print(f"{r.team:14s} {r.name:28s} -> {out['bluesky_handle'] or '-'} {out['posts_last_14d']}", flush=True)
D = pd.DataFrame(rows)
D.to_csv(os.path.join(W, "research", "media", "bluesky_check.csv"), index=False)
f = D[D.bluesky_handle != ""]; act = f[pd.to_numeric(f.posts_last_14d, errors="coerce").fillna(0) >= 3]
print(f"\nOn Bluesky: {len(f)} of {len(D)}; posting regularly (3+ posts in the last 14 days): {len(act)}")
