# Original User Request

## Initial Request — 2026-08-18T03:32:56Z

# Teamwork Project Prompt — Final

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

본 프로젝트는 V2X 혼잡 제어(DCC)를 위해 제안된 하이브리드 강화학습 모델(REMO-DQN)의 우수성을 14개 최신 알고리즘들과 비교 분석하는 논문(Paper4) 작성입니다. 타겟 저널은 **IEEE Transactions on Wireless Communications (TWC)** 입니다.

Working directory: /home/imnyj/Workspace/paper4

## Requirements

### R1. 서론 (Introduction) 작성 가이드라인
IEEE TWC 수준의 깊이 있는 서술을 위해, 각 문단은 최소 5문장 이상으로 상세하고 짜임새 있게 작성할 것.
- **문단 1 (배경):** V2X 및 VANET의 중요성, 고밀도 환경에서의 신뢰성 있는 통신 채널 확보의 어려움, DCC의 필요성, 정보 연령(AoI) 지표의 중요성.
- **문단 2 (문제점 1):** 기존 ETSI 표준 DCC 기법(ReactDCC, AdaptDCC)의 고정 규칙으로 인한 CBR 요동(Oscillation) 및 폭주(Burst) 한계. 단순 RL 도입의 한계와 PDR 추락/Fake AoI 문제.
- **문단 3 (문제점 2):** 다양한 최신 DRL(PPO, SAC, MAPPO 등)의 등장이 있었으나 V2X 환경에서의 총체적/경험적 비교 부재. 복잡한 비선형적 교통/채널 상태를 인지하고 동적으로 라우팅할 수 있는 통합 아키텍처(MoE 등) 적용의 필요성.
- **문단 4 (제안 방안 및 기여도):** 14개 RL 알고리즘 종합 비교 및 새로운 하이브리드 아키텍처(ResNet+MoE+Dueling DQN) 제안. 
  - (기여도 1) 14개 알고리즘의 최적화 및 수렴성 종합 분석. 
  - (기여도 2) 채널 안정성 확보 및 고밀도 환경에서 PDR 방어, 최저 AoI 달성. 
  - (기여도 3) 샘플 효율성 및 하드웨어 추론 지연시간(Latency) 검증으로 실효성 입증.
- **문단 5 (글 구성 안내):** 2장 관련 연구, 3장 네트워크 모델, 4장 본문(시나리오), 5장 성능 평가, 6장 결론으로 이어지는 구성 안내.

### R2. 관련 연구 (Related Works) 설계
- 기존 연구 흐름(표준 DCC, 단일 DRL, 다중 에이전트 DRL) 외에, **2025~2026년 MoE+무선망/RL 결합 관련 최신 논문(예: "Mixture of Experts for Decentralized Generative AI and Reinforcement Learning in Wireless Networks", 2025)**을 반드시 포함할 것.
- 비교 테이블 포함: [Reference, Year, Optimization Target (AoI/PDR), RL Algorithm Used, Number of Baselines, MoE/Ensemble Applied (Y/N)]

### R3. 시스템 모델 (Network Model) 구조
- System Overview, MDP Formulation (상태, 행동, 다중 보상 함수 R1, R2), Proposed Architecture (REMO-DQN) 서술.

### R4. 본문 (Main Body - 시나리오 흐름)
- 4.1 Packet Generation & Traffic Mixed Scenario: 안전 비콘, 다운로드, 메시지 등 이기종 패킷 발생 모델.
- 4.2 Channel Contention & MAC Collision: 밀도 증가 시 CSMA/CA MAC 계층의 패킷 충돌 및 큐 병목 메커니즘.
- 4.3 DRL-based Congestion Recognition: OBU 에이전트의 주기적 채널 상태 관측 및 혼잡 페널티 산출.
- 4.4 Dynamic Routing & Transmission Control: 관측된 상황(여유 vs 혼잡)에 맞춰 MoE가 전문가 네트워크를 라우팅하여 최종 전송 주기(Rate)를 최적화하는 과정.

