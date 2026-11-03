"""Sportsbook names: one spelling per book, so 'dk', 'DraftKings' and 'Draft Kings' count as the same book (used by log_bet.py, log_limit.py, edge_stats.py)."""
import re

BOOKS = {"draftkings": "DraftKings", "draft kings": "DraftKings", "dk": "DraftKings", "dkng": "DraftKings",
         "fanduel": "FanDuel", "fan duel": "FanDuel", "fd": "FanDuel",
         "betmgm": "BetMGM", "bet mgm": "BetMGM", "mgm": "BetMGM",
         "caesars": "Caesars", "caesar": "Caesars", "williamhill": "Caesars", "william hill": "Caesars", "czr": "Caesars",
         "betrivers": "BetRivers", "bet rivers": "BetRivers", "rivers": "BetRivers",
         "fanatics": "Fanatics", "espn bet": "ESPN BET", "espnbet": "ESPN BET", "espn": "ESPN BET",
         "bet365": "bet365", "bovada": "Bovada", "betonline": "BetOnline", "betonlineag": "BetOnline", "pinnacle": "Pinnacle",
         "polymarket": "Polymarket", "kalshi": "Kalshi", "hard rock": "Hard Rock Bet", "hardrock": "Hard Rock Bet"}
NOT_RECORDED = "(not recorded)"


def canon_book(s):
    """canonical spelling for a book name; unknown names are kept as typed (trimmed); blank -> '(not recorded)'"""
    s = "" if s is None or (isinstance(s, float) and s != s) else str(s).strip()
    if not s or s.lower() in ("nan", "none"): return NOT_RECORDED
    k = re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
    return BOOKS.get(k, BOOKS.get(k.replace(" ", ""), s))
