# Fable review of props v1b at the opener (Nov 5, 2026)

Independent review (Claude Fable) before any live use. Verbatim:

**Verdict: not as specified. OK as a PROVISIONAL record only with the changes in issues 1–3 below, and with the record split by book.** Script reproduces exactly (`python3 analysis/props_v1b_opener.py .` → byte-identical output). No look-ahead found. The pre-registered checks pass as written, but the evidence behind them is thinner than the output suggests.

**Leak / mechanics (clean)**
- Opener is market-wide (one `open_*` per selection; `open_book` = first book to post), so "DK/FD opener" = DK/FD was first. Timing guard holds: only 3 of 1,653 bets had the opener posted <3 h after the previous game's tip (+3.0u, immaterial). Opponent/pace features can use other teams' games played after a 24–48 h opener — minor.
- No duplicate keys; voids (min=0) excluded by inner join; pushes 0u; price conversion correct. Both fixes are legitimate: the missing 2021-22 prior was a real bug (model log loss 0.753→0.702 on the fit season), and the bad-quote filter removes +1100/−10000 fg3m quotes, price 0, and `open_book='60'`; it drops only 5 rows in 2023-24 and 49 in 2024-25, so it does not drive the conclusion.
- Data bug left in: 6 DK bets on a line of **0.0** (under 0.0 cannot win; cost −4u). Filter `line < 0.5`.

**Issues**

1. **(material) 55% of the test profit is one 132-bet slice.** FanDuel openers posted <4 h before tip, 2023-24: +47.0u (36% ROI) with lean-adjusted CLV −0.3% and zero line move. DK late openers in the same season: −31.5u on 109. Test seasons by slice: FD-early 604 bets +25.1u (adj CLV +4.7%, line moves our way +0.29), FD-late 243 +53.4u (CLV ≈0), DK-early 688 +37.8u (CLV −2.3%), DK-late 118 −30.6u (CLV −5.8%). Without FD-late-2024 the test is 1,521 bets +38.7u, ~2.5% ROI. Fix: exclude openers posted <4 h before tip (negative CLV, and these are props posted after lineup news, the least obtainable in practice); record FD and DK as separate provisional rows. DK openers: +7u over 1,655 bets across four seasons, raw CLV negative in 3 of 4 seasons.

2. **(material) Check 2 is a coin flip.** Pooled lean-adjusted close-EV +0.41% with 90% CI [−0.70, +1.53]; −1.12% in 2023-24, +3.73% in 2024-25. The ~1.4-pt lean adjustment is worth ~2.5% EV, so it flips the sign. LOSO is computed correctly (excluding 2025-26 changes nothing, 0.42%). Note the raw over-lean of the close is monotonic in model disagreement on the test seasons (model 35+ pts below opener: close no-vig over 50.1% vs 44.9% hit, n=733; model above: 49.5% vs 52.9%), which is the best evidence here that the model carries information beyond the close.

3. **(material) April loses in 3 of 4 seasons** (−16.7, −17.2, −23.7, +4.2 = −53u on 486 bets); Oct–Mar positive in all four. Plausible mechanism (minutes projection lags end-of-season role changes), but post-hoc. Record as [LEAD]; if adopted as a stop, declare it before the first bet.

4. **(material) 2023-24 is not an unseen season.** `var_ab` in `data/props_v1b_params.json` was fit on 2023-24 box scores; the NB dispersion sets p_model's tails, which is exactly what creates EV ≥5% at 25–30-pt disagreements. Box-only, but it violates the provisional rule's "not used to build it". The only clean season, 2024-25, is +18.5u on 506 bets, CI [−3.9, +12.2].

5. **(material) Bet set is a knife-edge in w.** Test bets at w=0.09/0.15/0.20/0.25/0.30: 1/338/1,638/3,602/5,802; units stay positive (+16 to +83u) but adjusted CLV drops below 0 at w ≥0.25. Threshold sweep is non-monotonic (EV≥7%: +28.6u; ≥8%: +40.7u; ≥10%: −4.6u). Live volume will swing with any refit.

6. **(minor) Check 3 is vacuous as written:** w=0 gives 0 bets by construction (de-vigged opener never has +EV) and blind unders lose 4.6%. I ran stronger baselines on the same rows: "under when line ≥1.2–1.5× trailing-10 average" loses 2.7–3.2% ROI at 1,783–7,264 bets; plus-money unders −4.2%. The model does beat them.

7. **(minor) Realism:** BettingPros `open_time` in 2024-25 clusters at 16–22 h before tip (looks like a daily crawl, not true posting time), so the "opener" is their first capture. The live rule must replicate "first book market-wide", not "first FD line while DK already exists". FD prop openers carry small limits and account restrictions; 1 unit is fine only if the unit is sized to those limits. Up to 4 bets per player-game (368 player-games with 2+) are correlated; the date bootstrap covers this.

**Fixes to require before a record:** lead ≥4 h, line ≥0.5, separate FD/DK rows with their own stop lines, standard −10u/−5u@25/units<0@50 stops, and label 2023-24 as semi-in-sample in FINDINGS.md. Scratch work: `/tmp/claude-0/fable2/` (chk1–4.py, T.pkl, bets.csv.gz). Repo untouched (`analysis/props_v1b_opener_bets.csv.gz` restored after the run).
