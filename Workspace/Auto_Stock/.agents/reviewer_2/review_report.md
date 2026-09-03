# Phase 3 실거래 제어 모듈 아키텍처 및 보안/견고성 정밀 검토 보고서 (Review Report)

- **검토자**: Code Reviewer 2 (Roles: Reviewer, Adversarial Critic)
- **검토 일시**: 2026-09-01T23:42:30+09:00
- **대상 마일스톤**: Phase 3 (실거래 제어 모듈 및 Kiwoom REST API 연동)
- **프로젝트 루트**: `/home/imnyj/Workspace/Auto_Stock`
- **최종 판정**: **APPROVE (승인)**

---

## 1. Review Summary (검토 요약)

**최종 판정 (Verdict)**: **APPROVE (승인)**

본 검토자는 Auto Stock ML/RL Trader 프로젝트의 Phase 3(실거래 제어 모듈 및 Kiwoom REST API 연동) 산출물 전체(`core/config.py`, `core/kiwoom_api.py`, `core/__init__.py`, `modules/engine/manual_trader.py`, `config/settings.yaml`, `.env.example`, `.gitignore`, `tests/test_phase3_api.py`)에 대해 아키텍처 계층 정합성, 네트워크/예외 내결함성, 시크릿 보안 및 테스트 무결성을 독립적·적대적(Adversarial) 관점에서 심층 감사하였습니다.

검토 결과:
1. **아키텍처 및 모듈 경계**: `core/`와 `modules/engine/` 간의 단방향 의존성(`modules/engine/` -> `core/`)이 완벽히 준수되어 순환 참조가 없으며, `ManualTrader`의 의존성 주입(DI) 및 `PriceQuote`/`OrderResult`/`AccountBalance`의 Dual Object/Dict 인터페이스를 통한 개방-폐쇄 원칙(OCP)과 확장성이 우수합니다.
2. **네트워크 및 내결함성**: HTTP 401 수신 시 1회 강제 토큰 갱신 후 재시도(`retry_on_401=False` 가드로 무한 루프 원천 차단), HTTP 429 지수 백오프, HTTP 500/503 서버 에러 처리, 네트워크 타임아웃 예외 포획, 증권사 비즈니스 거절(`rt_cd != 0`)에 대한 세분화된 커스텀 예외 계층(`KiwoomOrderError`, `KiwoomQueryError` 등)이 빈틈없이 구현되었습니다.
3. **보안 및 데이터 격리**: `SecretStr` 클래스를 통한 `__repr__`, `__str__`, f-string 평문 노출 차단(`***`), 4단계 설정 우선순위(OS env > .env > YAML > default), `.gitignore` 내 민감정보 격리, 소스코드 전역 하드코딩 0건 정적 감사(Forensic Audit)가 입증되었습니다.
4. **테스트 및 무퇴행 검증**: `/home/imnyj/venv/bin/pytest tests/` 전체 242개 테스트가 100% PASS(14.55초)되었으며, Phase 1 및 Phase 2 기존 기능에 대한 회귀가 0건임을 확인하였습니다.

---

## 2. Detailed Findings (상세 평가 및 소견)

### [Minor / Observation] 1. 계좌 잔고 응답 내 `output1`/`output2` Null 방어적 안전장치
- **위치**: `core/kiwoom_api.py:686-691` (`get_account_balance`)
- **현황**: `raw_positions = res.get("output1", [])`의 경우 정상 API 응답에서는 `[]`가 반환되어 정상 동작하나, 비정상 프록시 등에서 `{"output1": null}` 형태로 전달될 경우 `res.get("output1")`이 `None`을 반환할 수 있음.
- **평가**: 현재 `test_empty_account_positions_parsing` 및 일반 키움 서버 명세(`output1: []`)에서는 100% 정상 작동하며 문제없음. 향후 Phase 4 고도화 시 `raw_positions = res.get("output1") or []` 형태로 보강 권장 (Minor 권고사항).

