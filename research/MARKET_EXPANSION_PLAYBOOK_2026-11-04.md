# Market Expansion Playbook — every DraftKings & FanDuel bet type, ranked by edge
*Nov 4, 2026 · applies to NBA, NHL, NFL, and the new NCAA models*

## The one-paragraph answer
Not every market deserves a model. The books make their money on the markets with the highest hold (parlays, same-game parlays, futures, exotics), and they put the least pricing effort into the markets with lots of lines and little money (player props, quarter/half lines, team totals). So the plan is: **build models where the book is lazy, use pure math where the book is generous (boosts/promos), and only touch parlays as a delivery vehicle for legs that are already +EV on their own.** Everything new goes in as PROVISIONAL under the goals rule, graded on CLV first, units second.

---

## 1. The full menu, ranked

Hold = the book's built-in cut. Lower is better for us. Figures are typical ranges from industry sources, not DK/FD-published numbers.

| Tier | Market | Typical hold | Why there's (or isn't) an edge | How we attack it |
|---|---|---|---|---|
| **A — build now** | **Player props** (pts, reb, ast, 3PM, PRA, SOG, pass/rush/rec yds) | ~6–10% | Hundreds of lines per slate; books can't watch them all; slow to react to lineup news; lower-tier players & mid-week games softest | Mixed model: player as random effect (same idea as a breeding value), minutes × usage × pace → a full **distribution**, not a point estimate |
| **A** | **1st quarter / 1st half / 2nd half spreads & totals** | ~5–8% | Books mostly derive these mechanically from the full-game line (a fixed fraction) instead of handicapping them; thin money corrects them slowly | We already have full-game models → model the halves directly using team-level start/finish tendencies, rotation patterns, pace by quarter |
| **A** | **Team totals** | ~5–7% | Derivative of spread + total; mispriced when the spread and total move separately | Free: derive from our existing spread + total models; bet when ours disagrees with the book's implied split |
| **A** | **Profit/odds boosts, promos** | negative for the book | Book gives up part (sometimes all) of its edge on purpose | No model needed — de-vig the market, apply the boost, bet if EV > 0. Fastest win on this list |
| **B — build next** | **Alternate spreads & totals** | ~5–10% | Priced off an assumed distribution; when *our* distribution differs from theirs (fat tails, key numbers) the ladder is mispriced | Generate a fair-price ladder from our model's distribution; compare each rung. NFL key numbers (3, 7, 10) matter; NBA alt lines matter far less |
| **B** | **Alt player props** (e.g. 30+ pts, 4+ threes) | ~8–15% | Tail pricing is where books guess the most | Same prop distribution as Tier A, read off the tails. Watch variance |
| **B** | **NHL alt puck lines, NHL period lines** | ~5–8% | Same derivative logic; empty-net goals distort the puck line | Extend the NHL moneyline/puck line models |
| **B** | **Live in-game lines** | ~5–8%+ | Books reprice under time pressure; but they also have faster data than us | We're capturing live lines already — research first, bet later. Halftime lines are the most promising slice |
| **C — math tool only** | **Straight parlays (different games)** | ~9% (2 legs) → 17% (4 legs) → 37% (10 legs) at -110 | Hold compounds with every leg | Only parlay legs that are already +EV. Then it multiplies our edge (see §2). Never add a leg to "get a bigger number" |
| **C** | **Same-game parlays / SGP+** | ~15–30%+ | Books price correlation with proprietary models and add extra margin on top | Research only: simulate the joint outcome from our models, compare to the book's SGP price. Bet only where the book under-prices correlation. Expect most to be traps |
| **C** | **Teasers** | high | NFL "Wong teasers" (crossing 3 and 7) used to be +EV; books reprice them now | Price-check with our margin distribution; skip unless fair |
| **D — skip** | Futures & awards | ~15–25% | High hold and money tied up for months | Only if a model shows a huge gap (e.g. ROY / 6MOY, which you already planned to track) |
| **D** | Exotics: first basket/goal/TD scorer, race to X, exact margin, highest-scoring quarter, odd/even | ~10–30% | Near-coin-flips or long shots with heavy margin | Skip. Possible exception later: first basket via tip-off win % + first-shot share |

---

## 2. The parlay math (run, not estimated)

Every leg at -110 (52.38% needed to break even on a straight bet):

