# Milestone 1 Handoff Report (`handoff.md`)

- **작성자**: Milestone 1 구현 엔지니어 (`worker_m1`)
- **수행 완료 일시**: 2026-08-24
- **작업 디렉토리**: `/home/imnyj/Workspace/paper4/.agents/teamwork_preview_worker_m1`
- **대상 프로젝트**: `/home/imnyj/Workspace/paper4`
- **수신자**: 오케스트레이터 (`orchestrator_1` / `parent`)

---

## 1. Observation (직접 관찰한 사실)
1. **`code/aoi_tracker.py`**:
   - 기존 코드에서는 전체 활성 차량 쌍의 스텝별 평균 AoI(`aoi_history`)만 계산하고 있었으며, 6개 통신 거리 구간(0~50, 50~100, 100~150, 150~200, 200~250, 250~300m)별 AoI 누적 변수 및 반환 메서드가 부재했습니다.
2. **`code/sim_engine.py`**:
   - 에피소드 종료 시점의 메트릭 반환 딕셔너리(`SimulationRunner.run:655-672`)에 `distance_pdr` (6개 구간)과 `cbr_history`는 포함되어 있었으나, `distance_aoi` 필드가 누락되어 있었습니다.
3. **`code/resnet_moe_agent.py` & `code/moe_agent.py`**:
   - `ResNetMoEAgent` 및 `MoEAgent` 클래스에 행동 인덱스(`int`)를 선택하는 `act()`/`select_action()` 메서드만 정의되어 있었고, t-SNE 및 동적 라우팅 분석을 위한 128차원 잠재 특징 벡터($z$)와 3차원 Softmax Gating 가중치($g$)를 외부로 반환하는 API가 존재하지 않았습니다.
4. **수정 후 실측 관찰**:
   - `aoi_tracker.py`에 거리 구간별 AoI 누적 로직과 `get_distance_aoi()` / `get_distance_aoi_dict()` 메서드를 구현하고, `sim_engine.py`의 반환 딕셔너리에 `"distance_aoi"`를 연동했습니다.
   - `resnet_moe_agent.py` 및 `moe_agent.py`에 `get_latent_and_gate(state)` 메서드를 구현했습니다.
   - 신규 구현된 `code/test_m1_audit.py`를 실행한 결과 6개 테스트 전수 통과(exit code 0)하였으며, 실제 SUMO 시뮬레이션에서 6개 버킷 `distance_aoi` 및 `cbr_history`가 정상 추출되었습니다.

---

## 2. Logic Chain (논리적 추론 과정)
1. **거리 구간별 실측 AoI 집계 필요성**:
   - [Observation 1, 2] $\implies$ 시뮬레이터에서 거리 구간별 실제 수신 패킷 연령을 누적하지 않아 `visualizer/prepare_data.py`가 사후 가상 역산 수식으로 `aoi_vs_distance.csv`를 생성하는 왜곡이 발생했습니다.
   - [수정 조치] $\implies$ `aoi_tracker.step()` 시점에 유효 차량 쌍의 거리 $d = \sqrt{\Delta x^2 + \Delta y^2}$에 따라 6개 거리 버킷($b = \min(\lfloor d/50 \rfloor, 5)$)에 순간 AoI를 누적하고, 에피소드 종료 시 `get_distance_aoi()`를 통해 6개 구간의 실측 평균 AoI를 반환하도록 개선함으로써 사후 가상 수식을 전면 배제할 수 있는 기반을 완성했습니다.
2. **`cbr_history` 연속 시계열 보장**:
   - [Observation 2] $\implies$ 매 스텝(0.1초) 계산되는 국소 CBR의 전체 평균이 웜업 이후 매 스텝 `cbr_history` 리스트에 순차 추가되고, 에피소드 결과 딕셔너리에 리스트로 온전히 반환됨을 실측 확인했습니다.
3. **MoE 잠재 벡터 및 게이팅 가중치 추출 API**:
   - [Observation 3] $\implies$ `ResNetMoEAgent`에 `get_latent_and_gate(state)`를 구현하여 5차원 상태를 전달하면 2블록 ResNet Feature Extractor의 128차원 벡터와 Softmax Gating Network의 3차원 확률 벡터를 `(128,), (3,)` (단일 상태) 또는 `(B, 128), (B, 3)` (배치) 형태의 NumPy 배열로 `torch.no_grad()` 환경에서 안전하게 추출할 수 있도록 하였습니다.
   - 이를 통해 향후 t-SNE 2D 투영 및 혼잡도별 전문가 라우팅 비율 플롯을 100% 실제 신경망 추론 데이터로부터 직접 생성할 수 있게 되었습니다.

---

## 3. Caveats (제약 사항 및 가정)
- **No caveats.**
- 본 작업은 시뮬레이션 환경 및 신경망 인터페이스 수정(Milestone 1)에 국한되며, 후속 마일스톤(M2: 모델/데이터 정제 및 Optuna 재최적화, M3: 17개 모델 재훈련, M4: 17,000 에피소드 대규모 병렬 스윕, M5: 실측 데이터 기반 시각화 파이프라인 개편)은 계획된 파이프라인에 따라 순차적으로 진행될 예정입니다.

---

## 4. Conclusion (최종 결론)
- Milestone 1의 모든 요구사항(`aoi_tracker.py` 6-bin distance AoI 누적, `sim_engine.py` `distance_aoi`/`cbr_history` 반환 연동, `resnet_moe_agent.py` `get_latent_and_gate` 구현, 파일 락/감사 로깅 준수)을 100% 결함 없이 완수하였습니다.
- 신규 감사 테스트 스위트(`test_m1_audit.py`) 6개 테스트 및 기존 회귀 테스트 31개 테스트가 전수 PASS되었음을 확인했습니다.

---

## 5. Verification Method (독립 검증 방법)
독립 감사관 또는 후속 에이전트는 다음 명령어를 통해 본 작업 내용을 즉시 재검증할 수 있습니다:

```bash
# 1. Milestone 1 전용 감사 테스트 실행
/home/imnyj/venv/bin/pytest -v -s /home/imnyj/Workspace/paper4/code/test_m1_audit.py

# 2. 전체 연계 회귀 테스트 실행
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/code/test_m1_audit.py /home/imnyj/Workspace/paper4/code/test_comm_module.py /home/imnyj/Workspace/paper4/code/test_c1_c2_wiring.py /home/imnyj/Workspace/paper4/code/test_c3_reward.py /home/imnyj/Workspace/paper4/code/test_m7_nest.py /home/imnyj/Workspace/paper4/code/test_m8_local_cbr.py

# 3. 소스 코드 수정 파일 검사
# - /home/imnyj/Workspace/paper4/code/aoi_tracker.py
# - /home/imnyj/Workspace/paper4/code/sim_engine.py
# - /home/imnyj/Workspace/paper4/code/resnet_moe_agent.py
# - /home/imnyj/Workspace/paper4/code/moe_agent.py
```
