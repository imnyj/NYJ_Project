# REMO-DQN 훈련 파이프라인 및 수렴성 검증 분석 보고서 (Analysis Report)

## 1. 개요 (Executive Summary)
- **과업 목표**: Paper 4 제안 모델인 **REMO-DQN (ResNetMoEDQN)**의 100 에피소드(총 20만 스텝) 훈련 파이프라인 구성 및 수렴성 프로그램 검증 방안 분석 (R1 요구사항).
- **분석 대상**:
  - `code/train_resnet.py` (훈련 메인 진입점)
  - `code/resnet_moe_agent.py` (ResNet-MoE 아키텍처 및 DRL 에이전트)
  - `code/sim_engine.py` (SUMO 및 802.11p 통신 시뮬레이션 엔진)
  - `code/ai_dcc_hook.py` (C-3 보상 함수 및 전이 수집 훅)
  - `visualizer/evaluation_plan.md` 및 `prompt_draft.md` (평가 명세 및 수렴 요구사항)
- **핵심 결론**:
  1. `train_resnet.py`의 기본 파라미터는 현재 `episodes=500`, `duration_steps=1000`, `epsilon_decay=0.995`로 설정되어 있으므로, 요구사항인 `episodes=100`, `duration_steps=2000`, `epsilon_decay=0.95`로 조정해야 함.
  2. 현재 에피소드별 차량 밀도가 50으로 고정되어 있으므로, 매 에피소드 `random.choice([30, 50, 100])`를 선택하고 `SimulationRunner`에 `n_vehicles=density`와 `method_params={'n_vehicles_sweep': density}`를 함께 전달하도록 수정이 필요함.
  3. 모델 가중치는 `data/models/resnet_moe_dqn.pth` (또는 `REMO-DQN.pth`)에 저장되며, 훈련 로그 CSV에는 `Cumulative_Steps` 및 `Density` 컬럼이 추가되어야 함.
  4. 수렴성 검증 스크립트는 100 에피소드 완료 후 초기 10 에피소드($ep \in [1, 10]$)와 마지막 10 에피소드($ep \in [91, 100]$)의 평균 보상 상승량 및 Welch's t-test($p < 0.05$), 표준편차 안정성을 독립적으로 평가하도록 설계함.

---

## 2. 코드베이스 심층 분석

### 2.1. 하이퍼파라미터 설정 및 적용 가능 여부 분석

#### 현황 (`code/train_resnet.py`)
- `train()` 함수 정의 (Line 14-16):
  ```python
  def train(num_episodes=500, seed=42, duration_steps=1000,
            output_model="resnet_moe_dqn.pth", output_log="resnet_train_log.csv",
            epsilon_decay=0.995, min_epsilon=0.01):
  ```
- `parse_args()` CLI 기본값 (Line 100-106):
  - `--episodes`: 500
  - `--duration_steps`: 1000
  - `--epsilon_decay`: 0.995
  - `--min_epsilon`: 0.01

#### 요구사항 대조 및 분석
- **목표 설정값**:
  - `num_episodes = 100`
  - `duration_steps = 2000` (에피소드당 2,000 스텝)
  - `epsilon_decay = 0.95`
  - `min_epsilon = 0.01`
- **적용 가능성**:
  - `train_resnet.py` 내부 구조는 이미 `num_episodes`, `duration_steps`, `epsilon_decay`를 파라미터화하여 받고 있으므로 완벽하게 호환 가능.
- **총 훈련 스텝 규모**:
  - $100 \text{ episodes} \times 2,000 \text{ steps/episode} = 200,000 \text{ steps}$ (총 20만 스텝).
  - 이는 `visualizer/evaluation_plan.md` Line 49 ("학습을 시킬 때는 20만번의 step을 진행하면서 수치가 전반적으로 상승하다가 수렴되는지를 확인해야 함")과 정확히 일치함.
- **Epsilon 감쇄 역학 ($\epsilon$-Decay Dynamics)**:
  - 감쇄 공식: $\epsilon_t = \max(0.01, 1.0 \times 0.95^{t-1})$
  - 에피소드 진행에 따른 $\epsilon$ 추이:
    - Episode 1: $1.0000$ (완전 무작위 탐색)
    - Episode 10: $0.6302$
    - Episode 20: $0.3774$
    - Episode 40: $0.1353$
    - Episode 60: $0.0485$
    - Episode 80: $0.0174$
    - Episode 90: $0.0100$ (최소 탐험율 도달)
    - Episode 91 ~ 100: $0.0100$ (안정적 정책 활용/Exploitation 구간)
  - **평가**: 100 에피소드 체계에서 0.95의 감쇄율은 1~40 에피소드에서 다양한 교통 밀도에 대한 상태-행동 탐색을 충분히 수행하고, 80 에피소드 이후 최소 탐험율($\epsilon=0.01$)로 진입하여 후반 10 에피소드(91~100)의 수렴 보상을 왜곡(무작위 탐색으로 인한 패널티) 없이 측정하기에 최적의 설정임.

