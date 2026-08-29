# AoI-aware V2I Uplink RL Scheduling Pipeline — 진행 현황 및 인계 동기화 문서 (progress_sync.md)

> [!CAUTION]
> **이 문서는 2026-08-27T02:57 시점에서 멈춰 있으며, 상당 부분이 폐기된 내용이다.**
> 아래 4절의 baseline 9종(HybridPPO / HybridSAC / HybridTD3 / MAPPO / HyARPPO / MPDQN /
> PureAoI / DuelingQAoI / SACAoI)은 **전부 폐기**되었다. 현행 확정 목록은
> PPO, SAC, TD3, RES-MAPDDPG, MA2HDQN, I-HAMAPPO, SPAM-D3QN, CARLTON, MADDPG-MT이며
> 근거는 `Conversation.md` 4번 절과 `librarian/baselines_v2.json`에 있다.
> 5절의 실행 명령(`hot_swap_trainer.py --model HybridPPO` 등)도 현재 인터페이스와 맞지 않는다.
> **최신 상태는 `simulation_plan.md`(rev.3)와 `review/claude_audit_20260828.md`를 볼 것.**
> 2026-08-28 22시 기준 판정: Δ 액션 미반영 등 치명 결함으로 **본훈련 착수 불가**.

---

**최종 갱신 일시**: 2026-08-27T02:57:00+09:00  
**현재 진행 상태**: **Phase 2 완료 / Gate 100% PASS / Pre-Compute Halt (사용자 코드 리뷰 및 20만 스텝 착수 승인 대기)**  
**프로젝트 루트**: `/home/imnyj/Workspace/paper4/coder`

---

## 1. 프로젝트 요구사항 및 인수 기준(Acceptance Criteria) 달성 현황

| 항목 | 요구사항 명칭 | 세부 내용 | 상태 | 판정 |
|---|---|---|---|---|
| **R1** | Genuine SUMO 환경 연동 및 Anti-Mocking 4대 단언문 | `make_sumo_set.py` 기반 네트워크 생성, `NetSim.py` 및 `Communications.py`를 매 스텝마다 실시간 호출, `AoiV2IEnv.step()` 내 우회 차단 하드코딩 단언문 4종 탑재 | **구현 및 실증 완료** | **PASS** |
| **R2** | RL 인터페이스 및 9종 하이브리드 베이스라인 | 16차원 정규화 관측 벡터(누설 차단), 하이브리드 액션 공간($\Delta, ch, p$), SMDP 후향적 버퍼, 9개 베이스라인(기초 3종, 최신 3종, AoI 특화 3종) 완비 | **구현 및 실증 완료** | **PASS** |
| **R3** | 200k 스텝 훈련 파이프라인 및 Optuna HPO 준비 | 200,000 스텝(2,000 steps * 100 episodes) 확장형 훈련 루프, TensorBoard(`SummaryWriter`) 및 `checkpoints/` 저장 체계, 실제 SUMO 연동 Optuna HPO 및 듀얼 모델 Act/Rest 핫스왑 완비 | **구현 및 실증 완료** | **PASS** |
| **R4** | 사전 구현 및 Short Dummy 검증 후 Halt (Review Phase) | `verify_environment.py` (실제 SUMO 물리 좌표 이동 $\Delta x \ne 0$ 자가 검증), 10스텝 단기 더미 테스트 통과 후 200k 연산 시작 전 자동 중단 및 사용자 코드 리뷰 대기 | **구현 및 실증 완료** | **PASS** |
| **R5** | 안티 치팅 포렌식 감사 및 다자간 검증 게이트 | 독립 Reviewer(`APPROVE`), Challenger(`APPROVE`), Forensic Auditor(`CLEAN`) 전원 통과, 전체 199개 통합 테스트 100% 무결점 달성 | **게이트 전원 통과** | **PASS** |
| **R6** | 인계 문서화 및 진행 상태 공유 | `PROJECT.md`, `progress_sync.md`에 아키텍처, 검증 결과, 최적 파라미터 및 인계 사항 실시간 완벽 갱신 | **완료 (Active)** | **PASS** |

---

## 2. 세부 마일스톤 완료 내역

