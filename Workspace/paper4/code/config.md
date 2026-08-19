# SUMO 네트워크 환경 설정 가이드 (SUMO Environment Configuration)

본 문서는 Paper4 V2X 시뮬레이션 환경(SUMO 및 802.11p 통신 모듈)의 매개변수를 제어하는 최상위 설정 파일입니다.  
`code/sim_engine.py` 및 `SumoNetSim1.1.5/src/sumo/make_sumo_set.py` 엔진은 본 파일의 마크다운 설정 표를 파싱하여 도심 격자망(Urban Grid) 네트워크와 차량 흐름을 동적으로 빌드합니다.

---

## 1. 환경 설정 변수 테이블 (Configuration Table)

사용자는 아래 표의 `Value` 열을 원하는 값으로 직접 수정하여 실험 환경을 변경할 수 있습니다.

| Variable | Value | Description |
|---|---|---|
| AV_SPEED | 60 | 평균 차량 속도 (km/h). `0`으로 설정 시 시뮬레이션 실행마다 10~120 km/h 범위 내 균등 무작위 할당. |
| DENSITY | 0 | 차량 밀도 (veh/1km-lane). `0`으로 설정 시 시뮬레이션 실행마다 1~20 사이 임의 무작위 할당. |
| NUM_BLOCKS | 6 | 도심 도로망(Urban Grid) 격자 블록 수 (기본 $6 \times 6$). |
| MAX_STEPS | 3600.0 | 에피소드 최대 시뮬레이션 시간/스텝 (초 단위). |
| OUTAGE_ZONE | 800 | 음영 구역(Outage Zone) 크기 (m). |
| RSU_RANGE | 800.0 | 노변 기지국(RSU) 통신 반경 (m). |
| COMM_RANGE_M | 300.0 | 차량 간(V2V) 공칭 802.11p 무선 통신 반경 (+20 dBm 기준, m). |
| DATA_RATE_BPS | 3000000 | 무선 채널 전송 속도 (기본 3 Mbps, bps). |
| NUM_LANES | 2 | 도로 링크별 차선 수 (Lanes per edge). |
| SEED | 42 | SUMO 네트워크 및 차량 경로 생성용 난수 시드 (Random Seed). |

---

## 2. 주요 설정 항목 상세 설명

1. **`AV_SPEED` (평균 차량 속도, km/h)**:
   - 양수 값 입력 시(예: `40`, `60`, `80`): 해당 속도를 기준으로 가우시안 편차를 둔 차량 속도 분포가 생성됩니다.
   - `0` 입력 시: $10 \text{ km/h} \sim 120 \text{ km/h}$ 범위에서 무작위(Uniform Random)로 차량 속도가 할당됩니다.

2. **`DENSITY` (차량 밀도, veh/1km-lane)**:
   - 양수 값 입력 시(예: `20`, `50`, `100`): 차선 km당 차량 대수를 정확히 고정하여 혼잡도를 제어합니다.
   - `0` 입력 시: $1 \sim 20\text{ veh/1km-lane}$ 범위 내에서 무작위로 밀도가 선정되어 다양한 교통 혼잡 환경을 평가합니다.

3. **`NUM_BLOCKS` (도심 격자 블록 수)**:
   - 도심 맨해튼 그리드(Manhattan Grid) 네트워크의 블록 개수를 결정합니다. $6$ 설정 시 $6 \times 6$ 교차로 네트워크가 생성됩니다.

4. **`OUTAGE_ZONE` & `RSU_RANGE` (음영 구역 및 RSU 반경)**:
   - RSU 커버리지 밖의 음영 지역 크기와 RSU 반경을 정의합니다. 전체 엣지 길이는 `2 * RSU_RANGE + OUTAGE_ZONE`으로 계산됩니다.

5. **`COMM_RANGE_M` (V2V 통신 반경)**:
   - Nakagami-$m$ ($m=3$) 페이딩 및 자유공간 경로손실 모델이 적용되는 공칭 유효 통신 반경입니다.

6. **`SEED` (재현성 난수 시드)**:
   - SUMO 라우트 파일(`generated.rou.xml`) 생성 및 차량 생성 타이밍의 결정론적 재현성을 보장합니다.
