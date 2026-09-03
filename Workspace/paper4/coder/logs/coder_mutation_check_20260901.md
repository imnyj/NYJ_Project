# coder 회귀 테스트 변이 검사 — 2026-09-01

## 왜 했는가
NaN 가드 결함에 대해 내가 처음 작성한 동시성 테스트 2건이 **락을 제거해도 통과했다.**
GIL과 짧은 update 창 때문에 문제의 인터리빙이 사실상 샘플링되지 않았기 때문이다. 통과하지만
아무것도 증명하지 않는 테스트를 하나 실제로 만들었으므로, 나머지 회귀 테스트도 같은 상태가
아닌지 전수로 확인해야 했다.

**원칙: 결함을 되돌렸을 때 실제로 실패하는 것을 보이기 전까지, 회귀 테스트의 통과에는 의미가 없다.**

## 방법
두 가지를 병행했다. 어느 쪽도 **작업 트리를 수정하지 않는다** — 다른 두 에이전트가 동시에
전체 스위트를 돌리고 있어서, 파일을 잠깐이라도 되돌리면 그쪽에 가짜 실패가 보인다.

1. 런타임 몽키패치(같은 프로세스에서 결함 구현으로 교체 후 pytest 실행)
2. 몽키패치로 충실하게 되돌릴 수 없는 것(루프 내부에 인라인된 비교식 등)은 저장소를
   `scratchpad/mutrepo`로 복사해 **격리된 사본에서만** 소스를 고쳐 검사

## 결과 — 7건 전부 탐지

| 변이 (결함 재도입) | 대상 테스트 | 결과 |
|---|---|---|
| (대조군) 변이 없음 | `TestOpenIntervalsAreClosed` | passed (기대대로) |
| `finalize_open_intervals`를 no-op으로 | `TestOpenIntervalsAreClosed` | **FAILED** |
| `n_active`를 SUMO 지상진실로 복귀 | `TestNoGroundTruthInObservation` | **FAILED** |
| `decide_grant`가 `action_idx`를 버림 | `TestDiscreteActionIndexSurvives` | **FAILED** |
| 버퍼가 모델 gamma 대신 0.99 고정 | `TestGammaIsWired` | **FAILED** |
| 구간 종결 시각을 스텝 이후로 복귀 | `TestLedgerTimeAlignment` | **FAILED** |
| 스테일 체크포인트가 맨 RuntimeError | `TestStaleCheckpointsDegradeGracefully` | **FAILED** |
| `_best.pt` 선택을 구간당 평균으로 복귀 (격리 사본) | `TestCheckpointSelectionUsesTheRewardRate` | **FAILED** |

앞서 개별 확인한 2건도 같은 성질이다.
- 찢어진 스냅샷: 락 제거 시 `act_state_dict [2.0, 3.0]`, `rest_state_dict [31.0, 32.0]`
- NaN 가드: 락 제거 시 `the NaN guard passed on a clean model and the copy then carried
  weights that were poisoned after the check`

## 이 과정에서 메운 공백
**C2의 핵심 주장 — `_best.pt`를 무엇으로 고르는가 — 에 테스트가 아예 없었다.** 요약과 CSV에
두 지표가 있는지만 확인하고 있었고, 선택 기준이 구간당 평균으로 되돌아가도 아무 테스트도
실패하지 않았다. `TestCheckpointSelectionUsesTheRewardRate`를 신설해 `_best.pt`에 저장된
`best_reward`가 초당 비율의 최댓값과 일치하고 구간당 평균의 최댓값과는 **다른지** 단언한다.
두 지표가 그 실행에서 실제로 갈라지는지 확인하는 대조 단언을 함께 두어, 우연히 두 값이
같아져 단언이 공허해지는 경우를 막는다.

## 대조군의 필요성
"결함을 넣으니 값이 변했다"만으로는 부족하고, "결함이 없으면 값이 정확히 같다"가 함께
성립해야 관측된 차이가 신호임이 증명된다. 위 표의 대조군 행과, C2 테스트의
"두 지표가 실제로 갈라진다" 단언이 그 역할이다.
