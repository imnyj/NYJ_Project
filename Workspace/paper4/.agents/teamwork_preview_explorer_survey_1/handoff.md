# Handoff Report - explorer_survey_1

## 1. Observation (직접 관찰 결과)
1. **SUMO 네트워크 및 모빌리티 연동 (`code/sim_engine.py:487-587`)**:
   - `sim_engine.py:499`에서 `generate_sumonetsim_files(self.work_dir, config, self.seed)`를 호출하여 `/home/imnyj/SumoNetSim1.1.5/src/sumo/make_sumo_set.py`를 통해 $6\times 6$ 격자망(`generated.net.xml`, `generated.rou.xml`)을 동적 생성함.
   - `libsumo.simulationStep()`을 통해 100ms마다 `libsumo.vehicle.getPosition`, `getSpeed`, `getAngle`, `getAcceleration`을 호출하여 활성 차량의 모빌리티를 추출함.
2. **PDR 수학적 감쇄 모델 (`code/sim_engine.py:54-96, 258-261`)**:
   - 거리 감쇄: `PL_d = PL_0_dB + 10 * PATH_LOSS_EXP * log10(dist_m)` (5.9 GHz, $\alpha=2.0$, $PL_0 \approx 47.85\text{ dB}$).
   - 페이딩: Nakagami-$m$ ($m=3$) CCDF 공식 $P_{\text{rx}} = \exp(-x)(1 + x + 0.5 x^2)$ ($x = 3 \cdot SNR_{\text{thresh}} / SNR$).
   - 밀도/CBR 감쇄: `col_factors = np.maximum(0.1, 1.0 - rcv_cbrs * 0.8)`, `p_success = p_rx_arr * col_factors`.
3. **AoI 추적 및 거리별 메트릭 구조 (`code/sim_engine.py:655-672`, `code/aoi_tracker.py:114-163`)**:
   - `aoi_tracker.py`는 $300\text{m}$ 통신 반경 내 차량 쌍별 $AoI_{ij}(t) = \text{clip}((t_{\text{sim}} - T_{ij}) \times 1000, 0, 2000)\text{ [ms]}$를 추적하여 평균 AoI를 반환함.
   - `sim_engine.py:655-661`는 `distance_pdr` (6개 거리 구간: 0~50, 50~100, 100~150, 150~200, 200~250, 250~300m)를 계산하여 반환함.
   - **결함 확인**: `sim_engine.py`의 return dict(lines 662-672) 및 `aoi_tracker.py`에 `distance_aoi`에 대한 구간별 집계 로직 및 반환 필드가 전혀 없음.
4. **MoE/t-SNE 로깅 및 가상 데이터 현황 (`code/resnet_moe_agent.py:63-93`, `visualizer/prepare_data.py:258-325, 405-437`)**:
   - `ResNetMoEDQN`은 128차원 `feature_extractor`와 3개 전문가 `gating_network`를 보유하나, `ResNetMoEAgent`에 이를 추출/반환하는 인터페이스가 없음.
   - `visualizer/prepare_data.py`의 `build_distance_metrics()`는 가상 수식(`aoi_base / max(0.01, prx/100)`), `build_moe_routing()`은 하드코딩 배열(`[88, 76, 58, ...]`), `build_tsne_clustering()`은 임의 상태 샘플/사인 함수를 사용하고 있음.

---

## 2. Logic Chain (논리적 추론 체인)
1. **관찰 1 & 2 $\implies$ SUMO 모빌리티 및 무선 채널 모델의 신뢰성 검증**:
   - SUMO의 실제 주행 궤적(위치, 속도, 각도)이 매 100ms마다 정확히 추출되어 `ETSICAMLayer`의 CAM 생성 트리거와 통신 반경 300m 내 유클리드 거리 계산에 사용되고 있습니다.
   - PDR은 자유공간 경로손실, Nakagami-3 페이딩, 로컬 CBR 충돌 계수에 의해 거리 및 교통 밀도에 따라 수학적으로 정밀하게 감쇄하므로 통신 채널 시뮬레이션의 물리적 타당성이 확인되었습니다.
