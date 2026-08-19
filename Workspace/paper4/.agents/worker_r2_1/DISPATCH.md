# Dispatch Instructions — Worker R2 (Execute R1 Remediation & Pure Real Data Pipeline)

## Identity
- Role: Real Data Pipeline Implementation Worker (`worker_r2_1`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/worker_r2_1/`

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/.agents/orchestrator_5/DEAD_ENDS.md`
- `/home/imnyj/Workspace/paper4/.agents/explorer_r2_1/handoff.md`
- `/home/imnyj/Workspace/paper4/.agents/explorer_r2_1/proposed_prepare_data.py`

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Tasks
1. **GEMINI.md 안전 프로토콜 준수**:
   - 파일 수정/이동 전 `/home/imnyj/Command/core/lock_manager.py acquire` 실행.
   - 작업 완료 후 `/home/imnyj/Command/core/audit_logger.py` 기록 및 `lock_manager.py release` 실행.
2. **`visualizer/prepare_data.py` 전면 교체**:
   - `/home/imnyj/Workspace/paper4/.agents/explorer_r2_1/proposed_prepare_data.py`의 내용으로 `/home/imnyj/Workspace/paper4/visualizer/prepare_data.py`를 교체하십시오.
   - `prepare_data.py` 내에 `np.random` import 및 합성 난수 생성 로직이 단 1건도 존재하지 않음을 확인하십시오.
3. **잔존 Mock 스크립트 격리 보관**:
   - `mkdir -p /home/imnyj/Workspace/paper4/backup/legacy_mock_scripts_20260819/`
   - `coder/patch_csv.py`, `etc/scripts/generate_and_validate_11_target_datasets.py`, `code/extract_true_data.py`를 해당 백업 디렉토리로 이동하십시오.
4. **전체 시각화 파이프라인 재실행 및 산출물 생성**:
   - `python3 /home/imnyj/Workspace/paper4/visualizer/prepare_data.py`
   - `python3 /home/imnyj/Workspace/paper4/visualizer/plot_all.py`
   - 11대 타겟 22개 산출물(9개 350 DPI PNG, 9개 PDF, 4개 CSV/TeX 표)이 100% 실데이터 기반으로 렌더링되는지 확인하십시오.
5. **검증 커맨드 실행 및 결과 기록**:
   - `grep -rn "np.random" /home/imnyj/Workspace/paper4/visualizer/prepare_data.py` (0건 확인)
   - PIL을 통한 350 DPI 실측 검증.
   - 결과를 `handoff.md`에 기록하고 `send_message`로 보고하십시오.
