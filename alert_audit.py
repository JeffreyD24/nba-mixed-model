#!/usr/bin/env python3
"""Alert-delivery audit, all sports (Nov 6, 2026, Jeffrey: "our daily audits should be checking the health of the alert system").

health_check.py checks that the jobs RUN. This checks that the alerts they send ARRIVE and are usable. It reads the ntfy topic's own
history (ntfy.sh keeps ~12 h, so this runs twice a day: 8:20 AM and 8:20 PM ET) and the alert records of every sport repo.

Checks
  1) delivery: every alert the repos recorded as sent in the window is on the ntfy server (records with sent/pushed = True in
     {nba,nhl,nfl}/state/alerts.csv and {nba,nfl}/state/props_live.csv). A recorded-sent alert missing from ntfy = BAD.
  2) bet links: every bet alert (BET, PROP, REMINDER, BET again) has a one-tap bet-slip button (DraftKings 'outcomes=' or FanDuel
     'addToBetslip'), not just a league page; every BAIL-OUT has a My Bets button. Missing = WARN, listed.
  3) bursts: the most alerts sent within 60 s. Big bursts are when the phone app lost alerts on Nov 6 (17 in 5 s). 5+ = WARN.
  4) retries / failures in the alert logs are counted by each repo's health_check.py (section b).
Writes state/alert_audit_latest.md, appends state/alert_audit_log.csv; pushes a summary (morning: always; evening: only if
something is wrong). Exit 1 when there is a problem.

Usage: python alert_audit.py [WORKDIR] [--no-notify]   (env NTFY_TOPIC; sibling repo clones are used when present, else GitHub raw)
"""
import csv, datetime as dt, io, json, os, re, sys, urllib.request
from zoneinfo import ZoneInfo
import pandas as pd

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
W = os.path.abspath(ARGS[0] if ARGS else ".")
NO_NOTIFY = "--no-notify" in sys.argv
ET = ZoneInfo("America/New_York")
NOW = dt.datetime.now(ET).replace(tzinfo=None)
TOPIC = os.environ.get("NTFY_TOPIC", "")
WINDOW_H = 11.5               # ntfy.sh keeps 12 h of messages
GRACE_MIN = 3                 # an alert recorded in the last few minutes may not be on the server yet
BURST_WARN = 5
TRUE = ("True", "true", "1", "1.0")
problems, warnings, lines = [], [], []
def ok(m): lines.append(f"OK    {m}")
def bad(m): problems.append(m); lines.append(f"BAD   {m}")
def warn(m): warnings.append(m); lines.append(f"WARN  {m}")


def state_csv(repo, name):
    """a sport repo's state file: the sibling clone if there is one, else the public copy on GitHub"""
    local = os.path.join(os.path.dirname(W), repo, "state", name) if os.path.basename(W) != repo else os.path.join(W, "state", name)
    try:
        if os.path.exists(local): return pd.read_csv(local, low_memory=False)
        url = f"https://raw.githubusercontent.com/JeffreyD24/{repo}/main/state/{name}"
        with urllib.request.urlopen(url, timeout=30) as r: return pd.read_csv(io.BytesIO(r.read()), low_memory=False)
    except Exception as e:
        warn(f"{repo}/state/{name}: not readable ({type(e).__name__})"); return pd.DataFrame()


# ---- ntfy history ---------------------------------------------------------------------------------------------------
msgs = []
try:
    with urllib.request.urlopen(f"https://ntfy.sh/{TOPIC}/json?poll=1&since=12h", timeout=30) as r:
        for l in r.read().decode().splitlines():
            m = json.loads(l)
            if m.get("event") == "message":
                m["t"] = dt.datetime.fromtimestamp(m["time"], ET).replace(tzinfo=None); msgs.append(m)
except Exception as e:
    bad(f"could not read the ntfy history ({type(e).__name__}): the audit can't check delivery")
lo = NOW - dt.timedelta(hours=WINDOW_H)
ok(f"ntfy history: {len(msgs)} messages since {min((m['t'] for m in msgs), default=NOW):%a %I:%M %p}")
U = lambda m: m.get("title", "").upper()

# ---- 1) delivery -----------------------------------------------------------------------------------------------------
def near(t, pred, mins=5):
    return any(abs((m["t"] - t).total_seconds()) <= mins * 60 and pred(m) for m in msgs)

