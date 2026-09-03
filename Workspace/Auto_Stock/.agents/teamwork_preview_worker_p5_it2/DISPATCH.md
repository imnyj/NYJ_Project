## 2026-09-03T01:31:53Z

<USER_REQUEST>
당신은 Auto_Stock Phase 5의 결함 수정 및 코드 강화를 담당하는 Worker (teamwork_preview_worker)입니다.
당신의 작업 디렉토리는 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p5_it2/` 입니다.

### MANDATORY INTEGRITY WARNING (필수 준수 경고)
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 필수 참조 자료 (Mandatory References)
1. `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
2. `/home/imnyj/GEMINI.md` (파일 락, 감사 로그, 한국어 사용, 가상환경 등)
3. `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_challenger_p5_1/handoff.md` (Challenger 1 결함 상세 보고서)
4. `/home/imnyj/Workspace/Auto_Stock/etc/scripts/phase5_screener_adversarial_stress_suite.py` (Challenger 1 적대적 테스트 하네스)

### 수정 대상 파일
- `modules/data/screener.py`
- `tests/test_phase5_screener.py` (신규 4개 엣지케이스 테스트 케이스 추가 반영)

### 해결해야 할 4대 실측 결함
1. **[BUG-P5-01] 문자열 `baseline_volume` 유입 시 `TypeError` (`screener.py:400`)**:
   - `prev_same_time_volume`이 문자열일 때 `base_vol <= 0` 비교에서 TypeError 발생.
   - 조치: 수치 비교 전 `try: base_vol = float(base_vol) if base_vol is not None else None except (ValueError, TypeError, OverflowError): return None`로 안전 변환 및 None/NaN/Inf 검사.
2. **[BUG-P5-02] 무한대/초대형 수치 유입 시 `OverflowError` (`screener.py:373, 392, 409`)**:
   - `float('inf')` 거래량 유입 시 `int(accum_raw)`가 `OverflowError` 발생.
   - 조치: 수치 파싱 블록의 예외 포획을 `except (ValueError, TypeError, OverflowError): return None`로 확장하고, `math.isinf()` 또는 `math.isnan()`인 경우 안전하게 None 반환.
3. **[BUG-P5-03] `market_cap = np.inf` 누수 및 시총 1위 탈취 (`screener.py:240`)**:
   - 시가총액 마스크에 무한대 검증이 누락되어 inf 종목이 풀에 진입하고 정렬 시 1위를 탈취함.
   - 조치: `valid_cap_mask = (df["market_cap"] >= self.criteria.min_market_cap) & (~np.isinf(df["market_cap"])) & (~df["market_cap"].isna())`로 무한대 철저 배제.
4. **[BUG-P5-04] '억원' 단위 메가캡(100조 원 이상) 존재 시 전 종목 탈락 (`screener.py:236~239`)**:
   - `if 0 < max_cap < 1_000_000:` 조건으로 인해 삼성전자(500조 원 = 500만 억원) 등이 포함되면 단위 변환이 생략되어 전 종목 탈락함.
   - 조치: 단위 판별 상한을 `if 0 < max_cap < 100_000_000:` (1경 원)으로 상향하여 메가캡 억원 단위가 정상적으로 원 단위로 변환되도록 수정.

### 안전 규칙 준수 (GEMINI.md)
- 파일 수정 전 `/home/imnyj/Command/core/lock_manager.py acquire <filepath>`로 락 획득, 수정 후 release.
- 수정 후 `/home/imnyj/Command/core/audit_logger.py`로 로깅.

### 필수 검증 단계
수정 완료 후 다음 명령어들을 직접 실행하여 검증하십시오:
1. `/home/imnyj/venv/bin/python etc/scripts/phase5_screener_adversarial_stress_suite.py`
   -> **11/11 PASS (0 failures, exit code 0)** 반드시 확인!
2. `/home/imnyj/venv/bin/pytest tests/test_phase5_screener.py -v`
   -> **100% PASS** 확인!
3. `/home/imnyj/venv/bin/pytest tests/test_live_learning_simulator.py tests/test_hybrid_trading_env.py -v`
   -> **100% PASS** 확인!

결과를 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p5_it2/handoff.md`에 기록하고 caller에게 send_message로 완료 보고하십시오.
</USER_REQUEST>
