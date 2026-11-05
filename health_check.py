#!/usr/bin/env python3
"""Daily pipeline health check (same file in the NBA, NHL and NFL repos).

Why: GitHub shows the alert workflow green even when every line check inside it fails (the loop swallows errors).
That hid a 19-hour NFL outage on Nov 2-3, 2026. This script looks inside.

Checks
  a) each scheduled workflow: last completed run succeeded and is recent enough
  b) the last 3 completed alert-loop logs: count 'Check failed' / Traceback lines
  c) newest commit touching each data stream vs a per-stream maximum age (registry STREAMS; unregistered research/state
     paths and unregistered scheduled workflows are flagged), plus failure messages inside morning/evening/early/live logs
  d) recent 'Alerts' commits exist
  e) sends one ntfy summary EVERY day (silence means the health check itself is broken),
     writes state/health_latest.md and appends state/health_log.csv, exits 1 when something is wrong.

Usage:  python health_check.py [WORKDIR] [--no-notify] [--repo OWNER/NAME]
Needs the GitHub CLI (`gh`) with a token (GH_TOKEN in Actions). Optional env: NTFY_TOPIC.
"""
import csv, datetime as dt, json, os, re, subprocess, sys, urllib.request

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
WORK = ARGS[0] if ARGS else "."
NO_NOTIFY = "--no-notify" in sys.argv
REPO = os.environ.get("GITHUB_REPOSITORY", "")
if "--repo" in sys.argv:
    REPO = sys.argv[sys.argv.index("--repo") + 1]
if not REPO:
    REPO = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
                          capture_output=True, text=True, cwd=WORK).stdout.strip()
SPORT = "nhl" if "nhl" in REPO.lower() else "nfl" if "nfl" in REPO.lower() else "nba"
NOW = dt.datetime.now(dt.timezone.utc)

# ---- settings -------------------------------------------------------------------------------------------------
# workflow file -> (max hours since last completed run, label). Daily jobs get 30 h; the alert loop 3 h.
WORKFLOWS = {
    "alerts.yml": (3, "Line check + alerts"),
    "morning.yml": (30, "Morning run"),
    "evening.yml": (30, "Evening run"),
}
if SPORT in ("nba", "nhl"):
    WORKFLOWS["early.yml"] = (16, "Early model run (2-4 days ahead)")
if SPORT in ("nfl", "nhl", "nba"):
    WORKFLOWS["live.yml"] = (30, "Live line recorder")
if SPORT == "nba":   # Nov 5, 2026: live sharp-money tracker, all five leagues
    WORKFLOWS["sharp-live.yml"] = (2, "Sharp money tracker (about every minute)")
    STREAMS.update({"sharp/live/nba": (24, "Sharp money live captures", "warn")})
if SPORT == "nba":
    WORKFLOWS["econ-gdp.yml"] = (14, "Economics (GDP) recorder")
    WORKFLOWS["ncaab.yml"] = (30, "NCAAM daily (test-only)")        # Nov 5, 2026
    WORKFLOWS["archive-kaggle.yml"] = (30, "Kaggle tables archive (data-source audit, Nov 5 2026)")

