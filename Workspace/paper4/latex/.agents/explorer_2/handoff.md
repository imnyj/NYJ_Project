# Handoff Report: R2 & R3 Structure Investigation

**작업 디렉토리**: `/home/imnyj/Workspace/paper4/latex/.agents/explorer_2`  
**보고서 파일**: `handoff.md`  
**Handoff Type**: Hard (완료)  
**대상 요구사항**: R2 (Introduction Contributions 포맷), R3 (Related Works 비교 테이블 재구성)  
**분석 대상**: `/home/imnyj/Workspace/paper4/latex/main.tex`  

---

## 1. Observation (직접 관찰 결과)

### A. R2: Introduction Contributions 관찰
- **대상 파일**: `/home/imnyj/Workspace/paper4/latex/main.tex`
- **위치**: Line 72 ~ Line 78
- **직접 인용 (Verbatim Code)**:
```latex
72: The main contributions of this paper are summarized as follows:
73: \begin{itemize}
74:     \item \textbf{Comprehensive 21-Model Empirical Benchmark:} We construct an end-to-end simulation framework integrating Eclipse SUMO micro-mobility and Nakagami-$m$ fading channels, conducting the first systematic empirical comparison across 14 RL/DRL algorithms and 7 baseline/machine-learning models optimized via the Optuna framework.
75:     \item \textbf{CBR Flapping Suppression and PDR Defense:} REMO-DQN eliminates standard DCC limit-cycle oscillations, achieving a stable mean CBR of 0.3442 ($\sigma=0.1008$) with 0.0\% violation of the 0.60 threshold. At an extreme density of 100~veh/km, REMO-DQN maintains a 73.41\% PDR (a modest 3.13\%p drop from 76.54\% at 10~veh/km), whereas conventional schemes collapse by 74--91\%p.
76:     \item \textbf{True AoI Freshness Optimization:} By coupling reward signals with physical CSMA/CA MAC collision dynamics, REMO-DQN achieves a network average AoI of 373.21~ms across all density domains, outperforming AdaptDCC (3,205.96~ms) and Fixed 10~Hz (4,682.51~ms) by 8.59-fold and 12.55-fold, respectively.
77:     \item \textbf{OBU Hardware Feasibility and Latency Profiling:} We profile the computational complexity on target ARM Cortex embedded hardware, confirming that REMO-DQN requires only 3.8M MACs, 350K parameters (1.4~MB memory), and 1.2~ms inference latency, occupying merely 1.2\% of the 100~ms DCC operational window.
78: \end{itemize}
```
- **관찰 결과 요약**:
  1. 기여도 목록은 이미 `\begin{itemize}` 환경으로 선언되어 있으나, 항목 내부에 R1 금지어(`Comprehensive`, `systematic`) 및 불필요한 괄호 부연 설명(`($\sigma=0.1008$)`, `(a modest 3.13\%p drop...)`, `(3,205.96~ms)`, `(1.4~MB memory)`)이 포함되어 있어 학술 문체 다듬기가 필요함.

