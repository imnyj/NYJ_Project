# Critic Agent 피드백 보고서: 4. 본문.md (Section 1. content 요청)

## 1. 글의 흐름 및 논리적 완결성 검토 (통신 시나리오 관점 비판적 평가)

**1) 통신 프로토콜 흐름의 명확성 및 Index Number 체계 개선**
- 현재 패킷의 목적지를 구분하기 위해 `index no.` (0과 1)을 사용하는 방식은 다소 혼동을 줄 수 있습니다. 논문(`main.tex`)의 V2I/I2I 통신 프로토콜 정의에 맞추어, `[INFO REQ]`, `[INFO HELLO]`, `[INFO REP]` 와 같이 패킷 Type을 명확히 명명하는 방식으로 수정하는 것이 가독성과 프로토콜 설계 관점에서 훨씬 직관적입니다.
- 예를 들어, Current RSU가 Next RSU에게 `[INFO REQ]`를 보내고, Next RSU가 주변 이웃들에게 `[INFO HELLO]`를 브로드캐스트한 뒤, 이웃들이 회신한 값을 취합하여 `[INFO REP]`로 Current RSU에게 전달하는 흐름으로 서술을 개선할 것을 제안합니다.

**2) 불필요한/잘못된 Feature 제거**
- `4. 본문.md`에 언급된 **'통계적인 평균 통신 속도'**와 Interest packet의 **'가속도'**는 H-ST-MBAN 모델의 실제 30개 입력 피처에 존재하지 않습니다. 해당 내용을 삭제하여 실제 모델 구현(Table 1)과의 일관성을 맞춰야 합니다.

**3) 지연 시간(Latency) 및 오버헤드 관점의 보완**
- 정보 수집(Information Request/Reply) 과정에서 이웃 RSU들과의 다중 홉 통신으로 인해 발생하는 지연 시간 동안 캐싱(content 제공)이 어떻게 병렬적으로 처리되는지 논리적 연결을 강화해야 합니다.
- "content 제공은 별도로 진행되기 때문에"라는 문장 부분을, "차량의 초기 Interest Packet 수신 즉시 Current RSU는 가용 chunk 제공을 시작(Reactive Caching)하며, 백그라운드에서는 Next RSU의 상태를 묻는 I2I 통신을 통해 Snapshot을 완성하고 Dwell Time을 예측하여 Precaching을 스케줄링하므로 서비스 지연이 발생하지 않는다"는 형태로 구체화할 것을 권장합니다.

## 2. 누락된 Feature Vector 식별 및 추가 방안 제안

**1) 누락된 Feature 식별**
실제 H-ST-MBAN 모델은 30차원의 Feature Vector를 사용하지만, 현재 스케치에서는 약 15개만 서술되어 있습니다. 누락된 15개의 Feature는 다음과 같습니다.
- **기본/상수 지표 (3개)**: $r_{cov}$ (RSU 커버리지 반경), $d_{rsu}$ (RSU 간 거리), $direct$ (차량 진행 방향: -1 or +1)
- **차량 추종 및 주행 지표 (6개)**: $d_{leader}$ (선행 차량과의 거리), $v_{leader}$ (선행 차량 속도), $v_{ahead,avg}$ (동일 엣지의 전방 차량 평균 속도), $n_{ahead,cur}$ (현재 도로 전방 차량 수), $t_{est}$ (현재 도로 추정 통과 시간), $\Delta_{lane}$ (다음 RSU 도달을 위한 차선 변경 횟수)
- **다음 RSU 혼잡 및 합류 지표 (2개)**: $n_{ahead,nxt}$ (다음 RSU 접근 전방 차량 수), $n_{merge,nxt}$ (인접 차선에서 다음 RSU 방향으로 합류하는 경쟁 차량 수)
- **교차로 대기 큐 및 점유율 지표 (4개)**: $q_{len,cur}$ (현재 RSU 대기 큐 길이), $q_{len,nxt}$ (다음 RSU 대기 큐 길이), $occ_{cur}$ (현재 RSU 차선 점유율), $occ_{nxt}$ (다음 RSU 차선 점유율)

**2) 내용 추가 방안 (흐름에 자연스럽게 녹여내는 방법)**
서술의 흐름을 해치지 않기 위해, 다음과 같이 각 정보 수집 주체별로 나누어 Feature를 설명하는 것을 제안합니다.

- **차량의 Interest Packet 전송 시 (11번 라인 부근)**:
  - 수정 제안: 차량이 Interest Packet을 보낼 때 차량의 위치, 속도, 경로뿐만 아니라 센서/내비게이션 기반의 미시적 지표인 **선행 차량과의 간격($d_{leader}$), 선행 차량 속도($v_{leader}$), 현재 도로 추정 통과 시간($t_{est}$), 필요 차선 변경 횟수($\Delta_{lane}$)**를 함께 포함하여 전송한다고 추가합니다.
- **Current RSU의 PDT 추가 시 (14번 라인 부근)**:
  - 수정 제안: Current RSU가 로컬 관측을 통해 신호등 상태($tls_c$), 변경 시간($tlt_c$), 평균 속도($v_{c,a}$) 등을 넣을 때, 추가적으로 도로 인프라 센서(카메라/레이더 등)에서 얻은 **대기 큐 길이($q_{len,cur}$), 차선 점유율($occ_{cur}$), 전방 차량 수($n_{ahead,cur}$) 및 전방 차량 평균 속도($v_{ahead,avg}$)**와 시스템 고정 상수인 **$r_{cov}, d_{rsu}, direct$**를 함께 기록한다고 보완합니다.
- **Next RSU의 Information Reply Packet 회신 시 (25번 라인 부근)**:
  - 수정 제안: Next RSU가 최종 패킷을 보낼 때, 기존의 차량 수나 신호등 정보 외에도, Next RSU 교차로의 국소적 혼잡도를 나타내는 **대기 큐 길이($q_{len,nxt}$), 차선 점유율($occ_{nxt}$), 다음 RSU 접근 전방 차량 수($n_{ahead,nxt}$), 인접 차선 합류 경쟁 차량 수($n_{merge,nxt}$)**를 시뮬레이션 기반(혹은 노변 센서 기반)으로 함께 집계하여 회신한다고 명시합니다.
