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
