import requests
import os
from dotenv import load_dotenv

load_dotenv()
kakao_key = os.getenv("KAKAO_REST_API_KEY").split('#')[0].strip().strip('"')
url = "https://dapi.kakao.com/v2/local/search/category.json"
headers = {
    "Authorization": f"KakaoAK {kakao_key}",
    "KA": "sdk/1.0.0 os/javascript lang/ko-KR device/web origin/http://localhost"
}
params = {"category_group_code": "FD6", "x": "127.4646", "y": "36.6433", "radius": 500}
res = requests.get(url, headers=headers, params=params)
print(res.status_code)
if res.status_code == 200:
    print(len(res.json().get('documents', [])))
else:
    print(res.text)
