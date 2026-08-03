# Paper4 Visualizer Configuration

이 문서는 Paper4의 모든 그래프를 렌더링하는 `visualizer` 에이전트들이 공통적으로 참조해야 하는 **모델 순서(Order) 및 색상(Color) 맵핑 전역 설정 파일**입니다.
모든 시각화 파이썬 스크립트(`matplotlib` 등)는 반드시 이 테이블에 명시된 순서대로 범례(Legend)를 배치하고 지정된 색상(Hex Code 또는 이름)과 선 스타일을 사용해야 합니다.

## 🎨 Global Legend & Color Map (총 16개 모델)

| Order | Category | Model Name | Color (Hex/Name) | Line Style | Marker (for Line plots) |
|---|---|---|---|---|---|
| 1 | Baseline | **Fixed 10Hz** | `#000000` (Black) | `--` (Dashed) | `x` |
| 2 | Heuristic | **ReactDCC** | `#8B4513` (SaddleBrown) | `-` (Solid) | `v` |
| 3 | Heuristic | **AdaptDCC** | `#FF0000` (Red) | `-` (Solid) | `^` |
| 4 | Supervised | **TinyMLP** | `#FF69B4` (HotPink) | `-` (Solid) | `<` |
| 5 | Basic RL | **Q-Learning** | `#D3D3D3` (LightGray) | `-` (Solid) | `.` |
| 6 | Basic RL | **SARSA** | `#A9A9A9` (DarkGray) | `-` (Solid) | `,` |
| 7 | Basic RL | **Actor-Critic** | `#808080` (Gray) | `-` (Solid) | `1` |
| 8 | Basic DRL | **Vanilla DQN** | `#87CEEB` (SkyBlue) | `-` (Solid) | `s` |
| 9 | Basic DRL | **PPO** | `#0000FF` (Blue) | `-` (Solid) | `p` |
| 10 | Basic DRL | **DDPG** | `#000080` (Navy) | `-` (Solid) | `h` |
| 11 | Add. DRL | **Double DQN** | `#00FFFF` (Cyan) | `-` (Solid) | `+` |
| 12 | Add. DRL | **TD3** | `#008080` (Teal) | `-` (Solid) | `d` |
| 13 | Latest 2026 | **Decision Transformer**| `#90EE90` (LightGreen) | `-` (Solid) | `*` |
| 14 | Latest 2026 | **SAC** | `#FFA500` (Orange) | `-` (Solid) | `D` |
| 15 | Latest 2026 | **MAPPO** | `#808000` (Olive) | `-` (Solid) | `o` |
| 16 | **Proposed** | **REMO-DQN** | `#FF00000` (Red) | **`-` (Thick Solid)** | **`*` (Large)** |

## 📌 Visualizer 에이전트 지침서
* **색상 난립 금지**: 그래프를 그릴 때 `matplotlib`의 자동 색상 할당 기능을 끄고, 이 문서의 Hex Code를 명시적으로 파라미터로 넘길 것.
* **REMO-DQN 강조**: 제안 모델인 `REMO-DQN`은 논문의 핵심이므로, 다른 라인들보다 두께(linewidth)를 최소 1.5배 이상 두껍게 처리하고 Z-order를 가장 높게 설정하여 모든 그래프에서 가장 위로 올라오게(가려지지 않게) 할 것.
* **범례 렌더링**: 모델 개수가 많아 범례가 차트를 가릴 수 있으므로, `bbox_to_anchor`를 조절하여 그래프 바깥쪽(우측 또는 하단)에 n열(columns)로 정갈하게 배치할 것.
