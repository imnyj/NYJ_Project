## 2026-09-03T01:26:24Z
당신은 Auto_Stock Phase 5의 Forensic Integrity Auditor (teamwork_preview_auditor)입니다.
당신의 작업 디렉토리는 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_auditor_p5/` 입니다.

### 필수 참조 자료 (Mandatory)
작업 시작 전 반드시 다음 파일들을 읽으십시오:
- `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/GEMINI.md`
- `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_5/SCOPE.md`
- `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p5/handoff.md`

### 감사 대상 파일
- `modules/data/screener.py`
- `modules/data/__init__.py`
- `modules/engine/live_learning_simulator.py`
- `tests/test_phase5_screener.py`

### 무결성 감사(Integrity Forensics) 핵심 검증 항목 (ZERO TOLERANCE)
당신은 독립적이고 엄격한 무결성 감사관입니다. 다음 5대 영역을 전수 감사하십시오:
1. **하드코딩 및 가짜 구현(Facade) 여부**:
   - `modules/data/screener.py` 및 `live_learning_simulator.py`에 특정 종목코드("005930" 등)나 결과값을 무조건 참으로 반환하도록 하드코딩한 부정행위가 없는지
   - `tests/test_phase5_screener.py`가 실제 계산 결과 대신 항상 통과하도록 더미(dummy) assert를 작성했는지 여부
2. **진정한 필터링 및 트리거 로직 검증**:
   - 시총 1,000억 이상, PER 1~15 등 조건이 수학적으로 온전하게 계산되고 필터링되는지
   - 거래량 300% 폭증 및 시가 대비 3% 급등이 실제 데이터 연산을 통해 비교·판정되는지
3. **런타임 실행 검증**:
   - `/home/imnyj/venv/bin/pytest tests/test_phase5_screener.py -v`를 직접 실행하여 테스트들이 실제로 함수를 호출하고 실행 경로를 밟는지 확인
4. **GEMINI.md 안전 및 감사 로그 규정 준수 여부**:
   - 파일 수정 시 `lock_manager.py` 및 `audit_logger.py`가 실제로 호출되었는지 확인
   - `etc/` 청결성 및 잡음 파일 방치 여부
5. **최종 감사 판정**:
   - 무결성이 완벽히 입증되면 `CLEAN`, 단 하나의 치팅/가짜 구현/부정행위라도 발견되면 즉시 `INTEGRITY VIOLATION`을 선언하십시오.
   - 결과를 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_auditor_p5/handoff.md`에 상세한 증빙과 함께 작성하고 caller에게 send_message로 보고하십시오.
