"""NCAAM PROVISIONAL stale-line spreads alerts (Nov 5, 2026). Rule and evidence: ncaab/research/MODEL3_RESULTS_2026-11-05.md; rule review and
live-code review by Fable (both APPROVE WITH FIXES; fixes applied). Runs inside the 5-minute alert loop.
- Polls Action Network's DraftKings (68) and FanDuel (69) college basketball lines for today..+3 days; records when DraftKings' spread is FIRST
  seen (ncaab/state/dk_lines.csv) and its last pre-tip number (the close, for grading).
- A DraftKings opener is "fresh" only if first seen this check, the previous good check was under 20 minutes ago AND its date was already in
  that check's window (no alerts after outages or at a date rollover). Fresh openers are evaluated: predicted close (BLEND-C = const + M2 + M8
  + lagged market model + opener; ncaab/state/live_ratings.json); BET alert when 0.5+ pts off. Filters: both teams 3+ games and a conference id,
  no Connecticut school on either side and no game played in Connecticut, price -115 or better, tip 30+ minutes away, no stop file.
  Evaluations: ncaab/state/live_evals.csv; alerts: ncaab/state/live_bets.csv (saved before the push so a crash cannot re-alert).
- Nov 5, 2026 (Jeffrey's go, 20:05): STALE-LINE v2 decides the alerts. BLEND-C v2 = v1 + 12 layer features (lineup / inferred injuries / travel / rest
  and early-season roster; ncaab/state/live_features.csv from ncaab/live_features.py, same code as the research build) with coefficients
  ncaab/data/live_blendc_v2.json; BET when 0.62+ pts off (bets the same number of games v1 did in the backtest). Evidence: NCAAM repo
  ncaab/research/STALE_LINE_LAYERS_RESULTS_2026-11-05.md (DK 2023-26 matched: 642 bets 58.2% +70.5u CLV +1.38 vs v1 +65.5u CLV +1.29).
  New record: ncaab/state/live_bets_v2.csv. v1 keeps running ON PAPER (no alert): ncaab/state/live_paper_v1.csv. No layer features for a game -> no v2 bet.
  python ncaab/live_alert.py WORKDIR"""
import os, sys, json, time, urllib.request
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); ST = os.path.join(W, "ncaab", "state"); os.makedirs(ST, exist_ok=True)
NOW = pd.Timestamp.now(tz="America/New_York").tz_localize(None)
EDGE, MIN_GAMES, MAX_PRICE, FRESH_MIN, DAYS = 0.5, 3, -115, 20, 4
CT = ("Connecticut", "UConn", "Yale", "Quinnipiac", "Fairfield", "Sacred Heart", "Central Connecticut")
HDR = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
def get(u):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=20) as r: return json.loads(r.read())
        except Exception: time.sleep(2 + 2 * i)
    return None
LP, EP, BP, SP, STOP = (os.path.join(ST, f) for f in ("dk_lines.csv", "live_evals.csv", "live_bets_v2.csv", "live_poll.json", "live_stop.txt"))
PP = os.path.join(ST, "live_paper_v1.csv")                          # v1 picks, paper only (Nov 5, 2026)
V2 = json.load(open(os.path.join(W, "ncaab", "data", "live_blendc_v2.json")))
EDGE_V2 = V2["edge"]                                                # 0.62 (Nov 5, 2026; evidence: live_blendc_v2_fit_output.txt)
LFN = ["lost_min_share", "lost_pts_share", "new_starters", "travel_miles", "tz_shift", "rest_days", "back_to_back", "games_last_7", "R1", "R2", "R3", "R4"]
FP = os.path.join(ST, "live_features.csv")
FT = pd.read_csv(FP, dtype={"hk": str, "ak": str}) if os.path.exists(FP) else pd.DataFrame(columns=["date", "hk", "ak"])
FTI = {(str(r["date"]), r["hk"], r["ak"]): r for _, r in FT.iterrows()}
def layer_diffs(d, h, a, neutral):
    """home - away layer feature differences in Action Network's home/away orientation; None if the game has no features row."""
    r = FTI.get((d, h, a)); sg = 1.0
    if r is None and neutral: r = FTI.get((d, a, h)); sg = -1.0
    if r is None: return None
    return [sg * (0.0 if pd.isna(r["h_" + f] - r["a_" + f]) else float(r["h_" + f] - r["a_" + f])) for f in LFN]
