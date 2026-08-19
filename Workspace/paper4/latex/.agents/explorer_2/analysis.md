# R2 & R3 Structure Investigation & Revision Plan

**문서 경로**: `/home/imnyj/Workspace/paper4/latex/.agents/explorer_2/analysis.md`  
**분석 대상 파일**: `/home/imnyj/Workspace/paper4/latex/main.tex`  
**담당 요구사항**: R2 (Introduction Contributions 포맷팅), R3 (Related Works 비교 테이블 재구성)  
**작성 일시**: 2026-08-18  

---

## 1. 개요 및 요약 (Executive Summary)

본 보고서는 `main.tex` 논문의 **R2 (Introduction의 Contributions 포맷)** 및 **R3 (Related Works의 Table I 비교 테이블 재구성)** 요구사항에 대한 정밀 조사 분석 및 구체적 적용 방안을 제시합니다.

- **R2 핵심 분석 요약**: Introduction 내 기여도 서술부는 **라인 72~78**에 위치합니다. 4개 항목으로 구성되어 있으며, R1 학술 문체 규칙(과장 표현 `Comprehensive` 및 AI 상투어 `systematic` 제거, 괄호 축소)을 반영하여 세련되고 건조한 학술적 문장의 `itemize` 환경으로 정제된 완성형 코드 블록을 설계하였습니다.
- **R3 핵심 분석 요약**: Related Works 섹션 내 비교 테이블(`tab:lit_comparison`)은 **라인 138~163**에 위치합니다. 기존 6개 열(Reference, Year, Optimization Target, RL Algorithm Used, Baselines, MoE / Ensemble)에서 **Year 열을 완전히 삭제**하고, Reference 열 내 **모든 저자명/학술지 표기를 제거하여 `\cite{}` 단독 표기로 전면 개편**합니다. 페이지 폭 초과 방지를 위해 고정 너비 및 자동 줄바꿈 지정자(`p{...}` 및 `tabularx`의 `L`/`Y`)를 적용한 최적의 5개 열 레이아웃을 도출하였습니다.

---

## 2. R2: Introduction Contributions 포맷 분석 및 수정안

### 2.1 현재 상태 조사 (Current State)
- **위치**: `main.tex` Line 72 ~ Line 78
- **직전 문맥 (Line 70-71)**: REMO-DQN 아키텍처 및 해결 원리 요약 문단
- **직후 문맥 (Line 80-81)**: 논문 전체 구성(Paper Organization) 안내 문단
- **현재 코드 (Line 72-78)**:
```latex
The main contributions of this paper are summarized as follows:
\begin{itemize}
    \item \textbf{Comprehensive 21-Model Empirical Benchmark:} We construct an end-to-end simulation framework integrating Eclipse SUMO micro-mobility and Nakagami-$m$ fading channels, conducting the first systematic empirical comparison across 14 RL/DRL algorithms and 7 baseline/machine-learning models optimized via the Optuna framework.
    \item \textbf{CBR Flapping Suppression and PDR Defense:} REMO-DQN eliminates standard DCC limit-cycle oscillations, achieving a stable mean CBR of 0.3442 ($\sigma=0.1008$) with 0.0\% violation of the 0.60 threshold. At an extreme density of 100~veh/km, REMO-DQN maintains a 73.41\% PDR (a modest 3.13\%p drop from 76.54\% at 10~veh/km), whereas conventional schemes collapse by 74--91\%p.
    \item \textbf{True AoI Freshness Optimization:} By coupling reward signals with physical CSMA/CA MAC collision dynamics, REMO-DQN achieves a network average AoI of 373.21~ms across all density domains, outperforming AdaptDCC (3,205.96~ms) and Fixed 10~Hz (4,682.51~ms) by 8.59-fold and 12.55-fold, respectively.
    \item \textbf{OBU Hardware Feasibility and Latency Profiling:} We profile the computational complexity on target ARM Cortex embedded hardware, confirming that REMO-DQN requires only 3.8M MACs, 350K parameters (1.4~MB memory), and 1.2~ms inference latency, occupying merely 1.2\% of the 100~ms DCC operational window.
\end{itemize}
```

