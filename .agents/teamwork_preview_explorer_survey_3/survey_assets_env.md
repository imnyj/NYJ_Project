# Paper4 작업 공간 및 LaTeX 환경 전방위 조사 보고서 (Survey of Assets & Environment)

**작성 에이전트**: `teamwork_preview_explorer_survey_3`  
**대상 프로젝트**: `/home/imnyj/Workspace/paper4/`  
**타깃 저널**: *IEEE Transactions on Wireless Communications (TWC)*  
**목표**: 한글 마스터 초안(`paper4_draft_korean.md`)을 출판급 IEEE TWC 영문 LaTeX 문서(`main.tex`, `references.bib`, `IEEEtran.cls`, `figures/`)로 완벽하게 변환하기 위한 자산 인벤토리, 그래프 매핑, 수식/테이블/참고문헌 분석, 로컬 컴파일 환경 진단 및 LaTeX 템플릿 아키텍처 수립

---

## 1. 개요 및 작업 공간 구조 분석

`/home/imnyj/Workspace/paper4/` 작업 공간을 전수 조사한 결과, 강화학습 훈련 데이터, 미시 교통 시뮬레이션 로그, 정량 평가 CSV, 고해상도 시각화 플롯, 6개 챕터별 마크다운 초안 및 통합 마스터 초안이 체계적으로 구축되어 있음을 확인하였습니다.

### 주요 디렉토리 구조 및 역할
```
/home/imnyj/Workspace/paper4/
├── paper/                                  # 논문 마스터 초안 및 챕터별 원고
│   ├── paper4_draft_korean.md              # 887줄 규모의 한글 마스터 통합 원고 (Abstract ~ References 27편)
│   ├── 01_introduction.md                  # 제1장 서론 원고
│   ├── 02_related_works.md                 # 제2장 관련 연구 원고 (표 1 비교표 포함)
│   ├── 03_system_model.md                  # 제3장 시스템 모델 및 REMO-DQN 아키텍처 원고
│   ├── 04_scenario_flow.md                 # 제4장 동적 시나리오 흐름 원고
│   ├── 05_performance_evaluation.md        # 제5장 성능 평가 정량 분석 원고 (7대 지표, 표 5.1~5.12)
│   ├── 06_conclusion.md                    # 제6장 결론 및 향후 과제 원고
│   └── data/plots/fig_all_convergence.png  # 전체 수렴 곡선 플롯 (2370x1974)
├── visualizer/                             # 렌더링 완료된 최종 플롯 및 시각화 스크립트
│   ├── 1_reward_convergence.png            # [Fig 2] 14개 RL/DRL 모델 학습 보상 수렴 곡선 (1000x600)
│   ├── 2_ablation_study.png                # [Fig 7] 구조적 절제 연구 수렴 곡선 (1000x600)
│   ├── 3_moe_routing.png                   # [Fig 8] 차량 밀도별 MoE 3개 전문가 라우팅 가중치 (800x600)
│   ├── 4_tsne_clustering.png               # [Fig 9] ResNet 잠재 공간 t-SNE 2차원 혼잡도 클러스터링 (800x600)
│   ├── 5_hardware_feasibility.png          # [Fig 10/Table] OBU 하드웨어 복잡도 프로파일링 표 (600x300)
│   ├── 7_cbr_trace.png                     # [Fig 3] 100초 시계열 채널 점유율(CBR) 안정성 궤적 (1000x600)
│   ├── 8_pdr_vs_density.png                # [Fig 4] 차량 밀도(10~100 veh/km)별 패킷 전달률(PDR) (1000x600)
│   ├── 9_aoi_vs_density.png                # [Fig 5] 차량 밀도(10~100 veh/km)별 정보 연령(AoI) (1000x600)
│   ├── 10_pdr_vs_distance.png              # [Fig 6] 전송 거리(0~300m)별 패킷 전달률(PDR) (1000x600)
│   ├── config.md                           # 16개 비교 모델 전역 범례/색상/마커 표준 가이드
│   └── plot_all.py                         # Matplotlib 기반 플롯 일괄 생성 파이썬 스크립트
├── coder/data/                             # 시뮬레이션 실측 원본 정량 데이터셋 (CSV)
│   ├── reward_convergence.csv              # 14개 RL/DRL 모델의 100 에피소드 보상 수렴 원본
│   ├── ablation_study.csv                  # Vanilla DQN, DQN+MoE, REMO-DQN 절제 수렴 원본
│   ├── moe_routing.csv                     # 20~160 veh/km 구간 전문가 3종 가중치 분포
│   ├── tsne_clustering.csv                 # 150개 상태 샘플의 t-SNE 2차원 임베딩 좌표
│   ├── hardware_feasibility.csv            # MACs, Params, Latency, OBU 점유율 실측치
│   ├── cbr_trace.csv                       # 100초 연속 CBR 시계열 궤적 데이터
│   ├── pdr_vs_density.csv / raw_metrics_density.csv # 10~100 veh/km 구간 PDR/AoI 실측치
│   ├── aoi_vs_density.csv                  # 차량 밀도별 수신단 실제 AoI 실측치
│   ├── pdr_vs_distance.csv                 # 0~300m 거리별 PDR 실측치
│   └── oracle_dataset.csv                  # 약 3MB 규모의 전체 시뮬레이션 오라클 데이터셋
├── code/                                   # SUMO 시뮬레이션 엔진, 14개 에이전트 및 학습 코드
└── latex/                                  # [Target Directory] 신규 생성 예정 (IEEEtran 기반)
```

