"""Bail-out alerts for logged bets (Nov 4, 2026; PROVISIONAL tool). Test: analysis/BAILOUT_PREREG.md, analysis/bailout_test_output.txt.
When the DraftKings line moves k+ pts against a bet Jeffrey logged (state/my_bets.csv), before tip, send one alert per tier with the
cash-out amount worth taking: what riding has been worth on average from that spot in 2023-26 (analysis/bailout_thresholds.csv).
Below that offer, let it ride. Tiers from the pre-registered rule: totals 3 and 4 pts, spreads 1 and 2 pts (larger spread tiers had
under 30 bets). Called from alert.py every check; never allowed to break the alerts. Sent 24 hours a day (Nov 5, 2026: never held for sleep hours).
Log: state/bailout_alerts.csv (one row per bet and tier, sent or not)."""
import os
import numpy as np, pandas as pd

TIERS = {"total": (3, 4), "spread": (1, 2)}
AWAKE = (0, 24)                      # ET hours: 24 hours a day (Jeffrey, Nov 5, 2026; was 4 AM - 8 PM)
EXAMPLE_STAKE = 2.50


def payout(odds):
    try: o = float(odds)
    except (TypeError, ValueError): return 100 / 110
    if not np.isfinite(o) or o == 0: return 100 / 110
    return 100 / abs(o) if o < 0 else o / 100


# Nov 6, 2026 (Jeffrey): a button straight to the open bets at the book the bet was placed at (book column of my_bets.csv),
# for a quick cash-out. Web addresses the apps should open; not yet confirmed on his phone.
MY_BETS = {"DraftKings": "https://sportsbook.draftkings.com/mybets", "FanDuel": "https://sportsbook.fanduel.com/my-bets"}


def mybets_button(book):
    b = next((k for k in MY_BETS if k.lower() in str(book).lower()), None)
    return f"view, Cash out at {b} (My Bets), {MY_BETS[b]}" if b else None


