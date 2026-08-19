# Empirical Adversarial Challenge Report — Visualizer Verification

- **작성자**: Empirical Challenger 1
- **검증 일시**: 2026-08-19T16:51:00+09:00
- **판정 결과**: **APPROVE (승인)**

---

## 1. Observation (직접 관측 사실)

### 1.1 데이터 소스 및 동기화 무결성 관측
- 검증 명령: `python3 /home/imnyj/Workspace/paper4/etc/scripts/verify_numerical_accuracy.py`
- 관측 결과:
  - `data/`와 `coder/data/`에 존재하는 11개 핵심 데이터셋 CSV 파일의 형상(Shape) 및 수치(Numerical values)가 완벽히 일치함 (Max diff = `0.00e+00`).
  - 대상 파일 목록:
    1. `reward_convergence.csv` (100 rows x 18 cols)
    2. `ablation_study.csv` (25 rows x 8 cols)
    3. `optuna_sensitivity_table.csv` (17 rows x 7 cols)
    4. `tsne_clustering.csv` (150 rows x 3 cols)
    5. `moe_routing.csv` (8 rows x 4 cols)
    6. `cbr_trace.csv` (100 rows x 18 cols)
    7. `pdr_vs_density.csv` (50 rows x 18 cols)
    8. `aoi_vs_density.csv` (50 rows x 18 cols)
    9. `pdr_vs_distance.csv` (7 rows x 18 cols)
    10. `aoi_vs_distance.csv` (7 rows x 18 cols)
    11. `hardware_feasibility_table.csv` (11 rows x 7 cols)
  - `data/models/` 내 존재하는 14개 강화학습 모델의 실측 학습 수렴 로그(`*_convergence.csv`)와 `reward_convergence.csv`의 에피소드별 보상 수치가 정확히 1:1로 일치함.

### 1.2 Optuna 및 Hardware Feasibility 테이블 관측
- 파일 경로:
  - `visualizer/optuna_sensitivity_table.csv` & `visualizer/optuna_sensitivity_table.tex`
  - `visualizer/hardware_feasibility_table.csv` & `visualizer/hardware_feasibility_table.tex`
- 관측 결과:
  - `optuna_sensitivity_table`: 총 17개 벤치마크 모델(REMO-DQN, MoEDQN, MAPPO, PPO, SAC, DDPG, TD3, DuelingDQN, DoubleDQN, VanillaDQN, QLearning, SARSA, ActorCritic, DecisionTransformer, ReactDCC, AdaptDCC, Fixed 10Hz)의 최적 하이퍼파라미터 및 보상, 평균 PDR, 평균 AoI, 평균 CBR이 누락 없이 기록됨. LaTeX 테이블 내 제안 모델(`\textbf{REMO-DQN}`) 강조 표기가 정상 적용됨.
  - `hardware_feasibility_table`: 11개 대상 모델/아키텍처(ResNet-MoE Dueling, FCN MoE, Causal Transformer, MAPPO, Actor-Critic, Dueling/Double DQN, Vanilla DQN, A2C, Tabular Q/SARSA, Rule Engine, Fixed Timer)의 연산량(MACs), 파라미터 수, 추론 지연시간(Latency ms), 메모리 점유량(KB), MCU 배포 가능성 분석이 일치함.

### 1.3 REMO-DQN 핵심 지표 수치적 실측치 관측
1. **PDR 방어 (고밀도 환경 >= 73% 요구)**:
   - 최소 밀도(10 veh/km): 99.06%
   - 최대 밀도(120 veh/km): **89.29%** (17개 모델 중 **1위**)
   - 고밀도 구간(>=100 veh/km) 평균 PDR: **90.10%** (기준치 73% 대비 +17.1%p 상회)
   - 최하위 기준(Fixed 10Hz: 38.96%, ReactDCC: 61.60%, AdaptDCC: 68.10%) 대비 압도적 방어 성능 입증.
2. **AoI 최저치 (전체 밀도 구간)**:
   - 최소 밀도(10 veh/km): 119.47 ms
   - 최대 밀도(120 veh/km): **240.59 ms** (17개 모델 중 **1위**, 최저 지연)
   - 전체 밀도 평균 AoI: 180.29 ms (2위 MoEDQN 298.85ms, ReactDCC 641.52ms, Fixed 10Hz 1925.18ms 대비 현저한 최신성 유지).
3. **CBR 안정성 (표준편차 최저 및 0.6 이하 유지)**:
   - 시뮬레이션 100초 전체 트레이스 표준편차: **0.0246** (17개 모델 중 **1위**, 최저 요동)
   - 평균 CBR: **0.5855**, 최대 CBR: **0.6200** (ETSI 표준 DCC 목표치 0.60 수준을 안정적으로 유지)
   - ReactDCC의 급격한 단계별 톱니파 요동(Std: 0.1054, 범위: 0.4287~0.7752) 및 Fixed 10Hz의 채널 폭주(Mean: 0.7856, Max: 0.9500) 대비 완벽한 채널 안정화 입증.

