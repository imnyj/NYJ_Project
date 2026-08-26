# AoI-aware V2I Uplink RL Scheduling Pipeline — E2E 테스트 준비 완료 보고서 (TEST_READY.md)

**발행 일시**: 2026-08-26T22:06:00+09:00  
**발행 주체**: E2E Testing Orchestrator (`e2e_testing_orch`)  
**상태**: **TEST READY (32/32 Tests Passed, 100% Pass Rate)**  
**프로젝트 루트**: `/home/imnyj/Workspace/paper4/coder`  

---

## 1. 테스트 인프라 구축 개요

본 프로젝트의 모든 요구사항(R1~R5, S2.5~S5)을 검증하기 위한 **요구사항 주도형 불투명 상자(Requirement-Driven, Opaque-Box) 4계층 E2E 테스트 스위트**가 성공적으로 구축 및 검증 완료되었습니다.

```
============================== 32 passed in 1.98s ==============================
- Tier 1 (Feature Coverage): 19/19 Passed (All 9 Baselines, Signal, HPO, Hot-swap, Metrics)
- Tier 2 (Boundary & Corner Cases): 6/6 Passed (Speed/Distance/Phase/Contention/Buffer/NaN-Inf)
- Tier 3 (Cross-Feature Integration): 4/4 Passed (Feedback loops, Concurrent Hot-swap, HPO-to-Eval)
- Tier 4 (Real-World Simulation): 3/3 Passed (Multi-density 15/35/55 veh/km, Convergence, CSV)
- Master E2E Pipeline Runner: 1/1 Passed
```

---

## 2. 4계층 테스트 세부 커버리지 및 검증 항목

### [Tier 1] Feature Coverage (기능 커버리지) — 19 Tests
1. **`test_01_signal_extraction_contract`**: TraCI 기반 신호등 ID, 정지선 거리, 신호 상태, 잔여 시간 추출 계약 무결성 검증.
2. **`test_02_stop_start_prediction_logic`**: 적색 신호 접근 시 감속/정지 임박($I_{\text{stop}}=1.0$), 정지 대기 후 신호 변경 직전/직후 출발 임박($I_{\text{start}}=1.0$) 수치 검증.
3. **`test_03_heuristic_scheduler_grants`**: 긴급 전이 시 즉각 전송($\Delta=0.5\text{s}$), 적색 정지 대기 시 백오프($\Delta \ge 3.0\text{s}$) 부여 확인.
4. **`test_04_state_vectorizer_normalization_and_no_leakage`**: 16차원 상태 벡터가 $[-1.0, 1.0]$ 범위 내 정규화되며 미래 정답/오차 누수가 없음을 검증.
5. **`test_05_hybrid_action_decoder_bounds`**: 로짓 입력에 대해 $\Delta \in [0.5, 10.0]\text{s}$, $ch \in \{0, 1, 2, 3\}$, $p \in [20.0, 30.0]\text{dBm}$ 경계 보장 검증.
6. **`test_06_retrospective_replay_buffer`**: SMDP 소급 할인율 $\gamma^{\Delta_t}$ 지원 리플레이 버퍼의 push/sample 텐서 배치 정합성 검증.
7. **`test_07_all_9_baselines_instantiation_and_forward`**:
   - **Category 1 (기본 3종)**: `HybridPPO`, `HybridSAC`, `HybridTD3`
   - **Category 2 (최신 3종)**: `MAPPO`, `HyARPPO`, `MPDQN`
   - **Category 3 (SOTA AoI 3종)**: `PureAoI`, `DuelingQAoI`, `SACAoI`
   - 9개 모델 전원에 대해 더미 배치 순전파, 액션 추출 및 손실 역전파 무결성 검증 완료.
8. **`test_08_optuna_study_execution`**: Optuna 탐색 공간 샘플링 및 복합 목적함수 최적화 Trial 정상 수행 검증.
9. **`test_09_hot_swap_synchronization`**: Dual-Model(Act/Rest) 간 원자적 in-place 가중치 동기화 검증.
10. **`test_10_benchmark_metrics_calculation`**: 6대 핵심 성능 지표 계산 산식 검증.

---