### B. R3: Related Works 비교 테이블 관찰
- **대상 파일**: `/home/imnyj/Workspace/paper4/latex/main.tex`
- **위치**: Line 138 ~ Line 163 (`Table I: tab:lit_comparison`)
- **직접 인용 (Verbatim Code)**:
```latex
138: \begin{table*}[t]
139: \caption{Comprehensive Literature Comparison of V2X Congestion Control and RL Frameworks}
140: \label{tab:lit_comparison}
141: \centering
142: \scriptsize
143: \begin{tabularx}{\textwidth}{l c l l c c}
144: \toprule
145: \textbf{Reference} & \textbf{Year} & \textbf{Optimization Target} & \textbf{RL Algorithm Used} & \textbf{Baselines} & \textbf{MoE / Ensemble} \\
146: \midrule
147: ETSI TS 102 687 \cite{ETSI_TS_102_687, ETSI_TS_103_175} & 2018 & CBR Stability & N/A (Static Rule-based FSM / PI) & 2 & No \\
148: Ye \textit{et al.} (IEEE TVT) \cite{Ye2019Deep} & 2019 & V2V Capacity \& Latency & Vanilla DQN & 3 & No \\
149: Hu \textit{et al.} (IEEE TWC) \cite{Hu2021Deep} & 2021 & PDR \& Throughput & DDPG & 4 & No \\
150: Zheng \textit{et al.} (IEEE T-ITS) \cite{Zheng2022Age} & 2022 & AoI \& CBR Trade-off & Deep Q-Learning & 3 & No \\
151: Wang \textit{et al.} (IEEE TWC) \cite{Wang2023Multi} & 2023 & PDR \& Power Efficiency & MAPPO (CTDE) & 4 & No \\
152: Bhattacharyya \textit{et al.} (IEEE TVT) \cite{Bhattacharyya2024Hybrid} & 2024 & AoI \& Channel Load & Tabular Q-Learning & 3 & No \\
153: Liu \textit{et al.} (IEEE T-ITS) \cite{Liu2024Age} & 2024 & AoI \& Energy Consumption & SAC / PPO & 5 & No \\
154: Kang \textit{et al.} (IEEE JSAC) \cite{Kang2024Task} & 2024 & Edge Latency \& Resource Cost & Meta-RL + Task-Oriented MoE & 4 & Yes \\
155: Xu \textit{et al.} (IEEE COMST) \cite{Xu2025Mixture} & 2025 & Generalization \& Edge Efficiency & Survey on MoE + Wireless DRL & N/A & Yes \\
156: Du \textit{et al.} (IEEE Network) \cite{Du2025Generative} & 2025 & Slicing Resource Allocation & Generative AI + MoE & 3 & Yes \\
157: Park \& Kim (IEEE WCL) \cite{Park2025Ensemble} & 2025 & PDR \& Channel Load & Ensemble Deep Q-Learning & 3 & Yes \\
158: Zhang \textit{et al.} (IEEE TMC/TWC) \cite{Zhang2026Generalizable} & 2026 & MAC Throughput \& Protocol Adapt. & Meta-RL + MoE Router & 4 & Yes \\
159: \midrule
160: \textbf{This Work (REMO-DQN)} & \textbf{2026} & \textbf{CBR Stability, AoI Freshness, PDR, Energy, Latency} & \textbf{ResNet-MoE-Dueling DQN} & \textbf{21 (14 RL + 7 Base)} & \textbf{Yes (3 Dueling Experts)} \\
161: \bottomrule
162: \end{tabularx}
163: \end{table*}
```
- **관찰 결과 요약**:
  1. 테이블 헤더에 `Year` 열(2번째 열)이 존재하며 총 6개 열임.
  2. `Reference` 열에 저자명/학술지명(예: `Ye \textit{et al.} (IEEE TVT)`, `ETSI TS 102 687`)이 병기되어 있음.
  3. `tabularx` 환경에 `l c l l c c`로 지정되어 있어 자동 줄바꿈(`X` 또는 `p{...}`)이 적용되지 않고 있음.
  4. 캡션에 `Comprehensive` 금지어가 포함되어 있음.

---

## 2. Logic Chain (논리 전개 및 추론 과정)

1. **R2 추론**:
   - [Observation A]에 따라 기여도 목록은 Line 72~78에 위치함.
   - 문맥상 4개의 연구 기여(1. 21개 모델 벤치마크, 2. CBR 진동 억제 및 고밀도 PDR 방어, 3. 물리 계층 충돌 반영 True AoI 최적화, 4. ARM Cortex 임베디드 실현 가능성 및 저지연성)를 완벽하게 유지해야 함.
   - R1 규칙과의 일관성을 위해 `Comprehensive` $\rightarrow$ `Multi-Model`, `systematic` $\rightarrow$ 제거/수정, 괄호 부연 $\rightarrow$ 자연스러운 산문 문장으로 치환하여 `itemize` 환경을 완성함.

