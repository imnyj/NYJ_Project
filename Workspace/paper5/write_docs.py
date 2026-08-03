import sys
import os

sys.path.append(os.path.abspath("/home/imnyj/Command/core"))
from lock_manager import LockManager
from audit_logger import AuditLogger

lm = LockManager()
logger = AuditLogger()
agent_id = "paper_planner_agent"
base_dir = "/home/imnyj/Workspace/paper5"

docs = {
    "contributions.md": """# Contributions

본 논문은 UAM 환경에서의 빈번한 Handover로 인한 통신 지연(Delay) 및 Ping-Pong 현상을 최소화하기 위한 사전 예측적(Proactive) 핸드오버 최적화 방안을 제안하며, 다음과 같은 주요 기여를 가집니다.

1. **3D Map 시뮬레이션 기반 SAGIN 네트워크 환경 구축**
   - 3차원 빌딩 맵과 고도, 현실적인 비행 궤적 및 속도(수직/수평)를 반영한 고도화된 UAM 시뮬레이션 환경을 설계하였습니다.
   - 통신 커버리지 홀(Coverage Hole)을 극복하기 위해 지상망(Cellular, 5G), 노변 기지국(RSU), 위성망(Starlink LEO)을 혼합한 다중 계층(Multi-tier) SAGIN(Space-Air-Ground Integrated Networks) 환경을 구성하여 핸드오버 시나리오의 현실성을 극대화하였습니다.

2. **GNN-Transformer-PPO 기반 Proactive Handover 모델 제안**
   - **GNN (Graph Neural Network):** UAM 기체, 기지국, 장애물(건물) 간의 동적인 토폴로지 변화와 공간적 상호작용을 완벽히 모델링하여 핸드오버 시그널링 간섭 및 Ping-Pong 현상을 감소시킵니다.
   - **Transformer (Self-Attention):** 복잡하고 긴 비행 궤적의 시계열 데이터를 병렬적으로 처리하여, 기존 LSTM의 장기 의존성(Long-term Dependency) 학습 한계를 극복하고 예측 지연 시간을 극한으로 단축합니다.
   - **PPO (Proximal Policy Optimization):** 공간적(GNN) 및 시계열적(Transformer) 임베딩을 바탕으로 안정적이고 최적화된 핸드오버 정책(Action)을 결정합니다.

3. **기존 모델 대비 압도적인 성능 개선 입증**
   - 최신 논문(2025~2026) 및 강화학습 모델 12종과의 비교 실험(Optuna 최적화)을 통해 제안 방안이 Handover Delay 및 Ping-Pong Effect를 최소화하는 데 있어 1위를 달성함을 수치적으로 입증하였습니다.
""",
    "performance_metrics.md": """# Performance Metrics

제안하는 GNN-Transformer-PPO 모델의 성능 및 Contributions를 입증하기 위해 다음과 같은 평가 지표(Metrics)를 활용합니다.

1. **Handover Delay (핸드오버 지연 시간)**
   - 핸드오버 결정부터 타겟 네트워크에 완전히 접속되어 데이터 전송이 재개되기까지 소요되는 시간입니다. 통신 끊김 현상을 방지하기 위해 최소화해야 하는 핵심 지표입니다.

2. **Ping-Pong Rate (핑퐁 비율)**
   - 짧은 시간 내에 두 기지국 사이를 불필요하게 왕복하며 핸드오버하는 횟수의 비율입니다. 통신 오버헤드와 불안정성을 나타내며, 낮을수록 우수합니다.

3. **Packet Delivery Ratio (PDR, 패킷 전송 성공률)**
   - 송신된 패킷 중 수신지에 성공적으로 도달한 패킷의 비율입니다. 복잡한 3D Map 및 혼합망(SAGIN) 환경에서도 지속적인 연결을 유지하는지 평가합니다.

4. **Throughput (처리량)**
   - 단위 시간당 성공적으로 전송된 데이터의 양입니다. 핸드오버 과정에서 대역폭이 보장되는지 확인합니다.

5. **Total Handover Cost (종합 핸드오버 비용 / Score)**
   - Handover Delay와 Ping-Pong Effect에 가중치를 부여한 종합 점수입니다. 
   - *Score = (Handover Delay) + 2 * (Ping-Pong Effect)* (낮을수록 우수함)
""",
    "intro.md": """# Introduction (Storyline)

**1. 연구 배경: UAM 산업의 부상과 통신 연결의 중요성**
- UAM(Urban Air Mobility)은 차세대 도심 교통 수단으로 각광받고 있으며, 안전한 비행(충돌 방지 스케줄링 등)과 관제를 위해 끊김 없는 통신망 유지가 필수적입니다.
- 기존의 수동적(Reactive)이고 음성 중심의 관제는 고속 이동 및 3차원 궤적을 지닌 UAM 환경에 적합하지 않습니다.

**2. 문제 정의: UAM 통신 환경의 한계 (Handover Delay 및 핑퐁 현상)**
- UAM은 고도가 높고 이동 속도가 빨라 기존 지상망(Cellular) 안테나의 Main Lobe를 벗어나는 커버리지 홀(Coverage Hole)에 자주 진입합니다.
- 복잡한 도심 건물 구조(3D Map)에 의해 신호 간섭과 단절이 발생하며, 기지국 간 이동 시 빈번한 핸드오버로 인해 통신 지연(Delay) 및 불필요한 핑퐁(Ping-Pong) 현상이 발생합니다.

**3. 최신 연구 동향 및 한계점**
- 최근 연구(2025~2026)는 사전 예측적(Proactive) 핸드오버 및 위성/RSU를 포함하는 SAGIN 환경으로 진화하고 있습니다.
- 그러나 기존의 CNN-LSTM 기반 강화학습 모델 등은 격자 기반 데이터에 국한되어 동적인 토폴로지 변화(그래프 구조)를 반영하지 못하거나, 긴 궤적에 대한 시계열 장기 의존성(Long-term dependency) 학습에 한계(Gradient 소실 등)가 존재합니다.

**4. 제안 방안: 3D Map SAGIN 환경과 GNN-Transformer-PPO 기반 최적화**
- 본 논문에서는 통신 단절을 방지하기 위해 지상망(Cellular), RSU, 위성망(Starlink)을 융합한 SAGIN 환경을 구축하고, 3D Map 기반의 시뮬레이션을 설계합니다.
- 특히, 기존 한계를 극복하기 위해 공간적 동적 토폴로지를 캡처하는 GNN과 시계열 예측 지연을 최소화하는 Transformer를 결합한 **GNN-Transformer-PPO** 아키텍처를 제안하여 Proactive Handover를 최적화합니다.

**5. 기대 효과 및 논문의 구성**
- 이를 통해 핸드오버 지연 및 핑퐁 횟수를 획기적으로 낮출 수 있음을 증명하며, 이어지는 장에서 시스템 모델, 제안하는 알고리즘, 성능 평가 순으로 논의를 전개합니다.
""",
    "required_graphs.md": """# Required Graphs (결과 분석 필수 그래프)

제안하는 GNN-Transformer-PPO 모델의 우수성을 12개의 비교 모델 및 기존 제안 방안(CNN-LSTM+PPO)과 대비하여 입증하기 위해 다음의 그래프(Plots)를 도출해야 합니다.

1. **Learning Curve (학습 수렴 곡선)**
   - **X축:** Episode (학습 에피소드 수)
   - **Y축:** Cumulative Reward (누적 보상) 또는 Total Score
   - **의미:** 제안 모델이 기존 모델들(CNN-LSTM+PPO, PPO-GNN, TD3-Transformer 등)에 비해 빠르게 수렴하고, 안정적인 학습 성능을 보임을 증명합니다.

2. **Average Handover Delay by Vehicle Speed (비행 속도에 따른 평균 핸드오버 지연 시간)**
   - **X축:** UAM Velocity (속도, km/h)
   - **Y축:** Handover Delay (ms)
   - **의미:** 기체의 속도가 빨라져 토폴로지가 급변하더라도, Transformer 기반의 예측과 GNN 공간 분석을 통해 지연 시간이 현저히 적음을 나타냅니다.

3. **Ping-Pong Rate Comparison (핑퐁 비율 비교 Bar Chart)**
   - **X축:** Models (제안 모델 vs. 기존 비교 모델 12종 주요 모델 그룹)
   - **Y축:** Ping-Pong Handover Count / Rate
   - **의미:** 불필요한 네트워크 스위칭 빈도가 제안 모델에서 가장 적음을 가시적으로 보여줍니다.

4. **Network Utilization Rate in SAGIN (통신망 점유/활용 비율 분석)**
   - **X축:** Time Step 또는 UAM Trajectory Sequence
   - **Y축:** Connected Network Type (Cellular, RSU, Starlink)
   - **의미:** 고도 및 건물 장애물 상황에 따라 제안 모델이 언제 지상망(Cellular/RSU)을 쓰고 언제 위성(Starlink)으로 Proactive하게 넘어가는지 궤적에 따른 전환 패턴을 분석합니다.

5. **Throughput / Packet Delivery Ratio (PDR) CDF (누적 분포 함수)**
   - **X축:** Throughput (Mbps) 또는 PDR (%)
   - **Y축:** CDF (Cumulative Distribution Function)
   - **의미:** 통신 품질 측면에서 제안 방안이 하위 퍼센타일에서도 끊김 없는(High Reliability) 서비스를 제공함을 입증합니다.
""",
    "comparative_methods.md": """# Comparative Methods (비교 모델 12종 + 1종 특징 정리)

총 13종의 모델(기존 제안 및 12개 비교 모델)의 특징을 분석하여 성능 비교의 근거로 삼습니다. (평가 지표: Score = Handover Delay + 2 * Ping-Pong Effect)

## A. 최신 모델 (2025~2026)
1. **PPO-GNN (Score: 28.34)**
   - *특징:* 그래프 신경망(GNN)을 활용해 네트워크 노드 간 공간적 관계를 파악하나, 시계열적 궤적 변화(Transformer) 예측이 부족하여 한계가 존재합니다.
2. **TD3-Transformer (Score: 31.59)**
   - *특징:* 연속 행동 공간에 강한 TD3에 Transformer를 결합하였으나, 이산 행동(네트워크 선택) 환경인 핸드오버 매핑 시 효율성이 떨어집니다.
3. **MARL-Attention (Score: 31.08)**
   - *특징:* 다중 에이전트 및 Attention 메커니즘을 사용하지만, 복잡한 3D 공간 제약(건물 등) 처리 면에서 제안 방안보다 학습 안정성이 부족합니다.

## B. 기존 딥러닝/강화학습 제안 방안
4. **CNN-LSTM + PPO (Score: 26.01)**
   - *특징:* 기존에 제안되었던 방식으로, 궤적을 예측하지만 격자 기반 CNN의 한계와 긴 시계열 데이터에서 LSTM의 기울기 소실 문제로 동적 토폴로지 적응이 느립니다.

## C. 추가 DRL 모델군
5. **A2C (Advantage Actor-Critic, Score: 41.20)**
   - *특징:* PPO의 이전 버전 격으로 동기식(Synchronous) 업데이트를 수행하나 성능 변동폭이 큽니다.
6. **MAC (Multi-Agent Actor-Critic, Score: 41.36)**
   - *특징:* 여러 UAM 에이전트 간의 협력 학습을 시도하나, 복잡성 증가로 인해 최적화 점수가 상대적으로 낮습니다.
7. **TRPO (Trust Region Policy Optimization, Score: 43.98)**
   - *특징:* 안정적인 정책 업데이트를 보장하나 연산량이 과도하여 실시간 핸드오버 적용에 병목이 발생합니다.

## D. 기본 DRL (Deep Reinforcement Learning) 모델
8. **SAC (Soft Actor-Critic, Score: 48.44)**: 탐험(Exploration)을 극대화하는 Entropy 기반 모델이나, 빠른 수렴이 어려움.
9. **DDPG (Score: 48.90)**: 연속 제어용 모델로, 핸드오버 네트워크 선택(이산화)에 적용 시 성능이 매우 낮음.
10. **DQN (Score: 48.97)**: 가치 기반(Value-based)의 대표적 심층 모델이지만, 고차원 상태 공간 처리에서 PPO에 밀림.

## E. 기본 RL (전통적 기법)
11. **SARSA (Score: 63.61)**: On-policy 방식의 테이블 기반 학습으로, 연속적 상태 변수 환경 적용 불가.
12. **Q-Learning (Score: 63.67)**: Off-policy 방식의 테이블 기반 학습. 딥러닝 부재로 확장성(Scalability) 0.
13. **Monte Carlo (Score: 67.98)**: 에피소드가 끝나야만 학습하므로 실시간 결정(핸드오버)에는 부적합한 최하위 모델.
"""
}

for filename, content in docs.items():
    filepath = os.path.join(base_dir, filename)
    print(f"Acquiring lock for {filepath}...")
    if lm.acquire(filepath, agent_id, timeout=10):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.log_action(agent_id, "CREATE" if not os.path.exists(filepath) else "MODIFY", filepath, f"Generated {filename}")
            print(f"Successfully generated and saved: {filename}")
        except Exception as e:
            print(f"Error writing {filename}: {e}")
        finally:
            lm.release(filepath, agent_id)
            print(f"Released lock for {filepath}")
    else:
        print(f"Failed to acquire lock for {filepath}")
