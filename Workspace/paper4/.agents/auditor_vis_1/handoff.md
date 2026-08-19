# Forensic Audit Report: Paper4 Visualizer & Evaluation Pipeline

**Work Product**: `/home/imnyj/Workspace/paper4/visualizer/` 및 관련 평가 데이터셋 (`/home/imnyj/Workspace/paper4/data/`)  
**Profile**: General Project / Integrity Forensics  
**Verdict**: **CLEAN**  

---

## 1. Observation (직접 관찰 결과)

### 1.1 타겟 산출물 11대 항목 (총 13개 파일) 전수 검사 결과
- `visualizer/ablation_study.pdf` (31,865 bytes): 구조 및 보상 어블레이션 2패널 벡터 그래프 (정상 생성)
- `visualizer/optuna_sensitivity_table.csv` (2,287 bytes): 17개 베이스라인 하이퍼파라미터 민감도 표 (17행 7열)
- `visualizer/optuna_sensitivity_table.tex` (3,319 bytes): LaTeX `table*` 포맷 및 `resizebox` 규격 준수
- `visualizer/reward_convergence.pdf` (30,727 bytes): 17개 베이스라인 100 에피소드 보상 수렴 곡선
- `visualizer/tsne_clustering.png` (227,405 bytes): 2359 x 1759 해상도, 300 DPI MoE 잠재 공간 클러스터링 산점도
- `visualizer/moe_routing.pdf` (17,093 bytes): 밀도별 전문가 3종 활성화 가중치 스택플롯
- `visualizer/cbr_trace.pdf` (34,778 bytes): 시계열 CBR 트레이스 및 $CBR_{\mathrm{target}}=0.60$ 기준선
- `visualizer/pdr_vs_density.pdf` (24,612 bytes): 차량 밀도별 PDR 성능 곡선 (17개 베이스라인)
- `visualizer/aoi_vs_density.pdf` (23,961 bytes): 차량 밀도별 AoI 지연 곡선 (17개 베이스라인)
- `visualizer/pdr_vs_distance.pdf` (24,674 bytes): 통신 거리별 PDR 곡선 (17개 베이스라인)
- `visualizer/aoi_vs_distance.pdf` (23,750 bytes): 통신 거리별 AoI 곡선 (17개 베이스라인)
- `visualizer/hardware_feasibility_table.csv` (1,159 bytes): MCU 연산량/지연시간/메모리 표 (11행 7열)
- `visualizer/hardware_feasibility_table.tex` (1,958 bytes): LaTeX `table*` 포맷 표

### 1.2 범례 순서 및 색상/알파 규격 (`evaluation_plan.md §2`) 전수 일치 확인
`visualizer/plot_utils.py` 및 `visualizer/generate_visualizations.py`에 정의된 17개 베이스라인 규격:
1. `REMO-DQN (Proposed)`: `#FF0000` (`alpha=1.0`, Bold, `zorder=20`)
2. `Fixed 10Hz`: `#0000FF` (`alpha=0.6`)
3. `ReactDCC (ETSI Standard)`: `#4D96FF` (`alpha=0.6`)
4. `AdaptDCC (ETSI Standard)`: `#2A4B7C` (`alpha=0.6`)
5. `MoEDQN`: `#9B5DE5` (`alpha=0.6`)
6. `MAPPO`: `#D783FF` (`alpha=0.6`)
7. `PPO`: `#7A49A5` (`alpha=0.6`)
8. `SAC`: `#00FF00` (`alpha=0.6`)
9. `DDPG`: `#6BCB77` (`alpha=0.6`)
10. `TD3`: `#2E8B57` (`alpha=0.6`)
11. `DuelingDQN`: `#FF9F1C` (`alpha=0.6`)
12. `DoubleDQN`: `#FFD166` (`alpha=0.6`)
13. `VanillaDQN`: `#D67229` (`alpha=0.6`)
14. `QLearning`: `#1A1A1A` (`alpha=0.6`)
15. `SARSA`: `#555555` (`alpha=0.6`)
16. `ActorCritic`: `#888888` (`alpha=0.6`)
17. `DecisionTransformer`: `#B5B5B5` (`alpha=0.6`)

