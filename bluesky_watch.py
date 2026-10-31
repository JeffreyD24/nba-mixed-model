"""
Bluesky watcher: new posts from the NBA reporters in research/media/bluesky_watch.csv, every minute.

- Saves every new post (time posted, time first seen, reporter, team, text) to research/bluesky/YYYY-MM-DD.csv,
  flagging injury and lineup posts and the players they name.
- Sends a phone alert when an injury/lineup post names a key player (worth KEY_SWING+ model points) whose game
  hasn't started, with what he's worth and the current DraftKings line.
- Uses Bluesky's public API (no login, free). Run by alert_loop.sh between the 5-minute checks.

  python bluesky_watch.py WORKDIR
"""
import os, sys, json, re, time, glob, urllib.request, urllib.parse
from zoneinfo import ZoneInfo
import pandas as pd

W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
sys.path.insert(0, W)
STATE, R = os.path.join(W, "state"), os.path.join(W, "research")
API = "https://public.api.bsky.app/xrpc/"
ET = ZoneInfo("America/New_York")
KEY_SWING = 1.5            # model points (margin or total) a player must be worth to trigger a phone alert
MAX_AGE_MIN = 120          # ignore posts older than this when first seen (e.g. after the watcher was off)

INJURY = re.compile(
    r"\b(out|ruled out|won't play|will not play|not playing|will play|is playing|available|unavailable|questionable|doubtful|"
    r"probable|game[- ]time decision|gtd|upgraded|downgraded|injur\w*|sprain\w*|strain\w*|sore\w*|soreness|illness|sick|"
    r"rest(?:ing)?|load management|dnp|inactive|starting|starters?|lineup|return\w*|back tonight|cleared|surgery|mri|x-rays?|"
    r"ankle|knee|hamstring|calf|groin|back|wrist|hip|foot|shoulder|concussion|protocol)\b", re.I)
TEAM_CODE = {"Atlanta": "atl", "Boston": "bos", "Brooklyn": "bkn", "Charlotte": "cha", "Chicago": "chi", "Cleveland": "cle",
             "Dallas": "dal", "Denver": "den", "Detroit": "det", "Golden State": "gs", "Houston": "hou", "Indiana": "ind",
             "LA Clippers": "lac", "LA Lakers": "lal", "Memphis": "mem", "Miami": "mia", "Milwaukee": "mil", "Minnesota": "min",
             "New Orleans": "no", "New York": "ny", "Oklahoma City": "okc", "Orlando": "orl", "Philadelphia": "phi",
             "Phoenix": "phx", "Portland": "por", "Sacramento": "sac", "San Antonio": "sa", "Toronto": "tor", "Utah": "utah",
             "Washington": "wsh", "League-wide": ""}


def api(method, **q):
    url = API + method + "?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nba-mixed-model research"}), timeout=15) as r:
        return json.loads(r.read())


def players_index():
    """{normalized full name: (team code, display name, home-margin-if-sits by game, ...)} from today's/tomorrow's model files
    and team membership from the official injury reports (the players whose status matters)."""
    import build_report_features as brf
    now = pd.Timestamp.now(tz=ET).tz_localize(None)
    models = sorted(f for f in os.listdir(STATE) if f.startswith("model_") and f[6:16] >= str((now - pd.Timedelta(hours=8)).date()))
    rp = os.path.join(STATE, "injury_reports_2026_27.csv")
    rep = pd.read_csv(rp) if os.path.exists(rp) else pd.DataFrame(columns=["team", "player"])
    team_of = {}
    for t, p in zip(rep.team, rep.player):
        code = brf.ABBR2GAMES.get(brf.FULL2ABBR.get(t)) if isinstance(t, str) else None
        if code and isinstance(p, str): team_of[brf.key(p)] = (code, " ".join(reversed([x.strip() for x in p.split(",", 1)])) if "," in p else p)
    # the 5-minute checks save every player on the newest official report: key = "date|team|normalized name"
    sp = os.path.join(STATE, "injury_status_seen.csv")
    if os.path.exists(sp):
        for k in pd.read_csv(sp).key.astype(str):
            parts = k.split("|")
            if len(parts) == 3 and parts[2] not in team_of:
                team_of[parts[2]] = (parts[1], parts[2].title())
    idx = {}
    for mf in models:
        M = json.load(open(os.path.join(STATE, mf)))
        for k, v in M["players"].items():
            if k not in team_of: continue
            code, disp = team_of[k]
            for g in M["games"]:
                if code not in (g["home"], g["away"]): continue
                dm = M["c_off"] * v[0] - M["c_def"] * v[1]; dt = M["c_off"] * v[0] + M["c_def"] * v[1]
                idx.setdefault(k, []).append(dict(team=code, name=disp, game=g, date=M["date"],
                                                  home_margin_if_sits=dm if code == g["home"] else -dm, total_if_sits=dt))
    return idx