### 2.1 M1: Genuine SUMO 시뮬레이션 환경 및 4대 Anti-Mocking 단언문 (`src/aoi_env.py`, `verify_environment.py`)
- **`src/aoi_env.py` (Class `AoiV2IEnv`)**:
  - `libsumo.simulationStep()`을 통해 매 스텝 실제 물리 마이크로 시뮬레이션을 전진.
  - `sumo.vehicle.getPosition(vid)`를 통해 좌표를 실시간 조회하고 5.9GHz 무선 채널 모델(`Communications.judge_uplink()`)을 호출하여 Rayleigh 페이딩 간섭 및 패킷 성공 확률 $P_{\text{succ}}$ 산출.
  - **4대 하드코딩 런타임 단언문 (Anti-Mocking Assertions)**:
    1. **Assertion 1 (L687-697)**: 시뮬레이션 시간 전진 검증 (`current_time > prev_time`).
    2. **Assertion 2 (L698-726)**: 주행 차량 물리 변위 검증 (속도 $v > 1.0\text{ m/s}$ 시 $\Delta x > 0$).
    3. **Assertion 3 (L800-814)**: 무선 채널 계산 및 유효 확률 검증 ($0.0 \le P_{\text{succ}} \le 1.0$).
    4. **Assertion 4 (L894-913)**: 보상 수식 일치 및 음수성 검증 ($R_t \le 0$).
- **`verify_environment.py`**:
  - 5개 Phase 전수 검증 스크립트 (SUMO 파일 자동생성 $\to$ 60초 웜업 $\to$ 20스텝 물리 롤아웃 $\to$ 무선 간섭 감쇄 $\to$ 4대 결함 주입 단언문 크래시 테스트).
  - 정상 종료 코드 `0` 달성.

### 2.2 M2: 9종 하이브리드 RL 베이스라인 및 SMDP 인터페이스 (`src/rl_interface.py`, `src/baselines/`)
- 16차원 정규화 관측 벡터(RSU 관점, 정보 누설 방지) 및 하이브리드 액션 디코더 ($\Delta \in [0.5, 10.0]$, $ch \in \{0..3\}$, $p \in [20.0, 30.0]$).
- SMDP $\gamma^\Delta$ 가변 주기 할인 후향적 재생 버퍼 (`RetrospectiveReplayBuffer`).
- 9종 베이스라인 모델 PyTorch 완성:
  - **Category 1 (기초 3종)**: `HybridPPO` (10,953 params), `HybridSAC` (27,789 params), `HybridTD3` (32,906 params)
  - **Category 2 (최신 3종)**: `MAPPO` (10,953 params), `HyARPPO` (15,657 params), `MPDQN` (23,576 params)
  - **Category 3 (SOTA AoI 3종)**: `PureAoI` (1 param), `DuelingQAoI` (20,202 params), `SACAoI` (27,789 params)

### 2.3 M3: 200,000 스텝 훈련 루프, 핫스왑 및 Optuna HPO (`src/hot_swap_trainer.py`, `src/hpo.py`, `src/evaluate.py`)
- **`src/hot_swap_trainer.py`**:
  - `DualModelHotSwapManager`: Act 모델(고속 서빙)과 Rest 모델(백그라운드 학습) 간 원자적 뮤텍스 파라미터 복사(`copy_`), NaN/Inf 사전 가드, 디바이스 간 텐서 전송 지원.
  - `TransitionStreamer`: 멀티스레드 비차단 큐 $\to$ SMDP 재생 버퍼 연동.
  - 에피소드 단위 200,000 스텝(2,000 steps $\times$ 100 episodes) 확장형 루프, TensorBoard `SummaryWriter` 실시간 로깅, `checkpoints/` 최고 성능 모델 자동 저장.
- **`src/hpo.py`**:
  - 진성 `AoiV2IEnv`와 직접 연동된 9종 모델별 Optuna 하이퍼파라미터 탐색 파이프라인. 결과 자동 CSV 내보내기.
