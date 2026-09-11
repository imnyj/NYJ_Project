# Performance Evaluation Management (성능 평가 관리 체계)

본 문서는 논문의 성능 평가에 있어 **일관성과 신뢰성**을 보장하기 위해 사용되는 13개의 비교 방안(Baselines), 도출된 데이터, 그리고 시각화(Graphs) 현황을 중앙에서 추적 관리합니다. 

---

## 1. 비교 방안 리스트 (Comparison Schemes) & 표준 색상 규격 (Standard Colors)
모든 그래프(Graph 1 ~ 7)에서 각 모델의 데이터 라인 및 바 그래프 색상은 아래 지정된 색상 규격(Color Code)을 강제 적용합니다. 제안 방안은 돋보이도록 빨간색(`red`)으로 고정합니다.

### Proposed Model (제안 방안)
1. **H-ST-MBAN** (제안 방안): `red` (#FF0000)

### Deep Learning Baselines
2. TabR: `magenta` (#FF00FF)
3. FTT (Feature Tokenizer + Transformer): `pink` (#FFC0CB)
4. MLP: `navy` (#000080)
5. LSTM: `purple` (#800080)
6. GRU: `brown` (#A52A2A)
7. ResNet: `cyan` (#00FFFF)

### Machine Learning Baselines
8. LR (Linear Regression): `gray` (#808080)
9. RF (Random Forest): `orange` (#FFA500)
10. XGB (XGBoost): `blue` (#0000FF)
11. CatBoost: `green` (#008000)
12. NGBoost: `olive` (#808000)
13. TabPFN: `teal` (#008080)

*Note: 기존 `ST-MBAN` 구조는 `H-ST-MBAN`으로 대체되었습니다. 만약 Ablation으로 기존 ST-MBAN을 그려야 할 경우 `darkred` (#8B0000)를 사용합니다.*

---

## 2. 시각화 및 그래프 도출 계획 (Visualization Management)
사용자가 지정한 7개의 그래프 목표입니다. 
모든 CSV 데이터는 `/home/imnyj/papers/paper1/data/` 에 저장되며, 
모든 시각화 그래프(PNG/PDF)는 `/home/imnyj/papers/paper1/figure/` 에 저장됩니다.

| Graph ID | Graph Description | Status | Target Data (csv) | Target Figure (png) |
| :--- | :--- | :---: | :--- | :--- |
| **G1** | Learning Curves (Pre-Training) | ⏳ 대기 (Optuna 후 재추출) | `goal_loss_by_epoch.csv` | `fig_learning_curves.png` |
| **G2** | Ablation Study (NoMB, NoAttn, NoRes) | ⏳ 대기 | `ablation_results.csv` | `fig_ablation.png` |
| **G3** | Pred vs True (산점도) | ⏳ 대기 | `goal_pred_vs_true_all.csv` | `fig_pred_vs_true.png` |
| **G4** | Queue size analysis | ⏳ 대기 | `round_size_results.csv` | `fig_queue_size_analysis.png` |
| **G5** | 모델별 Round에 따른 MAE (fine-tuning) | ⏳ 대기 | `goal_mae_by_round.csv` | `fig_mae_by_round.png` |
| **G6** | 모델별 Average Access Delay, Wasted Traffic, Cache Hit | ⏳ 대기 | `cache_metrics_avg.csv` | `fig_cache_metrics_avg.png` |
| **G7** | 모델별 Density에 따른 Access Delay, Wasted Traffic, Cache Hit | ⏳ 대기 | `cache_metrics_by_density.csv` | `fig_cache_metrics_by_density.png` |

---

## 3. 데이터 및 시각화 파일 저장 규칙
1. **Data**: 모든 데이터 추출 스크립트는 시각화를 그리기 전에 반드시 `/home/imnyj/papers/paper1/data/` 경로에 `.csv` 형태로 결과를 먼저 저장해야 합니다.
2. **Figure**: 시각화 스크립트는 Data 폴더의 CSV를 읽어들인 후, `/home/imnyj/papers/paper1/figure/` 경로에 그래프를 출력해야 합니다.
