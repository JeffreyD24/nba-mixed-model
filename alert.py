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
MAX_LINE_MOVE = 3.0                 # caution flag when the line moved this much AGAINST the bet since opening
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


def notify(title, body, priority="high", tags="basketball", link=None):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC not set; would have sent:", title, "|", body); return False
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST",
                                 headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": priority, "Tags": tags,
                                          **({"Actions": f"view, Log this bet, {link}"} if link else {})})
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
    skipped = set((r.game_id, r.market) for r in A.itertuples() if isinstance(getattr(r, "skipped", None), str)) if len(A) else set()
    graded = A[A.result.isin(["W", "L"]) & A.skipped.isna()] if ("result" in A and "skipped" in A) else A.iloc[:0]
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

    news_for = lambda g: ("\n" + espn.news_text(NEWS, [g["away"], g["home"]])) if NEWS is not None else ""
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

        def missing(team):
            """(miss_off, miss_def) for a team from the latest report; None if the team has not filed"""
            if not len(rep): return None
            r = rep[rep.team_g == team]
            if (r.status == "NOT YET SUBMITTED").any(): return None
            mo = md = 0.0
            for p, st in zip(r.player, r.status):
                pm = M["p_miss"].get(st, 0.0); v = M["players"].get(brf.key(p))
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
            if h is None or a is None or not fresh:
                margin, total = g["morning_margin"], g["morning_total"]; used = f"as of {M.get('made_at_et', 'the last model run')[:16]}"
            else:
                ph = g["base_home"] + M["c_off"] * h[0] + M["c_def"] * a[1]
                pa = g["base_away"] + M["c_off"] * a[0] + M["c_def"] * h[1]
                margin, total = ph - pa, ph + pa; used = snap
            model_rows.append(dict(seen_at_et=str(NOW)[:16], game_id=g["game_id"], date=M["date"], away=g["away"], home=g["home"],
                                   model_margin=round(margin, 2), model_total=round(total, 2), injury_report=used))
            tip = pd.Timestamp(g["tip_et"]).strftime("%a %-I:%M %p")
            H, Aw = g["home"].upper(), g["away"].upper()
            for market in ("spread", "total"):
                cur = ln.get(f"current_{market}"); opn = ln.get(f"open_{market}")
                record_line(g["game_id"], market, cur, opn)
                if cur is None or pd.isna(cur): continue
                fmt = (lambda v: f"{v:+g}") if market == "spread" else (lambda v: f"{v:g}")
                hist_txt = history_text(g["game_id"], market, opn, fmt)
                if (g["game_id"], market) in done: continue
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
                elif opn is not None and not pd.isna(opn) and abs(cur - opn) >= MAX_LINE_MOVE and against_us(market, side, cur - opn):
                    skip = f"line moved {abs(cur - opn):.1f} pts against this bet since open"
                if market == "spread":
                    link = log_link(M["date"], g["away"], g["home"], "spread", team, f"{bet_line:+g}")
                else:
                    link = log_link(M["date"], g["away"], g["home"], "total", side, f"{cur:g}")
                rec_row = dict(alerted_at_et=str(NOW), game_id=g["game_id"], date=M["date"], home=g["home"], away=g["away"],
                               tip_et=g["tip_et"], market=market, side=side, line=cur, open_line=opn,
                               model=round(margin if market == "spread" else total, 2), edge=round(abs(e), 2),
                               injury_report=used, sent=False, skipped=skip)
                if skip:
                    # caution alert: still sent, once per game and market, flagged with the reason
                    if (g["game_id"], market) not in skipped:
                        cbody = (body + f"\nCAUTION: {skip}. The model may be missing news here; place this bet with caution."
                                 f"\nInjury report: {used}. Caution alerts so far: {crec}." + hist_txt + news_for(g))
                        rec_row["sent"] = notify("CAUTION - " + title, cbody, priority="default", tags="warning,basketball", link=link)
                        new.append(rec_row); skipped.add((g["game_id"], market))
                        print("CAUTION ALERT:", title, "|", skip)
                    continue
                if toward:
                    body += f" Market agrees: the line has moved {abs(move):.1f} pts toward the model since open."
                    moved_done.add((g["game_id"], market))
                body += f"\nInjury report: {used}. Alerts so far: {rec}. Tracking test: the model has not yet proven an edge live." + hist_txt + news_for(g)
                rec_row["sent"] = notify(title, body, link=link)
                new.append(rec_row); done.add((g["game_id"], market))
                print("ALERT:", title, "|", body)
    if new:
        A = pd.concat([A, pd.DataFrame(new)], ignore_index=True)
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
