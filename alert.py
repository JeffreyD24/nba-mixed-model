"""
Intraday alert check. Run every few minutes during the alert window.

  python alert.py WORKDIR [--force]

Uses state/today_model.json from the morning run (no refitting): pulls the latest official
injury report, re-predicts today's games, pulls the current DraftKings lines from ESPN, and sends
one ntfy push per game and market when the model differs from the current line by >= THRESHOLD.
Every alert is logged to state/alerts.csv and graded by the next morning run.
"""
import os, sys, json, subprocess, urllib.request, datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

W = os.path.abspath(sys.argv[1]); FORCE = "--force" in sys.argv
sys.path.insert(0, W)
from parse_injury_reports import parse as parse_pdf      # noqa: E402
import build_report_features as brf                      # noqa: E402
import espn                                              # noqa: E402
import actionnet

THRESHOLD = 3.0                     # points, for both spreads and totals
MAX_LINE_MOVE = 3.0                 # "market agrees" heads-up when the line moved this much TOWARD the model since opening
REMIND_AFTER_MIN = 30              # reminder if an alert's bet still isn't logged this many minutes later (once, before tip)
FRESH_OPEN_MIN = 60                 # an unmoved line counts as "the opener" for this long after it was first seen
AGAINST_MOVE = 0.5                  # caution when the line moved this much AGAINST the bet since opening. Backtest (2024-26, lines
                                    # between open and close, edge 3+): moved against 43% winners, toward 56%, unmoved 49%
JUMP_WINDOW_MIN = 60                # a "jump" is a move within this many minutes
JUMP_LOG = 1.5                      # log every jump at least this big (builds the database of line moves)
JUMP_ALERT = 3.0                    # send a "Line jump" notification at this size
WINDOW = None                       # None = check all day; or (16, 0, 19, 0) for 4:00-7:00 PM ET
ET = ZoneInfo("America/New_York")
STATE = os.path.join(W, "state")
NOW = pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None))
TODAY = NOW.normalize()
BASE = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_"


def in_window():
    if WINDOW is None: return True
    start = TODAY + pd.Timedelta(hours=WINDOW[0], minutes=WINDOW[1]); end = TODAY + pd.Timedelta(hours=WINDOW[2], minutes=WINDOW[3])
    return start <= NOW < end


def latest_report(max_hours=16):
    """newest official report: try every 15-minute file name going back up to max_hours (crosses midnight)"""
    tmp = os.path.join(W, "_latest_report.pdf")
    t = NOW.floor("15min")
    for k in range(int(max_hours * 4) + 1):
        x = t - pd.Timedelta(minutes=15 * k)
        names = [f"{x:%Y-%m-%d}_{x:%I_%M%p}"]
        if x.minute == 30: names.append(f"{x:%Y-%m-%d}_{x:%I%p}")           # older hourly naming (posted ~:30)
        for n in names:
            r = subprocess.run(["curl", "-s", "-m", "20", "-o", tmp, "-w", "%{http_code}", BASE + n + ".pdf"], capture_output=True, text=True)
            if r.stdout == "200" and os.path.getsize(tmp) > 1000:
                rows = parse_pdf(tmp); os.remove(tmp); return n, x, rows
    return None, None, []


def against_us(market, side, move):
    """True when the line moved away from the side the model likes (the market disagrees).
    move = current line - opening line (spreads are from the home team's view)."""
    if market == "total": return move < 0 if side == "over" else move > 0
    return move > 0 if side == "home" else move < 0


def log_link(date, away, home, market, pick, line):
    """prefilled 'Log a bet' form on GitHub for this alert"""
    import urllib.parse
    repo = os.environ.get("GITHUB_REPOSITORY", "JeffreyD24/nba-mixed-model")
    q = dict(template="log-bet.yml", title=f"Bet: {pick.upper()} {line} {away.upper()} @ {home.upper()} {date}",
             game_date=date, away=away.upper(), home=home.upper(), market=market, pick=pick.upper() if market == "spread" else pick,
             line=line, odds="-110")
    return f"https://github.com/{repo}/issues/new?" + urllib.parse.urlencode(q)


def notify(title, body, priority="high", tags="basketball", link=None, dk=None):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC not set; would have sent:", title, "|", body, "| DK:", dk or "-"); return False
    actions = "; ".join(a for a in (f"view, Bet on DraftKings, {dk}" if dk else "", f"view, Log this bet, {link}" if link else "") if a)
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST",
                                 headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": priority, "Tags": tags,
                                          **({"Actions": actions} if actions else {})})
    urllib.request.urlopen(req, timeout=20)
    return True


