import requests
import os
from dotenv import load_dotenv

load_dotenv()
kakao_key = os.getenv("KAKAO_REST_API_KEY").split('#')[0].strip().strip('"')
url = "https://dapi.kakao.com/v2/local/search/address.json"
headers = {"Authorization": f"KakaoAK {kakao_key}"}
params = {"query": "청주시"}
res = requests.get(url, headers=headers, params=params)
print(res.status_code, res.text)
