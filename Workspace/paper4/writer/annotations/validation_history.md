# Validation History

## leaf=L1-A-1
- **결과**: PASS
- **범위**: sim/sim_engine.py (libsumo 통합부)
- **요약**: sim_engine.py libsumo 통합부 결백. 문제 없음.

---

## leaf=L1-A-2
- **날짜**: 2025-01-31
- **결과**: FAIL
- **범위**: sim/etsi_cam_layer.py
- **검증 유형**: [Mode A: validator] 좁은 스코프 검증 — SA3 cbr_target sweep 무력화 원인 조사

### 질문별 판정 요약

| 질문 | 판정 | 핵심 근거 |
|------|------|-----------|
| Q-B1 | FAIL | line 97: `self.params.get('CBR_target', 0.60)` — 키 대소문자 불일치 ('CBR_target' vs 'cbr_target') |
| Q-B2 | FAIL | line 340: `error = vs.blb_CBR_smoothed - vs.blb_CBR_target` — 로직 존재하나 target 항상 0.60 |
| Q-B3 | PASS | line 296: `elif method == "BL-B":` — 분기 진입 조건 정확, 오타 없음 |
| Q-B4 | FAIL | default=0.60, key mismatch로 7개 sweep 값 전부 무시됨 → SA3 전체 동일 결과 직접 원인 |
| Q-B5 | PASS (무력화) | per-step cbr 비교 경로 존재하나 blb_CBR_target이 항상 0.60으로 고정됨 |

### 루트 코즈
`VehicleCAMState.__init__` line 97에서 `self.params.get('CBR_target', 0.60)` 키가  
sensitivity_runner.py가 전달하는 `'cbr_target'` (소문자)와 대소문자 불일치.  
Python dict.get()은 대소문자를 구별하므로 모든 SA3 run이 default 0.60으로 초기화됨.

### 수정 제안
1. line 97 키를 `'cbr_target'`으로 통일 (또는 runner 측 키를 `'CBR_target'`으로 변경)
2. 동일 init 블록의 T_min/T_max/delta_T/lambda_s 키 naming convention 일괄 점검
3. 방어적 logging/assert로 파라미터 누락 시 조기 경고 발생

---
