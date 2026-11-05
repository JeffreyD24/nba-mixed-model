# Rules for working in this repo (read every session)

Same file in nba-mixed-model, nhl-mixed-model and nfl-mixed-model. Set by Jeffrey on Nov 5, 2026.

## RULE 1: Everything gets recorded and saved. No exceptions.

Every test we run, and every inference, lead, association, correlation, causal claim and new idea that comes out of our work,
is written down in the repo, committed and pushed **in the same session it happens**. Nothing lives only in a chat, in `_tmp/`,
in a scratchpad or in someone's head. If a session ends before it's written up, the work did not count.

This includes small things: a quick check run in a terminal, a hunch from looking at one game, a test that "didn't find
anything", a number Jeffrey asked about in passing. Null and negative results matter as much as wins, because they stop us from
re-testing the same idea later.

### Where things go

| What | Where |
|---|---|
| **The master log** (all three sports, newest first) | `nba-mixed-model/analysis/FINDINGS.md`. One dated entry per test, finding, observation or decision. |
| Open leads and new ideas not yet tested | this repo's `research/IDEAS_AND_CHECKLIST.md` (checkbox list) **and** a one-line `[IDEA]`/`[LEAD]` entry in FINDINGS.md |
| The code for a test | `analysis/` or `dev/` in the repo whose data it uses, never only in a scratch folder |
| The full output of a test | next to the code as `<script>_output.txt` (or a `.csv` of every bet), committed |
| Pre-registrations | written and **pushed before** the holdout is run (git history is the proof) |
| A change to live rules or thresholds | FINDINGS.md `[DECISION]` entry + a code comment at the changed line with the date and the evidence file |

### Every FINDINGS.md entry has

```
## YYYY-MM-DD: <short title> (<sport>) [TYPE]
- Question: what we wanted to know, and why it came up.
- Data / method: seasons, prices (opener / close / live), sample size, script path.
- Result: the actual numbers (bets, units, ROI, CLV, per season), not just "it worked".
- Read: what we think it means, AND how strong the evidence is (in-sample or out-of-sample, sample size, noise).
- Decision: what changes (or "nothing changes"), and who approved it.
- Files: script, output, any results write-up.
```

TYPE labels (use one or more):
- `[TEST]` a backtest or analysis that was actually run
- `[OBSERVATION]` something seen in live results or a single game (e.g. a goalie swap killed an alert)
- `[CORRELATION]` two things move together; **not** evidence that one causes the other
- `[CAUSAL]` a claim that X causes Y: say what supports it beyond correlation (pre-registered holdout, mechanism, natural experiment)
- `[LEAD]` a result worth following up; say what the follow-up test is
- `[IDEA]` untested idea; say how it could be tested
- `[DECISION]` a change to live rules, thresholds or alerts

Keep correlation and causation separate in the wording. "Bets at EV 9-10% won more" is a correlation; "the model's EV causes
the win rate" is not something a backtest shows.

### End-of-session check

Before finishing any session: `git status` in every repo touched. Every new script and output is committed, FINDINGS.md has an
entry for every test/finding/idea from the session, and everything is pushed. Tell Jeffrey in one line what was recorded and where.

## Other standing rules
- Only bets at (or near) the opening price are real bets; the backtests only made money there.
- A new rule or model version starts a new record; old versions are never re-graded under new rules.
- Thresholds chosen on the same seasons they're reported on are in-sample: say so, and re-test on the next season.
