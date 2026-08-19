# Dispatch Instructions — Worker M2 (Visualizer Refactoring & 350 DPI Re-plotting)

## Identity
- Role: Visualizer Refactoring & Implementation Worker (`worker_m2_1`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/worker_m2_1/`

## Mandatory Reading & Context
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/PROJECT.md`
- `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`
- `/home/imnyj/Workspace/paper4/.agents/explorer_o5_2/handoff.md`

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Task Details
1. **파일 락 및 감사 로그 준수 (GEMINI.md Rules 3 & 4)**:
   - 파일 수정 전 `/home/imnyj/Command/core/lock_manager.py`를 통해 락을 획득하고 작업 후 해제하십시오.
   - 파일 수정 후 `/home/imnyj/Command/core/audit_logger.py`를 통해 변경 내역을 기록하십시오.

2. **시각화 스크립트 수정 및 기능 구현**:
   - 대상 파일: `/home/imnyj/Workspace/paper4/visualizer/plot_figures.py`, `/home/imnyj/Workspace/paper4/visualizer/generate_visualizations.py`, `/home/imnyj/Workspace/paper4/visualizer/plot_utils.py`, `/home/imnyj/Workspace/paper4/visualizer/plot_all.py`, `/home/imnyj/Workspace/paper4/visualizer/generate_tables.py`
   - **해상도**: 모든 PNG 이미지 저장 시 `dpi=350`을 엄격히 적용하십시오 (`plt.savefig(..., dpi=350)` 또는 `save_dual_figure(..., dpi=350)`).
   - **200,000 스텝 x축 스케일링**:
     - `3_reward_convergence.png`: `data/models/*_convergence.csv`의 `Global_Step` (2,000 ~ 200,000)을 직접 x축으로 사용하거나 에피소드(1~100) x 2,000 스텝 변환하여 x축이 0부터 200,000 스텝까지 명시적으로 표현되도록 라벨(`Training Steps` 또는 `Global Iterations ($\times 10^3$)`)과 틱을 설정하십시오.
     - `1_ablation_study.png`: x축을 200,000 스텝 스케일로 설정하여 구조적/보상 소거 모델의 200,000 스텝 수렴 양상을 명확히 표현하십시오.
   - **수렴/안정성 2단계 구분 시각화**:
     - `1_ablation_study.png` 및 `3_reward_convergence.png`에 `ax.axvspan()`을 활용하여 `Phase I: Convergence & Exploration (0 ~ 120k Steps)` (연한 회색/청색 음영) 및 `Phase II: Post-Convergence Steady-State Stability (120k ~ 200k Steps)` (연한 녹색 음영)과 텍스트 라벨을 추가하십시오.
   - **번호 접두사 자동 저장**:
     - `visualizer/` 내 산출물이 정확히 다음 번호 접두사를 갖도록 저장 로직을 보장하십시오:
       1. `1_ablation_study.png`
       2. `2_optuna_sensitivity_table.csv` & `2_optuna_sensitivity_table.tex`
       3. `3_reward_convergence.png`
       4. `4_tsne_clustering.png`
       5. `5_moe_routing.png`
       6. `6_cbr_trace.png`
       7. `7_pdr_vs_density.png`
       8. `8_aoi_vs_density.png`
       9. `9_pdr_vs_distance.png`
       10. `10_aoi_vs_distance.png`
       11. `11_hardware_feasibility_table.csv` & `11_hardware_feasibility_table.tex`
   - **17개 모델 스타일 및 범례 순서 엄수**:
     - `evaluation_plan.md §2` 및 `PROJECT.md §Interface Contracts`에 명시된 17개 모델 순서, HEX 색상, 선스타일, 마커, REMO-DQN Bold Red(#FF0000, zorder=99, lw=2.5)를 완벽히 유지하십시오.

3. **실행 및 자체 검증**:
   - `python3 /home/imnyj/Workspace/paper4/visualizer/plot_all.py` 및 관련 스크립트를 실행하여 오류 없이 11대 타겟 산출물이 모두 정상 생성되는지 확인하십시오.
   - PIL을 통해 생성된 9개 PNG 파일의 DPI가 350 DPI인지 검증하십시오.
   - 검증 커맨드 및 실행 결과를 `handoff.md`에 상세히 기록하십시오.

## Output Requirements
- 작업 디렉토리(`/home/imnyj/Workspace/paper4/.agents/worker_m2_1/`)에 `progress.md` 및 `handoff.md`를 작성하고 완료 시 `send_message`로 상위 오케스트레이터에게 보고하십시오.
