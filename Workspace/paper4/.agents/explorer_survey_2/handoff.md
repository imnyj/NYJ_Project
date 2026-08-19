# Visualizer 작업공간 현황 조사 및 백업 격리 대상 정의 보고서

**작성자**: Visualizer Workspace Explorer (`explorer_survey_2`)  
**대상 디렉토리**: `/home/imnyj/Workspace/paper4/visualizer/`  
**상위 보고 대상**: Orchestrator (`parent`, ID: `35416a47-4347-4d2b-b546-6cffd40c5bfe`)

---

## 1. 관측 결과 (Observation)

`/home/imnyj/Workspace/paper4/visualizer/` 디렉토리에 대한 전수 조사를 실시하였으며, 관측된 파일 목록 및 속성은 다음과 같습니다.

### 1.1 `visualizer/` 루트 파일 전수 목록 (총 20개 파일, 2개 디렉토리)

| 파일/디렉토리명 | 유형 | 크기 (Bytes) | 최종 수정일시 | 파일 목적 및 현 상태 |
|---|---|---|---|---|
| `evaluation_plan.md` | Markdown 문서 | 4,783 | 2026-08-19 16:36 | **최신 활성 시각화/평가 계획서** (11개 타깃 결과물, 17개 모델 범례/색상 정의) |
| `prompt.md` | Markdown 문서 | 3,067 | 2026-08-19 16:32 | Coder-Critic 워크플로우 및 시뮬레이션 지침 |
| `config.md` | Markdown 문서 | 2,583 | 2026-08-03 11:26 | **구버전 설정 파일** (16개 구 모델 목록 정의, 최신 `evaluation_plan.md`와 불일치) |
| `plot_all.py` | Python 스크립트 | 8,771 | 2026-08-05 13:34 | **구버전 일괄 플롯 스크립트** (`config.md` 기반 9개 그래프 일괄 렌더링) |
| `plot_utils.py` | Python 스크립트 | 2,280 | 2026-08-07 14:53 | **구버전 플롯 스타일 유틸리티** (구 16개 모델 스타일 맵) |
| `plot_convergence.py` | Python 스크립트 | 1,102 | 2026-08-07 14:49 | **구버전 스크립트** (`code/train_log.csv` 대상 플롯) |
| `plot_line_density.py` | Python 스크립트 | 1,515 | 2026-08-07 14:49 | **구버전 스크립트** (`papers/paper4/paper/data/SA1_results.csv` 대상) |
| `plot_cbr_cdf.py` | Python 스크립트 | 1,683 | 2026-08-07 14:49 | **구버전 스크립트** (`SA1_arrays.json` 대상 CDF 플롯) |
| `plot_pdr_distance.py` | Python 스크립트 | 1,528 | 2026-08-07 14:49 | **구버전 스크립트** (`SA1_arrays.json` 대상 PDR-Distance 플롯) |
| `1_reward_convergence.png` | PNG 이미지 | 50,437 | 2026-08-05 13:34 | **구버전 생성 그래프** |
| `2_ablation_study.png` | PNG 이미지 | 55,259 | 2026-08-05 13:34 | **구버전 생성 그래프** |
| `3_moe_routing.png` | PNG 이미지 | 38,427 | 2026-08-05 13:34 | **구버전 생성 그래프** |
| `4_tsne_clustering.png` | PNG 이미지 | 26,060 | 2026-08-05 13:34 | **구버전 생성 그래프** |
| `5_hardware_feasibility.png` | PNG 이미지 | 22,407 | 2026-08-05 13:34 | **구버전 생성 테이블 이미지** |
| `7_cbr_trace.png` | PNG 이미지 | 86,380 | 2026-08-05 13:34 | **구버전 생성 그래프** |
| `8_pdr_vs_density.png` | PNG 이미지 | 29,703 | 2026-08-05 13:34 | **구버전 생성 그래프** |
| `9_aoi_vs_density.png` | PNG 이미지 | 41,842 | 2026-08-05 13:34 | **구버전 생성 그래프** |
| `10_pdr_vs_distance.png` | PNG 이미지 | 41,345 | 2026-08-05 13:34 | **구버전 생성 그래프** |
| `convergence.png` | PNG 이미지 | 497,384 | 2026-08-07 14:48 | **구버전 생성 그래프** |
| `line_density.png` | PNG 이미지 | 248,330 | 2026-08-07 14:48 | **구버전 생성 그래프** |
| `backup/` | 디렉토리 | 4,096 | 2026-08-05 13:19 | 기존 백업 루트 디렉토리 (하위 2개 서브디렉토리 보유) |
| `__pycache__/` | 디렉토리 | 4,096 | 2026-08-07 14:54 | 파이썬 캐시 (`plot_utils.cpython-312.pyc` 포함) |