---

## 2. 논문 원고와 시각화 플롯(Figures) 간의 1:1 매핑 인벤토리

한글 마스터 초안(`paper4_draft_korean.md`)의 각 절에서 언급된 모든 성능 지표, 분석 그래프 및 아키텍처 다이어그램을 디스크 상의 실제 이미지 파일과 1:1 정밀 매핑하였습니다.

### 시각화 자산 매핑 테이블
| Figure No. (추천) | 논문 해당 절 | 다루는 주제 및 설명 | 원본 데이터 파일 | 생성된 플롯 이미지 경로 | 해상도 / 포맷 | 상태 및 권고사항 |
|:---:|:---:|:---|:---|:---|:---:|:---|
| **Fig. 1** | Section III-C / IV-D | REMO-DQN 3단 통합 아키텍처 및 데이터 흐름 다이어그램 | N/A (ASCII Block Diagram) | *Placeholder / TikZ / 신규 생성* | Vector / High-res | 마크다운 내 아스키 블록 다이어그램을 LaTeX TikZ 또는 고화질 블록 다이어그램으로 삽입 필요 |
| **Fig. 2** | Section V-B (Metric 1) | 14개 강화학습 및 DRL 모델의 보상 수렴도 및 샘플 효율성 비교 | `coder/data/reward_convergence.csv` | `visualizer/1_reward_convergence.png` | 1000x600 (RGBA) | 준비 완료 (Ready) |
| **Fig. 3** | Section V-C (Metric 2) | 100초 연속 시뮬레이션 하의 시계열 CBR 궤적 및 채널 안정성 (0.60 임계선 준수) | `coder/data/cbr_trace.csv` | `visualizer/7_cbr_trace.png` | 1000x600 (RGBA) | 준비 완료 (Ready) |
| **Fig. 4** | Section V-D-1 (Metric 3) | 차량 밀도(10~100 veh/km) 증가에 따른 패킷 전달률(PDR) 방어 성능 비교 | `coder/data/pdr_vs_density.csv` | `visualizer/8_pdr_vs_density.png` | 1000x600 (RGBA) | 준비 완료 (Ready) |
| **Fig. 5** | Section V-E-2 (Metric 5) | 차량 밀도(10~100 veh/km) 증가에 따른 실제 수신단 정보 연령(AoI) 비교 | `coder/data/aoi_vs_density.csv` | `visualizer/9_aoi_vs_density.png` | 1000x600 (RGBA) | 준비 완료 (Ready) |
| **Fig. 6** | Section V-F (Metric 6) | 전송 거리(0~300m)에 따른 패킷 전달률(PDR) 감쇄 및 원거리 신뢰성 비교 | `coder/data/pdr_vs_distance.csv` | `visualizer/10_pdr_vs_distance.png` | 1000x600 (RGBA) | 준비 완료 (Ready) |
| **Fig. 7** | Section V-H-1 | REMO-DQN 구조적 절제 연구(Ablation Study) 수렴 비교 (Vanilla vs MoE vs REMO) | `coder/data/ablation_study.csv` | `visualizer/2_ablation_study.png` | 1000x600 (RGBA) | 준비 완료 (Ready) |
| **Fig. 8** | Section V-H-2 | 차량 밀도(20~160 veh/km)에 따른 MoE 전문가 3종의 동적 라우팅 가중치 전이 스택 플롯 | `coder/data/moe_routing.csv` | `visualizer/3_moe_routing.png` | 800x600 (RGBA) | 준비 완료 (Ready) |
| **Fig. 9** | Section V-H-3 | ResNet 특징 추출기의 2차원 잠재 공간 t-SNE 혼잡도 클러스터링 산점도 | `coder/data/tsne_clustering.csv` | `visualizer/4_tsne_clustering.png` | 800x600 (RGBA) | 준비 완료 (Ready) |
| **Fig. 10** (선택) | Section V-G (Metric 7) | OBU 임베디드 플랫폼 상의 하드웨어 연산량 및 지연시간 프로파일링 | `coder/data/hardware_feasibility.csv` | `visualizer/5_hardware_feasibility.png` | 600x300 (RGBA) | 표 5.9(Table XI)와 병행 또는 단독 테이블로 처리 가능 |

### 추가 플롯 자산
- `/home/imnyj/Workspace/paper4/visualizer/convergence.png`: 대형 고해상도(2370x1974) 전체 수렴 플롯
- `/home/imnyj/Workspace/paper4/visualizer/line_density.png`: 와이드(3570x1466) 다중 지표 밀도 플롯
- `/home/imnyj/Workspace/paper4/paper/data/plots/fig_all_convergence.png`: 논문 원고 내 수렴 플롯

