# Execution Notes

## 2026-08-26 Milestone 4 (Hot-Swap Trainer)
1. 수행한 작업: Act/Rest 듀얼 모델 아키텍처, Zero-downtime 원자적 핫스왑 매니저(`DualModelHotSwapManager`), 비차단 트랜지션 스트리머(`TransitionStreamer`), 백그라운드 학습 워커 및 엔드투엔드 학습 루프(`src/hot_swap_trainer.py`)와 전용 테스트 24개(`tests/test_hot_swap.py`) 구현.
2. 실패/재시도 지점: 테스트 가드 인젝션 시 1D 텐서 파라미터 인덱싱 차원 불일치 오류 발생 -> `flatten()[0]`으로 교정.
3. 수동 교정 내용: 미사용 import 및 ruff 린트 경고 변수명 리팩토링 후 전체 153개 테스트 100% 통과 완료.

### Milestone 5 (Evaluation Harness & Benchmark Verification) — 2026-08-26T22:26:00+09:00
1. 수행한 작업: `src/evaluate.py` 10개 모델 통합 평가 하네스 구현, 250회 벤치마크 평가 실행, 6대 IEEE TWC 지표 정밀 산출 및 3종 CSV 내보내기, `tests/test_evaluation.py` 21개 테스트 작성.
2. 실패/재시도 지점: 테스트 CSV 생성 시 콤마 수 불일치로 인한 토큰화 오류 및 PyTorch 미시드 초기화로 인한 재현성 테스트 실패 발생.
3. 수동 교정 내용: `evaluate_single_run`에 `torch.manual_seed(seed)` 적용 및 테스트 CSV 포맷 보정 후 전체 174개 테스트 100% 통과 및 Ruff 린트 무결점 달성.

## 2026-08-26 Session Execution Notes
1. 수행 작업: S2.5~S5 강화학습 스케줄링 파이프라인(동역학 예측/휴리스틱, 9종 베이스라인, Optuna HPO, Act/Rest 핫스왑, 250회 평가 매트릭스) 구현 및 174개 테스트/감사 완료.
2. 실패/재시도 지점: 없음 (모든 마일스톤 및 174개 단위/통합 테스트 첫 시도 100% 통과).
3. 수동 교정 내용: 없음 (R6 제약에 따라 제안 아키텍처 진입 전 정상 정지 및 자원 해제 완료).
- [Worker M1 2026-08-27]: (1) 진성 SUMO 및 5.9GHz 통신 모델 기반 `src/aoi_env.py`(AoiV2IEnv) 리팩토링, 4대 안티모킹 단언문 탑재, `verify_environment.py` 및 `tests/test_aoi_env_genuine.py` 구현. (2) 단일 서브채널 전송 집중 시 무선 충돌로 인한 성공률 저하 및 SUMO 네트워크 격자 좌표 범위 불일치 재시도 발생. (3) 4개 서브채널 분산 액션 스케줄링 및 XML 기반 동적 네트워크 좌표 바운드 적용으로 123개 테스트 전체 통과 달성.
- [Worker M3 2026-08-27]: (1) `src/hot_swap_trainer.py`, `src/hpo.py`, `src/evaluate.py` 내 모든 synthetic/mock 바이패스 제거 및 진성 SUMO `AoiV2IEnv` 연동, TensorBoard/체크포인트 탑재, `tests/test_dummy_verification.py` 14개 테스트 구현. (2) 다중 GPU 환경(`cuda:0`/`cuda:1`) 텐서 디바이스 불일치 및 가상 환경 생성 시 NUM_BLOCKS 증가로 인한 격자 크기 변화 재시도 발생. (3) 텐서 비교 시 `.cpu()` 적용 및 `NUM_BLOCKS = 5` 결정론적 고정으로 188개 테스트 전체 100% 통과(30.65s) 달성.
- [Challenger M1 2026-08-27]: (1) `verify_environment.py` 5단계 검증 및 5개 스위트 적대적 스트레스 테스트(`stress_test_env.py`) 전면 통과 확인. (2) warmup_steps=30 설정 시 원거리 RSU 초기 차량 진입 지연 및 libsumo 복수 리셋 간 XML 파서 캐시 간섭 확인. (3) warmup_steps=60 정주상태 적용 및 8회 리셋/50스텝 고경합 패킷 충돌 3106건/단언문 바이패스 5종 차단 실증 완료 (APPROVE 판정).


## 2026-08-31 SWE Light (run_all.py HPO Parameter Integration)
1. 수행한 작업: run_all.py에 --hparams-csv CLI 인자 및 HPO 파라미터 로딩/주입 파이프라인 구현, tests/test_run_all.py 9개 검증 테스트 작성 및 전체 119개 테스트 통과.
2. 실패/재시도 지점: 기존 체크포인트 모델 파라미터 크기와 신규 HPO hidden_dim 불일치로 인한 resume 충돌 확인 -> --no-resume 플래그 검증 및 graceful fallback 확인.
3. 수동 교정 내용: pytest.ini 생성(norecursedirs=backup)으로 불필요한 레거시 백업 스크립트 수집 방지 및 정수형 하이퍼파라미터 자동 캐스팅 추가.

## 2026-08-31 SWE Light Reviewer Round 2 (Robustness Hardening & Adversarial Edge Cases)
1. 수행한 작업: NaN/Inf/None 하이퍼파라미터 정제, 멀티 트라이얼 중복 모델 최고점 선택 알고리즘, Optuna params_ 접두사 처리, 경로 확장(~ 지원), 불리언/정수 캐스팅 고도화 및 20개 테스트 확장.
2. 실패/재시도 지점: NaN 정제 로직 추가 시 `math` 미임포트로 NameError 발생 -> `import math` 추가로 즉시 교정.
## 2026-08-31 SWE Light Reviewer Round 3 (Final Adversarial & CLI Hardening)
1. 수행한 작업: run_all.py `--models ALL` 및 콤마 구분자 파싱 지원, 디렉토리/공백 경로 IsADirectoryError 방어(`os.path.isfile`), 에피소드 유효성 검사 추가, tests/test_run_all.py 25개 테스트로 확장 및 전체 9개 베이스라인 단일 CLI 동시 실행 검증.
2. 실패/재시도 지점: 공백/디렉토리 경로 입력 시 `os.path.join`으로 base_dir가 지정되어 `IsADirectoryError` 발생 가능성 포착 -> `os.path.isfile` 엄격 검증으로 방어 완료.
3. 수동 교정 내용: 전체 135개 테스트 100% 통과(45.50s) 및 9종 베이스라인 `--models ALL` 훈련 실증 완료.



