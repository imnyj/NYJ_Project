# Reviewer Memory

## 에이전트 정보
- **에이전트 이름**: Reviewer
- **역할**: 코드 검증 전문가 (Mode A: validator)
- **담당 논문**: /home/imnyj/papers/paper4

---

## 검증 이력

### L1-A-1 — PASS
- **파일**: sim/sim_engine.py
- **결과**: PASS — libsumo 통합부 결백
- **메모**: sim_engine.py의 libsumo 통합 부분에서 문제 없음 확인

---

### L1-A-2 — FAIL ⚠️
- **파일**: sim/etsi_cam_layer.py
- **결과**: FAIL
- **루트 코즈**: **키 대소문자 불일치 버그** (단 1개 라인)
  - `VehicleCAMState.__init__` **line 97**: `self.params.get('CBR_target', 0.60)`
  - sensitivity_runner.py는 `'cbr_target'` (소문자)를 전달
  - Python dict는 case-sensitive → 모든 SA3 run에서 default 0.60 사용
  - SA3 sweep 7개 값(0.30~0.70) 전부 동일 동작 → 동일 AoI/CBR/PDR 출력
- **핵심 라인들**:
  - line 77: VehicleCAMState.__init__ (method_params 수령)
  - line 80: self.params = method_params or {} (저장)
  - line 97: CBR_target = self.params.get('CBR_target', 0.60) ← **BUG HERE**
  - line 98: self.blb_CBR_target: float = CBR_target (인스턴스 변수)
  - line 168: ETSICAMLayer.__init__ (method_params 수령 및 저장 — 정상)
  - line 296: elif method == "BL-B": (분기 조건 — 정상)
  - line 340: error = vs.blb_CBR_smoothed - vs.blb_CBR_target (비교 — 경로 존재하나 target 고정)
- **수정 필요**: line 97의 키를 `'cbr_target'`으로 변경 (소문자 통일)
- **Q-B3 (BL-B 분기)**: PASS — 분기 진입 로직 정상
- **Q-B5 (per-step 경로)**: 구조적으로 존재하나 target 고정으로 무력화됨

---

## 핵심 지식

### etsi_cam_layer.py 아키텍처
- `ETSICAMLayer`: 중앙 CAM 관리 레이어, `step()` 메서드로 매 100ms마다 호출
- `VehicleCAMState`: 차량별 상태 (T_GenCam, p_tx, DCC 컨트롤러 상태)
- DCC 분기: BL-A (ETSI Reactive), BL-B (Simplified Adaptive), BL-C (Bhattacharyya), BL-D (Fixed 10Hz)
- method_params 전달 경로: ETSICAMLayer.__init__ → get_or_create_vehicle() → VehicleCAMState.__init__

### 알려진 버그
- `'CBR_target'` vs `'cbr_target'` 키 불일치 → SA3 sweep 완전 무력화
- 다른 파라미터(T_min, T_max, delta_T, lambda_s)도 동일 naming convention 점검 필요

---

## 검증 금지 파일 (절대 접근 불가)
- sim_engine.py
- aoi_tracker.py
- sensitivity_runner.py
