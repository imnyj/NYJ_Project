# Progress — explorer_2

- Last visited: 2026-09-01T23:31:35+09:00
- Current Status: Exploration and Survey Report Completed

## Checklist
- [x] Dispatch & Briefing initialization
- [x] Investigate existing codebase & configuration structure in Auto_Stock
- [x] Investigate Kiwoom Open API REST specification details:
  - OAuth2.0 Token 발급 / 갱신 (`/oauth2/tokenP`, token_type, expires_in)
  - Base URL (실거래: `https://openapi.kiwoom.com`, 모의투자: `https://openapivts.kiwoom.com`)
  - Headers (`content-type`, `authorization: Bearer ...`, `appkey`, `appsecret`, `tr_id`, `tr_cont`, `custtype` 등)
  - 현재가 조회 (국내주식 시세 tr_id: `FHKST01010100`, 종목코드, 현재가, 전일대비, 거래량 등)
  - 시장가 주문 전송 (매수/매도 주문 tr_id: `TTTC0802U`/`TTTC0801U`/`VTTC0802U`/`VTTC0801U`, 계좌번호, 종목코드, 주문수량, 주문단가=0, 주문구분=01)
  - 계좌 잔고 및 예수금 조회 (보유 종목별 잔고, 평가손익, 총평가금액, 주문가능예수금)
- [x] Design class architecture & signatures for `core/kiwoom_api.py` (KiwoomAPIClient, TokenManager, KiwoomConfig, Request/Response Data Models)
- [x] Design CLI manual trader structure for `modules/engine/manual_trader.py` (ManualTrader, CLI input loop, order validation, post-order balance reporting)
- [x] Design exception handling & security/secret management (`config/settings.yaml`, `.env`, Exception hierarchy)
- [x] Write `survey_report.md`
- [x] Write `handoff.md` (5-Component)
- [x] Send completion message to parent
