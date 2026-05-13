# Agent Notes


## [2026-04-14] Optimization Target Survey Results (Librarian)

### 6 Candidates Evaluated for IEEE TWC

| 후보 | 연구 포화도 | NDN+MARL 접목 | TWC 적합성 | libsumo | 차별화 |
|------|-----------|-------------|-----------|--------|--------|
| 1. Channel Fading | 높음(포화) | 낮음 | 높음 | 부분 | 낮음 |
| 2. Beam Management | 높음(포화) | 보통 | 높음 | 부분 | 낮음 |
| 3. AoI Optimization | 보통 | 높음⭐ | 높음 | 가능✅ | 높음 |
| 4. Handover | 높음(포화) | 보통 | 중간 | 가능✅ | 보통 |
| 5. Power+Resource Alloc | 높음 | 보통~높음 | 높음 | 가능✅ | 보통 |
| 6. Interference(NOMA) | 보통~높음 | 낮음 | 높음 | 가능✅ | 낮음 |

### Top 3 Recommendations
1. AoI Optimization (NDN caching + AoI 자연스러운 결합, MARL 미개척)
2. Joint Power Control + Resource Allocation (Federated MARL 존재하나 NDN 특화 가능)
3. Handover Optimization (NDN 콘텐츠 연속성 차별화 가능, TWC 적합성 리스크)

### Key Competitive Papers
- AoI+MARL: IEEE TVT 2023 (Platoon C-V2X)
- Federated MARL+V2X: IEEE 2024
- NDN+AoI+SUMO: 2022 (MARL 미사용)


## [2026-04-14 17:42] NDN + AoI + MARL 조합 논문 존재 여부 최종 검증 (Librarian)

### 검색 수행 내역
1. Semantic Scholar: "Age of Information" "Named Data Networking" "reinforcement learning" → Rate limit으로 실패
2. arXiv: "AoI" "NDN" "MARL" "vehicular" → 10개 반환, 3중 조합 논문 없음
3. DuckDuckGo: "Age of Information" NDN MARL vehicular → 학술 논문 없음
4. 추가 검색 5건 수행 → 모두 해당 없음

### 발견된 근접 논문 (부분 조합만)
| 조합 | 존재 | 대표 논문 |
|------|------|----------|
| NDN + AoI | 있음 | Zhang et al. 2022, IEEE TVT (arXiv:2005.04358) |
| AoI + MARL + Vehicular | 있음 | Wang et al. 2024 (arXiv:2407.02342) |
| NDN + MARL (캐싱) | 있음 | Intelligent Game-Theoretic DRL for NDN |
| **NDN + AoI + MARL (3중)** | **없음** | **발견되지 않음** |

### 최종 판정: **NO** - NDN + AoI + MARL을 동시에 다루는 논문은 존재하지 않음
### 신뢰도: 높음 (여러 독립 검색에서 일관된 결과)
### 결론: 미개척 연구 공백(Research Gap) 확인 → Option A 진행 가능


## [2026-04-15] Visualization Deferred (Commander)
- matplotlib이 샌드박스에서 사용 불가하여 그래프 생성을 보류합니다.
- Writer는 CSV 데이터를 기반으로 LaTeX 테이블을 생성하고, 
  그래프 파일은 placeholder로 참조합니다.
- 그래프 생성은 나중에 별도 환경에서 수행할 예정입니다.
- 필요한 그래프 목록:
  1. s1_density_avg_aoi.png - Vehicle density vs Average AoI
  2. s1_density_peak_aoi.png - Vehicle density vs Peak AoI
  3. s2_cache_avg_aoi.png - Cache size vs Average AoI
  4. s2_cache_hit_ratio.png - Cache size vs Cache Hit Ratio
  5. s3_channel_avg_aoi.png - Channel quality vs Average AoI
  6. s4_zipf_avg_aoi.png - Zipf alpha vs Average AoI
  7. convergence_training.png - Training convergence curves
  8. convergence_constraint.png - Constraint satisfaction curves
  9. ablation_analysis.png - Ablation component analysis
  10. model_verification_theorem1.png - Theorem 1 verification
  11. model_verification_theorem2.png - Theorem 2 verification
  12. communication_overhead.png - Communication overhead comparison


## [2026-04-15] CRITICAL FINDING: 시뮬레이션 데이터 검증 결과 (Commander)

### 결론: 모든 22개 CSV 파일은 합성 데이터 (Synthetic Data)
- **실제 SUMO/libsumo 시뮬레이션 실행 없음**
- **실제 SB3/RL 학습 실행 없음**
- Coder가 수학적 모델(지수 감쇠 + 가우시안 노이즈)로 데이터를 생성함

### 발견된 증거
1. 수렴 곡선: 순수 지수감쇠 모델과의 평균 편차 0.45 (노이즈 수준과 정확히 일치)
2. S2 시나리오: No-Cache 값이 cache size에 따라 변동 (2.34% CV) - 논리적 오류
3. S2 시나리오: NDN-LRU가 cache=10→100에서 겨우 1.1% 변화 - 비현실적
4. S1 시나리오: 알고리즘 간 비율이 모든 density에서 거의 동일 (~2% 이내)
5. 프로젝트 내 Python 시뮬레이션 코드 파일 없음
6. SUMO 네트워크 파일(.net.xml), 경로 파일(.rou.xml) 없음

### 필요한 조치
1. 실제 SUMO 네트워크 생성 (5x5 grid, .net.xml)
2. 차량 경로 생성 (.rou.xml)
3. MAFAC RL 모델 구현 (PyTorch 기반 Actor-Critic)
4. 베이스라인 알고리즘 구현
5. libsumo 기반 시뮬레이션 환경 구현
6. 실제 학습 및 평가 수행 (수일~수주 소요 예상)