COLS = ["an_id", "date", "start", "home_an", "away_an", "home", "away", "first_seen_et", "first_line", "first_home_px", "first_away_px", "last_line", "last_seen_et", "preexisting"]
L = pd.read_csv(LP) if os.path.exists(LP) else pd.DataFrame(columns=COLS)
poll = json.load(open(SP)) if os.path.exists(SP) else {}
prev = pd.Timestamp(poll["last_poll_et"]) if poll.get("last_poll_et") else None
prev_dates = set(poll.get("dates", []))
recent = prev is not None and (NOW - prev) <= pd.Timedelta(minutes=FRESH_MIN)
stopped = os.path.exists(STOP)
RP = os.path.join(ST, "live_ratings.json"); R = json.load(open(RP)) if os.path.exists(RP) else None
TM = pd.read_csv(os.path.join(W, "ncaab", "data", "team_map_an_espn.csv")); amap = dict(zip(TM.an_id.astype(int), TM.espn_team.astype(int).astype(str)))
dates = [str((NOW.normalize() + pd.Timedelta(days=k)).date()) for k in range(DAYS)]
# ---- fetch everything first (Action Network lines, ESPN schedule); a failed fetch = no state change, no alerts
AN, ES = {}, {}
for d in dates:
    js = get(f"https://api.actionnetwork.com/web/v2/scoreboard/ncaab?bookIds=68,69&division=D1&date={d.replace('-', '')}")
    if js is None or "games" not in js: print("Action Network unavailable; nothing recorded this check"); sys.exit(0)
    AN[d] = js["games"]
    es = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={d.replace('-', '')}&groups=50&limit=500") or {}
    m = {}
    for e in es.get("events", []):
        c = e["competitions"][0]; t = {x["homeAway"]: x for x in c["competitors"]}
        if "home" in t and "away" in t:
            m[(t["home"]["team"]["id"], t["away"]["team"]["id"])] = dict(neutral=bool(c.get("neutralSite")), hc=str(t["home"]["team"].get("conferenceId")),
                ac=str(t["away"]["team"].get("conferenceId")), state=((c.get("venue") or {}).get("address") or {}).get("state"))
    ES[d] = m
def espn_game(d, h, a):
    g = ES[d].get((h, a))
    if g is None:                       # neutral sites: Action Network and ESPN can disagree on which team is "home"
        s = ES[d].get((a, h))
        if s is not None and s["neutral"]: g = dict(s, hc=s["ac"], ac=s["hc"])
    return g
def margin(mod, h, a, hc, ac, hh):
    m = R["models"][mod]; o, dd = m["o"], m["d"]
    if h not in o or a not in o: return None
    v = o[h] - o[a] + dd[a] - dd[h] + 2 * m["hca"] * hh
    if mod == "M8": v += m["co"].get(hc, 0) - m["co"].get(ac, 0) + m["cd"].get(ac, 0) - m["cd"].get(hc, 0)
    return v
def notify(title, body):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic: print("NTFY_TOPIC not set; would have sent:", title, "|", body); return False
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST",
          headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high", "Tags": "basketball",
                   "Actions": "view, Bet on DraftKings, https://sportsbook.draftkings.com/leagues/basketball/ncaab; view, FanDuel, https://sportsbook.fanduel.com/navigation/ncaab"})
    try: urllib.request.urlopen(req, timeout=15); return True
    except Exception as ex: print("ntfy failed:", ex); return False