---

## 3. 정량 데이터 테이블(Tables) 전수 인벤토리

마스터 초안에는 총 14개의 대규모 정량 분석 테이블이 포함되어 있으며, 모두 출판급 2단(Two-column) 또는 1단 전폭(`table*`) LaTeX 테이블로 완벽하게 변환되어야 합니다.

| Table No. | 초안 표 번호 및 위치 | 테이블 명칭 (Title) | 차원 (열x행) | 권장 환경 | 주요 내용 |
|:---:|:---:|:---|:---:|:---:|:---|
| **Table I** | 표 1 (Sec. II-E) | Comprehensive Literature Comparison of V2X Congestion Control and RL Frameworks | 6 cols x 13 rows | `table*` (전폭) | 12개 선행 연구(ETSI, Ye, Hu, Zheng, Wang, Liu, Kang, Xu, Du, Park, Zhang 등)와 제안 모델 비교 |
| **Table II** | Table III-1 (Sec. III-E) | System Model and REMO-DQN Architecture Hyperparameters | 4 cols x 20 rows | `table` (1단) | 물리 계층, MAC/DCC, MDP 정식화, 신경망 구조, 학습 하이퍼파라미터 총괄 요약 |
| **Table III** | 표 5.1 (Sec. V-A-1) | Simulation Setup and Wireless Communication Parameters | 3 cols x 15 rows | `table` (1단) | SUMO 도로망, 802.11p 무선 채널, Nakagami-$m$, BPSK, 잡음지수 등 시뮬레이션 환경 파라미터 |
| **Table IV** | 표 5.2 (Sec. V-A-2) | Optimal Hyperparameters of 14 RL/DRL Benchmark Models Tuned via Optuna | 3 cols x 15 rows | `table` (1단) | 14개 비교 강화학습 모델의 Optuna 최적 하이퍼파라미터 구성값 |
| **Table V** | 표 5.3 (Sec. V-B) | Learning Convergence Statistics and Final Performance Comparison of 14 RL/DRL Models | 8 cols x 15 rows | `table*` (전폭) | 초기/최종/평균 보상, 최종 PDR, 최종 AoI, 평균 CBR 실측 통계 |
| **Table VI** | 표 5.4 (Sec. V-C) | Time-Series CBR Statistics and Channel Stability under 100-second Continuous Simulation | 7 cols x 4 rows | `table` (1단) | 평균/표준편차/최소/최대 CBR 및 0.60 상한 위반율 (REMO-DQN vs Vanilla vs DQN+MoE) |
| **Table VII** | 표 5.5 (Sec. V-D-1) | Packet Delivery Ratio (PDR) Comparison under Increasing Vehicle Density (10 to 100 veh/km) | 7 cols x 17 rows | `table*` (전폭) | 16개 모델의 저밀도/중밀도/고밀도 PDR 및 밀도 증가에 따른 하락폭 통계 |
| **Table VIII** | 표 5.6 (Sec. V-D-2) | Communication Energy Consumption and Energy Efficiency Comparison | 5 cols x 7 rows | `table` (1단) | 주행거리당 에너지 소모량(mJ/km) 및 Fixed 10Hz 대비 절감률 |
| **Table IX** | 표 5.7 (Sec. V-E-2) | Receiver-Side Age of Information (AoI) Comparison under Increasing Vehicle Density | 7 cols x 17 rows | `table*` (전폭) | 16개 모델의 저/중/고밀도 수신 AoI 및 증가폭 통계 (True AoI 실측치) |
| **Table X** | 표 5.8 (Sec. V-F) | Packet Delivery Ratio vs Transmission Distance (0 to 300 m) | 5 cols x 8 rows | `table` (1단) | 50m 간격 거리별 PDR 감쇄 추이 및 최장 300m 도달 신뢰성 비교 |
| **Table XI** | 표 5.9 (Sec. V-G) | Hardware Complexity, Memory Footprint, and Inference Latency Profiling on OBU Platform | 6 cols x 4 rows | `table` (1단) | ARM Cortex MCU 기준 MACs, 파라미터수, 추론 지연시간(1.2ms) 및 100ms 주기 점유율(1.2%) |
| **Table XII** | 표 5.10 (Sec. V-H-1) | Structural Ablation Study Performance Comparison of REMO-DQN Components | 8 cols x 4 rows | `table*` (전폭) | ResNet, MoE, Dueling 유무에 따른 PDR, AoI, CBR 표준편차 정량 기여도 |
| **Table XIII** | 표 5.11 (Sec. V-H-2) | Dynamic Routing Weight Distribution of 3 MoE Experts across Vehicle Densities (20~160 veh/km)| 5 cols x 9 rows | `table` (1단) | 차량 밀도별 Expert 1/2/3 가중치 및 주도 전문가 전이 분포 |
| **Table XIV** | 표 5.12 (Sec. V-H-3) | t-SNE 2D Latent Space Clustering Statistics and Cluster Separation across Traffic States | 6 cols x 4 rows | `table` (1단) | 저혼잡/중혼잡/고혼잡 3대 군집의 중심 좌표, 표준편차 및 분리도 통계 |