# data streams: path in repo -> (max hours since newest commit touching it, label[, "warn"])
# Odds files log CHANGES only, so a quiet overnight gap is normal: windows are deliberately wide.
# A 3rd item "warn" means a stale stream is reported as a WARNING instead of a problem (use while a window is still being tuned).
# RULE: every data path that gets new rows on a regular basis MUST be listed here. The unregistered-path detector below
# warns when research/ or state/ contains something that is neither listed nor in IGNORE, and when a scheduled workflow
# is not in WORKFLOWS. Register new feeds the day they are added.
COMMON = {
    "state/alerts.csv": (14, "Alert log"),
    "state/line_history.csv": (14, "DraftKings line history"),
    "research/polymarket": (14, "Polymarket prices"),
    "research/pregame": (14, "Pre-game lines every minute (all books, all periods)"),
    "research/bluesky": (30, "Bluesky reporter posts"),
    "research/odds": (14, "DraftKings odds snapshots"),
    "research/books": (30, "Book odds snapshots", "warn"),
    "research/news.csv": (30, "ESPN news log", "warn"),
    "research/espn_predictor.csv": (30, "ESPN predictor log", "warn"),
    "research/edge_stats": (30, "Edge statistics (daily)"),
    "research/splits": (30, "Betting splits", "warn"),
    "state/bet_record.csv": (30, "Bet record (daily grading)"),
    "state/picks_log.csv": (30, "Picks log"),
    "state/record_by_version.csv": (30, "Record by model version"),
    "state/provisional_review.md": (30, "Provisional bets review (daily; stop lines in research/PROVISIONAL_BETS.md)"),
    "state/last_run.json": (30, "Last morning/evening run marker", "warn"),
    "state/line_jumps.csv": (72, "Line jumps log", "warn"),
    "state/market_moves.csv": (168, "Market moves log", "warn"),
    "state/poly_paper.csv": (72, "Polymarket paper trades", "warn"),
}
STREAMS = dict(COMMON)
if SPORT == "nba":   # Nov 5, 2026: NCAA men's basketball (test-only): ncaab/daily.py
    STREAMS.update({"ncaab/data/games.csv": (30, "NCAAM scores and lines"), "ncaab/state/test_record.md": (30, "NCAAM test record (daily)"), "ncaab/state/m2_totals_test.md": (30, "NCAAM M2 totals test record (daily)"), "ncaab/state/live_ratings.json": (30, "NCAAM live ratings (daily)"), "ncaab/state/dk_lines.csv": (24, "NCAAM DraftKings first-seen lines (alert loop)", "warn"), "ncaab/state/live_record.md": (30, "NCAAM PROVISIONAL record (daily)")})
if SPORT == "nba":   # Nov 4, 2026: line-move shadow record (analysis/LINE_MOVE_PREREG.md); NBA only for now
    STREAMS["state/shadow_passed.md"] = (30, "Shadow record of bets passed for a line move against (daily)")
if SPORT == "nba":   # Nov 5, 2026: player props shadow (paper) record, props_shadow.py; FanDuel lines + daily picks/grading + box stats
    STREAMS.update({"research/props_fd": (30, "FanDuel player props (hourly)"), "state/props_shadow.csv": (48, "Props shadow record (paper, daily)", "warn"),
                    "data/player_stats": (48, "Player box stats 2026-27 (daily)")})
    WORKFLOWS["props-shadow.yml"] = (3, "Props shadow (FanDuel hourly)")
if SPORT == "nba":   # Nov 5, 2026 data-source audit: daily copy of the Kaggle box-score tables (no commit when unchanged)
    STREAMS["data/external/kaggle"] = (72, "Kaggle tables archive (box scores, schedule)", "warn")
if SPORT == "nhl":
    STREAMS.update({"research/goalies.csv": (30, "Goalie status log"), "research/line_moves": (30, "Line moves (9 books)"),
                    "research/edge": (30, "Edge research files", "warn"), "research/live": (30, "Live line recorder", "warn"),
                    "research/model": (30, "Model output archive", "warn"), "research/nhl_pbp": (48, "Play-by-play", "warn"),
                    "research/shifts": (48, "Shift charts", "warn"), "research/media": (168, "Media log", "warn"),
                    "state/box_2026_27.csv": (30, "Box scores 2026-27", "warn"), "state/shots_2026_27.csv": (30, "Shots 2026-27", "warn"),
                    "state/early": (30, "Early model files", "warn"), "state/picks_log_xg.csv": (30, "xG picks log", "warn"),
                    "state/leaderboard.json": (30, "Leaderboard", "warn"), "state/goalie_news.json": (72, "Goalie news", "warn")})
