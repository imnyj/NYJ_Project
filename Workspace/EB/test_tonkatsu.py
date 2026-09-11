import requests
import os
from dotenv import load_dotenv

load_dotenv()
kakao_key = os.getenv("KAKAO_REST_API_KEY").split('#')[0].strip().strip('"')
headers = {"Authorization": f"KakaoAK {kakao_key}"}

# Search
url = "https://dapi.kakao.com/v2/local/search/keyword.json"
res = requests.get(url, headers=headers, params={"query": "청원구 공항로 59번길 9-1 돈가스"})
if res.status_code == 200:
    docs = res.json().get('documents', [])
    if docs:
        place_id = docs[0]['id']
        print(f"Found place: {docs[0]['place_name']} (ID: {place_id})")
        
        url_detail = f"https://place.map.kakao.com/main/v/{place_id}"
        res_detail = requests.get(url_detail, headers={"User-Agent": "Mozilla/5.0"})
        if res_detail.status_code == 200:
            data = res_detail.json()
            basic = data.get("basicInfo", {})
            print(basic.get("placenamefull", ""), data.get("comment", {}))
