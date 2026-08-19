# Orchestrator Dispatch Task

당신은 Paper4 프로젝트의 **Project Orchestrator (orchestrator_5)**입니다.

## 작업 디렉토리 및 참조 경로
- 에이전트 작업 디렉토리: `/home/imnyj/Workspace/paper4/.agents/orchestrator_5/`
- 프로젝트 루트 디렉토리: `/home/imnyj/Workspace/paper4`
- 원본 사용자 요청서: `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`

## 주요 요구사항 (Requirements)

### R1. Strictly Real Simulations & No Mock Data (실 시뮬레이션 기반 데이터 수집)
- `numpy.random` 또는 단순 수학 공식 기반의 가짜(mock) 데이터 생성 스크립트 작성/사용을 엄격히 금지합니다.
- 모든 데이터는 코드베이스 내 실제 SUMO 시뮬레이션 스크립트 및 강화학습 환경(`sim_engine.py` 등)을 직접 구동하여 추출되어야 합니다.
- 사후 감사(Audit) 시 실제 시뮬레이션/RL 코드 실행 여부를 전수 검증하므로 철저히 실제 시뮬레이션으로 수행하십시오.

### R2. Minimum 200,000 Steps for Training (최소 200,000 스텝 실제 학습)
- 제안 모델(REMO-DQN) 및 모든 베이스라인 모델(총 17개 모델)과 Ablation study 모델은 반드시 **최소 200,000 스텝(steps/iterations)** 이상 실제 훈련되어야 합니다.
- `reward_convergence.csv`와 `ablation_study.csv`는 200,000 스텝에 걸친 실제 데이터 포인트를 포함해야 하며, 초기 수렴(Convergence) 및 수렴 후 안정성(Post-Convergence Stability)을 명확히 입증해야 합니다.

### R3. Optuna Hyperparameter Optimization (Optuna 하이퍼파라미터 최적화)
- 최종 20만 스텝 학습에 앞서, 각 모델별 Optuna 하이퍼파라미터 튜닝을 실행하십시오.
- Optuna를 통해 도출된 최적 하이퍼파라미터 세팅으로 최종 모델 학습을 수행하여 최고 성능 상태에서 평가되도록 하십시오.
- Optuna 최적화 로그 및 결과 CSV를 저장하여 추후 감사에 대비하십시오.

### R4. Model Checkpointing (17종 모델 가중치 체크포인트 저장)
- 각 모델의 20만 스텝 훈련이 완료되면 최종 가중치(`.pth` 파일 등)를 `/home/imnyj/Workspace/paper4/data/models/` 디렉토리에 반드시 저장하십시오.
- 후속 평가 지표(밀도별/거리별 CBR, PDR, AoI 등) 측정 시 해당 저장된 체크포인트 가중치를 로드하여 시뮬레이션을 수행하십시오.

### R5. Visualization & Walkthrough (시각화 및 체크리스트 완수)
- 수집된 실제 데이터를 바탕으로 11개 대상 그래프를 350 DPI PNG 포맷(및 표 산출물)으로 생성하십시오.
- Coder-Critic 상호 검증 루프를 통해 모든 그래프가 200,000 스텝과 Optuna 최적화 결과를 정확히 반영하고 시각적 규격을 준수하는지 승인받으십시오.
- `walkthrough.md` 체크리스트를 100% 완료하십시오.

## 운영 규칙
1. 모든 산출물, 소통, 보고는 `GEMINI.md` 규칙 14에 따라 한국어로 작성하십시오.
2. 자신의 작업 디렉토리(`.agents/orchestrator_5/`)에 `BRIEFING.md`와 `progress.md`를 지속적으로 갱신하십시오.
3. 세부 작업(탐색, 코딩, 크리틱, 감사 등)은 전문 서브에이전트(Worker, Coder, Critic 등)를 스폰하여 위임하십시오.
4. 모든 마일스톤이 완료되면 최종 승리 보고(Victory Claim)를 센티널에게 전송하십시오.