### 1.3 구버전 파일 격리 확인 (`PROJECT.md §M2`)
- 기존 구버전 그래프 및 스크립트들이 `visualizer/backup/legacy_20260819_pre_critic/`로 완전 격리 보관됨.

---

## 2. Logic Chain (논리적 추론 체계)

1. **데이터 출처(Provenance) 추적**:
   - `data/models/`에 14개 RL 모델의 실제 가중치 파일(`.pth`/`.pkl`) 및 100 에피소드 수렴 로그(`*_convergence.csv`)가 실제 시뮬레이션 타임스탬프와 함께 존재함을 확인.
   - `data/optuna/`에 Optuna 베이지안 최적화 하이퍼파라미터 검색 결과(`all_best_params.json` 및 `best_params_*.csv`)가 저장되어 있음을 확인.
   - `prepare_data.py`가 이를 유기적으로 파싱하여 정합성을 유지함.

2. **정적 소스 코드 무결성 검증**:
   - `generate_visualizations.py`, `plot_figures.py`, `generate_tables.py`의 전수 정적 분석 결과:
     - 테스트 성공을 위해 리턴값을 조작하는 더미 함수(Facade) 없음.
     - 테스트 결과 문자열을 하드코딩한 부정 행위 없음.
     - 실제 `matplotlib`, `seaborn`, `pandas` 렌더링 파이프라인을 온전하게 수행함.

3. **동적 재현성(Dynamic Reproduction) 검증**:
   - 독립 실행 명령 `/home/imnyj/venv/bin/python3 /home/imnyj/Workspace/paper4/visualizer/plot_all.py` 및 `/home/imnyj/Workspace/paper4/etc/audit_vis_verifier.py`를 직접 실행한 결과:
     - 13개 산출물 전수가 0 byte 없이 100% 정상 재현 생성됨.
     - `tsne_clustering.png`의 경우 2359x1759 해상도(300 DPI)로 IEEE 학술지 게재 요건을 충족함.
     - LaTeX 테이블 구문 에러 없이 완전한 표 문법을 생성함.

---

## 3. Caveats (주의 사항 및 한계)

- 비RL 표준 기법(`Fixed 10Hz`, `ReactDCC`, `AdaptDCC`)의 경우 별도의 강화학습 훈련 단계가 존재하지 않으므로, 보상 수렴 곡선(`reward_convergence.csv`) 상에서 해당 기법들의 정상 상태(Steady-state) 고정 베이스라인으로 표현되었습니다. 이는 논문 시각화 표준상 적합한 처리입니다.
- MCU 하드웨어 프로파일링 표(`hardware_feasibility_table.csv`)의 Latency 및 FLOPs 수치는 ARM Cortex-M7/M4 및 STM32H7 기준의 이론적/실측 프로파일링 값에 기초합니다.

---

## 4. Conclusion (최종 판정)

- **최종 판정: CLEAN**
- 더미 구현, 하드코딩된 거짓 결과, 위조 산출물, 부정 행위(Cheating)가 일절 발견되지 않았습니다.
- `evaluation_plan.md` 및 `PROJECT.md`의 모든 시각화 규격(11개 타겟 산출물, 17개 베이스라인 범례 순서, 색상/투명도 코드, 300+ DPI 해상도, LaTeX 테이블)을 100% 충족함을 확인하였습니다.

---

## 5. Verification Method (독립 검증 방법)

독립적인 검증을 위해 아래 명령어를 실행하여 결과를 확인할 수 있습니다:

```bash
# 1. 시각화 마스터 파이프라인 동적 실행 검증
/home/imnyj/venv/bin/python3 /home/imnyj/Workspace/paper4/visualizer/plot_all.py

# 2. Forensic Integrity 전수 검사 스크립트 실행
/home/imnyj/venv/bin/python3 /home/imnyj/Workspace/paper4/etc/audit_vis_verifier.py
```

### 무효화 조건 (Invalidation Conditions)
- `visualizer/` 내 13개 산출물 중 누락되거나 0바이트 파일이 발생하는 경우.
- `plot_utils.py` 내 17개 베이스라인 순서 또는 색상 코드가 `evaluation_plan.md §2`와 불일치하는 경우.
