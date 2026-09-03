# Dispatch for Milestone 1 Worker (System & API Core Refactoring)

## 2026-09-02T08:10:09Z

당신은 Auto_Stock 프로젝트의 **Milestone 1: System & API Core Refactoring**을 전담하여 구현 및 검증하는 Worker 에이전트입니다.

### 작업 환경 및 메타데이터
- 프로젝트 루트: `/home/imnyj/Workspace/Auto_Stock`
- 에이전트 전용 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m1`
- 원본 요구사항: `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
- 프로젝트 명세: `/home/imnyj/Workspace/Auto_Stock/PROJECT.md`
- 디스패치 지침: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m1/DISPATCH.md`
- 시스템 조사 분석 보고서: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_sys_1/analysis.md`
- API 명세 분석 보고서: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_spec_miner_survey_api_1/analysis.md`
- 룰: `/home/imnyj/GEMINI.md` 준수 (파일 락 및 변경 로그 준수)

### 수행할 구체적 작업 내역
1. **`core/kiwoom_api.py` 리팩토링 및 결함 수정**:
   - `Decimal("None")` 크래시 방어: `res.get("field") or 0` 형태로 안전하게 변환
   - `TokenManager` 스레드 세이프티: `self._lock = threading.Lock()` 추가 및 `get_access_token()`에 Double-Checked Locking 적용
   - `TokenManager.revoke_token()` 구현: 세션 토큰 무효화 및 초기화 로직 추가
   - `KiwoomClient.get_account_positions(account_no, ...)` 메서드 구현: 보유 종목 리스트(`Position` 객체 리스트) 반환
   - 응답 파싱 폴백 및 다중 스키마 지원: `get_current_price` (output / cur_prc / stck_prpr), `send_order` (output.ODNO / ord_no / ODNO), `get_account_balance` (output1, output2, dnca_tot_amt, prsm_dpst_aset_amt 등) 완벽 지원
   - 입력 파라미터 유효성 검증(6자리 종목코드 정규식, 매매구분, 수량/단가 양수 검증) 및 HTTP 429/500 에러 매핑
2. **`core/config.py` 리팩토링**:
   - `_CONFIG_LOCK = threading.Lock()`을 선언하고 `get_config()` 및 `_GLOBAL_CONFIG` 초기화/리로드 구간에 스레드 락 적용
3. **`etc/scripts/test_extreme_4_1.py` 수정**:
   - 탑레벨에서 즉시 실행되는 Optuna study 코드를 `if __name__ == "__main__":` 블록 내부로 감싸서 `pytest` 모듈 수집 크래시 방지
4. **루트 디렉토리 정리 (Cleanliness Rule)**:
   - 루트에 방치된 `fix_config.py`, `fix_kiwoom_api.py`, `fix_tests.py`, `fix_tests2.py`, `test_kw.py` 파일들을 `/home/imnyj/Workspace/Auto_Stock/backup/` 디렉토리로 이동/격리
5. **검증 및 빌드/테스트**:
   - `pytest tests/test_phase1_config.py tests/test_phase3_api.py` 실행하여 수정 사항 검증
   - 핸드오프 보고서(`/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m1/handoff.md`) 작성
