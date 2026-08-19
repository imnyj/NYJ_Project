# Paper4 Lead Visualization Critic & Reviewer 심사 보고서 (R2 Critic Audit)

## 1. Observation (직접 관찰 사실)

### 1.1 11대 타겟 산출물(총 13개 파일) 물리적 무결성 검증
`/home/imnyj/Workspace/paper4/visualizer/` 디렉토리에 대해 `plot_all.py` 실행 및 파일 전수 검사를 수행하여 다음 13개 산출물의 생성 여부와 크기, 무결성을 확인했습니다.

| Target No. | File Name | Format | Size (KB) | Status | Description |
|---|---|---|---|---|---|
| Target 1 | `ablation_study.pdf` | Vector PDF | 31.1 KB | PASS | (a) 구조적 절제 (REMO-DQN, w/o ResNet, w/o MoE, w/o Dueling) 및 (b) 보상 함수 절제 ($R_{full}$, w/o $R_1$, w/o $R_2$, w/o $R_3$) 서브플롯 구성 완료. |
| Target 2 | `optuna_sensitivity_table.csv` | CSV Data | 2.2 KB | PASS | 17개 비교군 전체의 최적 하이퍼파라미터 벡터 및 다차원 성능 메트릭 (Reward, PDR, AoI, CBR) 데이터셋. |
| Target 2 | `optuna_sensitivity_table.tex` | LaTeX Table | 3.2 KB | PASS | IEEE TWC 포맷의 2열 테이블(`table*`), `resizebox`, `booktabs`, REMO-DQN `\textbf{}` 볼드 강조 적용. |
| Target 3 | `reward_convergence.pdf` | Vector PDF | 30.0 KB | PASS | 17개 비교군 전체의 에피소드 진행에 따른 누적 보상 수렴 곡선. REMO-DQN 빨간 실선 강조. |
| Target 4 | `tsne_clustering.png` | Raster PNG | 222.1 KB | PASS | 300 DPI 고해상도, 3개 밀도 레짐(Low/Med/High Traffic) 및 전문가(Expert 1, 2, 3) 라우팅 군집 시각화. |
| Target 5 | `moe_routing.pdf` | Vector PDF | 16.7 KB | PASS | 트래픽 밀도(20~160 veh/km) 증가에 따른 3개 MoE Expert의 동적 활성화 가중치(%) 전환 Stackplot. |
| Target 6 | `cbr_trace.pdf` | Vector PDF | 34.0 KB | PASS | 17개 비교군 시계열 CBR 요동 폭 및 ETSI DCC Target CBR ($0.60$) 기준선 명시. |
| Target 7 | `pdr_vs_density.pdf` | Vector PDF | 24.0 KB | PASS | 차량 밀도(10~120 veh/km) 대비 17개 비교군의 패킷 전송 성공률(PDR) 방어 성능 비교. |
| Target 8 | `aoi_vs_density.pdf` | Vector PDF | 23.4 KB | PASS | 차량 밀도(10~120 veh/km) 대비 17개 비교군의 정보 연령(AoI) 최신성 비교 (Fixed 10Hz 폭증 및 REMO-DQN 최저 AoI). |
| Target 9 | `pdr_vs_distance.pdf` | Vector PDF | 24.1 KB | PASS | 통신 거리(0~300m) 대비 17개 비교군의 PDR 감쇄 곡선 및 마커 시각화. |
| Target 10 | `aoi_vs_distance.pdf` | Vector PDF | 23.2 KB | PASS | 통신 거리(0~300m) 대비 17개 비교군의 AoI 지연 곡선 및 마커 시각화. |
| Target 11 | `hardware_feasibility_table.csv` | CSV Data | 1.1 KB | PASS | 11개 주요 아키텍처별 MACs/FLOPs, 파라미터 수, 추론 지연시간(ms), 메모리 점유량(KB), MCU 적합성 데이터. |
| Target 11 | `hardware_feasibility_table.tex` | LaTeX Table | 1.9 KB | PASS | IEEE TWC 포맷의 2열 테이블(`table*`), `resizebox`, `booktabs`, REMO-DQN `\textbf{}` 볼드 강조 적용. |

### 1.2 `evaluation_plan.md §2` 17개 비교군 스타일 규격 1:1 전수 대조 결과
`visualizer/plot_utils.py`의 `MODEL_CONFIGS` 및 `apply_ordered_legend()` 함수 구현을 계획서와 전수 대조한 결과입니다:

| No | Baseline Model | Plan Color | Code Color | Plan Alpha | Code Alpha | Plan Style | Code Style & Linewidth | Z-Order | Verification |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **REMO-DQN (Proposed)** | `#FF0000` | `#FF0000` | `1.0` | `1.0` | Bold | `-`, `2.4` (Bold) | `20` (최상단) | **PASS** |
| 2 | **Fixed 10Hz** | `#0000FF` | `#0000FF` | `0.6` | `0.6` | `--` | `--`, `1.6` | `5` | **PASS** |
| 3 | **ReactDCC (ETSI Standard)** | `#4D96FF` | `#4D96FF` | `0.6` | `0.6` | `-.` | `-.`, `1.6` | `6` | **PASS** |
| 4 | **AdaptDCC (ETSI Standard)** | `#2A4B7C` | `#2A4B7C` | `0.6` | `0.6` | `:` | `:`, `1.6` | `7` | **PASS** |
| 5 | **MoEDQN** | `#9B5DE5` | `#9B5DE5` | `0.6` | `0.6` | `-` | `-`, `1.6` | `8` | **PASS** |
| 6 | **MAPPO** | `#D783FF` | `#D783FF` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 7 | **PPO** | `#7A49A5` | `#7A49A5` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 8 | **SAC** | `#00FF00` | `#00FF00` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 9 | **DDPG** | `#6BCB77` | `#6BCB77` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 10 | **TD3** | `#2E8B57` | `#2E8B57` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 11 | **DuelingDQN** | `#FF9F1C` | `#FF9F1C` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 12 | **DoubleDQN** | `#FFD166` | `#FFD166` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 13 | **VanillaDQN** | `#D67229` | `#D67229` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 14 | **QLearning** | `#1A1A1A` | `#1A1A1A` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 15 | **SARSA** | `#555555` | `#555555` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 16 | **ActorCritic** | `#888888` | `#888888` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |
| 17 | **DecisionTransformer** | `#B5B5B5` | `#B5B5B5` | `0.6` | `0.6` | `-` | `-`, `1.5` | `8` | **PASS** |

### 1.3 백업 격리 상태 확인
- `visualizer/backup/legacy_20260819_pre_critic/` (18개 파일 정상 격리)
- `visualizer/backup/2026-08-05_1319/` (9개 파일 정상 격리)
- `visualizer/backup/TinyMLP/` (26개 파일 정상 격리)
- `visualizer/` 루트에는 최신 산출물 13개 및 핵심 파이프라인 스크립트만 정돈되어 있음.

---

## 2. Logic Chain (추론 체계)

1. **완전성 검증**: 요구사항 및 `evaluation_plan.md §3`에 정의된 11대 타겟(그래프 8종 PDF + t-SNE 1종 PNG + 테이블 2종 CSV/TeX = 총 13개 산출물)이 모두 정상 생성되어 0바이트 빈 파일 없이 온전한 크기(최소 1.1 KB ~ 최대 222.1 KB)를 가지고 있음을 확인했습니다.
2. **규격 준수성 검증**: `evaluation_plan.md §2`의 17대 비교군 순서, Hex 코드, 라인 스타일, alpha 투명도, 선 두께(REMO-DQN 강조)가 `plot_utils.py` 및 모든 시각화 스크립트에서 단 하나의 오차도 없이 1:1로 매핑됨을 대조했습니다.
3. **가독성 및 레이아웃 검증**: 모든 그래프에서 범례 정렬 함수 `apply_ordered_legend()`가 적용되어 계획서에 정의된 1~17번 순서대로 2열 범례가 정확히 배치되었으며, REMO-DQN이 zorder=20으로 최상단에 렌더링되어 다른 16개 비교군과 명확히 구분됩니다.
4. **저널 적합성 검증**: 벡터 PDF 포맷 및 Type 42 TrueType 폰트 임베딩(`pdf.fonttype=42`), 300 DPI 래스터 출력, LaTeX `booktabs` 및 `resizebox` 규격이 완벽히 적용되어 IEEE Transactions 저널 투고 수준을 충족합니다.
5. **재현성 검증**: `python3 /home/imnyj/Workspace/paper4/visualizer/plot_all.py` 단일 명령으로 2.82초 내에 데이터 정합성 검증부터 13개 전체 산출물 빌드가 완벽히 재현되었습니다.

---

## 3. Caveats (한계 및 가정)

- **데이터 기반**: 본 시각화 산출물은 `data/` 및 `coder/data/`에 동기화된 시뮬레이션 및 Optuna 베이지안 최적화 결과를 토대로 생성되었으며, 논문 집필 에이전트(Writer)는 해당 CSV 및 TeX 테이블의 수치를 그대로 인용하여 본문을 서술해야 합니다.
- **추가 수정 불가**: 현재 시각화 결과물은 모든 규격을 완벽히 충족하므로, Coder의 추가적인 수정 없이 즉시 논문 집필 단계로 진행할 수 있습니다.

---

## 4. Conclusion (심사 판정 및 결론)

- **최종 판정**: **`APPROVE` (최종 승인)**
- **평가 요약**:
  - 11대 타겟(13개 산출물) 전수 생성 완료 (100% 무결성)
  - `evaluation_plan.md §2` 17개 비교군 스타일/순서 규격 1:1 전수 일치 (100% 규격 준수)
  - `visualizer/backup/` 구버전 파일 완전 격리 확인 (100% 정리 준수)
  - 파이프라인 단일 실행 재현성 검증 통과 (100% 재현성)

---

## 5. Verification Method (독립적 재검증 방법)

독립적인 검증을 수행하려면 터미널에서 다음 명령어를 실행하십시오:

```bash
# 1. 시각화 전체 파이프라인 재실행 및 13개 산출물 무결성 리포트 확인
python3 /home/imnyj/Workspace/paper4/visualizer/plot_all.py

# 2. 13개 산출물 존재 및 파일 크기 확인
ls -la /home/imnyj/Workspace/paper4/visualizer/*.pdf /home/imnyj/Workspace/paper4/visualizer/*.png /home/imnyj/Workspace/paper4/visualizer/*.csv /home/imnyj/Workspace/paper4/visualizer/*.tex

# 3. 백업 디렉토리 격리 상태 확인
ls -la /home/imnyj/Workspace/paper4/visualizer/backup/
```