def check(W, NOW, LINE_NOW, MYB, notify):
    STATE = os.path.join(W, "state")
    T = pd.read_csv(os.path.join(W, "analysis", "bailout_thresholds.csv")).set_index(["market", "k"])
    lp = os.path.join(STATE, "bailout_alerts.csv")
    L = pd.read_csv(lp) if os.path.exists(lp) else pd.DataFrame(columns=["bet_key", "tier"])
    done = set(zip(L.bet_key.astype(str), L.tier.astype(int))) if len(L) else set()
    if not len(MYB): return 0
    pending = MYB[MYB.result.isna() | (MYB.result.astype(str).str.strip() == "")] if "result" in MYB else MYB
    by_game = {}
    for (gid, mk), v in LINE_NOW.items(): by_game[(str(v["date"]), v["home"], v["away"], mk)] = dict(v, gid=gid)
    hp = os.path.join(STATE, "line_history.csv")
    LH = pd.read_csv(hp) if os.path.exists(hp) else pd.DataFrame(columns=["game_id", "market", "seen_at_et", "line"])
    LH["t"] = pd.to_datetime(LH.seen_at_et, errors="coerce")
    def dk_at(gid, mk, when):
        """DraftKings line (home view for spreads) at the time the bet was logged; None if unknown"""
        x = LH[(LH.game_id == gid) & (LH.market == mk) & (LH.t <= pd.to_datetime(when, errors="coerce"))]
        return float(x.line.iloc[-1]) if len(x) else None
    awake = AWAKE[0] <= NOW.hour < AWAKE[1]
    new, n_sent = [], 0
    for r in pending.itertuples(index=False):
        # Nov 6, 2026 (Jeffrey): no more bail-out alerts once he has cashed out or hedged (cashout_usd filled, or said so in the notes)
        if pd.notna(getattr(r, "cashout_usd", np.nan)) or any(w in str(getattr(r, "notes", "")).lower() for w in ("cashed out", "hedged")):
            continue
        mk = str(r.market)
        if mk not in TIERS: continue
        v = by_game.get((str(r.date), r.home, r.away, mk))
        if v is None or pd.Timestamp(v["tip_et"]) <= NOW: continue
        cur, line = float(v["cur"]), float(r.line)
        pick = str(r.pick).lower()
        fmt = (lambda x: f"{x:+g}") if mk == "spread" else (lambda x: f"{x:g}")
        ref = dk_at(v["gid"], mk, r.logged_at_et)         # moves are measured on DraftKings from when you bet (your book may differ)
        if mk == "total":
            base = ref if ref is not None else line
            against = (base - cur) if pick == "over" else (cur - base)
            what = f"{pick.upper()} {line:g}"; now_txt = f"{cur:g}"
            other = f"{'UNDER' if pick == 'over' else 'OVER'} {cur:g}"
        else:
            home_bet = pick == r.home
            hl = ref if ref is not None else (line if home_bet else -line)   # DraftKings home-view line when you bet
            against = (cur - hl) if home_bet else (hl - cur)
            team = (v["H"] if home_bet else v["Aw"])
            what = f"{team} {line:+g}"; now_txt = f"{v['H']} {cur:+g}"
            oteam = v["Aw"] if home_bet else v["H"]; oline = -cur if home_bet else cur
            other = f"{oteam} {oline:+g}"
        bet_key = f"{r.logged_at_et}|{r.date}|{r.away}@{r.home}|{mk}|{pick}|{line:g}"
        reached = [k for k in TIERS[mk] if against >= k - 0.01]
        if not reached or (bet_key, reached[-1]) in done or not awake: continue   # overnight: wait for morning, tier stays unsent
        for k in reached[-1:]:                                   # only the highest tier reached; lower ones count as covered
            t = T.loc[(mk, k)]
            per_unit = float(t.p_win) * (1 + payout(r.odds)) + float(t.p_push)
            pct = int(np.floor(per_unit * 100))
            model_txt = f"{v['model']:.1f}" if mk == "total" else f"{v['H']} by {v['model']:+.1f}"
            since = f" (DraftKings was {fmt(hl if mk == 'spread' else base)} when you logged it)" if ref is not None else ""
            body = (f"The line has moved {against:g} pts against your {what} ({r.odds:+g}): DraftKings now {now_txt}{since}, model {model_txt}.\nCash out only if offered at least {pct}% of your stake (e.g. ${np.floor(EXAMPLE_STAKE * per_unit * 100) / 100:.2f} "
                    f"on a ${EXAMPLE_STAKE:.2f} bet). Otherwise let it ride.\nWhy: in 2023-26, bets whose line moved {k}+ pts against went on to win "
                    f"{t.ride_win:.0%} ({int(t.n)} bets), so riding was worth about {pct} cents per $1 staked.")
            if bool(t.hedge_ok):
                body += (f"\nHedge option: bet {other} instead of cashing out. From here the other side won {t.hedge_win:.0%} in 2023-26 "
                         f"(only {int(t.n)} bets, provisional).")
            body += "\nProvisional tool (analysis/BAILOUT_PREREG.md). If you cash out or hedge, tell Claude (amount) and these alerts stop." + v.get("hist", "")
            title = f"BAIL-OUT CHECK - {what}: {v['Aw']} @ {v['H']}, {v['tip']}"
            sent = False
            try: sent = notify(title, body, priority="high", tags="rotating_light", kind="bailout", actions=mybets_button(getattr(r, "book", "")))
            except Exception as e: print("bail-out notify failed:", type(e).__name__)
            new.append(dict(at_et=str(NOW)[:16], bet_key=bet_key, date=r.date, home=r.home, away=r.away, market=mk, pick=pick,
                            bet_line=line, odds=r.odds, tier=k, line_now=cur, moved_against=round(against, 1),
                            cashout_min_pct=pct, sent=bool(sent)))
            for k_ in reached:
                done.add((bet_key, k_))
                if k_ != k: new.append(dict(new[-1], tier=k_, sent=False))
            n_sent += 1
            print("BAIL-OUT CHECK:", title, "|", body.splitlines()[1])
    if new:
        pd.concat([L, pd.DataFrame(new)], ignore_index=True).to_csv(lp, index=False)
    return n_sent
