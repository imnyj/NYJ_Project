# 파일 구조

작성 2026-08-30 · 대상: `Workspace/paper4`
짝 문서: `STRUCTURE_CODE.md` (파일 **안**의 구현 구조)

이 문서는 **어떤 파일이 어디에 있고 무엇을 담당하는가**만 다룬다.
파일 안의 클래스·함수 구조는 짝 문서를 볼 것.

---

## 1. 최상위

```
Workspace/paper4/
├── coder/          ★ 시뮬레이션 코드 전부
├── idea/           설계 문서 (여기서 시작)
├── critic/         코드 검토 보고서
├── review/         감사 기록
├── librarian/      문헌 조사 (baseline 9종 DOI 검증)
├── writer/         논문 원고 (main.tex)
├── logs/           세션별 실행 기록
├── backup/         프로젝트 수준 백업
├── data/ visualizer/ .agents/ .rules/
│
├── CODE_GUIDE.md         코드 안내서 + 결함 목록
├── STRUCTURE_FILES.md    ← 이 문서
├── STRUCTURE_CODE.md     구현 구조 (짝 문서)
├── simulation_plan.md    실행 계획
├── Conversation.md       사용자 승인 확정본 (설계 ground truth)
└── Prompt.md             인용 형식 규칙
```

### 문서를 읽는 순서

| 순서 | 파일 | 무엇을 알 수 있나 |
|---|---|---|
| 1 | `idea/scenario.md` | 사용자 원안. 무엇을 하려는 연구인가 |
| 2 | `idea/design_spec_v2.md` | **설계 확정본.** State/Action/Reward/SMDP 전이 |
| 3 | `Conversation.md` | 승인 이력과 baseline 9종의 문헌 근거 |
| 4 | `CODE_GUIDE.md` | 코드 안내 + 발견된 결함 |
| 5 | `STRUCTURE_CODE.md` | 클래스·함수 단위 구현 |

---

## 2. `coder/` — 시뮬레이션 코드

```
coder/
├── run_all.py                    훈련 진입점 (87줄)
│
├── src/
│   ├── rl_interface.py           상태·액션·버퍼의 정본 (754줄)
│   ├── hot_swap_trainer.py       ★ 환경·스케줄러·훈련루프 (2095줄)
│   ├── Communications.py         802.11p 물리계층 (411줄)
│   ├── dynamics_predictor.py     신호등·차량 동역학 피처 (410줄)
│   ├── heuristic_scheduler.py    규칙 기반 스케줄러 (185줄)
│   ├── evaluate.py               벤치마크 평가 (417줄)
│   ├── hpo.py                    Optuna 하이퍼파라미터 탐색 (630줄)
│   │
│   ├── sumo/
│   │   ├── make_sumo_set.py      격자망·차량흐름·신호등 생성 (502줄)
│   │   └── generated.*.xml       생성된 SUMO 파일 7종 (자동 생성물)
│   │
│   └── baselines/                비교 방안 9종 (3740줄)
│       ├── __init__.py           레지스트리 — 이름↔클래스의 정본
│       ├── base_agent.py         공통 인터페이스
│       ├── sb3_wrapper.py        Stable-Baselines3 하이브리드 액션 래퍼
│       ├── sb3_ppo.py  sb3_sac.py  sb3_td3.py          기본 3종
│       ├── res_mapddpg.py  ma2hdqn.py  i_hamappo.py    최신 3종
│       └── spam_d3qn.py  carlton.py  maddpg_mt.py      유사 3종
│
├── tests/                        pytest 110개
├── etc/scripts/                  검증 스크립트 9종
├── checkpoints/  logs/           산출물 (본훈련 전 비어 있어야 정상)
└── backup/                       코드 백업·격리
```

**전체 9,231줄.** 절반 가까이(2,095줄)가 `hot_swap_trainer.py` 하나에 있다.

---

## 3. 파일별 역할

### 3-1. 실행 경로 (훈련을 걸면 실제로 도는 것)

| 파일 | 역할 | 이것이 없으면 |
|---|---|---|
| `run_all.py` | 모델 이름을 받아 훈련을 건다 | 진입점이 없다 |
| `hot_swap_trainer.py` | SUMO를 굴리고, 관측을 만들고, 보상을 매기고, 학습을 돌린다 | 아무것도 안 돈다 |
| `rl_interface.py` | 상태 17차원·액션 3축·SMDP 버퍼를 정의 | 모델이 무엇을 보고 무엇을 내는지 정의되지 않는다 |
| `Communications.py` | 전송 성공/실패를 물리로 판정 | 통신이 항상 성공한다 |
| `dynamics_predictor.py` | 신호등 상태·앞차·정지 임박을 TraCI에서 추출 | 정지 추론의 근거가 사라진다 |
| `sumo/make_sumo_set.py` | 도로망과 교통 수요를 만든다 | 굴릴 도로가 없다 |
| `baselines/` | 비교 방안 9종 | 비교 대상이 없다 |

### 3-2. 훈련 이후 단계

| 파일 | 역할 | 비고 |
|---|---|---|
| `evaluate.py` | 밀도 5종 × 시드 5종 벤치마크 | 2026-08-30에 레지스트리 연결 복구 |
| `hpo.py` | Optuna 20 trial 하이퍼파라미터 탐색 | 같은 날 탐색공간 재작성 |
| `heuristic_scheduler.py` | 규칙 기반 비교군 | 평가에서만 쓰임 |

### 3-3. 검증 스크립트 (`etc/scripts/`)

