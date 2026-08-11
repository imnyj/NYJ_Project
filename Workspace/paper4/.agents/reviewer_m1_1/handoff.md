# Handoff Report — Paper4 M1 Verification Review

**Agent ID**: `reviewer_m1_1`  
**Date**: 2026-08-11  
**Target File**: `/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py`  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Review Summary

`worker_m1`이 작성한 `code/run_parallel_evaluation.py`의 체크포인트 재개(resume), CSV append 작성, 매 에피소드 가중치 저장(`agent.save()`), 프로세스 격리(`mp.set_start_method('spawn')`) 구문 및 로직을 다각도로 검증하였습니다.

검증 결과, **PyTorch 기반 RL 모델(VanillaDQN, DoubleDQN, DuelingDQN, MoEDQN, REMO-DQN 등)이 기존 `.pth` 체크포인트를 로드하여 재개할 때 `agent.epsilon` 탐험율(Exploration rate)이 초기값(1.0)으로 리셋되는 결함(Critical Finding)**이 발견되었습니다. 이에 따라 **REQUEST_CHANGES** 판정을 내립니다.

---

## 2. Findings (결함 상세 및 시정 요청)

### [Critical] Finding 1: 체크포인트 재개 시 PyTorch RL 모델의 Epsilon 탐험율 리셋 결함

- **위치**: `code/run_parallel_evaluation.py` 150~162행
- **현상**:
  ```python
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
  ```
- **원인 분석**:
  1. PyTorch 기반 모델(`VanillaDQN`, `DoubleDQN`, `DuelingDQN`, `MoEDQN`, `REMO-DQN` 등)의 `save()` 및 `load()` 메서드는 신경망 가중치(`state_dict`)만 저장/복원하고 `self.epsilon`은 저장하지 않습니다 (`QLearning`/`SARSA`는 `.pkl`에 epsilon 포함).
  2. `if os.path.exists(model_path):` 구문이 참이 되어 `agent.load(model_path)`를 실행하면, 바로 뒤의 `elif start_ep > 0:` 구문은 **절대로 실행되지 않습니다**.
  3. 그 결과 `create_agent()`에서 초기화된 `agent.epsilon = 1.0` 상태 그대로 54/68 에피소드부터 학습을 재개하게 됩니다.
- **영향 범위**:
  제안 모델인 `REMO-DQN`을 비롯한 주요 DQN 계열 모델들이 체크포인트에서 재개될 때 100% 무작위 행동(epsilon=1.0)으로 재출발하여 학습 수렴 곡선(Reward Convergence)이 심각하게 왜곡되고 정책 학습 데이터가 오염됩니다.
- **수정 제안**:
  `if os.path.exists(model_path): ...` 과 `epsilon` 보정을 `if...elif` 구조로 묶지 말고 별도의 단계로 분리하여, 체크포인트를 로드한 후에도 `start_ep > 0`일 경우 PyTorch 모델의 `agent.epsilon`을 `max(min_eps, initial_eps * (epsilon_decay ** start_ep))`로 정확히 계산/보정하도록 수정해야 합니다.

```python
# 수정 코드 예시
if os.path.exists(model_path):
    try:
        agent.load(model_path)
        print(f"[{name}] Loaded existing checkpoint from {model_path}")
    except Exception as e:
        print(f"[{name}] Warning: Could not load checkpoint from {model_path}: {e}")

# PyTorch 모델 등 weight 파일에 epsilon이 저장되지 않는 경우 start_ep에 맞춰 epsilon decay 보정
if start_ep > 0 and hasattr(agent, 'epsilon') and hasattr(agent, 'epsilon_decay'):
    if name not in ["QLearning", "SARSA"]:
        decay_factor = agent.epsilon_decay ** start_ep
        min_eps = getattr(agent, 'epsilon_min', getattr(agent, 'epsilon_end', 0.01))
        initial_eps = getattr(agent, 'epsilon_start', 1.0)
        agent.epsilon = max(min_eps, initial_eps * decay_factor)
        print(f"[{name}] Adjusted epsilon to {agent.epsilon:.4f} for start_ep={start_ep}")
```

---

### [Minor] Finding 2: CSV 파일 파싱 예외 처리 시 미완성 라인 append 위험

- **위치**: `code/run_parallel_evaluation.py` 130~138행
- **현상**: 비정상 프로세스 종료로 CSV 마지막 줄이 덜 작성된 경우, `int(lines[-1].split(',')[0])`에서 `ValueError`가 발생하여 `except` 구문의 `start_ep = len(lines) - 1`로 처리됩니다.
- **영향 범위**: 깨진 줄 뒤에 그대로 `writer.writerow`로 개행 없이 덧붙여지면 CSV 포맷 오염 가능성이 존재합니다.
- **수정 제안**: CSV 읽기 시 파일 마지막에 개행 문자(`\n`)가 포함되어 있는지 확인하거나 불완전한 라인을 정돈하는 가드가 추가되면 더욱 완벽합니다.