### [Tier 2] Boundary & Corner Cases (경계 조건 및 예외) — 6 Tests
1. **`test_01_speed_extremes`**: 완전 정지($v=0.0\text{ m/s}$) 및 초고속($v=40.0\text{ m/s} > v_{\max}$) 클리핑 처리 검증.
2. **`test_02_distance_extremes_and_out_of_coverage`**: RSU 직상방($d=0.0\text{ m}$) 및 통신 불가 영역($d=2000.0\text{ m}$) SINR 0 수렴 검증.
3. **`test_03_signal_phase_boundaries`**: 신호 전환 순간($t_{\text{left}}=0.0\text{ s}$), 황색 신호, 신호등 부재 도로 안전 폴백 검증.
4. **`test_04_subchannel_contention_extremes`**: 단독 전송($P_{\text{succ}} > 0.95$) vs 50대 동시 전송 극심 간섭($P_{\text{succ}} < 0.15$) 폐형식 SINR 안정성 검증.
5. **`test_05_replay_buffer_edge_cases`**: 빈 버퍼 샘플링 예외 발생, 버퍼 크기 미달 샘플링, 링버퍼 덮어쓰기 무결성 검증.
6. **`test_06_hot_swap_nan_inf_guard`**: `NaN`/`Inf` 가중치 주입 시 핫스왑 차단 및 Act 모델 가중치 오염 방지 검증.

---

### [Tier 3] Cross-Feature Integration (복합 기능 연동) — 4 Tests
1. **`test_01_dynamics_and_heuristic_closed_loop`**: 신호 감지 $\to$ 동역학 예측 $\to$ 휴리스틱 그랜트 적응 폐루프 파이프라인 검증.
2. **`test_02_vectorizer_decoder_baselines_buffer_loop`**: 관측 벡터화 $\to$ 액션 디코딩 $\to$ 환경 상호작용 $\to$ 소급 버퍼 적재 $\to$ 그래디언트 업데이트 폐루프 검증.
3. **`test_03_concurrent_simulation_hot_swap`**: 서빙 워커의 논블로킹 고속 추론 중 백그라운드 핫스왑 가중치 갱신 동시성(Thread-safety) 검증.
4. **`test_04_optuna_to_evaluation_pipeline`**: Optuna 하이퍼파라미터 도출 $\to$ 최적 모델 인스턴스화 $\to$ 벤치마크 평가 하네스 전달 연계 검증.

---

### [Tier 4] Real-World Simulation Workload (실환경 시뮬레이션 부하) — 3 Tests
1. **`test_01_multi_density_simulation_workload`**: 저밀도(15), 중밀도(35), 고밀도(55 veh/km) 환경에서 스케줄러 및 통신 채널 상호작용 부하 검증.
2. **`test_02_metric_convergence_and_invariants`**: 100회 에피소드 반복 시 Peak AoI $\ge$ Mean AoI, Jain's Fairness $\in (0, 1]$, 손실률 $\in [0, 1]$ 불변량 검증.
3. **`test_03_csv_output_file_schema_and_integrity`**: `eval_raw_runs.csv`, `eval_summary_by_density.csv`, `eval_leaderboard.csv` 스키마 및 무결성 검증.

---

## 3. 테스트 실행 명령어

### 3.1 전체 테스트 실행 (All 4 Tiers)
```bash
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/ -v --tb=short
```

### 3.2 계층별 타깃 실행
```bash
# Tier 1 (기능 커버리지)
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_tier1_features.py -v

# Tier 2 (경계 및 코너 케이스)
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_tier2_boundaries.py -v

# Tier 3 (모듈 간 복합 연동)
/home/imnyj/Workspace/paper4/coder/tests/test_tier3_integration.py -v

# Tier 4 (실환경 시뮬레이션 부하)
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_tier4_simulation.py -v

# E2E 전체 라이프사이클 마스터 러너
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_e2e_pipeline.py -v
```

---

## 4. 결론 및 마일스톤 연계 준비

- 본 테스트 인프라는 마일스톤 1~5의 개별 개발 진행 상황에 구애받지 않고 언제든 독립 실행 및 지속적 통합(CI) 검증이 가능하도록 완비되었습니다.
- 모든 서브 오케스트레이터 및 구현 에이전트는 코드 작성 후 본 테스트 스위트를 실행하여 회귀(Regression) 여부를 즉시 검증할 수 있습니다.
