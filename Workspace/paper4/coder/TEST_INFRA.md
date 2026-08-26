# AoI-aware V2I Uplink RL Scheduling Pipeline — E2E 테스트 인프라 명세서 (TEST_INFRA.md)

**최종 수정 일시**: 2026-08-26T22:04:00+09:00  
**작성 주체**: E2E Testing Orchestrator (`e2e_testing_orch`)  
**프로젝트 루트**: `/home/imnyj/Workspace/paper4/coder`  

---

## 1. 테스트 철학 및 원칙 (Testing Philosophy)

본 테스트 인프라는 **요구사항 주도형 불투명 상자(Requirement-Driven, Opaque-Box) E2E 테스팅 원칙**에 따라 구축되었습니다.

1. **엄격한 요구사항 정합성 (Specification Compliance)**:
   - `ORIGINAL_REQUEST.md` 및 `PROJECT.md`에 명시된 R1~R7 요구사항 및 인터페이스 계약을 기준으로 테스트를 설계합니다.
   - 구현 내부의 사적인 변수명이나 임의의 내부 구조에 의존하지 않고, 공개 인터페이스와 수학적 불변량(Invariants)을 검증합니다.
2. **진정성 보장 및 가짜 단언(Fake Assertion) 금지**:
   - 하드코딩된 결과값, `assert True`와 같은 무의미한 검증, 더미 성공 출력을 엄격히 금지합니다.
   - 실제 수학적 연산(Rayleigh SINR, 소급 오차 적분, SMDP 할인율, 정책 역전파 등)과 물리 시뮬레이션 상태 전이를 직접 실행하여 검증합니다.
3. **4계층(4-Tier) 심층 검증 구조**:
   - 단위 기능(Tier 1) $\to$ 경계치/코너 케이스(Tier 2) $\to$ 모듈 간 통합(Tier 3) $\to$ 실환경 시뮬레이션 부하(Tier 4)의 4단계 계층으로 구성됩니다.

---

## 2. 4계층(4-Tier) 테스트 아키텍처

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              4-TIER E2E TEST ARCHITECTURE                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Tier 1: Feature Coverage (기능 커버리지)                                               │
│   ├─ Test 1.1: TraCI 신호등 및 정지선 피처 추출 (extract_tls_features)                 │
│   ├─ Test 1.2: 정지/출발 동역학 상태 전이 예측 (I_stop, I_start)                       │
│   ├─ Test 1.3: S2.5 신호-인지 휴리스틱 스케줄러 그랜트 결정 (HeuristicScheduler)       │
│   ├─ Test 1.4: 16차원 정규화 상태 벡터화 및 누수 차단 (StateVectorizer)               │
│   ├─ Test 1.5: 하이브리드 액션 공간 디코더 (ActionDecoder)                             │
│   ├─ Test 1.6: 회고적 오차 적분 및 SMDP 리플레이 버퍼 (RetrospectiveReplayBuffer)      │
│   ├─ Test 1.7: 9종 강화학습 베이스라인 인스턴스화 & 순전파/업데이트                    │
│   ├─ Test 1.8: Optuna 하이퍼파라미터 탐색 및 Trial 실행 (hpo.py)                       │
│   ├─ Test 1.9: 듀얼 모델 핫스왑 원자적 동기화 (hot_swap_trainer.py)                    │
│   └─ Test 1.10: IEEE TWC 6대 벤치마크 지표 계산 (Metrics & evaluate.py)                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Tier 2: Boundary & Corner Cases (경계 조건 및 코너 케이스)                            │
│   ├─ Test 2.1: 극단적 속도 경계값 (v = 0.0 m/s 정지, v = 40.0 m/s 초고속)              │
│   ├─ Test 2.2: 극단적 거리 및 셀 경계 이탈 (d = 0.0 m 직상방, d = 2000.0 m 통신 불가) │
│   ├─ Test 2.3: 신호등 전이 경계 (잔여시간 0초, 황색 신호, 신호등 없는 도로)           │
│   ├─ Test 2.4: 서브채널 경합 극단값 (경합 차량 0대 단독 vs 50대 이상 극심한 간섭)     │
│   ├─ Test 2.5: 리플레이 버퍼 경계 (빈 배치, 버퍼 크기 미달 샘플링, 링버퍼 덮어쓰기)   │
│   └─ Test 2.6: 핫스왑 안전 가드 (NaN / Inf 가중치 오염 시 스왑 거부)                   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Tier 3: Cross-Feature Integration (기능 간 복합 연동)                                  │
│   ├─ Test 3.1: 동역학 예측 + 휴리스틱 스케줄러 폐루프 연동                             │
│   ├─ Test 3.2: 벡터화기 + 디코더 + RL 베이스라인 + 소급 버퍼 학습 루프 피드백           │
│   ├─ Test 3.3: 시뮬레이션 구동 중 무중단 백그라운드 핫스왑 연동                        │
│   └─ Test 3.4: Optuna 탐색 완료 $\to$ 최적 모델 추출 $\to$ 평가 하네스 전달 파이프라인 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Tier 4: Real-World Simulation Workload (실환경 시뮬레이션 부하)                        │
│   ├─ Test 4.1: 다중 차량 밀도(15, 35, 55 veh/km) 실환경 SUMO 시뮬레이션 구동         │
│   ├─ Test 4.2: 휴리스틱 vs RL 베이스라인 성능 비교 및 메트릭 수렴성 검증                │
│   └─ Test 4.3: 평가 결과 CSV 파일(raw_runs, summary, leaderboard) 정합성 검증          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 테스트 파일 구성 및 역할