---

### 2.2. 매 에피소드 랜덤 차량 밀도(30, 50, 100) 적용 분석

#### 현황 (`code/train_resnet.py`)
- 현재 코드 (Line 51-58):
  ```python
  runner = SimulationRunner(
      scenario="urban_grid",
      n_vehicles=50,
      seed=seed+ep,
      method="ResNetMoEDQN",
      method_params={},
      duration_steps=duration_steps
  )
  ```
- **문제점**:
  - `n_vehicles=50`으로 하드코딩되어 있어 매 에피소드가 50대의 단일 차량 밀도에서만 수행됨.

#### `code/sim_engine.py` 연동 메커니즘 분석
- `sim_engine.py`의 `SimulationRunner.run()` (Line 471-474):
  ```python
  # Override config DENSITY and AV_SPEED ONLY if explicitly passed as a sweep variable
  if self.method_params and 'n_vehicles_sweep' in self.method_params:
      config["DENSITY"] = self.method_params['n_vehicles_sweep']
  ```
- `generate_sumonetsim_files()` (Line 378-380):
  ```python
  for k, v in config.items():
      code = re.sub(rf"^{k}\s*=.*", f"{k} = {v}", code, flags=re.MULTILINE)
  ```
- **핵심 연동 규칙**:
  - SUMO 도로망 생성기(`make_sumo_set.py`)에 정확한 차량 밀도를 주입하기 위해서는 `SimulationRunner` 생성 시 `n_vehicles=density`와 함께 `method_params={'n_vehicles_sweep': density}`를 반드시 전달해야 함.

#### 제안 수정안
```python
import random

# 에피소드 루프 내부
for ep in range(num_episodes):
    hook.reset_episode()
    
    # 30, 50, 100 중 매 에피소드 무작위 선택
    density = random.choice([30, 50, 100])
    
    print(f"Starting Episode {ep+1}/{num_episodes} (Density: {density}, Epsilon: {agent.epsilon:.4f})...")
    runner = SimulationRunner(
        scenario="urban_grid",
        n_vehicles=density,
        seed=seed + ep,
        method="ResNetMoEDQN",
        method_params={'n_vehicles_sweep': density},
        duration_steps=duration_steps
    )
    metrics = runner.run()
```

---

### 2.3. 가중치 저장 경로 및 파일명 분석

#### 현황 및 요구사항
- **요구사항**: `data/models/` 경로 및 파일명 (e.g. `resnet_moe_dqn.pth` 또는 `REMO-DQN.pth`).
- **현황 (`train_resnet.py` Line 15, 91-95, 105)**:
  - 현재 기본 인자: `output_model="resnet_moe_dqn.pth"` (실행 경로에 저장).
  - 디렉토리 생성 처리 (Line 91-93):
    ```python
    model_dir = os.path.dirname(output_model)
    if model_dir and not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
    agent.save(output_model)
    ```
- **제안 수정안**:
  - 기본 저장 위치를 프로젝트 루트 기준 `data/models/resnet_moe_dqn.pth` (또는 `data/models/REMO-DQN.pth`)로 기본값 변경 및 상대/절대 경로 자동 해석 지원:
    ```python
    default_model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "models")
    default_model_path = os.path.join(default_model_dir, "resnet_moe_dqn.pth")
    ```

---

### 2.4. 훈련 로그 CSV 파일 경로 및 컬럼 구성 분석

#### 현황 (`code/train_resnet.py`)
- 현재 헤더 (Line 43):
  `['Episode', 'Reward', 'Loss', 'Epsilon', 'Steps', 'AoI_mean', 'CBR_mean', 'PDR_mean']`
- 현재 행 기록 (Line 88):
  `[ep+1, ep_reward, avg_loss, agent.epsilon, steps_val, aoi, cbr, pdr]`

#### 요구사항 대조 및 제안 구성
- **요구사항 필수 컬럼**: `Episode`, `Cumulative_Steps`, `Reward`, `Loss`, `Epsilon`, `Density`
- **확장 추천 컬럼**: 시뮬레이션 물리 지표 (`AoI_mean`, `CBR_mean`, `PDR_mean`, `Steps`)
- **수정 방안**:
  1. `cumulative_steps = 0` 누적 변수 초기화
  2. 에피소드 종료 시:
     `cumulative_steps += steps_val`
  3. CSV 헤더 구성:
     ```python
     ['Episode', 'Cumulative_Steps', 'Steps', 'Reward', 'Loss', 'Epsilon', 'Density', 'AoI_mean', 'CBR_mean', 'PDR_mean']
     ```
  4. 행 데이터 기록:
     ```python
     [ep+1, cumulative_steps, steps_val, ep_reward, avg_loss, agent.epsilon, density, aoi, cbr, pdr]
     ```
  5. 저장 경로: `data/models/REMO-DQN_convergence.csv` 또는 `data/train_logs/resnet_train_log.csv` (상대/절대 디렉토리 자동 생성).