### R5. 성능 평가 (Performance Evaluation) 병합
기존 14개 모델 시뮬레이션 결과와 7대 핵심 지표를 모두 융합하여 서술.
- 5.1 실험 세팅: SUMO 환경, 14개 벤치마크 모델 설명.
- 5.2 (Metric 1) 학습 수렴도: 14개 모델의 Reward Convergence 비교 (DQN 기반 모델의 샘플 효율성 우위 증명).
- 5.3 (Metric 2) 채널 안정성 (Time-Series CBR Trace): 표준 기법의 요동(Oscillation)과 제안 방안의 안정성 대조.
- 5.4 (Metric 3 & 4) PDR & 에너지 효율: 차량 밀도 증가 시 PDR 방어 우수성 및 통신 에너지 소모량.
- 5.5 (Metric 5) AoI vs Density: PDR 극대화에 따른 Trade-off 기회비용 투명 분석.
- 5.6 (Metric 6) 하드웨어 실효성: MCU 환경에서의 추론 지연시간/메모리(FLOPs) 프로파일링.

## Acceptance Criteria
- [ ] 서론 각 문단이 5문장 이상으로 논리적으로 충분히 서술되었는가.
- [ ] 성능 평가 지표에 14개 알고리즘 비교와 CBR, PDR, AoI, Latency 지표가 모두 포함되었는가.
- [ ] 글의 언어가 한글(Korean)이며, TWC 저널 수준의 격식과 마크다운(수식 포함) 포맷을 만족하는가.

## Follow-up — 2026-08-19T07:42:02Z

# Teamwork Project Prompt — Final

> Status: Launched
> Goal: Execute the evaluation & visualization pipeline using a Coder-Critic workflow, followed by automated background reporting and a one-time GitHub upload.

Working directory: /home/imnyj/Workspace/paper4

## Requirements

### R1. Evaluation Plan Parsing & Data Preparation
- Read `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md` to perfectly understand the 11 target outputs, legend order, and color/line style specifications.
- Check if the required CSV data for these plots already exists in `data/` or `logs/`. If any required data is missing, write and execute scripts to extract/generate the missing CSV data from simulation logs or model checkpoints.

### R2. Coder-Critic Iterative Visualization Pipeline
- Implement a **Coder-Critic** multi-agent loop.
- **Coder**: Write Python scripts (using `matplotlib`/`seaborn`/`pandas`) to generate the 11 target outputs (graphs as PDFs, tables as CSV/Tex, t-SNE as PNG) strictly adhering to the colors, line styles, and legend order defined in the plan.
- **Critic**: Review the generated scripts and the output files. The Critic must verify that the visual output perfectly matches the `evaluation_plan.md` guidelines. If there are any mismatches, the Critic must order the Coder to revise the code. This loop continues until the Critic gives a final approval.

### R3. Workspace Cleanup
- Move any pre-existing "old" graph images or outdated visualization files currently inside the `visualizer/` directory into a newly created `visualizer/backup/` directory. The main `visualizer/` directory should only contain the fresh, Critic-approved outputs and the scripts used to generate them.

### R4. Automated Reporting & One-time GitHub Upload
- Setup cron jobs to report progress to the user at exactly 06:00, 12:00, 18:00, and 24:00 (local time).
- Setup a 5-hour idle timer. If the agent team reaches 5 hours of idle time after completing the primary tasks, it must execute a one-time `/learn` self-improvement routine (updating `logs/execution_notes.md` or skills) and perform a `git commit` and `git push` to upload the entire workspace to GitHub. This 5-hour task must ONLY be executed once.

## Acceptance Criteria
- [ ] All required data is saved as CSV files before visualization begins.
- [ ] The Coder-Critic loop is visibly executed, with the Critic providing feedback until perfection.
- [ ] 11 final outputs are generated in the `visualizer/` directory, exactly matching the color/legend specifications in the plan.
- [ ] Old visualizer files are successfully moved to `visualizer/backup/`.
- [ ] Cron jobs for 06/12/18/24 reporting are actively running.
- [ ] A 5-hour timer is set up to trigger the one-time GitHub upload and self-reflection.

## Follow-up — 2026-08-19T08:18:20Z

# Teamwork Project Prompt — Final

> Status: Launched
> Goal: Execute a massive RL training and data extraction pipeline, validate 200,000-step convergence for all models, and complete the visualization walkthrough using a strict Coder-Critic loop.

Working directory: /home/imnyj/Workspace/paper4

## Requirements

### R1. Environment & Implementation Validation
- Verify the SUMO environment setup using `SumoNetSim1.1.5/src/sumo`. Extract the configuration and create a `config.md` so users can easily change environment variables (like vehicle speed, density = 0 for random).
- Verify the physical implementation of the communication module, 14 baseline models, and the proposed REMO-DQN.

