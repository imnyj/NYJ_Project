# R3. 평가 계획서 데이터 추출 및 통합 CSV 병합 파이프라인 분석 보고서

**작성일시**: 2026-08-20T23:02:00+09:00  
**담당 에이전트**: `explorer_eval_survey_3`  
**프로젝트 루트**: `/home/imnyj/Workspace/paper4`  
**분석 대상**: `visualizer/evaluation_plan.md` Item 1 & Item 3, `ORIGINAL_REQUEST.md`, `prompt_draft.md`, 관련 데이터 및 시각화 스크립트

---

## 1. 개요 및 분석 목적

본 조사는 Paper 4 프로젝트의 핵심 요구사항인 **R3 (평가 계획서 1번, 3번 항목 데이터 추출 및 통합 CSV 병합 파이프라인)**의 완벽한 실행을 위한 사전 조사 및 파이프라인 설계 분석입니다.

- **Item 1 (Ablation Study Convergence)**: REMO-DQN 및 5개 구조적 변형 모델과 다중 목적 보상 분해 항들의 200,000 스텝 수렴 데이터를 통합 CSV(`data/ablation_study.csv`)로 병합하는 요구사항과 컬럼 정합성 분석.
- **Item 3 (Comparing Reward Convergence)**: 제안 방안(REMO-DQN) 및 16개 비교 베이스라인(총 17개 모델)의 200,000 스텝 보상 수렴 데이터를 표준 범례 순서에 맞춘 통합 CSV(`data/reward_convergence.csv`)로 병합하는 요구사항 분석.
- **기존 스크립트 호환성 연계**: `code/plot_all_convergence.py`, `code/plot_convergence.py`, `visualizer/prepare_data.py`, `visualizer/plot_figures.py`, `visualizer/generate_visualizations.py` 등 기존 및 신규 시각화 파이프라인과의 완벽한 데이터 정합성 보장 방안 도출.

---

## 2. Item 1 (Ablation Study Convergence) 데이터 추출 분석

### 2.1 대상 모델 및 변형체 정의 (5대 점진적 구조 모델 & 4대 보상 항)

`code/test_h5_ablation.py` 및 `visualizer/evaluation_plan.md` §3.1에 정의된 5단계 점진적 소거 연구 구조 체계는 다음과 같습니다.

| 단계 (Stage) | 모델명 (Model) | 소거 연구 명칭 (Ablation Variant) | 아키텍처 특성 |
| :--- | :--- | :--- | :--- |
| **Stage 5 (Full)** | **REMO-DQN** | Proposed (Full Model) | ResNet Skip Connection + 3-Expert MoE Gating + Dueling Stream + Double DQN |
| **Stage 4** | **MoEDQN** | `w/o ResNet` | 2-Expert MoE Gating + Dueling Stream + Double DQN (ResNet 블록 제거) |
| **Stage 3** | **DuelingDQN** | `w/o MoE` | Pure MLP + Dueling Stream ($V(s) + A(s,a)$) + Double DQN (MoE 제거) |
| **Stage 2** | **DoubleDQN** | `w/o Dueling` | Pure MLP + Single Stream $Q(s,a)$ + Double DQN Target (Dueling 제거) |
| **Stage 1** | **VanillaDQN** | Baseline DQN | Pure MLP + Single Target $y = r + \gamma \max Q_{target}$ (Double DQN 제거) |

또한, 다중 목적 보상 함수(Multi-Objective Reward Formulation)에 대한 소거 연구는 다음과 같이 구성됩니다.
- $R_{\mathrm{full}}$: `REMO-DQN` 전체 보상
- $w/o\ R_1$ (`w/o R1`): 채널 혼잡도(CBR) 페널티 항 제거 ($-1.0 \times |\mathrm{CBR} - 0.60| \times 2000$)
- $w/o\ R_2$ (`w/o R2`): 정보 최신성(AoI) 페널티 항 제거 ($-0.1 \times \mathrm{AoI} \times 2000$)
- $w/o\ R_3$ (`w/o R3`): 통신 에너지 효율 및 송신 안정성 보상 항 제거 ($+5000.0$)

### 2.2 통합 CSV 컬럼 구조 및 스키마 요구사항

`visualizer/prepare_data.py` 및 `visualizer/generate_visualizations.py`와 `prompt_draft.md`를 모두 충족하는 표준 컬럼 구성은 다음과 같습니다.

- **대상 파일 경로**: `/home/imnyj/Workspace/paper4/data/ablation_study.csv` (및 `/home/imnyj/Workspace/paper4/coder/data/ablation_study.csv`)
- **표준 컬럼 헤더**:
  ```csv
  Episode,Global_Step,REMO-DQN,w/o ResNet,w/o MoE,w/o Dueling,w/o R1,w/o R2,w/o R3
  ```
- **호환 확장 컬럼 헤더 (5대 모델명 직관 매핑 포함 시)**:
  ```csv
  Episode,Global_Step,REMO-DQN,w/o ResNet,w/o MoE,w/o Dueling,w/o R1,w/o R2,w/o R3,MoEDQN,DuelingDQN,DoubleDQN,VanillaDQN
  ```