def main():
    if "--test" in sys.argv:
        topic = os.environ.get("NTFY_TOPIC") or ""
        try:
            ok = notify("Test alert: NBA tracker connected", "If you can read this, phone alerts from your GitHub tracker are working. No bet here.")
            msg = (f"sent OK to a topic {len(topic)} characters long, starting with '{topic[:2]}'" if ok
                   else "NOT sent: the NTFY_TOPIC secret is missing or empty")
        except Exception as e:
            msg = f"NOT sent: ntfy returned an error ({type(e).__name__}: {str(e)[:80]})"
        open(os.path.join(STATE, "test_alert_result.txt"), "w").write(f"{NOW}: test alert {msg}\n")
        print("Test alert", msg); return
    if not FORCE and not in_window():
        print(f"{NOW:%H:%M} ET is outside the alert window; nothing to do."); return
    models = sorted(f for f in os.listdir(STATE) if f.startswith("model_") and f[6:16] >= str(TODAY.date()))
    if not models:
        print("No model saved for today or tomorrow yet.")
        try:      # still record lines from the moment they're posted
            import research
            research.init(W); print(f"Line timeline: {research.timeline_snapshot(NOW)} changes.")
        except Exception as e:
            print("Line timeline logging skipped:", type(e).__name__, str(e)[:120])
        return
    snap, snap_time, rows = latest_report()
    allrep = pd.DataFrame(rows, columns=["snapshot", "as_of", "game_date", "game_time_et", "matchup", "team", "player", "status"])
    if len(allrep):
        allrep["gd"] = pd.to_datetime(allrep.game_date, format="%m/%d/%Y", errors="coerce")
        allrep["team_g"] = allrep.team.map(brf.FULL2ABBR).map(brf.ABBR2GAMES)
    print(f"Latest injury report: {snap or 'none found'}")

    apath = os.path.join(STATE, "alerts.csv")
    A = pd.read_csv(apath) if os.path.exists(apath) else pd.DataFrame(columns=["game_id", "market"])
    sent_ok = A[A["skipped"].isna()] if len(A) and "skipped" in A else A
    done = set(zip(sent_ok.game_id, sent_ok.market))
    news_done = set((r.game_id, r.market, r.news_key) for r in A.itertuples()
                    if isinstance(getattr(r, "news_key", None), str)) if len(A) else set()
    skipped = set((r.game_id, r.market) for r in A.itertuples() if isinstance(getattr(r, "skipped", None), str)) if len(A) else set()
    graded = A[A.result.isin(["W", "L"]) & A.skipped.isna()] if ("result" in A and "skipped" in A) else A.iloc[:0]
    bpath = os.path.join(STATE, "my_bets.csv")
    MYB = pd.read_csv(bpath) if os.path.exists(bpath) else pd.DataFrame(columns=["date", "home", "away", "market"])

    def bets_note(date, home, away, market, want=None):
        """('same market' text, 'other market' text) for bets already logged on this game"""
        if not len(MYB): return "", ""
        x = MYB[(MYB.date.astype(str) == str(date)) & (MYB.home == home) & (MYB.away == away)]
        def desc(r):
            pick = str(r.pick).upper(); ln = float(r.line)
            what = f"{pick} {ln:g}" if r.market == "total" else f"{pick} {ln:+g}"
            when = pd.Timestamp(r.logged_at_et).strftime("%-I:%M %p") if isinstance(r.logged_at_et, str) else "earlier"
            book = f", {r.book}" if isinstance(r.book, str) and r.book else ""
            st = float(r.stake); stake = f"${st:.0f}" if st == int(st) else f"${st:.2f}"
            return f"{what} ({float(r.odds):+g}, {stake}{book}, logged {when})"
        sm = x[x.market == market]
        if want is not None:            # bets on the same market but the OTHER side are reported separately
            opp = sm[sm.pick.astype(str).str.lower() != str(want).lower()]
            sm = sm[sm.pick.astype(str).str.lower() == str(want).lower()]
        else:
            opp = sm.iloc[:0]
        return ("; ".join(desc(r) for r in sm.itertuples()),
                "; ".join(desc(r) for r in x[x.market != market].itertuples()) +
                (("; " if (x.market != market).any() else "") + "OTHER SIDE: " + "; ".join(desc(r) for r in opp.itertuples()) if len(opp) else ""))

    def caution_before(gid, market):
        """the caution alert sent earlier for this game and market, if any"""
        c = A[(A.game_id == gid) & (A.market == market) & A.skipped.notna()] if len(A) and "skipped" in A else A.iloc[:0]
        return c.iloc[-1] if len(c) else None
    rec = (f"{int((graded.result == 'W').sum())}-{int((graded.result == 'L').sum())}" if len(graded) else "no graded alerts yet")
    cgraded = A[A.result.isin(["W", "L"]) & A.skipped.notna()] if ("result" in A and "skipped" in A) else A.iloc[:0]
    crec = (f"{int((cgraded.result == 'W').sum())}-{int((cgraded.result == 'L').sum())}" if len(cgraded) else "none graded yet")
    new, n_games = [], 0
    model_rows = []
    try:
        NEWS = espn.injury_news(hours=24)
    except Exception as e:
        NEWS = None; print("News feed unavailable:", type(e).__name__)
    hpath = os.path.join(STATE, "line_history.csv")
    H_ = pd.read_csv(hpath) if os.path.exists(hpath) else pd.DataFrame(columns=["game_id", "market", "seen_at_et", "line", "open_line"])
    hist_new = []
    SRC = {}   # game_id -> where the current line came from

    def record_line(gid, market, cur, opn):
        """log the line whenever it changes (or the first time it is seen), with the time we saw it"""
        if cur is None or pd.isna(cur): return
        prev = [r for r in hist_new if r["game_id"] == gid and r["market"] == market]
        old = H_[(H_.game_id == gid) & (H_.market == market)]
        last = prev[-1]["line"] if prev else (old.line.iloc[-1] if len(old) else None)
        if last is None or float(last) != float(cur):
            hist_new.append(dict(game_id=gid, market=market, seen_at_et=str(NOW)[:16], line=cur, open_line=opn, source=SRC.get(gid)))

    def history_text(gid, market, opn, fmt):
        rows = pd.concat([H_[(H_.game_id == gid) & (H_.market == market)],
                          pd.DataFrame([r for r in hist_new if r["game_id"] == gid and r["market"] == market])], ignore_index=True)
        if not len(rows): return ""
        first = rows.iloc[0]
        parts = []
        if opn is not None and not pd.isna(opn) and float(first.line) != float(opn):
            parts.append(f"opened {fmt(opn)} (before tracking began)")
        steps = [f"{fmt(r.line)} ({'first seen ' if i == 0 else ''}{pd.Timestamp(r.seen_at_et):%a %-I:%M %p})" for i, r in enumerate(rows.itertuples())]
        if len(steps) > 5: steps = steps[:1] + ["…"] + steps[-3:]
        return "\nLine history: " + " -> ".join(parts + steps)

    LINE_NOW = {}   # (game_id, market) -> what the line and model say at this check, for reminders

    def first_seen(gid, market, opn):
        """when we first saw this line, if that first sighting was the opening number (else None: opened before tracking)"""
        rows = pd.concat([H_[(H_.game_id == gid) & (H_.market == market)],
                          pd.DataFrame([r for r in hist_new if r["game_id"] == gid and r["market"] == market])], ignore_index=True)
        if not len(rows) or opn is None or pd.isna(opn) or float(rows.line.iloc[0]) != float(opn): return None
        return pd.Timestamp(rows.seen_at_et.iloc[0])

    def verdict(gid, market, side, cur, opn, e):
        """(BET / PASS / OPTIONAL / CHECK, reason) from the betting rule (backtests 2024-26, edge 3+):
        at the opener 53-55%; moved toward the model with 3+ left ~56%; moved against ~43%; unmoved for hours ~49%."""
        if opn is None or pd.isna(opn): return "CHECK", "opening line unknown, so use your judgment"
        mv = cur - opn
        if abs(mv) >= AGAINST_MOVE and against_us(market, side, mv):
            return "PASS", f"the line moved {abs(mv):.1f} pts AGAINST the model since it opened at {opn:g}"
        if abs(mv) >= AGAINST_MOVE:
            if abs(e) >= THRESHOLD:
                return "BET", f"the line moved {abs(mv):.1f} pts toward the model and {abs(e):.1f} pts of edge are left"
            return "PASS", f"the line moved toward the model and only {abs(e):.1f} pts of edge are left"
        fs = first_seen(gid, market, opn)
        if fs is not None and (NOW - fs) <= pd.Timedelta(minutes=FRESH_OPEN_MIN):
            return "BET", f"still at the opening line, posted about {max(1, int((NOW - fs).total_seconds() // 60))} min ago"
        if fs is not None:
            h_ = (NOW - fs).total_seconds() / 3600
            return "OPTIONAL", f"still at the opening line {h_:.0f}+ hours after it posted (about break-even in backtests once a line sits)"
        return "OPTIONAL", "still at the opening line, but it posted before tracking began (time unknown)"

    def news_verdict(g, market, side, cur, opn, e):
        """verdict for an alert caused by reporter news: what matters is whether the line has reacted yet"""
        vs = [v for v in NEWSOV.values() if str(v.get("game_id")) == str(g["game_id"])]
        age = min(((NOW - pd.Timestamp(v["posted_at_et"])).total_seconds() / 60 for v in vs), default=None)
        if age is None or age > NEWS_FRESH_MIN:
            return verdict(g["game_id"], market, side, cur, opn, e)
        if opn is not None and not pd.isna(opn) and abs(cur - opn) >= AGAINST_MOVE and against_us(market, side, cur - opn):
            return "CHECK", (f"the news is {age:.0f} min old, but the line has moved {abs(cur - opn):.1f} pts against the model "
                             f"since it opened at {opn:g}, so the market may know something else")
        return "BET", (f"reporter news {age:.0f} min old and {abs(e):.1f} pts of edge at the current line. Bet now if your app "
                       f"still shows this number; if the line has already jumped toward the model, the edge is gone")

    RULE_TXT = ("Rule: BET at the opener, or if the line moved toward the model with 3+ pts of edge left. PASS if it moved "
                "against the model by 0.5+ since it opened.")

    news_for = lambda g: ("\n" + espn.news_text(NEWS, [g["away"], g["home"]])) if NEWS is not None else ""
    # ---- key players: undecided injury statuses and status changes
    spath = os.path.join(STATE, "injury_status_seen.csv")
    SEEN = pd.read_csv(spath) if os.path.exists(spath) else pd.DataFrame(columns=["key", "status", "snapshot"])
    seen = dict(zip(SEEN.key, SEEN.status)); seen_new = {}
    kpath = os.path.join(STATE, "key_player_alerts.csv")
    KP = pd.read_csv(kpath) if os.path.exists(kpath) else pd.DataFrame(columns=["key"])
    kp_done = set(KP.key); kp_new = []
    dec_rows = []
    PENDING = ("Questionable", "Doubtful", "Probable")
    # reporter news (bluesky_watch.py): a clear "out"/"will play" post newer than the official report is used right away
    opath = os.path.join(STATE, "news_overrides.json")
    NEWSOV = json.load(open(opath)) if os.path.exists(opath) else {}
    NEWS_FRESH_MIN = 20          # a NEWS alert says BET only while the post is this new (the market catches up fast)
    KEY_SWING = 1.5        # model points (margin or total) a player is worth if he sits: "key player"

    def player_swings(M, rep, g):
        """[(player, team, status, p_miss, home-margin change if he sits, total change if he sits)] for both teams' listed players"""
        out = []
        for team in (g["home"], g["away"]):
            r = rep[rep.team_g == team] if len(rep) else rep
            for p, st in zip(r.player, r.status) if len(r) else []:
                v = M["players"].get(brf.key(p))
                if not v: continue
                dm = M["c_off"] * v[0] - M["c_def"] * v[1]           # his team's margin if he sits (vs plays)
                dt = M["c_off"] * v[0] + M["c_def"] * v[1]           # game total if he sits
                pmx = dict(M["p_miss"], NEWS_Out=1.0, NEWS_Available=0.0)
                out.append((p, team, st, pmx.get(st, 0.0), dm if team == g["home"] else -dm, dt))
        return out

    def fnum(x, signed=False):
        try: return f"{float(x):+g}" if signed else f"{float(x):g}"
        except (TypeError, ValueError): return "n/a"

    def name(p):
        return " ".join(reversed([x.strip() for x in p.split(",", 1)])) if "," in p else p

    def pending_text(sw, g):
        """undecided players worth 0.75+ model points, biggest first"""
        rows = [x for x in sw if x[2] in PENDING and max(abs(x[4]), abs(x[5])) >= 0.75]
        rows.sort(key=lambda x: -max(abs(x[4]), abs(x[5])))
        if not rows: return ""
        H = g["home"].upper(); parts = []
        for p, team, st, pm, dmh, dt in rows[:4]:
            parts.append(f"{name(p)} ({team.upper()}, {st.lower()}): if he sits, model {H} {dmh:+.1f}, total {dt:+.1f} "
                         f"(already counts a {pm:.0%} chance)")
        return "\nUndecided: " + "; ".join(parts) + "."

    def limbo(sw):
        """(n undecided, margin lo, hi, total lo, hi): how far the model can still move once every undecided player's status
        is final. Today's number already counts each one's chance of sitting, so 'sits' moves it (1-p) x swing, 'plays' -p x swing."""
        rows = [x for x in sw if x[2] in PENDING and max(abs(x[4]), abs(x[5])) >= 0.25]
        lm = hm = lt = ht = 0.0
        for p, team, st, pm, dmh, dt in rows:
            a, b = (1 - pm) * dmh, -pm * dmh; lm += min(a, b); hm += max(a, b)
            a, b = (1 - pm) * dt, -pm * dt; lt += min(a, b); ht += max(a, b)
        return len(rows), lm, hm, lt, ht

    def unrated_pending(g):
        """undecided players on the report for this game that the model has no rating for (new or barely played)"""
        if not len(rep) or "status" not in rep: return []
        r = rep[rep.team_g.isin([g["home"], g["away"]]) & rep.status.isin(PENDING)]
        return [f"{name(p)} ({t.upper()}, {st.lower()})" for p, t, st in zip(r.player, r.team_g, r.status)
                if isinstance(p, str) and brf.key(p) not in M["players"]]

    def limbo_text(sw, g, margin, total, market=None, side=None, e=None, always=False):
        n, lm, hm, lt, ht = limbo(sw)
        unr = unrated_pending(g) if always else []
        unr_t = (" Not rated by the model (assumed not to move it): " + ", ".join(unr[:4]) + ".") if unr else ""
        if not n or max(hm - lm, ht - lt) < 0.5:
            if not always: return ""
            if not len(rep) or (rep[rep.team_g.isin([g["home"], g["away"]])].status == "NOT YET SUBMITTED").any() \
                    or not rep.team_g.isin([g["home"], g["away"]]).any():
                return ("\nPoints in limbo: unknown. A team has not filed its injury report for this game yet, so the model "
                        "could still move when it does." + unr_t)
            if not n:
                return "\nPoints in limbo: none. No undecided players the model rates, so final statuses should not move the model." + unr_t
            w = max(hm - lm, ht - lt)
            return (f"\nPoints in limbo ({n} undecided): under 0.5 pts. Final statuses should move the model by {w:.1f} pts at most."
                    + unr_t)
        H = g["home"].upper()
        t = (f"\nPoints in limbo ({n} undecided): once statuses are final the model could land at {H} {margin + lm:+.1f} to "
             f"{margin + hm:+.1f} (now {margin:+.1f}) and total {total + lt:.1f} to {total + ht:.1f} (now {total:.1f}).")
        if market and e is not None:
            lo, hi = (lm, hm) if market == "spread" else (lt, ht)
            sg = 1 if side in ("home", "over") else -1
            a, b = sorted((sg * (e + lo), sg * (e + hi)))
            t += f" This bet's edge could end up {a:+.1f} to {b:+.1f}" + (" (it could flip to the other side)." if a < 0 else ".")
        return t + unr_t
    mpath = os.path.join(STATE, "market_moves.csv")
    MV = pd.read_csv(mpath) if os.path.exists(mpath) else pd.DataFrame(columns=["game_id", "market"])
    moved_done = set(zip(MV.game_id, MV.market)); moves_new = []

    for mf in models:
        M = json.load(open(os.path.join(STATE, mf)))
        day = pd.Timestamp(M["date"])
        # a report counts as current for this day if it was filed at or after 8 PM the night before
        # (the same snapshot the backtests used for opening lines)
        fresh = snap_time is not None and snap_time >= day - pd.Timedelta(days=1) + pd.Timedelta(hours=20)
        rep = allrep[allrep.gd == day] if len(allrep) else allrep

        # reporter news newer than the official report replaces that player's status until the next report
        news_used = {}            # game team -> [override]
        if len(NEWSOV):
            rep = rep.copy() if len(rep) else pd.DataFrame(columns=allrep.columns if len(allrep) else ["team_g", "player", "status"])
            for k, v in NEWSOV.items():
                d, team_, pk = k.split("|", 2)
                if d != M["date"] or pk not in M["players"]: continue
                if snap_time is not None and pd.Timestamp(v["posted_at_et"]) <= snap_time: continue      # official report caught up
                m_ = (rep.team_g == team_) & (rep.player.map(brf.key) == pk) if len(rep) else pd.Series(dtype=bool)
                off = rep.loc[m_, "status"].iloc[0] if len(rep) and m_.any() else None
                if off == v["status"] or (off == "Available" and v["status"] == "Available"): continue
                if off is None and v["status"] == "Available": continue                     # not listed: already counted as playing
                v = dict(v, official=off or "not listed")
                if len(rep) and m_.any(): rep.loc[m_, "status"] = "NEWS_" + v["status"]
                else: rep = pd.concat([rep, pd.DataFrame([dict(team_g=team_, player=v["player"], status="NEWS_" + v["status"])])],
                                      ignore_index=True)
                news_used.setdefault(team_, []).append(v)
        PM = dict(M["p_miss"], NEWS_Out=1.0, NEWS_Available=0.0)

        def news_text(g):
            vs = news_used.get(g["home"], []) + news_used.get(g["away"], [])
            if not vs: return ""
            return "\nReporter news used (official report not updated yet): " + "; ".join(
                f"{v['player']} {v['status'].upper()} per {v['reporter']} at {pd.Timestamp(v['posted_at_et']):%-I:%M %p} "
                f"(official: {str(v['official']).lower()})" for v in vs) + ". Read the post: " + vs[0]["url"]

        def missing(team):
            """(miss_off, miss_def) for a team from the latest report; None if the team has not filed"""
            if not len(rep): return None
            r = rep[rep.team_g == team]
            if (r.status == "NOT YET SUBMITTED").any(): return None
            mo = md = 0.0
            for p, st in zip(r.player, r.status):
                pm = PM.get(st, 0.0); v = M["players"].get(brf.key(p))
                if pm > 0 and v: mo += pm * v[0]; md += pm * v[1]
            return mo, md

        L = espn.lines([day], when=("open", "current"))      # DraftKings opening line (and backup current line) from ESPN
        L = actionnet.merge_current(L, day)                     # fresher current DraftKings line from Action Network
        for g in M["games"]:
            line = L[(L.home == g["home"]) & (L.away == g["away"])] if len(L) else L
            if len(line): SRC[g["game_id"]] = line.iloc[0].get("line_source")
            if not len(line) or line.iloc[0].get("state") not in (None, "pre"): continue
            n_games += 1
            ln = line.iloc[0]
            h, a = missing(g["home"]), missing(g["away"])
            rep_off = allrep[allrep.gd == day] if len(allrep) else allrep
            SW = player_swings(M, rep, g) if snap else []
            for p, team, st, pm, dmh, dt in (player_swings(M, rep_off, g) if snap else []):
                k = f"{M['date']}|{team}|{brf.key(p)}"
                prev = seen.get(k)
                if prev != st:
                    seen_new[k] = (st, snap)
                    if prev is not None and max(abs(dmh), abs(dt)) >= 0.5:
                        dec_rows.append(dict(detected_at_et=str(NOW)[:16], report=snap, game_id=g["game_id"], date=M["date"],
                                             away=g["away"], home=g["home"], tip_et=g["tip_et"], team=team, player=name(p),
                                             from_status=prev, to_status=st, p_miss_from=M["p_miss"].get(prev, 0.0), p_miss_to=pm,
                                             home_margin_if_sits=round(dmh, 2), total_if_sits=round(dt, 2),
                                             dk_spread_now=ln.get("current_spread"), dk_total_now=ln.get("current_total"),
                                             line_source=ln.get("line_source")))
                        if max(abs(dmh), abs(dt)) >= KEY_SWING and pd.Timestamp(g["tip_et"]) > NOW:
                            H, Aw = g["home"].upper(), g["away"].upper()
                            notify(f"Injury decision: {name(p)} {st.upper()} ({Aw} @ {H})",
                                   f"{name(p)} ({team.upper()}) changed from {prev.lower()} to {st.lower()} on the {snap} report. "
                                   f"Worth {dmh:+.1f} to {H}'s margin and {dt:+.1f} to the total if he sits (model). "
                                   f"DraftKings now: {H} {fnum(ln.get('current_spread'), True)}, total {fnum(ln.get('current_total'))}. "
                                   "If the line hasn't moved yet, the bet alerts below (if any) are ahead of the market." + news_for(g),
                                   priority="high" if st in ("Out", "Available") else "default", tags="hospital")
            for p, team, st, pm, dmh, dt in SW:
                k = f"{M['date']}|{g['game_id']}|{brf.key(p)}|{st}"
                if st in PENDING and max(abs(dmh), abs(dt)) >= KEY_SWING and k not in kp_done and pd.Timestamp(g["tip_et"]) > NOW:
                    H, Aw = g["home"].upper(), g["away"].upper()
                    notify(f"Key decision pending: {name(p)} {st.lower()} ({Aw} @ {H})",
                           f"{name(p)} ({team.upper()}) is {st.lower()} on the {snap} report. If he sits, the model moves {H} {dmh:+.1f} "
                           f"and the total {dt:+.1f} (it already counts a {pm:.0%} chance he sits). Expect the line to move when "
                           f"his status is decided. DraftKings now: {H} {fnum(ln.get('current_spread'), True)}, total "
                           f"{fnum(ln.get('current_total'))}." + limbo_text(SW, g, g["morning_margin"], g["morning_total"]) + news_for(g),
                           priority="low", tags="hourglass")
                    kp_done.add(k); kp_new.append(dict(key=k, sent_at_et=str(NOW)[:16], game_id=g["game_id"], player=name(p), status=st,
                                                       home_margin_if_sits=round(dmh, 2), total_if_sits=round(dt, 2)))
            if h is None or a is None or not fresh:
                margin, total = g["morning_margin"], g["morning_total"]; used = f"as of {M.get('made_at_et', 'the last model run')[:16]}"
            else:
                ph = g["base_home"] + M["c_off"] * h[0] + M["c_def"] * a[1]
                pa = g["base_away"] + M["c_off"] * a[0] + M["c_def"] * h[1]
                margin, total = ph - pa, ph + pa; used = snap
                if news_used.get(g["home"]) or news_used.get(g["away"]): used = f"{snap} + reporter news"
            nl, lm_, hm_, lt_, ht_ = limbo(SW)
            model_rows.append(dict(seen_at_et=str(NOW)[:16], game_id=g["game_id"], date=M["date"], away=g["away"], home=g["home"],
                                   model_margin=round(margin, 2), model_total=round(total, 2), injury_report=used,
                                   limbo_players=nl, limbo_margin_lo=round(margin + lm_, 2), limbo_margin_hi=round(margin + hm_, 2),
                                   limbo_total_lo=round(total + lt_, 2), limbo_total_hi=round(total + ht_, 2)))
            NK = ";".join(sorted(f"{v['player']}|{v['status']}" for v in news_used.get(g["home"], []) + news_used.get(g["away"], [])))
            tip = pd.Timestamp(g["tip_et"]).strftime("%a %-I:%M %p")
            H, Aw = g["home"].upper(), g["away"].upper()
            for market in ("spread", "total"):
                cur = ln.get(f"current_{market}"); opn = ln.get(f"open_{market}")
                record_line(g["game_id"], market, cur, opn)
                if cur is None or pd.isna(cur): continue
                fmt = (lambda v: f"{v:+g}") if market == "spread" else (lambda v: f"{v:g}")
                hist_txt = history_text(g["game_id"], market, opn, fmt)
                e_now = (margin + cur) if market == "spread" else (total - cur)
                side_now = ("home" if e_now > 0 else "away") if market == "spread" else ("over" if e_now > 0 else "under")
                LINE_NOW[(g["game_id"], market)] = dict(cur=cur, opn=opn, e=e_now, side=side_now, H=H, Aw=Aw, tip=tip,
                                                        tip_et=g["tip_et"], date=M["date"], home=g["home"], away=g["away"],
                                                        model=margin if market == "spread" else total, hist=hist_txt)
                is_news = bool(NK) and (g["game_id"], market, NK) not in news_done
                if (g["game_id"], market) in done and not is_news: continue
                is_open = opn is not None and not pd.isna(opn) and cur == opn
                if market == "spread":
                    e = margin + cur; side = "home" if e > 0 else "away"
                    team = H if side == "home" else Aw; bet_line = cur if side == "home" else -cur
                    title = f"Bet {team} {bet_line:+g}: {Aw} @ {H}, {tip}"
                    body = f"Model: {H} by {margin:+.1f}. DraftKings: {H} {cur:+g}" + (" (opening line)." if is_open else f" (opened {opn:+g}).")
                else:
                    e = total - cur; side = "over" if e > 0 else "under"
                    title = f"Bet {side.upper()} {cur:g}: {Aw} @ {H}, {tip}"
                    body = f"Model total {total:.1f}. DraftKings {cur:g}" + (" (opening line)." if is_open else f" (opened {opn:g}).")
                body += f" Edge {abs(e):.1f} pts."
                if is_news and (g["game_id"], market) in done:
                    # already alerted on this game: re-alert only if the news flips the side or adds 1+ pt of edge
                    prev = A[(A.game_id == g["game_id"]) & (A.market == market)].tail(1)
                    if len(prev) and prev.side.iloc[0] == side and abs(e) < float(prev.edge.iloc[0]) + 1.0:
                        continue
                if not is_open and opn is not None and not pd.isna(opn):
                    e_open = (margin + opn) if market == "spread" else (total - opn)
                    body += f" Edge at the opening line was {abs(e_open):.1f} pts{'' if (e_open > 0) == (e > 0) else ' the other way'}."
                # ---- market moving toward the model by 3+ since open: one info alert per game and market
                move = (cur - opn) if (opn is not None and not pd.isna(opn)) else 0.0
                toward = abs(move) >= MAX_LINE_MOVE and not against_us(market, side, move)
                if toward and (g["game_id"], market) not in moved_done and abs(e) < THRESHOLD:
                    mtitle = f"Market agrees: {Aw} @ {H} {market}, {tip}"
                    if market == "spread":
                        mbody = f"Line moved {abs(move):.1f} pts toward the model: {H} opened {opn:+g}, now {cur:+g}. Model: {H} by {margin:+.1f}."
                    else:
                        mbody = f"Total moved {abs(move):.1f} pts toward the model ({side}): opened {opn:g}, now {cur:g}. Model {total:.1f}."
                    mbody += f" Edge left: {abs(e):.1f} pts (under {THRESHOLD:g}, so no bet). Info only." + hist_txt + news_for(g)
                    notify(mtitle, mbody, priority="low", tags="chart_with_upwards_trend")
                    moves_new.append(dict(at_et=str(NOW), game_id=g["game_id"], date=M["date"], home=g["home"], away=g["away"],
                                          market=market, model_side=side, open_line=opn, line=cur, move=round(move, 1),
                                          model=round(margin if market == "spread" else total, 2), edge_left=round(abs(e), 2)))
                    moved_done.add((g["game_id"], market)); print("MARKET AGREES:", mtitle, "|", mbody)
                if abs(e) < THRESHOLD: continue
                skip = None
                if not fresh: skip = "no current injury report"
                elif h is None or a is None: skip = "a team has not filed its injury report"
                elif (not is_news and opn is not None and not pd.isna(opn) and abs(cur - opn) >= AGAINST_MOVE
                      and against_us(market, side, cur - opn)):
                    skip = (f"line moved {abs(cur - opn):.1f} pts against this bet since open (in backtests, bets after the line "
                            f"moved against the model won only about 43%)")
                if market == "spread":
                    link = log_link(M["date"], g["away"], g["home"], "spread", team, f"{bet_line:+g}")
                else:
                    link = log_link(M["date"], g["away"], g["home"], "total", side, f"{cur:g}")
                dkv = ln.get({"home": "dk_link_home_spread", "away": "dk_link_away_spread", "over": "dk_link_over",
                              "under": "dk_link_under"}[side]) or ln.get("dk_link_game")
                dk = dkv if isinstance(dkv, str) and dkv.startswith("http") else None
                if dk and "outcomes=" in dk:          # the bet-slip link has the line built in (P750 = +7.5, O23350 = 233.5);
                    import re as _re                  # ESPN's copy can lag, so use the game page if it isn't today's line
                    m_ = _re.search(r"(?:HC\d+([PN])(\d+)|OU\d+[OU](\d+))_", dk)
                    if m_:
                        lv = (int(m_.group(2)) / 100 * (1 if m_.group(1) == "P" else -1)) if m_.group(2) else int(m_.group(3)) / 100
                        want = (bet_line if market == "spread" else cur)
                        if abs(lv - float(want)) > 0.01:
                            gl = ln.get("dk_link_game"); dk = gl if isinstance(gl, str) and gl.startswith("http") else None
                rec_row = dict(alerted_at_et=str(NOW), game_id=g["game_id"], date=M["date"], home=g["home"], away=g["away"],
                               tip_et=g["tip_et"], market=market, side=side, line=cur, open_line=opn,
                               model=round(margin if market == "spread" else total, 2), edge=round(abs(e), 2),
                               injury_report=used, sent=False, skipped=skip, news_key=NK if is_news else np.nan)
                if skip:
                    # caution alert: still sent, once per game and market, flagged with the reason
                    if (g["game_id"], market) not in skipped:
                        cbody = (body + f"\nCAUTION: {skip}. The model may be missing news here; place this bet with caution."
                                 f"\nInjury report: {used}. Caution alerts so far: {crec}." + news_text(g) + pending_text(SW, g)
                                 + limbo_text(SW, g, margin, total, market, side, e, always=True) + hist_txt + news_for(g))
                        vd, vr = verdict(g["game_id"], market, side, cur, opn, e)
                        cbody = f"{vd}: {vr}.\n{RULE_TXT}\n" + cbody
                        same, other = bets_note(M["date"], g["home"], g["away"], market, (g[side] if market == "spread" else side))
                        ctitle = f"[{vd}] CAUTION - " + title
                        rec_row["verdict"] = vd
                        if same: cbody = f"ALREADY BET: you logged {same}.\n" + cbody; ctitle = "ALREADY BET - " + ctitle
                        if other: cbody += f"\nYour other bet on this game: {other}."
                        if "OTHER SIDE" in other: ctitle = "YOU BET THE OTHER SIDE - " + ctitle
                        rec_row["sent"] = notify(ctitle, cbody, priority="default", tags="warning,basketball", link=link, dk=dk)
                        new.append(rec_row); skipped.add((g["game_id"], market))
                        print("CAUTION ALERT:", title, "|", skip)
                    continue
                if toward:
                    body += f" Market agrees: the line has moved {abs(move):.1f} pts toward the model since open."
                    moved_done.add((g["game_id"], market))
                body += f"\nInjury report: {used}. Alerts so far: {rec}. Tracking test: the model has not yet proven an edge live." + news_text(g) + pending_text(SW, g)
                body += limbo_text(SW, g, margin, total, market, side, e, always=True) + hist_txt + news_for(g)
                prio = "high"; why = ""
                cb = caution_before(g["game_id"], market)
                if cb is not None:      # a caution went out earlier: say why this one follows it
                    t0 = pd.Timestamp(cb.alerted_at_et).strftime("%-I:%M %p")
                    reason = str(cb.skipped)
                    cleared = ("both teams have now filed injury reports" if "filed" in reason else
                               "a current injury report is now out" if "injury report" in reason else
                               "the line is no longer 3+ pts against this bet" if "against" in reason else "the caution no longer applies")
                    why = (f"UPDATE to the CAUTION alert at {t0}: {cleared} ({used}). Edge now {abs(e):.1f} pts "
                           f"(was {float(cb.edge):.1f} at {float(cb.line):g}).\n")
                    title = "UPDATE - " + title
                same, other = bets_note(M["date"], g["home"], g["away"], market, (g[side] if market == "spread" else side))
                if same:
                    why = f"ALREADY BET: you logged {same}. Only add to it if you mean to.\n" + why
                    title = "ALREADY BET - " + title; prio = "default"
                if other:
                    body += f"\nYour other bet on this game: {other}."
                if "OTHER SIDE" in other: title = "YOU BET THE OTHER SIDE - " + title
                vd, vr = news_verdict(g, market, side, cur, opn, e) if is_news else verdict(g["game_id"], market, side, cur, opn, e)
                if is_news:
                    title = "NEWS - " + title
                    why = ("NEWS: reporter news changed the model before the official report did. Read the post (link below) "
                           "before betting.\n") + why
                body = f"{vd}: {vr}.\n{RULE_TXT}\n" + why + body
                title = f"[{vd}] " + title; rec_row["verdict"] = vd
                if vd == "PASS": prio = "default"
                rec_row["sent"] = notify(title, body, priority=prio, link=link, dk=dk)
                new.append(rec_row); done.add((g["game_id"], market))
                if is_news: news_done.add((g["game_id"], market, NK))
                print("ALERT:", title, "|", body)
    if new:
        A = pd.concat([A, pd.DataFrame(new)], ignore_index=True)
    # ---- reminders: an alert's bet still not logged REMIND_AFTER_MIN later (you log every bet you place)
    n_rem = 0
    if len(A) and "sent" in A:
        if "reminded_at_et" not in A: A["reminded_at_et"] = np.nan
        A["reminded_at_et"] = A["reminded_at_et"].astype(object)
        if "verdict" not in A: A["verdict"] = np.nan
        # only alerts that carried a verdict (sent since reminders began), latest per game and market
        last = A[A.sent.astype(str).isin(["True", "1", "1.0"]) & A.verdict.notna()].groupby(["game_id", "market"]).tail(1)
        for i, r in last.iterrows():
            k = (r.game_id, r.market); now_ = LINE_NOW.get(k)
            if now_ is None or isinstance(r.get("reminded_at_et"), str): continue
            if A[(A.game_id == r.game_id) & (A.market == r.market)].reminded_at_et.astype(str).str.len().gt(3).any(): continue
            if NOW - pd.Timestamp(r.alerted_at_et) < pd.Timedelta(minutes=REMIND_AFTER_MIN): continue
            if pd.Timestamp(now_["tip_et"]) <= NOW: continue
            if str(r.get("verdict")) == "PASS": continue
            logged = len(MYB) and ((MYB.date.astype(str) == str(r.date)) & (MYB.home == r.home) & (MYB.away == r.away) & (MYB.market == r.market)).any()
            if logged: continue
            cur, opn, e_, side_ = now_["cur"], now_["opn"], now_["e"], now_["side"]
            vd, vr = verdict(r.game_id, r.market, side_, cur, opn, e_)
            H, Aw = now_["H"], now_["Aw"]
            if r.market == "spread":
                bl = cur if side_ == "home" else -cur; what = f"{H if side_ == 'home' else Aw} {bl:+g}"
            else:
                what = f"{side_.upper()} {cur:g}"
            then = f"{float(r.line):+g}" if r.market == "spread" else f"{float(r.line):g}"
            changed = "" if float(cur) == float(r.line) else f" The line was {then} at the alert."
            switched = "" if side_ == r.side else " NOTE: the model's side has flipped since the alert."
            body = (f"{vd}: {vr}.\n{RULE_TXT}\nNo bet logged yet for the alert at {pd.Timestamp(r.alerted_at_et):%-I:%M %p}. "
                    f"Now: {what}, edge {abs(e_):.1f} pts (model {now_['model']:.1f}).{changed}{switched}" + now_["hist"])
            notify(f"[{vd}] REMINDER - {what}: {Aw} @ {H}, {now_['tip']}", body,
                   priority="default" if vd != "PASS" else "low", tags="alarm_clock")
            A.loc[i, "reminded_at_et"] = str(NOW)[:16]; n_rem += 1
            print("REMINDER:", what, vd, vr)
    if new or n_rem:
        A.to_csv(apath, index=False)
    # ---- line jumps: fast moves, logged for research and alerted when large
    jpath = os.path.join(STATE, "line_jumps.csv")
    J = pd.read_csv(jpath) if os.path.exists(jpath) else pd.DataFrame(columns=["game_id", "market", "detected_at_et"])
    allh = pd.concat([H_, pd.DataFrame(hist_new)], ignore_index=True)
    jumps_new = []
    if len(allh):
        allh["t"] = pd.to_datetime(allh.seen_at_et)
        info = {}
        for mf in models:
            M2 = json.load(open(os.path.join(STATE, mf)))
            for g in M2["games"]: info[g["game_id"]] = (g, M2)
        for (gid, market), rows in allh.groupby(["game_id", "market"]):
            if gid not in info: continue
            rows = rows.sort_values("t"); cur = float(rows.line.iloc[-1]); t_cur = rows.t.iloc[-1]
            start = NOW - pd.Timedelta(minutes=JUMP_WINDOW_MIN)
            before = rows[rows.t <= start]
            ref_row = before.iloc[-1] if len(before) else rows.iloc[0]
            ref, t_ref = float(ref_row.line), ref_row.t
            move = cur - ref
            if abs(move) < JUMP_LOG or t_cur < start: continue
            recent = J[(J.game_id == gid) & (J.market == market)]
            if len(recent) and pd.to_datetime(recent.detected_at_et).max() >= start: continue   # already logged this jump
            moving = rows[rows.t > start]                      # changes inside the window
            t_move = moving.t.iloc[0] if len(moving) else t_cur  # when the line started moving
            g, M2 = info[gid]
            if market == "total": side_model = "over" if g["morning_total"] > cur else "under"; mod = g["morning_total"]
            else: side_model = "home" if g["morning_margin"] + cur > 0 else "away"; mod = g["morning_margin"]
            toward = not against_us(market, side_model, move)
            # news posted from 30 min before the earlier line to now
            win_news = []
            if NEWS is not None:
                for team in (g["away"], g["home"]):
                    for when, text in NEWS.get(team, []):
                        if when.replace(tzinfo=None) >= t_ref - pd.Timedelta(minutes=30):
                            win_news.append(f"{team.upper()} {when:%-I:%M %p}: {text}")
            tip = pd.Timestamp(g["tip_et"])
            row = dict(detected_at_et=str(NOW)[:16], game_id=gid, date=M2["date"], away=g["away"], home=g["home"], market=market,
                       from_line=ref, to_line=cur, move=round(move, 1), steady_since=str(t_ref)[:16], move_started=str(t_move)[:16],
                       move_seen=str(t_cur)[:16], minutes=int((t_cur - t_move).total_seconds() // 60), hours_to_tip=round((tip - t_cur).total_seconds() / 3600, 1),
                       model=round(mod, 1), direction="toward model" if toward else "away from model",
                       news_in_window=" | ".join(win_news), news_count=len(win_news), alerted=abs(move) >= JUMP_ALERT)
            jumps_new.append(row)
            if abs(move) >= JUMP_ALERT:
                fmt = (lambda v: f"{v:+g}") if market == "spread" else (lambda v: f"{v:g}")
                H2, A2 = g["home"].upper(), g["away"].upper()
                what = f"{H2} spread" if market == "spread" else "total"
                title = f"Line jump: {A2} @ {H2} {what} {fmt(ref)} -> {fmt(cur)}"
                speed = (f"within one check (seen {t_cur:%-I:%M %p})" if row["minutes"] < 5
                         else f"over about {row['minutes']} min ({t_move:%-I:%M} to {t_cur:%-I:%M %p})")
                body = (f"Moved {abs(move):.1f} pts {speed}; it had been {fmt(ref)} since {t_ref:%a %-I:%M %p}. "
                        f"{row['hours_to_tip']:.1f} h before tip. Model: {fmt(mod) if market == 'spread' else f'{mod:.1f}'} "
                        f"({'the move is toward the model' if toward else 'the move is away from the model'}).")
                body += ("\nNews around the move:\n- " + "\n- ".join(win_news[:6])) if win_news else "\nNo injury news reported around the move yet: possibly breaking news or big bets."
                notify(title, body, priority="default", tags="zap")
                print("LINE JUMP:", title, "|", body)
    if jumps_new:
        pd.concat([J, pd.DataFrame(jumps_new)], ignore_index=True).to_csv(jpath, index=False)

    if seen_new:
        S2 = pd.concat([SEEN[~SEEN.key.isin(seen_new)], pd.DataFrame([dict(key=k, status=v[0], snapshot=v[1]) for k, v in seen_new.items()])])
        S2 = S2[S2.key.str[:10] >= str((NOW - pd.Timedelta(days=3)).date())]          # keep a few days
        S2.to_csv(spath, index=False)
    if kp_new:
        pd.concat([KP, pd.DataFrame(kp_new)], ignore_index=True).to_csv(kpath, index=False)
    if dec_rows:
        os.makedirs(os.path.join(W, "research"), exist_ok=True)
        dp = os.path.join(W, "research", "injury_decisions.csv")
        pd.DataFrame(dec_rows).to_csv(dp, mode="a", header=not os.path.exists(dp), index=False)
        print(f"Injury status changes logged: {len(dec_rows)}")
    if hist_new:
        pd.concat([H_, pd.DataFrame(hist_new)], ignore_index=True).to_csv(hpath, index=False)
    if moves_new:
        pd.concat([MV, pd.DataFrame(moves_new)], ignore_index=True).to_csv(mpath, index=False)
    # ---- research database (never allowed to break alerts)
    try:
        import research, time as _time
        research.init(W); _t0 = _time.time()
        n_odds = n_pred = n_spl = n_bk = n_pm = n_po = n_live = n_per = n_ls = n_min = 0
        # include last night's games until 8 AM, so games running past midnight keep their live lines and final scores
        early = str((NOW - pd.Timedelta(hours=8)).date())
        rmodels = sorted(f for f in os.listdir(STATE) if f.startswith("model_") and f[6:16] >= early)
        for mf in rmodels:
            M3 = json.load(open(os.path.join(STATE, mf))); rows = []
            try:
                k, rows = research.odds_snapshot(NOW, M3["date"], M3["games"]); n_odds += k
                n_pred += research.predictor_snapshot(NOW, M3["date"], rows)
            except Exception as e:
                print("ESPN research logging skipped:", type(e).__name__, str(e)[:120]); research.log_error(NOW, "espn odds/predictor " + M3["date"], e)
            try:
                a, b = research.splits_snapshot(NOW, M3["date"], M3["games"]); n_spl += a; n_bk += b
            except Exception as e:
                print("Betting splits logging skipped:", type(e).__name__, str(e)[:120]); research.log_error(NOW, "splits " + M3["date"], e)
            try:
                n_per += research.periods_snapshot(NOW, M3["date"], M3["games"])
            except Exception as e:
                print("Half/quarter/team total logging skipped:", type(e).__name__, str(e)[:120]); research.log_error(NOW, "periods " + M3["date"], e)
            try:
                n_ls += research.linescores(NOW, M3["date"], M3["games"])
            except Exception as e:
                print("Linescore logging skipped:", type(e).__name__, str(e)[:120]); research.log_error(NOW, "linescores " + M3["date"], e)
            try:
                n_min += research.minutes_log(NOW, M3["date"], M3["games"])
            except Exception as e:
                print("Minutes logging skipped:", type(e).__name__, str(e)[:120]); research.log_error(NOW, "minutes " + M3["date"], e)
            try:
                n_live += research.live_snapshot(NOW, M3["date"], M3["games"])
            except Exception as e:
                print("Live line logging skipped:", type(e).__name__, str(e)[:120]); research.log_error(NOW, "live " + M3["date"], e)
            try:
                stamp = os.path.join(W, "research", "props", f"_full_{M3['date']}.txt")
                last_full = pd.Timestamp(open(stamp).read().strip()) if os.path.exists(stamp) else None
                tips = [pd.Timestamp(g["tip_et"]) for g in M3["games"] if pd.Timestamp(g["tip_et"]) > NOW]
                soon = any(t - NOW <= pd.Timedelta(minutes=40) for t in tips)
                full = last_full is None or NOW - last_full >= pd.Timedelta(minutes=115) or \
                    (soon and NOW - last_full >= pd.Timedelta(minutes=30))
                a, b = research.props_snapshot(NOW, M3["date"], rows, full=full); n_pm += a; n_po += b
                closing = research.started_rows(NOW, M3["date"], M3["games"])      # closing prop lines after tip
                if closing:
                    a, b = research.props_snapshot(NOW, M3["date"], closing, full=True); n_pm += a; n_po += b
                if full:
                    os.makedirs(os.path.dirname(stamp), exist_ok=True); open(stamp, "w").write(str(NOW))
            except Exception as e:
                print("Props logging skipped:", type(e).__name__, str(e)[:120]); research.log_error(NOW, "props " + M3["date"], e)
        n_tl = 0
        try:
            n_tl = research.timeline_snapshot(NOW)
        except Exception as e:
            print("Line timeline logging skipped:", type(e).__name__, str(e)[:120]); research.log_error(NOW, "timeline", e)
        n_news = research.news_log(NOW, NEWS) if NEWS is not None else 0
        n_mod = research.model_snapshot(NOW, model_rows)
        print(f"Research log: {n_odds} odds changes, {n_pred} predictor snapshots, {n_spl} betting-split changes, "
              f"{n_bk} book line changes, {n_pm} player prop changes, {n_po} other prop changes, {n_live} live line changes, {n_per} half/quarter/team-total changes, {n_ls} final linescores, {n_min} games of minutes by quarter, {n_tl} line timeline changes, {n_news} new news notes, {n_mod} model changes.")
        cl = os.path.join(W, "research", "check_log.csv")
        row = pd.DataFrame([dict(at_et=str(NOW)[:16], research_seconds=round(_time.time() - _t0), odds=n_odds, predictor=n_pred,
                                 splits=n_spl, books=n_bk, props=n_pm, props_other=n_po, live=n_live, periods=n_per, linescores=n_ls, minutes=n_min, timeline=n_tl, news=n_news, model=n_mod)])
        old_cl = pd.read_csv(cl) if os.path.exists(cl) else None
        if old_cl is not None and list(old_cl.columns) != list(row.columns):
            pd.concat([old_cl, row], ignore_index=True).to_csv(cl, index=False)     # new column: rewrite once
        else:
            row.to_csv(cl, mode="a", header=old_cl is None, index=False)
    except Exception as e:
        print("Research logging skipped:", type(e).__name__, str(e)[:120])

    n_clean = sum(1 for x in new if not x.get("skipped"))
    print(f"{NOW:%H:%M} ET: checked {n_games} upcoming games, {n_clean} alerts and {len(new) - n_clean} caution alerts sent.")


if __name__ == "__main__":
    main()
