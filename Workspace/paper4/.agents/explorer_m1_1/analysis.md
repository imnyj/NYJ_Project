# Checkpoint Resume & Model Training 정밀 분석 보고서 (M1-Explorer 1)

## 1. 개요 (Executive Summary)
본 분석은 V2X 멀티프로세싱 모델 훈련 스크립트인 `/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py` 내의 `train_worker` 함수 및 관련 제어 로직을 대상으로 수행되었습니다. 
현재 구현체는 중단된 훈련(에피소드 52 부근)을 이어서 수행하지 못하고 기존 로그를 덮어씌우거나 intermediate 가중치(`.pth`/`.pkl`)를 저장하지 못하는 구조적 결함을 가지고 있습니다.
본 보고서는 Worker 에이전트가 소스 코드를 수정할 때 즉시 적용할 수 있도록 정확한 코드 라인 번호와 변경 사양(Before / After 코드 패치)을 제시합니다.

---

## 2. 분석 대상 및 현황 (Current Status)

- **대상 파일**: `/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py`
- **핵심 함수**: `train_worker(args)` (Lines 118 – 195)
- **현재 훈련 상태 (`data/models/`)**:
  - `QLearning_convergence.csv`: 63 에피소드 저장됨 (마지막 에피소드 63, Global Step 126,000)
  - `SARSA_convergence.csv`: 63 에피소드 저장됨 (마지막 에피소드 63, Global Step 126,000)
  - `VanillaDQN_convergence.csv`: 50 에피소드 저장됨 (마지막 에피소드 50, Global Step 100,000)
  - `ActorCritic_convergence.csv`: 34 에피소드 저장됨 (마지막 에피소드 34, Global Step 68,000)
  - 기타 10개 모델: 아직 훈련 시작 안 됨 또는 로그 미생성
  - `.pth`/`.pkl` 가중치 파일: 0개 (중간 저장 로직 부재로 인해 프로세스 종료 시 모두 유실됨)

---

## 3. 현행 코드 결함 정밀 분석 (Detailed Defect Analysis)

### [결함 1] 잘못된 훈련 완료 체크 및 건너뛰기 조건 (Lines 130–135)
```python
130: if os.path.exists(model_path) and os.path.exists(log_path):
131:     with open(log_path, 'r') as f:
132:         lines = f.readlines()
133:         if len(lines) > 95: # Close enough to 100
134:             print(f"[{name}] Already trained. Skipping...")
135:             return name
```
- **문제점**:
  1. `model_path`와 `log_path`가 **둘 다 존재**해야만 체크합니다. 현재 intermediate 가중치 저장이 이루어지지 않아 `model_path`가 존재하지 않으므로, `log_path`에 63 에피소드가 남아있어도 이 조건문이 무시되고 훈련 재개가 불가능해집니다.
  2. 훈련 중단 시 기존 progress를 읽어 `start_ep`를 계산하는 로직이 완전히 누락되어 있습니다.

### [결함 2] 기존 CSV 로그 파괴 (Line 144)
```python
144: with open(log_path, 'w', newline='') as f:
145:     writer = csv.writer(f)
146:     writer.writerow(['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean'])
```
- **문제점**:
  - `log_path`를 무조건 `'w'` (write/overwrite) 모드로 열어 기존 훈련 수렴 로그(QLearning 63ep, SARSA 63ep 등)를 전량 삭제하고 Episode 1부터 새로 작성합니다.

### [결함 3] 에피소드 루프 시작점 고정 (Line 148–149)
```python
148: global_step = 0
149: for ep in range(TOTAL_EPISODES):
```
- **문제점**:
  - `start_ep` 계산 없이 항상 `ep = 0`부터 시작하며 `global_step`도 0으로 초기화됩니다. 이로 인해 이어서 학습하는 range(`range(start_ep, TOTAL_EPISODES)`) 처리가 되지 않습니다.

### [결함 4] Intermediate 가중치 미저장 (Line 186)
```python
149: for ep in range(TOTAL_EPISODES):
...
186:     agent.save(model_path)
```
- **문제점**:
  - `agent.save(model_path)`가 100 에피소드가 모두 완료된 루프 바깥(Line 186)에만 존재합니다. 훈련 과정 중 에피소드 단위 또는 주기적 가중치 저장이 전혀 이루어지지 않아, 훈련 도중 중단되면 모델 가중치가 완전히 분실됩니다.

---

