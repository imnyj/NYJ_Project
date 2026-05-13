# Writer Memory

## Stage 1 of 3 — Completed [2026-05-12]

### Output File
- `/home/imnyj/papers/paper4/paper/draft/main.tex` (신규 생성)
- 총 405 lines, 19,235 자

### 작성 완료 섹션
1. **Skeleton** — `\documentclass[journal]{IEEEtran}` + 패키지 (amsmath, booktabs, array, cite, hyperref, enumitem, balance, xcolor, graphicx, multirow, algorithmic, url) + custom column types (L/C/R) + 제목/저자 placeholder + \begin{document}
2. **Abstract** — 230단어 (AoI-CBR tension, TinyMLP-AI-DCC 제안, Behavior Cloning + oracle, MCU < 4 KB 요약)
3. **IEEEkeywords** — 7개 키워드 (Age of Information, vehicular networks, decentralized congestion control, TinyML, beacon rate control, ETSI CAM, behavior cloning)
4. **Introduction** (\label{sec:introduction}) — 5단락 + C1/C2/C3 itemize + "remainder of paper" 단락
5. **Related Work** (\label{sec2}) — subsection 3개:
   - §2-A: AI-Driven MAC Protocols for Vehicular Networks
   - §2-B: Lightweight ML and TinyML in IoT / V2X
   - §2-C: ETSI DCC and Beaconing Algorithms
   - Table 1 (table*): 7행 × 7열 비교 표 (Method, Control Target, AI Approach, Optimization Objective, Standard Compliance, MCU Deployment, AoI-Aware)
6. **TODO 헤더** — sec.net, sec.prop, sec.s, sec.c, thebibliography (Stage 2/3 예약)

### 인용 키 사용 현황 (섹션별)
**Introduction:**
- Bhattacharyya2024, Wu2025, Iqbal2025, Zila2026, Ni2024, Wang2024

**Related Work §2-A (AI-driven MAC):**
- Wu2025, Iqbal2025, Louvros2026, Li2024a, Wang2024, Ibrahim2025, Ni2024, PV2025

**Related Work §2-B (Lightweight ML / TinyML):**
- Zila2026, Li2025, Zhang2025b, Xie2025, Chen2026

**Related Work §2-C (ETSI DCC / Beaconing):**
- Bhattacharyya2024, Iliopoulos2025, Mianji2025

**Table 1 (comparison):**
- Bhattacharyya2024, Zila2026, Ni2024, Wu2025, Iqbal2025, Wang2024

**총 고유 인용 키 (16개):**
Bhattacharyya2024, Chen2026, Ibrahim2025, Iliopoulos2025, Iqbal2025,
Li2024a, Li2025, Louvros2026, Mianji2025, Ni2024, PV2025,
Wang2024, Wu2025, Xie2025, Zhang2025b, Zila2026

**할루시네이션 검증:** NONE — 모두 bibitem.tex 47개 키 내에서만 사용 ✅

### 제목 결정
"TinyMLP-Based Joint Beacon Rate and Power Control for AoI-Aware Vehicular IoT Under ETSI CAM"
(idea_spec §0/§2 기반, 56자 — IEEE 권고 범위 내)

### 다음 Stage 2 예정 작업
- \section{Network Model and Scheme Overview} (sec.net)
- \section{Proposed Scheme} (sec.prop): TinyMLP 구조 그림, Behavior Cloning 파이프라인, 수식, MCU 배포 흐름
- \section{Performance Evaluation} (sec.s) 부분 작성: 시뮬레이션 설정, 베이스라인 기술

### 제약 준수
- \includegraphics 미사용 (figure/, graph/ 디렉터리 비어 있음)
- \begin/\end 모든 쌍 검증 완료
- bibitem.tex 외 인용 키 없음
