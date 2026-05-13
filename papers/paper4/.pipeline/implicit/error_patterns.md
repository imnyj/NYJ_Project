# Error Patterns



## 패턴: sed pattern quote-mismatch
- 빈도: 1회 발견 (2026-05-08 L1-B-1)
- 증상: sed -i 명령이 silent하게 0건 매치 → 파일 변경 없음 → 후속 검증에서 "패치가 적용됐는데 효과가 없다"는 오해
- 원인: RUNBOOK에 적힌 sed 패턴의 따옴표 종류가 실제 파일과 다름 (작은따옴표 vs 큰따옴표)
- 예방법:
  1. sed 패턴을 만들기 전 반드시 file_read로 해당 라인의 실제 따옴표를 확인
  2. RUNBOOK의 명령 B 같은 in-place 수정 명령 전에는 항상 명령 A(grep/sed -n preview)로 매치 미리보기 강제
  3. 명령 B 직후 `diff` 출력이 비어있으면 (= no change) 즉시 alert
