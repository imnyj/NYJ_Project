# Experimenter Agent Memory Log

## [2026-04-29] [Stage 1: design] — 실험 설계 완료

### 작업 요약
- **대상 논문**: AoI-Guaranteed Robust ILP Precaching in CIoV
- **타겟 저널**: IEEE Internet of Things Journal
- **입력 문서**: idea_spec.md (24,934자, C1~C4 Contribution Frame)
- **출력 파일**: workspace/paper/experiment/experiment_spec.json (33,373자)

---

### 설계 근거

#### 시나리오 설계 원칙
- **Scenario A (소규모 ILP, density 1~5)**: RILP 정확해를 실제로 풀 수 있는 규모(≤5 vehicles/cell)에서 C1 정식화 유효성과 C3 AoI-SLA Theorem을 검증. NP-hard임에도 소규모 가능성을 활용하여 베이스라인과 공정한 최적해 비교 가능.
- **Scenario B (대규모 Greedy, density 6~20)**: RILP가 time limit 초과하는 NP-hard 현실 구현. C2 Greedy 근사비 (1-1/e)의 실증 근거 및 scalability 확인. 베이스라인 대비 Greedy 우위 검증.
- **Scenario C (예측오차 sweep, 0~30%)**: C2/C3 핵심 주장인 "baseline AoI 폭발, RILP AoI 안정"을 가장 직접적으로 보이는 실험. idea_spec.md beat 3(AoI blowup 3배 증가)를 수치로 입증.
- **Scenario D (τ_max sweep, 3~10 slots)**: C3 AoI-SLA Theorem의 sensitivity 분석. τ_max가 네트워크 파라미터(LET 분포, Δ_max)와 함께 Γ*를 결정하는 관계 확인.
- **Scenario E (Γ sweep, 0~5)**: C3 Corollary 1(단조성) + Corollary 2(Γ=0 복원) 수치 검증의 가장 직접적인 실험. Γ* 임계값 실험적 도출 및 해석적 공식(Γ* = (τ_max - f_min)/Δ_max)과 비교.

#### 알고리즘 선택 근거
- **RILP**: C1의 주 제안. PuLP/CBC 또는 Gurobi. Bertsimas-Sim dual counterpart로 반무한 robust 제약을 유한 LP로 변환. density 5 이하에서만 exact 실행.
- **RILP-Greedy**: C2의 주 제안. O(|V||C|log|V||C|) 복잡도. LET_robust × pop × AoI urgency priority. 모든 시나리오에 적용 가능(확장성).
- **Nam2023b**: 선형 lineage의 핵심 베이스라인. Set Ranking(deterministic LET). Γ=0시 RILP와 동일 결과 예상(Corollary 2 검증용).
- **Nam2025**: 직접 선행 연구(IEEE IoT-J). Storage-aware deterministic ILP. 동일 저널 직전 논문으로 비교 필수.
- **Youn2026**: 시스템 모델 소스(5x5 RSU, outage 800m). V2V 릴레이 deterministic ILP. 릴레이 구조 비교.
- **V2I-Base (알고리즘 7)**: 기존 코드베이스 직접 활용. PCO 정규화 기준(denominator).
- **V2V-Base (알고리즘 8)**: 기존 코드베이스 직접 활용. Youn2026 코드의 un-optimized 버전.
- **Random-K**: sanity check. K를 RILP 평균 선택 수로 맞춰 공정 비교.

#### 지표 선택 근거
- **CHR**: 프리캐싱 효과성의 표준 지표. IEEE IoT-J 리뷰어 기대 충족.
- **CDSR**: 불확실성 하 전송 완료율. C3 검증의 2차 지표(AoI violation의 원인 분석).
- **AoI violation rate**: C3 AoI-SLA Theorem의 직접 검증 지표. worst-case AoI > τ_max 비율. 10회 실험 중 최대값(worst-case)과 평균값 모두 기록.
- **PCO**: Robustness 비용(cost of robustness). RILP가 deterministic보다 PCO가 높을 것으로 예상 — 이를 IEEE IoT-J 리뷰어에게 투명하게 제시.
- **RLBI**: Jain's fairness index. V2V 릴레이 부하 분산. 단일 차량에 릴레이 부하 집중 방지 확인.

#### 시뮬레이션 파라미터 선택 근거
- RSU 5x5, comm_range 800m, outage 800m: idea_spec.md Section 4.1 및 Youn2026 시스템 모델 직접 계승
- duration_steps: Scenario A 1800s (소규모 빠른 수렴), Scenario B~E 3600s (대규모 충분한 통계)
- warmup_steps: 차량 밀도 안정화를 위한 burn-in (A: 300s, B~E: 600s)
- 10회 반복: 95% CI 산출 가능 최소 샘플 수. seed 42~51 고정으로 재현성 확보
- Zipf(s=0.8): vehicular content 표준 popularity 모델

#### 예상 주요 결과
1. Scenario A/C: RILP AoI violation rate ≈ 0% (Γ≤Γ*) vs. 베이스라인 15~30% at ε_max=20%
2. Scenario B: Greedy solve time < 5ms/window; RILP ≥ 300s time limit at density≥6
3. Scenario E: Γ vs. AoI violation rate 단조 증가 곡선 확인; Γ* 수치 도출

#### 총 예상 실행 수
- A: 1,600 runs
- B: 1,680 runs
- C: 1,120 runs
- D: 420 runs
- E: 3,520 runs
- **합계: 8,340 runs** (병렬 실행 권장)

---

### 생성된 파일
- `/home/imnyj/paper-ai.v1/workspace/paper/experiment/experiment_spec.json` (33,373자)
  - scenarios: A, B, C, D, E (5개)
  - algorithms: RILP, RILP-Greedy (proposed 2개) + 6개 baseline
  - metrics: CHR, CDSR, AoI_violation_rate, PCO, RLBI (5개, 수식 포함)
  - output_files: 26개 CSV 파일명 명시
  - implementation_notes: PuLP/CBC 기반 RILP 구현 가이드, Greedy 모듈 구조

### 다음 단계
- Stage 2 (implement): experiment_spec.json을 기반으로 libsumo 시뮬레이션 코드 구현
  - 신규 파일: rilp_solver.py, greedy_precaching.py, aoi_tracker.py
  - 기반 파일: 8.V2V_Precaching.py (SumoNetSim1.1.6, 90% 재사용)
