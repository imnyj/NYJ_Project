# BRIEFING — 2026-08-27T02:00:00Z

## Mission
Investigate R3 (Environment Knobs & HPO) and R4 (Baseline Scraping & References) for the AoI-aware V2I uplink RL scheduling pipeline architectural fixes.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, analyzer, synthesizer
- Working directory: /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_3/
- Original parent: 3d6a38f8-f0cb-48c4-98ea-b46062a1aceb
- Milestone: Initial Survey & Investigation (R3 & R4)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement changes in source code
- Strictly write files only inside `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_3/`
- Korean language for final report and messages

## Current Parent
- Conversation ID: 3d6a38f8-f0cb-48c4-98ea-b46062a1aceb
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `src/sumo/make_sumo_set.py`, `src/sumo/generated.sumocfg`, `src/sumo/.sumo_gen_signature.json`
  - `src/NetSim.py`
  - `src/aoi_env.py`
  - `src/hot_swap_trainer.py`
  - `src/rl_interface.py`
  - `src/evaluate.py`
  - `src/hpo.py`
  - `src/baselines/` (all 11 files)
  - `run_all.py`, `verify_environment.py`, `baselines_references.json`
  - `tests/` (all test files and contract_adapters.py)
  - `etc/scripts/`
- **Key findings**:
  - R3.1 RSU_RANGE: `make_sumo_set.py` has 300.0, but `NetSim.py:443` overwrites it to 800.0 in `pre_define()`; `hot_swap_trainer.py:441,719`, `aoi_env.py:304,402`, `evaluate.py:215`, `rl_interface.py:87`, `.sumo_gen_signature.json` and multiple test fixtures still default to 800.0.
  - R3.2 step-length: `make_sumo_set.py` has 0.1s and `generated.sumocfg` has `<step-length value="0.1"/>`, but `hot_swap_trainer.py:824-825` and `NetSim.py:532` pass `"--step-length", "1.0"` to SUMO startup cmd; `aoi_env.py:399` defaults to 1.0.
  - R3.3 evaluate.py speed: `evaluate.py:239` hardcodes `"speed": 10.0`. Live vehicle speed is available from `env.last_speeds[vid]` or `_get_vehicle_state_dict`.
  - R3.4 hpo.py search space: `sample_reward_weights(trial)` samples `w1_raw..w4_raw` and normalizes to `w1..w4`, but `aoi_env.py` uses legacy key mapping and needs clean alignment.
  - R4 Baseline Scraping: All 11 files in `src/baselines/` must be deleted. Imports/references in `hot_swap_trainer.py`, `evaluate.py`, `hpo.py`, `run_all.py`, `tests/`, and `etc/` must be systematically removed/cleaned.
- **Unexplored areas**: None (all R3 & R4 items explored and verified).

## Key Decisions Made
- Fully cataloged all file locations, line numbers, exact code diffs, and deletion/refactoring strategies for R3 & R4.

## Artifact Index
- DISPATCH.md — Dispatch logs
- BRIEFING.md — Working memory index
- progress.md — Liveness & progress tracker
- handoff.md — Final investigation report
