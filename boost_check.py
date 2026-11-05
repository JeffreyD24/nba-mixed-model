"""
Boost & parlay EV checker (NBA, NHL, NFL). Works from the 5-minute multi-book odds feed (research/live_odds/{sport}/{date}.csv.gz),
with Pinnacle's no-vig price as the fair price whenever the same bet is on Pinnacle.

Two jobs:
  1) SUGGEST - "I have a 30% profit boost at FanDuel, what should I use it on?"
     Ranks every moneyline, spread and total at that book (games not yet started) by boosted EV against Pinnacle's fair price.
     With --legs 2 or 3 it also builds the best parlay from different games (for boost tokens that require a parlay).
  2) CHECK - "Is this boost / parlay / SGP worth it?"
     Each leg is entered as its normal price at the book, optionally with the other side's price, e.g.
         "LeBron over 24.5 pts, -115, -105"   (both sides -> the book's own market de-vigged)
         "Knicks ML, +120"                    (one side  -> a typical margin is removed for that kind of market)
     plus either the boost % or the boosted price the book shows. Legs from the same game are flagged: the fair price below
     treats them as independent, which UNDERSTATES the chance when they move together (star over + team over) and OVERSTATES
     it when they pull apart.

Math: fair probability p (no vig); a profit boost b multiplies the profit, so the boosted decimal price is 1 + (d - 1)(1 + b);
EV per $1 = p * boosted_decimal - 1. For a parlay, p and d are the products over the legs.

  python boost_check.py WORKDIR suggest --book fanduel --boost 30 [--sport nba,nhl,nfl] [--legs 1] [--min-odds -200] [--max-odds 1000]
  python boost_check.py WORKDIR check --legs "Knicks ML, +120, -140" "Over 221.5, -110, -110" [--boost 25 | --boosted +300]
  python boost_check.py WORKDIR issue EVENT_JSON        (the 'Check a boost' GitHub issue form; writes state/_boost_reply.md)
"""
import os, sys, re, json, glob, itertools
import datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

ET = ZoneInfo("America/New_York")
BOOK_KEYS = {"draftkings": "draftkings", "dk": "draftkings", "fanduel": "fanduel", "fd": "fanduel", "betmgm": "betmgm", "mgm": "betmgm",
             "caesars": "williamhill_us", "czr": "williamhill_us", "betrivers": "betrivers"}
# margin removed from a one-sided price when the other side isn't given (typical two-way hold for that kind of bet)
ONE_SIDED_MARGIN = {"main": 0.045, "prop": 0.075, "alt": 0.10, "other": 0.10}


# ---------------- odds helpers ----------------
def dec(american):
    a = float(american)
    return 1 + (a / 100 if a > 0 else 100 / -a)


def amer(decimal):
    if not np.isfinite(decimal) or decimal <= 1: return float("nan")
    return round((decimal - 1) * 100) if decimal >= 2 else round(-100 / (decimal - 1))


def fmt(a):
    return "n/a" if a != a else (f"+{int(a)}" if a > 0 else f"{int(a)}")


def devig2(a1, a2):
    """two-way no-vig probability of side 1 (multiplicative)"""
    q1, q2 = 1 / dec(a1), 1 / dec(a2)
    return q1 / (q1 + q2)


def boosted_dec(d, boost_pct):
    return 1 + (d - 1) * (1 + boost_pct / 100)


def ev(p, d):
    return p * d - 1


# ---------------- the live multi-book feed ----------------
def latest_odds(W, sports):
    """latest snapshot per (sport, event, book, market, outcome, point) for games not yet started"""
    now = dt.datetime.now(ET).replace(tzinfo=None)
    out = []
    for sp in sports:
        files = sorted(glob.glob(os.path.join(W, "research", "live_odds", sp, "*.csv.gz")))[-2:]
        if not files: continue
        d = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
        d = d[d.snapshot_utc == d.snapshot_utc.max()].copy()      # the newest snapshot holds every upcoming game
        d["sport"] = sp
        d = d[pd.to_datetime(d.commence_et) > now]
        out.append(d)
    if not out: return pd.DataFrame(), None
    D = pd.concat(out, ignore_index=True)
    return D, D.snapshot_utc.max()


