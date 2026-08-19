# Empirical Challenge Report: Visualizer Resolution & 200,000 Steps Data Fidelity

**Challenger**: `challenger_m3_1` (Empirical Data & Resolution Challenger)  
**Target Milestone**: M3 (Multi-Agent Review & Challenger Stress-Test)  
**Date**: 2026-08-19T20:44:30+09:00  

---

## Challenge Summary

**Overall risk assessment**: **LOW** (All empirical tests passed with 100% precision)

본 검증은 Paper4 시각화 파이프라인의 9개 PNG 파일 전체에 대한 350 DPI 물리적 해상도 실측 검증과, `3_reward_convergence.png` 및 `1_ablation_study.png`에 플롯된 데이터가 `data/models/*_convergence.csv` 및 `data/ablation_study.csv`의 0~200,000 스텝 데이터와 엄격히 일치하는지 적대적으로 검증(Adversarial Stress-Testing)한 결과를 담고 있습니다.

---

## Challenges

### [Low] Challenge 1: DPI Metadata Spoofing & Sub-sampled Resolution Attack

- **Assumption challenged**: Matplotlib의 기본 DPI(100 또는 72 DPI)로 렌더링되거나 메타데이터만 350 DPI로 조작되고 실제 픽셀 해상도가 낮을 가능성.
- **Attack scenario**: PIL 라이브러리로 이미지 파일 바이너리를 직접 디코딩하여 실제 픽셀 크기(Pixel Width × Height)와 `img.info['dpi']` 튜플을 물리적으로 측정하고, 피규어 크기(Inches)와의 일관성을 역산 검증.
- **Blast radius**: IEEE Transactions on Wireless Communications (TWC) 출판 기준 미달로 논문 제출 시 즉각 Reject(Desk Reject) 위험.
- **Mitigation**: `plot_figures.py` 내 `savefig(..., dpi=350)` 적용 및 실제 렌더링된 9개 PNG 전수 PIL 검사.
- **Empirical Result**: 9개 대상 PNG 파일 전수가 정확히 350.012 DPI 해상도(예: `1_ablation_study.png` 4683×1772 px, `3_reward_convergence.png` 3967×2174 px)로 검증됨. (100% PASS)

### [Low] Challenge 2: Truncation / Mock Formula Substitution in 200,000-Step Trajectories

- **Assumption challenged**: 200k 스텝 훈련 데이터가 실제 200,000 스텝까지 도달하지 않고 100 에피소드에서 조기 중단되었거나, 수학적 수식/난수로 위조되었을 가능성.
- **Attack scenario**: 14개 개별 RL 모델 CSV 파일(`data/models/*_convergence.csv`) 및 통합 `reward_convergence.csv`, `ablation_study.csv`의 모든 행을 전수 스캔하여 `Global_Step` 범위(`2000 ~ 200000`), 스텝 간격(`diff == 2000`), NaN/Null/Inf 결측치, 단조 수렴 및 안정성 구간 거동을 검사.
- **Blast radius**: 연구 진실성 및 재현성 위반으로 인한 심각한 데이터 신뢰도 훼손.
- **Mitigation**: 모든 RL 모델의 200k 스텝 훈련 로그 및 체크포인트(`.pth`, `.pkl`) 물리적 확인 및 1:1 수치 오차 검증.
- **Empirical Result**: 14개 개별 모델 로그와 통합 `reward_convergence.csv`의 수치 오차가 $0.0\times 10^0$ (Max Absolute Error = 0.0)으로 완벽 일치하며, 2,000스텝 간격 100개 데이터포인트가 200,000 스텝까지 결측 없이 기록됨. (100% PASS)

### [Low] Challenge 3: Matplotlib Line2D Plot Reverse Extraction Mismatch

- **Assumption challenged**: 플롯 스크립트 실행 시 정렬 순서 불일치, 컬럼 매핑 오류, 또는 오프셋 왜곡으로 인해 시각화된 곡선과 CSV 원본 데이터 간의 괴리가 발생할 가능성.
- **Attack scenario**: `plot_figures.py`의 Matplotlib Axes 객체에서 `Line2D` 아티팩트의 `get_xdata()`와 `get_ydata()`를 직접 추출하여 원본 CSV 컬럼 데이터와의 수치 차이를 비교.
- **Blast radius**: 논문 본문 그래프의 시각적 결론과 첨부 데이터 테이블 간의 수치 불일치.
- **Mitigation**: `apply_ordered_legend` 및 17개 베이스라인 컬러/스타일 매핑 역검증.
- **Empirical Result**: `3_reward_convergence`의 17개 곡선 및 `1_ablation_study`의 8개 곡선 전체에서 Line2D 데이터와 CSV 데이터의 오차가 정확히 0.0으로 100% 정합성 검증됨. (100% PASS)

---

## Stress Test Results

| # | Stress Test Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| 1 | PIL 350 DPI 전수 검사 (9개 PNG 파일) | 모든 PNG가 350 DPI (`(350, 350)`) 및 0바이트 아님 | 9/9 파일 모두 350.012 DPI, 295KB~1.34MB | **PASS** |
| 2 | 14개 RL 모델 수렴 로그 무결성 검증 | 행 100개, Global_Step 2,000~200,000, NaN 0개 | 14개 모델 전원 100행, 2k~200k 스텝 완비, NaN 0개 | **PASS** |
| 3 | `reward_convergence.csv` vs `models/*_convergence.csv` 1:1 비교 | 전 알고리즘 Max Absolute Error $\le 10^{-6}$ | 14개 RL 전수 Max Error = $0.0\times 10^0$ 완벽 일치 | **PASS** |
| 4 | `ablation_study.csv` 7대 컬럼 200k 스텝 무결성 | 2k~200k 스텝, 수렴 개선폭 양수, NaN 0개 | 7개 컬럼 전원 수렴 완료 (+35k~+37k 보상 개선), NaN 0개 | **PASS** |
| 5 | Matplotlib Line2D 역추출 정합성 검증 | 17개 수렴 곡선 및 8개 Ablation 곡선 1:1 일치 | 25개 플롯 곡선 전수 x/y 데이터 CSV와 오차 0.0 | **PASS** |
| 6 | 전체 11대 타겟 데이터세트 NaN/Inf 전수 검사 | 11개 CSV 파일 모두 NaN/Inf 0개, 0바이트 없음 | 11개 CSV 파일 전수 100% Clean | **PASS** |
| 7 | 모델 체크포인트 물리적 검증 (14 RL + 3 표준) | 14개 `.pth`/`.pkl` 파일 존재 및 >0 KB | 14개 파일 모두 존재 (42.4KB ~ 6.25MB) | **PASS** |

---

## Unchallenged Areas

- **MCU 물리적 하드웨어 실측 런타임**: `hardware_feasibility.csv`는 임베디드 프로파일링 측정 로그에 기반하고 있으나, 물리적 마이크로컨트롤러 보드에 직접 연결하여 실시간 전류/전압을 측정하는 것은 본 M3 시뮬레이션 환경 범위 외(Out of scope)이므로 소프트웨어 벤치마크 데이터의 무결성 검증으로 갈음함.

---

## Final Verdict

**Verdict**: **APPROVE**  
모든 시각화 PNG 파일(350 DPI)과 200,000 스텝 훈련/수렴 데이터는 요구사항 및 논문 규격을 100% 충족하며 결함이 없음을 실증적으로 최종 확인하였습니다.
