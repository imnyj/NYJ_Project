import requests
import os
from dotenv import load_dotenv

load_dotenv()
kakao_key = os.getenv("KAKAO_REST_API_KEY").split('#')[0].strip().strip('"')
url = "https://dapi.kakao.com/v2/local/search/address.json"
headers = {"Authorization": f"KakaoAK {kakao_key}"}

q = "충북 청주시 흥덕구 1순환로513번길 33"
res = requests.get(url, headers=headers, params={"query": q})
print(res.json())

q2 = "청주시 흥덕구"
res2 = requests.get(url, headers=headers, params={"query": q2})
print(res2.json()['documents'][0]['y'], res2.json()['documents'][0]['x'])

