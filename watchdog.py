"""
Pipeline watchdog (Nov 5, 2026; Jeffrey: "is there a different way for us to find out faster when something isn't running?").
Runs every 10 minutes (nba-mixed-model watchdog.yml; it has the phone-alert secret). Checks every live pipeline in nba/nhl/nfl-mixed-model and pushes ONE phone alert when
something breaks (and one when it recovers). The daily health checks stay as the full review; this only catches breakage fast.

Checks per pipeline:
  - the newest run of a workflow FAILED                      -> problem
  - a loop workflow (alerts, props, sharp money) has no run in progress and none started recently -> problem
  - a file the loop writes after a successful check (heartbeat / snapshot log) has not been committed recently -> problem
    (this catches the silent case: a step fails inside '|| echo', GitHub shows green, but nothing is saved)
  - daily jobs (morning / evening / early / health): newest run failed, or none in the last ~26 h

  python watchdog.py WORKDIR [--no-notify]
State: state/watchdog.json (open problems, so each one pushes once). Log: state/watchdog_log.csv.
"""
import os, sys, json, urllib.request, urllib.error
import datetime as dt

W = os.path.abspath(sys.argv[1]); NO_NOTIFY = "--no-notify" in sys.argv
OWNER = "JeffreyD24"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
NOW = dt.datetime.now(dt.timezone.utc)

# (repo, workflow file, label, kind, max minutes since the newest run started / file committed)
LOOPS = [
    ("nba-mixed-model", "alerts.yml", "NBA alert loop", 30), ("nhl-mixed-model", "alerts.yml", "NHL alert loop", 30),
    ("nfl-mixed-model", "alerts.yml", "NFL alert loop", 30), ("nba-mixed-model", "props-loop.yml", "NBA props loop", 30),
    ("nba-mixed-model", "sharp-live.yml", "Sharp money tracker", 60),
]
HEARTBEATS = [   # file committed by a loop only after its check really worked
    ("nba-mixed-model", "state/heartbeat_alert.txt", "NBA alert checks", 25), ("nhl-mixed-model", "state/heartbeat_alert.txt", "NHL alert checks", 25),
    ("nfl-mixed-model", "state/heartbeat_alert.txt", "NFL alert checks", 25), ("nba-mixed-model", "state/props_fd_runs.csv", "FanDuel prop snapshots", 20),
]
DAILY = [(r, wf, f"{r.split('-')[0].upper()} {lab}", 26 * 60) for r in ("nba-mixed-model", "nhl-mixed-model", "nfl-mixed-model")
         for wf, lab in (("morning.yml", "morning run"), ("evening.yml", "evening run"), ("health.yml", "daily health check"))]
DAILY += [("nba-mixed-model", "early.yml", "NBA early model", 14 * 60), ("nhl-mixed-model", "early.yml", "NHL early model", 14 * 60),
          ("nba-mixed-model", "props-shadow.yml", "NBA props daily (grading, paper picks)", 3 * 60)]


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={"Accept": "application/vnd.github+json", "User-Agent": "watchdog",
                                                                            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())


def age_min(ts): return (NOW - dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 60


problems, checked = {}, 0
for repo, wf, lab, limit in LOOPS + DAILY:
    try:
        runs = api(f"/repos/{OWNER}/{repo}/actions/workflows/{wf}/runs?per_page=6").get("workflow_runs", [])
    except Exception as e:
        problems[f"api|{repo}|{wf}"] = f"{lab}: could not read its runs ({type(e).__name__})"; continue
    checked += 1
    if not runs: problems[f"none|{repo}|{wf}"] = f"{lab}: has never run"; continue
    live = [r for r in runs if r["status"] in ("in_progress", "queued")]
    done = [r for r in runs if r["status"] == "completed" and r["conclusion"] in ("success", "failure")]   # newest finished run, any trigger
    if done and done[0]["conclusion"] == "failure":
        problems[f"fail|{repo}|{wf}"] = f"{lab}: last run FAILED {age_min(done[0]['updated_at']):.0f} min ago ({done[0]['html_url']})"
    newest = min(age_min(r["created_at"]) for r in runs)
    if not live and newest > limit:
        problems[f"stale|{repo}|{wf}"] = f"{lab}: no run for {newest:.0f} min (expected within {limit})"
for repo, path, lab, limit in HEARTBEATS:
    try:
        c = api(f"/repos/{OWNER}/{repo}/commits?path={path}&per_page=1")
    except Exception as e:
        problems[f"api|{repo}|{path}"] = f"{lab}: could not read commits ({type(e).__name__})"; continue
    checked += 1
    if not c: problems[f"hb|{repo}|{path}"] = f"{lab}: {path} never saved"; continue
    a = age_min(c[0]["commit"]["committer"]["date"])
    if a > limit: problems[f"hb|{repo}|{path}"] = f"{lab}: nothing saved for {a:.0f} min (expected every few minutes)"

SP = os.path.join(W, "state", "watchdog.json"); os.makedirs(os.path.dirname(SP), exist_ok=True)
old = json.load(open(SP)) if os.path.exists(SP) else {}
new = {k: v for k, v in problems.items() if k not in old}
fixed = {k: v for k, v in old.items() if k not in problems}
json.dump(problems, open(SP, "w"), indent=1)
LP = os.path.join(W, "state", "watchdog_log.csv")
hdr = not os.path.exists(LP)
with open(LP, "a") as f:
    if hdr: f.write("time_utc,event,detail\n")
    for k, v in new.items(): f.write(f"{NOW:%Y-%m-%d %H:%M},problem,\"{v}\"\n")
    for k, v in fixed.items(): f.write(f"{NOW:%Y-%m-%d %H:%M},fixed,\"{v}\"\n")
print(f"checked {checked}; open problems {len(problems)}; new {len(new)}; fixed {len(fixed)}")
for v in problems.values(): print("  -", v)


def push(title, body):
    topic = os.environ.get("NTFY_TOPIC")
    if NO_NOTIFY or not topic: print("(no push)", title, "|", body); return
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode(), method="POST",
                                 headers={"Title": title, "Priority": "default", "Tags": "warning"})
    urllib.request.urlopen(req, timeout=20)


if new:
    push(f"PIPELINE PROBLEM ({len(new)})", "\n".join(f"- {v}" for v in new.values()) + "\nI'll push again when it's fixed.")
if fixed:
    push(f"PIPELINE FIXED ({len(fixed)})", "\n".join(f"- {v}" for v in fixed.values()))
