# Code Changelog


## [2026-05-08 22:14] L1-B-2 sim_engine.py generate_routes() patch
- 변경 함수: `generate_routes()` (sim/sim_engine.py)
- 변경 라인 (before → after):
  · `depart = rng.uniform(0, min(30, duration_s * 0.1))` → `depart = rng.uniform(0, max(30, duration_s * 0.7))`
  · `for i in range(n_vehicles):` → `for i in range(n_vehicles * 2):  # 2x stagger`
- 의도: 차량 출발이 [0, 30s]에 몰려 warmup(30s) 직후 모두 도달·소멸 → post-warmup 채널이 거의 비는 문제 해결.
  depart 분포를 [0, 0.7×duration]로 확장 + 2× stagger로 post-warmup 동시 차량 수 확보.
- 백업: `sim/sim_engine.py.bak_L1B2`
- 적용 시점: Experimenter[implement] 호출 (이번 세션). syntax 마커 검증 7/7 PASS.
- 다음: 사용자 직접 검증 (RUNBOOK 명령 6 → 명령 7).