### 2.2 항목별 분석 및 R1 연계 교정 사항
1. **항목 1 (Benchmark)**:
   - 문제점: 금지어 `Comprehensive` 및 AI 상투어 `systematic` 사용.
   - 교정: `\textbf{Multi-Model Empirical Benchmark:}`로 제목 수정. `systematic empirical comparison`을 건조한 학술 표현 `empirical comparison` 또는 `rigorous benchmark evaluation`으로 변경.
2. **항목 2 (CBR & PDR)**:
   - 문제점: 불필요한 괄호 부연 설명 `(a modest 3.13\%p drop from 76.54\% at 10~veh/km)` 및 감정적 수식어 `modest` 사용.
   - 교정: 자연스러운 산문 문장 `, representing a 3.13\%p decrease from 76.54\% at 10~veh/km,`으로 전환.
3. **항목 3 (AoI Optimization)**:
   - 문제점: 수치 병렬 괄호 나열 `(3,205.96~ms)` 및 `(4,682.51~ms)` 존재.
   - 교정: `outperforming AdaptDCC with 3,205.96~ms and Fixed 10~Hz with 4,682.51~ms`로 자연스럽게 연결.
4. **항목 4 (Hardware Feasibility)**:
   - 문제점: 괄호 `(1.4~MB memory)` 및 불필요한 부사 `merely`.
   - 교정: 괄호 제거 후 콤마로 나열 (`350K parameters, 1.4~MB memory, and 1.2~ms inference latency`), `occupying 1.2\% of the 100~ms DCC operational window`로 정리.

### 2.3 제안하는 최종 R2 LaTeX 코드
```latex
The main contributions of this paper are summarized as follows:
\begin{itemize}
    \item \textbf{Multi-Model Empirical Benchmark:} We construct an end-to-end simulation framework integrating Eclipse SUMO micro-mobility and Nakagami-$m$ fading channels, conducting an empirical evaluation across 14 RL/DRL algorithms and 7 baseline schemes optimized via the Optuna framework.
    \item \textbf{CBR Flapping Suppression and PDR Defense:} REMO-DQN eliminates standard DCC limit-cycle oscillations, maintaining a stable mean CBR of 0.3442 with standard deviation 0.1008 and zero violation of the 0.60 threshold. At a vehicle density of 100~veh/km, REMO-DQN defends a 73.41\% PDR, representing a 3.13\%p decrease from 76.54\% at 10~veh/km, whereas conventional schemes degrade by 74--91\%p.
    \item \textbf{True AoI Freshness Optimization:} By coupling reward signals with physical CSMA/CA MAC collision dynamics, REMO-DQN achieves a network average AoI of 373.21~ms across all density domains, outperforming AdaptDCC with 3,205.96~ms and Fixed 10~Hz with 4,682.51~ms by 8.59-fold and 12.55-fold, respectively.
    \item \textbf{OBU Hardware Feasibility and Latency Profiling:} We evaluate the computational complexity on target ARM Cortex embedded hardware, confirming that REMO-DQN requires 3.8M MACs, 350K parameters, 1.4~MB memory, and 1.2~ms inference latency, occupying 1.2\% of the 100~ms DCC operational window.
\end{itemize}
```

---

## 3. R3: Related Works 비교 테이블 재구성 분석 및 수정안

### 3.1 현재 상태 조사 (Current State)
- **위치**: `main.tex` Line 138 ~ Line 163 (`Table I: tab:lit_comparison`)
- **현재 구조**:
  - `\begin{table*}[t]` (전폭 테이블)
  - `\begin{tabularx}{\textwidth}{l c l l c c}` (6개 열: Reference, Year, Optimization Target, RL Algorithm Used, Baselines, MoE / Ensemble)