2. **R3 추론**:
   - [Observation B]에 따라 비교 테이블은 Line 138~163에 위치함.
   - 요구사항에 따라 2번째 열 `Year`를 헤더 및 13개 행에서 완전 제거하여 컬럼 수를 6개에서 5개로 축소함.
   - Reference 열의 12개 기존 문헌에 대해 저자명 및 저널명을 제거하고 오직 `\cite{...}` 키만 남김. 제안 모델은 `\textbf{Proposed REMO-DQN}`으로 명시함.
   - 열 너비 초과를 방지하기 위해 `main.tex` Line 23에 정의된 `L` (`>{\raggedright\arraybackslash}X`) 및 고정 너비 `p{...}`를 조합하여 `\begin{tabularx}{\textwidth}{>{\centering\arraybackslash}p{2.2cm} L L >{\centering\arraybackslash}p{2.0cm} >{\centering\arraybackslash}p{2.8cm}}` 구성을 도출함.
   - 캡션의 `Comprehensive`를 학술적으로 적절한 `Comparison of Related Studies`로 교정함.

---

## 3. Caveats (주의 사항 및 제약 조건)

- **조사 전용 제약**: 본 에이전트는 읽기 전용 탐색 에이전트로서 `main.tex` 소스 코드를 직접 수정하지 않고, 조사 결과와 교체용 코드 스니펫을 본 보고서 및 `analysis.md`에 제공합니다.
- **BibTeX 키 무결성**: 인용 키(`\cite{...}`)는 `references.bib`에 정의된 키와 완벽히 호환되도록 그대로 유지해야 합니다.
- **테이블 열 개수 일치**: 각 행의 열 구분자(`&`)는 5개 열 기준 정확히 4개여야 하며, 추가 앰퍼샌드가 들어가지 않도록 주의해야 합니다.

---

## 4. Conclusion (최종 결론 및 수정 권고안)

### A. R2 적용 코드 스니펫 (Line 72 ~ Line 78 교체용)
```latex
The main contributions of this paper are summarized as follows:
\begin{itemize}
    \item \textbf{Multi-Model Empirical Benchmark:} We construct an end-to-end simulation framework integrating Eclipse SUMO micro-mobility and Nakagami-$m$ fading channels, conducting an empirical evaluation across 14 RL/DRL algorithms and 7 baseline schemes optimized via the Optuna framework.
    \item \textbf{CBR Flapping Suppression and PDR Defense:} REMO-DQN eliminates standard DCC limit-cycle oscillations, maintaining a stable mean CBR of 0.3442 with standard deviation 0.1008 and zero violation of the 0.60 threshold. At a vehicle density of 100~veh/km, REMO-DQN defends a 73.41\% PDR, representing a 3.13\%p decrease from 76.54\% at 10~veh/km, whereas conventional schemes degrade by 74--91\%p.
    \item \textbf{True AoI Freshness Optimization:} By coupling reward signals with physical CSMA/CA MAC collision dynamics, REMO-DQN achieves a network average AoI of 373.21~ms across all density domains, outperforming AdaptDCC with 3,205.96~ms and Fixed 10~Hz with 4,682.51~ms by 8.59-fold and 12.55-fold, respectively.
    \item \textbf{OBU Hardware Feasibility and Latency Profiling:} We evaluate the computational complexity on target ARM Cortex embedded hardware, confirming that REMO-DQN requires 3.8M MACs, 350K parameters, 1.4~MB memory, and 1.2~ms inference latency, occupying 1.2\% of the 100~ms DCC operational window.
\end{itemize}
```

### B. R3 적용 코드 스니펫 (Line 138 ~ Line 163 교체용)
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

## 5. Verification Method (독립 검증 방법)

1. **파일 검사**:
   - `view_file` 도구로 `/home/imnyj/Workspace/paper4/latex/main.tex`의 Line 72~78 및 Line 138~163 영역을 검사하여 위의 제안 코드와 대조 확인.
2. **구문 및 정렬 검사**:
   - `Table I`의 각 행에 존재하는 `&` 기호 개수(정확히 4개) 확인.
   - `\begin{tabularx}` 와 `\end{tabularx}` 환경의 열 지정자 개수(5개)와 매칭 여부 확인.
3. **무효화 조건 (Invalidation Conditions)**:
   - 기여도 서술부에서 `itemize` 환경이 누락되거나 줄글 형태로 복원된 경우.
   - `Table I`에 저자명(`et al.`) 또는 `Year` 컬럼이 잔존하는 경우.
   - `tabularx`에서 자동 줄바꿈 지정자(`L` 또는 `p{...}`) 미사용으로 페이지 우측 여백 초과가 발생하는 경우.
