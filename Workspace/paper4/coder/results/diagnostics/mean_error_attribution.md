# Why `mean_error` fell, and which fix did it

## The question

Four physics fixes went in together. `mean_error` fell, and the team lead asked
whether that was the shadowing correction or the mid-entry ledger timestamp, or
whether the two could not be separated at all.

## They CAN be separated, and were, by construction

The comparison in `compare_physics_fixes.py` reverts **one fix at a time on top
of the fixed code**, not the whole set at once. So in the `shadowing_old` run the
ledger fix is still in, and in the `ledger_old` run the shadowing fix is still
in. Each delta is therefore that one fix against a baseline holding the other
three. The confounding the team lead was concerned about applies to a single
before/after run of the whole batch, which is not what was measured.

## The split

Density 25, 400 steps, seed 2001. Deltas are (fixed - reverted).

| reverted fix | mean_error delta | of the total |
|---|---|---|
| correlated shadowing | -0.1305 | 88 % |
| mid-entry ledger timestamp | -0.0184 | 12 % |

Both are negative: the fixed code reports a **lower** error than either
reversion. The shadowing correction accounts for about seven eighths of it.

## The ledger part was predicted; the shadowing part was not

The ledger contribution matches its prediction: one step of dead reckoning,
small, downward. 0.0184 of 1.5627 is 1.2 %, which is the "hard to see in a single
episode" the prediction called for.

**The shadowing contribution was not predicted at all**, and it points the
opposite way to the same fix's effect on delivery, which rose. A reading that
fits both: under independent draws a blocked vehicle eventually escapes at some
later retry and its report lands with a larger age, so the deliveries that do
happen are older and their dead-reckoned positions further off. Under correlation
the same burst either gets through early or is abandoned, so the reports that
arrive are younger.

**That is a reading, not a demonstration.** It is consistent with the two
measured directions and with `tx_abandoned` rising from 0 to 1 in the same
comparison, and nothing in this project's conclusions rests on it. Confirming it
would take a per-report age distribution split by retry index, which has not been
measured.

## What this costs, stated

Putting the four fixes in together was the right call on recollection cost -- one
recollection serves all four -- and it did make the attribution question
necessary. It was answerable here only because the comparison was designed to
revert one at a time. Had it been a single before/after of the batch, the answer
would have been "cannot be separated", and that is what the team lead was right
to anticipate.