- **현재 코드 (Line 138-163)**:
```latex
\begin{table*}[t]
\caption{Comprehensive Literature Comparison of V2X Congestion Control and RL Frameworks}
\label{tab:lit_comparison}
\centering
\scriptsize
\begin{tabularx}{\textwidth}{l c l l c c}
\toprule
\textbf{Reference} & \textbf{Year} & \textbf{Optimization Target} & \textbf{RL Algorithm Used} & \textbf{Baselines} & \textbf{MoE / Ensemble} \\
\midrule
ETSI TS 102 687 \cite{ETSI_TS_102_687, ETSI_TS_103_175} & 2018 & CBR Stability & N/A (Static Rule-based FSM / PI) & 2 & No \\
Ye \textit{et al.} (IEEE TVT) \cite{Ye2019Deep} & 2019 & V2V Capacity \& Latency & Vanilla DQN & 3 & No \\
Hu \textit{et al.} (IEEE TWC) \cite{Hu2021Deep} & 2021 & PDR \& Throughput & DDPG & 4 & No \\
Zheng \textit{et al.} (IEEE T-ITS) \cite{Zheng2022Age} & 2022 & AoI \& CBR Trade-off & Deep Q-Learning & 3 & No \\
Wang \textit{et al.} (IEEE TWC) \cite{Wang2023Multi} & 2023 & PDR \& Power Efficiency & MAPPO (CTDE) & 4 & No \\
Bhattacharyya \textit{et al.} (IEEE TVT) \cite{Bhattacharyya2024Hybrid} & 2024 & AoI \& Channel Load & Tabular Q-Learning & 3 & No \\
Liu \textit{et al.} (IEEE T-ITS) \cite{Liu2024Age} & 2024 & AoI \& Energy Consumption & SAC / PPO & 5 & No \\
Kang \textit{et al.} (IEEE JSAC) \cite{Kang2024Task} & 2024 & Edge Latency \& Resource Cost & Meta-RL + Task-Oriented MoE & 4 & Yes \\
Xu \textit{et al.} (IEEE COMST) \cite{Xu2025Mixture} & 2025 & Generalization \& Edge Efficiency & Survey on MoE + Wireless DRL & N/A & Yes \\
Du \textit{et al.} (IEEE Network) \cite{Du2025Generative} & 2025 & Slicing Resource Allocation & Generative AI + MoE & 3 & Yes \\
Park \& Kim (IEEE WCL) \cite{Park2025Ensemble} & 2025 & PDR \& Channel Load & Ensemble Deep Q-Learning & 3 & Yes \\
Zhang \textit{et al.} (IEEE TMC/TWC) \cite{Zhang2026Generalizable} & 2026 & MAC Throughput \& Protocol Adapt. & Meta-RL + MoE Router & 4 & Yes \\
\midrule
\textbf{This Work (REMO-DQN)} & \textbf{2026} & \textbf{CBR Stability, AoI Freshness, PDR, Energy, Latency} & \textbf{ResNet-MoE-Dueling DQN} & \textbf{21 (14 RL + 7 Base)} & \textbf{Yes (3 Dueling Experts)} \\
\bottomrule
\end{tabularx}
\end{table*}
```

### 3.2 세부 수정 요구사항 분석 및 매핑

#### A. 저자명/기관명 제거 및 `\cite{}` 단독 표기 변환 매핑
모든 행에서 저자 이름 및 학술지 표기를 삭제하고 오직 인용 태그 `\cite{...}`만 남깁니다.

