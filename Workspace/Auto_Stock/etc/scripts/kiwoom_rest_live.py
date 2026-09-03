import yaml
import requests
import os
import json

CONFIG_PATH = "/home/imnyj/Workspace/Auto_Stock/config/settings.yaml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def main():
    print("🚀 [키움증권 실전투자(Live) REST API 접속을 시도합니다]")
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            kiwoom = config.get("kiwoom", {})
            app_key = kiwoom.get("app_key", "")
            app_secret = kiwoom.get("app_secret", "")
    except Exception as e:
        print(f"❌ 설정 파일 읽기 실패: {e}")
        return

    # 1. 접근 토큰(Access Token) 발급
    print("1. 토큰 발급 중...")
    token_url = "https://api.kiwoom.com/oauth2/token"
    token_payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "secretkey": app_secret
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": USER_AGENT
    }
    
    res = requests.post(token_url, json=token_payload, headers=headers)
    if res.status_code != 200:
        print(f"❌ 토큰 발급 실패: HTTP {res.status_code}\n{res.text}")
        return
    
    token = res.json().get("access_token")
    if not token:
        print(f"❌ 토큰 파싱 실패: {res.text}")
        return
    print("✅ 토큰 발급 성공!")

    api_headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }

    # 2. 계좌 잔액 조회 (kt00018)
    print("\n2. 계좌 잔액 조회 중...")
    acnt_url = "https://api.kiwoom.com/api/dostk/acnt"
    api_headers["api-id"] = "kt00018"
    acnt_payload = {
        "qry_tp": "1",          # 합산 조회
        "dmst_stex_tp": "KRX"
    }
    
    res_acnt = requests.post(acnt_url, json=acnt_payload, headers=api_headers)
    if res_acnt.status_code == 200:
        data = res_acnt.json()
        print("✅ 잔고 조회 성공:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"❌ 잔고 조회 실패: HTTP {res_acnt.status_code}\n{res_acnt.text}")

    # 3. 종목 정보 조회 (ka10001)
    print("\n3. 관심 종목 정보(시세) 조회 중...")
    price_url = "https://api.kiwoom.com/api/dostk/stkinfo"
    api_headers["api-id"] = "ka10001"
    
    symbols = {"삼성전자": "005930", "SK하이닉스": "000660"}
    for name, code in symbols.items():
        payload = {"stk_cd": code}
        res_price = requests.post(price_url, json=payload, headers=api_headers)
        if res_price.status_code == 200:
            data = res_price.json()
            print(f"✅ [{name}] 조회 성공:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ [{name}] 조회 실패: HTTP {res_price.status_code}\n{res_price.text}")

if __name__ == "__main__":
    main()