def fair_table(D):
    """Pinnacle no-vig probability per (event, market, outcome, point)"""
    P = D[D.book == "pinnacle"].copy()
    P["pt"] = P.point.abs().fillna(0)
    rows = []
    for (ev_id, mk, pt), g in P.groupby(["event_id", "market", "pt"]):
        if len(g) != 2: continue
        a, b = g.iloc[0], g.iloc[1]
        pa = devig2(a.price, b.price)
        rows += [dict(event_id=ev_id, market=mk, outcome=a.outcome, point=a.point, p_fair=pa, pin_price=a.price),
                 dict(event_id=ev_id, market=mk, outcome=b.outcome, point=b.point, p_fair=1 - pa, pin_price=b.price)]
    return pd.DataFrame(rows)


def label(r):
    if r.market == "h2h": return f"{r.outcome} ML"
    if r.market == "spreads": return f"{r.outcome} {r.point:+g}"
    return f"{r.outcome} {r.point:g}"


def suggest(W, book, boost, sports=("nba", "nhl", "nfl"), legs=1, min_odds=None, max_odds=None, top=8):
    D, snap = latest_odds(W, sports)
    if D.empty: return "No upcoming games in the odds feed right now.", []
    F = fair_table(D)
    B = D[D.book == BOOK_KEYS.get(book.lower(), book.lower())].merge(F, on=["event_id", "market", "outcome", "point"], how="inner")
    if min_odds is not None: B = B[(B.price >= min_odds) if min_odds > 0 else ((B.price >= min_odds) | (B.price > 0))]
    if max_odds is not None: B = B[(B.price <= max_odds) | (B.price < 0)]
    if B.empty: return f"No {book} lines matched Pinnacle's right now.", []
    B["d"] = B.price.map(dec)
    B["ev_plain"] = B.p_fair * B.d - 1
    B["ev_boost"] = B.p_fair * B.d.map(lambda x: boosted_dec(x, boost)) - 1
    B["game"] = B.away + " @ " + B.home
    B["lbl"] = B.apply(label, axis=1)
    B = B.sort_values("ev_boost", ascending=False)
    picks = []
    if legs <= 1:
        for r in B.head(top).itertuples():
            picks.append(dict(bet=f"{r.sport.upper()} {r.game}: {r.lbl}", price=fmt(r.price), boosted=fmt(amer(boosted_dec(r.d, boost))),
                              fair=fmt(amer(1 / r.p_fair)), ev=r.ev_boost, ev_plain=r.ev_plain, start=str(r.commence_et)[:16]))
    else:
        C = B.drop_duplicates("event_id").head(14)      # one leg per game, best candidates only
        combos = []
        for idx in itertools.combinations(range(len(C)), legs):
            g = C.iloc[list(idx)]
            p, d = g.p_fair.prod(), g.d.prod()
            combos.append((ev(p, boosted_dec(d, boost)), g, p, d))
        combos.sort(key=lambda x: -x[0])
        for e, g, p, d in combos[:3]:
            picks.append(dict(bet=" + ".join(f"{r.sport.upper()} {r.lbl}" for r in g.itertuples()), price=fmt(amer(d)),
                              boosted=fmt(amer(boosted_dec(d, boost))), fair=fmt(amer(1 / p)), ev=e, ev_plain=ev(p, d),
                              start=str(g.commence_et.min())[:16]))
    return f"Odds snapshot {snap} UTC; fair price = Pinnacle no-vig.", picks


# ---------------- check a ticket the user typed in ----------------
def parse_leg(s):
    """'description, price[, other side price][, kind]' -> dict; kind = main | prop | alt | other (guessed if left out)"""
    parts = [x.strip() for x in s.split(",")]
    nums = [p.replace(" ", "") for p in parts[1:] if re.fullmatch(r"[+-]?\d{3,5}", p.replace(" ", ""))]
    kinds = [p.lower() for p in parts[1:] if p.lower() in ONE_SIDED_MARGIN]
    if not nums: raise ValueError(f"no price found in '{s}' (write it like: Knicks ML, +120)")
    price = float(nums[0]); other = float(nums[1]) if len(nums) > 1 else None
    desc = parts[0]
    kind = kinds[0] if kinds else ("prop" if re.search(r"\b(pts|points|reb|ast|threes|3pm|3s|yds|yards|sog|shots|rec|td|goal|assist|pra|blocks|steals|saves)\b",
                                                      desc.lower()) else "alt" if re.search(r"\balt\b|\d+\+", desc.lower()) else "main")
    if kind == "prop" and re.search(r"\d+\+", desc): kind = "alt"          # '30+ points' is an alt (yes-only) prop
    if other is not None:
        p = devig2(price, other); how = "both sides de-vigged"
    else:
        q = 1 / dec(price)
        p = q / (1 + ONE_SIDED_MARGIN[kind]); how = f"~{ONE_SIDED_MARGIN[kind]*100:.1f}% {kind} margin removed (no other side given)"
    return dict(desc=desc, price=price, other=other, p=p, how=how, kind=kind)


