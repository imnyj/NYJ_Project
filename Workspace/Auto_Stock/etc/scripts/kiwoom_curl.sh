#!/bin/bash
cd /home/imnyj/Workspace/Auto_Stock

APP_KEY=$(grep 'app_key:' config/settings.yaml | cut -d'"' -f2 | tr -d ' ')
APP_SECRET=$(grep 'app_secret:' config/settings.yaml | cut -d'"' -f2 | tr -d ' ')

if [ -z "$APP_KEY" ]; then
    echo "❌ APP_KEY를 찾을 수 없습니다."
    exit 1
fi

USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

echo "🚀 [키움증권 실전투자(Live) REST API 접속을 시도합니다]"
echo "1. 토큰 발급 중..."

# 2. 토큰 발급 요청
RESPONSE=$(curl -s -X POST \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -H "User-Agent: $USER_AGENT" \
  -d "{\"grant_type\":\"client_credentials\", \"appkey\":\"$APP_KEY\", \"secretkey\":\"$APP_SECRET\"}" \
  https://api.kiwoom.com/oauth2/token)

TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')

if [ -z "$TOKEN" ]; then
    echo "❌ 토큰 발급 실패: $RESPONSE"
    exit 1
fi
echo "✅ 토큰 발급 성공!"

echo ""
echo "2. 계좌 잔액 조회 중..."
curl -s -X POST \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -H "authorization: Bearer $TOKEN" \
  -H 'api-id: kt00018' \
  -H "User-Agent: $USER_AGENT" \
  -d '{"qry_tp": "1", "dmst_stex_tp": "KRX"}' \
  https://api.kiwoom.com/api/dostk/acnt | python3 -m json.tool

echo ""
echo "3. 종목 정보 조회 중..."
echo "[삼성전자]"
curl -s -X POST \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -H "authorization: Bearer $TOKEN" \
  -H 'api-id: ka10001' \
  -H "User-Agent: $USER_AGENT" \
  -d '{"stk_cd": "005930"}' \
  https://api.kiwoom.com/api/dostk/stkinfo | python3 -m json.tool

echo ""
echo "[SK하이닉스]"
curl -s -X POST \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -H "authorization: Bearer $TOKEN" \
  -H 'api-id: ka10001' \
  -H "User-Agent: $USER_AGENT" \
  -d '{"stk_cd": "000660"}' \
  https://api.kiwoom.com/api/dostk/stkinfo | python3 -m json.tool