---

### [Minor] Finding 3: `eval_worker` 내 `get_hook` 중복 호출

- **위치**: `code/run_parallel_evaluation.py` 248행 및 268행
- **현상**: `eval_worker` 함수 내에서 `runner.run()` 수행 전후로 `get_hook(hook_name)`을 두 번 호출합니다.
- **수정 제안**: 사전에 할당한 `hook` 변수를 재사용하도록 다듬어 불필요한 함수 호출을 줄일 수 있습니다.

---

## 3. Verified Claims (주장 검증)

| 검증 항목 | 제출된 주장 | 실제 검증 결과 | 상태 |
|---|---|---|---|
| 구문 검수 | `py_compile` 정상 통과 | `py_compile code/run_parallel_evaluation.py` 실행 완료 (exit code 0) | **PASS** |
| 에피소드 이어서 작성 | CSV 개행 및 에피소드 번호 연속성 유지 | `QLearning`, `SARSA` 등 CSV 열람 결과 Episode 1~68 개행 및 순서 보존 | **PASS** |
| 에피소드별 가중치 저장 | 매 에피소드 종료 시 `agent.save()` 호출 | loop 내부 209행 `agent.save(model_path)` 존재 및 실행 확인 | **PASS** |
| 멀티프로세싱 spawn | `mp.set_start_method('spawn', force=True)` 적용 | main() 함수 시작부 297행에 정상 적용 | **PASS** |
| Epsilon 상태 보정 | `start_ep > 0`일 때 epsilon decay 보정됨 | **`if...elif` 구조로 인해 `.pth` 로드 시 `elif` 미진입으로 epsilon=1.0 리셋 발생** | **FAIL** |

---

## 4. Adversarial Review & Stress Test Results (적대적 스트레스 테스트)

### 1) Assumption Stress-Testing
- **가정**: `.pth` 파일 로드 시 훈련 상태가 완벽히 복원될 것이다.
- **반례 검증**: `VanillaDQN`에 대해 `agent.load('VanillaDQN.pth')` 호출 후 `agent.epsilon`을 출력한 결과, `1.0`으로 유지됨을 직접 확인. (ep 54 재개 시 기대값 `0.7626` vs 실제값 `1.0`).
- **결론**: 학습 재개 시 초기 탐험율로 리셋되어 훈련 연속성 파괴.

### 2) Integrity Verification (무결성 검증)
- 하드코딩된 결과값, 눈속임(Dummy) 구현, 편법(Shortcut) 구현 여부를 정밀 전수 조사함.
- `sim_engine.py` (libsumo 기반 V2X 시뮬레이터)와 실제 연결되어 동작하며, 억지로 결과를 고정하는 무결성 위반 요소는 발견되지 않음. (동작 로직상의 Epsilon Bug가 유일한 주요 문제).

---

## 5. Caveats (주의사항)

- 현재 백그라운드 학습 프로세스(`task-283`)가 수행 중일 수 있으므로, `worker_m1`이 코드 수정 후 프로세스를 재시작할 수 있도록 명확히 안내해야 합니다.

---

## 6. Conclusion (최종 결론)

`code/run_parallel_evaluation.py`의 구조적 틀과 파일 다루기(append 모드, spawn 설정, agent.save)는 잘 구성되었으나, **PyTorch 모델의 탐험율(epsilon) 복원 불가능 결함**으로 인해 학습 결과의 정확성이 손상될 수 있습니다.

따라서 판정은 **REQUEST_CHANGES**이며, `worker_m1`에게 Finding 1 결함 수정을 요청해야 합니다.

---

## 7. Verification Method (독립 검증 방법)

1. Python 코드로 `VanillaDQN` 또는 `REMO-DQN` epsilon 복원 확인:
   ```bash
   /home/imnyj/venv/bin/python -c "
   import sys, os
   sys.path.append('/home/imnyj/Workspace/paper4/code')
   from run_parallel_evaluation import create_agent
   agent = create_agent('VanillaDQN')
   model_path = '/home/imnyj/Workspace/paper4/data/models/VanillaDQN.pth'
   if os.path.exists(model_path):
       agent.load(model_path)
   print('Resumed Epsilon:', getattr(agent, 'epsilon', None))
   "
   ```
2. 수정 후 Epsilon 값이 1.0이 아닌 `1.0 * (epsilon_decay ** start_ep)` 로 정교하게 조정되는지 확인.
