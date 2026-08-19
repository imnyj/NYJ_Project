# Paper 4 시각화 및 11대 타겟 산출물 전수 조사 핸드오프 리포트 (handoff.md)

**문서 유형**: Hard Handoff Report (Task Complete)  
**에이전트**: `explorer_o5_2`  
**작업 디렉토리**: `/home/imnyj/Workspace/paper4/.agents/explorer_o5_2/`  
**보고 대상**: 상위 오케스트레이터 (`parent`, ID: `b2af6a6b-58d2-40c7-a94a-6a2842ea1e6d`)  
**작성일시**: 2026-08-19T20:38:00Z  

---

## 1. Observation (직접 관찰 결과)

1. **11대 타겟 산출물 파일 구비 현황**:
   - `/home/imnyj/Workspace/paper4/visualizer/` 내 다음 13개 파일 확인:
     - `1_ablation_study.png` (436,290 bytes)
     - `2_optuna_sensitivity_table.csv` (2,279 bytes) & `2_optuna_sensitivity_table.tex` (3,353 bytes)
     - `3_reward_convergence.png` (983,568 bytes)
     - `4_tsne_clustering.png` (227,405 bytes)
     - `5_moe_routing.png` (285,248 bytes)
     - `6_cbr_trace.png` (805,007 bytes)
     - `7_pdr_vs_density.png` (539,199 bytes)
     - `8_aoi_vs_density.png` (409,896 bytes)
     - `9_pdr_vs_distance.png` (585,479 bytes)
     - `10_aoi_vs_distance.png` (499,366 bytes)
     - `11_hardware_feasibility_table.csv` (1,159 bytes) & `11_hardware_feasibility_table.tex` (1,960 bytes)

2. **PNG 이미지 해상도(DPI) 실측 결과 (PIL Inspection)**:
   - `python3 -c "from PIL import Image; ... img.info.get('dpi')"` 실행 결과:
     - `1_ablation_study.png`: `(299.9994, 299.9994)` (300 DPI)
     - `3_reward_convergence.png`: `(299.9994, 299.9994)` (300 DPI)
     - `4_tsne_clustering.png` ~ `10_aoi_vs_distance.png`: 모두 `(299.9994, 299.9994)` (300 DPI)
   - `visualizer/plot_figures.py:29` (`def save_dual_figure(..., dpi=300)`) 및 `visualizer/generate_visualizations.py:56` (`'savefig.dpi': 300`)에 `300 DPI`로 하드코딩되어 있음.

3. **x축 200,000 스텝 스케일 관찰 결과**:
   - `data/reward_convergence.csv:1-2`: `Episode` 컬럼이 1부터 100까지 정의되어 있음.
   - `data/ablation_study.csv:1-2`: `Episode` 컬럼이 1부터 25까지 정의되어 있음.
   - `visualizer/plot_figures.py:51,98`: `ep = df["Episode"]`로 x축을 플롯하고 있으며, `ax.set_xlabel("Training Episodes")`로 설정되어 x축이 1~100 또는 1~25로만 표기됨.
   - 반면 `data/models/REMO-DQN_convergence.csv:1-102`에는 `Episode` (1~100)와 `Global_Step` (2,000 ~ 200,000, 2k step 간격)이 모두 기록되어 있음.

4. **수렴 및 안정성 2단계 시각화 요소 관찰**:
   - `plot_figures.py`, `generate_visualizations.py` 코드 전체에서 `axvspan`, `axvline`, `Phase I / Phase II` 관련 배경 음영이나 텍스트 주석 코드가 전혀 존재하지 않음.

5. **17개 모델 범례 및 스타일 사양 일치 여부**:
   - `visualizer/plot_utils.py:52-223` 및 `visualizer/generate_visualizations.py:63-234`의 `MODEL_CONFIGS` / `BASELINES_SPEC` 검사 결과:
     - 1. REMO-DQN: `#FF0000`, `alpha=1.0`, `linewidth=2.4~2.5`, `zorder=20`, `marker='o'`
     - 2. Fixed 10Hz: `#0000FF`, `alpha=0.6`, `linestyle='--'`, `marker='s'`
     - 3. ReactDCC: `#4D96FF`, `alpha=0.6`, `linestyle='-.'`, `marker='^'`
     - 4. AdaptDCC: `#2A4B7C`, `alpha=0.6`, `linestyle=':'`, `marker='v'`
     - 5~17. MoEDQN (`#9B5DE5`), MAPPO (`#D783FF`), PPO (`#7A49A5`), SAC (`#00FF00`), DDPG (`#6BCB77`), TD3 (`#2E8B57`), DuelingDQN (`#FF9F1C`), DoubleDQN (`#FFD166`), VanillaDQN (`#D67229`), QLearning (`#1A1A1A`), SARSA (`#555555`), ActorCritic (`#888888`), DecisionTransformer (`#B5B5B5`)
     - `evaluation_plan.md §2`의 17대 모델 색상, 투명도, 순서와 **100% 일치함**.

6. **스크립트 파일명 저장 로직 관찰**:
   - `plot_figures.py:83, 129` 등: `save_dual_figure(fig, out_dir, "ablation_study")`, `save_dual_figure(fig, out_dir, "reward_convergence")` 등으로 접두사 번호 없이 저장함.