### R2. Massive Raw Data Extraction & 200k Step Training (Coder-Critic)
Read `visualizer/prompt.md` and `visualizer/evaluation_plan.md`. For each of the required studies, the **Coder** must implement the training/evaluation scripts and the **Critic** must verify the generated Raw CSV data.
- **Ablation Studies**: Generate raw CSV data for Structure ablation (ResNet/MoE/Dueling), Reward ablation ($R_1, R_2, R_3$), and State ablation.
- **Optuna Optimization**: Run and save Optuna hyperparameter tuning results for the proposed model AND all baselines.
- **200,000-step Convergence**: Check existing CSVs. Every model (baselines + proposed) MUST have been trained for at least 200,000 steps until clear reward convergence. If any model is missing or the CSV data is weak/fake, the Coder MUST write the script and run the actual RL training to generate real data. Save the converged `.pth` models.
- **Time/Environment Metrics**: Using the converged models, run evaluations to extract time-series data (CBR, PDR, AoI) and environment-varied data (density, speed vs PDR/AoI) into CSVs.

### R3. Walkthrough Completion & Visualization
- Continuously check `walkthrough.md`. As raw data is rigorously generated, run the visualization scripts to generate the PNG graphs.
- Do not stop until every single item in the `walkthrough.md` checklist is completed with real, validated data.

