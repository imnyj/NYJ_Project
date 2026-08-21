## 2026-08-20T09:04:57Z
[역할 및 작업 지시]
당신은 Paper4 (REMO-DQN) 코드 수정 프로젝트의 Coder Worker입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_h5/
프로젝트 루트: /home/imnyj/Workspace/paper4
참조 파일:
- /home/imnyj/Workspace/paper4/ORIGINAL_REQUEST.md
- /home/imnyj/Workspace/paper4/paper4_code_review_report.md
- /home/imnyj/Workspace/paper4/idea/paper4_code_fix_tasklist.md
- /home/imnyj/Workspace/paper4/.rules/coder.md
- /home/imnyj/GEMINI.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor/critic will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행할 단일 작업: H-5 5단계 점진적 Ablation 체인 구축 및 action_dim=24 정합]
순차 실행 원칙에 따라, H-4 완료에 이어 **H-5** 항목만 수정하고 독립 검증한 뒤 기록합니다.

1. **5단계 단일 요소 점진적 Ablation 아키텍처 확립**:
   각 단계가 직전 단계에서 **정확히 1개의 구성 요소만 추가**되도록 에이전트 클래스 및 타깃 계산 로직을 정합합니다:
   - **Stage 1 (`VanillaDQN`, `DQNAgent` in `code/dqn_agent.py`)**:
     * 순수 MLP (단일 출력 헤드, Dueling 아님, MoE 아님, Residual 아님)
     * Single DQN 타깃 업데이트: $y = r + \gamma \max_{a'} Q_{\text{target}}(s', a')$
     * 기본 `action_dim=24`, `vanilla_dqn.pth`
   - **Stage 2 (`DoubleDQN`, `DDQNAgent` in `code/ddqn_agent.py`)**:
     * Stage 1 + **Double DQN 타깃 업데이트**: $y = r + \gamma Q_{\text{target}}(s', \arg\max_{a'} Q_{\text{online}}(s', a'))$
     * 기본 `action_dim=24`, `ddqn.pth`
   - **Stage 3 (`DuelingDQN`, `DuelingDQNAgent` in `code/dueling_dqn_agent.py`)**:
     * Stage 2 + **Dueling 아키텍처**: Value Stream $V(s)$ (1차원) + Advantage Stream $A(s, a)$ (24차원) 분리 결합
     * 기본 `action_dim=24`, `dueling_dqn.pth`
   - **Stage 4 (`MoEDQN`, `MoEAgent` in `code/moe_agent.py`)**:
     * Stage 3 + **Mixture of Experts**: Gating Network + 2개 Expert Networks
     * 기본 `action_dim=24`, `moe_dqn.pth`
   - **Stage 5 (`ResNetMoEDQN`, `ResNetMoEAgent` in `code/resnet_moe_agent.py`)**:
     * Stage 4 + **Residual Block 결합**: Feature Extractor 내 Residual Skip Connections + 3개 Expert Networks (제안 REMO-DQN)
     * 기본 `action_dim=24`, `resnet_moe_dqn.pth`

2. **학습 스크립트 및 라벨/파일명 정합**:
   - `code/train_dqn.py`: `VanillaDQN` 학습 (`vanilla_dqn.pth`)
   - `code/train_ddqn.py`: `DoubleDQN` 학습 (`ddqn.pth`)
   - `code/train_dueling_dqn.py` (신설/정합): `DuelingDQN` 학습 (`dueling_dqn.pth`)
   - `code/train_moe.py`: `MoEDQN` 학습 (`moe_dqn.pth`)
   - `code/train_resnet.py`: `ResNetMoEDQN` 학습 (`resnet_moe_dqn.pth`)
   - `code/ablation_agents.py`: 위 5종 클래스를 한곳에서 import/export 가능하도록 정합.
   - `code/ai_dcc_hook.py` 및 `code/sensitivity_runner.py`의 hook 매핑 및 `DRL_SETUP`이 5종 모델과 완벽 호환되도록 유지.

3. **독립 검증 스크립트 작성 및 실행 (`code/test_h5_ablation.py`)**:
   - 5개 에이전트에 대해:
     * 아키텍처 요소 검증 (Single/Double 타깃 로직, Dueling 스트림 유무, Gating/Expert 유무, ResNet 블록 유무)
     * 모든 에이전트의 기본 `action_dim == 24` 검증
     * `select_action(state)`, `store_transition(...)`, `train_step()`, `save()`, `load()`가 오류 없이 100% 정상 작동하는지 검증
   - `python3 code/test_h5_ablation.py`를 실행하여 100% 통과(Exit Code 0)함을 입증합니다.

4. **마스터 작업 목록 갱신 (`idea/paper4_code_fix_tasklist.md`)**:
   - H-5 항목의 상태를 [x] 완료로 변경하고 5단계 Ablation 정의표, 수정 파일 목록, 독립 검증 결과를 상세히 기록합니다.

5. **핸드오프 보고서 작성 및 완료 알림**:
   - `/home/imnyj/Workspace/paper4/.agents/worker_h5/handoff.md`에 결과를 기록하고 오케스트레이터에게 `send_message`로 완료를 보고하세요.