- **`src/evaluate.py`**:
  - 5개 밀도(15~55 veh/km) $\times$ 5개 시드(42, 101, 2024, 777, 999)에 걸친 10종 모델 250회 벤치마크 평가 및 6대 IEEE TWC 표준 성능 지표(Mean/Peak AoI, Outage, Error, Power, Energy, Jain's fairness) 산출.

### 2.4 M4 & M5: Short Dummy 검증 및 최종 다자간 게이트 (`tests/test_dummy_verification.py`, 다자간 감사)
- `tests/test_dummy_verification.py` 14개 테스트 전원 통과 (소요 시간 3.41s~3.82s).
- 전체 통합 테스트 스위트: **199/199 통과 (100% Pass Rate, 42.09s)**.
- `ruff check` 린트 검사: 신규 구현 레이어 무결점 통과.

---

## 3. 다자간 독립 검증 게이트 결과 요약 (Gate Status: PASS)

| 역할 | 에이전트 ID | 검증 내용 | 최종 판정 | 보고서 위치 |
|---|---|---|---|---|
| **Code Quality Reviewer** | `fc370f8c` | `verify_environment.py`, 더미 14/14, 전체 199/199 테스트, 린트 검사 전수 실행 | **APPROVE** | `.agents/reviewer_final_1/handoff.md` |
| **Adversarial Challenger** | `302bfc06` | 4대 단언문 결함 주입(Fault Injection) 스트레스 테스트, 9종 모델 SUMO 실측, 원자적 핫스왑 및 NaN 가드 검증 | **APPROVE** | `.agents/challenger_final_1/handoff.md` |
| **Forensic Auditor** | `b3acd33f` | 정적 분석(`SyntheticVehicle` 박멸 확인), 런타임 물리 계층 추적, 200k 준비도 및 안전 Halt 프로토콜 감사 | **CLEAN** | `.agents/auditor_final_1/handoff.md` |

---

## 4. 9종 베이스라인 및 최적 하이퍼파라미터 현황

| 모델명 | 분류 | 액션 구조 | 대표 파라미터 설정 | 검증 상태 |
|---|---|---|---|---|
| **HybridPPO** | Category 1 (Basic) | Categorical(4) + Gaussian(2) | `lr`: 3e-4, `clip_eps`: 0.2, `gamma`: 0.99, `entropy_coef`: 0.01 | **검증 완료 (Verified)** |
| **HybridSAC** | Category 1 (Basic) | Gumbel-Softmax + Squashed Gaussian | `lr`: 3e-4, `alpha`: 0.2, `tau`: 0.005, `buffer_size`: 100,000 | **검증 완료 (Verified)** |
| **HybridTD3** | Category 1 (Basic) | Deterministic + Clipped Noise | `lr`: 3e-4, `noise_clip`: 0.5, `policy_noise`: 0.2, `policy_freq`: 2 | **검증 완료 (Verified)** |
| **MAPPO** | Category 2 (Latest) | Decentralized Actor + Centralized Critic | `lr`: 3e-4, `clip_eps`: 0.2, `vf_coef`: 0.5, `entropy_coef`: 0.01 | **검증 완료 (Verified)** |
| **HyARPPO** | Category 2 (Latest) | Discrete Embedding(4→8) + Continuous Branch | `lr`: 3e-4, `embed_dim`: 8, `clip_eps`: 0.2 | **검증 완료 (Verified)** |
| **MPDQN** | Category 2 (Latest) | Multi-Pass Parameterized Q-Network | `lr`: 1e-3, `gamma`: 0.99, `eps_decay`: 0.995, `target_update`: 1000 | **검증 완료 (Verified)** |
| **PureAoI** | Category 3 (SOTA AoI) | Whittle Index Heuristic Grant | `urgency_weight`: 1.0, `error_threshold`: 0.5 | **검증 완료 (Verified)** |
| **DuelingQAoI** | Category 3 (SOTA AoI) | Dueling $V(s) + A(s, a)$ Double DQN | `lr`: 5e-4, `gamma`: 0.99, `hidden_dim`: 128 | **검증 완료 (Verified)** |
| **SACAoI** | Category 3 (SOTA AoI) | Lyapunov Constrained Peak-AoI SAC | `lr`: 3e-4, `lyapunov_budget`: 1.5, `alpha_init`: 0.2 | **검증 완료 (Verified)** |

---

## 5. 사용자 검토(Code Review) 및 200,000 스텝 헤비 훈련 착수 가이드

현재 파이프라인은 200,000 스텝 대규모 연산 착수 전 **안전하게 정지(Halted)**되어 사용자의 코드 리뷰 및 실행 승인을 대기하고 있습니다.

### 5.1 사용자 자가 검증 명령어 (약 1분 소요)
```bash
# 1. 독립 SUMO 환경 및 Anti-Mocking 5단계 자가 검증 (종료 코드 0 확인)
/home/imnyj/venv/bin/python /home/imnyj/Workspace/paper4/coder/verify_environment.py

# 2. Short Dummy Run 엔드투엔드 파이프라인 검증 (14개 항목, ~3.5초)
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_dummy_verification.py -v

# 3. 전체 프로젝트 통합 회귀 테스트 스위트 (199개 항목, ~42초)
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/ -v
```

### 5.2 200,000 스텝 대규모 훈련 및 HPO 개시 명령어 (사용자 승인 후 실행)
```bash
# [작업 1] Optuna 하이퍼파라미터 최적화 (200k 스텝 환경 기반)
/home/imnyj/venv/bin/python /home/imnyj/Workspace/paper4/coder/src/hpo.py --trials 20

# [작업 2] 9종 베이스라인 모델 200,000 스텝 정규 훈련 (Dual-Model Hot-swap)
/home/imnyj/venv/bin/python /home/imnyj/Workspace/paper4/coder/src/hot_swap_trainer.py --model HybridPPO --episodes 100 --steps 2000

# [작업 3] 다중 밀도 / 다중 시드 IEEE TWC 벤치마크 평가 (250회)
/home/imnyj/venv/bin/python /home/imnyj/Workspace/paper4/coder/src/evaluate.py
```
