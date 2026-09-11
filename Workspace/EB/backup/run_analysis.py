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
def get_lat_lon():
    url_keyword = "https://dapi.kakao.com/v2/local/search/keyword.json"
    url_address = "https://dapi.kakao.com/v2/local/search/address.json"
    
    queries = [
        "청주시 흥덕구 1순환로 513번길 33",
        "청주시 흥덕구 1순환로513번길 33",
        "청주시 흥덕구 제1순환로 513번길 33",
        "청주시 흥덕구 제1순환로513번길 33",
        "청주시 흥덕구 봉명동 제1순환로513번길 33"
    ]
    
    for q in queries:
        # Try keyword
        res = requests.get(url_keyword, headers=headers, params={"query": q})
        if res.status_code == 200:
            docs = res.json().get('documents', [])
            if docs:
                return float(docs[0]['y']), float(docs[0]['x'])
        
        # Try address
        res = requests.get(url_address, headers=headers, params={"query": q})
        if res.status_code == 200:
            docs = res.json().get('documents', [])
            if docs:
                return float(docs[0]['y']), float(docs[0]['x'])
                
    # If all fails, return approx center of Bongmyeong-dong, Heungdeok-gu, Cheongju
    print("Warning: Exact address not found. Using approximate center of Bongmyeong-dong, Cheongju.")
    # Approximate coordinates for Cheongju Bongmyeong-dong: 36.6433, 127.4646
    return 36.6433, 127.4646

center_lat, center_lon = get_lat_lon()
print(f"[1] 기준 좌표 획득 완료: {center_lat}, {center_lon}")

# 2. Grid Search (4km 반경)
def get_stores_in_grid(center_y, center_x, radius_m=4000):
    step_lat = 0.005 # ~500m
    step_lon = 0.006 # ~500m
    
    stores = {}
    
    lat_min, lat_max = center_y - 0.036, center_y + 0.036
    lon_min, lon_max = center_x - 0.045, center_x + 0.045
    
    lat = lat_min
    
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi, delta_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    print("[2] 4km 반경 상가 데이터 수집 중... (카카오 API Grid Search)")
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    
    while lat <= lat_max:
        lon = lon_min
        while lon <= lon_max:
            if haversine(center_y, center_x, lat, lon) <= radius_m:
                for category in ['FD6', 'CE7']: 
                    for page in range(1, 4):
                        params = {
                            "category_group_code": category,
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
delivery_categories = ['치킨', '피자', '중식', '패스트푸드', '도시락', '족발', '보쌈', '분식', '햄버거']

for s in stores:
    cat_full = s.get('category_name', '')
    parts = [p.strip() for p in cat_full.split('>')]
    main_cat = parts[1] if len(parts) > 1 else '기타'
    sub_cat = parts[2] if len(parts) > 2 else main_cat
    
    # 세부분류가 있으면 세부분류를 우선하되, 너무 길면 메인 사용
    display_cat = sub_cat if sub_cat != '기타' else main_cat
    if display_cat == '': display_cat = '기타'
    
    categories.append(display_cat)
    
    name = s.get('place_name', '')
    is_delivery = False
    
    if any(k in name for k in delivery_keywords):
        is_delivery = True
    elif any(k in main_cat for k in delivery_categories) or any(k in sub_cat for k in delivery_categories):
        is_delivery = True
        
    if is_delivery:
        delivery_count += 1

cat_counts = Counter(categories)
top_10 = cat_counts.most_common(10)

print("\n==============================================")
print("📊 [상권 분석 결과 요약]")
print(f"- 기준: 청주시 흥덕구 1순환로 513번길 33 (반경 4km)")
print(f"- 총 추출된 식당/카페 수: {len(stores)}개")
print(f"- 배달 특화/유력 가게 수: {delivery_count}개 (약 {delivery_count/len(stores)*100:.1f}%)")
print("  * 배달 유력: 상호명 내 배달/포장 키워드 포함 또는 치킨, 중식, 피자 등 배달 중심 업종")
print("==============================================")
print("\n🏆 [음식점 종류별 밀집도 순위 (Top 10)]")
for i, (cat, count) in enumerate(top_10, 1):
    print(f" {i}위: {cat} ({count}개, {count/len(stores)*100:.1f}%)")
print("==============================================")

df = pd.DataFrame(stores)
df.to_csv('/home/imnyj/Workspace/EB/stores_4km_analysis.csv', index=False, encoding='utf-8-sig')
print("\n-> 상세 데이터가 'Workspace/EB/stores_4km_analysis.csv'에 저장되었습니다.")
