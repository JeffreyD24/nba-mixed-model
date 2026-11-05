"""
Report watcher (TEST, logged only, no phone pushes). Asked for Nov 4, 2026 after research/spreads/REPORT_SLOT_RESULTS.md showed that
DraftKings prices most of an injury report's news within ~26 minutes, so the only edge is reacting within minutes.
Plan and decision rule: research/spreads/REPORT_WATCH_PLAN.md.

Run every minute by alert_loop.sh. Looks for new official NBA injury report files (15-minute names, plus the older hourly name stamped
:30), and the moment one appears: downloads it, compares every listed player's status with the previous report, rates each change
with that day's saved model (state/model_<date>.json, the same valuation as alert.py's player_swings), and writes one row per changed
player to research/report_watch/<game date>.csv with the minute we first saw the file. Lines are NOT fetched here: pregame.py records
every DraftKings move each minute, and report_watch_grade.py (morning run) joins the two.

Safe for the live loop: short curl timeouts, state saved after every report with atomic writes, a corrupt state file is reset (and
said so), a 403 from the CDN (throttling) pauses the watcher 10 minutes instead of retrying.
  python report_watch.py WORKDIR        exit 0 always (never triggers a check or a push)
"""
import os, sys, json, subprocess, datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
from parse_injury_reports import parse                                       # noqa: E402
from build_report_features import key, FULL2ABBR, ABBR2GAMES                  # noqa: E402

ET = ZoneInfo("America/New_York")
NOW = pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None))
STATE = os.path.join(W, "state"); OUT = os.path.join(W, "research", "report_watch"); TMP = os.path.join(W, "_tmp_report_watch")
BASE = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_"
SEEN = os.path.join(STATE, "report_watch_seen.json")          # {"seen": [names], "pause_until": "...", "style": {"date": "15"|"hourly"}}
LAST = os.path.join(STATE, "report_watch_last.csv")           # the previous report's rows (the comparison point)


def slot_names(x, style):
    """file names for the 15-minute slot starting at x, in the naming style(s) worth trying"""
    out = []
    if style in (None, "15"): out.append(f"{x:%Y-%m-%d}_{x:%I_%M%p}")
    if x.minute == 30 and style in (None, "hourly"): out.append(f"{x:%Y-%m-%d}_{x:%I%p}")
    return out


def candidates(style):
    """(slot time, name) oldest first: this slot and the two before every minute; every 5th minute back 2 hours (late postings)"""
    t = NOW.floor("15min"); back = 8 if NOW.minute % 5 == 0 else 3
    return [(x, n) for k in reversed(range(back)) for x in [t - pd.Timedelta(minutes=15 * k)] for n in slot_names(x, style)]


def name_time(n):
    """slot time of a report name; the hourly name is stamped :30"""
    import re
    m = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{2})(?:_(\d{2}))?(AM|PM)$", str(n))
    if not m: return None
    return pd.to_datetime(f"{m.group(1)} {m.group(2)}:{m.group(3) or '30'}{m.group(4)}", format="%Y-%m-%d %I:%M%p")


def save_json(path, obj):
    tmp = path + ".tmp"; json.dump(obj, open(tmp, "w")); os.replace(tmp, path)


def load_state():
    try:
        js = json.load(open(SEEN)) if os.path.exists(SEEN) else {}
        if isinstance(js, list): js = {"seen": js}
    except Exception as e:
        print("Report watch: memory file unreadable, starting fresh:", type(e).__name__); js = {}
    js.setdefault("seen", []); js.setdefault("style", {}); js.setdefault("pause_until", "")
    return js


def fetch(name):
    """(rows or None, http code)"""
    os.makedirs(TMP, exist_ok=True); tmp = os.path.join(TMP, name + ".pdf")
    r = subprocess.run(["curl", "-s", "--connect-timeout", "5", "-m", "10", "-o", tmp, "-w", "%{http_code}", BASE + name + ".pdf"],
                       capture_output=True, text=True)
    code = r.stdout.strip()
    rows = parse(tmp) if code == "200" and os.path.exists(tmp) and os.path.getsize(tmp) > 1000 else None
    if os.path.exists(tmp): os.remove(tmp)
    return rows, code


def frame(rows, name):
    df = pd.DataFrame(rows, columns=["snapshot", "as_of", "game_date", "game_time_et", "matchup", "team", "player", "status"])
    df["snapshot"] = name                                       # the clean report name (the parser uses the temp file's name)
    df["code"] = df.team.map(FULL2ABBR).map(ABBR2GAMES)
    df["gd"] = pd.to_datetime(df.game_date, format="%m/%d/%Y", errors="coerce").dt.strftime("%Y-%m-%d")
    return df