| 행 (Row) | 기존 내용 (Before) | 수정 내용 (After) | 비고 |
|:---|:---|:---|:---|
| 1 | `ETSI TS 102 687 \cite{ETSI_TS_102_687, ETSI_TS_103_175}` | `\cite{ETSI_TS_102_687, ETSI_TS_103_175}` | 표준 규격명 제거 |
| 2 | `Ye \textit{et al.} (IEEE TVT) \cite{Ye2019Deep}` | `\cite{Ye2019Deep}` | 저자/저널 제거 |
| 3 | `Hu \textit{et al.} (IEEE TWC) \cite{Hu2021Deep}` | `\cite{Hu2021Deep}` | 저자/저널 제거 |
| 4 | `Zheng \textit{et al.} (IEEE T-ITS) \cite{Zheng2022Age}` | `\cite{Zheng2022Age}` | 저자/저널 제거 |
| 5 | `Wang \textit{et al.} (IEEE TWC) \cite{Wang2023Multi}` | `\cite{Wang2023Multi}` | 저자/저널 제거 |
| 6 | `Bhattacharyya \textit{et al.} (IEEE TVT) \cite{Bhattacharyya2024Hybrid}` | `\cite{Bhattacharyya2024Hybrid}` | 저자/저널 제거 |
| 7 | `Liu \textit{et al.} (IEEE T-ITS) \cite{Liu2024Age}` | `\cite{Liu2024Age}` | 저자/저널 제거 |
| 8 | `Kang \textit{et al.} (IEEE JSAC) \cite{Kang2024Task}` | `\cite{Kang2024Task}` | 저자/저널 제거 |
| 9 | `Xu \textit{et al.} (IEEE COMST) \cite{Xu2025Mixture}` | `\cite{Xu2025Mixture}` | 저자/저널 제거 |
| 10 | `Du \textit{et al.} (IEEE Network) \cite{Du2025Generative}` | `\cite{Du2025Generative}` | 저자/저널 제거 |
| 11 | `Park \& Kim (IEEE WCL) \cite{Park2025Ensemble}` | `\cite{Park2025Ensemble}` | 저자/저널 제거 |
| 12 | `Zhang \textit{et al.} (IEEE TMC/TWC) \cite{Zhang2026Generalizable}` | `\cite{Zhang2026Generalizable}` | 저자/저널 제거 |
| 13 (제안) | `\textbf{This Work (REMO-DQN)}` | `\textbf{REMO-DQN (Ours)}` 또는 `\textbf{Proposed REMO-DQN}` | 본 논문 제안 기법 명시 |

#### B. 'Year' 컬럼 삭제
- 헤더: `\textbf{Year} & ` 완전 삭제
- 데이터 행: 각 행의 `& 2018`, `& 2019`, ..., `& \textbf{2026}` 삭제
- 총 컬럼 수: 6개 $\rightarrow$ **5개**

#### C. 열 너비 초과 방지 및 컬럼 지정자 설계
- **문제점**: 기존 `\begin{tabularx}{\textwidth}{l c l l c c}`는 `tabularx`를 선언해두고도 `X` 지정자를 사용하지 않아, 텍스트가 긴 열(`Optimization Target`, `RL Algorithm Used`)이 자동 줄바꿈되지 않고 페이지 가로 경계를 벗어날 위험이 있음.
- **해결 방안**:
  - `main.tex`의 프리앰블(Line 22~23)에 정의된 `L` (`>{\raggedright\arraybackslash}X`) 및 고정 너비 `p{...}` 지정자 활용.
  - 5개 열 구성:
    1. **Reference**: `>{\centering\arraybackslash}p{2.2cm}` (중앙 정렬, 인용 번호 및 제안 모델명 배치)
    2. **Optimization Target**: `L` (`>{\raggedright\arraybackslash}X`, 텍스트 자동 줄바꿈)
    3. **RL Algorithm Used**: `L` (`>{\raggedright\arraybackslash}X`, 텍스트 자동 줄바꿈)
    4. **Baselines**: `>{\centering\arraybackslash}p{2.0cm}` (중앙 정렬, 베이스라인 개수)
    5. **MoE / Ensemble**: `>{\centering\arraybackslash}p{2.8cm}` (중앙 정렬, MoE 여부)
  - 이 설계를 적용하면 `\textwidth` (IEEE Transactions 2단 전폭) 내에서 완벽하게 균형 잡힌 비율로 자동 래핑이 이루어지며, 셀 내 텍스트 오버플로우가 100% 방지됩니다.
- **캡션 교정 (R1 연계)**:
  - 기존: `\caption{Comprehensive Literature Comparison of V2X Congestion Control and RL Frameworks}`
  - 수정: `\caption{Comparison of Related Studies on V2X Congestion Control and RL Frameworks}` (`Comprehensive` 제거)

---

### 3.3 제안하는 최종 R3 LaTeX 코드

