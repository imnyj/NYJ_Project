## Paper4 성능 평가 리스트

### 1. 🧪 모델 정당성 및 아키텍처 성능 (Model Justification)
1. **모델별 Reward 수렴 그래프 (Convergence Curve)**
   * 제안 모델(REMO-DQN)과 비교군(DQN 등)의 에피소드 진행에 따른 누적 보상 상승 및 수렴 안정성 비교.
2. **구조 절제 실험 (Ablation Study) 성능 바 그래프**
   * [Vanilla DQN] vs [DQN + MoE] vs [REMO-DQN] 의 PDR/CBR 성능을 막대그래프로 비교하여 구조적 정당성 입증.
3. **MoE 라우팅 분포도 (Expert Routing Distribution)**
   * 차량 밀도(혼잡도) 변화에 따라 MoE 모듈이 내부 Expert들을 어떻게 배분하여 사용하는지 보여주는 비율 그래프.
4. **Q-Value / 상태 특징 맵 클러스터링 (t-SNE Scatter Plot)**
   * ResNet 특징 추출기가 비선형적인 V2X 상황을 얼마나 잘 구분해 냈는지 2차원 산점도로 시각화.
5. **하드웨어 복잡도 및 추론 타당성 (Hardware Feasibility Table/Graph)**
   * **주체 정의**: 무거운 '학습(Training)'은 RSU/Edge Server가 담당하고, '추론(Inference)'은 차량(OBU)이 실시간으로 담당.
   * **평가 항목**: 차량 OBU 기준의 추론 시간(Inference Time), 파라미터 크기(Model Size), RAM/CPU 점유율 비교. REMO-DQN이 V2X 제어 주기(예: 100ms) 안에 충분히 돌아가는 가벼운 모델임을 증명.
6. **모델별 종합 성능 요약 표 (Model Performance/Accuracy Table)**
   * 전체 비교군 모델들의 평균 PDR, CBR, AoI, 학습 수렴 여부 등을 종합적으로 비교하는 마스터 테이블.

### 2. 📡 통신 성능 (Communication Performance)
7. **시간에 따른 CBR 궤적 (Time-Series CBR Trace)**
   * 시뮬레이션 시간 흐름에 따른 순간 CBR의 변화. 타 모델(AdaptDCC)의 톱니바퀴 요동 현상과 REMO-DQN의 일직선(안정성)을 극적으로 대비.
8. **차량 밀도에 따른 패킷 수신율 (PDR vs. Vehicle Density)**
   * 차량 증가 시 REMO-DQN이 어떻게 독보적으로 수신율을 방어해 내는지 비교.
9. **차량 밀도에 따른 정보 최신성 (AoI vs. Vehicle Density)**
   * 충돌 패킷 드랍 페널티가 포함된 진짜 지연시간(AoI) 방어 곡선.
10. **거리에 따른 PDR (PDR vs. Distance)**
    * 원거리 통신 시 제안 모델이 통신 반경을 얼마나 더 확보해 주는지 입증.

---

### 🎨 범례(Legend) 및 색상 고정 규칙 (Global Config)
지저분해지더라도 철저한 비교를 위해 과거 휴리스틱 기법들(ReactDCC, AdaptDCC, TinyMLP 등)을 모두 포함하여 **총 16개의 비교군 모델**을 시각화에 렌더링합니다.

* 모든 16개 모델의 정확한 표시 순서(Order)와 Hex Code 색상표는 `/home/imnyj/Workspace/paper4/visualizer/config.md` 파일에 정의된 전역 설정(Global Config)을 절대적으로 따릅니다.
* 시각화(visualizer) 에이전트는 스크립트 작성 시 해당 config.md 문서를 읽어와 범례와 색상을 통일성 있게 적용해야 합니다.