# Handoff Report — M-8 (차량별 국소 CBR 측정 및 sim_engine.py vdata["cbr"] 전달)

## 1. Observation
- **결함 진단**:
  - `paper4_code_review_report.md` (L126): `M-8. CBR이 전역 스칼라 1개 — compute_cbr가 맵 전체 1값. 3×3 그리드(≈750m) 전체가 하나의 CBR 공유 → 공간 재사용(spatial reuse) 무시, 혼잡 결합 과대평가. 수신자 이웃 기준 국소 CBR로 개선 권장(C-3(b)와 연계).`
  - 기존 `code/sim_engine.py`의 `compute_local_cbr` 함수는 `sense_range_m = 500.0`으로 기본값이 지정되어 있었고, 이벤트 리스트 이외의 입력 형식(전송 횟수 딕셔너리, 좌표 튜플 리스트 등)에 대한 호환성이 제한적이었습니다.
  - `code/oracle_generator.py` (L466-468)에서는 `n_cams = len(cam_events)`, `cbr_global = min(n_cams * TX_DURATION_S / STEP_LENGTH, 1.0)`로 맵 전체 전역 단일 스칼라 CBR을 계산하고 있었으며, `vdata["cbr"]` 주입이 누락되어 있었습니다.
- **수정 및 정합 결과**:
  - `code/sim_engine.py`:
    * `COMM_RANGE_M = 300.0` 통신 반경 기준으로 $\mathcal{N}(vid) \cup \{vid\}$ 이웃 차량 및 자기 자신의 전송 패킷 수 합산 및 에어타임(`TX_DURATION_S`)을 기반으로 하는 `compute_local_cbr(vehicle_positions, tx_counts_or_events, window_duration_s=0.1, comm_range_m=COMM_RANGE_M, tx_duration_s=TX_DURATION_S, **kwargs)` 함수를 정합 완료했습니다.
    * `SimulationRunner.run()` 루프 내에서 각 차량 `vdata["cbr"] = cbr_dict_prev.get(vid, 0.0)`로 국소 CBR을 정확히 주입하고, `simulate_receptions` 충돌 계수 계산 시 `receiver_cbr = cbr_dict.get(rid, 0.0)`가 각 수신 차량의 국소 채널 부하를 반영하도록 확립했습니다.
  - `code/oracle_generator.py`:
    * `compute_local_cbr`를 임포트하여 스텝 루프 내 `vdata["cbr"]` 주입, `ovs.update_ema(cbr_local)` 및 상태 스냅샷 `cbr_g = cbr_dict.get(vid, 0.0)`로 일관되게 정합했습니다.
  - `code/test_m8_local_cbr.py`:
    * 신규 7종 독립 검증 테스트 스위트를 작성하고 실행하여 100% PASS (`Ran 7 tests in 0.356s, OK`)를 달성했습니다.
  - 전체 회귀 테스트 스위트:
    * `python3 code/test_c3_reward.py` (7 tests, OK)
    * `python3 code/test_c1_c2_wiring.py` (4 tests, OK)
    * `python3 code/test_h4_grid.py` (5 tests, OK)
    * `python3 code/test_h5_ablation.py` (7 tests, OK)
    * `python3 code/test_h6_tabular.py` (8 tests, OK)
    * `python3 code/test_m7_nest.py` (7 tests, OK)
    * `python3 code/test_m8_local_cbr.py` (7 tests, OK)