---

## 4. 수학 공식 및 알고리즘 의사코드 인벤토리

마스터 초안의 34개 핵심 수학 방정식과 알고리즘 의사코드를 체계적으로 추출하였습니다.

### 주요 수식 목록
1. **ReactDCC 상태 전이 이산 임계치 함수**: $\text{State}_{t+1} = f(\text{CBR}_t)$ (Sec. 2.1)
2. **AdaptDCC 선형 피드백 전송 주기 갱신식**: $T_{\text{GenCAM}}(k) = T_{\text{GenCAM}}(k-1) + \beta (\text{CBR}_{\text{smooth}}(k) - \text{CBR}_{\text{target}})$ (Sec. 2.1)
3. **DQN 시간차(TD) 손실 함수**: $L(\theta) = \mathbb{E}[(r + \gamma \max_{a'} Q(s', a'; \theta^-) - Q(s, a; \theta))^2]$ (Sec. 2.2)
4. **PPO 클리핑 목적 함수**: $L^{\text{CLIP}}(\theta) = \hat{\mathbb{E}}_t [\min(\rho_t(\theta) \hat{A}_t, \text{clip}(\rho_t(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t)]$ (Sec. 2.2)
5. **SAC 최대 엔트로피 목적 함수**: $J(\pi) = \sum_{t=0}^T \mathbb{E}[(r(s_t, a_t) + \alpha \mathcal{H}(\pi(\cdot|s_t)))]$ (Sec. 2.2)
6. **Decision Transformer 궤적 시퀀스 정식화**: $\tau = (\hat{R}_1, s_1, a_1, \dots, \hat{R}_T, s_T, a_T)$ (Sec. 2.3)
7. **기본 MoE 소프트맥스 라우팅 가중치 결합식**: $y = \sum_{k=1}^K g_k(x) E_k(x)$ (Sec. 2.4)
8. **차량 간 유클리드 공간 거리**: $d_{ij}(t) = \|\mathbf{p}_i(t) - \mathbf{p}_j(t)\|_2$ (Sec. 3.1.A)
9. **CAM 패킷 전송 에어타임 시간**: $T_{\text{tx}} = (L_{\text{CAM}} \times 8) / R_{\text{data}} \approx 0.74667\text{ ms}$ (Sec. 3.1.B)
10. **기준 경로 손실 및 로그 거리 전파 모델**: $\text{PL}(d_{ij}) = \text{PL}_0 + 10\alpha \log_{10}(d_{ij}/d_0)$ (Sec. 3.1.B)
11. **수신 전력 및 선형 평균 SNR**: $\bar{P}_{\text{rx}, ij} = P_{\text{tx}, i} - \text{PL}(d_{ij})$, $\bar{\gamma}_{\text{lin}, ij} = 10^{(\bar{P}_{\text{rx}} - N_0)/10}$ (Sec. 3.1.B)
12. **Nakagami-$m$ 닫힌 형태 수신 성공 확률**: $P_{\text{succ}}(d_{ij}, P_{\text{tx}, i}) = \exp(-x)(1 + x + x^2/2), x = m \gamma_{\text{th, lin}} / \bar{\gamma}_{\text{lin}, ij}$ (Sec. 3.1.B, 5.1.1)
13. **MAC 채널 점유율 기반 충돌 감쇠 계수**: $f_{\text{collision}}(\text{CBR}_j) = \max(0.1, 1.0 - 0.8 \cdot \text{CBR}_j(t))$ (Sec. 3.1.C)
14. **결합 패킷 수신 성공 확률**: $P_{\text{rx}, ij}(t) = P_{\text{succ}}(d_{ij}, P_{\text{tx}, i}) \cdot f_{\text{collision}}(\text{CBR}_j)$ (Sec. 3.1.C)
15. **ETSI CAM 동적 이벤트 트리거 조건식**: $\text{Trig}_i(t) = \mathbb{I}(|\Delta\theta| \ge 4^\circ \lor \|\Delta\mathbf{p}\| \ge 4\text{m} \lor |\Delta v| \ge 0.5\text{m/s} \lor \Delta t \ge 1.0\text{s})$ (Sec. 3.1.D)
16. **DCC 제약 반영 최종 전송 결정 지시자**: $\Psi_i(t) = \text{Trig}_i(t) \cdot \mathbb{I}(\Delta t_i \ge T_{\text{GenCAM}, i}(t)) \cdot \mathbb{I}(\Delta t_i \ge T_{\text{GenCAM, min}})$ (Sec. 3.1.D)
17. **순시 채널 점유율 (CBR)**: $\text{CBR}_i(t) = \min(1.0, |\mathcal{E}_{\text{sense}}(i,t)| \cdot T_{\text{tx}} / \Delta T_{\text{step}})$ (Sec. 3.1.E)
18. **EMA 평활 채널 점유율**: $\text{CBR}_{\text{smoothed}, i}(t) = (1 - \lambda_s)\text{CBR}_{\text{smoothed}, i}(t - \Delta T) + \lambda_s \text{CBR}_i(t)$ (Sec. 3.1.E)
19. **순시 링크 AoI 및 2000ms 상한 네트워크 평균 AoI**: $\overline{\text{AoI}}(t) = \frac{1}{|\mathcal{P}|}\sum \min(\Delta_{ij}(t)\times 1000, 2000)$ (Sec. 3.1.F)
20. **네트워크 평균 패킷 전달률 (PDR)**: $\text{PDR} = \frac{\text{성공 수신 패킷 합}}{\text{총 시도 패킷 기회 합}} \times 100\%$ (Sec. 3.1.F)
21. **5차원 정규화 상태 벡터**: $\mathbf{s}_t = [\text{CBR}, N_{\text{est}}/50, v/25, \Delta t/1.0, \text{CBR}_{\text{smoothed}}]^T$ (Sec. 3.2.A)
22. **16차원 2차원 직교 격자 행동 디코딩**: $T_{\text{GenCAM}} = \mathcal{T}_{\text{grid}}[\lfloor a/4 \rfloor]$, $P_{\text{tx}} = \mathcal{P}_{\text{grid}}[a \bmod 4]$ (Sec. 3.2.B)
23. **다중 목표 보상 함수**: $R_t = +0.01(N_{\text{est}}/50) - 1.0|\text{CBR}_{\text{smoothed}} - 0.60| - 0.10(\Delta t/1.0)$ (Sec. 3.2.C)
24. **ResNet 잔차 블록 연산**: $\mathbf{x}_{\text{res}} = \text{ReLU}(\mathbf{W}_2 \text{ReLU}(\mathbf{W}_1 \mathbf{x} + \mathbf{b}_1) + \mathbf{b}_2 + \mathbf{x})$ (Sec. 3.3)
25. **MoE 게이팅 라우터 및 그래디언트 분리**: $g_k(\mathbf{s}_t) = \frac{\exp(l_{g,k})}{\sum_{j=1}^3 \exp(l_{g,j})}, l_g = f_g(\text{sg}[\phi(\mathbf{s}_t)])$ (Sec. 3.3)
26. **Dueling 상태 가치 및 행동 이점 결합**: $Q_k(\mathbf{s}_t, a) = V_k(\mathbf{s}_t) + (A_k(\mathbf{s}_t, a) - \frac{1}{16}\sum_{a'=0}^{15} A_k(\mathbf{s}_t, a'))$ (Sec. 3.3)
27. **전문가 Q-값 소프트 가중합 합성**: $Q(\mathbf{s}_t, a) = \sum_{k=1}^3 g_k(\mathbf{s}_t) Q_k(\mathbf{s}_t, a)$ (Sec. 3.3)
28. **MoE 부하 균등화 보조 손실**: $\mathcal{L}_{\text{LB}}(\bar{\mathbf{g}}) = \lambda_{\text{LB}} \cdot \text{CV}^2(\bar{\mathbf{g}}) = \lambda_{\text{LB}} \cdot \frac{\text{Var}(\bar{\mathbf{g}})}{\text{Mean}(\bar{\mathbf{g}})^2}$ (Sec. 3.3)
29. **Double DQN 타깃 가치 계산**: $y_b = r_b + \gamma Q(\mathbf{s}'_b, \arg\max_{a'} Q(\mathbf{s}'_b, a'; \theta); \theta^-)(1 - d_b)$ (Sec. 3.4)
30. **전체 최적화 손실 함수**: $\mathcal{L}_{\text{total}}(\theta) = \frac{1}{|\mathcal{B}|}\sum (Q(\mathbf{s}_b, a_b; \theta) - y_b)^2 + 0.01 \cdot \text{CV}^2(\bar{\mathbf{g}})$ (Sec. 3.4)
31. **Bianchi 2차원 마르코프 조건부 충돌 확률**: $P_{\text{collision}} = 1 - (1 - \tau)^{N-1}$ (Sec. 4.2)
32. **MAC 큐 누적 동역학**: $Q_k(t+1) = \max(0, Q_k(t) + \lambda_k(t) - \mu_k(t))$ (Sec. 4.1)
33. **시간 평균 정보 연령 적분 및 사다리꼴 면적**: $\bar{\Delta} = \frac{1}{\mathcal{T}} \sum Q_k$ (Sec. 5.5.1)
34. **연속 패킷 손실 시 면적 팽창 페널티**: $Q_k \propto \mathcal{O}(M^2)$ (Sec. 5.5.1)

### 알고리즘 의사코드 (Algorithm 1)
- **Algorithm 1**: Decentralized REMO-DQN Training and Real-Time Closed-Loop DCC Inference
  - 포함 내용: Replay Buffer 초기화, 타깃 네트워크 초기화, 에피소드 루프, 100ms 타임스텝 의사결정, ResNet 특징 추출, MoE 라우팅, Dueling Q-값 합성, $\epsilon$-탐욕 행동 선택, 무선 채널 전이 및 CAM 전송, 보상 계산, 미니배치 샘플링, Double DQN 타깃 계산, 부하 균등화 손실 계산, 파라미터 역전파 갱신, 타깃 주기적 동기화.

---

## 5. 참고문헌 27편 전수 인벤토리 및 BibTeX 매핑

마스터 초안 말미(lines 860-886)에 수록된 27편의 논문/표준 문헌에 대한 완전한 서지 정보와 BibTeX 키 매핑을 구축하였습니다.

| Ref No. | BibTeX Key | 유형 | 저자 (Authors) | 논문/표준 제목 | 저널 / 학술대회 / 표준 기구 | 연도/권/호/페이지 |
|:---:|:---|:---:|:---|:---|:---|:---:|
| [1] | `Arena2019overview` | article | F. Arena and P. Pau | An overview of vehicular communications | *Future Internet* | 2019, 11(2), p. 27 |
| [2] | `Kenney2011dsrc` | article | J. B. Kenney | Dedicated short-range communications (DSRC) standards in the United States | *Proc. IEEE* | 2011, 99(7), pp. 1162–1182 |
| [3] | `ETSI_EN_302_637_2` | standard | ETSI | Intelligent Transport Systems (ITS); Vehicular Communications; Basic Set of Applications; Part 2: Specification of Cooperative Awareness Basic Service | *ETSI EN 302 637-2 V1.4.1* | Nov. 2019 |
| [4] | `SAE_J2945_1` | standard | SAE International | On-Board System Requirements for V2V Safety Communications | *SAE Standard J2945/1* | Mar. 2016 |
| [5] | `ETSI_TS_102_687` | standard | ETSI | Intelligent Transport Systems (ITS); Decentralized Congestion Control (DCC) Methods: Part 1: Architecture and Mechanisms | *ETSI TS 102 687 V1.2.1* | Jul. 2018 |
| [6] | `Zheng2022aoi` | article | X. Zheng, C. Chen, and X. Guan | Age-of-Information-Oriented Congestion Control for Vehicular Networks | *IEEE Trans. Intell. Transp. Syst.* | 2022, 23(8), pp. 12845–12856 |
| [7] | `Liu2024aoi` | article | Y. Liu, C. Chen, and X. Guan | Age of Information and Energy Minimization in Vehicular Networks Using Deep Reinforcement Learning | *IEEE Trans. Intell. Transp. Syst.* | 2024, 25(4), pp. 3821–3834 |
| [8] | `ETSI_TS_103_175` | standard | ETSI | Intelligent Transport Systems (ITS); Cross Layer DCC Management Entity for operation in ITS G5A and ITS G5B medium | *ETSI TS 103 175 V1.1.1* | Jun. 2015 |
| [9] | `Bansal2013limeric` | article | G. Bansal, J. B. Kenney, and C. E. Rohrs | LIMERIC: A linear adaptive message rate algorithm for DSRC congestion control | *IEEE Trans. Veh. Technol.* | 2013, 62(9), pp. 4182–4197 |
| [10] | `Ye2019drl` | article | H. Ye, G. Y. Li, and B.-H. F. Juang | Deep reinforcement learning based resource allocation for V2V communications | *IEEE Trans. Veh. Technol.* | 2019, 68(4), pp. 3163–3173 |
| [11] | `Hu2021drl` | article | X. Hu, S. Liu, R. Chen, W. Wang, and Z. Wang | Deep reinforcement learning for resource allocation in vehicular networks: A cross-layer approach | *IEEE Trans. Wireless Commun.* | 2021, 20(11), pp. 7412–7426 |
| [12] | `Wang2023mappo` | article | Q. Wang, Y. Liu, J. Chen, W. Zhang, and C. Sun | Multi-agent deep reinforcement learning for cooperative resource allocation in dense V2X networks | *IEEE Trans. Wireless Commun.* | 2023, 22(6), pp. 4102–4116 |
| [13] | `Mnih2015nature` | article | V. Mnih, K. Kavukcuoglu, D. Silver, et al. | Human-level control through deep reinforcement learning | *Nature* | 2015, 518(7540), pp. 529–533 |
| [14] | `vanHasselt2016double` | inproceedings | H. van Hasselt, A. Guez, and D. Silver | Deep reinforcement learning with double Q-learning | *Proc. AAAI Conf. Artif. Intell.* | 2016, pp. 2094–2100 |
| [15] | `Wang2016dueling` | inproceedings | Z. Wang, T. Schaul, M. Hessel, et al. | Dueling network architectures for deep reinforcement learning | *Proc. ICML* | 2016, pp. 1995–2003 |
| [16] | `Yu2022mappo` | inproceedings | C. Yu, A. Velu, E. Vinitsky, et al. | The surprising effectiveness of PPO in cooperative multi-agent games | *NeurIPS* | 2022, pp. 24611–24624 |
| [17] | `Lowe2017maddpg` | inproceedings | R. Lowe, Y. Wu, A. Tamar, et al. | Multi-agent actor-critic for mixed cooperative-competitive environments | *NeurIPS* | 2017, pp. 6379–6390 |
| [18] | `Rashid2018qmix` | inproceedings | T. Rashid, M. Samvelyan, C. Schroeder, et al. | QMIX: Monotonic value function factorisation for deep multi-agent reinforcement learning | *Proc. ICML* | 2018, pp. 4295–4304 |
| [19] | `Chen2021decision` | inproceedings | L. Chen, K. Lu, A. Rajeswaran, et al. | Decision transformer: Reinforcement learning via sequence modeling | *NeurIPS* | 2021, pp. 15084–15097 |
| [20] | `Janner2021trajectory` | inproceedings | M. Janner, Q. Li, and S. Levine | Offline reinforcement learning as one big sequence modeling problem | *NeurIPS* | 2021, pp. 1273–1286 |
| [21] | `Shazeer2017moe` | inproceedings | N. Shazeer, A. Mirhoseini, K. Maziarz, et al. | Outrageously large neural networks: The sparsely-gated mixture-of-experts layer | *Proc. ICLR* | 2017 |
| [22] | `Xu2025moe` | article | Y. Xu, J. Wang, R. Zhang, et al. | Mixture of experts for decentralized generative AI and reinforcement learning in wireless networks: A comprehensive survey | *IEEE Commun. Surveys Tuts.* | 2025, 27(1), pp. 1–35 |
| [23] | `Zhang2026gma` | article | Z. Zhang, Y. Xiao, Z. Han, and H. V. Poor | Generalizable multiple access with meta-reinforcement learning and mixture-of-experts for heterogeneous wireless networks | *IEEE Trans. Mobile Comput. / IEEE Trans. Wireless Commun.* | 2026, early access |
| [24] | `Kang2024task` | article | J. Kang, D. Niyato, Z. Xiong, S. Mao, and D. I. Kim | Task-oriented mixture-of-experts for resource allocation in multi-modal edge intelligence | *IEEE J. Sel. Areas Commun.* | 2024, 42(10), pp. 2780–2795 |
| [25] | `Du2025generative` | article | H. Du, J. Wang, D. Niyato, J. Kang, et al. | Generative AI-enabled edge network slicing with decentralized mixture-of-experts | *IEEE Network* | 2025, 39(2), pp. 112–120 |
| [26] | `Park2025ensemble` | article | S. Park and D. Kim | Ensemble deep Q-learning for decentralized congestion control in dense vehicular networks | *IEEE Wireless Commun. Lett.* | 2025, 14(2), pp. 310–314 |
| [27] | `Bhattacharyya2024hybrid` | article | S. Bhattacharyya, P. Kumar, S. Darshi, et al. | Hybrid relaying based cross layer MAC protocol using variable beacon for cooperative vehicles | *IEEE Trans. Veh. Technol.* | 2024, 73(2), pp. 2480–2495 |

---

## 6. 로컬 컴파일 환경 진단 및 Overleaf 호환성 전략

### A. 로컬 시스템 툴체인 진단 결과
1. **LaTeX 컴파일러 (`pdflatex`, `xelatex`, `latexmk`, `bibtex`)**:
   - 호스트 OS 상에 `texlive` 패키지가 설치되어 있지 않음 (`which pdflatex` 결과 없음).
   - 유틸리티: `make` 및 `python3`는 정상 구동 가능.
2. **IEEEtran 클래스 파일 확보**:
   - 로컬 디스크 내 `/home/imnyj/Workspace/paper1/writer/IEEEtran.cls` (IEEE 공식 V1.8b 최신 버전)이 존재하여 완벽한 자체 독립(Self-contained) 번들 구축이 가능함.
3. **Overleaf 완벽 호환성 요구사항**:
   - 사용자가 `/home/imnyj/Workspace/paper4/latex/` 디렉토리를 통째로 압축(`zip`)하여 Overleaf(TeX Live 2023/2024 엔진)에 업로드하였을 때, 추가 설정이나 파일 누락 없이 **원클릭으로 에러 0건(Clean Compile)** 컴파일이 되어야 함.

---

## 7. IEEE TWC 출판급 LaTeX 아키텍처 및 패키지 사양

### A. 타깃 디렉토리 레이아웃 (`/home/imnyj/Workspace/paper4/latex/`)
```
/home/imnyj/Workspace/paper4/latex/
├── main.tex                    # 마스터 LaTeX 소스 코드 (Abstract부터 Conclusion까지 완결)
├── references.bib              # 27개 서지 정보가 담긴 완전한 BibTeX 파일
├── IEEEtran.cls                # IEEE Transactions 공식 클래스 파일 (v1.8b)
├── IEEEtran.bst                # IEEE 표준 참고문헌 스타일 파일 (선택/내장)
├── figures/                    # 논문 삽입용 고해상도 플롯 디렉토리
│   ├── 1_reward_convergence.png
│   ├── 2_ablation_study.png
│   ├── 3_moe_routing.png
│   ├── 4_tsne_clustering.png
│   ├── 7_cbr_trace.png
│   ├── 8_pdr_vs_density.png
│   ├── 9_aoi_vs_density.png
│   ├── 10_pdr_vs_distance.png
│   └── architecture_diagram.png (또는 TikZ)
├── Makefile                    # 로컬 컴파일 및 자동 빌드용 스크립트
├── validate_syntax.py          # 수식/참고문헌/문법 정합성 검증 파이썬 스크립트
└── README.md                   # Overleaf 업로드 및 컴파일 가이드라인
```

### B. 필수 LaTeX 패키지 구성 및 역할
```latex
\documentclass[journal]{IEEEtran}

% 1. 수학 및 기호 패키지
\usepackage{amsmath,amssymb,amsfonts,bm}   % 복합 수식, 볼드체 벡터, 기호
\usepackage{mathtools}                    % 수식 확장 기능

% 2. 참고문헌 인용 패키지
\usepackage{cite}                         % [1]-[3] 형태 자동 정렬 및 압축

% 3. 그래픽 및 그림 패키지
\usepackage{graphicx}                     % 고해상도 PNG/PDF 플롯 삽입
\usepackage{subfig}                       % IEEEtran 권장 서브피규어 환경 (\subfloat)
% 주의: IEEEtran에서는 'subcaption'보다 'subfig' 또는 기본 \subfloat 사용이 권장됨

% 4. 출판급 테이블 패키지
\usepackage{booktabs}                     % \toprule, \midrule, \bottomrule 출판급 테이블선
\usepackage{multirow,multicol}            % 복합 헤더 및 셀 병합
\usepackage{tabularx}                     % 2단 칼럼 폭 맞춤형 자동 줄바꿈 테이블
\usepackage{array}                        % 정밀한 칼럼 정렬

% 5. 알고리즘 의사코드 패키지
\usepackage{algorithm}                    % 알고리즘 플로팅 환경
\usepackage{algorithmic}                  % 알고리즘 라인별 의사코드 작성

% 6. 기타 필수 타이포그래피 및 편의 패키지
\usepackage{url}                          % URL 및 DOI 링크
\usepackage{xcolor}                       % 텍스트 강조 및 색상 지원
\usepackage{microtype}                    % 타이포그래피 마진 및 자간 최적화
```

### C. IEEE TWC 형식 준수 핵심 가이드라인
1. **저작권 및 헤더**: `\markboth{IEEE Transactions on Wireless Communications,~Vol.~XX, No.~XX,~2026}{REMO-DQN for Decentralized Congestion Control in Dense V2X Networks}` 적용.
2. **수식 표기**: 벡터 및 행렬은 볼드체 `\mathbf{s}_t`, 스칼라 및 인덱스는 이탤릭체 $t$, $i$, 집합은 `\mathcal{S}`, `\mathcal{A}` 표기.
3. **단위 표기**: $\text{dBm}$, $\text{MHz}$, $\text{ms}$, $\text{veh/km}$, $\text{mJ/km}$, $\text{Mbps}$ 등 물리 단위는 로만체(`\text{...}`) 처리.
4. **테이블 크기 및 정렬**:
   - 1단 칼럼 테이블(표 5.1, 5.2, 5.4, 5.6, 5.8, 5.9, 5.11, 5.12)은 `\begin{table}[t]`로 구성.
   - 2단 전폭 테이블(표 1, 표 5.3, 5.5, 5.7, 5.10)은 `\begin{table*}[t]`로 구성.
   - 모든 테이블은 세로선(`|`)을 배제하고 `booktabs`의 `\toprule`, `\midrule`, `\bottomrule`로 미려하게 조판.
5. **그림 크기**: 1단 칼럼 그림은 `width=\linewidth` 또는 `width=3.4in`, 2단 전폭 그림은 `figure*` 환경에서 `width=0.9\textwidth` 적용.

---

## 8. 후속 작성을 위한 체크리스트 및 권고사항

1. **영어 학술 번역 (Academic English)**:
   - 과장된 표현, 구어체 및 AI 상투어구(`delve`, `testament`, `game-changer`, `crucial milestone`) 배제.
   - IEEE TWC 저널 특유의 건조하고(dry), 정밀하며(precise), 객관적이고(objective) 고도로 기술적인(highly technical) 수동태/능동태 조화 영문체 구사.
2. **27개 인용 완벽 연계**:
   - 본문 내 모든 인용 부호(`[1]`, `[2]`, ..., `[27]`)가 `\cite{Arena2019overview}` 등으로 빠짐없이 1:1 매핑되어야 함.
3. **수식 번호 및 참조 완전성**:
   - 주요 34개 수식에 `\label{eq:...}`을 부여하고, 본문에서 `\eqref{eq:...}` 또는 `(1)` 형태로 일관되게 참조.
4. **플롯 파일 복사**:
   - `/home/imnyj/Workspace/paper4/visualizer/*.png` 파일들을 타깃 디렉토리 `/home/imnyj/Workspace/paper4/latex/figures/`로 복사하여 독립 경로 구성.

---
**조사 완료 일시**: 2026-08-18T13:42:00+09:00  
**보고서 저장 위치**: `/home/imnyj/.agents/teamwork_preview_explorer_survey_3/survey_assets_env.md`
