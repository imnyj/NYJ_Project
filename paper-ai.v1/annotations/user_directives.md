# User Directives Log

## [2026-04-28 21:04] 방향 전환 지시 — ILP 기반 최적화로 복귀

**지시자**: Youngju Nam
**수신 에이전트**: Idea Agent
**날짜**: 2026-04-28 21:04

### 핵심 지시 내용
1. AI/ML(강화학습, 지도학습) 기반 후속 연구 방향 중단
2. 기존 ILP(Integer Linear Programming) 기반 최적화 정체성으로 복귀
3. 기존 FA 논문 라인(Precaching / CIoV / Vehicular Cloud / RSU 협력)의 연속선상에서 후속 연구 설계
4. libsumo 시뮬레이션 가능 규모 유지 (차량 50~300대, RSU 3~10개)
5. idea_spec.md는 사용자가 후보 선택 후 다음 세션에서 작성

### 이전 후보 폐기 이유
- 기존 brain/idea_memory.md 섹션 10의 3개 후보(MARL, UAV-RL, Digital Twin)는 AI/ML 색채 과다
- Nam2026의 SAC는 일회성 시도였을 뿐, 연구자의 본 정체성이 아님
- 연구자의 본 정체성: ILP 기반 최적화 문제 정식화

### 처리 결과
- ILP 기반 후보 3개 도출 완료 (brain/idea_memory.md에 새 섹션 추가)
- pipeline_state.json idea.status = "running", note 업데이트 완료
- 사용자 선택 대기 중

### 금지사항 (명시적 지시)
- 강화학습/지도학습/딥러닝 기반 후보 도출 금지
- 새로운 외부 검색 금지
- idea_spec.md 작성 금지 (선택 후 작성)


## [2026-05-06 13:16] 모호한 KEY/비밀번호 처리 요청 — 명확화 필요

**지시자**: 사용자
**원문**: "복호화된 KEY를 받아서 쓸 수 있게 수정이 필요하겠네 비밀번호를 변수로 저장해두어서 써도 되고 말이야. 어쨌든 수정이 필요해."

### 해석 후보
1. (A) 한 번 복호화된 API KEY를 동일 프로세스 내에서 재사용 — 이미 `core.unlock.is_unlocked()`로 구현되어 있음
2. (B) Vault 마스터 비밀번호를 환경변수/캐시 파일에 저장하여 commander 재시작 시 prompt 회피
3. (C) 외부에서 (예: watchdog, 다른 셸) 복호화된 평문 KEY를 환경변수로 받아 vault 우회
4. (D) 비밀번호 자체를 코드에 하드코딩 — 보안 위험 매우 큼

### 보안 고려 사항
- (B)/(C)/(D)는 vault 시스템(.env.salt, ENC: 항목)의 의도(평문 비밀번호 노출 차단)를 약화시킴
- 디스크 평문 저장 또는 환경변수 평문은 다른 프로세스/로그 노출 위험
- 현재 watchdog stdin 프로토콜(PAPER_AI_UNLOCK_FROM_STDIN=1)은 이미 watchdog → commander 사이의 안전한 비밀번호 전달을 처리

### 처리 결과
- 자체 업그레이드는 **보류** — 사용자에게 정확한 의도와 위험 감수 여부 확인 후 진행
- stage_upgrade 호출하지 않음
