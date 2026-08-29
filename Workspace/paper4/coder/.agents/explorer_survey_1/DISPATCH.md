## 2026-08-27T01:54:21Z
<USER_REQUEST>
You are Explorer 1 for the AoI-aware V2I uplink RL scheduling pipeline architectural fixes.
Your working directory is /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_1/

Read the following reference documents:
1. /home/imnyj/Workspace/paper4/coder/.agents/ORIGINAL_REQUEST.md
2. /home/imnyj/Workspace/paper4/Conversation.md
3. /home/imnyj/Workspace/paper4/idea/scenario.md

Investigate the current codebase focusing on:
- R1: `src/hot_swap_trainer.py` and `src/aoi_env.py`
  * 4-term reward formula: check where $I_{redundant}$ penalty was removed or partially modified, and how it should be restored.
  * Power normalization: check current implementation vs `(p - p_min) / (p_max - p_min)`.
  * `tx_powers[-1]` bug: check how vehicle transmission powers are indexed/passed in the environment.
  * Anti-Mocking Assertion A4: inspect current assertion in `src/aoi_env.py` and verify what formula it checks against.
  * Resume logic in `hot_swap_trainer.py`: inspect how checkpoints are saved and loaded, specifically tracking `best_reward` in `.pt` file to prevent weak episodes from overwriting `best.pt`.
- Relevant unit and integration tests under `tests/` covering trainer and env.

Run tests if needed using pytest to see existing test failures or passes.
Document your findings, code diff analysis, exact line numbers, and recommended fix strategies in `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_1/handoff.md`.
Use Korean for reporting.
When done, message the orchestrator with your findings.
</USER_REQUEST>