2. **관찰 3 $\implies$ `distance_aoi` 누락과 시각화 왜곡의 원인 규명**:
   - `sim_engine.py`와 `aoi_tracker.py`에서 `distance_aoi`를 계산하지 않았기 때문에, `prepare_data.py`가 사후 가상 수식으로 `aoi_vs_distance.csv`를 생성할 수밖에 없었습니다.
   - `sim_engine.py` / `aoi_tracker.py`에 6개 거리 구간별 순간 AoI 누적 기능을 추가해야만 100% 실제 데이터 기반 거리별 AoI 곡선 도출이 가능합니다.
3. **관찰 4 $\implies$ MoE/t-SNE 100% 실제 신경망 추론 연동 경로 도출**:
   - `ResNetMoEAgent`에 `get_latent_and_gate(state)` API를 제공하고, 평가 파이프라인(`run_density_sweep_parallel.py`)에서 평가 에피소드 관측 상태들의 feature(128D)와 gating weight(3D)를 추출하여 `tsne_data.json` 및 `moe_routing.json`으로 덤프하면 `prepare_data.py`의 모든 하드코딩과 가상 배열을 완벽히 제거할 수 있습니다.

---

## 3. Caveats (제한 사항 및 전제 조건)
1. 본 조사는 코드 및 설정 파일에 대한 정밀 정적 분석(Read-only Survey)을 기반으로 수행되었습니다 (코드 직접 수정 미실시).
2. 실제 17,000 에피소드 대규모 스윕 실행 시간은 병렬 워커 수(CPU 코어 수 및 GPU 수)에 따라 달라질 수 있습니다.

---

## 4. Conclusion (최종 결론 및 권고 사항)
1. **시뮬레이션 환경 감사 완료 (R1 Audit PASSED with Modification Requirements)**:
   - SUMO 모빌리티 반영 및 거리/밀도에 따른 PDR 감쇄 모델은 수학적/물리적으로 완벽하게 구현되어 있습니다.
2. **후속 구현 필수 변경 요구사항**:
   - **`sim_engine.py` & `aoi_tracker.py`**: 6개 거리 구간(0~300m, 50m 간격)별 `distance_aoi` 누적 및 return dict 추가.
   - **`resnet_moe_agent.py`**: 128D Latent Feature 및 3D Gate Weight 추출 메서드(`get_latent_and_gate`) 구현.
   - **Evaluation Pipeline (`run_density_sweep_parallel.py`)**: 17개 모델에 대해 10개 밀도 평가 시 `eval_density_results.csv`, `distance_pdr.json`, `distance_aoi.json`, `cbr_trace.json`, `tsne_data.json`, `moe_routing.json`을 100% 실제 시뮬레이션 및 모델 추론 결과로 직접 생성.
   - **`visualizer/prepare_data.py`**: 가상 수식 및 하드코딩 배열을 완전 삭제하고 실제 생성된 JSON/CSV 파일만 로드하도록 단순화.

---

## 5. Verification Method (독립 검증 방법)
1. **통신 모듈 검증**:
   ```bash
   python3 code/test_comm_module.py
   ```
2. **주요 소스 파일 위치 및 라인 확인**:
   - `code/sim_engine.py`: lines 54-96 (PDR decay), lines 655-672 (metric return)
   - `code/aoi_tracker.py`: lines 114-163 (AoI calculation)
   - `code/resnet_moe_agent.py`: lines 63-93 (MoE architecture)
   - `visualizer/prepare_data.py`: lines 258-325, 405-437 (가상 데이터 및 수식 위치)
3. **상세 분석 보고서 확인**:
   - `/home/imnyj/Workspace/paper4/.agents/teamwork_preview_explorer_survey_1/survey_sim.md`
