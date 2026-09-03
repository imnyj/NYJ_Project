"""
.agents/victory_auditor_3/independent_verifier.py
=================================================
Independent Victory Audit Verification Script for Phase 3 (Auto Stock ML/RL Trader)
Zero trust, independent test runner for R1, R2, R3 and Acceptance Criteria.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from decimal import Decimal
from unittest.mock import MagicMock, patch
import requests

from core.config import KiwoomConfig, SecretStr, load_config, get_config
from core.kiwoom_api import KiwoomClient, TokenManager, PriceQuote, OrderResult, AccountBalance, PositionItem
from modules.engine.manual_trader import ManualTrader, main as manual_trader_main

def test_r1_kiwoom_api_core():
    print(">> [Check 1] R1. Kiwoom REST API Integration & Server Toggle")
    
    # 1. Config & URL / TR_ID mapping check
    cfg_mock = KiwoomConfig(
        app_key=SecretStr("mock_key"),
        app_secret=SecretStr("mock_secret"),
        account_no="12345678-01",
        use_mock_server=True,
    )
    assert cfg_mock.base_url == "https://openapivts.kiwoom.com", f"Mock URL mismatch: {cfg_mock.base_url}"
    assert cfg_mock.get_tr_id("order", "BUY") == "VTTC0802U", f"Mock Buy TR_ID mismatch: {cfg_mock.get_tr_id('order', 'BUY')}"
    assert cfg_mock.get_tr_id("order", "SELL") == "VTTC0801U", f"Mock Sell TR_ID mismatch: {cfg_mock.get_tr_id('order', 'SELL')}"
    assert cfg_mock.get_tr_id("inquire_balance") == "VTTC8434R", f"Mock Balance TR_ID mismatch: {cfg_mock.get_tr_id('inquire_balance')}"
    assert cfg_mock.get_tr_id("inquire_price") == "FHKST01010100", f"Mock Price TR_ID mismatch"

    cfg_live = KiwoomConfig(
        app_key=SecretStr("live_key"),
        app_secret=SecretStr("live_secret"),
        account_no="12345678-01",
        use_mock_server=False,
    )
    assert cfg_live.base_url == "https://openapi.kiwoom.com", f"Live URL mismatch: {cfg_live.base_url}"
    assert cfg_live.get_tr_id("order", "BUY") == "TTTC0802U", f"Live Buy TR_ID mismatch: {cfg_live.get_tr_id('order', 'BUY')}"
    assert cfg_live.get_tr_id("order", "SELL") == "TTTC0801U", f"Live Sell TR_ID mismatch: {cfg_live.get_tr_id('order', 'SELL')}"
    assert cfg_live.get_tr_id("inquire_balance") == "TTTC8434R", f"Live Balance TR_ID mismatch: {cfg_live.get_tr_id('inquire_balance')}"

    # 2. Mocking Token issue -> Price -> Order -> Balance pipeline
    session_mock = requests.Session()
    
    # Token POST mock
    mock_token_resp = requests.Response()
    mock_token_resp.status_code = 200
    mock_token_resp.json = MagicMock(return_value={"access_token": "verified_token_xyz", "expires_in": 3600})
    
    # Price GET mock
    mock_price_resp = requests.Response()
    mock_price_resp.status_code = 200
    mock_price_resp.json = MagicMock(return_value={
        "rt_cd": "0",
        "output": {
            "iscd": "005930",
            "stck_prpr": "75000",
            "prdy_vrss": "1000",
            "prdy_ctrt": "1.35",
            "stck_oprc": "74500",
            "stck_hgpr": "75500",
            "stck_lwpr": "74200",
            "acml_vol": "15000000",
            "acml_tr_pbmn": "1000000000000",
        }
    })

    # Order POST mock
    mock_order_resp = requests.Response()
    mock_order_resp.status_code = 200
    mock_order_resp.json = MagicMock(return_value={
        "rt_cd": "0",
        "msg1": "주문 전송이 완료되었습니다.",
        "output": {"ODNO": "0000998877", "ORD_TMD": "103000"}
    })

    # Balance GET mock
    mock_bal_resp = requests.Response()
    mock_bal_resp.status_code = 200
    mock_bal_resp.json = MagicMock(return_value={
        "rt_cd": "0",
        "output1": [{
            "pdno": "005930",
            "prdt_name": "삼성전자",
            "hld_qty": "10",
            "ord_psbl_qty": "10",
            "pchs_avg_pric": "75000.0000",
            "pchs_amt": "750000",
            "prpr": "75000",
            "evlu_amt": "750000",
            "evlu_pfls_amt": "0",
            "evlu_pfls_rt": "0.0",
        }],
        "output2": [{
            "dnca_tot_amt": "9250000",
            "nxdy_excc_amt": "9250000",
            "tot_evlu_amt": "750000",
            "nass_amt": "10000000",
            "evlu_pfls_smtl_amt": "0",
        }]
    })

    with patch.object(session_mock, "post", return_value=mock_token_resp), \
         patch.object(session_mock, "request") as mock_req:
        
        mock_req.side_effect = [mock_price_resp, mock_order_resp, mock_bal_resp]
        
        client = KiwoomClient(config=cfg_mock, session=session_mock)
        
        # Token
        tok = client.get_access_token()
        assert tok == "verified_token_xyz", f"Token issue failed: {tok}"
        
        # Price
        quote = client.get_current_price("005930")
        assert quote.symbol == "005930"
        assert quote.current_price == Decimal("75000")
        assert quote.volume == 15000000
        
        # Order
        order = client.send_order(symbol="005930", side="BUY", quantity=10)
        assert order.order_id == "0000998877"
        assert order.side == "BUY"
        assert order.quantity == 10
        assert order.order_type == "MARKET"
        
        # Balance
        bal = client.get_account_balance()
        assert bal.available_cash == Decimal("9250000")
        assert len(bal.positions) == 1
        assert bal.positions[0].symbol == "005930"
        assert bal.positions[0].quantity == 10

    print(">> [Check 1] PASS: R1 Kiwoom REST API Core & Toggle verified.")


def test_r2_manual_trading_cli():
    print(">> [Check 2] R2. Manual Trading Interface & Balance Tracking")
    
    cfg = KiwoomConfig(
        app_key=SecretStr("mock_key"),
        app_secret=SecretStr("mock_secret"),
        account_no="12345678-01",
        use_mock_server=True,
    )
    
    session_mock = requests.Session()
    
    # Mock responses for:
    # 1. Balance Before (10,000,000 cash, 0 shares)
    # 2. Price quote (75,000 KRW)
    # 3. Order send (ODNO=0000123456)
    # 4. Balance After (9,250,000 cash, 10 shares)
    
    mock_token = requests.Response()
    mock_token.status_code = 200
    mock_token.json = MagicMock(return_value={"access_token": "token_abc", "expires_in": 3600})
    
    b_before = requests.Response()
    b_before.status_code = 200
    b_before.json = MagicMock(return_value={
        "rt_cd": "0", "output1": [], "output2": [{"dnca_tot_amt": "10000000", "nxdy_excc_amt": "10000000"}]
    })
    
    price_res = requests.Response()
    price_res.status_code = 200
    price_res.json = MagicMock(return_value={
        "rt_cd": "0", "output": {"stck_prpr": "75000", "acml_vol": "100"}
    })
    
    order_res = requests.Response()
    order_res.status_code = 200
    order_res.json = MagicMock(return_value={
        "rt_cd": "0", "msg1": "주문 성공", "output": {"ODNO": "0000123456", "ORD_TMD": "110000"}
    })
    
    b_after = requests.Response()
    b_after.status_code = 200
    b_after.json = MagicMock(return_value={
        "rt_cd": "0",
        "output1": [{"pdno": "005930", "prdt_name": "삼성전자", "hld_qty": "10", "prpr": "75000"}],
        "output2": [{"dnca_tot_amt": "9250000", "nxdy_excc_amt": "9250000"}]
    })

    with patch.object(session_mock, "post", return_value=mock_token), \
         patch.object(session_mock, "request") as mock_req:
        
        mock_req.side_effect = [b_before, price_res, order_res, b_after]
        
        client = KiwoomClient(config=cfg, session=session_mock)
        trader = ManualTrader(client=client, config=cfg)
        
        summary = trader.execute_order(
            symbol="005930",
            side="BUY",
            quantity=10,
            price=0,
            order_type="01",
            confirm=False,
        )
        
        assert summary["status"] == "SUCCESS"
        assert summary["symbol"] == "005930"
        assert summary["side"] == "BUY"
        assert summary["quantity"] == 10
        assert summary["cash_diff"] == Decimal("-750000")
        assert summary["shares_diff"] == 10
        assert summary["order_result"].order_id == "0000123456"

    print(">> [Check 2] PASS: R2 Manual Trading Interface verified.")


def test_r3_secret_management():
    print(">> [Check 3] R3. Secret Management & Non-Hardcoding")
    
    # 1. Test SecretStr encapsulation
    s = SecretStr("actual_secret_token_never_printed")
    assert str(s) == "***", f"String exposure: {str(s)}"
    assert repr(s) == "SecretStr('***')", f"Repr exposure: {repr(s)}"
    assert f"log: {s}" == "log: ***", f"f-string exposure: {f'log: {s}'}"
    assert s.get_secret_value() == "actual_secret_token_never_printed"
    
    # 2. Verify settings.yaml structure
    app_cfg = load_config()
    assert isinstance(app_cfg.kiwoom.app_key, SecretStr)
    assert isinstance(app_cfg.kiwoom.app_secret, SecretStr)
    
    print(">> [Check 3] PASS: R3 Secret Management verified.")


if __name__ == "__main__":
    test_r1_kiwoom_api_core()
    test_r2_manual_trading_cli()
    test_r3_secret_management()
    print("\n=======================================================")
    print("ALL INDEPENDENT AUDIT VERIFICATION CHECKS PASSED (100%)")
    print("=======================================================")
