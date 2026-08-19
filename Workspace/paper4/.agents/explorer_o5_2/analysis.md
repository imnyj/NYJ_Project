# Paper 4 시각화 스크립트 및 11대 타겟 산출물 전수 조사 분석 보고서 (analysis.md)

**작성일시**: 2026-08-19T20:37:00Z  
**작성자**: Visualizer & 11 Target Figures Explorer (`explorer_o5_2`)  
**작업 디렉토리**: `/home/imnyj/Workspace/paper4/.agents/explorer_o5_2/`  
**대상 디렉토리**: `/home/imnyj/Workspace/paper4/visualizer/`, `/home/imnyj/Workspace/paper4/data/`  

---

## 1. 개요 및 핵심 요약 (Executive Summary)

본 보고서는 `ORIGINAL_REQUEST.md`, `evaluation_plan.md`, `walkthrough.md` 및 `DISPATCH.md`의 지침에 따라 `/home/imnyj/Workspace/paper4/visualizer/` 내 생성된 **11대 타겟 산출물**(그래프 PNG/PDF 9종, 테이블 CSV/TeX 2종)과 파이썬 시각화 스크립트군(`plot_figures.py`, `generate_visualizations.py`, `generate_tables.py`, `plot_all.py`, `plot_utils.py`, `prepare_data.py`)을 전수 조사한 결과입니다.