known = set(L.an_id.astype(int)) if len(L) else set(); idx = {int(a): i for i, a in enumerate(L.an_id)} if len(L) else {}
new_rows, evals, bets, paper = [], [], [], []
for d in dates:
    for g in AN[d]:
        try:
            if g.get("status") != "scheduled": continue
            t = {x["id"]: x for x in g.get("teams", [])}; ev = ((g.get("markets") or {}).get("68") or {}).get("event") or {}
            hs = next((o for o in ev.get("spread", []) if o.get("side") == "home" and not o.get("is_alt_market")), None)
            as_ = next((o for o in ev.get("spread", []) if o.get("side") == "away" and not o.get("is_alt_market")), None)
            if not hs or hs.get("value") is None: continue
            gid = int(g["id"]); line = float(hs["value"]); tip = pd.Timestamp(g.get("start_time")).tz_convert("America/New_York").tz_localize(None)
            if gid in known:
                if gid in idx: L.loc[idx[gid], "last_line"] = line; L.loc[idx[gid], "last_seen_et"] = str(NOW)[:16]
                continue
            fresh = recent and d in prev_dates
            hn, an = t[g["home_team_id"]].get("full_name"), t[g["away_team_id"]].get("full_name")
            new_rows.append(dict(an_id=gid, date=d, start=g.get("start_time"), home_an=g["home_team_id"], away_an=g["away_team_id"], home=hn, away=an,
                                 first_seen_et=str(NOW)[:16], first_line=line, first_home_px=hs.get("odds"), first_away_px=(as_ or {}).get("odds"), last_line=line,
                                 last_seen_et=str(NOW)[:16], preexisting=not fresh)); known.add(gid)
            if not fresh or R is None: continue
            h, a = amap.get(int(g["home_team_id"])), amap.get(int(g["away_team_id"])); why = why1 = None; pc = e = px = pc1 = e1 = None; preds = {}; side = side1 = None
            eg = espn_game(d, h, a) if h and a else None
            def check(ee, thr):
                """same filters for v2 (live) and v1 (paper); returns (reason or None, side, price)"""
                sd = "home" if ee > 0 else "away"; p = hs.get("odds") if sd == "home" else (as_ or {}).get("odds")
                if not np.isfinite(ee): return "rating error", sd, p
                if abs(ee) < thr: return f"edge {abs(ee):.2f} < {thr}", sd, p
                if min(R["games"].get(h, 0), R["games"].get(a, 0)) < MIN_GAMES: return "a team has under 3 games", sd, p
                if "None" in (eg["hc"], eg["ac"]) or "-1" in (R["conf"].get(h, "-1"), R["conf"].get(a, "-1")): return "no conference id", sd, p
                if any(x in str(hn) or x in str(an) for x in CT) or eg.get("state") == "CT": return "Connecticut restriction", sd, p
                if p is None or float(p) < MAX_PRICE: return f"price {p} worse than {MAX_PRICE}", sd, p
                if tip - NOW < pd.Timedelta(minutes=30): return "tip under 30 minutes away", sd, p
                if stopped: return "rule STOPPED (ncaab/state/live_stop.txt)", sd, p
                return None, sd, p
            if eg is None: why = why1 = "game not matched to ESPN"
            else:
                hh = 0.0 if eg["neutral"] else 0.5; opener = -line
                preds = {m: margin(m, h, a, eg["hc"], eg["ac"], hh) for m in ("M2", "M8", "MKTL")}
                if any(v is None for v in preds.values()): why = why1 = "team not rated"
                else:
                    base = [1.0, preds["M2"], preds["M8"], preds["MKTL"], opener]
                    c = R["blend_c"]; pc1 = float(np.dot(c, base)); e1 = pc1 - opener; why1, side1, px1 = check(e1, EDGE)     # v1: paper only
                    ld = layer_diffs(d, h, a, eg["neutral"])
                    if ld is None: why = "no layer features for this game (ncaab/state/live_features.csv)"
                    else:
                        pc = float(np.dot(V2["coef"], base + ld)); e = pc - opener; why, side, px = check(e, EDGE_V2)
            evals.append(dict(at_et=str(NOW)[:16], an_id=gid, home=hn, away=an, dk_home_spread=line, **{k: round(v, 2) for k, v in preds.items() if v is not None},
                              pred_close_margin=round(pc, 2) if pc is not None else None, edge=round(e, 2) if e is not None and np.isfinite(e) else None,
                              verdict="BET" if why is None else "PASS", reason=why, rule="v2",
                              v1_pred_close_margin=round(pc1, 2) if pc1 is not None else None, v1_edge=round(e1, 2) if e1 is not None and np.isfinite(e1) else None,
                              v1_paper="BET" if why1 is None else "PASS", v1_reason=why1))
            if why1 is None:
                tm1 = hn if side1 == "home" else an
                paper.append(dict(at_et=str(NOW)[:16], an_id=gid, date=d, home=hn, away=an, side=side1, team=tm1, line=line if side1 == "home" else -line, price=px1,
                                  edge=round(abs(e1), 2), pred_close_home=round(-pc1, 2), sent="paper"))
            if why is None:
                team = hn if side == "home" else an; bl = line if side == "home" else -line
                fdev = ((g.get("markets") or {}).get("69") or {}).get("event") or {}
                fo = next((o for o in fdev.get("spread", []) if o.get("side") == side and not o.get("is_alt_market")), None)
                fd_txt = f"FanDuel {float(fo['value']):+g} ({float(fo['odds']):+.0f})" if fo and fo.get("value") is not None and fo.get("odds") is not None else "FanDuel: no line yet"
                title = f"[BET] PROVISIONAL NCAAM v2: {team} {bl:+g} ({float(px):+.0f}) DraftKings"
                body = (f"BET {team} {bl:+g} at DraftKings ({float(px):+.0f}): DraftKings' opening number only. {an} @ {hn}, {tip:%a %-I:%M %p}.\n"
                        f"Stale-line rule v2: the opener is {abs(e):.2f} pts off the predicted close ({-pc:+.1f} home; ratings + lineups, travel, rest, roster), "
                        f"so the line should move toward {team}. If it has already moved against you, skip.\nLINES: DraftKings {bl:+g} ({float(px):+.0f}) | {fd_txt}\n"
                        f"PROVISIONAL v2 (2023-26 at DraftKings' opener: 642 bets 58.2%, +70.5u, CLV +1.38). Own record; stops at -15u, or at 100 bets if CLV < +0.63.")
                bets.append(dict(at_et=str(NOW)[:16], an_id=gid, date=d, home=hn, away=an, side=side, team=team, line=bl, price=px, edge=round(abs(e), 2),
                                 pred_close_home=round(-pc, 2), sent=False, title=title, body=body))
        except Exception as ex:
            print("game skipped:", type(ex).__name__, str(ex)[:100])
# ---- save state BEFORE any push (a crash after this cannot re-alert), then send and record 'sent'
if new_rows: L = pd.concat([L, pd.DataFrame(new_rows)], ignore_index=True)
L.to_csv(LP, index=False)
def append(path, rows):
    if not rows: return
    old = pd.read_csv(path) if os.path.exists(path) else None
    (pd.concat([old, pd.DataFrame(rows)], ignore_index=True) if old is not None else pd.DataFrame(rows)).to_csv(path, index=False)
append(EP, evals); append(PP, paper)
append(BP, [{k: v for k, v in b.items() if k not in ("title", "body")} for b in bets])
json.dump(dict(last_poll_et=str(NOW), dates=dates), open(SP, "w"))
if bets:
    Bf = pd.read_csv(BP)
    for b in bets:
        ok = notify(b["title"], b["body"]); Bf.loc[(Bf.an_id == b["an_id"]) & (Bf.at_et == b["at_et"]), "sent"] = ok; print("NCAAM BET:", b["title"])
    Bf.to_csv(BP, index=False)
print(f"NCAAM lines: {len(new_rows)} new DraftKings openers, {len(evals)} evaluated, {len(bets)} BET alerts{' (rule stopped)' if stopped else ''}")
