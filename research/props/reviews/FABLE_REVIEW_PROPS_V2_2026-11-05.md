# Fable review of the props v2 backtest (Nov 5, 2026)

Independent review (Claude Fable), run before anything went live. Verbatim:

**Verdict: not OK to go live, even as a provisional record of a "model" strategy.** The information test (criterion 1) is sound and survives my checks, but criterion 2 passes for a reason unrelated to the model, and the bets as constructed cannot be placed. It can stay in the paper record only if relabelled as "FanDuel-vs-DraftKings closing disagreement, model-tilted".

All numbers below are from a scratch copy (`/tmp/claude-0/fable/props_v2_scratch.py`) that reproduces `analysis/props_v2_output.txt` exactly; nothing in the repo was changed.

1. **Blocker – the bet test does not test the model.** `analysis/props_v2.py:115-116,157-162`: p ≈ 0.933·p_close(DK no-vig) + 0.067·p_model, then EV ≥ 5% at the better of DK/FD. A DK price can never beat DK's own fair by 5%, so all 1299 Test A bets are FD prices judged against DK's fair (crosstab: fanduel 1299, draftkings 0). With w = 0 (no model) the same rule gives 1140 bets, **+61.4u (+5.4%)**; with the model, +8.7u. The 426 bets that need the model's nudge to clear 5% lose **−50.9u (−11.9%)**. Fix: judge each bet against its own book's price (or a market prob not derived from the other book), and report model-attributable units separately.

2. **Blocker – bets are not placeable at tip−30.** BettingPros rows are each book's *last* update: median FD bet row 7 min before tip, DK row 22 min; 10.4% of all DK/FD rows are updated after the scheduled tip, and **118/1299 bets use an FD price stamped after tip** (`BP.hours_before.between(-0.25, 6)`, `props_v2.py:83`). Bets are 18–35 cent same-line gaps between DK and FD at close, i.e. mostly stale/suspended lines: where DK's row is >1h older than FD's, 248 bets return −14.5%; where FD's is 1–3h older, −10%. Fix: price at a snapshot taken at bet time, or require both books updated within ~15 min before bet time and before tip, and drop hours_before < 0.

3. **Material – v2 minutes double-count absences.** `props_v2.py:67` adds M_out shares on top of `min_proj`, whose 5-game EW mean already reflects ongoing absences. Per team-game in Test A: Σmin_proj 236, Σmin2 **272**, actual 239; +3.5 min/player, +11.5 min when M_out > 100. Hence mean(p2 − p_close) = +0.042 (v1b: −0.054), 77% of bets are overs, overs −23.3u, unders +33.0u. Fix: redistribute only absences newer than the player's recent games, or rescale min2 to 240 per team.

4. **Minor – injury-report timing.** `status_at` uses as_of ≤ tip−30, and the HH:30 report is usually posted a few minutes after its stamp. Rerun with tip−45: coef +0.092 [+0.063, +0.122], bets 1199, +27.2u — conclusion unchanged.

5. **Minor – `today` roster** (`props_v2.py:61-62`) is built from players who played; only 4.2% of them are absent from the 15-day set and they enter only the denominator `tot`. Negligible.

6. **Minor – deviations from the pre-registration.** Test B (2025-26 Odds API 11 AM, closing-line EV) is not run; "2025-26 (descriptive)" uses BP closes instead. Log loss vs market is reported only for the fit season. The (−0.25, 6)h window is imported from the unders rule, not in the v2 plan.

7. **Logistic test – OK.** Specification y ~ 1 + logit(close) + [logit(model) − logit(close)] is correct (close coef 1.105). Date-clustered SE 0.019 vs 0.018; adding stat dummies, stat×log(line) and stat×logit(close) leaves the coefficient at +0.109; a no-information null (model mean set to the line, which carries only the NB shape/line-size bias) gives −0.17. Positive within each stat (+0.08 to +0.12). v1b, which uses no injury data, is also +0.062.

8. **Grading – OK.** Voids via inner join on box rows with min > 0 (`props_v2.py:122`); pushes u = 0 (included in the ROI denominator, slight dilution); no duplicate (key, book, side) rows in BP; one bet per player-stat-game; same-line only (`line == mline`). Price conversion correct.

9. **Pass criteria applied as written**; w, α, var_ab all come from 2023-24. I cannot verify the timing of the α-weighting note. Note the units criterion passed by +8.7u on 1299 bets, 90% CI [−3.9, +5.4] — a coin flip, and 2022-23 shows −35u.