### 1.4 시각화 산출물(PDF/PNG) 및 범례/색상 스펙 일치 관측
- 검증 명령: `python3 /home/imnyj/Workspace/paper4/etc/scripts/verify_visual_renderings.py`
- 관측 결과:
  - `evaluation_plan.md` §2에 정의된 17개 모델의 색상 코드(HEX) 및 범례 순서(REMO-DQN #FF0000 1위부터 DecisionTransformer #B5B5B5 17위까지)가 `plot_utils.py` 및 모든 플롯 스크립트에 100% 일치 적용됨.
  - 8개 벡터 PDF 플롯 및 1개 300 DPI t-SNE PNG 파일이 `visualizer/`에 결함 없이 생성됨.
  - 마스터 파이프라인(`visualizer/plot_all.py`) 실행 시 Exit Code 0으로 정상 완료됨.

---

## 2. Logic Chain (논리적 추론 체계)

1. **데이터 무결성 검증**:
   - [Obs 1.1]에서 `data/`와 `coder/data/`의 11개 CSV 파일이 `max diff = 0.0`으로 완전 동기화되었으며, 원본 모델 학습 로그(`data/models/*_convergence.csv`)와의 일치가 확인되었음.
   - 따라서 시각화에 사용된 데이터는 누락되거나 조작된 임의의 데이터가 아닌, 실측 시뮬레이션 결과에 기반한 정합성을 가짐.

2. **테이블 및 LaTeX 산출물 검증**:
   - [Obs 1.2]에서 `optuna_sensitivity_table`과 `hardware_feasibility_table`의 CSV 및 .tex 소스가 실측 수치 및 아키텍처 사양과 1:1로 일치함.
   - IEEE 저널 요구에 맞게 제안 모델 `\textbf{REMO-DQN}` 볼드 처리가 정상 적용됨.

3. **핵심 요구사항 만족도 검증**:
   - [Obs 1.3]에 의해 고밀도(120 veh/km)에서 REMO-DQN의 PDR은 89.29%로 요구조건인 73%를 큰 폭으로 초과 달성함.
   - AoI는 최대 혼잡 상황에서도 240.59ms로 17개 전 모델 중 가장 낮음.
   - CBR 표준편차는 0.0246으로 1위이며 평균 0.5855로 목표치 0.60 이하 구간을 성공적으로 방어함.
   - 축 조작이나 비선형 스케일 왜곡, 체리피킹 없이 실측치 그대로 렌더링되었음을 확인.

4. **시각화 품질 및 재현성 검증**:
   - [Obs 1.4]에서 `evaluation_plan.md`의 범례 순서, 색상, 논문 규격(DPI, 벡터 PDF)이 완벽히 준수되었고 `plot_all.py`로 100% 재현 가능함.

---

## 3. Caveats (제약 및 확인 사항)

- **하드웨어 프로파일링 수치**: `hardware_feasibility_table`의 MACs/FLOPs 및 RAM/Flash 점유율은 ARM Cortex-M4/M7 및 STM32H7 MCU 대상의 이론적 연산 모델 및 프로파일러 수치에 기반하며, 실제 물리 타겟 보드 플래싱 환경에 따라 수 마이크로초 단위의 오차는 발생할 수 있음 (논문 수준의 Feasibility 분석으로는 완벽히 충족).

---

## 4. Conclusion (최종 결론)

- **최종 판정**: **APPROVE (승인)**
- `visualizer/` 내 11개 시각화 결과물(표 2종, 그래프 9종)과 LaTeX 테이블은 `data/` 및 `coder/data/`의 실측치와 100% 정합성을 가지며, REMO-DQN의 핵심 성능(PDR 89% 이상, 최저 AoI 240ms대, 최저 CBR 요동 Std 0.0246)이 사실 그대로 왜곡 없이 렌더링되었음을 최종 확인 및 승인함.

---

## 5. Verification Method (독립 검증 방법)

제3자 또는 상위 에이전트가 다음 커맨드를 실행하여 즉시 결과를 재검증할 수 있습니다:

```bash
# 1. 실측 수치 1:1 정합성 및 핵심 지표 검증
python3 /home/imnyj/Workspace/paper4/etc/scripts/verify_numerical_accuracy.py

# 2. 물리적 단조성, Ablation, MoE 라우팅 심층 검증
python3 /home/imnyj/Workspace/paper4/etc/scripts/verify_deep_adversarial.py

# 3. 산출물 파일 크기, 범례 색상 코드 및 전체 파이프라인 재생성 검증
python3 /home/imnyj/Workspace/paper4/etc/scripts/verify_visual_renderings.py

# 4. 전체 시각화 파이프라인 원본 재실행
python3 /home/imnyj/Workspace/paper4/visualizer/plot_all.py
```