if SPORT == "nba":
    STREAMS.update({"state/bet_timing.csv": (30, "Bet timing log", "warn"), "state/injury_reports_2026_27.csv": (30, "Official injury reports"),
                    "research/injury_decisions.csv": (72, "Injury decision log"),
                    "research/live": (30, "Live line recorder", "warn"), "research/live_odds": (30, "Live odds", "warn"),
                    "research/model": (30, "Model output archive", "warn"), "research/props": (30, "Player props", "warn"),
                    "research/periods": (48, "Period scores", "warn"), "research/timeline": (48, "Timeline", "warn"),
                    "research/media": (168, "Media log", "warn"), "research/check_log.csv": (30, "Check log", "warn"),
                    "state/picks_log_models.csv": (30, "Picks log by model", "warn"), "state/picks_log_shrunk.csv": (30, "Shrunk picks log", "warn"), "state/picks_log_stack.csv": (30, "Stack picks log", "warn"),
                    "state/nba_luck.json": (30, "Shooting luck", "warn"), "state/nba_shots_2026_27.csv.gz": (30, "Shots 2026-27", "warn"),
                    "state/early": (30, "Early model files", "warn"), "state/pinnacle_now.json": (72, "Pinnacle now", "warn"),
                    "state/injury_status_seen.csv": (72, "Injury status seen", "warn"),
                    "research/report_watch": (72, "Report watcher log (TEST, Nov 4 2026)", "warn"), "state/report_watch.md": (30, "Report watcher grades (daily)", "warn"),
                    "state/report_watch_seen.json": (30, "Report watcher memory", "warn"), "state/altitude_watch.json": (30, "Altitude tripwire watch", "warn")})
if SPORT == "nfl":
    # NFL is weekly: windows are 8-9 days for game-driven files (they go stale after the Super Bowl, expected in the off-season)
    STREAMS.update({"research/injury_decisions.csv": (72, "Key-player injury log"),
                    "research/injury_log": (72, "Injury list change log (new Nov 2026)", "warn"),
                    "research/weather": (6, "Weather forecasts"),
                    "research/live": (216, "Live line recorder", "warn"), "research/model": (216, "Model output archive", "warn"),
                    "research/media": (216, "Media log", "warn"),
                    "state/injury_seen.csv": (72, "Injury seen", "warn"), "state/injury_log_seen.csv": (72, "Injury log memory", "warn"),
                    "state/practice_now.json": (72, "Practice status now", "warn"), "state/weather_now.json": (6, "Weather now", "warn"),
                    "state/h2_totals_watch.csv": (216, "2H totals watch", "warn"), "state/homedog_test.csv": (216, "Home-dog lean test log (test-only)", "warn"), "state/half_lines_h2_2026.csv": (216, "2H lines", "warn")})

# paths that exist in research/ or state/ but are not regular data feeds (docs, one-off analyses, memory files)
IGNORE = {"MONEYLINE_V2_PREREG_2026-11-04.md", "MONEYLINE_V2_RESULTS_2026-11-04.md", "MARKET_EXPANSION_PLAYBOOK_2026-11-04.md", "MARKET_MODELS_PLAN.md", "PROVISIONAL_BETS.md", "RULE_AUDIT_2026-11-04.md", "SPREADS_HANDOFF_2026-11-04.md", "injury_history", "spreads", "derivatives", "market_models", "probes", "report_watch_record.csv", "report_watch_last.csv", "DATA_DICTIONARY.md", "HANDOFF_TO_OPUS.md", "IDEAS_AND_CHECKLIST.md", "LEAKAGE_AUDIT_2026-11-03.md",
          "SHRINK_WEIGHTS_2026-11-03.md", "how_sharp_models_work.md", "health_latest.md", "health_log.csv", "test_alert_result.txt",
          "errors.csv", "community_notes", "linescores.csv", "live_laptop", "minutes", "minutes_history", "model_comparison",
          "nba_tracking", "props_athletes.csv", "tournament", "cold_stretch", "bet_versions.csv", "my_bets.csv",
          "bluesky_seen.json", "news_overrides.json", "news_practice.json", "openers_seen.json", "key_player_alerts.csv",
          "report_snapshots_checked.json", "h2_alerts.csv", "poly_last.json"}
