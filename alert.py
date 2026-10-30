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

THRESHOLD = 3.0                     # points, for both spreads and totals
MAX_LINE_MOVE = 3.0                 # skip games whose line moved this much since opening (market knows something)
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


def notify(title, body):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC not set; would have sent:", title, "|", body); return False
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST",
                                 headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high", "Tags": "basketball"})
    urllib.request.urlopen(req, timeout=20)
    return True


def main():
    if "--test" in sys.argv:
        ok = notify("Test alert: NBA tracker connected", "If you can read this, phone alerts from your GitHub tracker are working. No bet here.")
        print("Test alert sent." if ok else "Test alert NOT sent: NTFY_TOPIC secret is missing."); return
    if not FORCE and not in_window():
        print(f"{NOW:%H:%M} ET is outside the alert window; nothing to do."); return
    models = sorted(f for f in os.listdir(STATE) if f.startswith("model_") and f[6:16] >= str(TODAY.date()))
    if not models: print("No model saved for today or tomorrow yet."); return
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
    new, n_games = [], 0

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

        L = espn.lines([day], when=("open", "current"))
        for g in M["games"]:
            line = L[(L.home == g["home"]) & (L.away == g["away"])] if len(L) else L
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
            tip = pd.Timestamp(g["tip_et"]).strftime("%a %-I:%M %p")
            H, Aw = g["home"].upper(), g["away"].upper()
            for market in ("spread", "total"):
                if (g["game_id"], market) in done: continue
                cur = ln.get(f"current_{market}"); opn = ln.get(f"open_{market}")
                if cur is None or pd.isna(cur): continue
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
                if abs(e) < THRESHOLD: continue
                skip = None
                if not fresh: skip = "no current injury report"
                elif h is None or a is None: skip = "a team has not filed its injury report"
                elif opn is not None and not pd.isna(opn) and abs(cur - opn) >= MAX_LINE_MOVE:
                    skip = f"line moved {abs(cur - opn):.1f} pts since open"
                rec_row = dict(alerted_at_et=str(NOW), game_id=g["game_id"], date=M["date"], home=g["home"], away=g["away"],
                               tip_et=g["tip_et"], market=market, side=side, line=cur, open_line=opn,
                               model=round(margin if market == "spread" else total, 2), edge=round(abs(e), 2),
                               injury_report=used, sent=False, skipped=skip)
                if skip:
                    if (g["game_id"], market) not in skipped:
                        new.append(rec_row); skipped.add((g["game_id"], market))
                    print("HELD BACK:", title, "|", skip); continue
                body += f"\nInjury report: {used}. Alerts so far: {rec}. Tracking test: the model has not yet proven an edge live."
                rec_row["sent"] = notify(title, body)
                new.append(rec_row); done.add((g["game_id"], market))
                print("ALERT:", title, "|", body)
    if new:
        A = pd.concat([A, pd.DataFrame(new)], ignore_index=True)
        A.to_csv(apath, index=False)
    n_sent = sum(1 for x in new if not x.get("skipped"))
    print(f"{NOW:%H:%M} ET: checked {n_games} upcoming games, {n_sent} alerts sent, {len(new) - n_sent} held back.")


if __name__ == "__main__":
    main()
