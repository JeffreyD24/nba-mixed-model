"""Check before merging stale-line v2 as a PAPER shadow (Nov 6, 2026; betting-goals handoffs/2026-11-06/1020_ncaam-stale-line-v2-paper-and-sbr-test.md, Task 1 step 5):
main's ncaab/live_alert.py and the new one, run on two throwaway copies with IDENTICAL inputs, must give the same v1 edges, verdicts, reasons and alerts.
ESPN and Action Network are not reachable from the session that ran this, so the inputs are synthetic responses built offline from real data: 72 games
between real rated teams (team map, ratings, venues), DraftKings openers set at the BLEND-C prediction plus noise (so some cross the 0.5 edge), plus edge
cases (price -120, neutral site with ESPN's home/away swapped, a Connecticut school, tip in 20 minutes, unrated team, a team with under 3 games).
Both scripts get the same responses (urllib patched in-process), the same state (empty dk_lines.csv, live_poll.json 5 minutes ago), NTFY_TOPIC unset.
In the copies, live_ratings.json game counts are raised to 5 for the synthetic teams (same for both) so the filters after "3+ games" are reached.
Scenarios: A normal; B stop file present (v1 must stop, v2 paper must keep logging); C features file older than 1 day; D malformed features file;
E no features file. v2 features come from ncaab/layer_features.py (the live code path) for the synthetic games.
  python ncaab/v1_unchanged_check.py WORKDIR -> ncaab/research/v1_unchanged_check_output.txt (via tee)"""
import os, sys, json, io, shutil, tempfile, runpy, subprocess, contextlib, importlib.util, urllib.request
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); rng = np.random.default_rng(11)
NOW = pd.Timestamp.now(tz="America/New_York").tz_localize(None); dates = [str((NOW.normalize() + pd.Timedelta(days=k)).date()) for k in range(4)]
R = json.load(open(os.path.join(W, "ncaab", "state", "live_ratings.json")))
TM = pd.read_csv(os.path.join(W, "ncaab", "data", "team_map_an_espn.csv")); TM["espn_team"] = TM.espn_team.astype(str)
TM = TM[TM.espn_team.isin(R["models"]["M2"]["o"]) & TM.espn_team.isin(R["models"]["MKTL"]["o"]) & TM.espn_team.map(lambda t: R["conf"].get(t, "-1") != "-1")]
CT = ("Connecticut", "UConn", "Yale", "Quinnipiac", "Fairfield", "Sacred Heart", "Central Connecticut")
TM = TM[~TM.an_name.map(lambda n: any(x in n for x in CT))].drop_duplicates("espn_team").reset_index(drop=True)
G = pd.read_csv(os.path.join(W, "ncaab", "data", "all_games.csv"), low_memory=False, usecols=["season", "espn_id", "hk"])
V = pd.concat([pd.read_csv(os.path.join(W, "ncaab", "data", "box", f"teams_{s}.csv.gz"), usecols=["espn_id", "city", "state"]) for s in (2026, 2027)]).drop_duplicates("espn_id")
V = V.merge(G, on="espn_id"); V["hk"] = V.hk.astype(str); home_venue = V.groupby("hk")[["city", "state"]].last().to_dict("index")
TM = TM[TM.espn_team.isin(home_venue)].reset_index(drop=True)
pick = TM.sample(144, random_state=3).reset_index(drop=True)
def mg(mod, h, a, hh):
    m = R["models"][mod]; v = m["o"][h] - m["o"][a] + m["d"][a] - m["d"][h] + 2 * m["hca"] * hh
    if mod == "M8": v += m["co"].get(R["conf"][h], 0) - m["co"].get(R["conf"][a], 0) + m["cd"].get(R["conf"][a], 0) - m["cd"].get(R["conf"][h], 0)
    return v
games = []
for i in range(72):
    hr, ar = pick.iloc[2 * i], pick.iloc[2 * i + 1]; h, a = hr.espn_team, ar.espn_team; d = dates[1 + i % 3]
    neutral = i % 9 == 4; hh = 0.0 if neutral else 0.5
    p = {m: mg(m, h, a, hh) for m in ("M2", "M8", "MKTL")}; c = R["blend_c"]
    op = round((c[0] + c[1] * p["M2"] + c[2] * p["M8"] + c[3] * p["MKTL"]) / (1 - c[4]) + rng.normal(0, 6)) / 1.0   # opener near the model, noise sd 6
    op = round(op * 2) / 2; hpx, apx = -110, -110
    if i == 5: hpx = apx = -120                                          # price filter
    tip = pd.Timestamp(f"{d} 19:00", tz="America/New_York")
    if i == 7: d = dates[0]; tip = (pd.Timestamp.now(tz="America/New_York") + pd.Timedelta(minutes=20)).floor("min")   # tip under 30 minutes
    games.append(dict(i=i, d=d, gid=990000 + i, han=int(hr.an_id), aan=int(ar.an_id), hn=hr.an_name, an=ar.an_name, h=h, a=a, line=-op, hpx=hpx, apx=apx,
                      tip=tip, neutral=neutral, swap=(neutral and i % 2 == 0), city=home_venue[h]["city"], state=home_venue[h]["state"], eid=980000000 + i))
