# Experimenter Memory

## Stage 2 — GPU/Speed Refactor & Checkpoint/Resume 기능 (2026-04-17)

### 배경
사용자 PC에서 500 ep 학습에 약 3개월 소요 추산 → GPU 워크스테이션으로 이전.
핵심 병목: (1) _update_torch의 256번 단일 forward, (2) GPU 미사용, (3) 체크포인트 약함.

### 수정한 파일 목록
1. `simulation/agents/mafac_agent.py`
   - device 파라미터 추가, actor/critic/critic_target .to(self.device)
   - _update_torch 전면 재작성: 256x single forward → 1x batch forward (Categorical)
   - advantage 계산: Q(s,a_sampled) - Q(s,a_old) baseline 재사용 (critic 2x/sub-action → 각 1x)
   - _onehot_actions_torch(): GPU scatter_ 직접 인코딩
   - save_lightweight_checkpoint / save_full_checkpoint / load_full_checkpoint 추가
   - ReplayBuffer.state_dict() / load_state_dict() 추가

2. `simulation/training/trainer.py`
   - device, resume_from 파라미터 추가
   - make_agent()에 device 전달
   - 체크포인트 정책: 매 ep lightweight(latest/), 매 10 ep full(ep{N}_full/)
   - trainer_state.json 매 ep 갱신 (episode, federated.round_count, reward_history)
   - _resume_from_checkpoint(): state JSON + latest/*.pt 로드
   - _save_checkpoints(): silent pass → 명시적 print/logger.warning

3. `simulation/run_full_simulation.py`
   - --resume 플래그 추가
   - --device 모든 phase 함수에 전달
   - Phase 0: GPU info (name, VRAM) 출력
   - 헤더 docstring: 워크스테이션 실행 가이드 추가

4. `simulation/env/sumo_env.py` (선택)
   - MockSUMO 블록에 주석: "fallback, 워크스테이션=libsumo 직접 사용"

### 예상 속도 개선
- next_action batch forward: ~256배 (이론), 실제 GPU 환경 50~100배 이상 기대
- CPU→GPU 전체 이전: 에피소드당 추가 10~30% 단축 예상
- 합산 목표: 3개월 → 수 일 이내 (GPU 워크스테이션 기준)

### 워크스테이션 실행 명령어
```bash
# 처음 실행
python3 run_full_simulation.py --phases 2 --device cuda --p2-episodes 500

# 백그라운드 실행
nohup python3 run_full_simulation.py --phases 2 --device cuda --p2-episodes 500 > simulation_log.txt 2>&1 &

# 중단 후 재개
python3 run_full_simulation.py --phases 2 --device cuda --p2-episodes 500 --resume
```

### GPU 메모리 부족 시 조절 파라미터
- batch_size: 256 → 128 (MAFACAgent 생성 시 변경)
- num_vehicles: 50 → 30 (env_config 직접 수정)
- buffer_size: 100000 → 50000 (MAFACAgent)
