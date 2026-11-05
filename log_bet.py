"""
Turn a 'Log a bet' issue into a row in state/my_bets.csv.

  python log_bet.py WORKDIR EVENT_JSON

Reads the GitHub issue event, parses the form, validates it, appends the bet, and writes a
short reply to state/_bet_reply.md for the workflow to post on the issue.
"""
import os, re, sys, json, datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
import books

W = os.path.abspath(sys.argv[1]); EVENT = json.load(open(sys.argv[2]))
STATE = os.path.join(W, "state")
TEAMS = {  # code: words that identify the team
    "atl": ["atl", "atlanta", "hawks"], "bos": ["bos", "boston", "celtics"], "bkn": ["bkn", "brk", "brooklyn", "nets"],
    "cha": ["cha", "cho", "charlotte", "hornets"], "chi": ["chi", "chicago", "bulls"], "cle": ["cle", "cleveland", "cavaliers", "cavs"],
    "dal": ["dal", "dallas", "mavericks", "mavs"], "den": ["den", "denver", "nuggets"], "det": ["det", "detroit", "pistons"],
    "gs": ["gs", "gsw", "golden state", "warriors"], "hou": ["hou", "houston", "rockets"], "ind": ["ind", "indiana", "pacers"],
    "lac": ["lac", "clippers", "la clippers"], "lal": ["lal", "lakers", "la lakers"], "mem": ["mem", "memphis", "grizzlies"],
    "mia": ["mia", "miami", "heat"], "mil": ["mil", "milwaukee", "bucks"], "min": ["min", "minnesota", "timberwolves", "wolves"],
    "no": ["no", "nop", "nor", "new orleans", "pelicans", "pels"], "ny": ["ny", "nyk", "new york", "knicks"], "okc": ["okc", "oklahoma city", "thunder"],
    "orl": ["orl", "orlando", "magic"], "phi": ["phi", "philadelphia", "76ers", "sixers"], "phx": ["phx", "pho", "phoenix", "suns"],
    "por": ["por", "portland", "trail blazers", "blazers"], "sac": ["sac", "sacramento", "kings"], "sa": ["sa", "sas", "sa spurs", "san antonio", "spurs"],
    "tor": ["tor", "toronto", "raptors"], "utah": ["utah", "uta", "uth", "jazz"], "wsh": ["wsh", "was", "washington", "wizards"]}
ALIAS = {w: k for k, ws in TEAMS.items() for w in ws}


def team(s):
    s = re.sub(r"[^a-z0-9 ]", "", str(s).lower()).strip()
    if s in ALIAS: return ALIAS[s]
    words = [ALIAS[w] for w in s.split() if w in ALIAS and len(w) >= 3]   # "PHO Suns", "DEN Nuggets"
    if words and len(set(words)) == 1: return words[0]
    for w, k in sorted(ALIAS.items(), key=lambda x: -len(x[0])):
        if len(w) > 3 and w in s: return k
    raise ValueError(f"couldn't recognize the team '{s}'")


def fields(body):
    out, cur = {}, None
    for line in (body or "").splitlines():
        m = re.match(r"^###\s+(.*)$", line.strip())
        if m: cur = m.group(1).strip(); out[cur] = []; continue
        if cur is not None: out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def num(s, what):
    s = str(s).replace("$", "").replace(",", "").strip().lower()
    if s in ("pk", "pick", "pickem", "even", "ev"): return 0.0
    try: return float(s)
    except ValueError: raise ValueError(f"'{s}' is not a number for {what}")


