# 9개 베이스라인 및 학습/HPO/평가 파이프라인 정밀 코드 리뷰 보고서

**작성자**: `reviewer_genuine_2`  
**일자**: 2026-08-27  
**대상 파일**:
- `src/hot_swap_trainer.py`
- `src/hpo.py`
- `src/evaluate.py`
- `src/rl_interface.py`
- `src/baselines/*.py`
- `tests/test_dummy_verification.py` 및 관련 테스트 스위트

---

## 1. Review Summary (총평 및 최종 판정)

**최종 판정**: **REQUEST_CHANGES (변경 요청)**

### 핵심 사유:
전반적인 코드베이스는 진정한 SUMO 물리 시뮬레이션 환경(`AoiV2IEnv`), 하이브리드 액션 공간 디코딩, 9개 베이스라인 RL 모델의 수학적/신경망 구현, 20만 스텝 대비 구조, TensorBoard 및 체크포인트 파이프라인을 매우 충실하고 정직하게 구현하였습니다. 가짜 모킹(Mocking)이나 하드코딩된 속임수는 전혀 발견되지 않았습니다.

그러나 다중 모델 및 다중 시드 연속 평가(`run_full_benchmark`, 10개 모델 × 5개 밀도 × 5개 시드 = 250회 실행) 또는 20만 스텝 다중 에피소드(100회 에피소드) 수행 시, 환경 `reset()` 과정에서 호출되는 `src/sumo/make_sumo_set.py`의 `generated.net.xml` 비원자적(non-atomic) 파일 덮어쓰기로 인해 간헐적으로 XML 파일 파싱 손상(`xml.etree.ElementTree.ParseError: unclosed token` / `invalid document structure`)이 발생하여 `test_09_run_full_benchmark_end_to_end`가 실패하는 치명적 레이스 컨디션(Race Condition) 결함이 발견되었습니다. 대규모 20만 스텝 장기 훈련의 무중단 안정성을 위해 이 결함의 수정이 필수적입니다.

---

## 2. Findings (발견 사항)

### [Major Finding 1] `make_sumo_set.py`의 비원자적 XML 수정으로 인한 연속 리셋 시 파싱 충돌
- **위치**: `/home/imnyj/Workspace/paper4/coder/src/sumo/make_sumo_set.py:41-48, 105, 138` 및 `/home/imnyj/Workspace/paper4/coder/src/hot_swap_trainer.py:696, 740`
- **현상**:
  `AoiV2IEnv.reset()`이 호출될 때마다 `_init_sumo()` -> `ss.make_sumo_files()`가 실행되어 `generated.net.xml`을 새로 생성하고 `make_dead_end_nodes`에서 `ET.parse(netfile)` 후 `tree.write(netfile)`을 수행합니다.
  연속으로 수차례 환경 리셋이 일어나는 벤치마크 루프(`run_full_benchmark`)에서 `netconvert` 프로세스 종료 직후 파일 버퍼가 디스크에 완전히 동기화되지 않은 상태에서 `ET.parse()`가 실행되거나 `tree.write()`가 수행되면서 `generated.net.xml`이 깨져 `libsumo.start()`가 `TraCIException: Process Error (Error: invalid document structure in file 'src/sumo/generated.net.xml')` 또는 `ParseError`를 던집니다.
- **영향도**: 단일 실행(1회 에피소드)은 정상 동작하나, 100회 에피소드 20만 스텝 연속 훈련 및 250회 벤치마크 전체 수행 시 불규칙하게 프로세스가 중단될 위험이 매우 큼.
- **개선 권고사항**:
  1. 도로망 토폴로지 XML(`generated.net.xml`, `generated.nod.xml`, `generated.edg.xml`)은 최초 1회만 생성하고, 에피소드 리셋 시에는 변동되는 차량 흐름 파일(`generated.rou.xml`)만 재생성하도록 분리.
  2. 파일 작성 시 임시 파일(`tempfile.NamedTemporaryFile`)에 작성 후 `os.replace`로 원자적 교체(atomic replace) 수행 및 `tree.write(..., encoding="utf-8", xml_declaration=True)` 지정.

