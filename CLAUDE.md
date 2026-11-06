# Rules for working in this repo (read every session)

The rules for every sports repo live in ONE place: `betting-goals/CLAUDE.md` (RULES 1-6: record everything, past seasons only,
read the playbook, never rebuild, alerts 24h, ask for push access). Since Nov 6, 2026 (Jeffrey) this file only points there.

@../betting-goals/CLAUDE.md

If the rules above did not load (betting-goals is not cloned next to this repo), clone it before doing anything else:
`git clone --depth 1 https://github.com/JeffreyD24/betting-goals ../betting-goals`, then read its CLAUDE.md. Never work from memory of the rules.

How work is split between Claude Code and Claude.ai: `betting-goals/WORKFLOW.md`. When Jeffrey says "start" or "wrap", follow
`betting-goals/claude_code/commands/start.md` or `wrap.md`.

## Notes for this repo
- Also holds the live NCAAM jobs (`ncaab/`); new college-basketball live state lands there first, then is copied to the NCAAM repo.
- Bets are logged through the GitHub "Log a bet" issue form (`log_bet.py` -> `state/my_bets.csv`).


## RULE 7: Heavy jobs run on public repos; private data is saved only to the private repo (Jeffrey, Nov 6, 2026)

GitHub Actions minutes are free on the public repos and limited on `JeffreyD24/private` (it hit its spending limit on Nov 6).
So every download or batch job runs on a public repo's runners (`nba-mixed-model`, `nhl-mixed-model`, `nfl-mixed-model`), and
anything that must stay private (Kalshi data: Developer Agreement sec. 3.1; wallet-level Polymarket data; unlicensed mirrors like
hockeyR) is pushed **only** to `JeffreyD24/private`, using the `PRIVATE_REPO_TOKEN` secret (fine-grained token, Contents read/write on
`private` only). Reference setup: `nba-mixed-model/.github/workflows/exchange-to-private.yml`.
- Never write private data into a public repo's files, commits or artifacts. Logs print counts only, never rows, wallets or prices.
- Check out the private repo sparsely (code, lists and resume markers), not its full data.
- The private repo runs no scheduled Actions of its own unless Jeffrey says so.
- Results with no private rows (a verdict, ROI, counts) go in the public repos and `betting-goals/FINDINGS.md` as usual.
