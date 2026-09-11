# CARLTON을 유사 범주에서 뺀 이유 (2026-09-05)

이 디렉터리에 격리한 `carlton.py`는 아래 문헌의 재구현이었다.

> Y. Cohen, T. Gafni, R. Greenberg and K. Cohen, "SINR-Aware Deep Reinforcement
> Learning for Distributed Dynamic Channel Allocation in Cognitive Interference
> Networks," IEEE Transactions on Wireless Communications, vol. 24, no. 1,
> pp. 228-243, 2025. DOI: 10.1109/TWC.2024.3491035

2026-09-05에 이 자리를 아래 문헌으로 교체했다. 새 구현은
`coder/src/baselines/hoorl.py`에 있다.

> J. Xu, X. Zhou, M. Song, W. Wang, D. Niyato and C. Yuen, "AoI and Energy-Aware
> Resource Scheduling for Crowdsensing: A Hybrid Reinforcement Learning
> Framework," IEEE Transactions on Vehicular Technology, vol. 75, no. 8,
> pp. 18102-18115, 2026. DOI: 10.1109/TVT.2026.3675626

## 교체의 주된 이유

CARLTON은 SINR을 목적으로 삼는 분산 채널 할당 방법이며 AoI 목적함수를 전혀
가지고 있지 않다. 유사 범주는 본 논문과 방법론적으로 가장 가까운 연구를 담는
자리인데, AoI 인지 스케줄링을 다루는 논문의 그 자리에 AoI 목적이 없는 연구를
두면 왜 이 논문이 가장 가까운 연구인지 설명할 수 없다. 재구현이 보상을
파이프라인의 4항 AoI 보상으로 치환하고 있었으므로, 실제로 비교되는 것은
CARLTON의 학습기와 채널 할당 정식화였을 뿐 CARLTON의 목적이 아니었다. 이는
하이퍼파라미터 조정으로 해소되는 문제가 아니라 문헌 선정의 문제다.

## 부수적으로 확인된 구조적 결함

탐색 온도 `policy_beta`가 기본값에서 backup 연산자의 `omega`에 묶여 있었다.
DeepMellow의 통상적인 지름길이기는 하지만, 볼츠만 정책 `softmax(beta * q)`는 Q
값의 척도에 불변이 아니다. 따라서 학습이 진행되어 Q의 규모가 커지면 같은
`beta`에서도 정책이 점점 argmax로 붕괴하며, CARLTON에는 epsilon-greedy 대체
경로가 없어서 되돌아올 방법이 없다. 재구현은 `policy_beta`를 별도 인자로
노출하고 분기별 정책 엔트로피를 로그에 남겨 붕괴가 관측되도록 해 두었지만,
온도 자체를 척도 불변으로 만들지는 않았다.

## 이 문헌 자체에는 결함이 없다

서지는 검증되었고(DOI 조회로 확인) 방법도 건전하다. 배제 사유는 오로지
"AoI 목적이 없는 연구가 유사 범주에 놓여 있었다"는 배치의 문제다.

## 되살릴 수 있는 조건

아래 두 가지가 함께 충족되면 이 구현을 다시 쓸 수 있다.

1. 유사 범주가 아니라 **순수한 채널 할당 대조군**을 따로 두기로 결정할 것.
   그 자리에서는 AoI 목적이 없다는 점이 결함이 아니라 대조군의 성질이 된다.
2. 탐색 온도를 **Q 값 척도에 불변**이 되도록 고칠 것. 예를 들어 분기별 Q를
   자기 표준편차로 정규화한 뒤 온도를 적용하거나, DeepMellow 원래의 근찾기로
   beta를 매 스텝 다시 구하는 방식이 있다. 어느 쪽이든 그 변경은 원논문의
   정책을 바꾸는 것이므로 원고에 명시해야 한다.

되살릴 때는 `src/baselines/__init__.py`의 레지스트리와 `BASELINE_CATEGORIES`,
`src/hpo.py`의 탐색 공간 분기, `tests/test_baselines_action_roundtrip.py`의
CARLTON 관련 검사를 함께 복구해야 한다. 이 파일들은 2026-09-05 교체 시점에
HOORL 기준으로 다시 쓰였다.
