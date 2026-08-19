# Milestone 1 구현 완료 보고서 (Implementation Report)

- **작성 에이전트**: `teamwork_preview_worker_m1` (Roles: implementer, qa, specialist)
- **작업 디렉토리**: `/home/imnyj/Workspace/paper4/latex/`
- **타깃 저널**: *IEEE Transactions on Wireless Communications (TWC)*
- **일시**: 2026-08-18

---

## 1. 과업 개요 및 구현 요약

Milestone 1(참고문헌 BibTeX 및 LaTeX 인프라 구축)을 성공적으로 완수하였습니다. 국문 초안(`/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md`) 및 마일스톤 명세서(`m1_spec.md`)의 요구사항을 100% 충족하여 출판급 환경을 조성하였습니다.

### 주요 구현 산출물 목록
1. **디렉토리 및 환경 구조화**:
   - `/home/imnyj/Workspace/paper4/latex/` (메인 작업 공간)
   - `/home/imnyj/Workspace/paper4/latex/figures/` (고해상도 시각화 자산 보관)
   - `/home/imnyj/Workspace/paper4/latex/etc/scripts/` (빌드/검증/테스트 도구 격리 보관)
   - `/home/imnyj/Workspace/paper4/latex/etc/logs/` (로그 디렉토리 격리 보관)

2. **공식 LaTeX 클래스 배치**:
   - `IEEEtran.cls` (IEEE 공식 V1.8b, 281,957 bytes)를 `/home/imnyj/Workspace/paper1/writer/IEEEtran.cls`로부터 복사 및 정상 배치.

3. **9종 시각화 플롯 자산 배치 및 표준 명명 동기화**:
   - 원본 플롯 9종(`1_reward_convergence.png`, `7_cbr_trace.png`, `8_pdr_vs_density.png`, `9_aoi_vs_density.png`, `10_pdr_vs_distance.png`, `5_hardware_feasibility.png`, `2_ablation_study.png`, `3_moe_routing.png`, `4_tsne_clustering.png`) 복사 완료.
   - 표준화된 별칭(`fig1_reward_convergence.png` ~ `fig9_tsne_clustering.png`) 9종 동기화 생성 완료 (총 18개 이미지 파일).

4. **27편 전수 참고문헌 BibTeX 데이터베이스 (`references.bib`)**:
   - 표준 PascalCase 인용 키(`AuthorYearKeyword`) 적용 완료.
   - 필수 메타데이터(저자명, 제목, 수록처, 권, 호, 페이지, 연도, DOI 등) 완결성 검증.
   - 중복 키 0건, 문법 오류 0건 검증 완료.

5. **자동화 빌드 및 검증 인프라 (`Makefile`, `validate_latex.py`, `test_m1_infrastructure.py`)**:
   - `Makefile`: `validate`, `zip`, `compile`, `clean` 타깃 완비.
   - `validate_latex.py`: 다계층(Tier 1~4) 정밀 무결성 검증기 구현 (`chmod +x` 적용).
   - `test_m1_infrastructure.py`: pytest 기반 무결성 단위 테스트 슈트 (6개 테스트 전수 통과).

---

## 2. 세부 산출물 검증 결과

### 2.1 BibTeX 인용 키 27종 전수 매핑 검증