### 1.2 `visualizer/backup/` 내부 현황

- `backup/2026-08-05_1319/`: 2026년 8월 5일에 백업된 9개 PNG 파일 보관 (`1_reward_convergence.png`, `2_ablation_study.png`, `3_moe_routing.png`, `4_tsne_clustering.png`, `5_hardware_feasibility.png`, `7_cbr_trace.png`, `8_pdr_vs_density.png`, `9_aoi_vs_density.png`, `10_pdr_vs_distance.png`)
- `backup/TinyMLP/`: 2026년 8월 3일에 백업된 TinyMLP 비교 실험 구버전 그래프 총 27개 PNG 파일 보관

---

## 2. 논리적 분석 및 추론 체계 (Logic Chain)

1. **요구사항 규정 (`ORIGINAL_REQUEST.md` R3 및 `GEMINI.md` Rule 5)**:
   - "Move any pre-existing "old" graph images or outdated visualization files currently inside the `visualizer/` directory into a newly created `visualizer/backup/` directory. The main `visualizer/` directory should only contain the fresh, Critic-approved outputs and the scripts used to generate them."
   - "결과물 저장 공간에는 항상 최신 파일만 유지하며, 모든 이전 버전의 파일은 `backup/` 디렉토리로 안전하게 자동 분리 격리 관리되도록 한다."