def mentioned(text, team, idx):
    """players named in a post: full name anywhere; last name alone only for the reporter's own team"""
    import build_report_features as brf
    t = " " + re.sub(r"[^a-z' ]", " ", text.lower()) + " "
    out = []
    for k, games in idx.items():
        full = " " + k + " "
        last = " " + k.split()[-1] + " " if " " in k else None
        if full in t or (team and games[0]["team"] == team and last and len(last.strip()) > 3 and last in t):
            out.append((k, games))
    return out


def process(posts, watch, seen, idx, now, notify=None):
    """posts: list of (handle, post dict from getAuthorFeed). Returns rows to log; updates seen; sends alerts."""
    rows = []
    for handle, p in posts:
        rec = p.get("record") or {}; uri = p.get("uri", "")
        if handle == "_alerted" or not uri or uri in seen.get(handle, []): continue
        created = pd.Timestamp(rec.get("createdAt")).tz_convert(ET).tz_localize(None) if rec.get("createdAt") else now
        seen.setdefault(handle, []).append(uri)
        if now - created > pd.Timedelta(minutes=MAX_AGE_MIN): continue           # old post (first run, or watcher was off)
        w = watch.get(handle, {}); team = TEAM_CODE.get(w.get("team", ""), "")
        text = (rec.get("text") or "").replace("\n", " ").strip()
        inj = bool(INJURY.search(text))
        names = mentioned(text, team, idx) if inj else []
        rows.append(dict(seen_at_et=str(now)[:19], posted_at_et=str(created)[:19], lag_min=round((now - created).total_seconds() / 60, 1),
                         handle=handle, reporter=w.get("name", ""), team=w.get("team", ""), injury_related=inj,
                         players="; ".join(g[0]["name"] for _, g in names), text=text[:500],
                         url=f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}"))
        for k, games in names:
            for gm in games:
                g = gm["game"]
                if pd.Timestamp(g["tip_et"]) <= now: continue
                if max(abs(gm["home_margin_if_sits"]), abs(gm["total_if_sits"])) < KEY_SWING: continue
                ak = f"{k}|{g['game_id']}"          # one alert per player and game per hour, however many reporters post it
                last = seen.setdefault("_alerted", {}).get(ak)
                if last and now - pd.Timestamp(last) < pd.Timedelta(minutes=60): continue
                seen["_alerted"][ak] = str(now)[:19]
                if notify:
                    H, A = g["home"].upper(), g["away"].upper()
                    notify(f"Reporter: {gm['name']} ({A} @ {H})",
                           f"{w.get('name', handle)} on Bluesky, {created:%-I:%M %p}: \"{text[:300]}\"\n"
                           f"Model: if {gm['name']} sits, {H} {gm['home_margin_if_sits']:+.1f} and total {gm['total_if_sits']:+.1f}. "
                           f"Check whether the line has moved yet; the next check will alert if there's an edge.",
                           rows[-1]["url"])
    return rows


def main():
    now = pd.Timestamp.now(tz=ET).tz_localize(None)
    wpath = os.path.join(R, "media", "bluesky_watch.csv")
    if not os.path.exists(wpath): print("No watch list."); return
    watch = {r.bluesky_handle: dict(name=r.name, team=r.team) for r in pd.read_csv(wpath).fillna("").itertuples()}
    spath = os.path.join(STATE, "bluesky_seen.json")
    seen = json.load(open(spath)) if os.path.exists(spath) else {}
    posts, errors = [], 0
    for h in watch:
        try:
            feed = api("app.bsky.feed.getAuthorFeed", actor=h, limit=15, filter="posts_and_author_threads")
            posts += [(h, i["post"]) for i in feed.get("feed", []) if i.get("post") and not i.get("reason")]    # skip reposts
        except Exception:
            errors += 1
        time.sleep(0.15)
    try:
        idx = players_index()
    except Exception as e:
        print("Player index unavailable:", type(e).__name__); idx = {}

    def notify(title, body, url):
        """phone alert through ntfy (repository secret NTFY_TOPIC), with a button that opens the post"""
        topic = os.environ.get("NTFY_TOPIC")
        if not topic:
            print("NTFY_TOPIC not set; would have sent:", title, "|", body); return
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST",
                                     headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high",
                                              "Tags": "speech_balloon", "Actions": f"view, Open post, {url}"})
        try: urllib.request.urlopen(req, timeout=15)
        except Exception as e: print("Alert not sent:", type(e).__name__)

    rows = process(posts, watch, seen, idx, now, notify=notify)
    for h in seen:
        if h != "_alerted": seen[h] = seen[h][-60:]                          # keep the file small
    seen["_alerted"] = {k: v for k, v in seen.get("_alerted", {}).items() if now - pd.Timestamp(v) < pd.Timedelta(days=2)}
    json.dump(seen, open(spath, "w"))
    if rows:
        os.makedirs(os.path.join(R, "bluesky"), exist_ok=True)
        p = os.path.join(R, "bluesky", f"{now.date()}.csv")
        pd.DataFrame(rows).to_csv(p, mode="a", header=not os.path.exists(p), index=False)
    n_inj = sum(r["injury_related"] for r in rows)
    print(f"Bluesky: {len(watch)} reporters, {len(rows)} new posts ({n_inj} injury/lineup), {errors} feeds unavailable.")


if __name__ == "__main__":
    main()
