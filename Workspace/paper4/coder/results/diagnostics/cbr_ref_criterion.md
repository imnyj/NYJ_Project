# CBR_REF recalculation: the rule, fixed before the measurement

Written 2026-09-07, BEFORE any occupancy was measured under the corrected
channel model. Recorded separately so that the rule cannot be adjusted after
seeing the numbers it selects.

## The rule

`CBR_REF` becomes the **99th percentile of per-step, per-subchannel occupancy**,
pooled over all seven training densities, measured under the fixed behaviour
policy, after the settled warm-up, with the B1 shadowing correction in place.

Rounded to two decimals, upward, so the recorded constant is a round number that
sits at or above the measured quantile.

## Why a realised quantile and not the achievability bound

`CBR_REF = 0.60` was set on 2026-09-02 as an achievability bound: one subchannel
forced to saturation, every vehicle granted every step at 23 dBm, giving 0.591 at
density 50. It answers "what could a policy cause". The congestion term then
reads as a fraction of that worst case, and since realised occupancy does not
exceed 0.04, `r_cong` never rises above 0.067; at weight 0.2 the term is about
0.2 % of the total penalty. A term that cannot move cannot be learned from,
whatever it means.

The realised quantile answers "what does occupancy actually reach", which is the
quantity a policy can act on.

## Why the 99th percentile specifically

Three constraints, and the 99th is where they meet.

The term must use most of [0, 1] in ordinary operation, or the scale problem
comes back in a smaller form. It must not clip so often that the gradient
vanishes where congestion matters, which is the fault that put `CBR_REF` at 0.25
and had to be reversed. And it should follow the precedent set for `QUEUE_MAX`
on the same day, which accepted 1.11 % clipping in exchange for keeping the
feature's spread: about one per cent of samples at the bound is the level this
project has already judged acceptable, so using it again keeps two decisions
consistent rather than each argued from scratch.

## Why pooled across densities rather than per density

One constant, applied at every density, so the reward stays comparable along the
density axis. Pooling lets the busy densities set the reference, which is the
right end: a reference set by the quiet end would clip through the whole
congested range.

## What this rule does NOT decide

Whether the congestion term should be normalised at all, and whether the four
subchannels are the right count. Both were settled earlier and are out of scope
here.

## Stated consequence, accepted in advance

Changing `CBR_REF` changes the reward scale, so scores are not comparable with
any earlier run. That is accepted because the offline dataset is being recollected
for the B1 correction regardless, and no tuned hyper-parameters exist yet under
the new channel model.
