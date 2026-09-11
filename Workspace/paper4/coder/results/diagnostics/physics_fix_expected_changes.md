# The four physics fixes: what each is expected to move, written before measuring

## What this document is, and what it is not

The four code changes were already applied when this was written. The
**before/after comparison has not been run**, and this registers the predictions
for that comparison before it runs. So this is not a pre-registration of the
fixes; it is a pre-registration of their measured effects, which is the part that
can still be honest. Saying otherwise would be the kind of after-the-fact
reconstruction this file exists to prevent.

The point is that a result which does not match a prediction is information. With
no prediction written down, any number is compatible with "that seems reasonable".

## Why the four are confounded and how the comparison is separated

Shadowing and `CBR_REF` both touch delivery and the congestion term. The ledger
timestamp touches `mean_error`. `mean_peak_aoi` touches its own metric. Applied
together, a single before/after run cannot attribute a movement to one of them.

So the comparison is run one fix at a time, each against the same baseline, using
the switches that already exist: `judge_uplink(moved_of=...)` reproduces the old
distance path, `CBR_REF` is a module constant that can be set, and the other two
are small enough to toggle by construction. Same seeds, same scenario, same
density throughout.

## Predictions

### 1. Correlated shadowing (B1)

**Delivery failure falls, and by a lot.** A retransmission now keeps the
obstruction it is behind instead of drawing a fresh channel, so a vehicle in a
deep shadow no longer gets ten independent chances to escape it. The earlier
measurement of this same defect at the cell edge was 0.08 % against 7.06 %, so
the direction is certain and the size could be an order of magnitude.

**Caveat on that number.** 0.08/7.06 was measured at the cell edge at 10 dBm,
which is the worst case. Pooled over a whole episode most transmissions are not
near the edge, so the episode-level change should be much smaller than 88x. A
pooled result anywhere near 88x would mean something else moved too.

`tx_abandoned` falls with it, since abandonment is what exhausting the retries
produces. Airtime spent falls, so **occupancy falls slightly** — which is why
`CBR_REF` had to be measured after this fix and not before.

**Direction on the reward: favourable.** Fewer failures, less power, less
airtime. That makes it a fix that flatters the system, so its size should be
reported plainly rather than folded into an aggregate.

### 2. `CBR_REF`, 0.60 to 0.02

**No physical quantity changes at all.** Occupancy, delivery and airtime are
untouched; only the divisor of the congestion term moves. Predictions are
therefore about the reward and nothing else.

`r_cong` rises about thirty-fold, from a mean near 0.008 to a mean near 0.24, and
**the total reward becomes more negative** because it is a penalty sum. Scores
are not comparable with any earlier run, which is accepted.

The congestion term's share of the mean penalty rises from about 0.2 % to
roughly 5-10 %. **It should not approach the error term's share**: if it did, the
recalculation would have overshot into a different objective rather than
repairing this one.

### 3. Mid-entry ledger timestamp

**`mean_error` falls, by less than one step of travel.** The offset was one
`step_length` of dead reckoning, so at 8 m/s the per-affected-sample effect is
about 0.8 m, and only vehicles entering mid-episode before their first successful
update are affected. Against a metric whose spread over 130 trials is 29.19 the
pooled movement should be **small enough to be hard to see** in a single episode.

**A large movement would mean the fix reached more samples than intended** and is
a reason to look again rather than to celebrate.

Larger at high density, where more vehicles enter mid-episode, and larger for
long Delta, where the uncorrected offset persisted over more samples.

### 4. `mean_peak_aoi` sampling condition

**The value rises.** The discarded samples were intermediate ages inside an
interval, all smaller than the age at the delivery that closes it. Removing them
removes a downward bias.

**The rise grows with the failure rate**, since failures are what produced the
spurious samples. Combined with fix 1, which reduces failures, the two effects
oppose: fix 4 raises the metric, fix 1 removes some of the samples that made it
wrong in the first place. **Measured separately for that reason.**

`peak_aoi` (the maximum) does not move. The composite HPO objective reads
neither, so no ranking changes.

## What would count as a surprise

- Delivery failure rising after fix 1, or moving by less than a per cent.
- Any physical quantity moving under fix 2.
- `mean_error` moving by more than a few per cent under fix 3.
- `mean_peak_aoi` falling under fix 4, or `peak_aoi` moving at all.

---

# Outcome, written after the comparison ran

`results/diagnostics/physics_fix_comparison.json`, density 25, 400 steps, seed
2001. Deltas are (fixed - reverted).

| fix | quantity | predicted | measured |
|---|---|---|---|
| shadowing | packet loss | **falls** | **rises**, 0.0666 to 0.0889 (+33 %) |
| shadowing | mean_error | not predicted | falls, 1.6748 to 1.5443 |
| cbr_ref | any physical quantity | no change | no change, exactly zero on all |
| ledger | mean_error | falls, small | falls 0.0184 (1.2 %) |
| ledger | anything else | no change | no change |
| peak_aoi | spurious samples | some | 135 of 1519 attempts (8.9 %) |

## The prediction that was wrong, and why it was wrong

**Delivery failure rises under the correlated model. I predicted it would fall,
and so did the team lead.**

The direction was already recorded in the very comment the prediction quoted:
"the final delivery-failure rate was 0.08 % with independent draws against
7.06 % when the shadow persists". Independent draws are the LOW-failure case,
because a vehicle in a deep shadow gets ten fresh chances to escape it, and that
is the fiction the correlation exists to remove. A persistent shadow means a
vehicle that is blocked stays blocked, so more bursts end in abandonment.

Both of us read the 88x as "the defect made things worse" and carried that into
"fixing it makes the number better". The 88x is the size of the disagreement, not
its direction. Two people reproduced the same error from the same sentence, which
suggests the sentence invites it; the CBR_REF comment has been rewritten to say
which arm is which.

**This is the honest direction and it is unfavourable to the system.** The
corrected physics reports about a third more packet loss at density 25. Anything
reported under the old model was optimistic by roughly that much.

## What the measurement adds beyond the direction

`mean_error` moves the other way: 1.5443 fixed against 1.6748 reverted. That was
not predicted at all. A plausible reading is that under independent draws a
blocked vehicle eventually escapes at some random later retry and delivers with a
larger age, whereas under correlation the same burst either gets through early or
is abandoned -- so the deliveries that do happen are younger. It is a reading, not
a demonstration, and nothing here rests on it.

`CBR_REF` moved no physical quantity at all, on every metric, exactly as
predicted. That is the cleanest of the four results: it confirms the constant is
a reward scale and nothing else, so the reward-comparability caveat is the whole
of its effect.