### 2.3 에피소드 및 누적 스텝 정렬 방식

1. **행 수 (Row Count)**: 총 100행 (Episode 1 ~ 100).
2. **에피소드 및 스텝 매핑**:
   - `Episode`: $1, 2, 3, \dots, 100$ (정수, 1씩 증가)
   - `Global_Step`: $2000, 4000, 6000, \dots, 200000$ (에피소드당 2,000 스텝씩 단조 증가)
   - 공식: $\text{Global\_Step} = \text{Episode} \times 2000$
3. **데이터 무결성 기준**:
   - 결측치(NaN, Null, Inf) 0건
   - 120,000 스텝 이전은 수렴 단계(Phase I), 120,000 ~ 200,000 스텝은 안정 단계(Phase II)의 특성을 보장.

---

## 3. Item 3 (Comparing Reward Convergence) 데이터 추출 분석

### 3.1 대상 17개 전체 모델 및 표준 범례 순서

`visualizer/evaluation_plan.md` §2에 규정된 엄격한 17개 비교 베이스라인 정의 및 순서는 다음과 같습니다.

| 순번 | 범례 명칭 (Method Display) | 모델 범주 (Category) | 데이터 소스 (Source File) | 특성 및 고정값 |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **REMO-DQN (Proposed)** | DRL (Proposed) | `data/models/REMO-DQN_convergence.csv` | ResNet+MoE+Dueling, bold, red (#FF0000) |
| **2** | **Fixed 10Hz** | Non-RL Standard | Rule-based Constant | 정상상태 보상 고정값: `-995000.0` |
| **3** | **ReactDCC (ETSI Standard)** | Non-RL Standard | Rule-based Table Lookup | 정상상태 보상 고정값: `-982000.0` |
| **4** | **AdaptDCC (ETSI Standard)** | Non-RL Standard | Gradient Descent Rate Adapt | 정상상태 보상 고정값: `-978000.0` |
| **5** | **MoEDQN** | DRL Baseline | `data/models/MoEDQN_convergence.csv` | MoE + Standard DQN (#9B5DE5) |
| **6** | **MAPPO** | DRL Baseline | `data/models/MAPPO_convergence.csv` | Multi-Agent PPO (#D783FF) |
| **7** | **PPO** | DRL Baseline | `data/models/PPO_convergence.csv` | Proximal Policy Opt (#7A49A5) |
| **8** | **SAC** | DRL Baseline | `data/models/SAC_convergence.csv` | Soft Actor-Critic (#00FF00) |
| **9** | **DDPG** | DRL Baseline | `data/models/DDPG_convergence.csv` | Deep Deterministic PG (#6BCB77) |
| **10** | **TD3** | DRL Baseline | `data/models/TD3_convergence.csv` | Twin Delayed DDPG (#2E8B57) |
| **11** | **DuelingDQN** | DRL Baseline | `data/models/DuelingDQN_convergence.csv` | Dueling DQN (#FF9F1C) |
| **12** | **DoubleDQN** | DRL Baseline | `data/models/DoubleDQN_convergence.csv` | Double DQN (#FFD166) |
| **13** | **VanillaDQN** | DRL Baseline | `data/models/VanillaDQN_convergence.csv` | Standard DQN (#D67229) |
| **14** | **QLearning** | Tabular RL | `data/models/QLearning_convergence.csv` | Tabular Q-Learning (#1A1A1A) |
| **15** | **SARSA** | Tabular RL | `data/models/SARSA_convergence.csv` | On-policy TD (#555555) |
| **16** | **ActorCritic** | DRL Baseline | `data/models/ActorCritic_convergence.csv` | Advantage Actor-Critic (#888888) |
| **17** | **DecisionTransformer** | Offline/Seq RL | `data/models/DecisionTransformer_convergence.csv` | Transformer-based RL (#B5B5B5) |

### 3.2 통합 CSV 컬럼 구조 및 스키마 요구사항

- **대상 파일 경로**: `/home/imnyj/Workspace/paper4/data/reward_convergence.csv` (및 `/home/imnyj/Workspace/paper4/coder/data/reward_convergence.csv`)
- **표준 컬럼 헤더 (총 19개 컬럼)**:
  ```csv
  Episode,Global_Step,REMO-DQN,Fixed 10Hz,ReactDCC,AdaptDCC,MoEDQN,MAPPO,PPO,SAC,DDPG,TD3,DuelingDQN,DoubleDQN,VanillaDQN,QLearning,SARSA,ActorCritic,DecisionTransformer
  ```
- **데이터 형식**:
  - `Episode`: 1 ~ 100 (정수)
  - `Global_Step`: 2000 ~ 200000 (정수, 2,000 단위)
  - 17개 알고리즘 컬럼: 각 에피소드의 누적 보상(Cumulative Episode Reward, float64)

### 3.3 수치 정합성 및 검증 기준 (Integrity Criteria)

1. **1:1 수치 일치 (Zero Error)**: `data/models/<Model>_convergence.csv`의 `Reward` 값과 `data/reward_convergence.csv`의 해당 모델 컬럼 값이 완벽하게 일치해야 함 ($\text{Max Absolute Error} = 0.0$).
2. **비RL 알고리즘 정상 상태 처리**: `Fixed 10Hz`, `ReactDCC`, `AdaptDCC`는 훈련 루프가 없는 규칙 기반 표준이므로 전 100 에피소드에 걸쳐 벤치마크 고정 보상값으로 유지.
3. **결측치 검증**: NaN, Null, 빈 문자열, Inf 등이 일체 없어야 함 (100행 $\times$ 19열 전수 데이터 유효).

---

## 4. 기존 통합 및 시각화 스크립트 연계 분석

### 4.1 기존 스크립트 현황 및 데이터 경로 매핑

| 스크립트 | 입력 파일 경로 | 출력 파일 경로 | 주요 역할 및 특징 |
| :--- | :--- | :--- | :--- |
| `code/plot_all_convergence.py` | `*_train_log.csv` (상대경로) | `../paper/data/plots/fig_all_convergence.png` | 개별 모델 로그 직접 플롯 (레거시) |
| `code/plot_convergence.py` | `train_log.csv` | `data/plots/fig_convergence_loss.png` | TinyMLP 수렴 손실/정확도 플롯 |
| `visualizer/prepare_data.py` | `data/models/*_convergence.csv` | `data/reward_convergence.csv`<br>`data/ablation_study.csv` | 순수 실측 데이터 기반 데이터 동기화 및 11종 타겟 CSV 생성 엔진 |
| `visualizer/plot_figures.py` | `data/reward_convergence.csv`<br>`data/ablation_study.csv` | `visualizer/1_ablation_study.png/pdf`<br>`visualizer/3_reward_convergence.png/pdf` | IEEE 스타일 350 DPI PNG 및 벡터 PDF 렌더링 모듈 |
| `visualizer/generate_visualizations.py` | `data/reward_convergence.csv`<br>`data/ablation_study.csv` | `visualizer/*_*.png/pdf` (13개 파일) | 11대 타겟 일괄 렌더링 및 Phase I/II 음영 처리 |
| `visualizer/plot_all.py` | (파이프라인 오케스트레이터) | 전체 11종 시각화 및 검증 | `prepare_data` $\rightarrow$ `plot_figures` $\rightarrow$ `generate_tables` $\rightarrow$ `verify_outputs` |

### 4.2 병합 파이프라인 설계 및 실행 방안

기존 `visualizer/prepare_data.py`의 `build_reward_convergence()` 및 `build_ablation_study()`를 활용하거나, 독립된 데이터 병합 유틸리티(`code/merge_convergence_data.py`)를 통해 다음 프로세스로 통합을 수행합니다.

```
[각 모델 훈련 로그]
 data/models/REMO-DQN_convergence.csv
 data/models/MoEDQN_convergence.csv
 data/models/MAPPO_convergence.csv
 ... (14개 RL 모델)
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│      통합 데이터 추출 및 정합성 검증 엔진             │
│  (Data Extraction & Harmonization Pipeline)             │
│                                                        │
│  1. Episode (1..100) & Global_Step (2k..200k) 정렬    │
│  2. 14개 RL 알고리즘 Reward 컬럼 1:1 결합 (오차 0.0)   │
│  3. 3개 Non-RL 베이스라인 Steady-state 보상 할당      │
│  4. 소거 연구 구조(4종) 및 보상 분해(4종) 계산        │
│  5. 결측치(NaN/Inf), 단조 증가성, 수렴/안정성 검증     │
└────────────────────────────────────────────────────────┘
                 │
                 ├──▶ data/reward_convergence.csv & coder/data/reward_convergence.csv
                 └──▶ data/ablation_study.csv & coder/data/ablation_study.csv
                                 │
                                 ▼
┌────────────────────────────────────────────────────────┐
│         시각화 및 보고서 생성 파이프라인                │
│  - visualizer/generate_visualizations.py               │
│  - visualizer/plot_figures.py                          │
│  - visualizer/plot_all.py                              │
│  - 350 DPI PNG & Vector PDF (Target 1 & Target 3) 도출 │
└────────────────────────────────────────────────────────┘
```

---

## 5. 결론 및 파이프라인 구축 권고사항

1. **스키마 및 데이터 포맷 확정**:
   - `data/reward_convergence.csv`: 100행 $\times$ 19열 (`Episode,Global_Step` + 17개 베이스라인).
   - `data/ablation_study.csv`: 100행 $\times$ 9열 (`Episode,Global_Step,REMO-DQN,w/o ResNet,w/o MoE,w/o Dueling,w/o R1,w/o R2,w/o R3`).
2. **이중 저장 동기화 (Dual Save)**:
   - `data/` 및 `coder/data/` 양쪽 디렉토리에 동일한 CSV를 저장하여 하위 파이프라인과의 경로 호환성 확보.
3. **무결성 검증 체계 구비**:
   - 병합 후 자동 검증 루틴(Row 수 100개, Global_Step 200,000 도달, NaN 0건, 원본 로그 대비 Absolute Error $\le 10^{-7}$)을 필수로 수행.
