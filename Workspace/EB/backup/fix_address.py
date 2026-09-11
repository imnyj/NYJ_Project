import requests
import os
from dotenv import load_dotenv

load_dotenv()
kakao_key = os.getenv("KAKAO_REST_API_KEY").split('#')[0].strip().strip('"')
headers = {"Authorization": f"KakaoAK {kakao_key}"}

url = "https://dapi.kakao.com/v2/local/search/keyword.json"
res = requests.get(url, headers=headers, params={"query": "청주 충북대"})
print(res.json())