def check(legs, boost=None, boosted=None, same_game=False):
    L = [parse_leg(x) for x in legs]
    p = float(np.prod([l["p"] for l in L])); d = float(np.prod([dec(l["price"]) for l in L]))
    lines = []
    for l in L:
        lines.append(f"- {l['desc']}: {fmt(l['price'])} -> fair {fmt(amer(1 / l['p']))} ({l['p']*100:.1f}%; {l['how']})")
    fair = amer(1 / p)
    if boosted is not None:
        bd = dec(boosted); base = f"boosted price {fmt(boosted)}"
    elif boost is not None:
        bd = boosted_dec(d, boost); base = f"{boost:g}% profit boost on {fmt(amer(d))} -> {fmt(amer(bd))}"
    else:
        bd = d; base = f"no boost, straight price {fmt(amer(d))}"
    e = ev(p, bd)
    out = dict(lines=lines, fair=fmt(fair), p=p, base=base, ev=e, n=len(L), unboosted_ev=ev(p, d))
    # what boosted price would be needed to break even
    out["breakeven"] = fmt(amer(1 / p))
    out["same_game"] = same_game and len(L) > 1
    return out


def verdict(e):
    if e >= 0.05: return "BET IT (max stake the boost allows)"
    if e > 0: return "Small edge: fine to bet, not a priority"
    return "SKIP: negative EV"


# ---------------- GitHub issue form ----------------
def _field(body, label):
    m = re.search(rf"### {re.escape(label)}\s*\n+(.*?)(?=\n### |\Z)", body, re.S)
    v = (m.group(1).strip() if m else "")
    return "" if v in ("_No response_", "None") else v


def _num(s):
    s = (s or "").replace("%", "").replace("$", "").strip()
    try: return float(s)
    except Exception: return None


