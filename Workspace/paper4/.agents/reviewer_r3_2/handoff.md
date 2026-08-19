# [Reviewer 2 최종 검토 보고서] Paper4 시각화 산출물, 분석 보고서 및 LaTeX 정합성 독립·적대적 검토

- **검토자**: Reviewer 2 (독립 검토관 및 적대적 비평가, `reviewer_r3_2`)
- **수행 일시**: 2026-08-19T17:31:00+09:00
- **검토 대상**:
  1. 시각화 코드 및 산출물 (`visualizer/plot_utils.py`, `visualizer/generate_visualizations.py`, `visualizer/plot_figures.py`, `visualizer/plot_all.py`, PNG/PDF 산출물 11종)
  2. MoE/t-SNE 심층 분석 보고서 (`analysis_report.md`) vs 원시 데이터 (`data/moe_routing.csv`, `data/tsne_clustering.csv`)
  3. 생성된 LaTeX 표 및 데이터 정합성 (`optuna_sensitivity_table.tex`, `hardware_feasibility_table.tex`, `optuna_sensitivity_table.csv`, `hardware_feasibility_table.csv`)
- **최종 판정**: **REQUEST_CHANGES (수정 요구)**

---

## 1. 관측 사실 (Observation)

### 1.1 시각화 규격 및 산출물 교차 검증 (Visualizer Compliance)
- **`visualizer/plot_utils.py` (L52–223) 및 `visualizer/generate_visualizations.py` (L63–234)**:
  - `evaluation_plan.md §2`에 명시된 17개 비교 모델의 Hex 색상이 100% 일치하게 정의됨:
    1. REMO-DQN: `#FF0000` (alpha=1.0, linewidth=2.4~2.5, bold, zorder=20)
    2. Fixed 10Hz: `#0000FF` (alpha=0.6, linestyle='--')
    3. ReactDCC: `#4D96FF` (alpha=0.6, linestyle='-.')
    4. AdaptDCC: `#2A4B7C` (alpha=0.6, linestyle=':')
    5. MoEDQN: `#9B5DE5` (alpha=0.6)
    6. MAPPO: `#D783FF` (alpha=0.6)
    7. PPO: `#7A49A5` (alpha=0.6)
    8. SAC: `#00FF00` (alpha=0.6)
    9. DDPG: `#6BCB77` (alpha=0.6)
    10. TD3: `#2E8B57` (alpha=0.6)
    11. DuelingDQN: `#FF9F1C` (alpha=0.6)
    12. DoubleDQN: `#FFD166` (alpha=0.6)
    13. VanillaDQN: `#D67229` (alpha=0.6)
    14. QLearning: `#1A1A1A` (alpha=0.6)
    15. SARSA: `#555555` (alpha=0.6)
    16. ActorCritic: `#888888` (alpha=0.6)
    17. DecisionTransformer: `#B5B5B5` (alpha=0.6)
  - `apply_ordered_legend` 함수가 범례 핸들 및 라벨을 1~17번 인덱스 순으로 엄격히 정렬하도록 구현됨.
  - `visualizer/` 디렉토리에 11개 대상 결과물(벡터 PDF 및 300 DPI PNG, CSV, TeX 총 22개 파일)이 모두 실존하고 정상 생성됨.

### 1.2 `analysis_report.md` 수학적 공식 및 데이터 정합성
- **수학 공식 정합성 (`analysis_report.md` §2.1, §3.1)**:
  - OBU 관측 상태 벡터 $s_t \in \mathbb{R}^5$, 2-block ResNet 특징 추출기 $f_\theta(s_t) \in \mathbb{R}^{128}$, Softmax Gating 가중치 $g_k(s_t)$, Mean-centered Dueling 복합 $Q(s_t, a)$, t-SNE KL 발산 목적 함수가 수학적으로 정확하고 결함 없이 기술됨.
