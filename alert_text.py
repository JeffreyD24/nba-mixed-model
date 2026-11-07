"""Phone-alert titles that fit on one line (Nov 7, 2026, Jeffrey: "make sure the titles don't get cut off, like in the Jase alert").
The ntfy iPhone app cut some titles at about 38 characters with '...' ("BET again Jase Richardson UNDER 2.5 reb..."), while others
wrapped; which ones it cuts is not predictable, so every title is kept to MAX characters. When a title has to be shortened, the
full title becomes the first line of the message, so nothing is lost. Same file in every sport repo."""
import re

MAX = 34
_STEPS = [
    (r" \| BEST AT FANDUEL", ""),
    (r" at DraftKings\b", " DK"), (r" at FanDuel\b", " FD"), (r" at Fanatics\b", " Fanatics"),
    (r"\breceiving yards\b", "rec yds"), (r"\brebounds\b", "reb"), (r"\bpoints\b", "pts"), (r"\bassists\b", "ast"),
    (r"\breceptions\b", "rec"), (r"\bthrees\b", "3s"), (r"\bgoals\b", "G"), (r"\bshots on goal\b", "SOG"),
    (r"^STOP: don't bet ", "STOP: "), (r"^REMINDER: BET ", "REMINDER: "),
    (r"\bOVER (?=[\d.]+)", "O"), (r"\bUNDER (?=[\d.]+)", "U"),
]


def short(title, max_len=MAX):
    t = " ".join(str(title).split())
    for pat, rep in _STEPS:
        if len(t) <= max_len: break
        t = re.sub(pat, rep, t)
    if len(t) > max_len:
        cut = t[:max_len + 1].rsplit(" ", 1)[0]
        t = cut if len(cut) >= max_len // 2 else t[:max_len]
    return t


def fit_title(title, body, max_len=MAX):
    """(title, body): the title shortened to one line; if it changed, the full title leads the body"""
    t = short(title, max_len)
    if t == " ".join(str(title).split()): return title, body
    full = " ".join(str(title).split()).replace(" | BEST AT FANDUEL", "")
    return t, (full + "\n" + body if body else full)