def issue(W, event_path):
    E = json.load(open(event_path)); body = E["issue"]["body"] or ""
    book = _field(body, "Sportsbook") or "FanDuel"
    kind = _field(body, "What kind of boost")
    boost = _num(_field(body, "Boost %"))
    boosted = _num(_field(body, "Boosted price (odds boosts only)"))
    nlegs = int(_num(_field(body, "Legs the boost requires")) or 1)
    sports = [s.strip().lower() for s in (_field(body, "Sports") or "NBA, NHL, NFL").split(",") if s.strip()]
    min_odds = _num(_field(body, "Lowest odds allowed (optional)"))
    maxst = _field(body, "Max stake ($, optional)")
    legs = [x.strip() for x in _field(body, "Bet(s) to check").splitlines() if x.strip() and "," in x]
    same = "same game" in (_field(body, "Are the legs from the same game?") or "").lower()
    md = [f"## Boost check — {book}", ""]
    title = f"Boost: {book}"
    if legs:
        r = check(legs, boost=boost, boosted=boosted, same_game=same)
        md += [f"**{verdict(r['ev'])}** — EV {r['ev']*100:+.1f}% per $1 ({r['base']}).", "",
               f"Fair price for the whole ticket: **{r['fair']}** (win chance {r['p']*100:.1f}%). Anything longer than that is +EV.", "",
               "Legs:"] + r["lines"]
        if boost is None and boosted is None:
            md += ["", f"Without a boost this ticket is EV {r['unboosted_ev']*100:+.1f}%."]
        if r["same_game"]:
            md += ["", "⚠️ Same-game legs: the fair price treats them as independent. If they help each other (star over + team over, "
                   "favorite covers + its QB passing yards), the real chance is HIGHER than shown and the book has usually already "
                   "shortened the price for it. If they work against each other, the real chance is LOWER. Treat this EV as a rough guide."]
        title = f"Boost: {book} {'+' if r['ev'] > 0 else ''}{r['ev']*100:.0f}% EV"
    else:
        head, picks = suggest(W, book, boost or 0, sports=sports, legs=nlegs, min_odds=min_odds)
        md += [f"Best uses of a **{boost:g}% profit boost** at {book}" + (f" ({nlegs}-leg parlay)" if nlegs > 1 else "") + ":", "",
               "| Bet | Price | Boosted | Fair | EV boosted | EV no boost | Starts (ET) |", "|---|---|---|---|---|---|---|"]
        for p in picks:
            md.append(f"| {p['bet']} | {p['price']} | {p['boosted']} | {p['fair']} | {p['ev']*100:+.1f}% | {p['ev_plain']*100:+.1f}% | {p['start']} |")
        _, safe = suggest(W, book, boost or 0, sports=sports, legs=1, min_odds=min_odds, max_odds=150, top=3)
        if nlegs <= 1 and safe:
            md += ["", "Lower-variance options (+150 or shorter; less EV, wins far more often):", "",
                   "| Bet | Price | Boosted | Fair | EV boosted | EV no boost | Starts (ET) |", "|---|---|---|---|---|---|---|"]
            for p in safe:
                md.append(f"| {p['bet']} | {p['price']} | {p['boosted']} | {p['fair']} | {p['ev']*100:+.1f}% | {p['ev_plain']*100:+.1f}% | {p['start']} |")
        md += ["", "Why long shots rank first: a profit boost multiplies the profit, so it's worth more on bigger prices. "
               "Pick from either table; both are +EV. 'EV no boost' above 0 means the line is already better than Pinnacle's fair price."]
        md += ["", head, "Only bets Pinnacle also lists are ranked (that's the fair price). Props and alt lines aren't in this feed yet: "
               "for those, re-open the form and type the bet into 'Bet(s) to check'."]
        if picks: title = f"Boost: {book} {boost:g}% -> {picks[0]['bet'][:60]}"
    if maxst: md += ["", f"Max stake noted: ${maxst}. With a +EV boost, bet the full max; the cap is what keeps it small risk."]
    md += ["", "_If you place it, log it with 'Log a bet' and put 'boost' in the notes so boosts get their own record._"]
    os.makedirs(os.path.join(W, "state"), exist_ok=True)
    open(os.path.join(W, "state", "_boost_reply.md"), "w").write("\n".join(md))
    open(os.path.join(W, "state", "_boost_title.txt"), "w").write(title[:120])
    # keep a record of every check (for the boost record later)
    rec = os.path.join(W, "state", "boost_checks.csv")
    row = pd.DataFrame([dict(checked_at_et=dt.datetime.now(ET).strftime("%Y-%m-%d %H:%M"), issue=E["issue"]["number"], book=book,
                             kind=kind, boost_pct=boost, boosted=boosted, legs=" | ".join(legs), n_legs=len(legs) or nlegs)])
    row.to_csv(rec, mode="a", header=not os.path.exists(rec), index=False)
    print("\n".join(md))


if __name__ == "__main__":
    W = os.path.abspath(sys.argv[1]); mode = sys.argv[2]
    A = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    if mode == "issue":
        issue(W, sys.argv[3])
    elif mode == "suggest":
        head, picks = suggest(W, A("--book", "fanduel"), float(A("--boost", "25")), A("--sport", "nba,nhl,nfl").split(","),
                              int(A("--legs", "1")), _num(A("--min-odds")), _num(A("--max-odds")))
        print(head)
        for p in picks: print(f"{p['ev']*100:+6.1f}%  {p['bet']}  {p['price']} -> {p['boosted']} (fair {p['fair']})  {p['start']}")
    elif mode == "check":
        i = sys.argv.index("--legs"); legs = []
        for x in sys.argv[i + 1:]:
            if x.startswith("--"): break
            legs.append(x)
        r = check(legs, boost=_num(A("--boost")), boosted=_num(A("--boosted")), same_game="--same-game" in sys.argv)
        print("\n".join(r["lines"])); print(f"{r['base']}; fair {r['fair']}; EV {r['ev']*100:+.1f}% -> {verdict(r['ev'])}")
