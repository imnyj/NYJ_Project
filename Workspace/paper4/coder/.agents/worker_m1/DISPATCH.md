# DISPATCH — 2026-08-27T01:58:25Z

## Tasks Assigned
1. `src/aoi_env.py`:
   - Import `P_MIN, P_MAX, DELTA_MIN, DELTA_MAX` from `src.rl_interface`.
   - Align default `p_min, p_max` to `P_MIN (10.0), P_MAX (23.0)`.
   - Align default `step_length` to 0.1, `rsu_range` to 300.0.
   - Ensure 4-term reward formula $R_t = -(w_1 \cdot \text{Norm}(e^2) + w_2 \cdot \text{Norm}(P_{tx}) + w_3 \cdot \text{Norm}(C_{freq}) + w_4 \cdot \mathbb{I}_{redundant})$ with default weights $w_1=0.5, w_2=0.2, w_3=0.2, w_4=0.1$.
   - Generalize power normalization to `(p - p_min) / (p_max - p_min)`.
   - Anti-Mocking Assertion A4: strictly verify:
     * $0.0 \le \text{Norm}(e^2) \le 1.0$
     * $0.0 \le \text{Norm}(P_{tx}) \le 1.0$
     * $0.0 \le \text{Norm}(C_{freq}) \le 1.0$
     * $\mathbb{I}_{redundant} \in \{0.0, 1.0\}$
     * $R_t == -(w_1 \cdot \dots)$ using `math.isclose`
     * $R_t \le 0.0$
2. `src/hot_swap_trainer.py`:
   - Fix `save_checkpoint(filepath, best_reward=None)`: persist `"best_reward": best_reward` in the checkpoint dictionary.
   - Fix `load_checkpoint(filepath)`: return loaded checkpoint dict.
   - Fix `run_hot_swap_training(..., resume=False)`:
     * When `resume=True`, load `best_reward` from `{model_name}_best.pt` or the checkpoint file if it exists, instead of resetting to `-inf`.
     * Pass `best_reward` to `save_checkpoint` during periodic and best checkpoint saves.
   - Ensure default `rsu_range=300.0`, `--step-length 0.1`.
   - Ensure `step_tx_power` per vehicle and `_is_redundant_update` logic are correct.
3. Verification:
   - Run tests: `/home/imnyj/venv/bin/pytest tests/test_aoi_env_genuine.py -v`
   - Test checkpoint saving and loading with `best_reward`.

Exclusively owned files:
- `src/hot_swap_trainer.py`
- `src/aoi_env.py`
