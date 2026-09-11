import pandas as pd
import folium
from folium.plugins import HeatMap
import os

# 1. 데이터 로드
csv_path = '/home/imnyj/Workspace/EB/tonkatsu_4km.csv'
if not os.path.exists(csv_path):
    print("CSV file not found!")
    exit(1)

df = pd.read_csv(csv_path)

# 2. 지도 초기화 (데이터의 중심 좌표 기준)
center_lat = df['y'].mean()
center_lon = df['x'].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles='OpenStreetMap')

# 3. 1차: 히트맵 (그라데이션 밀집도 시각화)
heat_data = [[row['y'], row['x']] for index, row in df.iterrows()]
HeatMap(heat_data, radius=25, blur=20, max_zoom=1, gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 1.0: 'red'}).add_to(m)

# 4. 2차: 동네별 밀집도 버블(원형) 마커 표시
def get_dong(address):
    for part in str(address).split():
        if part.endswith('동') or part.endswith('읍') or part.endswith('면'):
            return part
    return '기타'

df['dong'] = df['address_name'].apply(get_dong)
dong_stats = df.groupby('dong').agg(
    count=('id', 'count'),
    lat=('y', 'mean'),
    lon=('x', 'mean')
).reset_index()

for _, row in dong_stats.iterrows():
    # 가게 수(경쟁도)에 따라 원의 크기 조절
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=row['count'] * 2.5 + 5,
        popup=f"<b>{row['dong']}</b><br>돈가스 가게: {row['count']}곳",
        tooltip=f"<div style='font-size: 14px;'><b>{row['dong']}</b><br>밀집도: {row['count']}곳 (클릭)</div>",
        color='#FF4500',
        weight=2,
        fill=True,
        fill_color='#FF4500',
        fill_opacity=0.4
    ).add_to(m)

# 5. 지도 저장
map_path = '/home/imnyj/Workspace/EB/돈가스_상권지도.html'
m.save(map_path)
print(f"Map successfully generated at {map_path}")
