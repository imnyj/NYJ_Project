# Error Patterns



## 패턴: 장시간 시뮬레이션 batch-write 침묵
- 빈도: 1회 (Round 4)
- 증상: 사용자가 “데이터 폴더 비어 있음” 으로 시뮬 죽었다고 오해.
- 원인: run_scenario.py 가 시나리오 끝에서만 CSV 저장. 첫 파일 생성까지 수일 걸림.
- 예방법: 장시간 스크립트는 반드시
  (1) per-run incremental write + fsync,
  (2) line-buffered 또는 flush=True print,
  (3) resume on restart,
  (4) ETA 표시.

## 패턴: `python` vs `python3` 환경 차이
- 빈도: 1회 (Round 4)
- 증상: `Command 'python' not found, did you mean: command 'python3'`
- 원인: Ubuntu 22.04+ 기본 환경에 `python` 심볼릭 링크 없음.
- 예방법: 사용자에게 보내는 모든 셸 명령은 `python3` 사용.

## 패턴: ILP solver 호출 폭증
- 빈도: 1회 (Round 4 RILP)
- 증상: 한 run 이 수십 분~수 시간.
- 원인: 단일 cardinality constraint + 비음수 weight 인 knapsack 에 PuLP/CBC 호출.
  → 정렬 closed-form 과 결과 동일하나 solver overhead 만 추가됨.
- 예방법: ILP 작성 전 “이 문제는 정렬/그리디로 풀리는가?” 자문.
  Submodular maximization with cardinality constraint → 정렬.
  Multi-knapsack / capacity 다중 제약 → 진짜 ILP 필요.
