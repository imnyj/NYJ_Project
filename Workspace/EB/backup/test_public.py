import requests
import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()
data_go_kr_key = os.getenv("DATA_GO_KR_API_KEY").split('#')[0].strip().strip('"')

# The SGIS commercial api for radius is: http://apis.data.go.kr/B553077/api/open/sdam/storeListInRadius
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
    "cx": "127.4646",
    "cy": "36.6433",
    "type": "json"
}
res = requests.get(url, params=params)
print(res.status_code)
print(res.text[:300])
