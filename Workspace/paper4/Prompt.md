## 해야 할 일

* State 제대로 설계하기

* 보상 함수 제대로 설계하기

* 비교방안 물색
 - 최근 방안 3개: RainbowDQN 등 포함
 - 최신 방안 3개: 최신 논문에서 찾아볼 것 (2025~2026)
 - 기본 모델 3개: TD3, PPO, SAC 등 (SB3로 구현)
 - 기타 비교 필요 모델 들

* 시뮬레이션 검증 및 완성

* 비교 방안들 optuna로 하이퍼파라미터 최적화

* 최적화된 하이퍼파라미터로 성능 뽑기

* 성능들을 비교해가며 제안 방안 찾기 시작 (State와 action, reward 등을 기반으로 설계해볼것)
 - 베이스를 무엇으로 둘지
 - 내부 네트워크는 어떻게 바꿀지
 - 구조는 어떻게 설계할지
 - 정확도와 보상을 최대로 하기 위한 다른 방법은 무엇이 있을지

* 기존 성능평가들
 - ablation study (convergence curves로 표현)
 - sensitivity analysis는 optuna로 최적화
 - 비교모델들과 같이 convergence curves
 - contributions에 대한 검증 평가 지표들
 - HW feasibility 테이블 (RSU가 감당가능한지, 통신 서비스에 지장을 안 줄 수 있는지)
 - 통신 성능 (Density, Distance 등에 따른 유효 AoI, 혼잡도, 충돌 등)