- **MoE 활성화 데이터 정합성 (`analysis_report.md` §2.2 vs `data/moe_routing.csv`)**:
  - 밀도 20~160 veh/km 구간에 대한 Expert 1, 2, 3의 활성화 비율(%) 표가 `data/moe_routing.csv`의 수치와 100% 완벽히 일치함.
- **t-SNE 클러스터 좌표 불일치 (`analysis_report.md` §3.2 vs `data/tsne_clustering.csv`)**:
  - `analysis_report.md` L145, L148, L151에 명시된 클러스터 중심 좌표:
    - Low Traffic: $(\mu_x, \mu_y) \approx (-0.42, 0.18)$
    - Medium Traffic: $(\mu_x, \mu_y) \approx (0.15, -0.05)$
    - High Traffic: $(\mu_x, \mu_y) \approx (0.85, -0.22)$
  - `data/tsne_clustering.csv`의 실제 150개 샘플(클러스터별 50개) 산술 평균 좌표:
    - Low Traffic: $(\mu_x, \mu_y) = (-0.225, 0.084)$
    - Medium Traffic: $(\mu_x, \mu_y) = (5.018, 5.151)$
    - High Traffic: $(\mu_x, \mu_y) = (1.961, 4.979)$
  - Medium 및 High Traffic 클러스터의 실제 좌표계와 보고서 기술 수치 간의 명백한 불일치 확인.

### 1.3 LaTeX 표 문법 및 데이터 정합성 (`optuna_sensitivity_table.tex`, `hardware_feasibility_table.tex`)
- **`optuna_sensitivity_table.tex` LaTeX 문법 치명적 오류 (L13–26)**:
  - 3번째 열(`Optimal Hyperparameter Vector` / `Tuned Hyperparameters`) 내에 `batch_size`, `num_experts`, `top_k`, `eps_clip`, `k_epochs`, `lr_actor`, `lr_critic`, `policy_delay`, `target_noise`, `buffer_size`, `eps_decay`, `n_heads`, `n_layers`, `context_len` 등 **언더스코어(`_`)가 이스케이프 없이 텍스트 모드에 삽입**되어 있음.
  - LaTeX 컴파일러 실행 시 `! Missing $ inserted` 에러로 인한 컴파일 중단(Fatal Compilation Error) 유발.
- **`hardware_feasibility_table.tex` 수식 기호 이스케이프 누락 (L21)**:
  - 9행 `QLearning / SARSA`의 MACs/FLOPs 열에 `< 0.01 M`이 수식 모드(`$< 0.01$~M`) 또는 텍스트 기호(`\textless`) 없이 원시 부등호(`<`)로 작성되어 비정상 폰트 렌더링(예: 스페인어 역느낌표 `¡`) 유발.
- **`optuna_sensitivity_table.csv` 및 `prepare_data.py` 데이터 무결성 결함 (Integrity / Placeholder Artifact)**:
  - `visualizer/prepare_data.py` L156–158 및 `optuna_sensitivity_table.csv` L15–17:
    - `Fixed 10Hz`, `ReactDCC`, `AdaptDCC` 모델의 성능 수치가 모두 `Mean PDR (%) = 91.91%`, `Mean AoI (ms) = 145.17`, `Mean CBR = 0.086`으로 **동일하게 복사-붙여넣기(Dummy/Facade Pattern)** 처리되어 있음.
    - 고정 10Hz 전송(Fixed 10Hz)은 고밀도 환경에서 CSMA/CA MAC 브로드캐스트 스톰으로 인해 PDR이 30~50% 수준으로 붕괴하고 CBR이 0.85 이상으로 폭주해야 하나, 표에서는 91.91% PDR 및 0.086 CBR로 잘못 기재됨.
    - 또한 모든 모델의 `Mean CBR`이 실제 채널 점유율(0.3~0.8) 대비 1/10 수준인 `0.028 ~ 0.086`으로 스케일링 왜곡되어 있음 (`cbr_trace.csv` 및 `analysis_report.md`의 0.584~0.892와 모순).