---

## 2. Logic Chain (논리적 추론 체계)

1. **(DPI 결함 도출)**:
   - [관찰 2]에서 모든 PNG 파일의 DPI가 300 DPI로 측정되었고 코드 기본값이 `dpi=300`으로 설정됨.
   - [ORIGINAL_REQUEST.md Follow-up 2026-08-19T20:28:19]에서 350 DPI PNG 생성을 엄격히 요구함.
   - ∴ 현재 산출물은 350 DPI 요구조건을 만족하지 못하며, `dpi=350`으로 변경 및 재렌더링이 필수적임.

2. **(200,000 스텝 및 2단계 시각화 결함 도출)**:
   - [관찰 3]에서 `reward_convergence.csv`와 `ablation_study.csv`는 x축에 1~100 및 1~25 에피소드 값을 사용함.
   - [관찰 3]에서 실제 시뮬레이션 로그(`data/models/*.csv`)에는 200,000 스텝(`Global_Step`)이 존재함.
   - [관찰 4]에서 수렴 구간과 수렴 후 안정성 구간을 구분하는 인디케이터가 전무함.
   - [ORIGINAL_REQUEST.md R1, R2]에서 x축에 200,000 iterations 표시 및 (1) Convergence Phase, (2) Post-Convergence Stability Phase 시각화를 필수 조건으로 명시함.
   - ∴ `1_ablation_study.png`와 `3_reward_convergence.png`의 x축을 200,000 스텝 스케일로 교체하고, `axvspan` 및 주석을 통해 2단계 구간을 명확히 시각화해야 함.

3. **(스크립트 파이프라인 자동화 결함 도출)**:
   - [관찰 6]에서 스크립트 실행 시 번호 접두사가 없는 파일명으로만 저장됨.
   - ∴ `plot_figures.py`, `generate_visualizations.py`, `plot_all.py`가 직접 번호 접두사(`1_`~`11_`)를 붙여 저장하도록 리팩토링되어야 재현성이 완성됨.

---

## 3. Caveats (한계 및 가정 사항)

1. **실제 RL 재학습 미수행 (조사 전용 에이전트)**:
   - 본 에이전트는 Read-Only 조사 에이전트이므로 소스 코드 및 시뮬레이션 스크립트를 직접 수정하거나 모델을 재학습하지 않았습니다.
2. **기존 모델 로그 데이터의 유효성**:
   - `data/models/` 디렉토리에 존재하는 17개 모델의 `.pth`, `.pkl`, `*_convergence.csv` 파일(2,000~200,000 스텝)의 데이터 구조가 온전함을 확인하였으며, 이를 기반으로 시각화 스크립트를 즉시 수정할 수 있습니다.

---

## 4. Conclusion (최종 평가 및 권고사항)

- **종합 판정**: **조건부 반려 (Need Minor Revision before Final Sign-off)**
- **주요 수정 대상**:
  1. `visualizer/plot_figures.py` 및 `visualizer/generate_visualizations.py`의 `save_dual_figure` dpi 파라미터를 `350`으로 수정.
  2. `1_ablation_study.png`와 `3_reward_convergence.png`의 x축을 `0 ~ 200,000 Steps`로 스케일링하고, `Phase I: Exploration & Convergence` ($0 \sim 120\text{k}$) 및 `Phase II: Steady-State Stability` ($120\text{k} \sim 200\text{k}$) 배경 음영(`axvspan`) 및 라벨 추가.
  3. 스크립트의 저장 파일명을 `1_ablation_study.png` ~ `11_hardware_feasibility_table.tex`로 일치시키고 `plot_all.py` 한 번의 실행으로 전체 11대 타겟이 350 DPI로 자동 빌드되도록 파이프라인 정비.

---

## 5. Verification Method (독립 검증 방법)

상위 오케스트레이터 및 후속 에이전트는 다음 명령어로 본 보고서의 관찰 결과를 재현/검증할 수 있습니다:

1. **DPI 검증 명령**:
   ```bash
   python3 -c "
   from PIL import Image
   import os
   for f in sorted(os.listdir('/home/imnyj/Workspace/paper4/visualizer')):
       if f.endswith('.png'):
           img = Image.open(os.path.join('/home/imnyj/Workspace/paper4/visualizer', f))
           print(f'{f:30} -> DPI: {img.info.get(\"dpi\")}')
   "
   ```

2. **x축 및 에피소드 스케일 확인 명령**:
   ```bash
   head -n 5 /home/imnyj/Workspace/paper4/data/reward_convergence.csv
   head -n 5 /home/imnyj/Workspace/paper4/data/models/REMO-DQN_convergence.csv
   ```

3. **17개 모델 색상 및 순서 검증 명령**:
   ```bash
   python3 -c "
   import sys
   sys.path.insert(0, '/home/imnyj/Workspace/paper4/visualizer')
   from plot_utils import MODEL_CONFIGS
   for i, m in enumerate(MODEL_CONFIGS):
       print(f'{i+1:2d}. {m[\"name\"]:25} | {m[\"color\"]} | alpha={m[\"alpha\"]}')
   "
   ```
