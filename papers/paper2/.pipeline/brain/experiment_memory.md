# Experiment Memory

## [2026-04-15] 실험 설계 완료

### 실험 명세서 생성
- 파일: home/nyj/0_paper/paper/experiment/experiment_spec.json (12,045자)

### 시나리오 설계 (4개)
1. **S1: Vehicle Density Variation** — 차량 20/50/100대, AoI 스케일러빌리티 검증
2. **S2: Cache Size Sensitivity** — 캐시 10~100, NDN 캐싱 효과 분석
3. **S3: Channel Quality Variation** — Rician K=3/5/7/10 dB, 물리계층 영향
4. **S4: Zipf Exponent Sensitivity** — α=0.8/1.0/1.2, 인기도 분포 영향

### 알고리즘 (6개)
- Proposed: MAFAC (Multi-Agent Federated Actor-Critic)
- B1: No-Cache (NDN 캐싱 기여도)
- B2: NDN-LRU (AoI 인식 기여도)
- B3: Centralized-AoI (성능 상한선)
- B4: IQL (연합학습 기여도)
- B5: SAC-Single (다중 에이전트 기여도)

### 메트릭 (8개)
- Primary: Average AoI, Peak AoI, Cache Hit Ratio, Constraint Violation Rate
- Secondary: Tx Success Rate, Throughput, Convergence Speed, Communication Overhead

### 물리계층 파라미터
- C-V2X 5.9 GHz, 10 MHz BW, 50 subchannels
- Rician (V2V), Nakagami-m (V2I), 3GPP TR 36.885 path loss
- Max Tx: 23 dBm, CBR threshold: 0.65

### 실험 단계 (5 phases)
1. Model Verification (Theorem 1, 2 검증)
2. Convergence Analysis
3. Performance Comparison (4 scenarios × 6 algorithms)
4. Ablation Study
5. Overhead Analysis

### 예상 출력 CSV: 22개 파일