## 4. 변경 사양 및 상세 수정 가이드 (Detailed Change Specifications)

Worker 에이전트가 `/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py` 수정 시 반영해야 할 사양입니다.

### 4.1 `start_ep` 계산 및 재개 로직 구축
1. `log_path`가 존재하고 파일 내용이 존재할 경우:
   - CSV 헤더 행을 제외한 데이터 행 개수 또는 마지막 행의 `Episode` 번호를 읽어 `start_ep`로 설정합니다.
   - 예: `lines[-1].split(',')[0]`이 `63`이면 `start_ep = 63`.
2. 만약 `start_ep >= TOTAL_EPISODES` (100)이면 훈련 이미 완료된 것으로 판단하여 `return name`.

### 4.2 기존 가중치 및 에이전트 상태 로드 (Load Checkpoint)
1. `model_path`가 존재하는 경우 `agent.load(model_path)`를 호출하여 이전 가중치를 계승합니다.
2. `model_path`가 존재하지 않지만 `start_ep > 0`인 경우:
   - 에이전트의 epsilon decay 속성이 존재한다면 `agent.epsilon = max(min_eps, agent.epsilon * (agent.epsilon_decay ** start_ep))`로 엡실론 값을 재개 지점에 맞게 조정합니다.

### 4.3 CSV 헤더 작성 조건화 (`'w'` vs `'a'`)
1. `start_ep == 0` 이거나 `log_path`가 없는 경우에만 `'w'` 모드로 헤더를 새로 작성합니다.
2. `start_ep > 0`인 경우 기존 CSV 파일 내용을 보존합니다.

### 4.4 Global Step 및 훈련 루프 재개
1. `global_step = start_ep * STEPS_PER_EP` 로 설정합니다.
2. `for ep in range(start_ep, TOTAL_EPISODES):` 로 루프 범위를 지정합니다.

### 4.5 Intermediate Weight Saving (매 에피소드 가중치 저장)
1. 훈련 루프 내부 (에피소드 종료 및 CSV append 직후)에 `agent.save(model_path)`를 매 에피소드 호출하여 중단 시에도 최신 가중치를 보존하도록 조치합니다.

---

## 5. Worker 에이전트용 코드 변경 사양 (Exact Code Replacement Specs)

### Target File
`/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py`

### Target Range
Lines 128 – 188 (Total 61 lines)

### Code Replacement Details

#### [Existing Code: Lines 128 – 188]
```python
    # We will ALWAYS retrain if requested, but let's check if it exists just to be safe
    # If it's already fully trained, skip. We know it's fully trained if log has 100 episodes
    if os.path.exists(model_path) and os.path.exists(log_path):
        with open(log_path, 'r') as f:
            lines = f.readlines()
            if len(lines) > 95: # Close enough to 100
                print(f"[{name}] Already trained. Skipping...")
                return name
                
    try:
        print(f"--- Training {name} on GPU {gpu_id} ---")
        agent = create_agent(name)
        hook = get_hook(hook_name)
        hook.set_agent(agent)
        hook.is_training = True
        
        with open(log_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean'])
            
        global_step = 0
        for ep in range(TOTAL_EPISODES):
            hook.reset_episode()
            runner = SimulationRunner(
                scenario="urban_grid",
                n_vehicles=50,
                seed=42 + ep,
                method=hook_name,
                method_params={},
                duration_steps=STEPS_PER_EP
            )
            metrics = runner.run()
            global_step += STEPS_PER_EP
            
            if hasattr(agent, 'memory'):
                batch_size = getattr(agent, 'batch_size', 64)
                num_updates = max(1, len(agent.memory) // batch_size)
                for _ in range(num_updates):
                    if hasattr(agent, 'train_step'):
                        agent.train_step()
                    if hasattr(agent, 'update_epsilon'):
                        agent.update_epsilon()
            
            if hasattr(agent, 'update_target_network'):
                agent.update_target_network()
                
            ep_reward = hook.episode_reward
            aoi = metrics.get('AoI_mean', 0.0)
            cbr = metrics.get('CBR_mean', 0.0)
            pdr = metrics.get('PDR_mean', 0.0)
            
            with open(log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([ep+1, global_step, ep_reward, aoi, cbr, pdr])
            
            if (ep + 1) % 10 == 0:
                print(f"[{name}] Ep {ep+1}/{TOTAL_EPISODES} - Reward: {ep_reward:.2f}")
            
        agent.save(model_path)
```