missing, checked = [], 0
for repo in ("nba-mixed-model", "nhl-mixed-model", "nfl-mixed-model"):
    A = state_csv(repo, "alerts.csv")
    if len(A) and {"alerted_at_et", "sent", "home", "away"} <= set(A.columns):
        A["t"] = pd.to_datetime(A.alerted_at_et, errors="coerce")
        A = A[A.sent.astype(str).isin(TRUE) & (A.t >= lo) & (A.t <= NOW - dt.timedelta(minutes=GRACE_MIN))]
        if "skipped" in A: A = A[A.skipped.isna()]
        for r in A.drop_duplicates(["game_id", "market", "alerted_at_et"]).itertuples():
            checked += 1
            codes = [str(r.away).upper(), str(r.home).upper()]
            # title + text: since Nov 6 short alerts put the game ("FLA @ WSH") in the text, not the title
            if not near(r.t.to_pydatetime(), lambda m: any(re.search(rf"\b{re.escape(c)}\b", U(m) + " " + m.get("message", "").upper()) for c in codes)):
                missing.append(f"{repo.split('-')[0].upper()} {r.market} {r.away}@{r.home} recorded sent {r.t:%a %I:%M %p}")
    if repo == "nhl-mixed-model": continue
    P = state_csv(repo, "props_live.csv")
    if len(P) and {"logged_at_et", "pushed", "player"} <= set(P.columns):
        P["t"] = pd.to_datetime(P.logged_at_et, errors="coerce")
        P = P[P.pushed.astype(str).isin(TRUE) & (P.t >= lo) & (P.t <= NOW - dt.timedelta(minutes=GRACE_MIN))]
        for r in P.itertuples():
            checked += 1
            if not near(r.t.to_pydatetime(), lambda m: str(r.player).upper() in U(m)):
                missing.append(f"{repo.split('-')[0].upper()} prop {r.player} recorded sent {r.t:%a %I:%M %p}")
if missing:
    bad(f"{len(missing)} of {checked} alerts recorded as sent are NOT on the ntfy server: " + "; ".join(missing[:5]))
else:
    ok(f"delivery: all {checked} alerts recorded as sent in the last {WINDOW_H:g} h are on the ntfy server")

# ---- 2) bet links ----------------------------------------------------------------------------------------------------
BETLIKE = re.compile(r"\bBET\b|\bPROP\b|REMINDER|BET AGAIN|BACK IN RANGE")
direct = lambda m: any(("outcomes=" in a.get("url", "") or "addToBetslip" in a.get("url", "")) for a in m.get("actions", []) or [])
nolink, nobo = [], []
for m in msgs:
    ti = U(m)
    if "DON'T BET" in ti or "HEALTH" in ti or "RECAP" in ti or "SUMMARY" in ti: continue
    if "BAIL-OUT" in ti:
        if not any("mybets" in a.get("url", "").replace("-", "") for a in m.get("actions", []) or []): nobo.append(m)
    elif BETLIKE.search(ti) and not direct(m):
        nolink.append(m)
nbet = sum(1 for m in msgs if BETLIKE.search(U(m)) and "DON'T BET" not in U(m) and "BAIL-OUT" not in U(m))
if nolink:
    warn(f"{len(nolink)} of {nbet} bet alerts had no one-tap bet link: "
         + "; ".join(f"{m['t']:%I:%M %p} {m.get('title', '')[:60]}" for m in nolink[:5]))
else:
    ok(f"bet links: all {nbet} bet alerts had a one-tap bet link")
if nobo: warn(f"{len(nobo)} bail-out alert(s) without a My Bets button")

# ---- 3) bursts -------------------------------------------------------------------------------------------------------
ts = sorted(m["t"] for m in msgs)
burst, at = 0, None
for i, t in enumerate(ts):
    n = sum(1 for u in ts[i:] if (u - t).total_seconds() <= 60)
    if n > burst: burst, at = n, t
if burst >= BURST_WARN:
    warn(f"burst: {burst} alerts within 60 s at {at:%a %I:%M %p} (the phone app has lost alerts in bursts; check the summary push arrived)")
else:
    ok(f"bursts: at most {burst} alerts in any 60 s")

# ---- report ----------------------------------------------------------------------------------------------------------
status = "PROBLEMS" if problems else ("WARNINGS" if warnings else "ALL OK")
report = f"# Alert delivery audit, {NOW:%Y-%m-%d %H:%M} ET\n\nStatus: **{status}**\n\n```\n" + "\n".join(lines) + "\n```\n"
os.makedirs(os.path.join(W, "state"), exist_ok=True)
open(os.path.join(W, "state", "alert_audit_latest.md"), "w").write(report)
lp = os.path.join(W, "state", "alert_audit_log.csv"); new = not os.path.exists(lp)
with open(lp, "a", newline="") as f:
    w = csv.writer(f)
    if new: w.writerow(["checked_et", "status", "checked", "missing", "bet_alerts", "no_link", "max_burst", "detail"])
    w.writerow([f"{NOW:%Y-%m-%d %H:%M}", status, checked, len(missing), nbet, len(nolink), burst, " | ".join(problems + warnings)[:500]])
print(report)
if not NO_NOTIFY and TOPIC and (NOW.hour < 12 or problems or warnings):
    body = ("Alerts recorded as sent, on the ntfy server: " + (f"{checked - len(missing)}/{checked}" if checked else "none in window")
            + f". Bet alerts with a bet link: {nbet - len(nolink)}/{nbet}. Biggest burst: {burst} in 60 s.")
    if problems or warnings: body += "\n" + "\n".join("- " + x[:200] for x in (problems + warnings)[:5])
    try:
        urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=body.encode(), method="POST",
                               headers={"Title": f"[Alert delivery] {status}", "Priority": "default", "Tags": "satellite"}), timeout=20)
    except Exception as e:
        print("ntfy push failed:", e)
sys.exit(1 if problems else 0)