---

## 2. 논리적 추론 체계 (Logic Chain)

1. **시각화 계획 준수도**:
   - `plot_utils.py` 및 `generate_visualizations.py`의 구현 코드가 `evaluation_plan.md §2`의 17개 모델 Hex 색상, 투명도 차등(REMO-DQN 1.0, 기타 0.6), 마커, 선 스타일, 범례 정렬 함수를 충실히 반영하고 있음을 확인하였다.
2. **LaTeX 문법 결함과 논문 빌드 실패 위험**:
   - `optuna_sensitivity_table.tex`에 포함된 비이스케이프 언더스코어(`_`)는 표준 LaTeX 파서에서 텍스트 모드 서브스크립트 파싱 오류를 반드시 일으키며, IEEE 저널 템플릿과의 통합 컴파일을 불가능하게 만든다. 이는 즉시 수정되어야 하는 치명적(Critical) 결함이다.
3. **데이터 무결성 및 복사-붙여넣기 왜곡 (Data Integrity Defect)**:
   - `optuna_sensitivity_table.csv` 구축 코드(`prepare_data.py`)에서 표준 기법들(Fixed 10Hz, ReactDCC, AdaptDCC)의 결과 지표에 고정 더미값(91.91%, 145.17ms, 0.086)이 하드코딩/복제 입력되었다. 이는 `analysis_report.md` §4의 실측치(Fixed 10Hz PDR 48.20%, AoI 110ms, CBR 0.892; ReactDCC PDR 72.40%) 및 `pdr_vs_density.csv`, `cbr_trace.csv`의 추세와 정면으로 충돌하여 논문의 데이터 정합성을 심각하게 훼손한다.
4. **t-SNE 클러스터 기술 정합성**:
   - `analysis_report.md`의 t-SNE 수학적 설명과 정성적 분리성 해석은 우수하나, 기술된 중심 좌표$(\mu_x, \mu_y)$가 원시 데이터 파일(`tsne_clustering.csv`)의 실제 군집 중심(Low: -0.23, 0.08 / Mid: 5.02, 5.15 / High: 1.96, 4.98)과 괴리되어 있으므로 수치 정정이 요구된다.

---

## 3. 주의사항 및 한계 (Caveats)

- 본 검토는 제어 규칙에 따라 소스코드를 직접 수정하지 않고 Read-only 방식으로 결함을 식별하고 증거를 수집하였습니다.
- 시스템 환경에 `pdflatex` 바이너리가 직접 설치되어 있지 않으나, Python 기반 AST 및 구문 분석기를 통해 TeX 문법 오류(비이스케이프 언더스코어, 부등호)를 완벽히 입증하였습니다.
- 시각화 그래프 자체의 심미성과 색상/선스타일 매핑은 계획서와 일치하므로, 데이터 테이블 및 텍스트 기술의 수치 동기화에 집중하여 보완이 이루어져야 합니다.

---

## 4. 최종 결론 및 조치 요구사항 (Conclusion & Action Items)

### [최종 판정]: **REQUEST_CHANGES**

### 주요 지적 사항 목록 (Findings)

1. **[Critical] `optuna_sensitivity_table.tex` 내 비이스케이프 언더스코어(`_`) 전면 수정**
   - **위치**: `visualizer/optuna_sensitivity_table.tex`, `visualizer/generate_visualizations.py` L382, `visualizer/generate_tables.py` L55, `visualizer/prepare_data.py` L192
   - **문제**: `batch_size`, `num_experts`, `top_k`, `eps_clip`, `k_epochs`, `lr_actor`, `lr_critic`, `policy_delay`, `target_noise`, `buffer_size`, `eps_decay`, `n_heads`, `n_layers`, `context_len`의 언더스코어가 이스케이프되지 않아 LaTeX 컴파일 에러 발생.
   - **조치**: 모든 하이퍼파라미터 문자열 생성 로직에 `.replace('_', r'\_')` 또는 정규식을 적용하여 `batch\_size`, `num\_experts` 등으로 출력되도록 수정.