| 번호 | 표준 Citation Key | 유형 | 주요 저자 / 기구 | 논문 / 표준 제목 |
|:---:|:---|:---:|:---|:---|
| [1] | `Arena2019Overview` | article | F. Arena, G. Pau | An Overview of Vehicular Communications |
| [2] | `Kenney2011DSRC` | article | J. B. Kenney | Dedicated Short-Range Communications (DSRC) Standards in the United States |
| [3] | `ETSI_EN_302_637_2` | standard | ETSI | ITS; Basic Set of Applications; Part 2: Specification of CAM |
| [4] | `SAE_J2945_1` | standard | SAE International | On-Board System Requirements for V2V Safety Communications |
| [5] | `ETSI_TS_102_687` | standard | ETSI | ITS; DCC Methods: Part 1: Architecture and Mechanisms |
| [6] | `Zheng2022Age` | article | X. Zheng, C. Chen, X. Guan | Age-of-Information-Oriented Congestion Control for Vehicular Networks |
| [7] | `Liu2024Age` | article | Y. Liu, C. Chen, X. Guan | Age of Information and Energy Minimization in Vehicular Networks Using DRL |
| [8] | `ETSI_TS_103_175` | standard | ETSI | ITS; Cross Layer DCC Management Entity for Operation in ITS G5A and G5B |
| [9] | `Bansal2013LIMERIC` | article | G. Bansal, J. B. Kenney, C. E. Rohrs | LIMERIC: A Linear Adaptive Message Rate Algorithm for DSRC Congestion Control |
| [10] | `Ye2019Deep` | article | H. Ye, G. Y. Li, B.-H. F. Juang | Deep Reinforcement Learning Based Resource Allocation for V2V Communications |
| [11] | `Hu2021Deep` | article | X. Hu, S. Liu, R. Chen, et al. | Deep Reinforcement Learning for Resource Allocation: A Cross-Layer Approach |
| [12] | `Wang2023Multi` | article | Q. Wang, Y. Liu, J. Chen, et al. | Multi-Agent DRL for Cooperative Resource Allocation in Dense V2X Networks |
| [13] | `Mnih2015Human` | article | V. Mnih, K. Kavukcuoglu, D. Silver, et al. | Human-Level Control Through Deep Reinforcement Learning (Nature) |
| [14] | `VanHasselt2016Deep` | inproceedings | H. van Hasselt, A. Guez, D. Silver | Deep Reinforcement Learning with Double Q-Learning (AAAI) |
| [15] | `Wang2016Dueling` | inproceedings | Z. Wang, T. Schaul, M. Hessel, et al. | Dueling Network Architectures for Deep Reinforcement Learning (ICML) |
| [16] | `Yu2022Surprising` | inproceedings | C. Yu, A. Velu, E. Vinitsky, et al. | The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games (NeurIPS) |
| [17] | `Lowe2017Multi` | inproceedings | R. Lowe, Y. Wu, A. Tamar, et al. | Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments (NeurIPS) |
| [18] | `Rashid2018QMIX` | inproceedings | T. Rashid, M. Samvelyan, C. Schroeder, et al. | QMIX: Monotonic Value Function Factorisation for Deep MARL (ICML) |
| [19] | `Chen2021Decision` | inproceedings | L. Chen, K. Lu, A. Rajeswaran, et al. | Decision Transformer: Reinforcement Learning via Sequence Modeling (NeurIPS) |
| [20] | `Janner2021Offline` | inproceedings | M. Janner, Q. Li, S. Levine | Offline Reinforcement Learning as One Big Sequence Modeling Problem (NeurIPS) |
| [21] | `Shazeer2017Outrageously` | inproceedings | N. Shazeer, A. Mirhoseini, K. Maziarz, et al. | Outrageously Large Neural Networks: Sparsely-Gated MoE Layer (ICLR) |
| [22] | `Xu2025Mixture` | article | Y. Xu, J. Wang, R. Zhang, et al. | Mixture of Experts for Decentralized GenAI and RL in Wireless Networks (COMST) |
| [23] | `Zhang2026Generalizable` | article | Z. Zhang, Y. Xiao, Z. Han, H. V. Poor | Generalizable Multiple Access with Meta-RL and MoE for Heterogeneous Wireless |
| [24] | `Kang2024Task` | article | J. Kang, D. Niyato, Z. Xiong, et al. | Task-Oriented MoE for Resource Allocation in Multi-Modal Edge Intelligence (JSAC) |
| [25] | `Du2025Generative` | article | H. Du, J. Wang, D. Niyato, et al. | Generative AI-Enabled Edge Network Slicing with Decentralized MoE (IEEE Netw.) |
| [26] | `Park2025Ensemble` | article | S. Park, D. Kim | Ensemble Deep Q-Learning for DCC in Dense Vehicular Networks (LWC) |
| [27] | `Bhattacharyya2024Hybrid` | article | S. Bhattacharyya, P. Kumar, S. Darshi, et al. | Hybrid Relaying Based Cross Layer MAC Protocol Using Variable Beacon (TVT) |

---

## 3. 검증 명령어 및 실행 결과

### 3.1 `validate_latex.py` 검증
```bash
$ python3 /home/imnyj/Workspace/paper4/latex/etc/scripts/validate_latex.py
================================================================
 IEEE TWC LaTeX Conversion Verification Suite (Milestone 1-5)
 Target Directory: /home/imnyj/Workspace/paper4/latex
================================================================
[*] Tier 1: Validating Base Assets and Directory Structure...
  [OK] IEEEtran.cls found (281957 bytes)
  [OK] references.bib found (11247 bytes)
  [OK] figures directory found
    [OK] Figure asset: 1_reward_convergence.png (50437 bytes)
    [OK] Figure asset: 7_cbr_trace.png (86380 bytes)
    [OK] Figure asset: 8_pdr_vs_density.png (29703 bytes)
    [OK] Figure asset: 9_aoi_vs_density.png (41842 bytes)
    [OK] Figure asset: 10_pdr_vs_distance.png (41345 bytes)
    [OK] Figure asset: 5_hardware_feasibility.png (22407 bytes)
    [OK] Figure asset: 2_ablation_study.png (55259 bytes)
    [OK] Figure asset: 3_moe_routing.png (38427 bytes)
    [OK] Figure asset: 4_tsne_clustering.png (26060 bytes)

[*] Tier 2: Validating BibTeX Database Syntax & 27 Keys...
  [INFO] Found 27 BibTeX entries in references.bib
    [OK] Citation keys 27/27 verified
[*] Tier 3 & 4: main.tex not yet present (Skipping in early Milestone stage).

================================================================
 [SUCCESS] ALL INTEGRITY & VALIDATION CHECKS PASSED (0 ERRORS)
================================================================
```

### 3.2 Pytest 단위 테스트 슈트
```bash
$ /home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/latex/etc/scripts/test_m1_infrastructure.py -v
============================= test session starts ==============================
collected 6 items

etc/scripts/test_m1_infrastructure.py::test_directory_structure PASSED   [ 16%]
etc/scripts/test_m1_infrastructure.py::test_ieeetran_cls PASSED          [ 33%]
etc/scripts/test_m1_infrastructure.py::test_figures_exist_and_are_valid_png PASSED [ 50%]
etc/scripts/test_m1_infrastructure.py::test_references_bib_entries PASSED [ 66%]
etc/scripts/test_m1_infrastructure.py::test_makefile PASSED              [ 83%]
etc/scripts/test_m1_infrastructure.py::test_validate_latex_script_execution PASSED [100%]

============================== 6 passed in 0.05s ===============================
```

---

## 4. 후속 마일스톤 (M2~M5) 연계 준비 완료 사항
- `references.bib`에 정의된 27개 키는 `PROJECT.md`의 인터페이스 계약과 100% 일치합니다.
- `figures/` 디렉토리는 `fig1_...` 형식 및 `1_...` 형식 모두 지원하여 M4/M5 단계의 `\includegraphics` 호출 호환성을 보장합니다.
- 감사 로깅(`audit_logger.py`) 및 GEMINI.md의 `etc/` 디렉토리 격리 규칙을 엄격히 준수하였습니다.
