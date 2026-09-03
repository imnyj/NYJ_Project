import yaml
from kiwoom_rest_api import KiwoomAPI
import json

with open("config/settings.yaml", "r") as f:
    config = yaml.safe_load(f)
    kiwoom = config.get("kiwoom", {})
    app_key = kiwoom.get("app_key", "")
    app_secret = kiwoom.get("app_secret", "")
    acc_no = kiwoom.get("account_no", "")

api = KiwoomAPI(app_key, app_secret, is_mock=False)

try:
    # 1. 예수금 조회
    res1 = api.account.deposit_detail(account_no=acc_no)
    print("=== 예수금 ===")
    print(res1)
    
    # 2. 계좌평가잔고
    res2 = api.account.evaluation_balance_detail(account_no=acc_no)
    print("=== 잔고 ===")
    print(res2)
    
    # 3. 삼성전자 기본정보
    res3 = api.stock_info.basic_stock_info(stk_cd="005930")
    print("=== 삼성전자 ===")
    print(res3)

except Exception as e:
    print(e)