---

## 3. Verified Claims (주요 검증 항목 상세)

| 검증 항목 | 검증 기준 | 검증 방법 및 결과 | 판정 |
| :--- | :--- | :--- | :---: |
| **1. 9개 베이스라인 하이브리드 액션 공간 처리** | $\Delta \in [0.5, 10.0]$, $ch \in \{0..3\}$, $p \in [20.0, 30.0]$ | `tests/test_baselines_instantiation.py` 45개 테스트 및 모델 코드 검사. 모든 모델이 `ActionDecoder`를 통해 유효 범위 내의 튜플 반환 확인 | **PASS** |
| **2. 20만 스텝 학습 파이프라인 구조적 준비성** | 2000 steps * 100 episodes, TensorBoard, `checkpoints/` 저장 | `src/hot_swap_trainer.py:run_hot_swap_training` 확인: 100스텝 주기 `gc.collect()`/`empty_cache()`, `SummaryWriter` 9개 메트릭 로깅, `checkpoints/{model}_best.pt` 및 주기별 체크포인트 저장 확인 | **PASS** |
| **3. HPO 및 평가 파이프라인의 진성 SUMO 연동** | 모킹/더미 없이 `AoiV2IEnv` 직접 구동, 레일리 페이딩 채널 연산 | `src/hpo.py:evaluate_model_in_env`, `src/evaluate.py:evaluate_single_run` 확인: `AoiV2IEnv` 직접 생성 및 4개 안티 모킹 assertion 통과 확인 | **PASS** |
| **4. 10스텝 단기 더미 검증 테스트 스위트** | 파이프라인 전 구성요소 10스텝 충돌 없는 연동 및 <15초 완료 | `pytest tests/test_dummy_verification.py -v` 실행 결과 14개 테스트 전원 통과 (3.62초 소요) | **PASS** |
| **5. 무결성 위반 (Integrity Violation) 검사** | 하드코딩된 정답, 더미 구현체, 합성 모킹 숏컷 유무 | 전체 소스코드 정밀 검사: 순수 PyTorch 신경망 및 실시간 libsumo 텔레메트리 기반 동작 확인 (치팅 0건) | **PASS** |

---

## 4. 9개 베이스라인 구현 정밀 평가

### Category 1: 기본 모델 3종
1. **HybridPPO (`hybrid_ppo.py`)**:
   - 이산 서브채널 선택을 위한 `Categorical` 헤드와 연속 전송주기/전력 선택을 위한 `Normal` 가우시안 헤드를 장착한 액터-크리틱 구조.
   - SMDP 변동 주기 할인율 $\gamma^\Delta$ 적용 및 PPO 클리핑 목적함수 + 엔트로피 보너스 구현 정상.
2. **HybridSAC (`hybrid_sac.py`)**:
   - Gumbel-Softmax 이산 채널 샘플링과 재파라미터화(Reparameterization trick) 가우시안 헤드 연동.
   - Twin Q-Critic ($Q_1, Q_2$), 폴리악(Polyak) 타깃 소프트 업데이트, 자동 튜닝 엔트로피 온도($\alpha$) 구현 정상.
3. **HybridTD3 (`hybrid_td3.py`)**:
   - Twin Q-Critic 기반 타깃 액션 스무딩(Clipped Gaussian Noise) 및 2스텝 지연 정책 업데이트(`policy_freq=2`) 구현 정상.

### Category 2: 최신 / 하이브리드 모델 3종
4. **MAPPO (`mappo.py`)**:
   - 탈중앙화 액터(Decentralized Actor) + 중앙 집중형 크리틱(Centralized Critic, CTDE) 구조.
   - 개별 차량 텔레메트리 관측 기반 액션 도출 및 셀 전체 혼잡도를 반영한 전역 가치 평가 구현 정상.