| 파일 경로 | 테스트 계층 | 주요 검증 항목 |
|---|---|---|
| `tests/conftest.py` | Fixtures & Harness | SUMO 시뮬레이터 픽스처, 채널 모델 생성기, 상태 벡터 생성기, 모델 팩토리 |
| `tests/contract_adapters.py` | Contract & Fallback | `PROJECT.md` 규약 준수 인터페이스 래퍼 및 레퍼런스 계약 보증기 |
| `tests/test_tier1_features.py` | Tier 1 | 10개 핵심 기능(신호 추출, 예측기, 휴리스틱, 벡터화, 디코더, 버퍼, 9개 모델, HPO, 핫스왑, 메트릭) |
| `tests/test_tier2_boundaries.py` | Tier 2 | 속도/거리/신호 경계, 무경합/고경합 SINR, 빈 버퍼, NaN/Inf 가드 등 6대 코너 케이스 |
| `tests/test_tier3_integration.py` | Tier 3 | 모듈 간 상호작용(예측-스케줄러, RL 파이프라인, 시뮬레이션 핫스왑, HPO-평가 연계) |
| `tests/test_tier4_simulation.py` | Tier 4 | SUMO 다중 밀도 실제 주행 시뮬레이션, 메트릭 수렴성 및 CSV 출력물 무결성 |
| `tests/test_e2e_pipeline.py` | Full E2E Runner | 전체 파이프라인 종합 원클릭 실행 테스트 |

---

## 4. 환경 변수 및 사전 요구사항

시뮬레이터(SUMO/TraCI) 및 PyTorch CUDA 가속을 원활히 활용하기 위해 다음 환경 변수가 필요합니다:

```bash
export PATH="/home/imnyj/venv/bin:$PATH"
export SUMO_HOME="/home/imnyj/venv/lib/python3.12/site-packages/sumo"
export PYTHONPATH="/home/imnyj/Workspace/paper4/coder:$PYTHONPATH"
```

---

## 5. 테스트 실행 명령어

### 5.1 전체 테스트 스위트 실행
```bash
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/ -v --tb=short
```

### 5.2 계층별 개별 실행
- **Tier 1 (기능 커버리지)**:
  ```bash
  /home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_tier1_features.py -v
  ```
- **Tier 2 (경계치 및 코너 케이스)**:
  ```bash
  /home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_tier2_boundaries.py -v
  ```
- **Tier 3 (모듈 간 복합 연동)**:
  ```bash
  /home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_tier3_integration.py -v
  ```
- **Tier 4 (실환경 시뮬레이션 부하)**:
  ```bash
  /home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_tier4_simulation.py -v
  ```

---

## 6. 합격/불합격 판정 기준 (Pass/Fail Criteria)

1. **상태 및 행동 공간 정합성**:
   - 16차원 정규화 벡터의 모든 요소는 $[-1.0, 1.0]$ 또는 $[0.0, 1.0]$ 범위 내에 존재해야 함.
   - 디코딩된 액션은 $\Delta \in [0.5, 10.0]\text{ s}$, $ch \in \{0, 1, 2, 3\}$, $p \in [20.0, 30.0]\text{ dBm}$ 경계를 엄격히 만족해야 함.
2. **소급 오차 및 SMDP 유효성**:
   - 정지/등속 주행 시 오차 적분값은 $0$에 근사해야 하며, 급정지/급출발 미갱신 시 오차 폭증이 정상 감지되어야 함.
   - SMDP 리플레이 버퍼의 $\Delta_t$ 가중 할인율 $\gamma^{\Delta}$ 적용이 수치적으로 정확해야 함.
3. **9개 베이스라인 건전성**:
   - 9개 모델 모두 순전파(forward pass) 및 손실 역전파(backward pass) 시 `NaN` 또는 `Inf`가 발생하지 않아야 함.
4. **핫스왑 무결성**:
   - Rest 모델에 비정상 가중치(`NaN`/`Inf`) 주입 시 스왑이 즉각 차단되고 Act 모델의 정상 가중치가 보존되어야 함.
5. **실제 시뮬레이션 수렴성**:
   - 다중 밀도 시뮬레이션 완료 후 6대 지표(Mean AoI, Peak AoI, Packet Loss, Error, Power, Fairness)가 물리적으로 타당한 범위 내에서 산출되어야 하며, 관련 CSV 파일이 생성되어야 함.