```latex
\begin{table*}[t]
\caption{Comparison of Related Studies on V2X Congestion Control and RL Frameworks}
\label{tab:lit_comparison}
\centering
\scriptsize
\begin{tabularx}{\textwidth}{>{\centering\arraybackslash}p{2.2cm} L L >{\centering\arraybackslash}p{2.0cm} >{\centering\arraybackslash}p{2.8cm}}
\toprule
\textbf{Reference} & \textbf{Optimization Target} & \textbf{RL Algorithm Used} & \textbf{Baselines} & \textbf{MoE / Ensemble} \\
\midrule
\cite{ETSI_TS_102_687, ETSI_TS_103_175} & CBR Stability & N/A (Static Rule-based FSM / PI) & 2 & No \\
\cite{Ye2019Deep} & V2V Capacity \& Latency & Vanilla DQN & 3 & No \\
\cite{Hu2021Deep} & PDR \& Throughput & DDPG & 4 & No \\
\cite{Zheng2022Age} & AoI \& CBR Trade-off & Deep Q-Learning & 3 & No \\
\cite{Wang2023Multi} & PDR \& Power Efficiency & MAPPO (CTDE) & 4 & No \\
\cite{Bhattacharyya2024Hybrid} & AoI \& Channel Load & Tabular Q-Learning & 3 & No \\
\cite{Liu2024Age} & AoI \& Energy Consumption & SAC / PPO & 5 & No \\
\cite{Kang2024Task} & Edge Latency \& Resource Cost & Meta-RL + Task-Oriented MoE & 4 & Yes \\
\cite{Xu2025Mixture} & Generalization \& Edge Efficiency & Survey on MoE + Wireless DRL & N/A & Yes \\
\cite{Du2025Generative} & Slicing Resource Allocation & Generative AI + MoE & 3 & Yes \\
\cite{Park2025Ensemble} & PDR \& Channel Load & Ensemble Deep Q-Learning & 3 & Yes \\
\cite{Zhang2026Generalizable} & MAC Throughput \& Protocol Adapt. & Meta-RL + MoE Router & 4 & Yes \\
\midrule
\textbf{Proposed REMO-DQN} & \textbf{CBR Stability, AoI Freshness, PDR, Energy, Latency} & \textbf{ResNet-MoE-Dueling DQN} & \textbf{21 (14 RL + 7 Base)} & \textbf{Yes (3 Dueling Experts)} \\
\bottomrule
\end{tabularx}
\end{table*}
```

---

## 4. 통합 검증 및 상호 호환성 분석

1. **LaTeX 문법 무결성**:
   - `\begin{tabularx}` 와 `\end{tabularx}` 환경 일치.
   - 열 구분자 `&` 개수가 헤더 및 모든 데이터 행에서 정확히 4개(`&` 4개로 5개 열 생성)로 완벽히 일치하여 컴파일 에러(`Extra alignment tab has been changed to \cr`) 발생 원인을 사전에 원천 차단함.
   - `\cite{}` 태그들이 `references.bib`에 정의된 실제 BibTeX 키(`ETSI_TS_102_687`, `ETSI_TS_103_175`, `Ye2019Deep`, `Hu2021Deep`, `Zheng2022Age`, `Wang2023Multi`, `Bhattacharyya2024Hybrid`, `Liu2024Age`, `Kang2024Task`, `Xu2025Mixture`, `Du2025Generative`, `Park2025Ensemble`, `Zhang2026Generalizable`)와 100% 일치함을 확인.
2. **IEEEtran 스타일 규정 준수**:
   - `booktabs`의 `\toprule`, `\midrule`, `\bottomrule`을 유지하여 깔끔한 출판 품질 유지.
   - 캡션 및 라벨(`\label{tab:lit_comparison}`)이 상단에 정상 배치됨.
3. **요구사항 충족도 체크리스트**:
   - [x] R2: Introduction의 기여도 서술부가 `itemize` 환경으로 명확히 포맷팅됨.
   - [x] R3: Table I에서 모든 저자명이 제거되고 `\cite{}` 단독으로 표기됨.
   - [x] R3: 'Year' 컬럼이 완전히 삭제됨.
   - [x] R3: 고정 너비/자동 줄바꿈 지정자(`p{...}`, `L`)를 적용하여 폭 초과를 방지함.
   - [x] R1 연계: `Comprehensive`, `systematic` 등 금지 단어 제거 완료.
