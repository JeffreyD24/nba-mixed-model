#!/usr/bin/env python3
"""Daily pipeline health check (same file in the NBA, NHL and NFL repos).

Why: GitHub shows the alert workflow green even when every line check inside it fails (the loop swallows errors).
That hid a 19-hour NFL outage on Nov 2-3, 2026. This script looks inside.

Checks
  a) each scheduled workflow: last completed run succeeded and is recent enough
  b) the last 3 completed alert-loop logs: count 'Check failed' / Traceback lines
  c) newest commit touching each data stream vs a per-stream maximum age
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
if SPORT in ("nfl", "nhl"):
    WORKFLOWS["live.yml"] = (30, "Live line recorder")
if SPORT == "nba":
    WORKFLOWS["econ-gdp.yml"] = (14, "Economics (GDP) recorder")

# data streams: path in repo -> (max hours since newest commit touching it, label)
# Odds files log CHANGES only, so a quiet overnight gap is normal: windows are deliberately wide.
COMMON = {
    "state/alerts.csv": (14, "Alert log"),
    "state/line_history.csv": (14, "DraftKings line history"),
    "research/polymarket": (14, "Polymarket prices"),
    "research/bluesky": (30, "Bluesky reporter posts"),
    "research/odds": (14, "DraftKings odds snapshots"),
}
STREAMS = dict(COMMON)
if SPORT == "nhl":
    STREAMS.update({"research/goalies.csv": (30, "Goalie status log"), "research/line_moves": (30, "Line moves (9 books)")})
if SPORT == "nba":
    STREAMS.update({"state/injury_reports_2026_27.csv": (30, "Official injury reports"),
                    "research/injury_decisions.csv": (72, "Injury decision log")})
if SPORT == "nfl":
    STREAMS.update({"research/injury_decisions.csv": (72, "Key-player injury log"),
                    "research/weather": (6, "Weather forecasts")})

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
for path, (max_h, label) in STREAMS.items():
    try:
        c = api(f"repos/{REPO}/commits?path={path}&per_page=1")
    except Exception as e:
        warn(f"{label} ({path}): could not read commits ({e})"); continue
    if not c:
        bad(f"{label} ({path}): no commits touch it"); continue
    t = parse(c[0]["commit"]["committer"]["date"]); newest[path] = t
    age = hrs(t)
    if age > max_h:
        bad(f"{label} ({path}): newest data {age:.1f} h old (limit {max_h} h)")
    else:
        ok(f"{label}: {age:.1f} h old")

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

# summary -----------------------------------------------------------------------------------------------------------
status = "PROBLEMS" if problems else ("WARNINGS" if warnings else "ALL OK")
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