5. **HyAR-PPO (`hyar_ppo.py`)**:
   - 서브채널 이산 선택 결과를 `nn.Embedding`으로 임베딩 후 상태 벡터와 결합하여 연속 파라미터($\Delta, p$) 헤드를 조건화(Conditioning)하는 Branching PPO 아키텍처 완벽 구현.
6. **MP-DQN (`pdqn.py`)**:
   - 4개 서브채널 각각에 대한 연속 파라미터를 출력하는 Parameter Actor와, 모든 파라미터를 결합하여 각 채널별 Q-value를 평가하는 Multi-Pass Q-Network 및 $\epsilon$-greedy 탐색 구현 정상.

### Category 3: SOTA AoI 모델 3종
7. **PureAoI (`pure_aoi.py`)**:
   - AoI 정규화값과 RSU 거리를 반영한 Whittle Index 기반 적응형 Age-Greedy 스케줄러.
   - 긴급 차량에게는 $\Delta=0.5\text{s}, p=30\text{dBm}$의 우선권을 부여하고 신선한 차량은 백오프하는 스케줄링 로직 및 `BaseRLModel` 인터페이스 호환성 완비.
8. **DuelingQAoI (`dueling_q_aoi.py`)**:
   - 상태 가치 $V(s)$와 행동 이점 $A(s, a)$ 스트림을 분리하여 $Q(s, a) = V(s) + (A(s, a) - \bar{A})$로 결합하는 듀얼링 Q 구조.
   - 이산화된 20개 액션 그리드에 대한 Double DQN 타깃 계산 구현 정상.
9. **SAC-AoI (`sac_aoi.py`)**:
   - AoI 임계값 초과 패널티를 보상 함수에 증강하는 Lyapunov Drift-plus-Penalty 정식화 적용.
   - 하이브리드 SAC 기반 엔트로피 극대화 정책 및 트윈 크리틱 구조 정상.

---

## 5. Adversarial Stress-Test (공격적 한계 검증) 결과

1. **액션 공간 경계값 입력 테스트**:
   - 음수, 극단적 양수, NaN 입력에 대해 `ActionDecoder._sigmoid()`와 `np.clip`이 안전하게 [0.5, 10.0]s, [20.0, 30.0]dBm으로 클램핑함을 확인 (`PASS`).
2. **핫스왑 NaN/Inf 가드 주입 테스트**:
   - Rest 모델 가중치에 의도적으로 `torch.nan`, `torch.inf`를 주입했을 때 `DualModelHotSwapManager.hot_swap()`이 즉시 이를 감지하고 동기화를 거부하여 서비스 중인 Act 모델을 완벽히 보호함을 확인 (`PASS`).
3. **장기 훈련 메모리 프로파일링**:
   - 20만 스텝 진행 중 100스텝마다 `gc.collect()`와 `torch.cuda.empty_cache()`를 호출하여 ReplayBuffer 및 텐서 누수를 방지하도록 설계됨을 확인 (`PASS`).
4. **연속 에피소드 고주파 리셋 스트레스 테스트**:
   - 파일 I/O 동기화 지연으로 인한 XML 파싱 에러 발생 (`FAIL -> Major Finding 1 도출`).

---

## 6. 결론 및 조치 요구사항 (Action Items)

구현체는 매우 높은 무결성과 완성도를 가지고 있으므로, 다음 **1가지 핵심 사항**만 개발 에이전트가 수정 완료하면 즉시 최종 **APPROVE**가 가능합니다:

1. **`make_sumo_set.py` 및 `hot_swap_trainer.py`의 리셋 로직 안정화**:
   - 에피소드 리셋 시마다 네트워크 XML을 재생성하지 않고, `generated.rou.xml`만 갱신하거나 임시 파일 원자적 교체(`tempfile` + `os.replace`)를 적용하여 다중 리셋 환경에서 XML 파싱 손상이 발생하지 않도록 수정할 것.
   - 수정 후 `pytest tests/test_evaluation.py` 및 전체 스위트가 100% 무결하게 통과하는지 확인할 것.