| Legs | Pays | Fair payout | House edge if you're a coin flip | Your EV if each leg is 53% | Your EV if each leg is 55% |
|---|---|---|---|---|---|
| 1 | +91 | +100 | −4.5% | +1.2% | +5.0% |
| 2 | +264 | +300 | −8.9% | +2.4% | +10.3% |
| 3 | +596 | +700 | −13.0% | +3.6% | +15.8% |
| 4 | +1228 | +1500 | −17.0% | +4.8% | +21.6% |
| 6 | +4741 | +6300 | −24.4% | +7.3% | +34.0% |
| 10 | +64208 | +102300 | −37.2% | +12.5% | +62.9% |

**What this means:**
- A parlay is a magnifier. With a real edge on every leg, EV goes up per dollar. Without it, the house edge climbs fast.
- The break-even per leg never changes (52.38% at -110). So a parlay never "rescues" a weak leg.
- The catch is **variance**. A 3-leg ticket of 55% legs wins only ~17% of the time. Long losing streaks are normal, so stakes must shrink accordingly (fractional Kelly).
- Why it can still be useful: if DK/FD limit straight-bet size, a 2-leg parlay of two +EV bets gets more EV through the same limit.
- **SGPs are different.** The book reprices for correlation and adds margin. A 3-leg SGP often carries 12–18% hold. Only worth it if our simulated joint probability beats their price, so it gets the simulator first, real money only if it proves out.

## 3. The boost math
Taking a roughly fair market (a -110-style price with the vig removed) and applying a profit boost:

| Base odds | 25% boost | 50% boost | 100% boost |
|---|---|---|---|
| -200 | +3.5% EV | +11.4% EV | +27.3% EV |
| +100 | +7.4% | +19.4% | +43.2% |
| +200 | +11.4% | +27.3% | +59.2% |
| +400 | +14.6% | +33.7% | +71.9% |

**Takeaways:** boosts are worth more on longer odds, because the boost only multiplies profit. Put the boost on the line where DK/FD is already best-priced, and judge pre-packaged "odds boosts" (usually SGPs) against a de-vigged fair price — the crossed-out number means nothing. A small max stake on a boost is usually a sign it's genuinely +EV.

*Caveat: these are illustrative. The real EV depends on the fair line for that exact bet, which the checker will compute live.*

---

## 4. The constraint that matters most: account limits
This decides strategy more than any model does.
- Both books limit accounts that consistently beat the closing line. A CBS News report from late October 2026 described a pro limited to $25 per bet on DraftKings.
- Industry write-ups describe FanDuel as more lenient, and it often shows the max before you bet; DraftKings tends to limit sharp action faster and may hide the max until after.
- **Props get limited fastest**, since that's where the books know they are soft.

**What we do about it:**
1. Use both books every time and bet whichever has the better price (line shopping is also free EV).
2. Prioritize the highest-EV spots instead of spraying every small edge — each bet spends some "account life."
3. Keep a mix of normal-looking bets (main lines, some boosts) alongside props.
4. Track the max stake offered over time in the bet log, so we see a limit coming.
5. Long term, this is the strongest argument for Polymarket after the move out of Connecticut: exchanges don't limit winners.

---

## 5. Build order

**Phase 1 — this week (uses what already exists)**
- **Boost/promo EV checker:** de-vig the market from the lines we already pull, apply the boost, alert only if EV > 0. Lowest effort, guaranteed edge.
- **Parlay/SGP calculator:** given our model probabilities for each leg, return fair odds, EV and suggested stake. Also gives the "is this boost real?" answer.
- **NBA 1st-half & 1Q backtest:** derive our own 1H/1Q spread and total from the existing models plus team quarter-scoring splits, test on past seasons against archived derivative lines, pre-registered with CLV as the primary measure.
- **Team totals:** read straight off the existing spread + total models; backtest the same way.

**Phase 2 — NBA player props (already planned)**
- Points, rebounds, assists, threes first; starting with the All-NBA / ROY / 6MOY players you picked, then widening to role players, since that's where books are softest.
- Model: player random effect + minutes projection × usage × pace × opponent defense, outputting a distribution (Poisson or negative binomial for counts like threes; normal or gamma for points).
- Needs prop line history: we've been recording props since the live tracker started; backfill sources need checking.
- Then NHL shots on goal and NFL yardage/receptions with the same structure.