ct = TM[TM.an_name.str.contains("Connecticut|UConn")] if False else None
GM = pd.DataFrame(games)
# ---- synthetic responses
def an_json(d):
    out = []
    for g in GM[GM.d == d].itertuples():
        sp = lambda side, v, px: dict(side=side, value=v, odds=px, is_alt_market=False)
        out.append(dict(id=g.gid, status="scheduled", start_time=g.tip.tz_convert("UTC").isoformat(), home_team_id=g.han, away_team_id=g.aan,
                        teams=[dict(id=g.han, full_name=g.hn), dict(id=g.aan, full_name=g.an)],
                        markets={"68": dict(event=dict(spread=[sp("home", g.line, g.hpx), sp("away", -g.line, g.apx)])),
                                 "69": dict(event=dict(spread=[sp("home", g.line + 0.5, -108), sp("away", -g.line - 0.5, -112)]))}))
    return dict(games=out)
def es_json(d):
    ev = []
    for g in GM[GM.d == d].itertuples():
        hs, as_ = (g.a, g.h) if g.swap else (g.h, g.a)
        comp = lambda ha, t: dict(homeAway=ha, team=dict(id=t, conferenceId=R["conf"][t]))
        ev.append(dict(id=str(g.eid), competitions=[dict(neutralSite=g.neutral, competitors=[comp("home", hs), comp("away", as_)],
                                                         venue=dict(address=dict(city=g.city, state="CT" if g.i == 9 else g.state)))]))
    return dict(events=ev)
class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False
def fake_urlopen(req, timeout=None):
    u = req.full_url if hasattr(req, "full_url") else req
    if "ntfy.sh" in u: raise RuntimeError("ntfy must not be called in this check")
    dd = (u.split("date=")[1][:8] if "actionnetwork" in u else u.split("dates=")[1][:8]); d = f"{dd[:4]}-{dd[4:6]}-{dd[6:]}"
    return Resp(json.dumps(an_json(d) if "actionnetwork" in u else es_json(d)).encode())
# ---- v2 features for the synthetic games from the live code path
spec = importlib.util.spec_from_file_location("lf", os.path.join(W, "ncaab", "layer_features.py")); lf = importlib.util.module_from_spec(spec); spec.loader.exec_module(lf)
cur = int(G.season.max())
X = pd.DataFrame(dict(espn_id=GM.eid, season=cur, date=GM.d, hk=np.where(GM.swap, GM.a, GM.h), ak=np.where(GM.swap, GM.h, GM.a), neutral=GM.neutral, city=GM.city, state=GM.state))
F = lf.build(W, [cur], extra=X); F = X[["espn_id", "date", "hk", "ak", "neutral"]].merge(F, on="espn_id", how="left")
F = F[F.espn_id != 980000011]                                             # one game without a features row
F["made_at_et"] = str(NOW)[:16]
MAIN = subprocess.run(["git", "-C", W, "show", "origin/main:ncaab/live_alert.py"], capture_output=True, text=True, check=True).stdout
NEW = open(os.path.join(W, "ncaab", "live_alert.py")).read()
def make_copy(feat):
    T = tempfile.mkdtemp(); os.makedirs(os.path.join(T, "ncaab", "state")); os.makedirs(os.path.join(T, "ncaab", "data"))
    shutil.copy(os.path.join(W, "ncaab", "data", "team_map_an_espn.csv"), os.path.join(T, "ncaab", "data"))
    shutil.copy(os.path.join(W, "ncaab", "data", "live_blendc_v2.json"), os.path.join(T, "ncaab", "data"))
    R2 = json.loads(json.dumps(R))
    for t in set(GM.h) | set(GM.a): R2["games"][t] = 5
    R2["games"][GM.h[13]] = 2                                              # one team with under 3 games
    json.dump(R2, open(os.path.join(T, "ncaab", "state", "live_ratings.json"), "w"))
    pd.DataFrame(columns=["an_id", "date", "start", "home_an", "away_an", "home", "away", "first_seen_et", "first_line", "first_home_px", "first_away_px",
                          "last_line", "last_seen_et", "preexisting"]).to_csv(os.path.join(T, "ncaab", "state", "dk_lines.csv"), index=False)
    json.dump(dict(last_poll_et=str(NOW - pd.Timedelta(minutes=5)), dates=dates), open(os.path.join(T, "ncaab", "state", "live_poll.json"), "w"))
    fp = os.path.join(T, "ncaab", "state", "live_features.csv")
    if feat == "ok": F.to_csv(fp, index=False)
    elif feat == "stale": F.assign(made_at_et=str(NOW - pd.Timedelta(hours=30))[:16]).to_csv(fp, index=False)
    elif feat == "malformed": open(fp, "w").write('espn_id,date,hk\n1,"2026-11-0\n\x00\x00broken,,,,,\n')
    return T
