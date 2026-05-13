# User Preferences



## [2026-05-08 23:04] 패턴: 복합 메트릭의 OR-of-strong 평가
- 관찰: 사용자가 ABC-B 결과(runtime=1.5/cam=13885/CBR=0.38/AoI=323.25)를 받았을 때,
  Commander가 정의한 "정상 임계 4종 모두 충족"(runtime≥5 포함) 정의에 미달함에도
  나머지 3개 메트릭이 강하게 정상이라는 이유로 즉시 PASS 판단하고 다음 단계 자발 진행.
- 학습한 사용자 선호:
  · 임계값 4개 중 1개만 약간 어긋나도 다른 메트릭이 OOM(order of magnitude) 강세면 PASS
  · runtime은 HW 의존이라 신뢰도가 낮은 신호로 취급
  · 대신 substantive 메트릭(cam events, CBR, AoI 양수성)에 가중치 큼
- 향후 적용:
  · 정상 신호를 정의할 때 "필수(must)"와 "참고(advisory)"로 구분 권장
  · runtime, wall-clock 류는 advisory로
  · n_events, CBR, AoI 류 시뮬 동역학 메트릭은 must로
  · 사용자에게 결과 평가를 보고할 때 must/advisory 구분 표기


## [2026-05-13 08:41] 패턴: 옵션 알파벳 매김
- 관찰: 사용자가 19:18 Commander 옵션 제시("E4 / E1 / E2 / proofreader / highway+density")를
  받은 뒤 "C로 진행"이라고 답함.
- Commander가 별도로 A/B/C 라벨을 붙이지 않았는데도 사용자는 머릿속에서 등장 순서대로 매김:
    A=E4, B=E1, C=E2(?) or proofreader(?), D=...
- 실제 의도는 "논문 작업"이라는 한정사가 붙어 있어 C=proofreader로 확정됨.
- 학습된 사용자 선호:
  · Commander가 옵션을 N개 나열하면 사용자는 자동으로 A/B/C...로 매김.
  · 매김 순서는 Commander가 제시한 순서 그대로.
  · 모호함 회피를 위해 옵션 제시 시 명시적으로 "(A) (B) (C)" prefix를 붙이는 편이 안전.
- 향후 적용:
  · 옵션 제시 표/리스트에 "(A) E4 / (B) E1 / (C) E2 / (D) proofreader / (E) highway" 처럼 라벨링.
  · 사용자가 단답 "C"로 회신하면 즉시 매칭 가능.
