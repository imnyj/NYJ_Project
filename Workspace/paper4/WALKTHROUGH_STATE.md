# WALKTHROUGH 진행 상태 (paper4)

- 안내서: /home/imnyj/Workspace/paper4/paper_walkthrough.md
- 현재 단계: **4 (비교 방안 성능 도출) — 진행 중**
- 마지막 갱신: 2026-09-11 16:20

이 파일은 2026-09-11 에 처음 만들었습니다. paper4 는 안내서가 정리되기 전에 시작해
0~3단계를 안내서 없이 진행했고, 산출물이 안내서가 지정한 이름과 다른 곳에 있습니다.
아래 표의 "통과 근거" 는 실제 파일을 확인해 적은 것이며, 이름이 다른 경우 그 사실을
함께 적었습니다.

## 완료한 단계

| 단계 | 완료 일시 | 통과 근거(파일 경로) |
|---|---|---|
| 0 준비 | 2026-09 초 | `.rules/`, `~/.claude/agents/p4-*.md` 7개, 7개 역할 폴더(idea, librarian, coder, writer, visualizer, critic, review) |
| 1 아이디어 | 2026-09 초 | `idea/scenario.md`, `idea/design_spec_v2.md`, `idea/User_Response_v1.md`, `v2` — 안내서의 `idea/idea.md` 대신 이 이름을 씁니다 |
| 2 문헌·비교 방안 | 2026-09-06 | `librarian/references_v2.json`, `related_works.json`, `baselines_v2.json`(아홉 종 확정), `review/baseline_roster_review_20260906.md`(HOORL 유지 판정, 대안 문헌 부재 확인) — 안내서의 `references.json`, `comparative_methods.md` 대신 이 이름을 씁니다 |
| 3 시뮬레이션 | 2026-09-07 | `coder/src/` 전체, `review/HPO_LAUNCH_AUDIT_20260907.md`(552줄, 검토자 판정 "착수해도 된다"), 시험 570개 통과 |

## 진행 중인 단계: 4 (비교 방안 성능 도출)

### 절차별 상태

| 절차 | 상태 | 근거 |
|---|---|---|
| 1. 평가 지표 확정 | **완료** | `performance_metrics.md` (2026-09-11). 주지표를 AoI 중심으로 재편하고, HPO 목적함수가 mean_error 중심이라는 불일치를 원고에 명시하기로 기록 |
| 2. 모델 순서·색상 | **완료** | `visualizer/config.md` (2026-09-11). 문헌 범주별 순서, 범주마다 색상 계열과 선 모양 배정, 제안 방안은 맨 뒤 |
| 3. 탐색 공간 정리 | 완료(이름 다름) | `coder/src/hpo.py` 의 `sample_hparams` 가 방안별 공간을 정의합니다. 안내서가 말한 `data/hpo/hparam_space.csv` 는 없고 코드가 단일 출처입니다 |
| 4. HPO 실행 | **완료** | `coder/results/hpo/optuna_best_params.csv`(아홉 종 병합), `coder/results/hpo_parallel_v2/g*/optuna_trials_*.csv`(아홉 종 15시행, 벌점 0, 발산 0) |
| 5. 본훈련 승인 | **완료** | 2026-09-10 사용자 승인 |
| 6. 본훈련 실행 | **진행 중** | `coder/runs/accumulate_seed42/`, 2026-09-10 19:36 착수, `setsid nohup` 분리 실행, 감독자 재시작 0회 |
| 7. 결과 기록 | 부분 완료 | 학습 곡선 8종(`lg/*_progress.csv`), best 체크포인트 8종. **성능 CSV(metrics)는 아직 없습니다** |
| 8. critic 결과 검증 | 미착수 | 본훈련 완료 후 |

### 본훈련 현황 (2026-09-11 15:10)

여덟 종 완료, MADDPG-MT 진행 중, **HOORL 실패**.

| 모델 | 에피소드 | 최고보상 | 검증보상 |
|---|---|---|---|
| I-HAMAPPO | 100/100 | -0.0322 | -0.0338 |
| MA2HDQN | 100/100 | -0.0333 | -0.0455 |
| SAC | 100/100 | -0.0345 | -0.0345 |
| TD3 | 100/100 | -0.0380 | -0.0396 |
| SPAM-D3QN | 100/100 | -0.0385 | -0.0385 |
| PPO | 100/100 | -0.0406 | -0.0453 |
| RES-MAPDDPG | 100/100 | -0.0413 | -0.0651 |
| MADDPG-MT | 진행 중 | - | - |
| **HOORL** | **0/100** | **실패** | - |

HOORL 은 `PAPER4_HOORL_OFFLINE_DATASET` 이 `run_main_training.sh` 에서 전달되지
않아 `OfflineDatasetMissing` 으로 죽었습니다. HPO 런처는 2026-09-07 에 같은 결함을
고쳤으나 본훈련 런처는 고치지 않았습니다. 스크립트는 2026-09-11 15:0x 에 고쳤고
데이터셋 존재 확인 게이트도 넣었습니다. **HOORL 단독 재실행이 남았습니다.**

## 사용자 결정 기록

| 일시 | 단계 | 질문 | 사용자 결정 |
|---|---|---|---|
| 2026-09-06 | 4 | HPO 전량 재실행, 상태 21차원 확장, 오프라인 자료 재수집 | 세 가지 전부 진행 |
| 2026-09-06 | 2 | HOORL 오프라인 단계 유지 여부 | 유지하되 원고 근거를 교체 |
| 2026-09-07 | 4 | HPO 재실행 착수 | 검토자 확인 후 착수 |
| 2026-09-10 | 4 | 본훈련 착수 | 진행, 세션 종료와 무관하게 계속될 것 |
| 2026-09-10 | 4 | 보고 주기 | 6·12·18·24시, 디스코드 병행 |
| 2026-09-11 | 4 | 평가 지표 범위 | AoI 중심으로 재편 (mean_aoi 주지표) |
| 2026-09-11 | 4 | 그래프 모델 순서 | 문헌 범주별 (basic → similar → latest → proposed) |

## 대기 중인 질문

없음

## 되돌아가기 기록

없음

## 다음 행동

1. MADDPG-MT 완료 대기 (예상 2~3시간)
2. **HOORL 단독 재실행** — 나머지 여덟 종 결과는 보존
3. 아홉 종 성능 CSV 생성 (절차 7의 `metrics.csv`)
4. critic 결과 검증 (절차 8)
5. 4단계 완료 판정 후 5단계(제안 방안 개발)로

## 안내서 갱신 이력

- 2026-09-11 16:13 안내서가 갱신되었습니다. 입구 파일에 `/home/imnyj/command.md`
  (성능 그래프 구성, 논문 작성 요령)가 출처로 추가되었고, 7단계 결정 사안에
  Sensitivity analysis 형태와 환경 변화 실험의 Y축이 들어갔습니다. 06·07·08 단계
  파일이 커졌습니다. **4단계 파일은 바뀌지 않았습니다**(md5 f0fcc247).
