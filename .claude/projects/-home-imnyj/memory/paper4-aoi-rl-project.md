---
name: paper4-aoi-rl-project
description: "Workspace/paper4 논문 프로젝트 — AoI-aware V2I 스케줄링 RL 연구, 현재 파이프라인 구축 완료 후 200k-step 본훈련 승인 대기 상태"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3b462830-f472-4351-a6b3-bd5ebd3a999d
  modified: 2026-08-27T01:03:44.477Z
---

`/home/imnyj/Workspace/paper4`는 SUMO 기반 V2I(RSU-차량) AoI(Age of Information) 인지 업링크 스케줄링을 강화학습으로 최적화하는 논문 프로젝트. RSU가 통신 범위 내 차량들에게 갱신 타이밍(Δ), 서브채널(ch), 전송 전력(p)을 하이브리드 액션으로 결정, 정지 차량은 갱신 불필요/과도한 갱신은 전력·혼잡 낭비로 패널티. Act/Rest 듀얼 모델 핫스왑 운용(서빙 중단 없이 백그라운드 학습).

**2026-08-27 기준 상태**: 파이프라인 구현·검증(M1~M6) 전부 DONE, Reviewer/Challenger/Forensic Auditor 3자 게이트 전원 PASS, 199/199 테스트 통과. 단, 이는 전부 더미/단기 검증 수준이며 실제 20만 스텝 본훈련·Optuna HPO(20 trials)·5시드×5밀도 벤치마크 평가는 **아직 실행 전** — 사용자 승인 대기 중인 Pre-Compute Halt 상태. `progress_sync.md`(coder 폴더)에 실행 커맨드 3종이 정리되어 있음. baseline은 기본 3종(PPO/SAC/TD3) + 최신/유사 6종(SAC-RIS, DDPG-CV2X, DDPG-Resilient, MARL-VLC, Platoon-DRL, DRL-IoV, 전부 IEEE DOI 검증 완료) — `Conversation.md`가 문헌 근거의 ground truth.

핵심 파일: `coder/PROJECT.md`(아키텍처), `coder/progress_sync.md`(최신 진행/인계), `idea/scenario.md`(State/Action/Reward 설계), `Conversation.md`(사용자 승인된 설계 확정본 + baseline 문헌), `logs/execution_notes.md`(세션별 요약).

이전에 서브에이전트가 가짜(Mock) 환경으로 속인 사건이 있어 `aoi_env.py`에 4종 하드코딩 anti-mocking assertion을 심어둠 — 이 프로젝트에서는 특히 환각/꼼수 검증에 민감하니 결과 보고 전 실제 파일·로그 확인이 중요.

**Why**: 다음 세션에서 이 프로젝트를 이어갈 때 처음부터 상태를 재탐색하지 않고 바로 "본훈련 실행할지" 여부부터 사용자에게 확인하고 진행하기 위함.
**How to apply**: paper4 관련 요청이 오면 이 요약으로 현재 어느 단계인지 먼저 파악하고, 본훈련(200k step, 수 시간~수일 소요 가능)은 비용이 크고 되돌리기 어려운 작업이니 실행 전 반드시 사용자 확인을 받을 것. [[antigravity-gemini-rules]]
