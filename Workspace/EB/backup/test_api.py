import requests
import json
import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv()

kakao_key = os.getenv("KAKAO_REST_API_KEY")
data_go_kr_key = os.getenv("DATA_GO_KR_API_KEY")

if data_go_kr_key and data_go_kr_key.startswith('"'):
    data_go_kr_key = data_go_kr_key.strip('"')
if kakao_key and kakao_key.startswith('"'):
    kakao_key = kakao_key.strip('"')
if data_go_kr_key and " " in data_go_kr_key: # just in case of comments
    data_go_kr_key = data_go_kr_key.split('"')[0] if data_go_kr_key.startswith('"') else data_go_kr_key.split(' ')[0]

def get_lat_lon(address):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    params = {"query": address}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200 and res.json().get('documents'):
        doc = res.json()['documents'][0]
        return doc['y'], doc['x']
    return None, None

lat, lon = get_lat_lon("청주시 흥덕구 1순환로 513번길 33")
print(f"Coordinates: Lat {lat}, Lon {lon}")

# Test Public Data API
# Decoding the key as requests params will urlencode it again.
try:
    decoded_key = urllib.parse.unquote(data_go_kr_key)
except:
    decoded_key = data_go_kr_key

url = "http://apis.data.go.kr/B553077/api/open/sdam/storeListInRadius"
params = {
    "serviceKey": decoded_key,
    "pageNo": "1",
    "numOfRows": "10",
    "radius": "4000",
    "cx": lon,
    "cy": lat,
    "indsLclsCd": "I2", # I2 is usually Food in new schema? Or Q in old schema. Let's omit for now to see what comes back.
    "type": "json"
}

res = requests.get(url, params=params)
print(f"Status Code: {res.status_code}")
try:
    print(res.text[:500])
except Exception as e:
    print("Failed to print text", e)