### 🔍 핵심 발견 요약
1. **11대 산출물 파일 구비 현황**: 번호 접두사가 붙은 11대 파일(`1_ablation_study.png` ~ `11_hardware_feasibility_table.tex`)이 디렉토리 내에 생성되어 있음.
2. **❌ 200,000 스텝 표현 미흡**: `1_ablation_study.png`와 `3_reward_convergence.png`의 x축이 200,000 iterations가 아닌 각각 1~25 에피소드 및 1~100 에피소드로 표기되어 있음.
3. **❌ 수렴/안정성 2단계 시각화 부재**: 초기 수렴 구간(Convergence Phase)과 수렴 후 안정성 구간(Post-Convergence Stability Phase)을 구분하는 시각적 영역(음영, 수직선, 텍스트 주석 등)이 누락되어 있음.
4. **❌ 350 DPI PNG 규격 미달**: 현재 생성된 9개 PNG 파일 전체가 `300 DPI` (299.9994 DPI)로 렌더링되어 최신 요구사항인 `350 DPI`에 미달함.
5. **✅ 17개 모델 범례 및 스타일 준수**: 17개 베이스라인의 색상(#FF0000 ~ #B5B5B5), 투명도(REMO-DQN 1.0, 타 모델 0.6), 마커, 범례 정렬 순서는 `evaluation_plan.md §2`와 100% 일치함.
6. **❌ 스크립트 자동화 및 재현성 결함**: 스크립트 내부 `save_dual_figure` 함수가 번호 접두사(`1_`~`11_`) 없이 파일명을 저장하도록 되어 있어, 스크립트 재실행 시 번호 붙은 타겟 파일이 갱신되지 않는 결함이 존재함.

---

## 2. 11대 타겟 산출물 전수 조사 현황표

| 번호 | 타겟 산출물 파일명 | 포맷 | 파일 크기 | DPI / 행 수 | 데이터 소스 CSV | 요구사항 충족 여부 및 주요 이슈 |
|:---:|:---|:---:|:---:|:---:|:---|:---|
| **1** | `1_ablation_study.png` | PNG | 436.3 KB | 300 DPI | `ablation_study.csv` | ❌ **DPI 300(요구: 350)**, ❌ **x축 25 에피소드(요구: 200k steps)**, ❌ 2단계 미표시 |
| **2** | `2_optuna_sensitivity_table.csv`<br>`2_optuna_sensitivity_table.tex` | CSV<br>TeX | 2.3 KB<br>3.4 KB | 17 baselines | `optuna_sensitivity_table.csv` | ✅ 17개 모델 하이퍼파라미터 및 지표 완비 |
| **3** | `3_reward_convergence.png` | PNG | 983.6 KB | 300 DPI | `reward_convergence.csv` | ❌ **DPI 300(요구: 350)**, ❌ **x축 100 에피소드(요구: 200k steps)**, ❌ 2단계 미표시 |
| **4** | `4_tsne_clustering.png` | PNG | 227.4 KB | 300 DPI | `tsne_clustering.csv` | ❌ **DPI 300(요구: 350)**, ✅ 3개 군집 및 신뢰 타원체 표현 양호 |
| **5** | `5_moe_routing.png` | PNG | 285.2 KB | 300 DPI | `moe_routing.csv` | ❌ **DPI 300(요구: 350)**, ✅ 차량 밀도별 3개 전문가 활성화 분포 양호 |
| **6** | `6_cbr_trace.png` | PNG | 805.0 KB | 300 DPI | `cbr_trace.csv` | ❌ **DPI 300(요구: 350)**, ✅ 17개 모델 + 0.60 Target Line 양호 |
| **7** | `7_pdr_vs_density.png` | PNG | 539.2 KB | 300 DPI | `pdr_vs_density.csv` | ❌ **DPI 300(요구: 350)**, ✅ 17개 모델 밀도별 PDR 곡선 양호 |
| **8** | `8_aoi_vs_density.png` | PNG | 409.9 KB | 300 DPI | `aoi_vs_density.csv` | ❌ **DPI 300(요구: 350)**, ✅ 17개 모델 밀도별 AoI 곡선 양호 |
| **9** | `9_pdr_vs_distance.png` | PNG | 585.5 KB | 300 DPI | `pdr_vs_distance.csv` | ❌ **DPI 300(요구: 350)**, ✅ 17개 모델 거리별 PDR 곡선 양호 |
| **10** | `10_aoi_vs_distance.png` | PNG | 499.4 KB | 300 DPI | `aoi_vs_distance.csv` | ❌ **DPI 300(요구: 350)**, ✅ 17개 모델 거리별 AoI 곡선 양호 |
| **11** | `11_hardware_feasibility_table.csv`<br>`11_hardware_feasibility_table.tex` | CSV<br>TeX | 1.2 KB<br>2.0 KB | 11 models | `hardware_feasibility_table.csv` | ✅ MCU/OBU 탑재 적합성 및 Latency/FLOPs 표 완비 |

---

## 3. 심층 조사 및 문제점 분석 (Deep-Dive Findings)

### 3.1. [결함 1] 200,000 스텝 x축 명시적 표현 부재
- **현상**:
  - `data/models/REMO-DQN_convergence.csv` 파일에는 `Episode` (1~100)와 `Global_Step` (2,000 ~ 200,000)이 기록되어 있습니다 (에피소드당 2,000 steps).
  - 그러나 시각화 입력 데이터인 `data/reward_convergence.csv` 및 `visualizer/generate_visualizations.py` (Line 400, 425), `visualizer/plot_figures.py` (Line 98, 121)에서는 `ep = df["Episode"]`를 x축 데이터로 직접 사용하여 **x축이 1~100으로 표시**되고 x축 레이블도 `"Training Episode"`로 되어 있습니다.
  - `1_ablation_study.png` 역시 `ablation_study.csv`의 `Episode` 1~25 범위를 그대로 사용하여 **x축이 1~25로 표시**되어 있습니다.
- **요구사항 위반**:
  - `ORIGINAL_REQUEST.md` (2026-08-19T20:28:19+09:00): *"Update `plot_figures.py` and any related scripts so that the x-axis of `1_ablation_study.png` and `3_reward_convergence.png` is strictly set to represent 200,000 iterations."*
  - x축의 스케일이 0부터 200,000까지 (또는 $0 \sim 200\times 10^3$ Steps / $0 \sim 200$ k-Steps) 명시되어야 합니다.

### 3.2. [결함 2] 수렴 구간 및 수렴 후 안정성 구간 (2-Phase) 시각화 누락
- **현상**:
  - `1_ablation_study.png` 및 `3_reward_convergence.png` 그래프는 보상 곡선만 표시할 뿐, 모델이 급격히 학습되는 구간(예: $0 \sim 120,000$ steps)과 최적 정책에 도달하여 분산이 안정되는 구간(예: $120,000 \sim 200,000$ steps)을 분할하는 시각적 요소가 전무합니다.
- **요구사항 위반**:
  - `ORIGINAL_REQUEST.md`: *"The graphs must clearly visualize two phases: (1) The initial Convergence phase, and (2) The Post-Convergence Stability phase."*
  - 배경 영역에 `axvspan`을 적용하거나 수직 점선(`axvline`) 및 상단 라벨(Annotation)로 Phase I과 Phase II를 명확히 구분해야 합니다.

### 3.3. [결함 3] 350 DPI PNG 해상도 규격 미달 (300 DPI로 렌더링)
- **현상**:
  - `visualizer/plot_figures.py` (Line 29: `dpi=300`)
  - `visualizer/generate_visualizations.py` (Line 56: `'savefig.dpi': 300`, Line 293: `dpi=300`)
  - PIL로 검사한 결과 9개 PNG 파일 전체가 `DPI: (299.9994, 299.9994)` (300 DPI)로 저장되어 있습니다.
- **요구사항 위반**:
  - `ORIGINAL_REQUEST.md` 및 `DISPATCH.md`: *"Ensure all 11 target outputs are generated as 350 DPI PNGs"*
  - `dpi=350`으로 변경 및 재렌더링이 필수적입니다.

### 3.4. [결함 4] 번호 접두사 파일 저장 로직 불일치 및 재현성 문제
- **현상**:
  - `plot_figures.py`의 `save_dual_figure(fig, out_dir, basename)`은 `ablation_study.png` 등의 접두사 없는 파일명으로 저장합니다.
  - `generate_visualizations.py`의 `save_dual_figure(fig, basename)` 역시 접두사 없는 파일명으로 저장합니다.
  - 디렉토리에 존재하는 `1_ablation_study.png` 등은 이전에 수동 또는 별도 스크립트로 이름이 변경되어 복사된 것으로 추정되며, 현재 `python3 plot_all.py` 또는 `python3 generate_visualizations.py`를 실행할 경우 번호 접두사가 붙은 타겟 파일이 갱신되지 않습니다.
- **요구사항 위반**:
  - 스크립트 실행 한 번으로 `1_ablation_study.png` ~ `11_hardware_feasibility_table.tex` 파일이 직접 생성되도록 스크립트 저장 로직의 리팩토링이 필요합니다.

### 3.5. [결함 5] 데이터 준비 스크립트(`prepare_data.py`) 내 모의 수식 잔존
- **현상**:
  - `visualizer/prepare_data.py`의 `build_reward_convergence()` 및 `build_ablation_study()`에 `np.random.normal()` 및 인위적인 지수 감쇄 공식(`base_curve = -130000 + ...`)이 포함되어 있습니다.
- **요구사항 위반**:
  - `ORIGINAL_REQUEST.md` (2026-08-19T20:32:48+09:00): *"The Coder MUST NOT generate mock CSV files using numpy.random or mathematical formulas. ALL data must be extracted by actually running the SUMO simulation scripts and RL environments located in the codebase."*
  - `data/models/*.csv`에 이미 실제 200,000 스텝 학습 로그가 존재하므로, 이를 직접 파싱하여 CSV를 생성하도록 수정해야 합니다.

---

## 4. 17개 모델 스타일 및 범례 검증 결과

`evaluation_plan.md §2`에 정의된 17개 베이스라인의 순서, 색상, 라인 스타일, 마커, 투명도 매핑을 스크립트(`plot_utils.py`, `generate_visualizations.py`)와 비교 검증한 결과입니다.

| # | 모델명 | 표준 색상 코드 | Alpha | 라인 스타일 | 마커 | 스크립트 일치 여부 |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | **REMO-DQN (Proposed)** | `#FF0000` | 1.0 (Bold) | `-` (Solid) | `o` (Circle) | ✅ **100% Match** |
| 2 | **Fixed 10Hz** | `#0000FF` | 0.6 | `--` (Dashed) | `s` (Square) | ✅ **100% Match** |
| 3 | **ReactDCC (ETSI Standard)** | `#4D96FF` | 0.6 | `-.` (DashDot) | `^` (Triangle Up) | ✅ **100% Match** |
| 4 | **AdaptDCC (ETSI Standard)** | `#2A4B7C` | 0.6 | `:` (Dotted) | `v` (Triangle Down) | ✅ **100% Match** |
| 5 | **MoEDQN** | `#9B5DE5` | 0.6 | `-` (Solid) | `D` (Diamond) | ✅ **100% Match** |
| 6 | **MAPPO** | `#D783FF` | 0.6 | `-` (Solid) | `P` (Plus Filled) | ✅ **100% Match** |
| 7 | **PPO** | `#7A49A5` | 0.6 | `-` (Solid) | `p` (Pentagon) | ✅ **100% Match** |
| 8 | **SAC** | `#00FF00` | 0.6 | `-` (Solid) | `h` (Hexagon) | ✅ **100% Match** |
| 9 | **DDPG** | `#6BCB77` | 0.6 | `-` (Solid) | `X` (X Filled) | ✅ **100% Match** |
| 10 | **TD3** | `#2E8B57` | 0.6 | `-` (Solid) | `d` (Thin Diamond) | ✅ **100% Match** |
| 11 | **DuelingDQN** | `#FF9F1C` | 0.6 | `-` (Solid) | `<` (Triangle Left) | ✅ **100% Match** |
| 12 | **DoubleDQN** | `#FFD166` | 0.6 | `-` (Solid) | `>` (Triangle Right) | ✅ **100% Match** |
| 13 | **VanillaDQN** | `#D67229` | 0.6 | `-` (Solid) | `x` (X) | ✅ **100% Match** |
| 14 | **QLearning** | `#1A1A1A` | 0.6 | `-` (Solid) | `1` (Tri Down) | ✅ **100% Match** |
| 15 | **SARSA** | `#555555` | 0.6 | `-` (Solid) | `2` (Tri Up) | ✅ **100% Match** |
| 16 | **ActorCritic** | `#888888` | 0.6 | `-` (Solid) | `3` (Tri Left) | ✅ **100% Match** |
| 17 | **DecisionTransformer** | `#B5B5B5` | 0.6 | `-` (Solid) | `4` (Tri Right) | ✅ **100% Match** |

- **범례 정렬**: `apply_ordered_legend()` 함수가 구현되어 있어 1번부터 17번까지 완벽하게 정렬된 범례를 생성함.

---

## 5. 구체적 수정 제안 (Actionable Remediation Proposals)

### 5.1. 200,000 스텝 x축 및 2단계 시각화 코드 수정안 (Snippet)

`plot_figures.py` 및 `generate_visualizations.py`의 `plot_reward_convergence` 함수를 다음과 같이 수정할 것을 제안합니다:

```python
# [제안 수정안] 200,000 스텝 및 2-Phase 시각화 적용
def plot_reward_convergence(out_dir=VIS_DIR):
    df = pd.read_csv(os.path.join(DATA_DIR, "reward_convergence.csv"))
    fig, ax = plt.subplots(figsize=(11, 6))
    
    # x축을 Episode가 아닌 200,000 Steps로 스케일링 (100 episodes -> 200,000 steps)
    if "Global_Step" in df.columns:
        steps = df["Global_Step"].values
    elif "Step" in df.columns:
        steps = df["Step"].values
    else:
        steps = np.linspace(2000, 200000, len(df))
        
    # 2단계 시각화: 수렴 구간 (Phase I) 및 안정성 구간 (Phase II)
    conv_boundary = 120000  # 120k steps 기준 수렴점
    ax.axvspan(0, conv_boundary, color="#F0F4F8", alpha=0.6, label="_Phase1", zorder=0)
    ax.axvspan(conv_boundary, 200000, color="#E8F5E9", alpha=0.5, label="_Phase2", zorder=0)
    ax.axvline(x=conv_boundary, color="#666666", linestyle=":", linewidth=1.5, zorder=3)
    
    ax.text(conv_boundary * 0.45, ax.get_ylim()[0] + 5000, "Phase I: Exploration & Convergence", 
            fontsize=10, fontweight="bold", color="#1B365D", ha="center")
    ax.text(conv_boundary + (200000 - conv_boundary) * 0.5, ax.get_ylim()[0] + 5000, "Phase II: Steady-State Stability", 
            fontsize=10, fontweight="bold", color="#1B5E20", ha="center")

    # 17개 모델 플롯 (Reverse 순서로 REMO-DQN이 상단에 위치)
    for cfg in reversed(MODEL_CONFIGS):
        # ... (기존 플롯 로직 유지) ...
        ax.plot(steps, df[matched_col], color=cfg["color"], linestyle=cfg["linestyle"],
                linewidth=cfg["linewidth"], alpha=cfg["alpha"], zorder=cfg["zorder"], label=cfg["name"])

    ax.set_xlabel("Training Steps (Total: 200,000 Steps)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Cumulative Episode Reward", fontsize=11, fontweight="bold")
    ax.set_xlim(0, 200000)
    ax.set_title("Training Reward Convergence Across 17 Baselines (200,000 Iterations)", fontsize=13, fontweight="bold")
    # ...
```

### 5.2. 350 DPI 및 번호 접두사 통일 수정안

```python
# save_dual_figure 함수 개선
def save_dual_figure(fig, out_dir, basename, dpi=350):
    """350 DPI PNG 및 벡터 PDF 저장"""
    pdf_path = os.path.join(out_dir, f"{basename}.pdf")
    png_path = os.path.join(out_dir, f"{basename}.png")
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
    fig.savefig(png_path, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated -> {png_path} & {pdf_path} (DPI: {dpi})")
```
그리고 호출 시 번호 접두사를 명시하도록 수정:
- `save_dual_figure(fig, out_dir, "1_ablation_study", dpi=350)`
- `save_dual_figure(fig, out_dir, "3_reward_convergence", dpi=350)`
- `save_dual_figure(fig, out_dir, "4_tsne_clustering", dpi=350)`
- ...
- `save_dual_figure(fig, out_dir, "10_aoi_vs_distance", dpi=350)`

---

## 6. 결론

1. 현재 `visualizer/`에 존재하는 11대 타겟 산출물은 17개 베이스라인의 색상 및 범례 규격을 훌륭하게 준수하고 있으나, **(1) 200,000 스텝 x축 미반영, (2) 수렴/안정성 2-Phase 인디케이터 부재, (3) 300 DPI -> 350 DPI 미달, (4) 스크립트의 번호 접두사 자동 저장 누락**이라는 4가지 핵심 결함이 존재합니다.
2. 후속 Coder 에이전트는 본 보고서의 분석 결과와 수정 제안을 바탕으로 `prepare_data.py`, `plot_figures.py`, `generate_visualizations.py`, `generate_tables.py`, `plot_all.py`를 즉시 업데이트하고 11대 타겟 산출물을 350 DPI로 재렌더링해야 합니다.
