# Auto Stock ML/RL Trader — Phase 3: 실거래 제어 모듈 구현 상세 보고서

- **작성 에이전트**: Worker 1 (Phase 3 Core Implementer & QA)
- **작성 일시**: 2026-09-01T23:38:30+09:00
- **프로젝트 루트**: `/home/imnyj/Workspace/Auto_Stock`
- **대상 마일스톤**: Phase 3 (실거래 제어 모듈 및 Kiwoom REST API 연동)

---

## 1. 개요 및 구현 요약

본 구현 작업은 Auto Stock ML/RL Trader의 'Phase 3: 실거래 제어 모듈' 구축을 완벽하게 완수하였습니다. 증권사(Kiwoom) REST API 연동 코어, 4단계 우선순위 설정 및 시크릿 보안 로더, CLI 기반 수동 매매 제어기, 그리고 4-Tier 22개 E2E Mock 테스트 스위트를 성공적으로 개발 및 검증하였습니다.

### 주요 구현 산출물
1. **`config/settings.yaml`, `config/settings.example.yaml`, `.env.example`**:
   - 민감정보(AppKey, AppSecret, AccountNo) 템플릿(`${KIWOOM_APP_KEY:}`) 적용 및 모의/실서버 파라미터 정의.
2. **`core/config.py` 및 `core/__init__.py`**:
   - `OS 환경변수 > .env > settings.yaml > 기본값` 4단계 우선순위 로더 및 정규식 인터폴레이션.
   - `SecretStr` 클래스를 통한 민감정보 평문 은닉 및 마스킹(`***`).
   - `KiwoomConfig` 도메인 및 액션별 TR_ID 자동 분기 헬퍼 구현.
3. **`core/kiwoom_api.py`**:
   - `TokenManager`: OAuth 2.0 Client Credentials 토큰 발급, 만료 시간 추적, 자동 갱신 및 메모리 캐싱.
   - `KiwoomClient` (`KiwoomAPI`): 현재가 조회(`get_current_price`), 시장가/지정가 주문(`send_order`), 계좌 잔고/보유종목 조회(`get_account_balance`, `get_account_positions`).
   - 401 Unauthorized 수신 시 토큰 강제 갱신 후 1회 자동 재시도, 429 Rate Limit 지수 백오프, 커스텀 예외 계층화.
4. **`modules/engine/manual_trader.py` 및 `modules/engine/__init__.py`**:
   - CLI 및 대화형 수동 매매 인터페이스 (`--symbol`, `--side`, `--quantity`, `--price`, `--mock`, `--live`).
   - 주문 전 잔고/현재가 확인 -> 주문 전송 -> 주문 체결 후 잔고 및 보유 종목 변동 시각화 테이블 출력 (`rich` 패널/테이블 지원).
5. **`tests/test_phase3_api.py`**:
   - 4-Tier 22개 E2E Mock 테스트 스위트 전원 통과 (전체 프로젝트 테스트 234/234 100% 통과).
   - 소스코드 전역 민감정보 하드코딩 0건 정적 감사(Forensic Static Audit) 완료.

---

## 2. 모듈별 상세 구현 내역

### 2.1 보안 설정 계층 (`config/` & `core/config.py`)
- **SecretStr**:
  - `__str__` 및 `__repr__` 호출 시 `***` 또는 `SecretStr('***')`을 반환하여 로깅이나 터미널 출력 시 시크릿 유출 차단.
  - `get_secret_value()`를 통해서만 실제 평문 문자열 획득 가능.
- **계층적 설정 로더 (`load_config`)**:
  - Level 1: `os.environ` (최고 우선순위)
  - Level 2: `.env` (python-dotenv)
  - Level 3: `config/settings.yaml` (`${VAR:default}` 정규식 인터폴레이션 지원)
  - Level 4: Python 데이터클래스 안전 기본값 (`use_mock_server=True` 등)
- **TR_ID 동적 매핑**:
  - 현재가 시세: `FHKST01010100`
  - 주문 전송: 모의투자 매수(`VTTC0802U`), 매도(`VTTC0801U`) / 실거래 매수(`TTTC0802U`), 매도(`TTTC0801U`)
  - 잔고 조회: 모의투자(`VTTC8434R`) / 실거래(`TTTC8434R`)

