"""
modules/engine/manual_trader.py
===============================
Auto Stock ML/RL Trader — Phase 3: 수동 매매 제어기 (Manual Trading CLI Controller)

CLI 환경에서 종목 코드, 매매 방향(BUY/SELL), 수량을 입력받아 시장가/지정가 주문을 전송하고,
주문 체결 전/후 계좌 잔고 및 보유 종목 변동 내역을 시각화하여 출력합니다.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from core.config import KiwoomConfig, get_config
from core.kiwoom_api import (
    AccountBalance,
    KiwoomAPIError,
    KiwoomClient,
    OrderResult,
    OrderSide,
    OrderType,
    PriceQuote,
)

logger = logging.getLogger("AutoStock.ManualTrader")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ManualTrader:
    """
    CLI 기반 수동 매매 제어기.
    - 주문 전 잔고 및 현재가 확인
    - 주문 전송 (시장가/지정가)
    - 주문 체결 후 잔고 변동 내역 시각화 리포트 출력
    """

    def __init__(
        self,
        client: Optional[KiwoomClient] = None,
        config: Optional[KiwoomConfig] = None,
    ) -> None:
        if config is None:
            config = get_config().kiwoom
        self.config = config
        self.client = client or KiwoomClient(config=self.config)
        self.console = Console() if RICH_AVAILABLE else None

    def validate_inputs(
        self,
        symbol: str,
        side: str,
        quantity: Union[int, str],
        price: Union[int, str] = 0,
    ) -> Tuple[str, str, int, int]:
        """
        주문 파라미터의 유효성을 엄격하게 검증하고 정규화합니다.
        
        Returns:
            Tuple[symbol: str, side: str, quantity: int, price: int]
        """
        # 1. 종목코드 검증 (6자리 숫자)
        symbol_clean = str(symbol).strip()
        if not re.match(r"^[0-9]{6}$", symbol_clean):
            raise ValueError(f"유효하지 않은 종목코드입니다: '{symbol}' (6자리 숫자로 입력하십시오)")

        # 2. 매매 방향 검증
        side_clean = str(side).upper().strip()
        if side_clean in ("BUY", "02", "매수"):
            side_norm = "BUY"
        elif side_clean in ("SELL", "01", "매도"):
            side_norm = "SELL"
        else:
            raise ValueError(f"유효하지 않은 매매 방향입니다: '{side}' ('BUY' 또는 'SELL'로 입력하십시오)")

        # 3. 주문 수량 검증
        try:
            qty_int = int(quantity)
        except (ValueError, TypeError) as e:
            raise ValueError(f"주문 수량은 정수여야 합니다: '{quantity}'") from e

        if qty_int <= 0:
            raise ValueError(f"주문 수량은 1 이상의 양수여야 합니다: {qty_int}")

        # 4. 주문 단가 검증
        try:
            price_int = int(price)
        except (ValueError, TypeError) as e:
            raise ValueError(f"주문 단가는 정수여야 합니다: '{price}'") from e

        if price_int < 0:
            raise ValueError(f"주문 단가는 0 이상의 정수여야 합니다: {price_int}")

        return symbol_clean, side_norm, qty_int, price_int

    def execute_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: int = 0,
        order_type: str = "01",
        confirm: bool = False,
    ) -> Dict[str, Any]:
        """
        수동 매매 주문을 실행하고 전/후 잔고 변동 요약을 반환 및 출력합니다.
        """
        symbol_clean, side_norm, qty_int, price_int = self.validate_inputs(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        )

        # 1. 주문 전 계좌 잔고 조회
        try:
            balance_before = self.client.get_account_balance()
        except Exception as e:
            logger.warning("주문 전 잔고 조회 실패 (주문 계속 진행): %s", e)
            balance_before = AccountBalance(
                account_no=self.config.account_no,
                deposit_received=Decimal(0),
                available_cash=Decimal(0),
                total_eval_amount=Decimal(0),
                total_asset=Decimal(0),
                total_eval_pnl=Decimal(0),
            )

        # 2. 현재가 조회 (사전 점검용)
        try:
            quote = self.client.get_current_price(symbol_clean)
            current_price = quote.current_price
        except Exception as e:
            logger.warning("현재가 조회 실패: %s", e)
            current_price = Decimal(price_int if price_int > 0 else 0)

        # 3. 사전 잔고 / 보유 수량 체크
        if side_norm == "BUY":
            est_cost = (Decimal(price_int) if price_int > 0 else current_price) * qty_int
            if balance_before.available_cash > 0 and est_cost > balance_before.available_cash:
                logger.warning(
                    "예수금 부족 경고: 필요 추정금액 %s원 > 출금가능현금 %s원",
                    format(int(est_cost), ","),
                    format(int(balance_before.available_cash), ","),
                )
        elif side_norm == "SELL":
            held_qty = sum(
                p.quantity for p in balance_before.positions if p.symbol == symbol_clean
            )
            if held_qty < qty_int:
                logger.warning(
                    "보유 수량 부족 경고: 매도 요청 %d주 > 보유 수량 %d주",
                    qty_int,
                    held_qty,
                )

        # 4. 사용자 확인 프롬프트 (confirm=True인 경우)
        if confirm:
            server_type = "모의투자(Mock)" if self.config.use_mock_server else "실거래(LIVE) [주의!]"
            prompt_msg = (
                f"\n[주문 확인] 서버: {server_type}\n"
                f"종목: {symbol_clean} | 방향: {side_norm} | 수량: {qty_int}주 | "
                f"유형: {'시장가' if order_type == '01' else f'지정가({price_int}원)'}\n"
                f"정말 주문을 전송하시겠습니까? (y/N): "
            )
            ans = input(prompt_msg).strip().lower()
            if ans not in ("y", "yes"):
                print("주문이 사용자에 의해 취소되었습니다.")
                return {"status": "CANCELLED", "symbol": symbol_clean}

        # 5. 주문 전송
        order_result = self.client.send_order(
            symbol=symbol_clean,
            side=side_norm,
            quantity=qty_int,
            price=price_int,
            order_type=order_type,
        )

        # 6. 주문 후 계좌 잔고 조회
        try:
            balance_after = self.client.get_account_balance()
        except Exception as e:
            logger.warning("주문 후 잔고 조회 실패: %s", e)
            balance_after = balance_before

        # 7. 변동 내역 산출
        cash_before = balance_before.available_cash
        cash_after = balance_after.available_cash
        cash_diff = cash_after - cash_before

        shares_before = sum(
            p.quantity for p in balance_before.positions if p.symbol == symbol_clean
        )
        shares_after = sum(
            p.quantity for p in balance_after.positions if p.symbol == symbol_clean
        )
        shares_diff = shares_after - shares_before

        summary: Dict[str, Any] = {
            "status": "SUCCESS",
            "order_result": order_result,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "cash_before": cash_before,
            "cash_after": cash_after,
            "cash_diff": cash_diff,
            "shares_before": shares_before,
            "shares_after": shares_after,
            "shares_diff": shares_diff,
            "symbol": symbol_clean,
            "side": side_norm,
            "quantity": qty_int,
            "price": price_int,
            "current_price": current_price,
            "use_mock_server": self.config.use_mock_server,
        }

        # 8. 잔고 변동 시각화 출력
        self.display_balance_report(summary)
        return summary

    def display_balance_report(self, summary: Dict[str, Any]) -> str:
        """
        주문 전/후 잔고 변동 내역을 포맷팅하여 콘솔에 출력합니다.
        """
        if summary.get("status") != "SUCCESS":
            return "주문이 실행되지 않았습니다."

        order_res: OrderResult = summary["order_result"]
        symbol = summary["symbol"]
        side = summary["side"]
        qty = summary["quantity"]
        cash_before = summary["cash_before"]
        cash_after = summary["cash_after"]
        cash_diff = summary["cash_diff"]
        shares_before = summary["shares_before"]
        shares_after = summary["shares_after"]
        shares_diff = summary["shares_diff"]
        server_str = "모의투자 (Mock Server)" if summary["use_mock_server"] else "실거래 (Live Server)"

        if RICH_AVAILABLE and self.console:
            table = Table(title="[bold green]수동 주문 체결 및 계좌 잔고 변동 리포트[/bold green]", show_header=True)
            table.add_column("구분 항목", style="cyan", justify="left")
            table.add_column("주문 전 (Before)", justify="right")
            table.add_column("주문 후 (After)", justify="right")
            table.add_column("변동액 (Diff)", style="bold", justify="right")

            cash_diff_str = (
                f"+{format(int(cash_diff), ',')} 원" if cash_diff > 0
                else f"{format(int(cash_diff), ',')} 원"
            )
            shares_diff_str = (
                f"+{shares_diff} 주" if shares_diff > 0
                else f"{shares_diff} 주"
            )

            table.add_row(
                "출금가능 예수금 (현금)",
                f"{format(int(cash_before), ',')} 원",
                f"{format(int(cash_after), ',')} 원",
                f"[yellow]{cash_diff_str}[/yellow]",
            )
            table.add_row(
                f"{symbol} 보유 수량",
                f"{shares_before} 주",
                f"{shares_after} 주",
                f"[magenta]{shares_diff_str}[/magenta]",
            )

            side_color = "red" if side == "BUY" else "blue"
            info_text = (
                f"• 서버 환경: {server_str}\n"
                f"• 주문 번호: [bold yellow]{order_res.order_id or 'N/A'}[/bold yellow]  "
                f"• 접수 시각: {order_res.order_time or 'N/A'}\n"
                f"• 대상 종목: [bold cyan]{symbol}[/bold cyan]  "
                f"• 매매 구분: [{side_color}]{side}[/{side_color}] {qty}주 "
                f"({order_res.order_type})\n"
                f"• 응답 메시지: {order_res.message}"
            )

            self.console.print()
            self.console.print(Panel(info_text, title="[bold]주문 접수 정보[/bold]", border_style="green"))
            self.console.print(table)
            self.console.print()

        # Plain Text Fallback Formatting (for non-rich or log capture)
        plain_report = (
            f"\n{'='*70}\n"
            f"                  수동 주문 체결 및 잔고 변동 리포트\n"
            f"{'='*70}\n"
            f"서버 환경: {server_str}\n"
            f"주문 번호: {order_res.order_id or 'N/A'} | 접수 시각: {order_res.order_time or 'N/A'}\n"
            f"대상 종목: {symbol} | 매매 구분: {side} {qty}주 ({order_res.order_type})\n"
            f"응답 메시지: {order_res.message}\n"
            f"{'-'*70}\n"
            f"{'항목':<24}{'주문 전 (Before)':<18}{'주문 후 (After)':<18}{'변동액 (Diff)':<14}\n"
            f"{'-'*70}\n"
            f"{'출금가능 현금 (예수금)':<20}{format(int(cash_before), ',') + ' 원':>16}{format(int(cash_after), ',') + ' 원':>16}{format(int(cash_diff), ',') + ' 원':>14}\n"
            f"{f'{symbol} 보유 수량':<24}{str(shares_before) + ' 주':>16}{str(shares_after) + ' 주':>16}{str(shares_diff) + ' 주':>14}\n"
            f"{'='*70}\n"
        )
        if not RICH_AVAILABLE:
            print(plain_report)

        return plain_report

    def run_interactive(self) -> None:
        """대화형 CLI 프롬프트를 실행합니다."""
        print("\n=======================================================")
        print("   Auto Stock Trader — 수동 매매 제어 인터페이스 (CLI)   ")
        print("=======================================================")
        server_str = "모의투자 (Mock Server)" if self.config.use_mock_server else "실거래 (Live Server) [주의!]"
        print(f"현재 접속 환경: {server_str}\n")

        try:
            symbol = input("1. 종목코드 6자리 (예: 005930): ").strip()
            side_in = input("2. 매매 방향 (1. BUY/매수, 2. SELL/매도): ").strip()
            side = "BUY" if side_in in ("1", "buy", "BUY", "매수") else "SELL"
            qty_in = input("3. 주문 수량 (주): ").strip()
            type_in = input("4. 주문 구분 (1. 시장가, 2. 지정가) [기본: 1]: ").strip() or "1"
            
            price = 0
            order_type = "01"
            if type_in in ("2", "지정가", "limit", "LIMIT", "00"):
                order_type = "00"
                price_in = input("5. 지정가 주문 단가 (원): ").strip()
                price = int(price_in)

            self.execute_order(
                symbol=symbol,
                side=side,
                quantity=int(qty_in),
                price=price,
                order_type=order_type,
                confirm=True,
            )
        except Exception as e:
            print(f"\n[오류 발생] 주문 처리 중 에러가 발생하였습니다: {e}")


def main(args: Optional[List[str]] = None) -> int:
    """CLI 메인 엔트리포인트"""
    parser = argparse.ArgumentParser(
        description="Auto Stock ML/RL Trader — CLI 수동 매매 제어기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-s", "--symbol", type=str, help="종목 코드 (6자리 숫자, 예: 005930)")
    parser.add_argument("-d", "--side", type=str, choices=["BUY", "SELL", "buy", "sell"], help="매매 방향 (BUY 또는 SELL)")
    parser.add_argument("-q", "--quantity", type=int, help="주문 수량 (1주 이상 정수)")
    parser.add_argument("-p", "--price", type=int, default=0, help="주문 단가 (지정가 시 필수, 시장가 시 0)")
    parser.add_argument("-t", "--order-type", type=str, default="01", choices=["01", "00", "MARKET", "LIMIT"], help="주문 구분 (01: 시장가, 00: 지정가)")
    parser.add_argument("--mock", action="store_true", help="모의투자 서버 강제 사용")
    parser.add_argument("--live", action="store_true", help="실거래 서버 강제 사용")
    parser.add_argument("-i", "--interactive", action="store_true", help="대화형 인터랙티브 모드 실행")
    parser.add_argument("--no-confirm", action="store_true", help="주문 전 확인 프롬프트 생략")

    parsed_args = parser.parse_args(args)

    config = get_config(reload=True).kiwoom
    if parsed_args.mock:
        config.use_mock_server = True
    elif parsed_args.live:
        config.use_mock_server = False

    trader = ManualTrader(config=config)

    if parsed_args.interactive or (not parsed_args.symbol and not parsed_args.side):
        trader.run_interactive()
        return 0

    if not parsed_args.symbol or not parsed_args.side or not parsed_args.quantity:
        print("오류: --symbol, --side, --quantity 인자는 필수입니다. (--interactive 로 대화형 모드 사용 가능)")
        return 1

    try:
        trader.execute_order(
            symbol=parsed_args.symbol,
            side=parsed_args.side,
            quantity=parsed_args.quantity,
            price=parsed_args.price,
            order_type=parsed_args.order_type,
            confirm=not parsed_args.no_confirm,
        )
        return 0
    except Exception as e:
        print(f"주문 실행 오류: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