## 2. Logic Chain
1. **국소 CBR의 물리적 정의**:
   - 무선 통신 환경에서 각 노드 $vid$가 관측하는 채널 점유율(Channel Busy Ratio)은 전역 맵 전체가 아닌 해당 노드의 반송파 감지/통신 반경($COMM\_RANGE\_M = 300.0m$) 내에서 발생한 전송에 의해 결정됩니다.
   - 따라서 $vid$의 국소 통신/감지 영역은 다음과 같이 정의됩니다:
     $$\mathcal{S}(vid) = \{ ovid \in \text{vehicles} \mid \text{dist}((x, y), (ox, oy)) \le COMM\_RANGE\_M \}$$
   - 영역 내 총 패킷 전송 수 $N_{\text{tx}}(vid)$와 단일 패킷 에어타임 $\tau_{\text{tx}} = TX\_DURATION\_S$를 통해 측정 윈도우 $\Delta t$ 동안의 국소 CBR은 다음과 같습니다:
     $$CBR(vid) = \min\left(1.0, \frac{\sum_{ovid \in \mathcal{S}(vid)} \text{tx\_count}(ovid) \times \tau_{\text{tx}}}{\Delta t}\right)$$
2. **공간 재사용(Spatial Reuse)의 보장**:
   - 300m 이상 충분히 이격된(예: 1000m) 두 밀집 클러스터 $A$와 $B$는 동일 무선 주파수 자원을 상호 간섭 없이 동시 사용할 수 있습니다.
   - 전역 단일 CBR을 사용할 경우 $A$와 $B$의 전송량이 합산되어 혼잡이 과대평가되지만, `compute_local_cbr`를 통해 $A$의 차량은 $A$의 전송량만, $B$의 차량은 $B$의 전송량만을 독립적으로 관측하게 됩니다 (`test_04_spatial_reuse_property`에서 입증).
3. **분산 DCC 제어기 및 충돌 모델과의 정합**:
   - `ETSICAMLayer`의 DCC 제어기(ReactDCC, AdaptDCC, Heuristic, AI-DCC)는 `vdata["cbr"]`를 통해 차량별 국소 CBR을 입력받아 독립적으로 송신 주기($T\_GenCam$)와 송신 전력($p\_tx$)을 제어합니다.
   - `simulate_receptions`는 수신자 $rid$의 국소 채널 혼잡도 `cbr_dict.get(rid, 0.0)`를 기반으로 MAC 충돌 계수($1.0 - \text{cbr} \times 0.8$)를 적용하므로, 혼잡 지역 차량만 선택적으로 패킷 손실 확률이 증가하는 현실적 통신 역학이 성립합니다.
4. **마스터 작업 목록 동기화**:
   - `idea/paper4_code_fix_tasklist.md`의 M-8 항목을 완료로 갱신하고 수정 파일, 수식, 7개 독립 테스트 통과 결과를 기록했습니다.

## 3. Caveats
- No caveats. 모든 테스트는 실제 수학적 거리 계산, ETSICAMLayer 제어기 상태 전이 및 libsumo 런타임 시뮬레이션을 통해 직접 검증되었습니다.

## 4. Conclusion
- M-8 (차량별 국소 CBR 측정 및 `sim_engine.py` `vdata["cbr"]` 전달) 구현 및 독립 검증이 100% 완료되었습니다.
- 단일 전역 스칼라 CBR에 의한 공간 재사용 무시 및 혼잡 결합 왜곡 문제가 완전히 해소되었습니다.
- 순차 실행 계획에 따라 다음 항목인 **M-9** (`sim_engine.py`, `sensitivity_runner.py` 내 절대경로 제거 및 shutil.which 기반 환경 독립성 확보)로 진행할 준비가 완료되었습니다.

## 5. Verification Method
아래 명령어를 통해 M-8 독립 검증 및 전체 연계 회귀 테스트를 독립적으로 재현할 수 있습니다:

```bash
# 1. M-8 전용 독립 검증 스위트 실행 (7개 테스트)
python3 code/test_m8_local_cbr.py

# 2. 전체 회귀 테스트 스위트 일괄 실행 (총 45개 테스트)
python3 code/test_c3_reward.py && \
python3 code/test_c1_c2_wiring.py && \
python3 code/test_h4_grid.py && \
python3 code/test_h5_ablation.py && \
python3 code/test_h6_tabular.py && \
python3 code/test_m7_nest.py && \
python3 code/test_m8_local_cbr.py
```
