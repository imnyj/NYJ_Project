# 6단계. Contributions 정리

## 목적

제안 방안을 찾았으면 가장 먼저 그 모델이 왜 더 좋은지를 정리합니다. 이 정리가 논문의 main contribution 이 되고,
이후 성능 평가에서 어떤 그래프를 뽑을지와 서론을 어떻게 쓸지를 결정합니다.

## 들어가기 전 조건

- 5단계 완료 조건을 통과한 제안 방안이 있습니다.

## 참여 역할

idea(contribution 정리), coder(원인 분석 실험), critic(주장과 근거의 일치 검토), writer(서론 설계), visualizer(그래프 목록 작성), worker(파일 기록)

## 절차

1. 어떤 시도를 해 보았는지, 어떤 구조가 왜 좋은 성능을 내는지 원인을 분석합니다. 근거는 `idea/attempts.md` 와 결과 CSV 에서 가져옵니다.
2. 아래 다섯 파일을 만듭니다.
   - (1) `contributions.md`: Contributions 를 모두 정리합니다. idea 가 정리한 보고서를 worker 가 `contributions.md` 와 `idea/idea.md` 에 기록해 main contribution 으로 설정합니다.
   - (2) `performance_metrics.md`: 각 contribution 을 보여 줄 성능 지표를 정리합니다(4단계 파일을 갱신).
   - (3) `intro.md`: contribution 과 연결되도록 서론을 설계합니다. 8단계 파일 Introduction 절의 여섯 요소(배경 및 동기, 기존 해결책, 고도화된 해결책과 한계점,
     제안 방안, 주요 기여도, 논문 구성)를 3~4문단에 어떻게 배치할지와 문단별 인용 후보를 적습니다.
   - (4) `figure_list.md`: 제안 방안의 정당성을 보여 주기 위해 뽑아야 할 그래프와 표의 목록입니다. 그래프마다 보여 줄 주장, 데이터 출처, 형태(학습 곡선, 막대, 추이)를 적습니다.
     목록은 세 묶음으로 나눕니다. 첫째는 ML 공통 결과(State/Feature ablation, Reward/Loss ablation, Structure ablation, Sensitivity analysis, Learning curves,
     Hardware feasibility)입니다. 둘째는 Contributions 에 따른 결과로, contribution 마다 무엇 때문에 무엇이 좋아졌는지를 검증하는 결과입니다. 셋째는 연구 분야의 주요 결과로,
     X축에 사용자 밀도나 속도 같은 환경 변화 변수를 두고 Y축에 Delay, Traffic, AoI 같은 목표 성능이나 부가 성능을 둡니다. 묶음별 세부 내용은 7단계 파일의 "성능 결과 구성" 절을 봅니다.
   - (5) `comparative_methods.md`: 비교 방안 목록을 다시 확인해 정리합니다.

   idea 와 critic 은 쓰기 도구가 없으므로 두 역할이 낸 내용은 worker 가 파일로 기록합니다. `intro.md` 는 writer 가, `figure_list.md` 는 visualizer 가 씁니다.
3. **[사용자 결정]** Contributions 를 확정합니다.
4. **[사용자 결정]** 성능 평가 그래프의 흐름과 개수가 적당한지 사용자 판단을 받습니다. 원문에서도 이 부분은 사용자의 판단이 필요하다고 명시했습니다.
5. **[사용자 결정]** 서론 설계를 확인받습니다. 사용자는 서론만큼은 문장 단위로 어떤 내용을 어떤 순서로 넣을지 직접 설계하는 편을 선호하므로, 초안 설계를 보여 주고 사용자가 고칠 여지를 둡니다.

## 산출물

- `contributions.md`, `performance_metrics.md`, `intro.md`, `figure_list.md`, `comparative_methods.md`

## 완료 조건

- 사용자가 Contributions, 그래프 목록, 서론 설계를 승인했고, 그 기록이 `WALKTHROUGH_STATE.md` 에 있습니다.

## 사용자 명령 예시

> /goal (1) Contributions 를 모두 정리하여 파일로 관리하기. (2) Contributions 를 나타내기 위한 성능 지표 정리하여 파일로 관리.
> (3) Contributions 에 연결성이 있도록 서론에 대한 설계를 intro.md 로 관리. (4) 제안 방안의 정당성을 위해 뽑아야 하는 그래프 목록을 정리하여 파일로 관리.
> (5) 비교 방안 목록을 확인하여 정리.