def main():
    issue = EVENT["issue"]
    f = fields(issue.get("body"))
    get = lambda k: "" if f.get(k, "") in ("", "_No response_") else f[k]
    try:
        date = pd.Timestamp(get("Game date")).date()
        away, home = team(get("Away team")), team(get("Home team"))
        market = get("Market").lower().strip()
        if market.startswith("s"): market = "spread"
        elif market.startswith("t") or market.startswith("o") or market.startswith("u"): market = "total"
        elif market.startswith("p"): market = "prop"     # Nov 5, 2026: player props (PROVISIONAL props v1b at FanDuel openers)
        else: raise ValueError("Market must be 'spread', 'total' or 'prop'")
        pick = get("Pick").lower().strip()
        if market == "prop":
            import re as _re
            m = _re.match(r"^(.*?)[ ,]+(over|under|o|u)[ ,]+(?:[\d.]+[ ,]+)?(points|pts|rebounds|reb|assists|ast|threes|3s|3pm|3pt)\b", pick)
            if not m: raise ValueError("For a prop, Pick must look like: Desmond Bane under points")
            prop_player = m.group(1).strip(" ,").title(); prop_side = "over" if m.group(2).startswith("o") else "under"
            prop_stat = {"p": "pts", "r": "reb", "a": "ast", "t": "fg3m", "3": "fg3m"}[m.group(3)[0]]
            pick = f"{prop_player} {prop_side} {prop_stat}"
        elif market == "total":
            if pick.startswith("o"): pick = "over"
            elif pick.startswith("u"): pick = "under"
            else: raise ValueError("For a total, Pick must be 'over' or 'under'")
        else:
            pick = team(pick)
            if pick not in (home, away): raise ValueError(f"Pick '{pick.upper()}' isn't one of the two teams")
        line = num(get("Line you got"), "the line"); odds = num(get("Odds (American)") or "-110", "the odds")
        stake = num(get("Stake (units)") or get("Stake ($)") or "1", "the stake")   # units (Nov 2, 2026: every bet is 1 unit unless stated)
        today = dt.datetime.now(ZoneInfo("America/New_York")).date()
        if not (today - dt.timedelta(days=3) <= date <= today + dt.timedelta(days=10)):
            raise ValueError(f"the game date {date} is more than a few days from today ({today}); check the date")
        if abs(odds) < 100: raise ValueError("Odds should look like -110 or +105")
        if stake <= 0: raise ValueError("Stake must be more than 0")
    except Exception as e:
        open(os.path.join(STATE, "_bet_reply.md"), "w").write(
            f"⚠️ I couldn't log this bet: {e}.\n\nPlease open a new **Log a bet** form with that fixed. (This issue will be closed.)")
        print("invalid:", e); return
    path = os.path.join(STATE, "my_bets.csv")
    B = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    if len(B) and "issue" in B and (pd.to_numeric(B.issue, errors="coerce") == issue["number"]).any():
        open(os.path.join(STATE, "_bet_reply.md"), "w").write("✅ This bet is already logged.")
        print("already logged:", issue["number"]); return          # a retry after this bet was already saved
    row = dict(logged_at_et=str(dt.datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None, microsecond=0)),
               issue=issue["number"], date=str(date), away=away, home=home, market=market, pick=pick, line=line, odds=odds,
               stake=stake, book=(books.canon_book(get("Sportsbook (optional)")) if get("Sportsbook (optional)") else ""), notes=get("Notes (optional)"))
    if market == "prop":     # Fable fix 1: before saving, so the columns exist for grading
        row.update(player=prop_player, side=prop_side, stat=prop_stat)
    B = pd.concat([B, pd.DataFrame([row])], ignore_index=True)
    B.to_csv(path, index=False)
    desc = (f"{pick.upper()} {line:g}" if market in ("total", "prop") else f"{pick.upper()} {line:+g}")
    win = stake * (100 / abs(odds) if odds < 0 else odds / 100)
    open(os.path.join(STATE, "_bet_reply.md"), "w").write(
        f"✅ Logged: **{desc}**, {away.upper()} @ {home.upper()} on {date}, {odds:+g} for {stake:g}u (to win {win:.2f}u).\n\n"
        "It will be graded in the morning run after the game and show up on the **My Bets** sheet of `NBA_Live_Tracker.xlsx`.")
    book = row["book"]
    if not book:        # the book matters for limits and per-book results (see research/edge_stats/REPORT.md)
        open(os.path.join(STATE, "_bet_reply.md"), "a").write("\n\n⚠️ No sportsbook was recorded for this bet. Please fill in the Sportsbook field next time; it feeds the per-book results and limit tracking.")
    open(os.path.join(STATE, "_bet_title.txt"), "w").write(
        f"Bet {date}: {away.upper()} @ {home.upper()} {desc} {odds:+g} {stake:g}u" + (f" ({book})" if book else ""))
    print("logged:", row)


if __name__ == "__main__":
    main()
