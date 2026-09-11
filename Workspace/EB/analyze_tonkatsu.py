import requests
import os
import math
from dotenv import load_dotenv
from collections import Counter
import pandas as pd

load_dotenv()
kakao_key = os.getenv("KAKAO_REST_API_KEY").split('#')[0].strip().strip('"')
headers = {"Authorization": f"KakaoAK {kakao_key}"}

def get_lat_lon(query):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    res = requests.get(url, headers=headers, params={"query": query})
    if res.status_code == 200 and res.json().get('documents'):
        doc = res.json()['documents'][0]
        return float(doc['y']), float(doc['x'])
    return None, None

center_y, center_x = get_lat_lon("청원구 공항로59번길 9-1")
if not center_y:
    center_y, center_x = get_lat_lon("청주시 청원구 공항로59번길") # Fallback

if not center_y:
    print("Error: Coords not found")
    exit(1)

print(f"Center: {center_y}, {center_x}")

stores = {}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi, delta_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

lat_min, lat_max = center_y - 0.036, center_y + 0.036
lon_min, lon_max = center_x - 0.045, center_x + 0.045
step_lat = 0.005
step_lon = 0.006

url = "https://dapi.kakao.com/v2/local/search/keyword.json"

lat = lat_min
while lat <= lat_max:
    lon = lon_min
    while lon <= lon_max:
        if haversine(center_y, center_x, lat, lon) <= 4000:
            for page in range(1, 4):
                params = {
                    "query": "돈까스",
                    "x": str(lon),
                    "y": str(lat),
                    "radius": 500,
                    "page": page,
                    "size": 15
                }
                res = requests.get(url, headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    for doc in data.get('documents', []):
                        if '돈가스' in doc['category_name'] or '돈까스' in doc['category_name'] or '돈가스' in doc['place_name'] or '돈까스' in doc['place_name']:
                            stores[doc['id']] = doc
                    if data.get('meta', {}).get('is_end'):
                        break
                
                # Also search "돈가스"
                params["query"] = "돈가스"
                res = requests.get(url, headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    for doc in data.get('documents', []):
                        if '돈가스' in doc['category_name'] or '돈까스' in doc['category_name'] or '돈가스' in doc['place_name'] or '돈까스' in doc['place_name']:
                            stores[doc['id']] = doc
        lon += step_lon
    lat += step_lat

stores_list = list(stores.values())
print(f"Total Tonkatsu found: {len(stores_list)}")

# Analyze neighborhoods (Dong)
dongs = []
for s in stores_list:
    addr = s.get('address_name', '')
    # Usually format is "충북 청주시 청원구 율량동 123"
    parts = addr.split()
    for p in parts:
        if p.endswith('동') or p.endswith('읍') or p.endswith('면'):
            dongs.append(p)
            break

dong_counts = Counter(dongs).most_common()
print("Top neighborhoods:")
for d, c in dong_counts:
    print(f"{d}: {c}")

df = pd.DataFrame(stores_list)
df.to_csv('/home/imnyj/Workspace/EB/tonkatsu_4km.csv', index=False, encoding='utf-8-sig')
