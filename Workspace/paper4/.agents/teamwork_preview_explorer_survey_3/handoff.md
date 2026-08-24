# Handoff Report — Explorer Survey 3 (Evaluation Sweep & Visualization Pipeline)

## 1. Observation (직접 관찰 결과)

### 1.1 하드웨어 및 CPU/GPU 자원
- `lscpu` 및 `python3 multiprocessing.cpu_count()` 확인:
  - CPU: Intel(R) Core(TM) i9-10900X CPU @ 3.70GHz, 10 Physical Cores, 20 Logical Threads (`os.cpu_count() == 20`)
  - RAM: 125 GiB (Free: 89 GiB, Available: 108 GiB)
  - GPU: 4x NVIDIA GeForce RTX 3090 (개당 24,576 MiB VRAM, 총 96 GB VRAM)

### 1.2 `visualizer/prepare_data.py` 내 Mock/Fake 데이터 코드 관찰
- `build_reward_convergence()`:
  - L98: `pad = [vals[-1] if len(vals) > 0 else -900000.0] * (episodes - len(vals))`
  - L108-113: `Fixed 10Hz: -995000.0`, `ReactDCC: -982000.0`, `AdaptDCC: -978000.0`
- `build_ablation_study()`:
  - L169-170: `cbr_term = -1.0 * (df_remo['CBR_mean'].values[:episodes] - 0.6).clip(min=0.0) * 2000.0`
  - L173-175: `moe_rew = remo_rew - 10000.0`, `duel_rew = remo_rew - 20000.0`, `dbl_rew = remo_rew - 30000.0`
  - L184-186: `w/o R1: remo_rew - aoi_term`, `w/o R2: remo_rew - cbr_term`, `w/o R3: remo_rew + 5000.0`
- `build_optuna_sensitivity()`:
  - L195-213: 17개 모델 전체에 대한 튜플 하드코딩 (`-850665.1, 96.22, 145.45, 0.584` 등)
- `build_tsne_clustering()`:
  - L276-281: `x: [i*0.1 for i in range(150)], y: [math.sin(i*0.1) for i in range(150)]`
- `build_moe_routing()`:
  - L299: `cbr_val = min(0.9, 0.05 + d * 0.007)`, `s_tensor = torch.tensor([[cbr_val, float(d), 0.5, 0.2, cbr_val]])`
  - L314-316: `Expert1: [88, 76, 58, 38, 20, 12, 6, 3, 2, 1, 1]`, `Expert2: [10, 20, 36, ...]`, `Expert3: [2, 4, 6, ...]`
- `build_density_metrics()`:
  - L381-382: `Delay_ms = df_eval['AoI_mean'] * 0.085 + (df_eval['CBR_mean'] * 12.0)`, `Fairness = np.clip(df_eval['ETSI_compliance'] / 100.0 * 0.96 + 0.02, 0.85, 0.99)`
- `build_distance_metrics()`:
  - L425-427: `prx = reception_probability(float(d)) * max(0.1, 1.0 - cbr * 0.8) * 100.0`, `aoi_val = aoi_base / max(0.01, prx / 100.0)`
- `build_hardware_feasibility()`:
  - L443-453: 정적 테이블 튜플 정의

### 1.3 `visualizer/generate_visualizations.py` 및 산출물 구조 관찰
- `generate_visualizations.py` 및 `plot_all.py` (L35-58) 확인:
  - 11개 대상 데이터셋 (1~11)과 22개 시각화/테이블 파일 (9개 플롯의 PNG 350 DPI + Vector PDF = 18개, 2개 테이블의 CSV + LaTeX TeX = 4개).
  - 17개 베이스라인 표준 컬러/선스타일/마커/범례 정렬 규칙 정의 (`BASELINES_SPEC`, L63-234).

### 1.4 기존 평가 스크립트 관찰
- `code/run_parallel_evaluation.py`: 16개 모델의 100 에피소드 수렴 훈련/평가 지원 (multiprocessing Pool, GPU 라운드로빈).
- `code/run_density_sweep_all.py`: 17개 모델 및 10개 밀도(5~50) 루프 스켈레톤 존재.
- `code/sim_engine.py` (L655-672): `cbr_history`, `distance_pdr` (6개 거리 버킷) 반환 로직 존재하나 `distance_aoi` 거리별 버킷 로직은 추가 필요.