| 스크립트 | 무엇을 검증 |
|---|---|
| `verify_model_input_liveness.py` | **모델이 실제로 받는** 17차원이 전부 살아 있는가 |
| `verify_all_baselines.py` | 9종이 액션 범위·계약을 지키는가 |
| `verify_phy_802_11p.py` | 물리 수식이 802.11p 규격과 맞는가 |
| `verify_bibliography.py` | 인용이 Crossref와 대조되는가 |
| `measure_hw_feasibility.py` | Act/Rest 핫스왑의 추론 지연 |
| `verify_sumo_gen_lock.py` | 동시 실행 시 SUMO 파일 생성 락 |
| `verify_n_queue_live.py` | n_queue 피처가 실제로 변하는가 |
| `verify_observation_liveness.py` | (구) 환경 반환 관측의 liveness |
| `verify_sb3_baselines.py` | SB3 3종의 래퍼 계약 |

`verify_observation_liveness.py`는 `env.step()`이 **반환하는** 벡터를 본다.
그 벡터는 살아 있었으나 모델에게 가지 않았고, 그래서 18차원 중 15개가 상수인 것을 놓쳤다.
`verify_model_input_liveness.py`가 그 교훈으로 만들어진 후속이며 **추론 함수의 인자**를 잰다.

### 3-4. 격리된 파일 (`coder/backup/unused_20260830_172551/`)

import 그래프를 실측해 현재 파이프라인이 전혀 쓰지 않는 것만 옮겼다.

| 파일 | 정체 | 왜 안 쓰이나 |
|---|---|---|
| `8. V2V Precaching.py` | 다른 논문 예제 | 이 프로젝트와 무관 |
| `src/model.py` | TensorFlow/Keras PPO | 실제 구현은 PyTorch. import 0건 |
| `src/aoi_env.py` | 초기 환경 클래스 | 감사는 받았으나 **실행 경로가 아니었다.** D1에서 폐기 확정 |
| `src/NetSim.py` | 초기 SUMO 래퍼 | `aoi_env.py` 전용. libsumo 직접 호출 방식으로 대체됨 |
| `verify_environment.py` | `aoi_env.py` 전용 검증 | 대상이 폐기됨 |
| `tests/test_aoi_env_genuine.py` | 위 클래스 검증 11개 | 동상 |
| `tests/test_tier4_simulation.py` | 위 클래스 검증 3개 | 동상 |
| `etc/scripts/test_adversarial_suite.py` | 위 클래스 스트레스 테스트 | 동상 |

> `NetSim.py`를 되살릴 일이 있다면 주의할 것: `pre_define()`이 `make_sumo_set`의
> 전역 상수(RSU_RANGE 등)를 덮어쓴다. 실수로 import하면 정본이 오염된다.

---

## 4. 산출물 디렉토리

| 경로 | 내용 | 주의 |
|---|---|---|
| `coder/checkpoints/` | `{모델}_ep###.pt`, `{모델}_best.pt` | **본훈련 시작 전 비어 있어야 한다.** 남아 있으면 `--no-resume` 없이 재개된다 |
| `coder/logs/training/` | `{모델}_progress.csv` 에피소드별 지표 | 동상 |
| `coder/logs/tensorboard/` | 학습 곡선 | `tensorboard --logdir` 로 확인 |
| `coder/src/sumo/generated.*` | SUMO XML 7종 | 자동 생성. 파라미터가 바뀌면 재생성됨 |
| `coder/backup/` | 백업·격리 | 날짜별 디렉토리 |

`checkpoints/`와 `logs/training/`이 비어 있는지가 재현성의 전제다.
스모크 테스트나 처리량 측정 후에는 반드시 `backup/`으로 격리한다.

---

## 5. 데이터·설정의 정본이 어디에 있는가

같은 값을 두 곳에 쓰지 않는다. 아래가 각 값의 **유일한 출처**다.

| 값 | 정본 | 유도 방식 |
|---|---|---|
| 상태 벡터 폭 (17) | `rl_interface.STATE_DIM` | 상수 |
| Δ 범위 [0.1, 45] s | `rl_interface.DELTA_MIN` / `DELTA_MAX` | 상한은 net.xml의 실제 적색 시간에서 추출 |
| 전력 범위 [10, 23] dBm | `rl_interface.P_MIN` / `P_MAX` | 3GPP power-class-3 |
| 시나리오 제한속도 | `rl_interface.V_LIMIT` | net.xml의 최대 차선 속도에서 추출 |
| 오차 정규화 기준 `E_REF` | `rl_interface.E_REF` | `V_LIMIT × 1초` |
| RSU 반경 300 m | `make_sumo_set.RSU_RANGE` | 상수. `rl_interface`가 재수출 |
| 서브채널 4개 | `Communications.NUM_SUBCHANNELS` | 802.11p 10 MHz × 4 |
| baseline 이름↔클래스 | `baselines/__init__.py::BASELINE_REGISTRY` | 상수 |
| 보상 가중치 w1~w4 | 환경 생성자 (Optuna 탐색 대상) | `hpo.py`가 샘플 |

> [!IMPORTANT]
> **리터럴을 새로 쓰지 말 것.** 이 프로젝트에서 반복적으로 결함을 만든 원인이다.
> 테스트 15개 파일이 `18`을 박아둬서 상태 차원 축소 시 17건이 깨졌고,
> 실행 계획서가 CSV 컬럼 번호를 박아둬서 지표 추가 후 엉뚱한 열을 읽고 있었고,
> `evaluate.py`·`hpo.py`가 baseline 이름을 박아둬서 9종을 하나도 못 돌렸다.
> 세 건 모두 정본이 바뀌었는데 사본이 안 따라온 같은 뿌리다.