def main():
    # Nov 5, 2026: watch 24 hours a day (alerts are never held for any hours); reports mostly post ~11 AM - 10 PM ET
    js = load_state()
    if js["pause_until"] and str(NOW) < js["pause_until"]:
        print("Report watch: paused after a 403 until", js["pause_until"]); return
    seen = set(js["seen"]); day = f"{NOW:%Y-%m-%d}"; style = js["style"].get(day)   # "15" once a 15-min name works today
    probed = False
    for x, n in candidates(style):
        if n in seen: continue
        rows, code = fetch(n)
        if code == "403":
            # the CDN answers 403 both for "no such file" (incl. not posted yet) and when throttling. Only for a slot 20+ min old
            # (should be posted by now), and once per run, re-ask for 1 byte of a file we already have: 403 there = throttled -> pause.
            probe = sorted(s for s in seen if s[:10] == day)
            if probe and not probed and NOW - x > pd.Timedelta(minutes=20):
                probed = True
                r = subprocess.run(["curl", "-s", "--connect-timeout", "5", "-m", "10", "-r", "0-0", "-o", os.devnull, "-w", "%{http_code}",
                                    BASE + probe[-1] + ".pdf"], capture_output=True, text=True)
                if r.stdout.strip() == "403":
                    js["pause_until"] = str(NOW + pd.Timedelta(minutes=10)); print("Report watch: CDN throttling (403), pausing 10 min")
                    save_json(SEEN, js)
                    break
            continue
        if rows is None: continue
        seen.add(n)
        if "_" in n[11:]: js["style"][day] = "15"
        try: last_name = str(pd.read_csv(LAST, nrows=1).snapshot.iloc[0]) if os.path.exists(LAST) else None
        except Exception: last_name = None
        lt = name_time(last_name)
        if lt is not None and name_time(n) is not None and name_time(n) < lt:
            print("Report watch:", n, "posted late, older than the last report; recorded as seen, not compared")
        else:
            process(n, frame(rows, n))
        js["seen"] = sorted(s for s in seen if s[:10] >= f"{NOW - pd.Timedelta(days=2):%Y-%m-%d}")
        js["style"] = {k: v for k, v in js["style"].items() if k >= f"{NOW - pd.Timedelta(days=2):%Y-%m-%d}"}
        save_json(SEEN, js)                                     # after every report, so a timeout can't cause re-processing
    else:
        if js["pause_until"]: js["pause_until"] = ""
        save_json(SEEN, js)


def process(name, cur):
    try: prev = pd.read_csv(LAST) if os.path.exists(LAST) else None
    except Exception as e: print("Report watch: previous report unreadable, starting fresh:", type(e).__name__); prev = None
    tmp = LAST + ".tmp"; cur.drop(columns=["code", "gd"]).to_csv(tmp, index=False); os.replace(tmp, LAST)
    if prev is None or prev.empty: print("Report watch: first report stored,", name); return
    prev["code"] = prev.team.map(FULL2ABBR).map(ABBR2GAMES)
    prev["gd"] = pd.to_datetime(prev.game_date, format="%m/%d/%Y", errors="coerce").dt.strftime("%Y-%m-%d")
    prev_name = str(prev.snapshot.iloc[0])
    rows = []
    for gd in sorted(set(cur.gd.dropna())):
        mp = os.path.join(STATE, f"model_{gd}.json")
        if not os.path.exists(mp): continue
        M = json.load(open(mp)); pmx = M["p_miss"]
        for g in M["games"]:
            for team in (g["home"], g["away"]):
                c = cur[(cur.gd == gd) & (cur.code == team)]
                p = prev[(prev.gd == gd) & (prev.code == team)]
                if c.empty or (c.status == "NOT YET SUBMITTED").all(): continue      # not filed in this report (or block dropped): no news
                if p.empty or (p.status == "NOT YET SUBMITTED").all(): continue      # first filing: starting point only
                base = dict(zip(p.player.dropna(), p.status[p.player.notna()]))
                now_ = dict(zip(c.player.dropna(), c.status[c.player.notna()]))
                for pl in set(base) | set(now_):
                    s0, s1 = base.get(pl, "not listed"), now_.get(pl, "not listed")
                    if s0 == s1: continue
                    v = M["players"].get(key(pl))
                    pm0, pm1 = pmx.get(s0, 0.0), pmx.get(s1, 0.0)
                    if v:
                        dm = M["c_off"] * v[0] - M["c_def"] * v[1]; dtot = M["c_off"] * v[0] + M["c_def"] * v[1]
                        d_margin = round((pm1 - pm0) * (dm if team == g["home"] else -dm), 3); d_total = round((pm1 - pm0) * dtot, 3)
                    else: d_margin = d_total = None
                    rows.append(dict(first_seen_et=str(NOW)[:19], report=name, prev_report=prev_name,
                                     report_as_of=str(cur.as_of.dropna().iloc[0]) if cur.as_of.notna().any() else "",
                                     date=gd, game_id=g["game_id"], away=g["away"], home=g["home"], tip_et=g["tip_et"], team=team, player=pl,
                                     from_status=s0, to_status=s1, p_miss_from=round(pm0, 3), p_miss_to=round(pm1, 3), rated=v is not None,
                                     d_home_margin=d_margin, d_total=d_total))
    if not rows: print("Report watch:", name, "no status changes for modeled games"); return
    os.makedirs(OUT, exist_ok=True)
    df = pd.DataFrame(rows)
    for gd, g in df.groupby("date"):
        path = os.path.join(OUT, f"{gd}.csv")
        g.to_csv(path, mode="a", header=not os.path.exists(path), index=False)
    print(f"Report watch: {name} -> {len(df)} status changes logged")


if __name__ == "__main__":
    try: main()
    except Exception as e: print("Report watch failed:", type(e).__name__, str(e)[:120])
