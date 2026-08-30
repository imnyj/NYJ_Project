## 사용자 요청

1. critic을 활용하여 시뮬레이션 code를 읽게 하는데, 내가 구조를 파악하기 좋게 요약을 해주었으면 좋겠어.
일단은 다음과 같이 사용되는 파일들의 리스트 및 구조를 설명해줘.

coder/
 - src/: core 기능들 포함
   - sumo/: SUMO 구현 디렉토리
   - Communications.py: 통신 모듈 정리
   - NetSim.py: ....??

2. 그리고 코드 요약은 주로 함수와 클래스 느낌으로 요약을 해주었으면 해.
다음과 같은 예시로 하나의 md 파일에 코드 요약문을 작성해줘.

## coder/src/Communications.py
class WiFiChannelManager:
    def __init__(): 어떤 것들 초기화
    def _rate_per_user(): 유저에게 ..??

## coder/src/sumo/make_sumo_set.py
def ~~~