### [Good Practice] 2. 401 Unauthorized 무한 재귀 방어 가드
- **위치**: `core/kiwoom_api.py:470-485` (`_request`)
- **평가**: `_request` 재귀 호출 시 `retry_on_401=False`를 전달하여, 자격증명이 영구적으로 무효한 경우 무한 토큰 갱신 루프에 빠지지 않고 즉시 `KiwoomAuthError`를 발생시키도록 안전하게 설계됨.

### [Good Practice] 3. Dual Object/Mapping Data Model 호환성
- **위치**: `core/kiwoom_api.py:104-254` (`PriceQuote`, `OrderResult`, `PositionItem`, `AccountBalance`)
- **평가**: `@dataclass` 기반으로 타입 안정성을 제공하면서 `Mapping[str, Any]`를 상속받아 딕셔너리 색인(`quote["current_price"]`)과 속성 접근(`quote.current_price`)을 동시에 완벽 지원함.

---

## 3. Verified Claims (검증된 주요 주장 및 사실 확인)

| 검증 항목 | 주장 내용 | 검증 방법 및 실행 결과 | 판정 |
|---|---|---|:---:|
| **VC-1** | `SecretStr` 평문 은닉 및 마스킹 | `str()`, `repr()`, f-string 노출 시 `***` 반환 확인 (`etc/scripts/reviewer2_phase3_audit.py`) | **PASS** |
| **VC-2** | 4단계 설정 로딩 및 인터폴레이션 | OS env 오버라이드 및 `${VAR:default}` 파싱 검증 (`tests/test_phase3_api.py::test_interpolate_env_vars`) | **PASS** |
| **VC-3** | HTTP 401 토큰 자동 갱신 및 재시도 | 만료 토큰 주입 후 401 수신 -> 신규 토큰 발급 -> 200 OK 복구 확인 (`test_http_401_auto_retry_token_refresh`) | **PASS** |
| **VC-4** | HTTP 401 무한 재귀 차단 | 지속적 401 발생 시 최대 2회 호출 후 `KiwoomAuthError` 발생 확인 (`test_infinite_401_prevention`) | **PASS** |
| **VC-5** | HTTP 429 Rate Limit 백오프 | 지수 백오프 대기 후 `KiwoomRateLimitError` 정상 송출 확인 (`test_http_429_rate_limit_error`) | **PASS** |
| **VC-6** | 증권사 비즈니스 거절 분기 | `rt_cd != 0` 수신 시 `KiwoomOrderError` / `KiwoomQueryError` 정상 분기 확인 | **PASS** |
| **VC-7** | 음수 부호 현재가 정규화 | 키움 하락 종목의 음수 호가(`"-75000"`)에 대해 `abs()` 절대값 변환 확인 | **PASS** |
| **VC-8** | ManualTrader E2E 라운드트립 | 매수/매도 주문 전/후 잔고 변동액 산출 및 CLI 리포트 출력 확인 (`test_e2e_manual_trader_buy_execution`) | **PASS** |
| **VC-9** | 하드코딩 0건 정적 감사 | 전역 디렉토리(`core/`, `modules/`, `config/`) 내 시크릿 하드코딩 0건 확인 (`test_forensic_static_audit_zero_hardcoded_secrets`) | **PASS** |
| **VC-10** | 전체 회귀 테스트 통과 | `pytest -v tests/` 실행 결과 242/242 PASSED (0 failures, 14.55s) 확인 | **PASS** |

---

## 4. Coverage Gaps & Unexplored Areas (적대적 분석 및 미검증 영역)

- **실제 키움 REST API 운영 서버 라이브 트래픽 연동**:
  - 현재 Phase 3 요구사항에 따라 100% Mocking 격리 환경에서 검증되었으며, 실제 증권사 서버와의 물리적 네트워크 레이턴시 및 웹소켓 실시간 체결 통보는 Phase 4/5 범위에 해당합니다. (위험도: Low, 차기 마일스톤 인계 권장)

---

## 5. 최종 결론

Phase 3 실거래 제어 모듈은 소프트웨어 공학적 설계 품질, 보안성(SecretStr & Config 계층), 네트워크 복원력(TokenManager & Retry Handler), 그리고 포괄적인 E2E 테스트 인프라를 완벽히 갖추었으므로 최종 **APPROVE** 판정을 부여합니다.
