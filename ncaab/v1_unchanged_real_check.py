"""Real-data companion to ncaab/v1_unchanged_check.py (Nov 6, 2026): today's REAL Action Network and ESPN responses are fetched once, recorded, and
served identically to main's ncaab/live_alert.py and the new one (v1 live + v2 paper), each in a throwaway copy with: empty dk_lines.csv,
live_poll.json 5 minutes ago (so every DraftKings opener counts as fresh and is evaluated), the real live_ratings.json, NTFY_TOPIC unset, and
LIVE_FEATURES (a live_features.csv made today by ncaab/live_features.py). Every v1 edge, verdict, reason and alert must match.
  python ncaab/v1_unchanged_real_check.py WORKDIR LIVE_FEATURES -> ncaab/research/v1_unchanged_real_check_output.txt (via redirect)"""
import os, sys, json, io, shutil, tempfile, runpy, subprocess, contextlib, urllib.request
import pandas as pd
W, FEAT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
NOW = pd.Timestamp.now(tz="America/New_York").tz_localize(None); dates = [str((NOW.normalize() + pd.Timedelta(days=k)).date()) for k in range(4)]
CACHE, real = {}, urllib.request.urlopen
class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False
def recorded(req, timeout=None):
    u = req.full_url if hasattr(req, "full_url") else req
    if "ntfy.sh" in u: raise RuntimeError("ntfy must not be called in this check")
    if u not in CACHE:
        with real(req, timeout=timeout) as r: CACHE[u] = r.read()
    return Resp(CACHE[u])
MAIN = subprocess.run(["git", "-C", W, "show", "origin/main:ncaab/live_alert.py"], capture_output=True, text=True, check=True).stdout
NEW = open(os.path.join(W, "ncaab", "live_alert.py")).read()
def run(src, stop):
    T = tempfile.mkdtemp(); st = os.path.join(T, "ncaab", "state"); os.makedirs(st); os.makedirs(os.path.join(T, "ncaab", "data"))
    for f in ("team_map_an_espn.csv", "live_blendc_v2.json"): shutil.copy(os.path.join(W, "ncaab", "data", f), os.path.join(T, "ncaab", "data"))
    shutil.copy(os.path.join(W, "ncaab", "state", "live_ratings.json"), st); shutil.copy(FEAT, os.path.join(st, "live_features.csv"))
    pd.DataFrame(columns=["an_id", "date", "start", "home_an", "away_an", "home", "away", "first_seen_et", "first_line", "first_home_px", "first_away_px",
                          "last_line", "last_seen_et", "preexisting"]).to_csv(os.path.join(st, "dk_lines.csv"), index=False)
    json.dump(dict(last_poll_et=str(NOW - pd.Timedelta(minutes=5)), dates=dates), open(os.path.join(st, "live_poll.json"), "w"))
    if stop: open(os.path.join(st, "live_stop.txt"), "w").write("STOP test\n")
    p = os.path.join(T, "live_alert_under_test.py"); open(p, "w").write(src)
    os.environ.pop("NTFY_TOPIC", None); urllib.request.urlopen = recorded; old = sys.argv; sys.argv = [p, T]; buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf): runpy.run_path(p, run_name="__main__")
    finally: urllib.request.urlopen = real; sys.argv = old
    rd = lambda f: pd.read_csv(os.path.join(st, f)) if os.path.exists(os.path.join(st, f)) else pd.DataFrame()
    return rd("live_evals.csv"), rd("live_bets.csv"), rd("live_paper_v2.csv"), rd("dk_lines.csv"), buf.getvalue()
V1C = ["an_id", "home", "away", "dk_home_spread", "pred_close_margin", "edge", "verdict", "reason"]
BC = ["an_id", "date", "home", "away", "side", "team", "line", "price", "edge", "pred_close_home", "sent"]
LC = ["an_id", "date", "home", "away", "first_line", "first_home_px", "first_away_px", "last_line", "preexisting"]
def same(a, b, cols):
    if len(a) == 0 and len(b) == 0: return True
    cols = [c for c in cols if c in a]
    try: pd.testing.assert_frame_equal(a[cols].sort_values("an_id").reset_index(drop=True), b[cols].sort_values("an_id").reset_index(drop=True), check_dtype=False); return True
    except AssertionError as ex: print("    DIFF:", str(ex)[:400]); return False
allok = True
for name, stop in (("real responses", False), ("real responses + stop file", True)):
    em, bm, _, lm, om = run(MAIN, stop); en, bn, pn, ln, on = run(NEW, stop)
    sm = sorted(l for l in om.splitlines() if l.startswith("NTFY_TOPIC not set")); sn = sorted(l for l in on.splitlines() if l.startswith("NTFY_TOPIC not set"))
    ok = same(em, en, V1C) & same(bm, bn, BC) & same(lm, ln, LC) & (sm == sn); allok &= ok
    print(f"[{name}] main: {len(lm)} openers captured, {len(em)} evaluated, {len(bm)} v1 alerts | new: {len(ln)} captured, {len(en)} evaluated, {len(bn)} v1 alerts, "
          f"alert texts identical {sm == sn} | v2 paper picks {len(pn)} | v1 identical: {ok}")
    if len(em): print("   v1 reasons:", em.reason.fillna("BET").str.replace(r"edge [0-9.]+ <", "edge <", regex=True).value_counts().to_dict())
    if "v2_reason" in en: print("   v2 reasons:", en.v2_reason.fillna("PAPER").str.replace(r"edge [0-9.]+ <", "edge <", regex=True).value_counts().to_dict())
    print("   new script's last line:", on.strip().splitlines()[-1][:220])
print(f"responses recorded: {len(CACHE)} (Action Network + ESPN, {dates[0]}..{dates[-1]}), fetched at {NOW:%Y-%m-%d %H:%M} ET")
print("RESULT:", "v1 UNCHANGED on real responses" if allok else "MISMATCH")
