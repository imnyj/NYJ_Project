# Deferred to the next run, not fixable during this one

Written 2026-09-07 while the nine-model HPO is running. Nothing here may be
applied to `src/` until that run finishes: changing code mid-run makes it
impossible to say which trial came from which code.

## 1. A trial leaves no trace until its whole study finishes

`src/hpo.py:1623` sets `optuna.logging.set_verbosity(optuna.logging.WARNING)`,
which suppresses the per-trial completion line, and `save_study_results` writes
the trial CSV once, after all fifteen trials of a model. So between the start of
a model and its end there is no record of an individual trial at all.

**What that hides.** A trial that runs for its normal duration and then scores
the failure penalty -- a diverged run, an empty rollout -- is invisible until the
model completes. Monitoring can see a worker die and can see a worker stop
consuming CPU; it cannot see a worker producing bad trials at full speed. The
worst case is losing a whole model, which for SPAM-D3QN is 3.4 hours.

**The fix is one line per trial**: model, trial index, score, wall clock,
n_failed_seeds, appended to a CSV as each trial returns. There is no cost, and
the information already exists at that point in `evaluate_trial_multiseed`.

**Why not now.** It touches `src/hpo.py`, which the four running workers have
loaded. Editing it changes nothing for them and makes the provenance of the
results ambiguous for a reader.

## 2. Monitoring covers two layers with a gap between them

Process state catches a worker that dies or stalls. Model completion catches a
study that finished badly. Between them sits "running normally, producing
penalised trials", which item 1 is what would close.

Recorded here rather than left implicit: knowing where the gap is worth more
than believing there is none.

## 3. `observation_constants()` reads a process-global scenario path

It takes no path argument and reads `make_sumo_set.BASE_PATH`, which is bound at
import. One process therefore cannot handle two scenarios, and a caller that
passes `sumo_dir=X` gets its road written to X while the compatibility check
reads the constants of `BASE_PATH`.

**Not a defect in this run.** `run_hpo_parallel.sh` gives each worker its own
`PAPER4_SUMO_DIR` in the environment before the process starts, so `BASE_PATH` is
correct for the whole life of each worker and the two never disagree. It is a
latent trap for any future caller that tries to do both in one process, and the
verification scripts that pass a temporary `sumo_dir` are already living with it.

---

# How to inspect a running study without disturbing it

Used on 2026-09-07 to test HOORL's dataset load three hours before the model was
due to start, rather than discovering a failure after 3.4 hours of SPAM-D3QN had
already gone.

**Copy the worker's scenario directory and point a separate process at the copy.**
`cp -a /var/tmp/paper4_sumo/g3/. <scratch>/` then run with
`PAPER4_SUMO_DIR=<scratch>` and `CUDA_VISIBLE_DEVICES=`. The check then reads the
same road, and therefore the same scenario-derived constants, as the worker it is
asking about, while touching none of the worker's files and none of its GPU.

**Read process state rather than logs when the logs are quiet.**
`/proc/<pid>/environ` answered "did the launcher's environment variable reach the
worker" immediately, where the log would only have answered it when HOORL started
three hours later. `ps -o etime,time,pcpu` distinguishes a worker that is running
slowly from one that is not running at all: the failure of 2026-09-04, where 45
rollouts were lost, showed as trials completing in 0.01 s, which is elapsed time
accumulating while CPU time does not.

**What is safe and what is not.** Loading a dataset, reading a copied scenario
and reading `/proc` are all read-only. Calling `prepare_scenario`, or letting any
code path regenerate a scenario, is not: `make_sumo_set.BASE_PATH` is bound at
import from the environment, so a process that has imported it with the shared
directory will write there whatever it is told afterwards. That is how the
pre-flight gate came to overwrite the scenario it then refused to launch over.

## 주기형 배관 플래그의 판정 규칙 (2026-09-11, 본훈련 중 발견)

`i_hamappo.py:105` 가 배관 플래그를 "창 평균이 0.0 이면 결함"으로 판정하라고 적는다.
**주기형 플래그에는 그 규칙이 그대로 성립하지 않는다.**

본훈련 200,000스텝 로그에서 MA2HDQN 의 `wiring_target_synced` 는 에피소드 평균이
0.0049 로 설계값 1/200 과 맞는데, **어떤 에피소드에서는 최솟값이 0.0000 이다.**
그 모델의 에피소드당 갱신이 평균 273회이고 최소 68회이므로, 갱신이 주기 200 에
못 미친 에피소드에서는 동기화가 한 번도 일어나지 않는다. 정상 실행이 0 을 보고한다.

**고칠 것.** 판정 규칙을 이렇게 좁혀 적는다.

- 조건형(`neighbourhood_used`, `per_sampled`, `task_decomposed`,
  `global_critic_cooperative`, `behaviour_logp_stored`): 매 갱신에 켜져야 하므로
  창 평균이 1.0 이 아니면 결함이다.
- 주기형(`target_synced`, `policy_synced`, `actor_updated`): 창 평균이 1/N 근처여야
  하고, **갱신 횟수가 주기 N 을 넘는 창에서 0 이면 결함이다.** 갱신이 N 에 못 미친
  창의 0 은 정상이다.

본훈련 실측(100 에피소드):

    TD3         actor_updated   0.4999   policy_delay 2 의 역수
    I-HAMAPPO   policy_synced   0.2500   policy_sync_interval 4 의 역수
    MA2HDQN     target_synced   0.0049   주기 200 의 역수

셋 다 설계값과 일치한다. 지금 고치지 않는 이유는 실행 중 `src/` 를 건드리지 않기
때문이고, 본훈련이 끝난 뒤 `i_hamappo.py:105` 의 규칙 서술을 위 두 갈래로 나눈다.
