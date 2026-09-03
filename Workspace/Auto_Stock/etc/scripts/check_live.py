import json
import logging
import sys
import os

# 현재 경로를 sys.path에 추가하여 모듈 임포트 가능하게 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.kiwoom_api import KiwoomClient

logging.basicConfig(level=logging.WARNING)

def main():
    print("🚀 실거래(Live) 모드로 키움 API 접속을 시도합니다...")
    try:
        with KiwoomClient() as client:
            print("\n✅ 토큰 발급 및 접속 성공!")
            
            # 잔액 조회
            print("\n[계좌 잔액 및 보유 종목 조회]")
            balance = client.get_account_balance()
            print(f"- 계좌번호: {balance.account_no}")
            print(f"- 총 예수금(예탁금): {balance.deposit_received:,.0f} 원")
            print(f"- 주문 가능 현금: {balance.available_cash:,.0f} 원")
            print(f"- 총 자산: {balance.total_asset:,.0f} 원")
            print(f"- 총 평가 손익: {balance.total_eval_pnl:,.0f} 원")
            
            print(f"- 보유 종목 수: {len(balance.positions)}개")
            for pos in balance.positions:
                print(f"  > [{pos.symbol}] {pos.name} : {pos.quantity}주 (수익률: {pos.eval_pnl_rate}%)")
                
            # 종목 조회
            print("\n[관심 종목 현재가 조회]")
            symbols = {"삼성전자": "005930", "SK하이닉스": "000660", "현대차": "005380", "카카오": "035720", "NAVER": "035420"}
            for name, code in symbols.items():
                quote = client.get_current_price(code)
                sign = "+" if quote.price_change > 0 else "-" if quote.price_change < 0 else ""
                print(f"- {name}({code}): {quote.current_price:,.0f} 원 (전일대비 {sign}{abs(quote.price_change):,.0f}원, {quote.change_rate}%)")
                
            print("\n조회가 모두 완료되었습니다.")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
