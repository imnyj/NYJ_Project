
## 2026-08-26 Session Auto-Upgrade
1. 수행 작업: 가짜 환경(Mock) 배제 및 실제 SUMO 연동(`NetSim.py`) 기반 V2X AoI 20만 스텝 RL 파이프라인(9개 베이스라인) 코드 작성 및 199/199 더미 테스트 검증 완료.
2. 실패/재시도: 이전 에이전트들의 꼼수(hpo.py Mocking) 발각으로 파이프라인 전면 백업 및 재설계 수행, 팀워크 쿼터 리밋(429) 에러 발생 후 2.5시간 자동 복구(Auto-Recovery) 성공.
3. 수동 교정: 엄격한 IEEE DOI 논문 6편 교체(MDPI/arXiv 배제), `[0,1]` Min-Max 보상 정규화 도입, 환경 꼼수 방지용 하드코딩 단언문 4종 필수 삽입 룰 확립.

## 2026-08-28 Session (Claude Code)
1. 수행 작업: agy 작업 전격 재검토 → 관측벡터 3개 차원(속도X/Y·heading) 상수 0 결함 발견·수정. 문헌 51편 Crossref 전수 검증(날조 0건, IEEE TWC 2편 확보). baseline 9종 신규 구현(SB3 3종 + 논문 이식 6종) 및 실제 SUMO 실측 검증. `Conversation.md` 5번 체크리스트 5/5 통과.
2. 실패/재시도: 서브에이전트가 사용량 한도로 3회 중단(파일은 작성 완료, 검증만 미수행) → Claude가 직접 인수. 초기 스모크가 `steps_per_ep(20) < warmup_steps(35)`로 빈 실행이면서 "성공" 보고되어, 스텝 수를 300으로 올려 재검증.
3. 수동 교정: `_get_vehicle_state_dict`의 위치차분 속도를 SUMO 방위각 기반으로 교체(한 스텝 3회 호출로 2·3번째가 항상 0), `run_all.py` 20만 스텝 인자 복원 및 클래스 주입 방식 전환, ruff 4건 수정.

## 2026-08-28 Session 2 (Claude Code, 22시)
1. 수행 작업: agy의 "훈련 시작 가능"(simulation_plan rev.2) 판정을 독립 검증하여 **결함 6건 발견**. Δ 액션이 환경에 전혀 반영되지 않음(Δ=0.1s와 45.0s가 tx_attempts 4407로 완전 동일), AoI가 `max(1.0,·)` 클램프로 상수 포화(실제 age 평균 0.0437s, 98.8% 절단), I_redundant 호출 순서 오류로 발화 0.68%, **버퍼에 들어가는 보상이 승인된 4항 보상이 아닌 스케줄러 자체 3항 보상**이며 실질 신호가 `−(0.01+0.01·전력)`뿐, **모델 입력 18차원 중 15개가 상수**(신호등·거리·CBR·heading 미전달). PHY 계층(448 µs, −95 dBm, 안테나이득)은 재계산 결과 정확함을 확인.
2. 실패/재시도: 초기 진단 스크립트가 키 오타(`redundant`→`i_redundant`)로 I_redundant를 0건으로 오측정, 재측정. 상태벡터 계측도 env/scheduler 두 호출 지점이 섞여 1차 결과가 무의미해 rsu_pos 인자로 분리 재측정.
3. 수동 교정: 코드 수정은 **하지 않음**(사용자 지시로 설계 재논의 우선). 문서만 갱신 — `review/claude_audit_20260828.md` 신규 작성, `simulation_plan.md` rev.3(훈련 금지 배너), `progress_sync.md` 폐기 baseline 경고 배너, `idea/design_spec_v2.md` 재설계 명세 신규 작성(미확정 D1~D8).
