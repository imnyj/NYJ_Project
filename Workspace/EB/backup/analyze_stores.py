import requests
import os
import math
from dotenv import load_dotenv
import pandas as pd
from collections import Counter

load_dotenv()
kakao_key = os.getenv("KAKAO_REST_API_KEY").split('#')[0].strip().strip('"')
headers = {"Authorization": f"KakaoAK {kakao_key}"}

# 1. Geocoding
def get_lat_lon(query):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    res = requests.get(url, headers=headers, params={"query": query})
    if res.status_code == 200:
        docs = res.json().get('documents', [])
        if docs:
            return float(docs[0]['y']), float(docs[0]['x'])
    
    # Fallback to address search
    url_addr = "https://dapi.kakao.com/v2/local/search/address.json"
    res_addr = requests.get(url_addr, headers=headers, params={"query": query})
    if res_addr.status_code == 200:
        docs = res_addr.json().get('documents', [])
        if docs:
            return float(docs[0]['y']), float(docs[0]['x'])
    
    return None, None

address = "청주시 흥덕구 1순환로513번길 33"
center_lat, center_lon = get_lat_lon(address)

if not center_lat:
    # Try just the street name
    center_lat, center_lon = get_lat_lon("충북 청주시 흥덕구 1순환로513번길")

if not center_lat:
    print("Error: Could not find the coordinate for the address.")
    exit(1)

print(f"[1] 기준 좌표 획득 완료: {center_lat}, {center_lon}")

# 2. Grid Search (4km 반경)
def get_stores_in_grid(center_y, center_x, radius_m=4000):
    # 4km = approx 0.036 lat, 0.045 lon
    step_lat = 0.005 # ~500m
    step_lon = 0.006 # ~500m
    
    stores = {}
    
    # Grid bounding box
    lat_min, lat_max = center_y - 0.036, center_y + 0.036
    lon_min, lon_max = center_x - 0.045, center_x + 0.045
    
    lat = lat_min
    total_grids = 0
    
    # Helper to calculate distance
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    print("[2] 4km 반경 상가 데이터 수집 중... (약 10~20초 소요)")
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    
    while lat <= lat_max:
        lon = lon_min
        while lon <= lon_max:
            # Check if grid point is within 4km of center
            if haversine(center_y, center_x, lat, lon) <= radius_m:
                total_grids += 1
                for category in ['FD6', 'CE7']: # Food and Cafe
                    for page in range(1, 4):
                        params = {
                            "category_group_code": category,
                            "x": str(lon),
                            "y": str(lat),
                            "radius": 500, # overlap to catch all
                            "page": page,
                            "size": 15
                        }
                        res = requests.get(url, headers=headers, params=params)
                        if res.status_code == 200:
                            data = res.json()
                            for doc in data.get('documents', []):
                                stores[doc['id']] = doc
                            if data.get('meta', {}).get('is_end'):
                                break
                        else:
                            break
            lon += step_lon
        lat += step_lat
        
    return list(stores.values())

stores = get_stores_in_grid(center_lat, center_lon, 4000)
print(f"-> 총 {len(stores)}개의 음식점/카페 데이터를 수집했습니다.")

# 3. Analyze Data
categories = []
delivery_count = 0
delivery_keywords = ['배달', '테이크아웃', '포장', '야식']
delivery_categories = ['치킨', '피자', '중식', '패스트푸드', '도시락', '족발', '보쌈', '분식']

for s in stores:
    # 카테고리 추출 (e.g. "음식점 > 한식 > 국밥" -> "한식")
    cat_full = s.get('category_name', '')
    parts = [p.strip() for p in cat_full.split('>')]
    main_cat = parts[1] if len(parts) > 1 else '기타'
    sub_cat = parts[2] if len(parts) > 2 else main_cat
    
    categories.append(main_cat)
    
    # 배달 가능/전문 유추
    name = s.get('place_name', '')
    is_delivery = False
    
    # 1) 이름에 키워드 포함
    if any(k in name for k in delivery_keywords):
        is_delivery = True
    # 2) 배달 특화 업종
    elif any(k in main_cat for k in delivery_categories) or any(k in sub_cat for k in delivery_categories):
        is_delivery = True
        
    if is_delivery:
        delivery_count += 1

# 순위 집계
cat_counts = Counter(categories)
top_10 = cat_counts.most_common(10)

print("\n==============================================")
print("[상권 분석 결과 요약]")
print(f"기준: 청주시 흥덕구 1순환로513번길 반경 4km")
print(f"총 추출된 식당/카페 수: {len(stores)}개")
print(f"배달 가능/특화로 분류된 가게 수: {delivery_count}개 (약 {delivery_count/len(stores)*100:.1f}%)")
print("==============================================")
print("\n[음식점 종류별 비율 순위 (Top 10)]")
for i, (cat, count) in enumerate(top_10, 1):
    print(f"{i}위: {cat} - {count}개 ({count/len(stores)*100:.1f}%)")
print("==============================================")

# CSV 저장
df = pd.DataFrame(stores)
df.to_csv('stores_4km.csv', index=False, encoding='utf-8-sig')
print("\n-> 전체 데이터가 'stores_4km.csv' 파일로 저장되었습니다.")