### R4. Analysis Generation
- Based on the real data, generate a textual analysis explaining the meaning of the `moe_routing` and `tsne_clustering` graphs (as requested in `prompt.md` #4, #5). Save this as `analysis_report.md`.

### R5. Automated Reporting & One-time GitHub Upload
- Setup cron jobs to report progress to the user at exactly 06:00, 12:00, 18:00, and 24:00 (local time).
- Setup a 5-hour idle timer. If the agent team reaches 5 hours of idle time after completing all tasks, execute a one-time `/learn` self-improvement routine (updating `logs/execution_notes.md`) and perform `git commit` and `git push` to upload the workspace to GitHub. This 5-hour task must ONLY be executed once.

## Acceptance Criteria
- [ ] `config.md` is created explaining the SUMO setup.
- [ ] All required CSVs (Ablations, Optuna, 200k-step Convergence, Eval metrics) are fully populated with real training data for all specified models.
- [ ] If data is missing, actual training processes are executed to gather it.
- [ ] All checklist items in `walkthrough.md` are checked off.
- [ ] `analysis_report.md` is generated containing the deep analysis of MoE routing and t-SNE clustering.
- [ ] 06/12/18/24 reporting crons and the 5-hour one-time GitHub upload timer are active.

## Follow-up — 2026-08-19T20:28:19+09:00

# Teamwork Project Prompt — Final

> Status: Launched
> Goal: Re-run and fix the evaluation & visualization pipeline. Specifically, the "Reward Convergence" must explicitly show at least 200,000 iterations to prove both convergence speed and post-convergence stability.

Working directory: /home/imnyj/Workspace/paper4

## Requirements

### R1. 200,000 Iterations Enforcement (Critical Correction)
- The previous pipeline failed to properly represent 200,000 iterations for convergence.
- You must ensure that **every single model** (17 baselines) and **ablation study** is trained for at least **200,000 iterations (steps)**.
- The CSV data for `reward_convergence.csv` and `ablation_study.csv` MUST contain data spanning 200,000 steps (you can bin or average them, but the total scale must be 200,000).
- If the current CSVs only go up to 100 (e.g., 100 episodes instead of 200,000 steps) or mock data was used, **the Coder MUST write a script to re-extract the exact 200,000 step logs or re-train the models to 200,000 steps**.

### R2. Re-plotting Convergence Graphs
- Update `plot_figures.py` and any related scripts so that the x-axis of `1_ablation_study.png` and `3_reward_convergence.png` is strictly set to represent 200,000 iterations.
- The graphs must clearly visualize two phases: (1) The initial Convergence phase, and (2) The Post-Convergence Stability phase.
- The **Critic** must rigorously reject any graph that does not explicitly show 200,000 steps on the x-axis.

### R3. Output Format and Checklist
- Ensure all 11 target outputs are generated as 350 DPI PNGs (and CSV/Tex for tables) with numbered prefixes (`1_ablation_study.png` ... `11_hardware_feasibility_table.tex`) in the `visualizer/` directory.
- Update `walkthrough.md` checklist upon completion.

### R4. Automated Reporting
- Set up a cron job to report progress at 06:00, 12:00, 18:00, and 24:00 (local time).
- Do not stop the goal until the 200,000 iterations constraint is completely verified and visually proven.

## Acceptance Criteria
- [ ] `reward_convergence.csv` and `ablation_study.csv` reflect 200,000 training iterations.
- [ ] `1_ablation_study.png` and `3_reward_convergence.png` have an x-axis spanning up to 200,000, clearly showing both convergence and post-convergence stability.
- [ ] All other graphs and tables are successfully re-generated to match this data scale.
- [ ] The Coder-Critic loop is strictly enforced.
- [ ] Crons are active.

## Follow-up — 2026-08-19T20:32:48+09:00

# Teamwork Project Prompt — Final

> Status: Launched
> Goal: Execute the ENTIRE training, Optuna optimization, and data extraction pipeline using ONLY real simulations. NO mock data allowed.

Working directory: /home/imnyj/Workspace/paper4

## Requirements

### R1. Strictly Real Simulations & No Mock Data
- The Coder MUST NOT generate mock CSV files using `numpy.random` or mathematical formulas.
- ALL data must be extracted by actually running the SUMO simulation scripts and RL environments located in the codebase.
- The user will audit the source of the simulation files later to ensure actual SUMO/RL code was executed.

### R2. Minimum 200,000 Steps for Training
- Every single RL model (all baselines and proposed REMO-DQN) must be trained for a MINIMUM of 200,000 steps.
- The resulting `reward_convergence.csv` and `ablation_study.csv` MUST contain actual data points spanning 200,000 steps, clearly demonstrating the convergence point and post-convergence stability.

### R3. Optuna Hyperparameter Optimization
- Before the final 200,000-step training, every model must undergo Optuna hyperparameter optimization.
- The models must be trained using the optimal hyperparameters found by Optuna to ensure they are evaluated in their best state.
- The Optuna results must be saved, as the user will audit this optimization process.

### R4. Model Checkpointing
- Once a model completes its 200,000-step training, its final weights must be saved (e.g., `.pth` or `.pkl`) in the `data/models/` directory so they can be loaded for future evaluation graphs (CBR, PDR, AoI vs Density/Distance).

### R5. Visualization & Walkthrough
- After all real data is collected, generate the 11 target graphs (as numbered 350 DPI PNGs).
- The Coder-Critic loop must ensure the graphs accurately reflect the 200,000 steps and the Optuna-optimized performance.

## Acceptance Criteria
- [ ] No mock data generation scripts exist; all data comes from `sim_engine.py` or equivalent simulation runners.
- [ ] All models are trained for $\ge$ 200,000 steps.
- [ ] Optuna optimization logs/CSVs are generated and used for the final training.
- [ ] All 17 trained models are saved in `data/models/`.
- [ ] All graphs correctly visualize this rigorously collected data.

## Follow-up — 2026-08-19T22:06:16+09:00

# Teamwork Project Prompt — Final (Continuation after quota reset)

> Status: Launched
> Goal: CONTINUE and COMPLETE the real simulation training pipeline. The previous run was interrupted by a 429 quota error during the Victory Auditor re-audit phase.

## CRITICAL CONTEXT — What was already done before the crash:
1. `prepare_data.py` was already refactored to remove ALL `np.random` mock data routines. Legacy mock scripts were quarantined to `backup/legacy_mock_scripts_20260819/`.
2. 22 visualization artifacts (350 DPI) were regenerated from pure simulation data.
3. The first Victory Auditor REJECTED the initial submission due to `np.random` residue in `prepare_data.py`.
4. The team fixed this and was about to undergo a RE-AUDIT when the quota error hit.

## What you must do NOW:
1. Verify the fix is still intact: run `grep -rn 'np.random' visualizer/prepare_data.py` and confirm 0 matches.
2. Verify all 11 numbered target outputs exist in `visualizer/` with the `1_` through `11_` prefix naming.
3. Verify the convergence graphs (`1_ablation_study.png`, `3_reward_convergence.png`) show 200,000 steps on the x-axis with Phase I (Convergence) and Phase II (Stability) clearly marked.
4. Run the independent Victory Audit to confirm VICTORY.
5. If ANY issue is found, fix it using the Coder-Critic loop before re-auditing.

Working directory: /home/imnyj/Workspace/paper4

## Requirements

### R1. Strictly Real Simulations & No Mock Data
- The Coder MUST NOT generate mock CSV files using `numpy.random` or mathematical formulas.
- ALL data must come from actually running the SUMO simulation scripts and RL environments.
- The user will audit the simulation source files later.

### R2. Minimum 200,000 Steps for Training
- Every model must be trained for at least 200,000 steps.
- `reward_convergence.csv` and `ablation_study.csv` MUST span 200,000 steps, showing convergence AND post-convergence stability.

### R3. Optuna Hyperparameter Optimization
- Every model must use Optuna-optimized hyperparameters for its final training run.
- Optuna results must be saved for user audit.

### R4. Model Checkpointing
- All 17 trained model weights must be saved in `data/models/`.

### R5. Visualization & Walkthrough
- Generate all 11 target outputs as numbered 350 DPI PNGs in `visualizer/`.
- Update `walkthrough.md` checklist upon completion.

## Acceptance Criteria
- [ ] `grep -rn 'np.random' visualizer/prepare_data.py` returns 0 matches.
- [ ] All 11 numbered target outputs exist and are valid 350 DPI PNGs/CSVs/TeXs.
- [ ] Convergence graphs show x-axis up to 200,000 with Phase I/II annotations.
- [ ] All 17 model checkpoints exist in `data/models/`.


## Follow-up — 2026-08-20T17:29:56+09:00

# REMO-DQN (Paper4) 코드 전수 수정 프로젝트

REST 모드(논문 코드)의 12개 결함(C-1~M-12)을 `paper4_code_review_report.md`에 기재된 권장 실행 순서(C-3→C-1,C-2→H-4→H-5→H-6→M-7~M-12)에 따라 **한 항목씩** (수정→검증→기록) 사이클로 전부 수정한다. 수정 대상은 오직 `/code/` 디렉토리 내 파일만이며, 각 수정 후 **반드시** 독립 검증 스크립트를 실행하여 통과시킨 뒤 다음 항목으로 넘어간다.

Working directory: /home/imnyj/Workspace/paper4
Integrity mode: development

## 핵심 컨텍스트
- **제안 모델**: `ResNetMoEDQN` (ResNet + MoE + Dueling + Double DQN)
- **TinyMLP/"Proposed" 라벨**: 완전 폐기 (backup/로 이동)
- **규칙 파일**: `.rules/coder.md`와 `.rules/critic.md`를 반드시 준수
- **입력 보고서**: `/home/imnyj/Workspace/paper4/paper4_code_review_report.md` — 시작 전에 전부 읽을 것

## 사용자 확정 설계 결정

| 결정 | 선택 |
|---|---|
| C-3 CBR_TARGET | 채널 모델 유지, CBR_TARGET은 밀도별 시뮬레이션 측정으로 자동 설정 (스크립트 작성) |
| H-4 p_tx 그리드 | `[-5, 0, 5, 10, 15, 20]` dBm (6단계), 모든 hook이 `etsi_cam_layer.PTX_GRID_DBM`을 import |
| H-5 Ablation | VanillaDQN → +Double → +Dueling → +MoE → +ResNet (5단계, 한 번에 한 요소만 변경) |
| M-10 에피소드 수 | 500 에피소드 |
| M-10 ε 스케줄 | 지수 디케이 epsilon_decay=0.995 (500ep 후 ≈0.082) |
| 폐기 코드 | backup/로 이동 (train_final.py, aggregator.py, tinymlp_train*.py 등) |
| action_dim | 4(t_grid) × 6(p_tx_grid) = 24 (기존 16에서 변경, 모든 .pth 재학습 필요) |

## Requirements

### R1. 12개 항목 전수 수정 (권장 실행 순서 준수)

보고서의 12개 항목을 **정확히 아래 순서**로 수정한다. 하나라도 빠짐없이, 한 번에 몰아서 처리 금지:

**C-3 보상 함수 재설계**:
- 보상 = `-1.0*over - 0.5*osc - 0.3*stale - 0.05*cost` (over-target only + oscillation + staleness + cost)
- `DuelingDQNHook.__init__`에 `self.prev_cbr = {}` 추가, `reset_episode`에서 `clear()`
- **모든 hook의 predict 메서드**(DuelingDQNHook, SARSAHook, DecisionTransformerHook, MAPPOHook 등)에 동일 보상 적용
- CBR_TARGET: 밀도별 자동 보정 스크립트(`measure_cbr_target.py`) 작성하여 Fixed10Hz 기준 최대 CBR 측정 → `CBR_TARGET = max_cbr * 0.8` 등으로 산출
- `cost` 항에서 이전 액션의 T_GenCam을 참조하기 위해 `self.prev_t_gencam[vid]` 저장

**C-1 평가 러너 DRL 등록**:
- `sensitivity_runner.py`의 SA1/SA2 메서드 리스트에 `VanillaDQN`, `DoubleDQN`, `DuelingDQN`, `MoEDQN`, `ResNetMoEDQN` 추가
- `"Proposed"`(TinyMLP 매핑) 라벨 제거
- 결과 집계/플롯의 라벨 매핑도 수정

**C-2 러너 가중치 로드 배선**:
- `setup_eval_hook(method)` 함수 추가: agent 생성 → .pth 로드 → epsilon=0 → set_agent → is_training=False
- DRL_SETUP dict에 5개 모델(ResNetMoEDQN, MoEDQN, DuelingDQN, DoubleDQN, VanillaDQN) 등록
- 각 DRL 메서드 실행 전에 `setup_eval_hook()` 호출하도록 배선

**H-4 p_tx 그리드 통일**:
- `etsi_cam_layer.py`의 `PTX_GRID_DBM = [-5, 0, 5, 10, 15, 20]`으로 변경
- 모든 hook(DuelingDQNHook, SklearnHook, TinyMLPHook 등)이 `from etsi_cam_layer import PTX_GRID_DBM` 사용
- 30dBm 포함 그리드 제거

**H-5 Ablation 재구성**:
- 5단계: VanillaDQN(Single,MLP) → DoubleDQN(Double,MLP) → DuelingDQN(Double,Dueling,MLP) → MoEDQN(Double,Dueling,MoE) → ResNetMoEDQN(Double,Dueling,MoE,ResNet)
- 기존 에이전트 파일(`dqn_agent.py`, `ddqn_agent.py`, `dueling_dqn_agent.py`, `moe_agent.py`, `resnet_moe_agent.py`)을 활용
- action_dim=24로 통일
- 파일명/라벨 정합: vanilla_dqn.pth, ddqn.pth, dueling_dqn.pth, moe_dqn.pth, resnet_moe_dqn.pth

**H-6 Tabular 상태 정규화**:
- `qlearning_agent.py`, `sarsa_agent.py`의 `state_bounds` 이웃 축을 `(0.0, 1.0)`으로 통일
- 주석도 정정
- 빈 `train_step()` no-op 메서드 추가 (AttributeError 방지)

**M-7 n_est 국소 이웃**: 이미 수정됨 확인, 검증만 수행

**M-8 국소 CBR**: 차량별 국소 CBR을 `vdata["cbr"]`로 전달하도록 `sim_engine.py` 수정

**M-9 하드코딩 경로 제거**:
- `sim_engine.py`의 4개 절대경로 → 환경변수/shutil.which
- `sensitivity_runner.py`의 기본경로 → 상대경로
- `aggregator.py` → backup/로 이동
- `train_final.py` → backup/로 이동

**M-10 학습량 재설정**: 모든 학습 스크립트 `num_episodes=500`, `epsilon_decay=0.995`

**M-11 train_7_models 정정**: 클래스 수 25→24, 라벨 `TinyMLP (Proposed)` → `REMO-DQN (Proposed)`

**M-12 Terminal 전이**: 이미 terminate_vehicle() 존재 확인, 모든 hook에 적용 검증

### R2. 체크리스트 관리

`idea/paper4_code_fix_tasklist.md`를 생성하여 12개 ID 각각에 [파일:라인, 문제, 수정계획, 상태(대기/진행/완료/차단), 검증결과, 근거] 열을 둔다. 각 항목 완료 시 실시간으로 갱신한다.

### R3. 독립 검증

각 항목 수정 후 독립 검증 스크립트를 `/code/` 내에 작성하고 실행:
- **C-3 검증**: 저밀도에서 T_GenCam=0.1이 유일 최적이 아님 확인
- **C-2 검증**: ResNetMoEDQN 300step 평가 시 action 분포 ≠ {0}
- **H-4 검증**: 모든 hook의 max(p_tx) ≤ 20 assert
- **H-5 검증**: 5단계 에이전트 구조 차이 확인 (파라미터 출력)
- **H-6 검증**: 정규화 상태 → bin 매핑 정합
- **회귀 검증**: 베이스라인(Fixed10Hz/ReactDCC/AdaptDCC) 결과 재현

### R4. TinyMLP 폐기 및 코드 정리

아래 파일들을 `backup/legacy_tinymlp/` 및 `backup/legacy_scripts/`로 이동:
- `train_final.py`, `tinymlp_train.py`, `tinymlp_train_redo3.py`, `tinymlp_train_redo4.py`
- `aggregator.py` (Windows 절대경로)
- `*.bak*` 파일들 → `backup/bak_files/`

`get_hook()`의 `"Proposed"` 분기 → TinyMLP 로딩 제거 (또는 주석처리 후 backup 참조 주석)

### R5. Critic 검토

모든 12개 항목 완료 후 `.rules/critic.md` 기준으로 최종 검토:
- 빈 공간, TODO, pass 확인
- 의도대로 구현되었는지 확인
- 오타, 변수명 오류, 데이터 누수, 논리적 결함 검토

## Acceptance Criteria

### 코드 수정 완전성
- [ ] 12개 항목(C-1~M-12) 전부 '완료(검증 통과)' 또는 '차단(명시 사유+질문)' 상태
- [ ] `idea/paper4_code_fix_tasklist.md`에 12개 ID의 최종 상태·근거·검증결과가 기록됨
- [ ] 체크리스트와 실제 코드가 일치

### 보상 함수 (C-3)
- [ ] 보상이 over-target only + osc + stale + cost 4항으로 구성
- [ ] 모든 DRL hook의 predict에 동일 보상 적용 (grep으로 `abs(cbr_smoothed - 0.6)` 0건)
- [ ] `prev_cbr` dict가 존재하고 reset_episode에서 clear됨
- [ ] 밀도별 CBR_TARGET 측정 스크립트 존재

### 평가 배선 (C-1, C-2)
- [ ] SA1/SA2 methods에 5개 DRL 모델 등록 (grep으로 확인)
- [ ] `"Proposed"` 라벨이 methods 리스트에서 제거됨
- [ ] `setup_eval_hook()` 함수가 존재하고 5개 모델에 대해 agent 생성·로드·주입 수행
- [ ] DRL 평가 시 action 분포가 단일값(0)이 아님 (300step 테스트)

### 액션 그리드 (H-4)
- [ ] `etsi_cam_layer.PTX_GRID_DBM = [-5, 0, 5, 10, 15, 20]`
- [ ] 모든 hook의 p_tx_grid가 이 상수를 import (grep으로 확인)
- [ ] 30dBm 포함 그리드 0건 (grep으로 확인)

### Ablation (H-5)
- [ ] 5단계 에이전트가 각각 정확히 1개 컴포넌트만 추가
- [ ] action_dim=24로 통일

### Tabular (H-6)
- [ ] state_bounds 이웃 축이 (0.0, 1.0)
- [ ] train_step() no-op 메서드 존재

### 경로 (M-9)
- [ ] `/home/imnyj/` 하드코딩 경로가 sim_engine.py에서 환경변수로 대체됨
- [ ] `g:/` 경로 파일이 backup/로 이동됨

### 학습 설정 (M-10)
- [ ] 모든 학습 스크립트의 num_episodes ≥ 500

### 폐기 코드 (R4)
- [ ] TinyMLP 관련 파일이 backup/로 이동됨
- [ ] `get_hook("Proposed")`가 TinyMLP를 로딩하지 않음

### Critic 통과 (R5)
- [ ] critic 검토 완료 보고서 존재

## Follow-up — 2026-08-20T17:34:36+09:00

[추가 지시사항] 
1. 작업 진행 중 API Quota(429 에러) 초과나 토큰 부족 현상이 감지될 경우, 작업을 억지로 진행하지 말고 에이전트를 5시간(18000초) 대기/휴식 상태로 전환한 뒤 자동으로 재개하도록 자체 스케줄링 하세요.
2. 현재 메인 에이전트가 00시, 06시, 12시, 18시에 정기 보고를 수행하도록 설정해두었습니다. 각 시간 직전에 오케스트레이터가 진척 상황을 요약해서 보고해 주면 도움이 됩니다.





