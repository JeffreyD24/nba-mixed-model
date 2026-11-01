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
# clear statements of a final decision. A sentence counts only if it names the player, matches one side and not the
# other, and has no hedge word. The model then uses it until the next official report (alert.py, state/news_overrides.json).
OUT_RX = re.compile(r"\b(ruled out|will not play|won'?t play|not playing|(?:is|are) out\b(?! of)|will be out\b(?! of)|out tonight|"
                    r"resting|will rest|to rest|sit(?:ting|s)? out|dnp|inactive|will miss|won'?t be available|not available|sidelined|"
                    r"out for (?:tonight|today|the game))", re.I)
IN_RX = re.compile(r"\b(will play|is playing|are playing|available to play|(?:is|are|will be) available|cleared to play|will return|"
                   r"returns tonight|will start|is starting|good to go|in the lineup|upgraded to available|will suit up)\b", re.I)
HEDGE_RX = re.compile(r"\b(questionable|doubtful|probable|game[- ]time|gtd|likely|unlikely|could|might|may|hope|hoping|"
                      r"expected|expects|if he|whether|unclear|uncertain|undecided|considered|plans? to)\b", re.I)
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def day_hint(sent, now):
    """the game date a sentence is about, if it says ('tonight', 'tomorrow', 'Sunday'); else None (= his next game)"""
    t = sent.lower()
    if re.search(r"\b(tonight|today)\b", t): return str(now.date())
    if re.search(r"\btomorrow\b", t): return str((now + pd.Timedelta(days=1)).date())
    for i, d in enumerate(DAYS):
        if re.search(rf"\b{d}\b", t):
            return str((now + pd.Timedelta(days=(i - now.weekday()) % 7)).date())
    return None


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


def without_player(sent, k):
    """True if the sentence says a team is without this player: "without" right before his full or last name"""
    t = re.sub(r"[^a-z' ]", " ", sent.lower())
    names = [k] + ([k.split()[-1]] if " " in k else [])
    return any(re.search(rf"\bwithout\s+(?:(?:star|forward|guard|center)\s+)?{re.escape(n)}\b", t) for n in names)


def target_game(k, idx, now, day=None):
    """the game a post is about for this player: the day it names, else his next game not started (None if none)"""
    up = sorted((gm for gm in idx[k] if pd.Timestamp(gm["game"]["tip_et"]) > now and (day is None or gm["date"] == day)),
                key=lambda gm: gm["game"]["tip_et"])
    return up[0] if up else None


def player_day(text, k, now):
    """the day named in the first sentence that mentions this player ('tonight', 'Monday'...), else None"""
    last = k.split()[-1]
    for sent in re.split(r"(?<=[.!?;])\s+|\n", text):
        if last in sent.lower():
            d = day_hint(sent, now)
            if d: return d
    return None


def decisions(text, team, idx, now=None):
    """[(player key, ('Out' or 'Available', game date or None))] for clear statements in a post"""
    out = {}
    now = now if now is not None else pd.Timestamp.now(tz=ET).tz_localize(None)
    for sent in re.split(r"(?<=[.!?;])\s+|\n", text):
        if HEDGE_RX.search(sent): continue
        o_all, i = bool(OUT_RX.search(sent)), bool(IN_RX.search(sent))
        for k, _ in mentioned(sent, team, idx):
            o = o_all or without_player(sent, k)     # "Raptors without Leonard (knee)"
            if o == i: continue
            out[k] = ("Out" if o else "Available", day_hint(sent, now))
    return list(out.items())


def process(posts, watch, seen, idx, now, notify=None, overrides=None):
    """posts: list of (handle, post dict from getAuthorFeed). Returns rows to log; updates seen and overrides; sends alerts."""
    rows = []
    if overrides is None: overrides = {}
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
                         decisions="; ".join(f"{idx[k][0]['name']} {st[0]}" for k, st in (decisions(text, team, idx, now) if inj else [])),
                         url=f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}"))
        dec = dict(decisions(text, team, idx, now)) if inj else {}
        for k, (st, day) in list(dec.items()):   # news the model should use now: that day's game, else his next one not started
            dec[k] = st
            gm = target_game(k, idx, now, day)
            if gm is None: continue
            ok = f"{gm['date']}|{gm['team']}|{k}"
            if overrides.get(ok, {}).get("status") == st: continue
            overrides[ok] = dict(status=st, player=gm["name"], game_id=gm["game"]["game_id"], reporter=w.get("name", handle),
                                 posted_at_et=str(created)[:19], seen_at_et=str(now)[:19], url=rows[-1]["url"], text=text[:300],
                                 swing=round(max(abs(gm["home_margin_if_sits"]), abs(gm["total_if_sits"])), 2), new=True)
        for k, games in names:      # alert only for the game the post is about (named day, else his next game)
            gm0 = target_game(k, idx, now, player_day(text, k, now))
            for gm in ([gm0] if gm0 else []):
                g = gm["game"]
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
                           + (f"Read as {gm['name']} {dec[k].upper()}: the model is using this now and a full check is running; "
                              f"a NEWS alert follows if it opens an edge. Read the post to make sure."
                              if k in dec else "Not a clear final decision, so the model waits for the official report."),
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

    opath = os.path.join(STATE, "news_overrides.json")
    overrides = json.load(open(opath)) if os.path.exists(opath) else {}
    for v in overrides.values(): v.pop("new", None)
    rows = process(posts, watch, seen, idx, now, notify=notify, overrides=overrides)
    fresh_news = [v for v in overrides.values() if v.get("new")]
    for v in overrides.values(): v.pop("new", None)
    keep = str((now - pd.Timedelta(days=2)).date())
    overrides = {k: v for k, v in overrides.items() if k.split("|")[0] >= keep}
    json.dump(overrides, open(opath, "w"), indent=1)
    for h in seen:
        if h != "_alerted": seen[h] = seen[h][-60:]                          # keep the file small
    seen["_alerted"] = {k: v for k, v in seen.get("_alerted", {}).items() if now - pd.Timestamp(v) < pd.Timedelta(days=2)}
    json.dump(seen, open(spath, "w"))
    if rows:
        os.makedirs(os.path.join(R, "bluesky"), exist_ok=True)
        p = os.path.join(R, "bluesky", f"{now.date()}.csv")
        D = pd.DataFrame(rows)
        if os.path.exists(p):
            old = pd.read_csv(p)
            if list(old.columns) != list(D.columns): D = pd.concat([old, D], ignore_index=True); D.to_csv(p, index=False)   # new column
            else: D.to_csv(p, mode="a", header=False, index=False)
        else: D.to_csv(p, index=False)
    n_inj = sum(r["injury_related"] for r in rows)
    print(f"Bluesky: {len(watch)} reporters, {len(rows)} new posts ({n_inj} injury/lineup), {errors} feeds unavailable.")
    for v in fresh_news: print(f"NEWS: {v['player']} {v['status']} ({v['reporter']}, posted {v['posted_at_et'][11:16]})")
    return 10 if any(v["swing"] >= 0.75 for v in fresh_news) else 0


if __name__ == "__main__":
    sys.exit(main())