**Phase 3 — alt lines & ladders**
- Fair-price ladder from each model's distribution, compared rung by rung against DK/FD.
- NFL first (key numbers make it the most promising), then NHL puck lines, then NBA.

**Phase 4 — research only, money later**
- SGP correlation simulator (joint distributions from our models vs the book's SGP price).
- Halftime / live lines once enough live snapshots exist.
- First basket via tip-off win % (only if the data is easy).

**Not building:** futures (except awards already on the list), odd/even, race-to-X, exact margin, long-leg parlays.

---

## 6. Rules for every new market
- Starts PROVISIONAL; reviewed on the regular provisional schedule.
- Graded separately from the core spread/total/moneyline records, with a record per model version.
- CLV is the primary measure, units second, accuracy alongside. For props, CLV comes from the closing prop line at the same book.
- Every bet still logged as 1 unit unless you say otherwise.
- Fable double-checks each new market's model before it goes live, per the standing rule.
- New data feeds get added to the daily pipeline health check.

---

## 7. Takeaways / personal note
- **Biggest realistic edge: player props and quarter/half lines.** They're soft because there are too many of them for the books to watch, and our mixed-model setup (player effects, shrinkage) is built for exactly this.
- **Fastest money: boosts.** No model, just math, and the books are handing over the edge.
- **Parlays aren't a strategy by themselves.** They amplify whatever edge you already have. Treat them as a sizing tool, not a source of profit.
- **SGPs are where most bettors lose.** Leave them in research until the simulator shows a repeatable gap.
- **The real ceiling is account limits, not model quality.** Spend edge where it counts, shop both books, and keep Polymarket as the long-term exit.
- **Breadth has a cost:** each new market adds data feeds, health checks and records. Phase 1 reuses existing pipes on purpose, so we learn what's worth expanding before we build heavy.

## Sources
- Industry hold and parlay data: [DeucesCracked hold rates](https://www.deucescracked.com/blog/sportsbook-hold-rates-by-sport-and-state-data), [Legal Sports Report 2025 hold](https://www.legalsportsreport.com/263300/sportsbooks-make-more-money-from-slower-sports-betting-growth-in-2025/), [Muddy River News on FanDuel parlay hold](https://muddyrivernews.com/business/the-parlay-powerhouse-why-56-of-missouri-bets-are-multi-leg-wagers-and-why-operators-love-them/20260220102914/)
- SGP pricing: [JuiceReel on SGPs](https://juicereel.beehiiv.com/p/the-dangers-of-same-game-parlays), [DeucesCracked SGP strategy](https://www.deucescracked.com/blog/same-game-parlay-strategy-correlation-guide), [OpticOdds SGP pricer](https://opticodds.com/resources/news/the-optic-odds-same-game-parlay-pricer)
- Props: [Establish The Run on props](https://establishtherun.com/?p=387901), [NFL props sportsbook accuracy study](https://shaanchanchani.github.io/articles/sportsbook-props)
- Derivatives: [DeucesCracked NFL first half](https://www.deucescracked.com/blog/nfl-first-half-halftime-betting-strategy), [DeucesCracked derivative markets](https://www.deucescracked.com/blog/first-half-betting-derivative-markets-explained-2026)
- Alt lines: [DeucesCracked alt lines](https://www.deucescracked.com/blog/alternate-lines-betting-guide-buying-selling-points), [BettorEdge alt line calculator](https://www.bettoredge.com/alternate-lines-calculator)
- Boosts: [Action Network on boosts](https://www.actionnetwork.com/general/best-march-13-north-carolina-promotions-fanduel-draftkings-wednesday-boosts), [Bleacher Nation on boosts](https://briefly-prod.herokuapp.com/anchor/Chicago_Cubs/story/do-draftkings-and-fanduel-have-odds-or-profit-boosts-on-any-game---bleacher-nation)
- Limits: [CBS News, Oct 2026](https://www.cbsnews.com/news/online-betting-apps-losers-perks-limiting-winners/), [OddsShopper DK vs FD](https://www.oddsshopper.com/articles/comparisons/draftkings-vs-fanduel), [ESPN on limiting](https://www.espn.com/sports-betting/story/_/id/41231266/espn-sports-betting-news-sportsbooks-defend-practice-limiting-sharp-customers)
- Academic: Baryla et al. (2007), early-season bias in NBA totals, *Finance Research Letters* 4(3):155–164, doi:10.1016/j.frl.2007.04.002
