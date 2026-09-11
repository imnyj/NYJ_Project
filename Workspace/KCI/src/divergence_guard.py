"""Detect a training run that has stopped learning, while it is still running.

Why this module exists
----------------------
On 2026-09-02 the PPO baseline diverged eleven episodes into a 100-episode run.
The background worker thread raised `ValueError: Expected parameter loc ... to
satisfy the constraint Real(), but found invalid values: tensor([[nan, ...]])`
out of `sb3_ppo.update()`, `threading` printed the traceback to stderr, and the
thread died.  Nothing in the pipeline was watching the thread, so the episode
loop kept stepping SUMO for another 8.8 hours, wrote 89 further episode rows,
saved checkpoints, and returned a summary saying `total_steps: 200000,
episodes: 100`.  The scheduled report called it `done 100/100`.

Measured evidence, from `runs/*/lg/*_progress.csv` (18 runs, 9 models x 2 reward
arms, 200,000 steps each, 2026-09-02/03). CARLTON was in the registry then and
is not now, so the model that set the healthy ceiling below no longer exists;
the number is kept because the ceiling it established is what the floor was
placed above, and replacing it would rewrite the reason the floor is where it
is. What the current registry measures instead is in the next block:

    healthy runs      per-episode `mean_loss` peaked at 12.43 (CARLTON)
                      and never exceeded that across 7 models
    PPO / mean        -0.09 for ten episodes, then 285,247.46 forever,
                      gradient updates frozen at 746 from episode 12 on
    PPO / accumulate  ~15 for fifteen episodes, then 1.61e7 forever,
                      gradient updates frozen at 1,610 from episode 20 on
    I-HAMAPPO         spikes to 1.5e5 at one episode and recovers to 0.79 two
                      episodes later, so a single-episode threshold would kill
                      a run that was still learning

Re-measured on 2026-09-06, AFTER the 2026-09-05 rewiring (MADDPG-MT's second
critic and task decomposition, SPAM-D3QN's prioritised replay, the neighbourhood
reaching I-HAMAPPO and RES-MAPDDPG, CARLTON replaced by HOORL, the discount
search ceiling lowered from 0.999 to 0.99). Eight of the nine models ran, HOORL
could not because its offline dataset did not exist yet. Full numbers in
`results/diagnostics/loss_scale_after_rewiring_20260906.csv`:

    worst episode across all eight   1.3654 (RES-MAPDDPG), i.e. one order of
                                     magnitude BELOW the 12.43 above
    per-model warmup medians         0.0186 (TD3) .. 0.7661 (SAC)
    verdict at these thresholds      none; no episode exceeded the floor and no
                                     episode received zero gradient updates

READ THAT MEASUREMENT ONLY AS WHAT IT IS. It is 4,000 steps per model -- one
HPO rollout, 2 % of a production run -- at density 25.0 and seed 42, with the
model defaults rather than tuned hyperparameters. Three models were still
climbing when it ended (last quarter over first quarter: TD3 4.76x,
RES-MAPDDPG 3.72x, MA2HDQN 3.59x, MADDPG-MT 3.57x), so it cannot say where a
200,000-step run ends up, and the thresholds below were deliberately NOT
retuned to it. Setting a threshold from a window narrower than the runs it
polices is the same error the current thresholds are being questioned for.

WHEN TO DECIDE. Re-judge these thresholds against the first 20 episodes of the
200,000-step main run: compare that per-episode `mean_loss` range with the table
above, check whether the four climbing models keep climbing, and only then fix
the floor. Until that comparison exists, leave the numbers alone.

Three separate things had to be true for that to go unnoticed, so there are
three detectors here and in `hot_swap_trainer`:

  * the loss magnitude ran away          -> `DivergenceMonitor` (this file)
  * gradient updates stopped entirely    -> `DivergenceMonitor` (this file)
  * the worker thread died silently      -> `BackgroundTrainer._worker_loop`

The thresholds below are chosen from the table above.  Between the worst
healthy episode (12.43) and the mildest divergence (285,247) there are four
orders of magnitude of empty space, so any absolute floor in [1e3, 1e5]
separates them; the floor is set at the bottom of that gap.  The floor alone is
not enough because loss scales differ by four orders of magnitude ACROSS models
(SPAM-D3QN settles at 5e-4, CARLTON at 12), so a relative rule runs alongside
it: a run is diverging when its loss is `RATIO` times its own early-episode
median.  Both rules require `PATIENCE` consecutive episodes, which is what
keeps the recoverable I-HAMAPPO spike from being treated as a failure.

This module holds no torch state and imports nothing from the trainer, so both
`hot_swap_trainer.run_hot_swap_training` (live, during a run) and
`etc/report_progress.py` (after the fact, replayed over a progress CSV) apply
exactly the same rule.  A run finished before this file existed is therefore
judged by the same criterion as one finished after it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "ABORT_DIVERGED",
    "ABORT_GRAD_STALL",
    "ABORT_TRAINER_CRASH",
    "ABORT_EMPTY_EPISODES",
    "ABORT_KINDS",
    "STATUS_COMPLETED",
    "DEFAULT_WARMUP_EPISODES",
    "DEFAULT_LOSS_RATIO",
    "DEFAULT_LOSS_ABS_FLOOR",
    "DEFAULT_LOSS_PATIENCE",
    "DEFAULT_MAX_ZERO_UPDATE_EPISODES",
    "DEFAULT_MAX_NONFINITE_LOSS_UPDATES",
    "HEALTHY_MAX_EPISODE_LOSS",
    "AbortVerdict",
    "DivergenceMonitor",
    "scan_progress_rows",
    "is_finite_number",
]

# --- abort kinds -----------------------------------------------------------
# One string per way a run can stop being worth continuing. They are written
# verbatim into the summary dict, the progress CSV `run_status` column and the
# `{model}_status.json` sidecar, so the report never has to guess.
ABORT_DIVERGED = "diverged"
ABORT_GRAD_STALL = "grad_stall"
ABORT_TRAINER_CRASH = "trainer_crash"
ABORT_EMPTY_EPISODES = "empty_episodes"
ABORT_KINDS = frozenset({
    ABORT_DIVERGED, ABORT_GRAD_STALL, ABORT_TRAINER_CRASH, ABORT_EMPTY_EPISODES,
})
STATUS_COMPLETED = "completed"

# --- thresholds ------------------------------------------------------------
#: Largest per-episode `mean_loss` any of the seven models that trained normally
#: ever recorded (CARLTON, accumulate arm, episode 16), over 200,000 steps.
#: Documentation for where the floor below comes from; not read by the logic,
#: only quoted in the abort message.
#:
#: CARLTON has since been dropped from `src/baselines`, so no run of the current
#: registry can reproduce this number. The eight models that replaced it peaked
#: at 1.3654 over 4,000 steps on 2026-09-06. That is NOT a substitute for this
#: constant and is not written here: 4,000 steps is 2 % of a run, and the four
#: models that were still climbing at the end of it make the short-run peak a
#: lower bound on the long-run one, not an estimate of it. The value stays until
#: the main run supplies a 200,000-step figure for the current registry.
HEALTHY_MAX_EPISODE_LOSS = 12.43

#: Episodes used to establish each model's own loss scale before the relative
#: rule can fire. PPO/mean had already diverged by episode 11 and PPO/accumulate
#: by episode 17, so five leaves ample margin.
DEFAULT_WARMUP_EPISODES = 5

#: Relative rule: `|loss| > RATIO * median(|loss|) over the warmup episodes`.
#: 1e3 sits inside the four-order gap between the worst healthy episode and the
#: mildest real divergence.
#:
#: MEASURED 2026-09-06: this rule currently decides nothing. `loss_threshold`
#: takes the LARGER of the relative threshold and the absolute floor, and all
#: eight models measured had a warmup median below 1.0 (0.0186 .. 0.7661), so
#: their relative thresholds landed at 18.6 .. 766.1 and the floor of 1e3 won
#: every time. The rule exists because loss scales once differed by four orders
#: of magnitude ACROSS models; after the rewiring they span two orders and sit
#: below the floor, which is why it went inert. This is an observation about the
#: present loss scale, not a fault in the rule: if the main run's losses are
#: larger than these 4,000-step ones, the medians rise and the rule starts
#: binding again on its own. Do not retune the ratio to make it bind on
#: short-run numbers.
DEFAULT_LOSS_RATIO = 1.0e3

#: Absolute rule, applied from the first episode (the relative rule cannot fire
#: until the warmup window closes, and a model can blow up before then). Also
#: guards the case where the warmup median is ~0, which would make the relative
#: threshold meaninglessly small: PPO/mean's early losses averaged -0.09, and a
#: ratio-only rule would have fired on ordinary noise at 89.5.
#:
#: As of 2026-09-06 this is the ONLY loss rule that binds, for the reason given
#: above `DEFAULT_LOSS_RATIO`. Its margin over the measured healthy band widened
#: rather than narrowed: 732x above the worst of the eight short runs, against
#: 80x above the 12.43 it was originally placed over. A run whose loss grew a
#: hundredfold to 130 would therefore pass. Lowering the floor to close that gap
#: needs the main run's first 20 episodes, not these 4,000-step ones.
DEFAULT_LOSS_ABS_FLOOR = 1.0e3

#: Consecutive over-threshold episodes required. I-HAMAPPO/mean recorded
#: 145,990 at episode 16, 4,141 at 17 and 0.79 at 18 and went on to train for
#: another 83 episodes, so one episode is not evidence; three is.
DEFAULT_LOSS_PATIENCE = 3

#: Consecutive episodes with zero gradient updates before the run is stopped.
#: All eighteen recorded runs that were training had zero such episodes, and
#: both PPO runs had an unbroken run of them from the failure to the end.
DEFAULT_MAX_ZERO_UPDATE_EPISODES = 3

#: Consecutive non-finite loss values, counted per gradient update rather than
#: per episode, before the background trainer stops. A NaN loss means the update
#: that produced it has already written NaN into the weights, so this is not a
#: threshold to be generous with; it is > 1 only so that a single numerically
#: unlucky batch cannot end a run.
DEFAULT_MAX_NONFINITE_LOSS_UPDATES = 10


def is_finite_number(value: Any) -> bool:
    """True when `value` is a real number that is neither NaN nor infinite."""
    if value is None or isinstance(value, bool):
        return False
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(as_float)


@dataclass
class AbortVerdict:
    """Why a run should stop, in a form that survives into CSV and JSON."""

    kind: str
    episode: int
    reason: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "abort_kind": self.kind,
            "abort_episode": int(self.episode),
            "abort_reason": self.reason,
            "abort_detail": dict(self.detail),
        }

    def __str__(self) -> str:  # pragma: no cover - formatting only
        return f"[{self.kind}] episode {self.episode}: {self.reason}"


class DivergenceMonitor:
    """Feed it one episode at a time; it says when the run has stopped learning.

    Deliberately episode-granular. The quantity it reads, `mean_loss`, is the
    mean over the trainer's retained loss window and is exactly the column the
    progress CSV records, so a verdict reached live and a verdict reached by
    replaying the CSV afterwards are the same verdict.
    """

    def __init__(
        self,
        warmup_episodes: int = DEFAULT_WARMUP_EPISODES,
        loss_ratio: float = DEFAULT_LOSS_RATIO,
        loss_abs_floor: float = DEFAULT_LOSS_ABS_FLOOR,
        loss_patience: int = DEFAULT_LOSS_PATIENCE,
        max_zero_update_episodes: int = DEFAULT_MAX_ZERO_UPDATE_EPISODES,
    ) -> None:
        self.warmup_episodes = max(1, int(warmup_episodes))
        self.loss_ratio = float(loss_ratio)
        self.loss_abs_floor = float(loss_abs_floor)
        self.loss_patience = max(1, int(loss_patience))
        self.max_zero_update_episodes = max(1, int(max_zero_update_episodes))

        self._warmup_losses: List[float] = []
        self.baseline_loss: Optional[float] = None
        self.high_loss_streak = 0
        self.zero_update_streak = 0
        self.episodes_seen = 0
        self.verdict: Optional[AbortVerdict] = None

    # -- thresholds ---------------------------------------------------------
    @property
    def loss_threshold(self) -> float:
        """The magnitude an episode's loss must exceed to count as diverging.

        Before the warmup window closes this is the absolute floor alone: there
        is no per-model scale to be relative to yet, and waiting for one would
        let a model that blows up on episode 2 run unwatched.
        """
        if self.baseline_loss is None:
            return self.loss_abs_floor
        return max(abs(self.baseline_loss) * self.loss_ratio, self.loss_abs_floor)

    def _close_warmup_if_ready(self) -> None:
        if self.baseline_loss is not None or len(self._warmup_losses) < self.warmup_episodes:
            return
        ordered = sorted(self._warmup_losses)
        mid = len(ordered) // 2
        median = (ordered[mid] if len(ordered) % 2
                  else 0.5 * (ordered[mid - 1] + ordered[mid]))
        self.baseline_loss = float(median)

    # -- the detector -------------------------------------------------------
    def observe(
        self,
        episode: int,
        mean_loss: Any,
        grad_updates_this_episode: Optional[int] = None,
    ) -> Optional[AbortVerdict]:
        """Record one finished episode and return a verdict if it condemns the run.

        Once a verdict has been returned it is latched: every later call returns
        the same one, so a caller that keeps feeding episodes cannot un-fail a
        run by following a bad episode with a good one.
        """
        if self.verdict is not None:
            return self.verdict

        self.episodes_seen += 1
        episode = int(episode)

        # 1. Gradient-update stall. Checked first only so that a run which both
        #    stalled and diverged is still reported with whichever crossed its
        #    threshold on this episode; in practice divergence precedes the
        #    stall, so divergence is what gets reported.
        if grad_updates_this_episode is not None:
            if int(grad_updates_this_episode) <= 0:
                self.zero_update_streak += 1
            else:
                self.zero_update_streak = 0

        # 2. Loss magnitude. A non-finite episode loss is not a matter of degree
        #    -- the weights that produced it are already poisoned -- so it is
        #    condemned on sight rather than after `loss_patience` episodes.
        if not is_finite_number(mean_loss):
            self.high_loss_streak = self.loss_patience
            self.verdict = AbortVerdict(
                kind=ABORT_DIVERGED,
                episode=episode,
                reason=(
                    f"episode mean loss is non-finite ({mean_loss!r}); the gradient "
                    "update that produced it has already written NaN/Inf into the "
                    "model weights"
                ),
                detail={
                    "mean_loss": str(mean_loss),
                    "baseline_loss": self.baseline_loss,
                    "loss_threshold": self.loss_threshold,
                    "rule": "non_finite_loss",
                },
            )
            return self.verdict

        loss_mag = abs(float(mean_loss))
        threshold = self.loss_threshold
        if loss_mag > threshold:
            self.high_loss_streak += 1
        else:
            self.high_loss_streak = 0

        if len(self._warmup_losses) < self.warmup_episodes:
            self._warmup_losses.append(loss_mag)
            self._close_warmup_if_ready()

        if self.high_loss_streak >= self.loss_patience:
            self.verdict = AbortVerdict(
                kind=ABORT_DIVERGED,
                episode=episode,
                reason=(
                    f"episode mean loss stayed above {threshold:.6g} for "
                    f"{self.high_loss_streak} consecutive episodes (latest "
                    f"{float(mean_loss):.6g}); healthy runs of this pipeline peaked "
                    f"at {HEALTHY_MAX_EPISODE_LOSS}"
                ),
                detail={
                    "mean_loss": float(mean_loss),
                    "baseline_loss": self.baseline_loss,
                    "loss_threshold": threshold,
                    "streak": self.high_loss_streak,
                    "rule": "sustained_high_loss",
                },
            )
            return self.verdict

        if self.zero_update_streak >= self.max_zero_update_episodes:
            self.verdict = AbortVerdict(
                kind=ABORT_GRAD_STALL,
                episode=episode,
                reason=(
                    f"{self.zero_update_streak} consecutive episodes received zero "
                    "gradient updates; the remaining environment steps would train "
                    "nothing"
                ),
                detail={
                    "streak": self.zero_update_streak,
                    "mean_loss": float(mean_loss),
                    "rule": "zero_gradient_updates",
                },
            )
            return self.verdict

        return None

    def state(self) -> Dict[str, Any]:
        """Everything the summary needs to explain how the decision was reached."""
        return {
            "episodes_seen": self.episodes_seen,
            "baseline_loss": self.baseline_loss,
            "loss_threshold": self.loss_threshold,
            "high_loss_streak": self.high_loss_streak,
            "zero_update_streak": self.zero_update_streak,
            "warmup_episodes": self.warmup_episodes,
            "loss_ratio": self.loss_ratio,
            "loss_abs_floor": self.loss_abs_floor,
            "loss_patience": self.loss_patience,
            "max_zero_update_episodes": self.max_zero_update_episodes,
        }


def scan_progress_rows(
    rows: Sequence[Dict[str, Any]],
    loss_key: str = "mean_loss",
    episode_key: str = "episode",
    grad_key: str = "grad_updates_this_episode",
    **monitor_kwargs: Any,
) -> Optional[AbortVerdict]:
    """Replay a finished run's episode rows through the live detector.

    Used by the scheduled report so that runs completed before the guard existed
    are judged by the guard's rule rather than shown as `done`.
    """
    monitor = DivergenceMonitor(**monitor_kwargs)
    for idx, row in enumerate(rows, start=1):
        episode = row.get(episode_key, idx)
        try:
            episode = int(episode)
        except (TypeError, ValueError):
            episode = idx
        grad = row.get(grad_key)
        if grad is not None and not is_finite_number(grad):
            grad = None
        verdict = monitor.observe(
            episode=episode,
            mean_loss=row.get(loss_key),
            grad_updates_this_episode=None if grad is None else int(float(grad)),
        )
        if verdict is not None:
            return verdict
    return None