2. **최신 스펙 대비 구버전 파일 식별**:
   - `evaluation_plan.md`(2026-08-19 16:36 작성)는 17개 베이스라인/제안 모델의 새로운 범례 순서, 색상 코드(#FF0000, #0000FF, #4D96FF, ...) 및 11개 타깃 결과물(PDF, PNG, CSV/TeX)을 지정함.
   - 반면 현재 `visualizer/` 루트에 존재하는 11개 PNG 이미지(`1_*.png` ~ `10_*.png`, `convergence.png`, `line_density.png`)는 8월 5일 및 8월 7일에 구버전 스크립트에 의해 생성된 파일로, 최신 17개 모델 색상 맵 및 포맷 가이드라인(PDF/PNG)과 일치하지 않음.
   - `config.md`는 8월 3일자 16개 모델 설정으로 최신 `evaluation_plan.md`와 상이하여 향후 혼선을 초래할 위험이 있음.
   - `plot_all.py`, `plot_utils.py`, `plot_convergence.py`, `plot_line_density.py`, `plot_cbr_cdf.py`, `plot_pdr_distance.py` 등 6개 스크립트는 구버전 데이터 경로 및 구 설정을 참조하고 있으므로, 새로운 Coder 에이전트가 최신 `evaluation_plan.md` 기반으로 작성할 스크립트와 격리되어야 함.

3. **작업공간 분리/격리 기준 정의**:
   - **유지 대상 (Retain)**: 최신 기획 및 요구사항 문서 (`evaluation_plan.md`, `prompt.md`), 백업 폴더 (`backup/`)
   - **격리 대상 (Quarantine to Backup)**:
     - 구버전 이미지 11종
     - 구버전 파이썬 스크립트 6종
     - 구버전 설정 문서 1종 (`config.md`)
     - 빌드 캐시 `__pycache__/` (삭제 또는 etc 격리)

---

## 3. 주의사항 및 한계 (Caveats)

1. **Read-Only 조사 제약**: 본 에이전트는 Explorer로서 읽기 전용 권한을 준수하여 실제 파일 이동/삭제 명령은 수행하지 않았습니다. 실제 파일 이동 작업은 Orchestrator 또는 후속 이동 작업 담당 에이전트가 수행해야 합니다.
2. **백업 디렉토리 네이밍 제안**: 기존 `backup/` 내에 이미 `2026-08-05_1319`와 `TinyMLP`가 존재하므로, 이번 격리 작업은 충돌 방지를 위해 `visualizer/backup/legacy_20260819_pre_critic/` 하위 디렉토리를 생성하여 보관하는 것을 권장합니다.

---

## 4. 결론 및 격리 대상 정의 (Conclusion)

### 4.1 유지 대상 목록 (Keep in `visualizer/`)
1. `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md` (최신 평가/시각화 기준 문서)
2. `/home/imnyj/Workspace/paper4/visualizer/prompt.md` (프롬프트 요구사항)
3. `/home/imnyj/Workspace/paper4/visualizer/backup/` (백업 저장소)

### 4.2 백업 격리 대상 목록 (Move to `visualizer/backup/legacy_20260819_pre_critic/`)
총 **18개 파일 + 1개 캐시 디렉토리**:

#### [A] 구버전 이미지 파일 (11개)
1. `/home/imnyj/Workspace/paper4/visualizer/1_reward_convergence.png`
2. `/home/imnyj/Workspace/paper4/visualizer/2_ablation_study.png`
3. `/home/imnyj/Workspace/paper4/visualizer/3_moe_routing.png`
4. `/home/imnyj/Workspace/paper4/visualizer/4_tsne_clustering.png`
5. `/home/imnyj/Workspace/paper4/visualizer/5_hardware_feasibility.png`
6. `/home/imnyj/Workspace/paper4/visualizer/7_cbr_trace.png`
7. `/home/imnyj/Workspace/paper4/visualizer/8_pdr_vs_density.png`
8. `/home/imnyj/Workspace/paper4/visualizer/9_aoi_vs_density.png`
9. `/home/imnyj/Workspace/paper4/visualizer/10_pdr_vs_distance.png`
10. `/home/imnyj/Workspace/paper4/visualizer/convergence.png`
11. `/home/imnyj/Workspace/paper4/visualizer/line_density.png`

#### [B] 구버전 스크립트 파일 (6개)
12. `/home/imnyj/Workspace/paper4/visualizer/plot_all.py`
13. `/home/imnyj/Workspace/paper4/visualizer/plot_utils.py`
14. `/home/imnyj/Workspace/paper4/visualizer/plot_convergence.py`
15. `/home/imnyj/Workspace/paper4/visualizer/plot_line_density.py`
16. `/home/imnyj/Workspace/paper4/visualizer/plot_cbr_cdf.py`
17. `/home/imnyj/Workspace/paper4/visualizer/plot_pdr_distance.py`

#### [C] 구버전 설정 문서 (1개)
18. `/home/imnyj/Workspace/paper4/visualizer/config.md`

#### [D] 임시 캐시 디렉토리
19. `/home/imnyj/Workspace/paper4/visualizer/__pycache__/` (삭제 권장)

---

## 5. 독립적 검증 방법 (Verification Method)

후속 작업자가 본 조사 결과를 검증하고 격리를 실행할 수 있는 명령어는 다음과 같습니다:

1. **파일 목록 및 격리 대상 확인**:
   ```bash
   ls -la /home/imnyj/Workspace/paper4/visualizer
   ```
2. **권장 백업 이동 실행 명령 (참고용)**:
   ```bash
   mkdir -p /home/imnyj/Workspace/paper4/visualizer/backup/legacy_20260819_pre_critic
   mv /home/imnyj/Workspace/paper4/visualizer/*.png /home/imnyj/Workspace/paper4/visualizer/backup/legacy_20260819_pre_critic/
   mv /home/imnyj/Workspace/paper4/visualizer/plot_*.py /home/imnyj/Workspace/paper4/visualizer/backup/legacy_20260819_pre_critic/
   mv /home/imnyj/Workspace/paper4/visualizer/config.md /home/imnyj/Workspace/paper4/visualizer/backup/legacy_20260819_pre_critic/
   rm -rf /home/imnyj/Workspace/paper4/visualizer/__pycache__
   ```
3. **격리 후 상태 검증**:
   - `ls /home/imnyj/Workspace/paper4/visualizer` 실행 시 `evaluation_plan.md`, `prompt.md`, `backup/` 디렉토리만 남아있는지 확인.
