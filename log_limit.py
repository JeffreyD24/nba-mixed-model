"""
Turn a 'Log a limit' issue into a row in state/book_limits.csv (a sportsbook cut your max bet, refused a bet, took away boosts, or closed you).

  python log_limit.py WORKDIR EVENT_JSON

Writes a short reply to state/_limit_reply.md for the workflow to post on the issue. The reply says how many bets (and units) the log
shows at that book up to that day, so a limit can be read against how much was bet there first. Limits are per repo (this sport's
state/); log it in the repo of the sport you were betting, or in any one repo if it hit the whole account.
"""
import os, re, sys, json, datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
import books

W = os.path.abspath(sys.argv[1]); EVENT = json.load(open(sys.argv[2]))
STATE = os.path.join(W, "state")
KINDS = {"some markets": "limit_some", "account-wide": "limit_all", "refused": "refused", "boost": "promos", "closed": "closed"}


def fields(body):
    out, cur = {}, None
    for line in (body or "").splitlines():
        m = re.match(r"^###\s+(.*)$", line.strip())
        if m: cur = m.group(1).strip(); out[cur] = []; continue
        if cur is not None: out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def money(s, what):
    s = str(s).replace("$", "").replace(",", "").strip().lower()
    if s in ("", "_no response_", "none", "n/a", "na", "unknown"): return None
    try: return float(s)
    except ValueError: raise ValueError(f"'{s}' is not a number for {what}")


def main():
    issue = EVENT["issue"]; f = fields(issue.get("body"))
    get = lambda k: "" if f.get(k, "") in ("", "_No response_") else f[k]
    reply = os.path.join(STATE, "_limit_reply.md")
    try:
        day = pd.Timestamp(get("Date it happened") or dt.datetime.now(ZoneInfo("America/New_York")).date()).date()
        book = books.canon_book(get("Sportsbook"))
        if book == books.NOT_RECORDED: raise ValueError("Sportsbook is required")
        what = get("What happened"); kind = next((v for k, v in KINDS.items() if k in what.lower()), "other")
        before, after = money(get("Max bet before ($)"), "max bet before"), money(get("Max bet after ($)"), "max bet after")
        tried = money(get("Stake you tried ($)"), "stake you tried")
        today = dt.datetime.now(ZoneInfo("America/New_York")).date()
        if not (today - dt.timedelta(days=60) <= day <= today): raise ValueError(f"the date {day} is not within the last 60 days or is in the future")
    except Exception as e:
        open(reply, "w").write(f"⚠️ I couldn't log this: {e}.\n\nPlease open a new **Log a limit** form with that fixed. (This issue will be closed.)")
        print("invalid:", e); return
    path = os.path.join(STATE, "book_limits.csv")
    L = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    if len(L) and "issue" in L and (pd.to_numeric(L.issue, errors="coerce") == issue["number"]).any():
        open(reply, "w").write("✅ This limit is already logged."); print("already logged:", issue["number"]); return
    row = dict(logged_at_et=str(dt.datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None, microsecond=0)), issue=issue["number"],
               date=str(day), book=book, event=kind, what=what, max_bet_before=before, max_bet_after=after, stake_tried=tried,
               market=get("Sport / market affected (optional)"), notes=get("Notes (optional)"))
    L = pd.concat([L, pd.DataFrame([row])], ignore_index=True); L.to_csv(path, index=False)
    seen = ""
    bp = os.path.join(STATE, "my_bets.csv")
    if os.path.exists(bp):
        B = pd.read_csv(bp)
        if len(B) and "book" in B:
            B = B[(B.book.map(books.canon_book) == book) & (pd.to_datetime(B.logged_at_et) < pd.Timestamp(day) + pd.Timedelta(days=1))]
            seen = f" This repo's log has {len(B)} bets ({pd.to_numeric(B.stake, errors='coerce').sum():g}u) at {book} up to that day."
    cap = f", max bet {before:g} -> {after:g}" if before is not None and after is not None else (f", max bet now {after:g}" if after is not None else "")
    open(reply, "w").write(f"✅ Logged: **{book}**, {what} on {day}{cap}.{seen}\n\nIt shows in the **By sportsbook** section of `research/edge_stats/REPORT.md` after the next morning run.")
    open(os.path.join(STATE, "_limit_title.txt"), "w").write(f"Limit {day}: {book} ({kind})")
    print("logged:", row)


if __name__ == "__main__":
    main()
