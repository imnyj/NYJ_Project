---
name: paper2-uam-handover-project
description: paper2는 UAM 선제적 핸드오버 스케줄링 논문이며, paper5의 자산을 승계하고 PAMDP 구조를 유지한다
metadata:
  type: project
---

`Workspace/paper2`는 UAM(Urban Air Mobility) 선제적 핸드오버 스케줄링 논문이다. eVTOL 기체가 Cellular, RSU, Starlink LEO로 이루어진 SAGIN 다중 계층 망을 통과하며 겪는 핸드오버를 사전에 스케줄링한다. 2026년 9월 4일 사용자가 확정한 사항은 다음과 같다.

- **대상은 UAM이지 UAV가 아니다.** 기획 초기에 UAV로 잘못 기재된 이력이 있으므로 문서와 코드에서 `UAV`, `drone`, `무인기` 표기를 발견하면 UAM 기준으로 바로잡는다.
- **`Workspace/paper5`의 자산을 paper2로 승계한다.** paper5에는 같은 주제로 먼저 진행된 3D 도심 시뮬레이터(`environment.py`), 13종 비교 모델(`models.py`), 통신 파라미터(`config.md`), Optuna 결과표가 있다. paper5는 홈 저장소에 있고 paper2는 독립된 git 저장소다.
- **제안 방안은 PAMDP를 유지한다.** 이산 행동인 타겟 망 선택과 연속 행동인 다음 결정까지의 대기 시간을 함께 결정한다. paper5가 쓰던 매 타임스텝 이산 선택 방식의 GNN-Transformer-PPO를 그대로 계승하지 않는다.
- **`overleaf/main.tex`는 다른 논문(윤종필 1저자 VaT-Min, V2V 프리캐싱)이다.** IEEEtran 프리앰블과 저자 블록, 표 서식만 물려받고 본문은 paper2 내용으로 새로 쓴다.

**Why:** paper2와 paper5가 같은 주제를 다루고 있어 관계를 정리하지 않으면 자기표절 위험과 중복 작업이 발생한다. 또한 UAV 전제로 쓰인 기획 문서를 그대로 두면 상태 공간과 오차 모델이 UAM 시나리오와 어긋난 채 구현으로 넘어간다.

**How to apply:** paper2 작업을 시작할 때 `Workspace/paper2/.rules/`와 `idea/`를 먼저 읽고, paper5의 대응 파일과 대조한다. 서브에이전트는 [[paper-subagent-team-convention]]에 따라 `p2-` 접두사 팀을 쓴다.

## 2026년 9월 4일 추가 확정 사항

- **paper5의 13종 비교 실험은 위조였다.** `paper5/etc/scripts/generator.py`가 모델 이름별로 미리 정한 상수에 난수를 더해 점수를 만들었고, 제안 방안 분기에는 `# Much better` 주석이 달려 있었다. 저장소에 딥러닝 라이브러리 import가 한 줄도 없어 신경망은 구현된 적이 없다. `related_works.json`의 문헌 3건도 저자명이 자리표시자인 가짜다. 상세 근거는 `Workspace/paper2/idea/paper5_결과_위조_검증.md`에 있다. **살아남는 것은 시뮬레이터 본체뿐이다.**
- **의사결정 간격이 가변이므로 시간 기반 할인을 쓴다.** 판단 횟수 기준 할인을 쓰면 대기 시간을 길게 잡아 판단을 줄이는 정책이 성능과 무관하게 유리해진다.
- **상태는 계획 정보(위첨자 sch)와 실측 정보(위첨자 act)로 나눈다.** 계획 정보는 예측 지평까지의 미래를 허용하고 실측 정보는 현재 시각까지만 허용한다. 이 두 줄이 데이터 누수 판정 기준이며 `mathematical_model.md` 2.2절에 표로 있다.
- **C2 연속 두절 상한은 보상 페널티로 다루고, 제약 충족 여부는 지표로 측정해 보고한다.** 제약 조건부 강화학습은 쓰지 않는다.
- **비교 모델은 13종 규모를 유지하되 처음부터 구현한다.** 파라미터화 행동 계열(P-DQN, MP-DQN, PA-DDPG 등)이 반드시 들어가야 하며, 연속 행동 전용 모델은 파라미터화 확장형으로 대체하고, 표 기반 기법은 이산화 방식을 명시한다.
