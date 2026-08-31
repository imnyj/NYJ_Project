# Antigravity Update Log (2026-08-30)

Claude가 진행할 후속 작업을 위해 Antigravity가 수행한 최근 변경 사항 및 컨텍스트를 기록합니다.

## 1. 메모리 누수 방지 (Memory Leak Prevention)
`libsumo`의 특성 상 동일 프로세스 내에서 에피소드를 반복하며 `start()`와 `close()`를 수백 번 호출할 경우 C++ 내부 메모리가 누수되는 고질적인 문제가 있습니다. 이를 방지하기 위해 다음 조치를 완료했습니다.
- `src/hot_swap_trainer.py`의 `AoiV2IEnv.close()`에 객체 컨테이너(`vehicle_tracks`, `pending_grant` 등)를 명시적으로 `clear()`하는 로직 추가.
- `run_hot_swap_training` 에피소드 종료 지점, 그리고 `evaluate.py`와 `hpo.py`의 평가 종료 지점에서 `env.close()` 호출 후 `del env` 및 `gc.collect()`를 강제 수행하여 참조가 끊긴 TraCI 객체들이 즉시 회수되도록 처리함.

*결과: `pytest tests/` 110개 항목 모두 통과. (메모리 안정성 확보)*

## 2. HPO 결과 반영 (진행 중)
기존 코드에서는 `hpo.py`로 최적의 하이퍼파라미터를 찾더라도, 정작 최종 훈련 진입점인 `run_all.py`에서 이를 로드하지 않고 모델의 기본값(Default)으로만 훈련하는 치명적 누락이 있었습니다.
- 현재 이 문제를 해결하기 위해 Teamwork 에이전트가 백그라운드에서 `run_all.py`에 `--hparams-csv` 인자를 추가하고, `optuna_best_params.csv`를 읽어 `run_hot_swap_training`에 `hparams` 딕셔너리를 주입하는 작업을 수행 중입니다.

## Claude를 위한 인수인계 사항
1. **State Dimension 유의:** Claude가 이전에 18차원에서 17차원으로 관측 공간을 축소(`stop/start_imminent` 파생 피처 제거)했습니다. 따라서 18차원 시절에 생성된 구형 체크포인트 가중치 파일을 그대로 로드하려고 하면 차원 충돌로 크래시가 납니다. 훈련 재개(Resume) 전 구형 체크포인트 정리가 필요할 수 있습니다.
2. **단일 파일 거대화 현상:** 환경 클래스(`AoiV2IEnv`)가 `hot_swap_trainer.py` 안에 완전히 병합되어 파일이 2000줄이 넘어갔습니다. 이는 기능상 문제는 없으나 모듈화 측면에서 아쉬우므로 향후 리팩토링 시 참고 바랍니다.
3. **다음 단계:** Teamwork의 `run_all.py` 수정이 완료되면, 20만 스텝 시뮬레이션을 4개 GPU에 분산하여 돌릴(이전 `simulation_plan.md` 참고) 모든 준비가 끝납니다.