### 2.2 키움 Open API REST 코어 (`core/kiwoom_api.py`)
- **TokenManager**:
  - `POST /oauth2/tokenP` 호출을 통한 Bearer 토큰 획득.
  - 메모리 캐싱 및 만료 10분 전 자동 판별(`is_expired`).
  - `revoke_token`을 통한 토큰 폐기 지원.
- **KiwoomClient (KiwoomAPI)**:
  - `_request()`: 공통 헤더 자동 조립, 401 수신 시 `TokenManager` 강제 갱신 후 재호출 복구, 429 수신 시 지수 백오프, 증권사 에러코드(`rt_cd != "0"`) 감지 시 적절한 예외(`KiwoomOrderError`, `KiwoomQueryError`) 발생.
  - `get_current_price(symbol: str) -> PriceQuote`: 6자리 종목코드 정규식 검증, Decimal 정밀 변환, Dictionary 인터페이스 호환 지원.
  - `send_order(symbol, side, quantity, price, order_type) -> OrderResult`: 시장가(`ORD_DVSN: 01`, `ORD_UNPR: 0`) 및 지정가 지원, 주문번호(`ODNO`) 파싱.
  - `get_account_balance() -> AccountBalance`: `output1`(보유종목) 및 `output2`(총괄요약) 파싱, 출금가능예수금 및 평가손익 계산.

### 2.3 수동 매매 제어기 (`modules/engine/manual_trader.py`)
- **ManualTrader**:
  - 파라미터 유효성 검사 (`validate_inputs`): 종목코드 6자리 정규식, 양수 수량, 유효 주문방향(BUY/SELL).
  - 주문 라이프사이클: 주문 전 잔고 조회 -> 현재가 조회 -> 사용자 최종 확인 -> 주문 전송 -> 주문 후 잔고 조회 -> 잔고 변동액 산출 -> 리포트 렌더링.
  - 리포트 출력: `rich` 터미널 테이블 및 패널 지원 (출금가능 예수금 변동, 보유 수량 변동 직관적 표시), Plain-text fallback 지원.
  - CLI 엔트리포인트 (`main`): 커맨드라인 옵션 및 대화형(`--interactive`) 모드 지원.

---

## 3. 검증 결과 및 테스트 스위트 현황

### 3.1 4-Tier Phase 3 테스트 매트릭스 (`tests/test_phase3_api.py`)
| Tier | 테스트 항목 | 검증 대상 | 결과 |
|---|---|---|---|
| **Tier 1** | TC-01 ~ TC-08 | SecretStr 마스킹, KiwoomConfig TR_ID 분기, 토큰 캐싱, 토큰 폐기, 현재가 조회, 시장가 매수/매도, 지정가 주문, 계좌 잔고 파싱 | **8/8 PASSED** |
| **Tier 2** | TC-09 ~ TC-16 | 토큰 만료 자동갱신, 401 재시도 복구, 429 백오프, 500 에러, 타임아웃, 비즈니스 거절, 입력값 검증 실패 방어, 자격증명 누락 | **8/8 PASSED** |
| **Tier 3** | TC-17 ~ TC-19 | YAML 정규식 인터폴레이션, OS 환경변수 오버라이드, Mock/Live 도메인 및 TR_ID 토글 불변성 | **3/3 PASSED** |
| **Tier 4** | TC-20 ~ TC-22 | ManualTrader E2E 라운드트립, CLI main() 실행, 소스코드 하드코딩 0건 정적 감사 | **3/3 PASSED** |

### 3.2 전체 프로젝트 테스트 실행 결과
- **실행 명령어**: `/home/imnyj/venv/bin/pytest tests/`
- **결과**: **234 Passed / 0 Failed (100% PASS, 13.45s)**
  - 기존 Phase 1 & Phase 2 테스트: 212개 (100% 통과, 무퇴행 확인)
  - Phase 3 신규 테스트: 22개 (100% 통과)

---

## 4. 결론

Phase 3 실거래 제어 모듈의 모든 요구사항(R1, R2, R3 및 Acceptance Criteria)이 무결하게 구현되었습니다.
