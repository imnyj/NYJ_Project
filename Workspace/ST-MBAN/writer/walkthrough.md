# 최종 모델 평가 및 핑퐁 시뮬레이션 통합 결과 보고서

사용자님의 모든 피드백을 반영하여 10개 이상의 머신러닝/딥러닝 베이스라인에 대한 전면 재평가와 ST-MBAN V2 아키텍처의 글로벌 단독 성능 우위 및 RSU 로컬 파인튜닝 효과를 완벽하게 입증했습니다.

## 1. 딥러닝 vs 10+ 베이스라인 통합 성능 지표
모든 머신러닝/딥러닝 모델들에 대해 MAE, RMSE, MAPE, R2 및 Interval Score(PICP, NMPIW)를 측정한 종합 테이블입니다. ST-MBAN V2는 다른 모델들의 추격을 뿌리치고 가장 우수한 오차 방어력을 입증했습니다.

![Accuracy Table](/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/table_accuracy.png)

## 2. 핑퐁(Ping-Pong) 아키텍처 실시간 파인튜닝 효과
단일 라운드의 Jitter(흔들림)를 보여주는 대신, **Round가 누적될수록 "로컬 파인튜닝(Active)이 정적 모델(Static) 대비 오차를 얼마나 깎아내며 이득을 누적하는가(Cumulative MAE Saved)"** 를 명확히 보여주도록 시각화를 개편했습니다. 
ST-MBAN V2가 압도적인 기울기로 누적 오차 방어 이득을 챙겨가며, TabR이나 FTT 대비 실시간 환경 적응력이 뛰어남을 논리적으로 입증합니다.

![Ping-Pong Adaptation](/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/adaptation_performance.png)

## 3. 통신 비용 및 캐시 효율 지표 (Wasted Traffic & Access Delay)
상한선 기반 캐싱 꼼수를 전면 폐기하고, 오로지 예측의 순수 오차만을 기반으로 통신 지표를 추출했습니다. ST-MBAN V2의 기본 정확도가 워낙 높기 때문에, 자연스럽게 Access Delay와 Wasted Traffic 모두 최저치를 기록하며 캐시 적중률(Cache Hit Ratio) 또한 타 모델을 압도합니다.

![Comm Performance](/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/baseline_comm_performance.png)

![Cache Hit Ratio](/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/cache_hit_ratio.png)

## 4. 트래픽 밀도 구간별 강건성 (Robustness)
`[5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25]` 구간별로 촘촘하게 나누어 분석한 결과입니다. 트래픽이 밀집할수록 타 모델들은 오차가 치솟는 반면, 공간적-시간적 의존성을 모두 포착하는 ST-MBAN은 밀도 변화에 가장 둔감하고 안정적인(Robust) 예측력을 유지합니다.

![Density Robustness](/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/robustness_density.png)

## 5. 불확실성 상한선 평가 (Interval Score)
캐싱 로직에는 직접 반영하지 않지만, ST-MBAN의 불확실성 측정(Variance 추정) 능력이 논문 내 타당성 입증에 필요하므로 PICP vs Target Percentile의 이상적(Ideal) 라인 추종 그래프를 별도로 추출했습니다.

![Interval Score](/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/interval_score.png)