#### [Replacement Code]
```python
    # Check existing progress to compute start_ep
    start_ep = 0
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if len(lines) > 1: # Header line exists + at least 1 episode row
                try:
                    last_ep = int(lines[-1].split(',')[0])
                    start_ep = last_ep
                except (ValueError, IndexError):
                    start_ep = len(lines) - 1

    if start_ep >= TOTAL_EPISODES:
        print(f"[{name}] Already completed ({start_ep}/{TOTAL_EPISODES} episodes). Skipping...")
        return name

    try:
        print(f"--- Training {name} starting from Episode {start_ep+1}/{TOTAL_EPISODES} on GPU {gpu_id} ---")
        agent = create_agent(name)
        
        # Load existing weights if available
        if os.path.exists(model_path):
            try:
                agent.load(model_path)
                print(f"[{name}] Loaded existing checkpoint from {model_path}")
            except Exception as e:
                print(f"[{name}] Warning: Could not load checkpoint from {model_path}: {e}")
        elif start_ep > 0:
            # Adjust decay state if model checkpoint missing
            if hasattr(agent, 'epsilon') and hasattr(agent, 'epsilon_decay'):
                decay_factor = agent.epsilon_decay ** start_ep
                min_eps = getattr(agent, 'epsilon_min', getattr(agent, 'epsilon_end', 0.01))
                agent.epsilon = max(min_eps, agent.epsilon * decay_factor)
                print(f"[{name}] Adjusted epsilon to {agent.epsilon:.4f} for start_ep={start_ep}")

        hook = get_hook(hook_name)
        hook.set_agent(agent)
        hook.is_training = True
        
        # Only initialize header if starting fresh
        if start_ep == 0 or not os.path.exists(log_path):
            with open(log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean'])
            
        global_step = start_ep * STEPS_PER_EP
        for ep in range(start_ep, TOTAL_EPISODES):
            hook.reset_episode()
            runner = SimulationRunner(
                scenario="urban_grid",
                n_vehicles=50,
                seed=42 + ep,
                method=hook_name,
                method_params={},
                duration_steps=STEPS_PER_EP
            )
            metrics = runner.run()
            global_step += STEPS_PER_EP
            
            if hasattr(agent, 'memory'):
                batch_size = getattr(agent, 'batch_size', 64)
                num_updates = max(1, len(agent.memory) // batch_size)
                for _ in range(num_updates):
                    if hasattr(agent, 'train_step'):
                        agent.train_step()
                    if hasattr(agent, 'update_epsilon'):
                        agent.update_epsilon()
            
            if hasattr(agent, 'update_target_network'):
                agent.update_target_network()
                
            ep_reward = hook.episode_reward
            aoi = metrics.get('AoI_mean', 0.0)
            cbr = metrics.get('CBR_mean', 0.0)
            pdr = metrics.get('PDR_mean', 0.0)
            
            with open(log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([ep+1, global_step, ep_reward, aoi, cbr, pdr])
            
            # Save intermediate model weights after each episode
            agent.save(model_path)
            
            if (ep + 1) % 10 == 0 or (ep + 1) == TOTAL_EPISODES:
                print(f"[{name}] Ep {ep+1}/{TOTAL_EPISODES} - Reward: {ep_reward:.2f} (Weights saved)")
```

---

## 6. 검증 방안 (Verification Method)

Worker 에이전트가 코드 수정 후 검증해야 하는 절차입니다:

1. **문법 및 컴파일 검증**:
   ```bash
   python3 -m py_compile /home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py
   ```
2. **시뮬레이션 재개 검증 (Dry Run / Log Verification)**:
   - `python3 code/run_parallel_evaluation.py` 실행 시 콘솔에 출력되는 메시지 확인:
     - 예: `--- Training QLearning starting from Episode 64/100 on GPU 0 ---`
     - 에피소드 1부터 재시작하지 않고 에피소드 64부터 이어짐을 증명.
3. **가중치 파일 생성 확인**:
   - `ls -l /home/imnyj/Workspace/paper4/data/models/` 명령으로 훈련 도중 `.pkl` 및 `.pth` 파일이 실시간 생성/갱신되는지 확인.
4. **CSV 수렴 로그 보존 확인**:
   - `wc -l /home/imnyj/Workspace/paper4/data/models/*_convergence.csv` 수행 시 라인 수가 101개(헤더 1 + 에피소드 100)로 최종 도출되는지 검증.