IGNORE_PREFIX = ("model_20",)   # state/model_YYYY-MM-DD.json files (one per game day)

EVENT_DRIVEN = {"health.yml", "log-bet.yml", "log-limit.yml", "bluesky-check.yml", "pm-check-test.yml", "bluesky-watch-test.yml"}

LOG_RUNS = 3                    # alert-loop runs whose logs are read
MAX_FAILED_CHECKS = 0           # 'Check failed' lines tolerated per run (the loop prints one per failed alert.py call)
MAX_ALERT_COMMIT_AGE_H = 6      # at least one 'Alerts' commit this recently while games are on
# ----------------------------------------------------------------------------------------------------------------


def gh(*a, timeout=120):
    r = subprocess.run(["gh", *a], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def api(path):
    rc, out, err = gh("api", path)
    if rc != 0:
        raise RuntimeError(err.strip()[:200])
    return json.loads(out)


def parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def hrs(t):
    return (NOW - t).total_seconds() / 3600


problems, warnings, lines = [], [], []


def ok(msg): lines.append(f"OK    {msg}")
def bad(msg): problems.append(msg); lines.append(f"BAD   {msg}")
def warn(msg): warnings.append(msg); lines.append(f"WARN  {msg}")


# a) workflow runs ------------------------------------------------------------------------------------------------
alert_run_ids = []
for wf, (max_h, label) in WORKFLOWS.items():
    try:
        runs = api(f"repos/{REPO}/actions/workflows/{wf}/runs?per_page=10").get("workflow_runs", [])
    except Exception as e:
        warn(f"{label} ({wf}): could not read runs ({e})"); continue
    done = [r for r in runs if r["status"] == "completed"]
    if not done:
        bad(f"{label} ({wf}): no completed runs"); continue
    last = done[0]
    age = hrs(parse(last["updated_at"]))
    if wf == "alerts.yml":
        alert_run_ids = [r["id"] for r in done if r["conclusion"] in ("success", "failure")][:LOG_RUNS]
    if last["conclusion"] != "success":
        # a cancelled run (queued behind another, superseded) is normal for the alert loop; look one run further
        if last["conclusion"] == "cancelled" and len(done) > 1 and done[1]["conclusion"] == "success":
            last = done[1]; age = hrs(parse(last["updated_at"]))
        else:
            bad(f"{label} ({wf}): last run {last['conclusion']} {age:.1f} h ago")
            continue
    if age > max_h:
        bad(f"{label} ({wf}): last completed run {age:.1f} h ago (limit {max_h} h)")
    else:
        ok(f"{label}: last run {age:.1f} h ago")

# b) inside the alert-loop logs -------------------------------------------------------------------------------------
tot_fail = tot_tb = tot_poly = 0
for rid in alert_run_ids:
    try:
        rc, out, err = gh("run", "view", str(rid), "-R", REPO, "--log", timeout=180)
        if rc != 0:
            warn(f"alert run {rid}: log not readable ({err.strip()[:80]})"); continue
    except Exception as e:
        warn(f"alert run {rid}: log not readable ({e})"); continue
    fail = len(re.findall(r"Check failed; trying again next time", out))
    poly = len(re.findall(r"Polymarket check failed", out))
    pgf = len(re.findall(r"Pregame recorder failed", out)); pgn = len(re.findall(r"pregame: \d+ prices seen", out))
    if pgf > 5 or (pgn == 0 and checks):
        warn(f"alert run {rid}: pre-game line recorder failed {pgf} times, ran OK {pgn} times")
    tb = len(re.findall(r"Traceback \(most recent call last\)", out))
    checks = len(re.findall(r"=== check at", out))
    tot_fail += fail; tot_tb += tb; tot_poly += poly
    first_err = ""
    m = re.search(r"(TypeError|KeyError|ValueError|AttributeError|FileNotFoundError|IndexError|JSONDecodeError)[^\n]{0,140}", out)
    if m:
        first_err = f" first error: {m.group(0)}"
    if fail > MAX_FAILED_CHECKS and checks and fail >= max(1, checks // 2):
        bad(f"alert run {rid}: {fail} of {checks} line checks failed.{first_err}")
    elif fail > MAX_FAILED_CHECKS:
        warn(f"alert run {rid}: {fail} of {checks} line checks failed.{first_err}")
    else:
        ok(f"alert run {rid}: {checks} checks, 0 failed" + (f" ({poly} Polymarket timeouts, harmless)" if poly else ""))
if not alert_run_ids:
    warn("no alert-loop logs to read")

# c) data streams ---------------------------------------------------------------------------------------------------
newest = {}
for path, spec in STREAMS.items():
    max_h, label = spec[0], spec[1]
    soft = len(spec) > 2 and spec[2] == "warn"
    flag = warn if soft else bad
    try:
        c = api(f"repos/{REPO}/commits?path={path}&per_page=1")
    except Exception as e:
        warn(f"{label} ({path}): could not read commits ({e})"); continue
    if not c:
        flag(f"{label} ({path}): no commits touch it"); continue
    t = parse(c[0]["commit"]["committer"]["date"]); newest[path] = t
    age = hrs(t)
    if age > max_h:
        flag(f"{label} ({path}): newest data {age:.1f} h old (limit {max_h} h)")
    else:
        ok(f"{label}: {age:.1f} h old")

# c3) unregistered data paths and unregistered scheduled workflows -------------------------------------------------------
try:
    known = {p.split("/", 1)[1].split("/")[0] for p in STREAMS if "/" in p}
    for top in ("research", "state"):
        for ent in api(f"repos/{REPO}/contents/{top}"):
            n = ent["name"]
            if n in IGNORE or n in known or n.startswith(IGNORE_PREFIX):
                continue
            if any(p.startswith(f"{top}/{n}") for p in STREAMS):
                continue
            warn(f"UNREGISTERED data path {top}/{n}: add it to STREAMS (or IGNORE) in health_check.py")
    for wf in api(f"repos/{REPO}/contents/.github/workflows"):
        fn = wf["name"]
        if fn in WORKFLOWS or fn in EVENT_DRIVEN:
            continue
        rc, txt, _ = gh("api", "-H", "Accept: application/vnd.github.raw", f"repos/{REPO}/contents/.github/workflows/{fn}")
        if rc == 0 and re.search(r"^\s*-?\s*cron:", txt, re.M):
            warn(f"UNREGISTERED scheduled workflow {fn}: add it to WORKFLOWS in health_check.py")
except Exception as e:
    warn(f"unregistered-path scan failed ({e})")

# c4) failure messages inside the other scheduled runs (their steps end in '|| echo "... failed"' so GitHub shows green) ---
STEP_FAIL = re.compile(r"[^\n]*(not updated|not saved|failed;|failed\.|will be retried|try again tomorrow|Traceback \(most recent call last\))[^\n]*")
for wf, (max_h, label) in WORKFLOWS.items():
    if wf == "alerts.yml":
        continue
    try:
        runs = [r for r in api(f"repos/{REPO}/actions/workflows/{wf}/runs?per_page=5").get("workflow_runs", []) if r["status"] == "completed"]
        if not runs:
            continue
        rc, out, err = gh("run", "view", str(runs[0]["id"]), "-R", REPO, "--log", timeout=180)
        if rc != 0:
            warn(f"{label}: log not readable ({err.strip()[:60]})"); continue
        hits = []
        for m in STEP_FAIL.finditer(out):
            s = re.sub(r"^.*?\d{4}-\d\d-\d\dT[\d:.]+Z\s*", "", m.group(0)).strip()
            if s.startswith("echo ") or "|| echo" in s or s in hits:
                continue
            hits.append(s)
        if hits:
            warn(f"{label} (run {runs[0]['id']}): " + "; ".join(h[:90] for h in hits[:3]))
        else:
            ok(f"{label}: no step failures in last run log")
    except Exception as e:
        warn(f"{label}: step-failure scan failed ({e})")

# c2) heartbeat: written by alert_loop.sh only after alert.py itself succeeded --------------------------------------------
MAX_HEARTBEAT_AGE_H = 3
try:
    hb = open(os.path.join(WORK, "state", "heartbeat_alert.txt")).read().strip()
    age = hrs(parse(hb))
    if age > MAX_HEARTBEAT_AGE_H:
        bad(f"last SUCCESSFUL alert.py call was {age:.1f} h ago (limit {MAX_HEARTBEAT_AGE_H} h)")
    else:
        ok(f"last successful alert.py call {age:.1f} h ago")
except FileNotFoundError:
    warn("no state/heartbeat_alert.txt yet (written after the first good alert.py call)")
except Exception as e:
    warn(f"heartbeat unreadable ({e})")

# d) recent 'Alerts' commits ----------------------------------------------------------------------------------------
try:
    since = (NOW - dt.timedelta(hours=MAX_ALERT_COMMIT_AGE_H)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs = api(f"repos/{REPO}/commits?since={since}&per_page=100")
    n_alert = sum(1 for c in cs if c["commit"]["message"].startswith("Alerts "))
    if n_alert == 0:
        bad(f"no 'Alerts' commits in the last {MAX_ALERT_COMMIT_AGE_H} h")
    else:
        ok(f"{n_alert} 'Alerts' commits in the last {MAX_ALERT_COMMIT_AGE_H} h")
except Exception as e:
    warn(f"could not read recent commits ({e})")

# e) provisional bets: a stop or promote line crossed needs a decision (research/PROVISIONAL_BETS.md) -------------------
try:
    pr = open(os.path.join(WORK, "state", "provisional_review.md")).read()
    flagged = [l for l in pr.splitlines() if "Decision: **STOP" in l or "Decision: **PROMOTE" in l]
    for l in flagged: warn("provisional bet needs a decision: " + l.split("**")[1] + " -> " + l.split("Decision: **")[1].rstrip("*"))
    if not flagged: ok("provisional bets: no stop/promote line crossed")
except Exception as e:
    warn(f"could not read state/provisional_review.md ({type(e).__name__})")

# summary -----------------------------------------------------------------------------------------------------------
status ="PROBLEMS" if problems else ("WARNINGS" if warnings else "ALL OK")
stamp = NOW.strftime("%Y-%m-%d %H:%M UTC")
title = f"[{SPORT.upper()} health] {status}"
body = (f"{len(problems)} problem(s), {len(warnings)} warning(s). " if (problems or warnings) else "All pipelines healthy. ")
if problems:
    body += "\n" + "\n".join("- " + p for p in problems[:6])
if warnings and not problems:
    body += "\n" + "\n".join("- " + w for w in warnings[:4])

report = f"# {SPORT.upper()} pipeline health, {stamp}\n\nStatus: **{status}**\n\n```\n" + "\n".join(lines) + "\n```\n"
os.makedirs(os.path.join(WORK, "state"), exist_ok=True)
open(os.path.join(WORK, "state", "health_latest.md"), "w").write(report)
logp = os.path.join(WORK, "state", "health_log.csv")
new = not os.path.exists(logp)
with open(logp, "a", newline="") as f:
    w = csv.writer(f)
    if new:
        w.writerow(["checked_utc", "status", "problems", "warnings", "alert_checks_failed", "polymarket_timeouts", "detail"])
    w.writerow([stamp, status, len(problems), len(warnings), tot_fail, tot_poly, " | ".join(problems + warnings)[:500]])
print(report)

topic = os.environ.get("NTFY_TOPIC")
if NO_NOTIFY or not topic:
    print("(no ntfy push:", "--no-notify" if NO_NOTIFY else "NTFY_TOPIC not set", ")")
else:
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST",
                                     headers={"Title": title.encode("ascii", "ignore").decode(),
                                              "Priority": "high" if problems else "low",
                                              "Tags": "rotating_light" if problems else "white_check_mark"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"ntfy accepted (HTTP {resp.status})")
    except Exception as e:
        print("ntfy push failed:", e)
sys.exit(1 if problems else 0)
