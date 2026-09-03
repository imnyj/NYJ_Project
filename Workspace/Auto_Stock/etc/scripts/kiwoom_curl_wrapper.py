import yaml
import subprocess
import os
import json

CONFIG_PATH = "/home/imnyj/Workspace/Auto_Stock/config/settings.yaml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def run_curl(url, payload=None, token=None, api_id=None):
    headers = [
        "-H", "Content-Type: application/json;charset=UTF-8",
        "-H", f"User-Agent: {USER_AGENT}"
    ]
    if token:
        headers.extend(["-H", f"authorization: Bearer {token}"])
    if api_id:
        headers.extend(["-H", f"api-id: {api_id}"])
        
    cmd = ["curl", "-s", "-X", "POST"] + headers
    if payload:
        cmd.extend(["-d", json.dumps(payload)])
    cmd.append(url)
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(res.stdout)
    except:
        return res.stdout

def main():
    print("🚀 [키움증권 실전투자(Live) REST API 접속을 시도합니다]")
    
    # 1. 키 읽어오기 (settings.yaml 파싱 로직)
    # config.py의 정규식을 직접 모방하여 기본값(fallback)을 추출합니다.
    import re
    app_key = ""
    app_secret = ""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw_yaml = f.read()
            # ${VAR:default} 패턴 추출
            key_match = re.search(r'\$\{KIWOOM_APP_KEY:([^}]+)\}', raw_yaml)
            sec_match = re.search(r'\$\{KIWOOM_APP_SECRET:([^}]+)\}', raw_yaml)
            if key_match: app_key = key_match.group(1)
            if sec_match: app_secret = sec_match.group(1)
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
    
    res_token = run_curl(token_url, payload=token_payload)
    if isinstance(res_token, dict):
        token = res_token.get("token") or res_token.get("access_token")
        if not token:
            print(f"❌ 토큰 발급 실패 (증권사 응답): {res_token.get('return_msg', res_token)}")
            return
    else:
        print(f"❌ 토큰 요청 WAF 차단 또는 통신 실패: {res_token}")
        return
        
    print("✅ 토큰 발급 성공!")

    # 2. 계좌 잔액 조회 (kt00018)
    print("\n2. 계좌 잔액 조회 중...")
    acnt_url = "https://api.kiwoom.com/api/dostk/acnt"
    acnt_payload = {
        "qry_tp": "1",          # 합산 조회
        "dmst_stex_tp": "KRX"
    }
    
    res_acnt = run_curl(acnt_url, payload=acnt_payload, token=token, api_id="kt00018")
    if isinstance(res_acnt, dict):
        print("✅ 잔고 조회 성공:")
        print(json.dumps(res_acnt, indent=2, ensure_ascii=False))
    else:
        print(f"❌ 잔고 조회 통신 실패: {res_acnt}")

    # 3. 종목 정보 조회 (ka10001)
    print("\n3. 관심 종목 정보(시세) 조회 중...")
    price_url = "https://api.kiwoom.com/api/dostk/stkinfo"
    
    symbols = {"삼성전자": "005930", "SK하이닉스": "000660"}
    for name, code in symbols.items():
        payload = {"stk_cd": code}
        res_price = run_curl(price_url, payload=payload, token=token, api_id="ka10001")
        if isinstance(res_price, dict):
            print(f"✅ [{name}] 조회 성공:")
            print(json.dumps(res_price, indent=2, ensure_ascii=False))
        else:
            print(f"❌ [{name}] 통신 실패: {res_price}")

if __name__ == "__main__":
    main()
