"""
core/kiwoom_api.py
==================
Auto Stock ML/RL Trader — Phase 3: 키움 REST API (2024) 통신 및 트레이딩 코어 모듈
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Iterator, List, Mapping, Optional, Union

import requests

from core.config import KiwoomConfig, SecretStr, get_config

logger = logging.getLogger("AutoStock.KiwoomAPI")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "3"  # 시장가 (키움 REST API 기준 3)
    LIMIT = "0"   # 지정가 (키움 REST API 기준 0)

# ==============================================================================
# Custom Exceptions Hierarchy
# ==============================================================================

class KiwoomAPIError(Exception):
    def __init__(self, message: str, code: Optional[str] = None, raw_response: Optional[Dict[str, Any]] = None, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.raw_response = raw_response or {}
        self.status_code = status_code

class KiwoomAuthError(KiwoomAPIError): pass
class TokenError(KiwoomAuthError): pass
class KiwoomOrderError(KiwoomAPIError): pass
class KiwoomQueryError(KiwoomAPIError): pass
class KiwoomRateLimitError(KiwoomAPIError): pass
class KiwoomNetworkError(KiwoomAPIError): pass

# ==============================================================================
# Data Models with Dual Object/Dict Interface
# ==============================================================================

@dataclass
class PriceQuote(Mapping[str, Any]):
    symbol: str
    current_price: Decimal
    price_change: Decimal
    change_rate: Decimal
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    volume: int
    trade_amount: Decimal
    raw_response: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol, "current_price": self.current_price, "price_change": self.price_change,
            "change_rate": self.change_rate, "open_price": self.open_price, "high_price": self.high_price,
            "low_price": self.low_price, "volume": self.volume, "trade_amount": self.trade_amount,
            "timestamp": self.timestamp.isoformat(), "raw_response": self.raw_response,
        }
    def __getitem__(self, key: str) -> Any: return self.to_dict()[key]
    def __iter__(self) -> Iterator[str]: return iter(self.to_dict())
    def __len__(self) -> int: return len(self.to_dict())


@dataclass
class OrderResult(Mapping[str, Any]):
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: int
    order_type: str
    order_time: str
    message: str
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id, "symbol": self.symbol, "side": self.side, "quantity": self.quantity,
            "price": self.price, "order_type": self.order_type, "order_time": self.order_time,
            "message": self.message, "raw_response": self.raw_response,
        }
    def __getitem__(self, key: str) -> Any: return self.to_dict()[key]
    def __iter__(self) -> Iterator[str]: return iter(self.to_dict())
    def __len__(self) -> int: return len(self.to_dict())


@dataclass
class PositionItem(Mapping[str, Any]):
    symbol: str
    name: str
    quantity: int
    available_quantity: int
    avg_purchase_price: Decimal
    purchase_amount: Decimal
    current_price: Decimal
    eval_amount: Decimal
    eval_pnl: Decimal
    eval_pnl_rate: Decimal
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol, "name": self.name, "quantity": self.quantity, "available_quantity": self.available_quantity,
            "avg_purchase_price": self.avg_purchase_price, "purchase_amount": self.purchase_amount, "current_price": self.current_price,
            "eval_amount": self.eval_amount, "eval_pnl": self.eval_pnl, "eval_pnl_rate": self.eval_pnl_rate, "raw_response": self.raw_response,
        }
    def __getitem__(self, key: str) -> Any: return self.to_dict()[key]
    def __iter__(self) -> Iterator[str]: return iter(self.to_dict())
    def __len__(self) -> int: return len(self.to_dict())


@dataclass
class AccountBalance(Mapping[str, Any]):
    account_no: str
    deposit_received: Decimal
    available_cash: Decimal
    total_eval_amount: Decimal
    total_asset: Decimal
    total_eval_pnl: Decimal
    positions: List[PositionItem] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_no": self.account_no, "deposit_received": self.deposit_received, "available_cash": self.available_cash,
            "total_eval_amount": self.total_eval_amount, "total_asset": self.total_asset, "total_eval_pnl": self.total_eval_pnl,
            "positions": [pos.to_dict() for pos in self.positions], "timestamp": self.timestamp.isoformat(), "raw_response": self.raw_response,
        }
    def __getitem__(self, key: str) -> Any: return self.to_dict()[key]
    def __iter__(self) -> Iterator[str]: return iter(self.to_dict())
    def __len__(self) -> int: return len(self.to_dict())

# ==============================================================================
# Token Manager (OAuth 2.0 Caching & Auto-Refresh)
# ==============================================================================

class TokenManager:
    def __init__(self, config: KiwoomConfig, session: Optional[requests.Session] = None) -> None:
        self.config = config
        self.session = session or requests.Session()
        self._access_token: Optional[str] = None
        self._expires_at: Optional[datetime] = None
        self._lock = threading.Lock()

    def is_expired(self, buffer_seconds: int = 600) -> bool:
        if not self._access_token or not self._expires_at:
            return True
        return datetime.now() + timedelta(seconds=buffer_seconds) >= self._expires_at

    def get_access_token(self, force_refresh: bool = False) -> str:
        if force_refresh or self.is_expired():
            with self._lock:
                if force_refresh or self.is_expired():
                    self.refresh_token()
        return self._access_token or ""

    def revoke_token(self) -> bool:
        """캐시된 액세스 토큰 및 만료 시각을 초기화합니다."""
        with self._lock:
            self._access_token = None
            self._expires_at = None
        return True

    def refresh_token(self) -> str:
        url = f"{self.config.base_url}/oauth2/token"
        app_key = self.config.app_key.get_secret_value()
        app_secret = self.config.app_secret.get_secret_value()

        if not app_key or not app_secret:
            raise KiwoomAuthError("API 키 또는 시크릿이 설정되지 않았습니다.")

        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_secret,
        }
        headers = {"Content-Type": "application/json;charset=UTF-8", "User-Agent": USER_AGENT}

        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=self.config.timeout_seconds)
        except requests.exceptions.RequestException as e:
            raise KiwoomNetworkError(f"토큰 발급 통신 오류: {e}") from e

        data = resp.json() if resp.text else {}
        token = data.get("token") or data.get("access_token")

        if not token:
            raise KiwoomAuthError(f"토큰 발급 실패: {data.get('return_msg', resp.text)}", raw_response=data)

        # Parse expires_dt (e.g. 20260903102555) or expires_in
        expires_dt_str = data.get("expires_dt")
        if expires_dt_str and len(str(expires_dt_str)) == 14:
            self._expires_at = datetime.strptime(str(expires_dt_str), "%Y%m%d%H%M%S")
        elif "expires_in" in data:
            self._expires_at = datetime.now() + timedelta(seconds=int(data["expires_in"]))
        else:
            self._expires_at = datetime.now() + timedelta(hours=23)

        self._access_token = str(token)
        logger.info("Kiwoom Access Token이 갱신되었습니다.")
        return self._access_token


# ==============================================================================
# Kiwoom Client / API Engine
# ==============================================================================

class KiwoomClient:
    def __init__(self, config: Optional[KiwoomConfig] = None, session: Optional[requests.Session] = None) -> None:
        if config is None:
            config = get_config().kiwoom
        self.config = config
        self.session = session or requests.Session()
        self.token_manager = TokenManager(self.config, self.session)

    def __enter__(self) -> "KiwoomClient": return self
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: self.close()
    def close(self) -> None:
        if self.session: self.session.close()

    def _get_common_headers(self, tr_id: str) -> Dict[str, str]:
        token = self.token_manager.get_access_token()
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "api-id": tr_id,
            "User-Agent": USER_AGENT,
        }

    def _request(
        self,
        method: str,
        path: str,
        tr_id: str,
        json_data: Optional[Dict[str, Any]] = None,
        is_order: bool = False,
        retry_on_401: bool = True,
    ) -> Dict[str, Any]:
        url = f"{self.config.base_url}{path}"
        max_attempts = max(1, self.config.max_retries)
        last_exception: Optional[Exception] = None

        for attempt in range(max_attempts):
            headers = self._get_common_headers(tr_id=tr_id)
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    timeout=self.config.timeout_seconds,
                )
            except requests.exceptions.Timeout as e:
                last_exception = KiwoomNetworkError(f"네트워크 타임아웃 오류: {e}")
                time.sleep(self.config.retry_backoff_factor * (2 ** attempt))
                continue
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
                last_exception = KiwoomNetworkError(f"네트워크 통신 장애: {e}")
                time.sleep(self.config.retry_backoff_factor * (2 ** attempt))
                continue

            if resp.status_code == 401 and retry_on_401:
                self.token_manager.get_access_token(force_refresh=True)
                return self._request(method, path, tr_id, json_data, is_order=is_order, retry_on_401=False)

            if resp.status_code == 429:
                last_exception = KiwoomRateLimitError("요청 한도 초과 (HTTP 429)", status_code=429)
                time.sleep(self.config.retry_backoff_factor * (2 ** attempt) + 0.1)
                continue

            if resp.status_code >= 500:
                last_exception = KiwoomAPIError(f"서버 내부 오류 (HTTP {resp.status_code})", status_code=resp.status_code)
                time.sleep(self.config.retry_backoff_factor * (2 ** attempt))
                continue

            data = resp.json() if resp.text else {}

            # Kiwoom returns return_code: 0 for success
            rt_cd = str(data.get("return_code", "0")).strip()
            if rt_cd != "0":
                msg = data.get("msg1") or data.get("return_msg") or f"API 에러 (code={rt_cd})"
                code = data.get("msg_cd") or data.get("return_code") or rt_cd
                if is_order:
                    raise KiwoomOrderError(msg, code=code, raw_response=data)
                raise KiwoomQueryError(msg, code=code, raw_response=data)

            return data

        raise last_exception or KiwoomAPIError("최대 재시도 초과")

    def get_current_price(self, symbol: str) -> PriceQuote:
        symbol_clean = str(symbol).strip()
        if not re.match(r"^\d{6}$", symbol_clean):
            raise ValueError(f"유효하지 않은 6자리 종목코드입니다: '{symbol}'")

        path = "/api/dostk/stkinfo"
        tr_id = "ka10001"
        payload = {"stk_cd": symbol_clean}

        res = self._request("POST", path, tr_id=tr_id, json_data=payload)

        output = res.get("output", {}) if isinstance(res.get("output"), dict) else {}

        def _get_val(*keys: str, default: Any = 0) -> Any:
            for k in keys:
                if k in output and output[k] is not None:
                    return output[k]
                if k in res and res[k] is not None:
                    return res[k]
            return default

        cur_p = _get_val("stck_prpr", "cur_prc", default=0)
        current_price = Decimal(str(abs(int(Decimal(str(cur_p or 0))))))

        diff_p = _get_val("prdy_vrss", "pred_pre", default=0)
        price_change = Decimal(str(diff_p or 0))

        rate_p = _get_val("prdy_ctrt", "flu_rt", default="0.0")
        change_rate = Decimal(str(rate_p or "0.0"))

        open_p = _get_val("stck_oprc", "open_pric", default=0)
        open_price = Decimal(str(abs(int(Decimal(str(open_p or 0))))))

        high_p = _get_val("stck_hgpr", "high_pric", default=0)
        high_price = Decimal(str(abs(int(Decimal(str(high_p or 0))))))

        low_p = _get_val("stck_lwpr", "low_pric", default=0)
        low_price = Decimal(str(abs(int(Decimal(str(low_p or 0))))))

        vol_p = _get_val("acml_vol", "trde_qty", default=0)
        volume = int(Decimal(str(vol_p or 0)))

        trade_amount_val = _get_val("acml_tr_pbmn", "trade_amount", default=0)
        trade_amount = Decimal(str(trade_amount_val or 0))

        return PriceQuote(
            symbol=symbol_clean,
            current_price=current_price,
            price_change=price_change,
            change_rate=change_rate,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            volume=volume,
            trade_amount=trade_amount,
            raw_response=res,
        )

    def send_order(
        self,
        symbol: str,
        side: Union[str, OrderSide],
        quantity: int,
        price: int = 0,
        order_type: Union[str, OrderType] = "3",
    ) -> OrderResult:
        symbol_clean = str(symbol).strip()
        if not re.match(r"^\d{6}$", symbol_clean):
            raise ValueError(f"유효하지 않은 6자리 종목코드입니다: '{symbol}'")

        side_raw = str(side.value if isinstance(side, OrderSide) else side).upper().strip()
        if side_raw not in ("BUY", "SELL", "01", "02", "매수", "매도"):
            raise ValueError(f"지원하지 않는 주문 방향입니다: '{side}' ('BUY' 또는 'SELL')")
        is_buy = side_raw in ("BUY", "02", "매수")
        normalized_side = "BUY" if is_buy else "SELL"

        if int(quantity) <= 0:
            raise ValueError(f"주문 수량은 1 이상의 양수여야 합니다: {quantity}")

        if isinstance(order_type, OrderType):
            type_code = order_type.value
            type_name = order_type.name
        else:
            type_str = str(order_type).strip()
            if type_str in ("3", "MARKET", "market"):
                type_code = "3"
                type_name = "MARKET"
            elif type_str in ("0", "00", "LIMIT", "limit"):
                type_code = "0"
                type_name = "LIMIT"
            else:
                type_code = type_str
                type_name = type_str

        if type_name == "LIMIT" and int(price) <= 0:
            raise ValueError(f"지정가 주문은 0원보다 큰 단가를 지정해야 합니다: {price}")

        path = "/api/dostk/ordr"
        tr_id = "kt10000" if is_buy else "kt10001"
        payload = {
            "dmst_stex_tp": "KRX",
            "stk_cd": symbol_clean,
            "ord_qty": str(quantity),
            "ord_uv": str(price),
            "trde_tp": type_code,
        }

        res = self._request("POST", path, tr_id=tr_id, json_data=payload, is_order=True)

        output = res.get("output", {}) if isinstance(res.get("output"), dict) else {}
        ord_no = (
            res.get("ord_no")
            or res.get("ODNO")
            or output.get("ODNO")
            or output.get("ord_no")
            or output.get("ORD_NO")
            or ""
        )
        msg = res.get("msg1") or res.get("return_msg") or output.get("msg1") or "주문 접수"

        return OrderResult(
            order_id=str(ord_no),
            symbol=symbol_clean,
            side=normalized_side,
            quantity=int(quantity),
            price=int(price),
            order_type=type_name,
            order_time=datetime.now().strftime("%H%M%S"),
            message=str(msg),
            raw_response=res,
        )

    def get_account_balance(self) -> AccountBalance:
        path = "/api/dostk/acnt"
        tr_id = "kt00018"
        payload = {"qry_tp": "1", "dmst_stex_tp": "KRX"}

        res = self._request("POST", path, tr_id=tr_id, json_data=payload)

        positions: List[PositionItem] = []
        raw_positions = res.get("acnt_evlt_remn_indv_tot") or res.get("output1") or []
        if isinstance(raw_positions, dict):
            raw_positions = [raw_positions]
        for item in raw_positions:
            if not isinstance(item, dict):
                continue
            pdno = str(item.get("stk_cd") or item.get("pdno") or item.get("iscd") or "").strip()
            if not pdno:
                continue
            hld_qty = int(Decimal(str(item.get("hld_qty") or item.get("hldg_qty") or 0)))
            if hld_qty <= 0:
                continue
            ord_psbl_qty = int(Decimal(str(item.get("ord_psbl_qty") or item.get("ord_possible_qty") or hld_qty)))
            pchs_avg_uv = Decimal(str(item.get("pchs_avg_uv") or item.get("pchs_avg_pric") or 0))
            pchs_amt = Decimal(str(item.get("pchs_amt") or item.get("pchs_amt_tot") or 0))
            cur_prc = Decimal(str(item.get("cur_prc") or item.get("prpr") or 0))
            evlu_amt = Decimal(str(item.get("evlt_amt") or item.get("evlu_amt") or 0))
            evlu_pl = Decimal(str(item.get("evlt_pl") or item.get("evlu_pfls_amt") or 0))
            evlu_rt = Decimal(str(item.get("prft_rt") or item.get("evlu_pfls_rt") or 0))

            positions.append(
                PositionItem(
                    symbol=pdno,
                    name=str(item.get("stk_nm") or item.get("prdt_name") or item.get("name") or ""),
                    quantity=hld_qty,
                    available_quantity=ord_psbl_qty,
                    avg_purchase_price=pchs_avg_uv,
                    purchase_amount=pchs_amt,
                    current_price=cur_prc,
                    eval_amount=evlu_amt,
                    eval_pnl=evlu_pl,
                    eval_pnl_rate=evlu_rt,
                    raw_response=item,
                )
            )

        summary: Dict[str, Any] = {}
        if isinstance(res.get("output2"), list) and len(res["output2"]) > 0:
            summary = res["output2"][0]
        elif isinstance(res.get("output2"), dict):
            summary = res["output2"]

        deposit_received = Decimal(str(res.get("prsm_dpst_aset_amt") or summary.get("dnca_tot_amt") or summary.get("deposit_received") or 0))
        available_cash = Decimal(str(summary.get("nxdy_excc_amt") or res.get("ord_psbl_cash") or deposit_received))
        total_eval_amount = Decimal(str(res.get("tot_evlt_amt") or summary.get("tot_evlu_amt") or 0))
        total_eval_pnl = Decimal(str(res.get("tot_evlt_pl") or summary.get("evlu_pfls_smtl_amt") or 0))
        total_asset = Decimal(str(summary.get("nass_amt") or (deposit_received + total_eval_amount)))

        return AccountBalance(
            account_no=self.config.account_no,
            deposit_received=deposit_received,
            available_cash=available_cash,
            total_eval_amount=total_eval_amount,
            total_asset=total_asset,
            total_eval_pnl=total_eval_pnl,
            positions=positions,
            raw_response=res,
        )

    def get_account_positions(self, account_no: Optional[str] = None) -> List[PositionItem]:
        """계좌 보유 종목 리스트를 반환합니다."""
        balance = self.get_account_balance()
        return balance.positions

    def revoke_token(self) -> bool:
        """토큰 폐기 및 캐시 초기화"""
        return self.token_manager.revoke_token()


KiwoomAPI = KiwoomClient
