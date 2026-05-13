
## [2026-04-15] Paper Draft v1.0 작성 완료

### 작성된 섹션
1. ✅ Abstract + Keywords
2. ✅ Section I: Introduction (IEEEPARstart, 3 contributions, paper organization)
3. ✅ Section II: Related Work (3 subsections + comparison table*)
4. ✅ Section III: System Model and Problem Formulation
   - 3.1 Vehicular Network Environment
   - 3.2 Channel Model (path loss, Rician, Nakagami, SINR, Tx success)
   - 3.3 C-V2X MAC Model (SPS, collision, CBR)
   - 3.4 NDN-AoI Formulation (Theorem 1, Theorem 2 with proofs)
   - 3.5 CMDP Formulation (state, action, reward, constraints, Lagrangian)
5. ✅ Section IV: MAFAC Algorithm
   - 4.1 Factored Actor-Critic Architecture
   - 4.2 Policy Gradient with Lagrangian Advantage
   - 4.3 Federated Critic Aggregation (5-step protocol)
   - 4.4 Convergence Analysis (Theorems 3, 4, Proposition 1)
   - Algorithm 1 pseudocode
6. ✅ Section V: Performance Evaluation
   - 5.1 Simulation Setup (Table: parameters, 5 baselines)
   - 5.2 Model Verification (Theorems 1,2 vs simulation)
   - 5.3 Convergence Analysis
   - 5.4 Performance Comparison (Table: S1 density results)
   - 5.5 Ablation Study (Table: component analysis)
   - 5.6 Communication Overhead
7. ✅ Section VI: Conclusion
8. ✅ Bibliography (34 references from bibitem.tex)
9. ✅ Author Biography

### 사용된 cite 키
Lim2024, Khan2024, Kaul2012, Sun2019, Dhara2023, Wang2024a, Silva2024, Wang2024b, Ning2024

### 논문 통계
- 전체 길이: ~50,770 characters
- 예상 페이지: ~14 pages (IEEE two-column)
- 테이블: 4개 (comparison, sim_params, s1_results, ablation)
- 알고리즘: 1개 (MAFAC pseudocode)
- 수식: ~30개
- Theorems: 4개 (Theorem 1-4) + Proposition 1

### 미완성/TODO 항목
- Figure 삽입: 그래프 PNG 생성 후 주석 해제 필요
- Proofreader 교정 필요
- 일부 cite 키가 bibitem.tex에 없을 수 있음 (Kaul2012, Sun2019, Ning2024 확인 필요)