---

## 2. Logic Chain (논리 전개 및 추론)

1. **[Observation 1.1 $\rightarrow$ 병렬성 설계]**: 20개 논리 스레드와 4개 RTX 3090 GPU가 가용하므로 `num_workers = 16`을 설정하고 `gpu_id = worker_idx % 4`로 분배하면 17,000 에피소드 스윕을 CPU/GPU 자원 병목 없이 고속 병렬 수행 가능함.
2. **[Observation 1.2 $\rightarrow$ 가짜 데이터 정화 필수성]**: `prepare_data.py` 전반에 오프셋, 인위적 수식, 하드코딩 튜플이 산재해 있으므로 이를 완전히 제거하지 않으면 논문 시각화에 가짜 수치가 반영되는 중대한 결함이 발생함.
3. **[Observation 1.3 $\rightarrow$ 시각화 22종 파이프라인 규격]**: `generate_visualizations.py`와 `plot_all.py`의 11개 대상 데이터셋 매핑 및 350 DPI PNG + PDF 렌더링 규격이 이미 완비되어 있으므로, `prepare_data.py`가 100% 실측 시뮬레이션 결과 파일만을 읽어 `data/*.csv`로 집계하도록 연결해야 함.
4. **[Observation 1.4 $\rightarrow$ 시뮬레이션 엔진 및 스윕 연동]**: `sim_engine.py`의 `SimulationRunner` 및 `aoi_tracker.py`에 거리별 AoI 측정 로직을 보강하고, `run_density_sweep_parallel.py`를 구현하여 17,000 에피소드 실행 시 `eval_density_results.csv`, `distance_pdr.json`, `distance_aoi.json`, `cbr_trace.json`, `tsne_data.json`, `moe_routing.json`을 직접 생성해야 함.

---

## 3. Caveats (주의사항 및 한계)

- **Ablation 모델 학습 로그 필요성**: `ablation_study.csv`를 순수 실측치로 구성하기 위해서는 구조적 소거(w/o ResNet, w/o MoE, w/o Dueling) 및 보상 소거(w/o R1, w/o R2, w/o R3) 모델의 훈련 로그가 `data/ablation_structure/` 및 `data/ablation_reward/`에 정상적으로 존재해야 함.
- **t-SNE 및 MoE 라우팅 추출**: 학습 완료된 `REMO-DQN.pth` 체크포인트를 로드하여 실제 평가 시뮬레이션 중의 상태 벡터를 forward pass하여 추출해야 함.

---

## 4. Conclusion (최종 결론)

1. `visualizer/prepare_data.py`의 모든 하드코딩 및 합성 수식 지점(9개 함수)이 정확히 식별되었으며, 전면 정화 및 실측 파일 파싱 로직으로 대체되어야 함.
2. 17,000 에피소드 병렬 평가를 위해 16워커 / 4 GPU 기반의 `run_density_sweep_parallel.py` 아키텍처 및 6대 실측 데이터 JSON/CSV 스키마가 완벽히 규격화됨.
3. 22개 시각화/테이블 산출물(11개 데이터셋)의 생성 명세와 350 DPI 요구사항 검증 체계가 확립됨.

---

## 5. Verification Method (독립 검증 방법)

1. **하드웨어 사양 검증**:
   ```bash
   nproc
   python3 -c "import os; print(os.cpu_count())"
   nvidia-smi
   ```
2. **`prepare_data.py` mock/fake 잔존 검증**:
   ```bash
   grep -rn "np.random" /home/imnyj/Workspace/paper4/visualizer/prepare_data.py
   grep -rn "math.sin" /home/imnyj/Workspace/paper4/visualizer/prepare_data.py
   grep -rn "\-900000" /home/imnyj/Workspace/paper4/visualizer/prepare_data.py
   ```
3. **시각화 산출물 생성 및 350 DPI 검증**:
   ```bash
   python3 /home/imnyj/Workspace/paper4/visualizer/plot_all.py
   ```
