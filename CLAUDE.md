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

## RULE 2: The current season is NOT a test season (Jeffrey, Nov 5, 2026)

Never answer "can we test this?" with "wait for this season's results". Every idea is tested **now, on past seasons**, using
whatever honest out-of-sample design the data allows, before anyone suggests waiting:
1. Older seasons the rule was not chosen on (SportsbookReview 2011-2021 in `nhl-mixed-model/data/external/sbr` and the other
   repos' `data/external`; hockeyR xG and goalies for the NHL).
2. Leave-one-season-out: choose the rule on the other seasons, grade the held-out one, repeat for every season.
3. Reconstructed or approximate inputs (e.g. a price rebuilt from another market), clearly labeled as approximate.
Only if NONE of these is possible may the current season be used, and then say exactly why past seasons can't answer it and
record that reason in FINDINGS.md. The live season's own TEST rows are a running check, not the test.

## RULE 3: Read the model playbook before building any model
Before building or changing any model, read `MODEL_PLAYBOOK.md` in the JeffreyD24/betting-goals repo (how to build the best model:
the market as part of the base model, then lineups / injuries / travel / sharp money, scored against the close) and `SHARP_MONEY.md`
there for the money-tracking system. Say which playbook steps the new work covers. Set Nov 5, 2026.

## RULE 4: Never rebuild what was already built (Jeffrey, Nov 5, 2026)

Anything that takes more than about a minute to build (walk-forward predictions, joined game tables, snapshot pulls, fitted
models) is saved in the repo under `derived/`, gzipped, with a row in `derived/MANIFEST.md` saying what it is, which script and
inputs built it, and the commit. Same session it is built. `_tmp/` is scratch only: nothing in it is ever the only copy.

Before building anything:
1. Read `derived/MANIFEST.md` and run `python derived.py .` (restores every saved file into `_tmp/`, where the scripts look).
2. Only build what is not listed there; then `python derived.py . --save` and add its MANIFEST row.
New analysis scripts call `derived.ensure(WORK, [...])` at the top so they use the saved copy automatically.
nhl-mixed-model has the reference setup (`derived.py`, `derived/MANIFEST.md`); nba/nfl-mixed-model copy it the first time they save.
Files over ~50 MB compressed: ask Jeffrey before committing (GitHub's limit is 100 MB per file).

## Other standing rules
- Only bets at (or near) the opening price are real bets; the backtests only made money there.
- A new rule or model version starts a new record; old versions are never re-graded under new rules.
- Thresholds chosen on the same seasons they're reported on are in-sample: say so, and test them right away on seasons they
  were NOT chosen on (see RULE 2).
