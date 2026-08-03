# H-ST-MBAN 논문 피드백 기반 수정 계획 (Revision Plan)

---

## 1. $\alpha, \beta$ 파라미터 충돌 해결 (Line 335 및 345 부근)
* **문제점**: 모델 앙상블 가중치(learnable parameters)인 $\alpha, \beta$와, 캐싱 마진 $\eta(t)$ 계산식에 사용된 가중치 $\alpha, \beta$ 기호가 중복되어 혼동을 유발함.
* **수정 계획**:
  * $\eta(t)$ 계산식에 쓰인 기호를 $\gamma$와 $\delta$ (혹은 $\lambda_1, \lambda_2$) 등 완전히 다른 수학 기호로 교체.
  * 해당 파라미터들이 채널 상태(Packet success rate, SNR variance)를 반영하는 독립적인 스케일링 팩터임을 명시하여 딥러닝 가중치와 명확히 선을 그음.

## 2. $z_i$와 MHA 간의 논리적 연결 보강 (수식 부근)
* **문제점**: Residual Block(1단계)을 통과한 $z_i$가 MHA(2단계)로 어떻게 들어가는지 설명이 부족함.
* **수정 계획**:
  * 각 도메인 브랜치(Kinematic, Traffic, Social)에서 출력된 벡터 $z_k, z_t, z_s$가 어떻게 동일한 임베딩 차원($D_{model}$)으로 투영되는지 설명.
  * 이 벡터들이 시퀀스 토큰(Sequence tokens)처럼 취급되어 하나의 행렬 $Z = [z_k; z_t; z_s]$로 연결(Concatenate)된 후, MHA의 Query, Key, Value 연산을 통해 크로스 도메인(Cross-domain) 특징을 교환하게 된다는 논리적 흐름을 보강.

## 3. 연산 복잡도(Complexity) 근거 추가 (Line 343 부근)
* **문제점**: IoT 저널급(T-ITS 포함)에서는 알고리즘의 복잡도에 대한 엄밀한 증명이나 가상 코드(Pseudo-code)를 요구할 수 있음.
* **수정 계획**:
  * 논문 본문 내에 **Pseudo-code (Algorithm 블록)**를 추가하여 H-ST-MBAN의 추론 및 캐싱 절차를 명확히 제시.
  * 이론적 시간 복잡도($\mathcal{O}(D_{model}^2 \times L)$)를 수식으로 간략히 유도하는 문장을 추가하여 연산량이 RSU 엣지에 적합함을 증명.

## 4. 'Online' 용어의 보수적 교체 (Line 375, 545 등)
* **문제점**: 트리 모델은 'from scratch' 학습이 기본이므로, 지속적/실시간 업데이트를 뜻하는 'Online'이라는 단어는 AI 리뷰어에게 공격받을 소지가 큼.
* **수정 계획**:
  * 논문 전체에서 사용된 **"Online Fine-Tuning"** 이라는 명칭을 **"Periodic Local Adaptation"** 또는 **"Batch-based Edge Fine-Tuning"**으로 전면 교체.
  * "RSU가 새로운 데이터셋 Queue를 채운 뒤, 트리 모델은 처음부터 재학습하고 신경망 가중치는 미세 조정(Fine-tuning)하는 '주기적(Periodic)' 구조"임을 명확히 서술.

## 5. Boosting Rounds vs Epochs 분리 서술 (Line 406 부근)
* **문제점**: ML의 트리 앙상블 횟수(Boosting rounds)와 DL의 가중치 업데이트 횟수(Epochs)를 동일한 'Iteration' 개념으로 묶어서 비교하는 것은 위험함.
* **수정 계획**:
  * 해당 비교 단락에서 두 개념을 엄격하게 분리하여 서술.
  * "머신러닝 모델의 X축은 앙상블 된 트리의 수(Boosting Rounds)를 의미하며, 딥러닝 모델의 경우 역전파 가중치 업데이트 횟수(Training Epochs)를 의미한다"라고 명시하여 두 모델이 특정 횟수 이후 수렴한다는 결과적인 특징에 초점을 맞춤.

## 6. 90.7% Cache Hit Ratio 달성 메커니즘 고찰 (Line 578 부근)
* **문제점**: 캐시 적중률이 왜 높게 나왔는지에 대한 인과관계(Discussion) 설명 부족.
* **수정 계획**:
  * Performance Evaluation 섹션 끝부분에 **Discussion 단락**을 신설.
  * "낮은 예측 오차(MAE)가 차량의 실제 체류 시간과 캐싱 윈도우를 일치시켜 불필요한 콘텐츠 밀어내기(Eviction)를 막았다"는 점 서술.
  * "안전 마진인 $\eta(t)$가 무선 채널의 일시적 드롭 상황에서도 조기 캐시 삭제를 막는 버퍼 역할을 수행하여 결과적으로 90.7%의 높은 Hit Ratio를 달성할 수 있었다"는 논리적 결론 추가.
