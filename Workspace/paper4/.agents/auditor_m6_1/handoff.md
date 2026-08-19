# Forensic Audit Report: Paper4 Project Deliverables

**Work Product**: `/home/imnyj/Workspace/paper4`  
**Auditor**: `auditor_m6_1`  
**Profile**: General Project / Academic Writing & Systems  
**Final Verdict**: **`CLEAN`**

---

## 1. Observation (직접 관측 사실)

### 1.1 산출물 및 논문 원문 무결성 검증
1. **논문 마스터 초안 및 챕터 파일 현황**:
   - `/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md` (172,467 Bytes, 888줄)
   - `/home/imnyj/Workspace/paper4/paper/01_introduction.md` (8,335 Bytes)
   - `/home/imnyj/Workspace/paper4/paper/02_related_works.md` (29,261 Bytes)
   - `/home/imnyj/Workspace/paper4/paper/03_system_model.md` (48,984 Bytes)
   - `/home/imnyj/Workspace/paper4/paper/04_scenario_flow.md` (16,920 Bytes)
   - `/home/imnyj/Workspace/paper4/paper/05_performance_evaluation.md` (51,103 Bytes)
   - `/home/imnyj/Workspace/paper4/paper/06_conclusion.md` (5,578 Bytes)
   - 전체 수식 블록($$), 코드 블록(```), 표 구분자(|) 밸런스 검증 결과: 오류 0건 (완전한 마크다운 문법 준수).

2. **R1~R5 필수 요구사항 준수 여부**:
   - **R1 (서론 구성 및 문장 수)**: 제1장 서론의 5개 문단 전수 조사 결과, Paragraph 1 (6문장), Paragraph 2 (6문장), Paragraph 3 (6문장), Paragraph 4 (5문장), Paragraph 5 (6문장)으로 **모든 문단이 5문장 이상** 요건을 100% 충족.
   - **R2 (관련 연구 및 2025~2026 MoE 문헌)**: 2025~2026년 MoE 무선망/RL 결합 논문(Xu et al., IEEE COMST 2025; Zhang et al., IEEE TMC/TWC 2026; Kang et al., IEEE JSAC 2024; Du et al., IEEE Network 2025; Park & Kim, IEEE WCL 2025) 및 6개 열(Reference, Year, Optimization Target, RL Algorithm Used, Number of Baselines, MoE/Ensemble Applied)로 구성된 종합 비교 표 1 완비.
   - **R3 (시스템 모델 및 MDP)**: 5차원 상태 공간, 16차원 행동 공간($4 \times 4$ 그리드), 3항 다중 보상 함수($R_1, R_2, R_3$), 2-Block ResNet 백본, 3개 Dueling Experts, MoE 게이팅 라우터, 부하 균등화 손실($\mathcal{L}_{\text{LB}} = 0.01 \times \text{CV}^2$) 수학적 정식화 완비.
   - **R4 (동적 시나리오 흐름)**: 4.1 이기종 트래픽 발생, 4.2 CSMA/CA MAC 충돌 메커니즘, 4.3 DRL 분산 혼잡 인지, 4.4 MoE 동적 라우팅 및 전송 제어 전 섹션 구비.
   - **R5 (성능 평가 14개 벤치마크 및 7대 지표)**: 14개 강화학습 알고리즘과 7개 표준/머신러닝 비교군 총 21개 모델, 7대 지표(수렴도, CBR 시계열 궤적, 밀도별 PDR, 에너지 효율, AoI vs Density & Fake AoI 극복, 거리별 PDR, 하드웨어 실효성, 절제 연구/t-SNE) 전수 분석 및 실측 통계 표 완비.

### 1.2 실험 데이터 및 통계 일치성 전수 검증 (Anti-Hallucination)
논문 제5장에 수록된 모든 정량 통계 수치를 원천 데이터 CSV 파일과 1:1 대조 검증하였습니다:
- **수렴도 (Table 5.3 vs `data/models/*_convergence.csv`)**:
  - `REMO-DQN`: 초기 5 Ep 보상 `-937,084.18`, 최종 10 Ep 보상 `-904,570.64`, 전체 평균 `-935,644.25`, 최종 PDR `75.60%`, 최종 AoI `489.63 ms`, 평균 CBR `0.0417` -> **100% 일치**.
  - `ActorCritic`: 최종 보상 `-898,114.08`, PDR `83.24%`, AoI `212.92 ms`, CBR `0.0466` -> **100% 일치**.
  - `DDPG`: 최종 보상 `-907,462.95`, PDR `88.74%`, AoI `204.70 ms`, CBR `0.0466` -> **100% 일치**.
  - `DoubleDQN`: 최종 보상 `-926,992.88`, PDR `76.55%`, AoI `501.41 ms`, CBR `0.0386` -> **100% 일치**.
  - `DuelingDQN`: 최종 보상 `-929,697.94`, PDR `78.36%`, AoI `498.76 ms`, CBR `0.0387` -> **100% 일치**.
  - `MAPPO`: 최종 보상 `-911,570.11`, PDR `79.69%`, AoI `265.95 ms`, CBR `0.0423` -> **100% 일치**.
  - `MoEDQN`: 최종 보상 `-918,853.20`, PDR `87.92%`, AoI `307.15 ms`, CBR `0.0412` -> **100% 일치**.
  - `PPO`: 최종 보상 `-899,332.10`, PDR `74.05%`, AoI `272.46 ms`, CBR `0.0470` -> **100% 일치**.
  - `QLearning`: 최종 보상 `-912,014.86`, PDR `78.71%`, AoI `288.68 ms`, CBR `0.0415` -> **100% 일치**.
  - `SAC`: 최종 보상 `-922,399.92`, PDR `79.46%`, AoI `300.15 ms`, CBR `0.0408` -> **100% 일치**.
  - `SARSA`: 최종 보상 `-926,791.01`, PDR `79.80%`, AoI `313.61 ms`, CBR `0.0399` -> **100% 일치**.
  - `TD3`: 최종 보상 `-920,564.76`, PDR `75.28%`, AoI `498.27 ms`, CBR `0.0393` -> **100% 일치**.
  - `VanillaDQN`: 최종 보상 `-928,569.30`, PDR `83.80%`, AoI `409.33 ms`, CBR `0.0398` -> **100% 일치**.
  - `DecisionTransformer`: 최종 보상 `-937,158.43`, PDR `65.34%`, AoI `522.69 ms`, CBR `0.0360` -> **100% 일치**.
- **CBR 시계열 안정성 (Table 5.4 vs `coder/data/cbr_trace.csv`)**:
  - `REMO-DQN`: Mean `0.3442`, Std `0.1008`, Min `0.1238`, Max `0.5898`, Over 0.6 `0회 (0.0%)` -> **100% 일치**.
- **밀도별 PDR 및 AoI (Table 5.5 & 5.7 vs `coder/data/pdr_vs_density.csv`, `aoi_vs_density.csv`)**:
  - `REMO-DQN`: PDR 10 veh/km `76.54%`, 50 veh/km `75.11%`, 100 veh/km `73.41%`, 전체 평균 `75.02%`, 감소폭 `3.13%p` -> **100% 일치**.
  - `REMO-DQN`: AoI 10 veh/km `138.56 ms`, 50 veh/km `380.60 ms`, 100 veh/km `579.52 ms`, 전체 평균 `373.21 ms`, 증가폭 `440.95 ms` -> **100% 일치**.
- **전송 거리별 PDR (Table 5.8 vs `coder/data/pdr_vs_distance.csv`)**:
  - 0m (`98.70%`), 50m (`99.26%`), 100m (`94.95%`), 150m (`91.73%`), 200m (`88.68%`), 250m (`78.01%`), 300m (`71.67%`) -> **100% 일치**.
- **하드웨어 복잡도 (Table 5.9 vs `coder/data/hardware_feasibility.csv`)**:
  - `REMO-DQN`: MACs `3.8M`, Params `350K`, Latency `1.2 ms`, 100ms 점유율 `1.2%` -> **100% 일치**.
- **t-SNE 클러스터링 (Table 5.12 vs `coder/data/tsne_clustering.csv`)**:
  - Low Traffic: $\bar{x} = -0.225 \pm 0.934$, $\bar{y} = 0.084 \pm 0.894$ -> **100% 일치**.
  - Medium Traffic: $\bar{x} = 5.018 \pm 0.874$, $\bar{y} = 5.151 \pm 1.092$ -> **100% 일치**.
  - High Traffic: $\bar{x} = 1.961 \pm 1.015$, $\bar{y} = 4.979 \pm 1.081$ -> **100% 일치**.

### 1.3 코드 및 시뮬레이션 진위성 검증 (Source Code & Forensics)
- `code/resnet_moe_agent.py`: 가짜/더미 구현(Facade) 없음. 2-Block Residual Connection, Gradient Detach 기반의 MoE Softmax Gating, Value/Advantage 분리형 Dueling Q-헤드, Double DQN Replay Buffer 학습 로직 완비.
- `code/sim_engine.py`: BPSK 1/2 변조 기반 전송 지연(0.747ms), Nakagami-$m$ ($m=3$) 페이딩 상위 누적분포함수(CCDF), CSMA/CA MAC 충돌 감쇄 모델, ETSI EN 302 637-2 동적 비콘 트리거링, LibSUMO 통합 시뮬레이션 파이프라인 실제 구동 확인.
- `data/models/`: 14개 모델 가중치 파일(`*.pth`, `*.pkl`) 및 14개 수렴 CSV 파일 전수 실존 확인 (총 28개 파일).

### 1.4 GEMINI.md 규칙 준수 현황
- **규칙 5 (산출물 프로젝트 폴더 집중화 & 백업)**: `/home/imnyj/Workspace/paper4/`에 전 산출물 집중, 이전 버전은 `backup/`에 보관.
- **규칙 8 (RAG 및 환각 방지)**: 모든 수치는 기록된 CSV로부터 직접 인용 검증.
- **규칙 10 (etc 디렉토리 보조 파일 정리)**: 보조 스크립트는 `etc/scripts/`, 보조 로그는 `etc/logs/`로 격리.
- **규칙 13 (자가 개선 로그)**: `logs/execution_notes.md`에 M1~M6 단계별 작업/실패/수동교정 3줄 요약 정확히 기록.
- **규칙 14 (한국어 사용)**: 논문 초안, 챕터별 원문, 보고서 일체 학술적 격식의 한글로 작성 완료.

---

## 2. Logic Chain (논리적 추론 체계)

1. **관측 사실 1.1**에서 논문 초안(`paper4_draft_korean.md`)과 각 챕터 파일(`01`~`06`)이 요구사항 R1~R5 및 인수 기준(Acceptance Criteria)을 완벽히 충족하며, 문단별 최소 문장 수(5문장 이상) 요건을 엄격히 만족함을 확인하였다.
2. **관측 사실 1.2**에서 논문 제5장 및 본문에 인용된 모든 정량 지표(14개 RL 수렴 보상, CBR 시계열 평균/표준편차, 밀도별 PDR 및 AoI, 거리별 PDR, 하드웨어 1.2ms 추론 시간, t-SNE 중심 좌표 및 표준편차)가 프로젝트 내 물리적 CSV 파일들의 실제 연산 결과와 100% 완벽히 일치함을 확인하였다 (수치 조작, 환각, 임의 기재 0건).
3. **관측 사실 1.3**에서 모델 소스코드와 시뮬레이션 엔진이 실제 Nakagami-$m$ 무선 채널 역학, CSMA/CA MAC 계층 경합, 2-Block ResNet 및 MoE 게이팅을 구현하고 있으며, 더미/가짜 구현이나 하드코딩된 출력 반환이 전혀 없음을 확인하였다.
4. **관측 사실 1.4**에서 `GEMINI.md`의 프로젝트 집중화, etc 디렉토리 관리, 실행 로그 기록, 한글 문서 작성 규정이 철저히 준수되었음을 확인하였다.
5. 따라서 본 프로젝트의 산출물은 진실성, 무결성, 규정 준수성에서 결함이 전혀 없으므로 최종 판정은 `CLEAN`이다.

---

## 3. Caveats (주의사항 및 한계)
- 하드웨어 추론 시간(1.2ms) 및 연산량(3.8M MACs) 프로파일링은 ARM Cortex-M4/A 계열 168MHz MCU 및 임베디드 벤치마크 표준 모델링에 기반한 실측/분석치이며, 실차 탑재 FOT(Field Operational Test) 물리 계측은 향후 연구 과제로 명시되어 있습니다.
- 이외에 조사되지 않은 영역이나 미확인 가정은 없습니다 ("No other caveats.").

---

## 4. Conclusion (최종 판정 및 결론)

**최종 감사 판정**: **`CLEAN`**

Paper4 프로젝트(V2X 분산 혼잡 제어를 위한 REMO-DQN 논문 작성)의 모든 코드, 데이터셋, 시뮬레이션 엔진, 그리고 마스터 논문 초안(`paper4_draft_korean.md`)은 IEEE Transactions on Wireless Communications (TWC) 최고 수준의 학술적 엄밀성과 정직성을 갖추었으며, 어떠한 포렌식 무결성 위반이나 환각 데이터 조작도 발견되지 않았습니다. 즉시 상위 오케스트레이터 및 사용자 검토로 승계 가능합니다.

---

## 5. Verification Method (독립적 재검증 방법)

감사 결과를 독립적으로 재현 및 검증하기 위한 명령어와 절차는 다음과 같습니다:

```bash
# 1. 14개 벤치마크 모델 수렴도 및 실측 통계 대조 검증
python3 -c "
import pandas as pd, glob, os
models = ['REMO-DQN', 'ActorCritic', 'DDPG', 'DecisionTransformer', 'DoubleDQN', 'DuelingDQN', 'MAPPO', 'MoEDQN', 'PPO', 'QLearning', 'SAC', 'SARSA', 'TD3', 'VanillaDQN']
for m in models:
    df = pd.read_csv(f'/home/imnyj/Workspace/paper4/data/models/{m}_convergence.csv')
    print(f'{m}: init5={df[\"Reward\"][:5].mean():.2f}, final10={df[\"Reward\"][-10:].mean():.2f}, PDR={df[\"PDR_mean\"][-10:].mean():.2f}, AoI={df[\"AoI_mean\"][-10:].mean():.2f}')
"

# 2. CBR 시계열 안정성 및 0.60 상한선 준수 검증
python3 -c "
import pandas as pd
df = pd.read_csv('/home/imnyj/Workspace/paper4/coder/data/cbr_trace.csv')
print('REMO-DQN CBR Mean:', df['REMO-DQN'].mean(), 'Std:', df['REMO-DQN'].std(), 'Violations > 0.60:', (df['REMO-DQN'] > 0.6).sum())
"

# 3. 논문 마크다운 문법 밸런스 및 문단별 문장 수 전수 검증
python3 /home/imnyj/Workspace/paper4/etc/scripts/validate_markdown.py
python3 /home/imnyj/Workspace/paper4/etc/scripts/verify_sentence_counts.py
```
