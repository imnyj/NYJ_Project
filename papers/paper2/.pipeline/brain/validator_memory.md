# Validator Memory

(첫 작업 수행 시 자동으로 채워집니다)


## [2026-04-15] 검증 #1 (PASS)

### 검증 대상: 22개 CSV 파일
### 결과: PASS (MINOR 이슈 1건)

### 데이터 무결성
- NaN 체크: PASS (모든 파일)
- 범위 체크: PASS (AoI>0, CHR∈[0,1], TSR∈[0,1], CVR∈[0,1])
- 일관성 체크: PASS

### 알고리즘 순위 일관성
- S1 (3개 density 포인트): 모두 Centralized < MAFAC < SAC < IQL < NDN-LRU < No-Cache ✅
- S2 (6개 cache size 포인트): 모두 순위 일관 ✅
- S3, S4: 순위 일관 ✅

### 시나리오 트렌드
- S1: 차량 증가 → AoI 증가 ✅ (3.6→30.9 for MAFAC)
- S2: 캐시 증가 → AoI 감소 ✅ (10.7→9.1), CHR 증가 ✅ (0.34→0.73)
- S3: K-factor 증가 → AoI 감소 ✅ (9.69→9.51), TSR MINOR 이슈
- S4: α 증가 → AoI 감소 ✅ (10.3→9.8), CHR 증가 ✅ (0.51→0.68)

### Model Verification
- Theorem 1: 최대 오차 4.7% (< 10% 기준) ✅
- Theorem 2: TTL 최대 오차 5.2%, AoI 최대 오차 4.5% (< 10%) ✅

### 수렴 곡선
- DRL 알고리즘: 초기 40+ → 최종 수렴 ✅
- NDN-LRU/No-Cache: 변동 <6% ✅

### Ablation
- MAFAC-Full 최고 성능 ✅
- 모든 구성요소 제거 시 AoI 악화 ✅

### MINOR 이슈
- S3_TSR_TREND: MAFAC TSR 0.2903→0.2881 (비단조, 차이 <1%)
