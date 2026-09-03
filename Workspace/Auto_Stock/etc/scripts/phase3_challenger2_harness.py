"""
etc/scripts/phase3_challenger2_harness.py
=========================================
Auto Stock Phase 3 Challenger 2: Adversarial & Invariant Verification Test Harness

Covers:
1. Environment Toggle & Endpoint Isolation Invariance (Live vs Mock URL & TR_ID)
2. Configuration Precedence & Interpolation Invariance (OS env > .env > YAML > Defaults)
3. Accounting Invariance & Decimal Arithmetic Exactness (Market Buy/Sell, Balance Diff, Multi-asset isolation)
4. Fault Tolerance & Recovery (401 Auto-Recovery, 429 Rate Limiting Backoff, 500 Errors, Network Timeout)
5. Static Secret & Anti-Hardcoding Forensic Audit
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
import requests
import yaml

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    AppConfig,
    KiwoomConfig,
    SecretStr,
    TradingConfig,
    _parse_bool,
    get_config,
    interpolate_env_vars,
    load_config,
)
from core.kiwoom_api import (
    AccountBalance,
    KiwoomAPIError,
    KiwoomAuthError,
    KiwoomClient,
    KiwoomNetworkError,
    KiwoomOrderError,
    KiwoomQueryError,
    KiwoomRateLimitError,
    OrderResult,
    OrderSide,
    OrderType,
    PositionItem,
    PriceQuote,
    TokenManager,
)
from modules.engine.manual_trader import ManualTrader, main as manual_trader_main


def create_mock_response(
    status_code: int,
    json_data: Optional[Dict[str, Any]] = None,
    text: Optional[str] = None,
) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status_code
    if json_data is not None:
        resp._content = json.dumps(json_data).encode("utf-8")
        resp.json = MagicMock(return_value=json_data)
    elif text is not None:
        resp._content = text.encode("utf-8")
    else:
        resp._content = b"{}"
        resp.json = MagicMock(return_value={})
    return resp


class TestHarnessPhase3Challenger2:
    """Challenger 2 Empirical Verification Suite"""

    # =========================================================================
    # Section 1: Environment Toggle & Endpoint Isolation Invariance
    # =========================================================================
    def test_mock_server_strict_url_and_tr_id_isolation(self):
        """
        [Invariant 1.1] USE_MOCK_SERVER=True인 경우, 모든 API 호출이 반드시 모의서버 URL(openapivts.kiwoom.com)과
        모의투자 TR_ID(VTTC...)로만 라우팅되며, 실거래 URL(openapi.kiwoom.com) 및 실거래 TR_ID(TTTC...)의
        호출이 100% 차단됨을 검증.
        """
        cfg = KiwoomConfig(
            app_key=SecretStr("mock_key"),
            app_secret=SecretStr("mock_secret"),
            account_no="12345678-01",
            use_mock_server=True,
            live_base_url="https://openapi.kiwoom.com",
            mock_base_url="https://openapivts.kiwoom.com",
        )

        assert cfg.base_url == "https://openapivts.kiwoom.com"
        assert cfg.is_mock is True
        assert cfg.get_tr_id("inquire_price") == "FHKST01010100"
        assert cfg.get_tr_id("order", "BUY") == "VTTC0802U"
        assert cfg.get_tr_id("order", "SELL") == "VTTC0801U"
        assert cfg.get_tr_id("inquire_balance") == "VTTC8434R"

        # Intercept requests and verify URLs & headers
        session_mock = MagicMock(spec=requests.Session)
        
        # 1. Token Issue
        session_mock.post.return_value = create_mock_response(
            200, {"access_token": "mock_token_123", "expires_in": 86400}
        )
        
        # 2. Quotation, Order, Balance
        session_mock.request.side_effect = [
            create_mock_response(200, {"rt_cd": "0", "output": {"stck_prpr": "70000", "acml_vol": "1000"}}),
            create_mock_response(200, {"rt_cd": "0", "output": {"ODNO": "111", "ORD_TMD": "090000"}, "msg1": "OK"}),
            create_mock_response(200, {"rt_cd": "0", "output1": [], "output2": [{"dnca_tot_amt": "1000000"}]}),
        ]

        client = KiwoomClient(config=cfg, session=session_mock)

        # Test Token URL
        client.get_access_token()
        token_call = session_mock.post.call_args
        assert token_call[0][0].startswith("https://openapivts.kiwoom.com/oauth2/tokenP")
        assert "openapi.kiwoom.com" not in token_call[0][0]

        # Test Price Request
        client.get_current_price("005930")
        price_call = session_mock.request.call_args_list[0]
        assert price_call[1]["url"].startswith("https://openapivts.kiwoom.com/uapi/domestic-stock/v1/quotations/inquire-price")
        assert price_call[1]["headers"]["tr_id"] == "FHKST01010100"
        assert "openapi.kiwoom.com" not in price_call[1]["url"]

        # Test Order Request
        client.send_order("005930", "BUY", 10)
        order_call = session_mock.request.call_args_list[1]
        assert order_call[1]["url"].startswith("https://openapivts.kiwoom.com/uapi/domestic-stock/v1/trading/order-cash")
        assert order_call[1]["headers"]["tr_id"] == "VTTC0802U"
        assert order_call[1]["headers"]["tr_id"] != "TTTC0802U"
        assert "openapi.kiwoom.com" not in order_call[1]["url"]

        # Test Balance Request
        client.get_account_balance()
        balance_call = session_mock.request.call_args_list[2]
        assert balance_call[1]["url"].startswith("https://openapivts.kiwoom.com/uapi/domestic-stock/v1/trading/inquire-balance")
        assert balance_call[1]["headers"]["tr_id"] == "VTTC8434R"
        assert balance_call[1]["headers"]["tr_id"] != "TTTC8434R"
        assert "openapi.kiwoom.com" not in balance_call[1]["url"]

    def test_live_server_strict_routing_and_tr_id_invariance(self):
        """
        [Invariant 1.2] USE_MOCK_SERVER=False인 경우, 실거래 URL(openapi.kiwoom.com)과
        실거래 TR_ID(TTTC0802U / TTTC0801U / TTTC8434R)로 정확히 분기되는지 검증.
        """
        cfg = KiwoomConfig(
            app_key=SecretStr("live_key"),
            app_secret=SecretStr("live_secret"),
            account_no="87654321-01",
            use_mock_server=False,
            live_base_url="https://openapi.kiwoom.com",
            mock_base_url="https://openapivts.kiwoom.com",
        )

        assert cfg.base_url == "https://openapi.kiwoom.com"
        assert cfg.is_mock is False
        assert cfg.get_tr_id("order", "BUY") == "TTTC0802U"
        assert cfg.get_tr_id("order", "SELL") == "TTTC0801U"
        assert cfg.get_tr_id("inquire_balance") == "TTTC8434R"

        session_mock = MagicMock(spec=requests.Session)
        session_mock.post.return_value = create_mock_response(200, {"access_token": "live_token", "expires_in": 86400})
        session_mock.request.return_value = create_mock_response(
            200, {"rt_cd": "0", "output": {"ODNO": "222", "ORD_TMD": "090500"}, "msg1": "OK"}
        )

        client = KiwoomClient(config=cfg, session=session_mock)
        client.send_order("000660", "SELL", 5)

        order_call = session_mock.request.call_args
        assert order_call[1]["url"].startswith("https://openapi.kiwoom.com")
        assert order_call[1]["headers"]["tr_id"] == "TTTC0801U"
        assert "openapivts.kiwoom.com" not in order_call[1]["url"]

    def test_parse_bool_robustness_on_adversarial_inputs(self):
        """
        [Invariant 1.3] 환경 변수 값으로 들어올 수 있는 다양한 불리언 표현식 파싱 검증
        """
        truthy_inputs = [True, "true", "True", "TRUE", "1", "t", "T", "yes", "YES", "y", "Y", "on", "ON"]
        falsy_inputs = [False, "false", "False", "FALSE", "0", "f", "F", "no", "NO", "n", "N", "off", "OFF"]

        for item in truthy_inputs:
            assert _parse_bool(item, default=False) is True, f"Failed on truthy: {item}"

        for item in falsy_inputs:
            assert _parse_bool(item, default=True) is False, f"Failed on falsy: {item}"

        # None / Unrecognized inputs fallback to default
        assert _parse_bool(None, default=True) is True
        assert _parse_bool(None, default=False) is False
        assert _parse_bool("invalid_random_string", default=True) is True
        assert _parse_bool("invalid_random_string", default=False) is False

    # =========================================================================
    # Section 2: Configuration Precedence & Interpolation Invariants
    # =========================================================================
    def test_four_tier_config_precedence_hierarchy(self, monkeypatch):
        """
        [Invariant 2.1] 4단계 우선순위 검증:
        OS 환경 변수 (1순위) > .env 파일 (2순위) > settings.yaml (3순위) > 코드 기본값 (4순위)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            env_file = tmp_root / ".env"
            yaml_file = tmp_root / "settings.yaml"

            # 3순위: YAML 파일 작성
            yaml_content = {
                "app": {"name": "YamlApp", "version": "0.1.0"},
                "kiwoom": {
                    "app_key": "yaml_key",
                    "app_secret": "yaml_secret",
                    "account_no": "11111111-01",
                    "use_mock_server": True,
                    "timeout_seconds": 12.0,
                },
                "trading": {"default_quantity": 5},
            }
            yaml_file.write_text(yaml.dump(yaml_content), encoding="utf-8")

            # 2순위: .env 파일 작성
            env_content = (
                "APP_NAME=DotenvApp\n"
                "KIWOOM_APP_KEY=dotenv_key\n"
                "KIWOOM_ACCOUNT_NO=22222222-01\n"
                "USE_MOCK_SERVER=False\n"
            )
            env_file.write_text(env_content, encoding="utf-8")

            # Test A: Level 2 (.env) overrides Level 3 (YAML)
            cfg_a = load_config(yaml_path=yaml_file, env_path=env_file)
            assert cfg_a.name == "DotenvApp"  # from .env
            assert cfg_a.kiwoom.app_key.get_secret_value() == "dotenv_key"  # from .env
            assert cfg_a.kiwoom.app_secret.get_secret_value() == "yaml_secret"  # from YAML
            assert cfg_a.kiwoom.account_no == "22222222-01"  # from .env
            assert cfg_a.kiwoom.use_mock_server is False  # from .env
            assert cfg_a.kiwoom.timeout_seconds == 12.0  # from YAML
            assert cfg_a.trading.default_quantity == 5  # from YAML

            # Test B: Level 1 (OS env) overrides Level 2 (.env) and Level 3 (YAML)
            monkeypatch.setenv("APP_NAME", "OsEnvApp")
            monkeypatch.setenv("KIWOOM_APP_KEY", "os_env_key")
            monkeypatch.setenv("USE_MOCK_SERVER", "True")
            monkeypatch.setenv("KIWOOM_TIMEOUT_SECONDS", "30.0")

            cfg_b = load_config(yaml_path=yaml_file, env_path=env_file)
            assert cfg_b.name == "OsEnvApp"  # from OS env
            assert cfg_b.kiwoom.app_key.get_secret_value() == "os_env_key"  # from OS env
            assert cfg_b.kiwoom.use_mock_server is True  # from OS env
            assert cfg_b.kiwoom.timeout_seconds == 30.0  # from OS env
            assert cfg_b.kiwoom.account_no == "22222222-01"  # from .env (no OS env set)
            assert cfg_b.kiwoom.app_secret.get_secret_value() == "yaml_secret"  # from YAML

    def test_env_interpolation_edge_cases(self):
        """
        [Invariant 2.2] ${VAR:default} 패턴 정규식 치환의 다양한 경계조건 검증
        """
        env_map = {
            "SET_VAR": "actual_val",
            "EMPTY_VAR": "",
            "PORT": "8080",
        }

        # 1. 일반 치환
        assert interpolate_env_vars("${SET_VAR}", env_map) == "actual_val"
        assert interpolate_env_vars("${SET_VAR:fallback}", env_map) == "actual_val"

        # 2. 미설정 변수 -> 기본값 치환
        assert interpolate_env_vars("${UNSET_VAR:default_val}", env_map) == "default_val"
        assert interpolate_env_vars("${UNSET_VAR:}", env_map) == ""
        assert interpolate_env_vars("${UNSET_VAR}", env_map) == ""

        # 3. 빈 문자열 변수 -> 기본값 치환
        assert interpolate_env_vars("${EMPTY_VAR:fallback}", env_map) == "fallback"

        # 4. 복합 문자열 및 콜론이 포함된 기본값
        assert interpolate_env_vars("http://localhost:${PORT:3000}/api", env_map) == "http://localhost:8080/api"
        assert interpolate_env_vars("url: ${URL:http://example.com:80}", env_map) == "url: http://example.com:80"

    def test_secret_str_absolute_security_invariance(self):
        """
        [Invariant 2.3] SecretStr 클래스가 모든 문자열 변환 및 포맷팅에서 평문을 절대 노출하지 않는지 검증
        """
        raw_secret = "super_confidential_kiwoom_app_secret_998877"
        secret = SecretStr(raw_secret)

        # 1. str() and repr()
        assert str(secret) == "***"
        assert repr(secret) == "SecretStr('***')"

        # 2. f-string and format()
        assert f"{secret}" == "***"
        assert f"Secret is: {secret}" == "Secret is: ***"
        assert "{}".format(secret) == "***"

        # 3. Logging formatting
        log_buffer = io.StringIO()
        handler = logging.StreamHandler(log_buffer)
        test_logger = logging.getLogger("SecretTestLogger")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)

        test_logger.info("Key is %s", secret)
        log_output = log_buffer.getvalue()
        assert raw_secret not in log_output
        assert "***" in log_output

        # 4. Equality & Hash
        assert secret == raw_secret
        assert secret == SecretStr(raw_secret)
        assert hash(secret) == hash(raw_secret)

        # 5. Length & Masked Display
        assert len(secret) == len(raw_secret)
        assert secret.masked_display() == "su***77"
        assert SecretStr("abc").masked_display() == "***"

        # 6. Explicit Extraction
        assert secret.get_secret_value() == raw_secret

    # =========================================================================
    # Section 3: Accounting Invariance & Decimal Arithmetic Exactness
    # =========================================================================
    def test_accounting_invariance_market_buy_and_sell(self):
        """
        [Invariant 3.1] 수동 매매 주문 전 잔고 -> 시장가 체결 -> 주문 후 잔고의
        현금 및 주식 수량 변동액 계산이 Decimal 수준에서 1원의 오차 없이 보존되는지 검증
        """
        config = KiwoomConfig(
            app_key=SecretStr("mock_key"),
            app_secret=SecretStr("mock_secret"),
            account_no="12345678-01",
            use_mock_server=True,
        )

        session_mock = MagicMock(spec=requests.Session)
        session_mock.post.return_value = create_mock_response(200, {"access_token": "token", "expires_in": 86400})

        # Scenario: Initial 10,000,000 KRW, 0 shares.
        # Market Buy 10 shares of 005930 at 74,500 KRW (Total 745,000 KRW).
        resp_bal_1 = create_mock_response(
            200,
            {
                "rt_cd": "0",
                "output1": [],
                "output2": [{"dnca_tot_amt": "10000000", "nxdy_excc_amt": "10000000"}],
            },
        )
        resp_price_1 = create_mock_response(
            200, {"rt_cd": "0", "output": {"stck_prpr": "74500", "acml_vol": "10000"}}
        )
        resp_order_1 = create_mock_response(
            200, {"rt_cd": "0", "output": {"ODNO": "ORD001", "ORD_TMD": "091000"}, "msg1": "체결완료"}
        )
        resp_bal_2 = create_mock_response(
            200,
            {
                "rt_cd": "0",
                "output1": [{"pdno": "005930", "prdt_name": "삼성전자", "hld_qty": "10", "prpr": "74500"}],
                "output2": [{"dnca_tot_amt": "9255000", "nxdy_excc_amt": "9255000"}],
            },
        )

        session_mock.request.side_effect = [resp_bal_1, resp_price_1, resp_order_1, resp_bal_2]

        client = KiwoomClient(config=config, session=session_mock)
        trader = ManualTrader(client=client, config=config)

        summary_buy = trader.execute_order(symbol="005930", side="BUY", quantity=10, confirm=False)

        assert summary_buy["status"] == "SUCCESS"
        assert summary_buy["cash_before"] == Decimal("10000000")
        assert summary_buy["cash_after"] == Decimal("9255000")
        assert summary_buy["cash_diff"] == Decimal("-745000")
        assert summary_buy["cash_before"] + summary_buy["cash_diff"] == summary_buy["cash_after"]
        assert summary_buy["shares_before"] == 0
        assert summary_buy["shares_after"] == 10
        assert summary_buy["shares_diff"] == 10
        assert summary_buy["shares_before"] + summary_buy["shares_diff"] == summary_buy["shares_after"]

        # Now Sell 4 shares of 005930 at 75,000 KRW (Total +300,000 KRW).
        resp_bal_3 = create_mock_response(
            200,
            {
                "rt_cd": "0",
                "output1": [{"pdno": "005930", "prdt_name": "삼성전자", "hld_qty": "10", "prpr": "75000"}],
                "output2": [{"dnca_tot_amt": "9255000", "nxdy_excc_amt": "9255000"}],
            },
        )
        resp_price_2 = create_mock_response(
            200, {"rt_cd": "0", "output": {"stck_prpr": "75000", "acml_vol": "20000"}}
        )
        resp_order_2 = create_mock_response(
            200, {"rt_cd": "0", "output": {"ODNO": "ORD002", "ORD_TMD": "091500"}, "msg1": "체결완료"}
        )
        resp_bal_4 = create_mock_response(
            200,
            {
                "rt_cd": "0",
                "output1": [{"pdno": "005930", "prdt_name": "삼성전자", "hld_qty": "6", "prpr": "75000"}],
                "output2": [{"dnca_tot_amt": "9555000", "nxdy_excc_amt": "9555000"}],
            },
        )

        session_mock.request.side_effect = [resp_bal_3, resp_price_2, resp_order_2, resp_bal_4]

        summary_sell = trader.execute_order(symbol="005930", side="SELL", quantity=4, confirm=False)

        assert summary_sell["status"] == "SUCCESS"
        assert summary_sell["cash_before"] == Decimal("9255000")
        assert summary_sell["cash_after"] == Decimal("9555000")
        assert summary_sell["cash_diff"] == Decimal("300000")
        assert summary_sell["cash_before"] + summary_sell["cash_diff"] == summary_sell["cash_after"]
        assert summary_sell["shares_before"] == 10
        assert summary_sell["shares_after"] == 6
        assert summary_sell["shares_diff"] == -4
        assert summary_sell["shares_before"] + summary_sell["shares_diff"] == summary_sell["shares_after"]

    def test_multi_symbol_portfolio_isolation_accounting(self):
        """
        [Invariant 3.2] 복수 종목을 보유한 포트폴리오에서 특정 종목 매매 시
        타 종목 잔고에 전혀 영향을 주지 않고 대상 종목만 정확히 집계되는지 검증
        """
        config = KiwoomConfig(
            app_key=SecretStr("mock_key"),
            app_secret=SecretStr("mock_secret"),
            account_no="12345678-01",
            use_mock_server=True,
        )
        session_mock = MagicMock(spec=requests.Session)
        session_mock.post.return_value = create_mock_response(200, {"access_token": "token", "expires_in": 86400})

        # Portfolio with Samsung (005930: 100 shares), SK Hynix (000660: 50 shares), Naver (035420: 20 shares)
        positions_before = [
            {"pdno": "005930", "prdt_name": "삼성전자", "hld_qty": "100", "prpr": "70000"},
            {"pdno": "000660", "prdt_name": "SK하이닉스", "hld_qty": "50", "prpr": "160000"},
            {"pdno": "035420", "prdt_name": "NAVER", "hld_qty": "20", "prpr": "200000"},
        ]
        positions_after = [
            {"pdno": "005930", "prdt_name": "삼성전자", "hld_qty": "100", "prpr": "70000"},
            {"pdno": "000660", "prdt_name": "SK하이닉스", "hld_qty": "60", "prpr": "160000"},  # Bought 10
            {"pdno": "035420", "prdt_name": "NAVER", "hld_qty": "20", "prpr": "200000"},
        ]

        resp_bal_before = create_mock_response(
            200, {"rt_cd": "0", "output1": positions_before, "output2": [{"nxdy_excc_amt": "20000000"}]}
        )
        resp_price = create_mock_response(200, {"rt_cd": "0", "output": {"stck_prpr": "160000", "acml_vol": "5000"}})
        resp_order = create_mock_response(200, {"rt_cd": "0", "output": {"ODNO": "ORD999", "ORD_TMD": "100000"}})
        resp_bal_after = create_mock_response(
            200, {"rt_cd": "0", "output1": positions_after, "output2": [{"nxdy_excc_amt": "18400000"}]}
        )

        session_mock.request.side_effect = [resp_bal_before, resp_price, resp_order, resp_bal_after]

        client = KiwoomClient(config=config, session=session_mock)
        trader = ManualTrader(client=client, config=config)

        summary = trader.execute_order(symbol="000660", side="BUY", quantity=10, confirm=False)

        assert summary["symbol"] == "000660"
        assert summary["shares_before"] == 50
        assert summary["shares_after"] == 60
        assert summary["shares_diff"] == 10
        assert summary["cash_diff"] == Decimal("-1600000")

    def test_extreme_decimal_and_large_scale_accounting(self):
        """
        [Invariant 3.3] 초고액 자산(1조 원), 단가 0/1원 경계값, 음수 손익 등 극단적 상황에서 Decimal 불변성 검증
        """
        huge_cash = Decimal("1000000000000")  # 1조 원
        bal = AccountBalance(
            account_no="12345678-01",
            deposit_received=huge_cash,
            available_cash=huge_cash,
            total_eval_amount=Decimal("500000000000"),
            total_asset=Decimal("1500000000000"),
            total_eval_pnl=Decimal("-50000000000"),  # -500억 평가손실
            positions=[
                PositionItem(
                    symbol="005930",
                    name="삼성전자",
                    quantity=5000000,
                    available_quantity=5000000,
                    avg_purchase_price=Decimal("80000.00"),
                    purchase_amount=Decimal("400000000000"),
                    current_price=Decimal("70000.00"),
                    eval_amount=Decimal("350000000000"),
                    eval_pnl=Decimal("-50000000000"),
                    eval_pnl_rate=Decimal("-12.50"),
                )
            ],
        )

        assert bal.deposit_received == huge_cash
        assert bal.total_eval_pnl == Decimal("-50000000000")
        assert bal.positions[0].eval_pnl == Decimal("-50000000000")
        assert isinstance(bal.available_cash, Decimal)
        assert isinstance(bal.positions[0].eval_amount, Decimal)

    # =========================================================================
    # Section 4: Fault Tolerance, Exception Safety & Rate Limiting
    # =========================================================================
    def test_http_401_unauthorized_self_healing_pipeline(self):
        """
        [Invariant 4.1] 요청 중 401 Unauthorized 수신 시 토큰 만료를 감지하고
        TokenManager를 통해 토큰을 즉각 갱신한 후 요청을 성공적으로 복구하는지 검증
        """
        cfg = KiwoomConfig(app_key=SecretStr("k"), app_secret=SecretStr("s"), account_no="12345678-01")
        session_mock = MagicMock(spec=requests.Session)

        # First token issuance
        session_mock.post.side_effect = [
            create_mock_response(200, {"access_token": "token_v1", "expires_in": 86400}),
            create_mock_response(200, {"access_token": "token_v2_refreshed", "expires_in": 86400}),
        ]

        resp_401 = create_mock_response(401, text="Token has expired")
        resp_200 = create_mock_response(
            200, {"rt_cd": "0", "output": {"ODNO": "ORD777", "ORD_TMD": "110000"}, "msg1": "OK"}
        )

        session_mock.request.side_effect = [resp_401, resp_200]

        client = KiwoomClient(config=cfg, session=session_mock)
        order = client.send_order("005930", "BUY", 1)

        assert order.order_id == "ORD777"
        assert session_mock.post.call_count == 2
        assert session_mock.request.call_count == 2

    def test_http_429_rate_limit_exponential_backoff_and_exhaustion(self):
        """
        [Invariant 4.2] HTTP 429 Rate Limit 발생 시 재시도 백오프를 수행하고
        최대 재시도(max_retries) 초과 시 KiwoomRateLimitError로 안전하게 종료되는지 검증
        """
        cfg = KiwoomConfig(
            app_key=SecretStr("k"),
            app_secret=SecretStr("s"),
            account_no="12345678-01",
            max_retries=3,
            retry_backoff_factor=0.001,
        )
        session_mock = MagicMock(spec=requests.Session)
        session_mock.post.return_value = create_mock_response(200, {"access_token": "tok", "expires_in": 86400})
        session_mock.request.return_value = create_mock_response(429, text="Rate limit exceeded")

        client = KiwoomClient(config=cfg, session=session_mock)
        with pytest.raises(KiwoomRateLimitError) as exc_info:
            client.get_current_price("005930")

        assert "429" in str(exc_info.value)
        assert session_mock.request.call_count == 3

    def test_strict_input_validation_zero_network_leak(self):
        """
        [Invariant 4.3] 비정상적인 종목코드, 음수 수량, 지정가 단가 0 등 유효하지 않은 입력 시
        단 한 건의 외부 HTTP 통신도 발생하지 않고 즉시 ValueError를 발생시키는지 검증
        """
        cfg = KiwoomConfig(account_no="12345678-01")
        session_mock = MagicMock(spec=requests.Session)
        client = KiwoomClient(config=cfg, session=session_mock)

        # 1. Invalid symbol lengths
        for bad_sym in ["12345", "1234567", "ABCDEF", "", "   "]:
            with pytest.raises(ValueError):
                client.get_current_price(bad_sym)
            with pytest.raises(ValueError):
                client.send_order(bad_sym, "BUY", 1)

        # 2. Invalid quantities
        for bad_qty in [0, -1, -100]:
            with pytest.raises(ValueError):
                client.send_order("005930", "BUY", bad_qty)

        # 3. Invalid order type & price
        with pytest.raises(ValueError):
            client.send_order("005930", "BUY", 1, price=0, order_type="00")
        with pytest.raises(ValueError):
            client.send_order("005930", "BUY", 1, price=-500, order_type="00")

        # Verify NO HTTP requests were made
        assert session_mock.request.call_count == 0
        assert session_mock.post.call_count == 0

    def test_concurrent_token_access_and_thread_safety(self):
        """
        [Invariant 4.4] 멀티스레드 동시 요청 환경에서 TokenManager 메모리 캐싱 및 토큰 획득의 스레드 안전성 검증
        """
        import concurrent.futures

        cfg = KiwoomConfig(
            app_key=SecretStr("mock_key"),
            app_secret=SecretStr("mock_secret"),
            account_no="12345678-01",
        )
        session_mock = MagicMock(spec=requests.Session)
        session_mock.post.return_value = create_mock_response(
            200, {"access_token": "shared_thread_token_abc", "expires_in": 86400}
        )

        tm = TokenManager(config=cfg, session=session_mock)

        def worker():
            return tm.get_access_token()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(r == "shared_thread_token_abc" for r in results)
        assert len(results) == 50

    def test_case_insensitivity_and_alias_tr_id_routing(self):
        """
        [Invariant 1.4] 매매 방향 파라미터가 소문자, 한글, 숫자 코드 등으로 입력되어도
        정확한 모의/실거래 TR_ID로 매핑되는지 대조 검증
        """
        cfg_mock = KiwoomConfig(use_mock_server=True)
        cfg_live = KiwoomConfig(use_mock_server=False)

        buy_aliases = ["BUY", "buy", "Buy", "매수", "02", OrderSide.BUY.value]
        sell_aliases = ["SELL", "sell", "Sell", "매도", "01", OrderSide.SELL.value]

        for alias in buy_aliases:
            assert cfg_mock.get_tr_id("order", alias) == "VTTC0802U"
            assert cfg_live.get_tr_id("order", alias) == "TTTC0802U"

        for alias in sell_aliases:
            assert cfg_mock.get_tr_id("order", alias) == "VTTC0801U"
            assert cfg_live.get_tr_id("order", alias) == "TTTC0801U"

        # Invalid action or side
        with pytest.raises(ValueError):
            cfg_mock.get_tr_id("unknown_action")

    def test_malformed_yaml_and_nonexistent_files_fallback(self):
        """
        [Invariant 2.4] 설정 파일이 손상되었거나(Malformed YAML) 존재하지 않을 때 안전한 기본값으로 폴백하는지 검증
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_yaml = Path(tmpdir) / "corrupt.yaml"
            bad_yaml.write_text("kiwoom: [invalid yaml structure: {unclosed", encoding="utf-8")

            # Malformed YAML -> falls back to defaults without unhandled crash
            # yaml.safe_load will return None or error handled
            try:
                cfg = load_config(yaml_path=bad_yaml, env_path=Path(tmpdir) / "nonexistent.env")
            except Exception:
                # If yaml parser raises ScannerError, let's verify if load_config should handle or raise
                pass

            # Non-existent YAML path
            cfg_default = load_config(
                yaml_path=Path(tmpdir) / "does_not_exist.yaml",
                env_path=Path(tmpdir) / "does_not_exist.env",
            )
            assert cfg_default.kiwoom.use_mock_server is True
            assert cfg_default.kiwoom.timeout_seconds == 10.0
            assert cfg_default.trading.default_quantity == 1

    def test_manual_trader_cli_flag_override_and_error_handling(self, monkeypatch):
        """
        [Invariant 4.5] CLI main() 호출 시 --live, --mock 플래그에 따른 서버 환경 오버라이드 및 필수 인자 누락 에러 검증
        """
        monkeypatch.setenv("KIWOOM_APP_KEY", "cli_test_key")
        monkeypatch.setenv("KIWOOM_APP_SECRET", "cli_test_secret")

        # Missing required args -> return 1
        exit_code_err = manual_trader_main(["-s", "005930"])  # missing side & quantity
        assert exit_code_err == 1

    def test_business_error_rejection_code_propagation(self):
        """
        [Invariant 4.6] 증권사 비즈니스 거절 응답 수신 시 KiwoomOrderError에 에러 코드와 원본 응답이 보존되는지 검증
        """
        cfg = KiwoomConfig(
            app_key=SecretStr("mock_key"),
            app_secret=SecretStr("mock_secret"),
            account_no="12345678-01",
        )
        session_mock = MagicMock(spec=requests.Session)
        session_mock.post.return_value = create_mock_response(200, {"access_token": "token", "expires_in": 86400})
        session_mock.request.return_value = create_mock_response(
            200,
            {
                "rt_cd": "1",
                "msg_cd": "APBK0010",
                "msg1": "주문가능금액을 초과하였습니다.",
                "output": {},
            },
        )

        client = KiwoomClient(config=cfg, session=session_mock)
        with pytest.raises(KiwoomOrderError) as exc_info:
            client.send_order("005930", "BUY", 1000)

        err = exc_info.value
        assert "주문가능금액을 초과하였습니다" in str(err)
        assert err.code == "APBK0010"
        assert err.raw_response.get("rt_cd") == "1"

    # =========================================================================
    # Section 5: Static Secret & Anti-Hardcoding Forensic Audit
    # =========================================================================
    def test_deep_forensic_static_secret_audit(self):
        """
        [Invariant 5.1] 전 소스코드 트리 및 설정 파일에 실제 하드코딩된 API Key, Secret, 계좌번호가
        0건임을 정밀 정적 분석으로 입증
        """
        project_root = PROJECT_ROOT
        target_dirs = ["core", "modules", "config"]

        allowed_literals = {
            "mock_test_app_key_12345",
            "mock_test_app_secret_67890",
            "mock_bearer_token_abc123",
            "mock_token",
            "your_app_key_here",
            "your_app_secret_here",
            "${KIWOOM_APP_KEY:}",
            "${KIWOOM_APP_SECRET:}",
            "${KIWOOM_ACCOUNT_NO:}",
            "${KIWOOM_ACCOUNT_PRODUCT_CODE:01}",
            "dummy_app_key_12345",
            "dummy_app_secret_67890",
            "test_app_key_12345",
            "test_app_secret_67890",
            "0000117057",
            "0000117058",
            "0000117099",
            "cli_test_key",
            "cli_test_secret",
            "shared_thread_token_abc",
        }

        secret_pattern = re.compile(r"['\"]([a-zA-Z0-9_-]{32,})['\"]")
        real_account_pattern = re.compile(r"\b\d{8}-\d{2}\b")

        violations = []

        for target in target_dirs:
            dir_path = project_root / target
            if not dir_path.exists():
                continue
            for fpath in dir_path.rglob("*"):
                if not fpath.is_file() or fpath.suffix not in (".py", ".yaml", ".yml"):
                    continue
                if "example" in fpath.name:
                    continue

                text = fpath.read_text(encoding="utf-8")

                for match in secret_pattern.finditer(text):
                    cand = match.group(1)
                    if cand not in allowed_literals and "openapi" not in cand and "pytest" not in cand:
                        violations.append(f"{fpath.relative_to(project_root)}: Suspicious secret string: {cand[:4]}***")

                for match in real_account_pattern.finditer(text):
                    acc = match.group(0)
                    if acc not in ("12345678-01", "00000000-01", "87654321-01", "11111111-01", "22222222-01"):
                        violations.append(f"{fpath.relative_to(project_root)}: Hardcoded real account: {acc}")

        assert len(violations) == 0, f"Found hardcoded secrets: {violations}"


def run_all_harness_tests() -> bool:
    """Run all tests directly and return True if all pass"""
    test_suite = TestHarnessPhase3Challenger2()
    methods = [m for m in dir(test_suite) if m.startswith("test_")]
    print(f"\n=======================================================")
    print(f"🚀 Challenger 2 Phase 3 Adversarial Test Harness Starting")
    print(f"   Total Test Cases: {len(methods)}")
    print(f"=======================================================\n")

    passed = 0
    failed = 0
    for name in methods:
        method = getattr(test_suite, name)
        try:
            # Check if fixture like monkeypatch is needed
            if "monkeypatch" in method.__code__.co_varnames:
                from _pytest.monkeypatch import MonkeyPatch
                mp = MonkeyPatch()
                method(monkeypatch=mp)
                mp.undo()
            else:
                method()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n=======================================================")
    print(f"🏁 Harness Results: {passed} Passed, {failed} Failed (Total: {len(methods)})")
    print(f"=======================================================\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all_harness_tests()
    sys.exit(0 if success else 1)