2. **[Critical - Data Integrity] `optuna_sensitivity_table.csv` 및 `prepare_data.py` 데이터 정합성 교정**
   - **위치**: `visualizer/prepare_data.py` L141–173, `data/optuna_sensitivity_table.csv`, `visualizer/optuna_sensitivity_table.csv`
   - **문제**: Fixed 10Hz, ReactDCC, AdaptDCC 등의 PDR(91.91%), AoI(145.17), CBR(0.086)이 더미 복제값으로 입력되어 있으며, 전체 CBR 값이 10배 축소 표기됨.
   - **조치**: `analysis_report.md` 및 `data/evaluation/`, `data/cbr_trace.csv`, `data/pdr_vs_density.csv`의 실제 평균값(Fixed 10Hz: PDR ~48.2%, AoI ~110ms, CBR ~0.892; ReactDCC: PDR ~72.4%, AoI ~285ms, CBR ~0.648; AdaptDCC: PDR ~78.9%, AoI ~240ms, CBR ~0.612 등)으로 정확히 교체 동기화.

3. **[Major] `analysis_report.md` t-SNE 클러스터 중심 좌표 수치 동기화**
   - **위치**: `analysis_report.md` §3.2 (L145, L148, L151)
   - **문제**: 실제 `data/tsne_clustering.csv`의 산술 평균 좌표와 불일치 (Low: -0.23, 0.08 / Mid: 5.02, 5.15 / High: 1.96, 4.98).
   - **조치**: 본문 내 표기된 중심 좌표 수치를 실제 데이터의 평균 및 분산 수치로 정정.

4. **[Minor] `hardware_feasibility_table.tex` 부등호 수식 기호 이스케이프**
   - **위치**: `visualizer/hardware_feasibility_table.tex` L21, `visualizer/generate_tables.py` L95, `visualizer/generate_visualizations.py` L711
   - **문제**: `< 0.01 M` 원시 부등호 작성으로 인한 폰트 결함 가능성.
   - **조치**: `$< 0.01$~M` 또는 `\textless~0.01~M`으로 포맷팅 개선.

---

## 5. 독립적 검증 방법 (Verification Method)

1. **LaTeX 구문 및 언더스코어 검증 명령**:
   ```bash
   python3 -c "
   with open('/home/imnyj/Workspace/paper4/visualizer/optuna_sensitivity_table.tex') as f:
       lines = f.readlines()
   errors = [l.strip() for l in lines if '_' in l.replace(r'\_', '')]
   print('Unescaped underscores count:', len(errors))
   assert len(errors) == 0, 'Unescaped underscores still exist!'
   "
   ```
2. **Optuna 표 데이터 정합성 검증 명령**:
   ```bash
   python3 -c "
   import pandas as pd
   df = pd.read_csv('/home/imnyj/Workspace/paper4/data/optuna_sensitivity_table.csv')
   print(df[['Method', 'Mean PDR (%)', 'Mean AoI (ms)', 'Mean CBR']])
   # Fixed 10Hz PDR should NOT be 91.91% in dense V2X
   fixed_pdr = df[df['Method'] == 'Fixed 10Hz']['Mean PDR (%)'].values[0]
   print('Fixed 10Hz PDR:', fixed_pdr)
   assert fixed_pdr < 60.0, 'Fixed 10Hz PDR must reflect real congestion degradation!'
   "
   ```
3. **t-SNE 군집 좌표 산출 검증 명령**:
   ```bash
   python3 -c "
   import pandas as pd
   df = pd.read_csv('/home/imnyj/Workspace/paper4/data/tsne_clustering.csv')
   print(df.groupby('Cluster')[['x', 'y']].agg(['mean', 'std']))
   "
   ```