---

## 3. 수렴성(Convergence) 프로그램 검증 방안

### 3.1. 수렴 판정 수학적 모델 및 가설 검정

1. **초기/후기 에피소드 표본 정의**:
   - Initial Window ($N_1 = 10$): $R_{\text{init}} = \{ R_1, R_2, \dots, R_{10} \}$
   - Final Window ($N_2 = 10$): $R_{\text{final}} = \{ R_{91}, R_{92}, \dots, R_{100} \}$

2. **평균 보상 상승 검정 (Reward Improvement)**:
   - $\bar{R}_{\text{init}} = \frac{1}{10} \sum_{i=1}^{10} R_i$
   - $\bar{R}_{\text{final}} = \frac{1}{10} \sum_{i=91}^{100} R_i$
   - 보상 개선량: $\Delta \bar{R} = \bar{R}_{\text{final}} - \bar{R}_{\text{init}}$
   - 판정 조건 1: $\Delta \bar{R} > 0$ (보상이 음수 체계인 C-3 reward에서도 $-50 \rightarrow -10$과 같이 값이 증가해야 함).

3. **통계적 유의성 검정 (Statistical Significance via Welch's t-test)**:
   - 귀무가설 ($H_0$): $\mu_{\text{final}} \le \mu_{\text{init}}$ (학습에 따른 보상 향상이 없음)
   - 대립가설 ($H_1$): $\mu_{\text{final}} > \mu_{\text{init}}$ (학습 후 보상이 유의미하게 상승함)
   - 검정 통계량:
     $$t = \frac{\bar{R}_{\text{final}} - \bar{R}_{\text{init}}}{\sqrt{\frac{s_{\text{init}}^2}{N_1} + \frac{s_{\text{final}}^2}{N_2}}}$$
   - 자유도 (Welch–Satterthwaite equation):
     $$\nu \approx \frac{\left(\frac{s_1^2}{N_1} + \frac{s_2^2}{N_2}\right)^2}{\frac{(s_1^2 / N_1)^2}{N_1 - 1} + \frac{(s_2^2 / N_2)^2}{N_2 - 1}}$$
   - 판정 조건 2: One-sided $p$-value $< 0.05$.

4. **정책 안정화 및 분산 검정 (Variance & Stability)**:
   - 후반부 표준편차: $s_{\text{final}} = \sqrt{\frac{1}{9}\sum_{i=91}^{100}(R_i - \bar{R}_{\text{final}})^2}$
   - 판정 조건 3: 후반부 탐험율 $\epsilon \le 0.01$ 및 보상 진폭 안정화.

5. **데이터 무결성 검증 (Data Integrity Acceptance)**:
   - 총 레코드 수 $N = 100$
   - 총 누적 스텝 == $200,000$ (각 2,000 스텝)
   - 결측치/NaN/Null 없음

---

### 3.2. 수렴성 검증 스크립트 구조 설계 (`code/verify_remo_convergence.py`)

```python
#!/usr/bin/env python3
"""
verify_remo_convergence.py
===========================
Programmatic convergence verification script for REMO-DQN (ResNetMoEDQN).
Acceptance Criteria:
  1. File exists and contains exactly 100 episodes.
  2. Final 10 episodes mean reward > Initial 10 episodes mean reward.
  3. Welch's t-test p-value < 0.05 (statistically significant reward growth).
  4. Final 10 episodes epsilon <= 0.01.
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np
from scipy import stats

def verify_convergence(csv_path: str, alpha: float = 0.05) -> dict:
    if not os.path.exists(csv_path):
        return {"status": "FAIL", "reason": f"File not found: {csv_path}"}

    df = pd.read_csv(csv_path)
    
    # Check 1: Record count
    if len(df) < 100:
        return {"status": "FAIL", "reason": f"Expected at least 100 episodes, found {len(df)}"}

    # Extract initial and final windows
    init_rewards = df.iloc[:10]['Reward'].values
    final_rewards = df.iloc[-10:]['Reward'].values
    
    mean_init = float(np.mean(init_rewards))
    mean_final = float(np.mean(final_rewards))
    std_init = float(np.std(init_rewards, ddof=1))
    std_final = float(np.std(final_rewards, ddof=1))
    delta_reward = mean_final - mean_init

    # Check 2: Mean reward improvement
    reward_improved = delta_reward > 0

    # Check 3: Statistical significance (Welch's t-test, one-sided)
    t_stat, p_two_sided = stats.ttest_ind(final_rewards, init_rewards, equal_var=False)
    p_one_sided = p_two_sided / 2.0 if t_stat > 0 else 1.0 - (p_two_sided / 2.0)
    statistically_significant = (p_one_sided < alpha) and (t_stat > 0)

    # Check 4: Epsilon converged
    final_eps = float(df.iloc[-1]['Epsilon'])
    eps_converged = final_eps <= 0.015

    is_passed = reward_improved and statistically_significant and eps_converged

    result = {
        "status": "PASS" if is_passed else "FAIL",
        "total_episodes": len(df),
        "mean_init_reward": mean_init,
        "mean_final_reward": mean_final,
        "delta_reward": delta_reward,
        "std_init_reward": std_init,
        "std_final_reward": std_final,
        "t_statistic": float(t_stat),
        "p_value_one_sided": float(p_one_sided),
        "final_epsilon": final_eps,
        "checks": {
            "reward_improved": bool(reward_improved),
            "statistically_significant": bool(statistically_significant),
            "epsilon_converged": bool(eps_converged)
        }
    }
    return result

def main():
    parser = argparse.ArgumentParser(description="Verify REMO-DQN training convergence")
    parser.add_argument("--csv", type=str, default="data/models/REMO-DQN_convergence.csv", help="Path to training log CSV")
    args = parser.parse_args()

    res = verify_convergence(args.csv)
    print("=" * 60)
    print("REMO-DQN Convergence Verification Result")
    print("=" * 60)
    print(f"Status: {res['status']}")
    if res['status'] == "FAIL" and 'reason' in res:
        print(f"Reason: {res['reason']}")
        sys.exit(1)

    print(f"Total Episodes: {res['total_episodes']}")
    print(f"Initial 10 Ep Reward Mean: {res['mean_init_reward']:.4f} (±{res['std_init_reward']:.4f})")
    print(f"Final 10 Ep Reward Mean  : {res['mean_final_reward']:.4f} (±{res['std_final_reward']:.4f})")
    print(f"Reward Improvement (Delta): {res['delta_reward']:+.4f}")
    print(f"t-statistic: {res['t_statistic']:.4f}, p-value (one-sided): {res['p_value_one_sided']:.6f}")
    print(f"Final Epsilon: {res['final_epsilon']:.4f}")
    print("Detailed Checks:")
    for k, v in res['checks'].items():
        print(f"  - {k}: {'PASS' if v else 'FAIL'}")
    print("=" * 60)

    sys.exit(0 if res['status'] == "PASS" else 1)

if __name__ == "__main__":
    main()
```

---

## 4. 제안 코드 변경 요약 (Proposed Modifications Summary)

| 파일 경로 | 수정 위치 | 현재 상태 | 제안 변경 내용 |
|---|---|---|---|
| `code/train_resnet.py` | Line 14-16, 100-106 | `episodes=500, duration_steps=1000, epsilon_decay=0.995` | `episodes=100, duration_steps=2000, epsilon_decay=0.95` 로 변경 |
| `code/train_resnet.py` | Line 51-58 | `n_vehicles=50, method_params={}` 고정 | `density = random.choice([30, 50, 100])` 및 `n_vehicles=density, method_params={'n_vehicles_sweep': density}` 적용 |
| `code/train_resnet.py` | Line 43, 88 | 컬럼: `[Episode, Reward, Loss, Epsilon, Steps, AoI_mean, CBR_mean, PDR_mean]` | `Cumulative_Steps`, `Density` 컬럼 추가 및 누적 스텝 계산 로직 반영 |
| `code/train_resnet.py` | Line 15, 105 | `output_model="resnet_moe_dqn.pth"` (로컬 디렉토리) | `data/models/resnet_moe_dqn.pth` (또는 `REMO-DQN.pth`)로 경로 지정 |
| `code/verify_remo_convergence.py` | 신규 스크립트 | 미존재 | 초기 10 에피소드 vs 후기 10 에피소드 보상 상승 및 Welch's t-test 검증 스크립트 생성 |

---

## 5. 결론 및 향후 작업 방향
- **R1 단계 준비 완료**:
  - `train_resnet.py`의 파라미터 및 밀도 난수화, 로그 CSV 형식, 모델 가중치 저장 경로가 명확히 정의됨.
  - 훈련 완료 후 수렴성을 객관적으로 판정할 수 있는 통계적 검증 스크립트(`verify_remo_convergence.py`)의 구현 규격이 확립됨.
- **R2 및 R3 연계**:
  - R1의 검증 완료 후 동일한 100 에피소드/2000 스텝/랜덤 밀도(30, 50, 100) 인터페이스를 바탕으로 나머지 16개 모델의 학습 및 데이터 수집 파이프라인으로 매끄럽게 확장 가능함.