def run(src, T, stop):
    if stop: open(os.path.join(T, "ncaab", "state", "live_stop.txt"), "w").write("STOP test\n")
    p = os.path.join(T, "live_alert_under_test.py"); open(p, "w").write(src)
    os.environ.pop("NTFY_TOPIC", None); orig = urllib.request.urlopen; urllib.request.urlopen = fake_urlopen; old = sys.argv; sys.argv = [p, T]; buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf): runpy.run_path(p, run_name="__main__")
    finally: urllib.request.urlopen = orig; sys.argv = old
    st = os.path.join(T, "ncaab", "state")
    rd = lambda f: pd.read_csv(os.path.join(st, f)) if os.path.exists(os.path.join(st, f)) else pd.DataFrame()
    return rd("live_evals.csv"), rd("live_bets.csv"), rd("live_paper_v2.csv"), rd("dk_lines.csv"), buf.getvalue()
V1C = ["an_id", "home", "away", "dk_home_spread", "M2", "M8", "MKTL", "pred_close_margin", "edge", "verdict", "reason"]
BC = ["an_id", "date", "home", "away", "side", "team", "line", "price", "edge", "pred_close_home", "sent"]
LC = ["an_id", "date", "home", "away", "first_line", "first_home_px", "first_away_px", "last_line", "preexisting"]
def same(a, b, cols):
    if len(a) == 0 and len(b) == 0: return True
    a, b = a[cols].sort_values("an_id").reset_index(drop=True), b[cols].sort_values("an_id").reset_index(drop=True)
    try: pd.testing.assert_frame_equal(a, b, check_dtype=False); return True
    except AssertionError as ex: print("    DIFF:", str(ex)[:400]); return False
allok = True
for name, feat, stop in (("A normal", "ok", False), ("B stop file present", "ok", True), ("C features older than 1 day", "stale", False),
                         ("D malformed features file", "malformed", False), ("E no features file", "none", False)):
    em, bm, _, lm, om = run(MAIN, make_copy(feat), stop); en, bn, pn, ln, on = run(NEW, make_copy(feat), stop)
    sent_m = sorted(l for l in om.splitlines() if l.startswith("NTFY_TOPIC not set")); sent_n = sorted(l for l in on.splitlines() if l.startswith("NTFY_TOPIC not set"))
    ok = same(em, en, V1C) & same(bm, bn, BC) & same(lm, ln, LC) & (sent_m == sent_n)
    allok &= ok
    print(f"[{name}] main: {len(em)} evaluated, {len(bm)} v1 alerts | new: {len(en)} evaluated, {len(bn)} v1 alerts, alert texts identical {sent_m == sent_n} "
          f"| v2 paper picks {len(pn)} | v1 identical: {ok}")
    print("   v1 verdicts:", em.verdict.value_counts().to_dict() if len(em) else {}, "| v1 reasons:", em.reason.fillna("BET").str.replace(r"edge [0-9.]+ <", "edge <", regex=True).value_counts().to_dict() if len(em) else {})
    if "v2_verdict" in en:
        print("   v2:", en.v2_verdict.value_counts().to_dict(), "| v2 reasons:", en.v2_reason.fillna("PAPER").str.replace(r"edge [0-9.]+ <", "edge <", regex=True).value_counts().to_dict())
    print("   new script's last line:", on.strip().splitlines()[-1][:220])
    if stop: print("   stop file: v1 alerts", len(bn), "(must be 0); v2 paper picks", len(pn), "(must be > 0)"); allok &= (len(bn) == 0 and len(pn) > 0)
    if name.startswith("A"):
        both = en.dropna(subset=["edge", "v2_edge"]); print(f"   v1 vs v2 edge correlation on {len(both)} games: {np.corrcoef(both.edge, both.v2_edge)[0, 1]:.3f}; "
                                                       f"v2 never alerts: {not any('v2' in l for l in sent_n)}")
print("RESULT:", "v1 UNCHANGED in every scenario" if allok else "MISMATCH")
