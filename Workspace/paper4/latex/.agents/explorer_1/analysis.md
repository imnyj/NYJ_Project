# R1 학술적 글쓰기 스타일 정밀 분석 보고서 (Academic Style Analysis)

- **대상 파일**: `/home/imnyj/Workspace/paper4/latex/main.tex`
- **분석 기준**: 
  1. `/home/imnyj/Workspace/paper4/latex/.agents/ORIGINAL_REQUEST.md` (R1 요구사항)
  2. `/home/imnyj/.agents/skills/academic-writing-style/SKILL.md` (학술 글쓰기 스타일 가이드)
- **작성 일자**: 2026-08-18

---

## 1. 금지 및 과장 어휘 (Forbidden & Exaggerated Words) 전수 조사

### 1.1 조사 개요
- 조사 대상 어휘: `elucidate`, `seamless`, `vital`, `fosters`, `comprehensive`, `significantly`, `substantially` 및 파생어 전수 조사
- 조사 결과 요약:
  - `comprehensive` 총 6건 검출 (Abstract, Intro, Related Works Table Caption, Evaluation, Conclusion 등 전역 분포)
  - `elucidate`, `seamless`, `vital`, `fosters`, `significantly`, `substantially`: 0건 검출 (미사용 확인)

### 1.2 상세 위치 및 대체 권고안

| 번호 | 라인 | 원본 텍스트 스니펫 (Before) | 교정 권고안 (After) | 변경 사유 |
|:---:|:---:|:---|:---|:---|
| 1 | **L51** | `\textbf{Comprehensive} empirical evaluations across 21 benchmark models...` | `\textbf{Extensive} empirical evaluations across 21 benchmark models...` | `Comprehensive` → `Extensive` (과장 어휘 완화) |
| 2 | **L68** | `First, existing literature lacks \textbf{comprehensive}, standardized empirical benchmarks evaluating...` | `First, existing literature lacks \textbf{extensive}, standardized empirical benchmarks evaluating...` | `comprehensive` → `extensive` (학술적 톤 유지) |
| 3 | **L74** | `\item \textbf{\textbf{Comprehensive} 21-Model Empirical Benchmark:} We construct an end-to-end...` | `\item \textbf{\textbf{Extensive} 21-Model Empirical Benchmark:} We construct an end-to-end...` | `Comprehensive` → `Extensive` (기여 요약 과장 제거) |
| 4 | **L139** | `\caption{\textbf{Comprehensive} Literature Comparison of V2X Congestion Control and RL Frameworks}` | `\caption{\textbf{Summary} Comparison of V2X Congestion Control and RL Frameworks}` 또는 `\caption{Literature Comparison of V2X Congestion Control and RL Frameworks}` | 표 캡션 내 불필요한 수식어 제거 |
| 5 | **L522** | `To establish a \textbf{comprehensive} comparison, we classify 21 benchmark models into six structural categories:` | `To establish a \textbf{broad} comparison, we classify 21 benchmark models into six structural categories:` 또는 `To compare diverse approaches, we classify...` | `comprehensive` → `broad` / `detailed` |
| 6 | **L933** | `\textbf{Comprehensive} evaluations across 21 benchmark models under SUMO mobility and Nakagami-$m$ fading channels demonstrated...` | `\textbf{Extensive} evaluations across 21 benchmark models under SUMO mobility and Nakagami-$m$ fading channels demonstrated...` | 결론부 과장 수식어 제거 |

---

## 2. AI 상투어구 (AI Clichés & Buzzwords) 전수 조사

### 2.1 조사 개요
- 조사 대상 어휘: `leveraging`/`leverages`, `utilizing`/`utilize`/`utilizes`/`utilized`, `subsequently`, `systematically`/`systematic`, `effectively`, `autonomously`, `encapsulates`
- 조사 결과 요약:
  - `utilize`: L166 1건 검출
  - `systematic`: L74 1건 검출
  - `autonomous`: L64 (Connected and Autonomous Vehicles - CAVs), L935 (3GPP Rel-16/17 Mode 2(b) autonomous sensing) 검출 (모두 표준 학술 고유명사로 예외 인정 대상)
  - `leveraging`, `subsequently`, `effectively`, `encapsulates`: 0건 검출

### 2.2 상세 위치 및 대체 권고안

| 번호 | 라인 | 원본 텍스트 스니펫 (Before) | 교정 권고안 (After) | 변경 사유 |
|:---:|:---:|:---|:---|:---|
| 1 | **L74** | `...conducting the first \textbf{systematic} empirical comparison across 14 RL/DRL algorithms...` | `...conducting a \textbf{detailed} empirical comparison across 14 RL/DRL algorithms...` 또는 `...conducting an empirical comparison across 14 RL/DRL algorithms...` | AI 특유의 'systematic' 과시형 표현 제거 |
| 2 | **L166** | `MAPPO \cite{Yu2022Surprising} and MADDPG \cite{Lowe2017Multi} \textbf{utilize} centralized critics evaluating global state vectors...` | `MAPPO \cite{Yu2022Surprising} and MADDPG \cite{Lowe2017Multi} \textbf{use} centralized critics evaluating global state vectors...` | `utilize` → `use` (간결하고 건조한 동사 대체) |
| 3 | **L64** | `...advancement of Connected and Autonomous Vehicles (CAVs)...` | *유지 (표준 도메인 고유명사)* | CAVs 공식 명칭 |
| 4 | **L935** | `...5G-NR V2X Sidelink Resource Allocation Mode 2(b) autonomous sensing and slot reservation...` | *유지 (3GPP 표준 용어)* | 표준 규격 명칭 |

---

## 3. 소괄호 남용 및 중복 약어 정의 (Unnecessary Parentheses & Redundant Acronyms) 전수 조사

### 3.1 조사 개요
- 불필요한 소괄호 나열(데이터 덤프식 괄호 표기), 중복 약어 선언(FSM, SAC, CBR 등 섹션 간 재선언), 괄호 중첩/연속 나열 전수 조사.

### 3.2 상세 분석 및 산문체 변환 방안

| 번호 | 라인 | 유형 | 원본 텍스트 (Before) | 교정 권고안 (After, 산문체 변환) |
|:---:|:---:|:---:|:---|:---|
| 1 | **L66** | 소괄호 연속 나열 | `Standard DCC protocols standardized by the European Telecommunications Standards Institute (ETSI TS 102 687), notably reactive control (ReactDCC) and adaptive linear control (AdaptDCC), adjust packet generation intervals and transmit power according to local Channel Busy Ratio (CBR) measurements \cite{ETSI_TS_102_687, ETSI_TS_103_175}.` | `Standard ETSI DCC protocols \cite{ETSI_TS_102_687, ETSI_TS_103_175}, namely reactive control (ReactDCC) and adaptive linear control (AdaptDCC), adjust packet generation intervals and transmit power according to local channel busy ratio (CBR) measurements.` |
| 2 | **L91** | 약어 중복 정의 (FSM) | `ReactDCC (ETSI TS 102 687 Annex B) adopts a Finite State Machine (FSM) that transitions...` (L66에서 FSM 이미 정의됨) | `ReactDCC \cite{ETSI_TS_103_175} adopts an FSM that transitions...` (약어 재정의 제거) |
| 3 | **L126** | 약어 중복 정의 (SAC) | `Soft Actor-Critic (SAC) maximizes expected return alongside policy entropy...` (L68에서 SAC 이미 정의됨) | `SAC maximizes expected return alongside policy entropy...` 또는 `The Soft Actor-Critic algorithm maximizes...` |
| 4 | **L70** | 약어 중복 정의 (REMO-DQN) | `...we introduce REMO-DQN (Resource-Efficient Multi-Objective Deep Q-Network), an integrated modular framework...` (Abstract L49에서 이미 정의됨) | `...we introduce REMO-DQN, an integrated modular framework...` |
| 5 | **L75** | 괄호 내 부연설명 및 과장형 어휘 | `...defends a 73.41\% Packet Delivery Ratio (PDR) at an extreme density of 100~veh/km with merely a 3.13\%p drop (a modest 3.13\%p drop from 76.54\% at 10~veh/km), whereas...` | `...defends a 73.41\% PDR at an extreme density of 100~veh/km, exhibiting a minimal drop of 3.13 percentage points from 76.54\% at 10~veh/km, whereas...` |
| 6 | **L76** | 괄호 내 수치 나열 | `...outperforming AdaptDCC (3,205.96~ms) and Fixed 10~Hz (4,682.51~ms) by 8.59-fold and 12.55-fold, respectively...` | `...compared to 3,205.96~ms for AdaptDCC and 4,682.51~ms for Fixed 10~Hz, yielding an 8.59-fold and 12.55-fold improvement, respectively...` |
| 7 | **L77** | 괄호 연속/중첩 | `...while requiring only 3.8M MACs, 350K parameters (1.4~MB memory), and 1.2~ms inference latency (occupying 1.2\% of the 100~ms DCC interval) on an ARM Cortex MCU.` | `...while requiring only 3.8M MACs, 350K parameters, a 1.4~MB memory footprint, and 1.2~ms inference latency, which occupies 1.2\% of the 100~ms DCC interval on an ARM Cortex MCU.` |
| 8 | **L183** | 괄호 내 하드웨어 스펙 나열 | `In contrast, REMO-DQN provides an embedded MCU design (350K parameters, 1.2~ms latency), explicit multi-objective rewards...` | `In contrast, REMO-DQN provides an embedded MCU design with 350K parameters and 1.2~ms latency, explicit multi-objective rewards...` |
| 9 | **L453** | 다중 괄호 중첩 | `...periodic safety beacons (CAM/BSM, 280~B, 1--10~Hz), event-triggered decentralized environmental notification messages (DENM, mapped to AC\_VO with highest EDCA priority), and background infrastructure telemetry (AC\_BE/BK).` | `...periodic safety beacons such as CAM and BSM (280~B payloads generated at 1--10~Hz), event-triggered DENMs mapped to AC\_VO with the highest EDCA priority, and background infrastructure telemetry mapped to AC\_BE and AC\_BK.` |
| 10 | **L596** | 괄호 내 알고리즘/수치 덤프 | `Conversely, continuous actor-critic algorithms (PPO, Actor-Critic, SAC, TD3) exhibit severe gradient variance across non-stationary traffic transitions. Decision Transformer exhibits slow convergence (final reward $-937\,158.43$, PDR 65.34\%) due to context window mismatch...` | `Conversely, continuous actor-critic algorithms including PPO, Actor-Critic, SAC, and TD3 exhibit substantial gradient variance across non-stationary traffic transitions. Decision Transformer exhibits slow convergence, recording a final reward of $-937\,158.43$ and PDR of 65.34\%, due to context window mismatch...` |
| 11 | **L636** | 3연속 괄호 수치 덤프 | `At low density (10~veh/km), baseline models achieve high reception (Fixed 10Hz: 89.70\%, AdaptDCC: 87.15\%, Vanilla DQN: 91.07\%). However, as density reaches 100~veh/km, standard and baseline schemes collapse catastrophically (Fixed 10Hz drops by 74.08\%p to 15.62\%; AdaptDCC drops by 78.01\%p to 9.15\%; ReactDCC collapses to 0.00\%). Monolithic DRL models similarly fail under high contention (Vanilla DQN falls to 1.21\%, TinyMLP to 0.00\%, Decision Transformer to 11.33\%).` | `At a low density of 10~veh/km, baseline models maintain high reception, where Fixed 10Hz, AdaptDCC, and Vanilla DQN achieve 89.70\%, 87.15\%, and 91.07\% PDR, respectively. However, as traffic density increases to 100~veh/km, conventional schemes degrade sharply; Fixed 10Hz drops by 74.08 percentage points to 15.62\%, while AdaptDCC and ReactDCC fall to 9.15\% and 0.00\%, respectively. Monolithic DRL models also experience severe degradation under high contention, with Vanilla DQN and Decision Transformer declining to 1.21\% and 11.33\%, respectively.` |
| 12 | **L719** | 괄호 내 수치 나열 | `REMO-DQN attains an overall mean AoI of \textbf{373.21~ms} (138.56~ms at 10~veh/km, 380.60~ms at 50~veh/km, and 579.52~ms at 100~veh/km)...` | `REMO-DQN attains an overall mean AoI of \textbf{373.21~ms}, measuring 138.56~ms at 10~veh/km, 380.60~ms at 50~veh/km, and 579.52~ms at 100~veh/km...` |
| 13 | **L721** | 괄호 내 수치 나열 | `In contrast, Fixed 10Hz averages 4\,682.51~ms (reaching 6\,735.73~ms at 100~veh/km), performing 12.55-fold worse due to packet collisions. AdaptDCC (3\,205.96~ms) and ReactDCC (3\,848.90~ms) are 8.59-fold and 10.31-fold worse.` | `In contrast, Fixed 10Hz averages 4\,682.51~ms and reaches 6\,735.73~ms at 100~veh/km, resulting in a 12.55-fold degradation due to packet collisions. Similarly, AdaptDCC and ReactDCC exhibit average AoI values of 3\,205.96~ms and 3\,848.90~ms, which are 8.59-fold and 10.31-fold higher than REMO-DQN.` |
| 14 | **L793** | 괄호 내 비교 수치 | `At 200~m, REMO-DQN maintains 88.68\% PDR (+3.54\%p over Vanilla DQN). At the maximum 300~m boundary, REMO-DQN achieves \textbf{71.67\% PDR}, outperforming Vanilla DQN (66.74\%) by \textbf{+4.93\%p} and DQN+MoE (67.58\%) by \textbf{+4.09\%p}, confirming superior link budget preservation.` | `At a distance of 200~m, REMO-DQN maintains an 88.68\% PDR, exceeding Vanilla DQN by 3.54 percentage points. At the maximum 300~m communication boundary, REMO-DQN achieves \textbf{71.67\% PDR}, surpassing Vanilla DQN (66.74\%) and DQN+MoE (67.58\%) by 4.93 and 4.09 percentage points, respectively.` |
| 15 | **L826** | 괄호 내 인라인 모델명/메트릭 덤프 | `Monolithic Vanilla DQN suffers high density collapse (1.21\% PDR, AoI 1\,290.89~ms). Adding MoE routing (`DQN+MoE`) improves PDR to 65.20\%...` | `Monolithic Vanilla DQN suffers severe high-density degradation, yielding a 1.21\% PDR and an AoI of 1\,290.89~ms. Introducing MoE routing in DQN+MoE improves PDR to 65.20\%...` |
| 16 | **L935** | 괄호 내 설명 | `(ii) fusing multi-modal onboard perception uncertainty (LiDAR point cloud sparsity and radar cross-section) into cross-layer state representations` | `(ii) fusing multi-modal onboard perception uncertainty, including LiDAR point cloud sparsity and radar cross-section, into cross-layer state representations` |

---

## 4. 논문 본문 내 소스/데이터 파일명 언급 (Source File Names) 전수 조사

### 4.1 조사 개요
- 독자는 코드베이스를 볼 수 없으므로 논문 본문 내의 `.csv`, `.py`, `.tex`, `.sh` 등 모든 파일명 언급을 제거하거나 학술적 표현으로 재작성해야 함.
- 조사 결과: **총 8건의 `.csv` 파일명**이 Section V 본문 텍스트에 직접 노출되어 있음. (`.py`, `.tex` 등 기타 소스 파일명은 0건)

### 4.2 상세 위치 및 재작성 권고안

| 번호 | 라인 | 노출된 파일명 | 원본 문장 (Before) | 교정 권고안 (After) |
|:---:|:---:|:---:|:---|:---|
| 1 | **L632** | ``cbr_trace.csv`` | `To assess temporal stability, Fig.~\ref{fig:cbr_trace} and Table~\ref{tab:cbr_stats} report 100-second continuous CBR traces sampled at 1~Hz (\textbf{`cbr_trace.csv`}).` | `To assess temporal stability, Fig.~\ref{fig:cbr_trace} and Table~\ref{tab:cbr_stats} report 100-second continuous CBR traces sampled at 1~Hz.` (파일명 완전 삭제) |
| 2 | **L636** | ``pdr_vs_density.csv`` | `Fig.~\ref{fig:pdr_density} and Table~\ref{tab:pdr_density_stats} evaluate PDR across 50 density levels from 10 to 100~veh/km (\textbf{`pdr_vs_density.csv`}).` | `Fig.~\ref{fig:pdr_density} and Table~\ref{tab:pdr_density_stats} evaluate PDR across 50 density levels ranging from 10 to 100~veh/km.` (파일명 완전 삭제) |
| 3 | **L719** | ``aoi_vs_density.csv`` | `Fig.~\ref{fig:aoi_density} and Table~\ref{tab:aoi_density_stats} present receiver-side AoI measurements (\textbf{`aoi_vs_density.csv`}).` | `Fig.~\ref{fig:aoi_density} and Table~\ref{tab:aoi_density_stats} present receiver-side AoI measurements across traffic densities.` (학술적 맥락 문장으로 대체) |
| 4 | **L793** | ``pdr_vs_distance.csv`` | `Fig.~\ref{fig:pdr_distance} and Table~\ref{tab:pdr_distance_stats} evaluate PDR across transmission distances from 0 to 300~m at 50~m intervals (\textbf{`pdr_vs_distance.csv`}).` | `Fig.~\ref{fig:pdr_distance} and Table~\ref{tab:pdr_distance_stats} evaluate PDR across transmission distances from 0 to 300~m at 50~m intervals.` (파일명 완전 삭제) |
| 5 | **L822** | ``hardware_feasibility.csv`` | `We profile hardware execution on an ARM Cortex-M4/A MCU clocked at 168~MHz (\textbf{`hardware_feasibility.csv`}), as illustrated in Fig.~\ref{fig:hardware_profile} and Table~\ref{tab:hardware_stats}.` | `We profile hardware execution on an ARM Cortex-M4/A MCU clocked at 168~MHz, as illustrated in Fig.~\ref{fig:hardware_profile} and Table~\ref{tab:hardware_stats}.` (파일명 완전 삭제) |
| 6 | **L826** | ``ablation_study.csv`` | `Fig.~\ref{fig:ablation} and Table~\ref{tab:ablation_stats} evaluate structural ablations (\textbf{`ablation_study.csv`}).` | `Fig.~\ref{fig:ablation} and Table~\ref{tab:ablation_stats} evaluate structural ablation configurations.` (학술적 맥락 문장으로 대체) |
| 7 | **L912** | ``moe_routing.csv`` | `Fig.~\ref{fig:moe_routing} and Table~\ref{tab:moe_routing_stats} track MoE routing weights across densities from 20 to 160~veh/km (\textbf{`moe_routing.csv`}).` | `Fig.~\ref{fig:moe_routing} and Table~\ref{tab:moe_routing_stats} track MoE routing weights across vehicle densities ranging from 20 to 160~veh/km.` (파일명 완전 삭제) |
| 8 | **L915** | ``tsne_clustering.csv`` | `Fig.~\ref{fig:tsne} and Table~\ref{tab:tsne_stats} present t-SNE 2D latent embeddings for 150 state samples (\textbf{`tsne_clustering.csv`}).` | `Fig.~\ref{fig:tsne} and Table~\ref{tab:tsne_stats} present 2D t-SNE latent embeddings for 150 sampled states across traffic congestion regimes.` (학술적 맥락 문장으로 대체) |

---

## 5. 단락 길이 및 구조 점검 (Paragraph Length Compliance)

### 5.1 점검 기준
- `academic-writing-style` 규정: 논문 내 본문 단락은 논리적 완결성을 위해 **최소 5문장 이상**으로 구성되어야 함.

### 5.2 교정 대상 단락 목록 및 병합/보강 방안

1. **Section II-B 단락 (L133)**: 현재 1문장 (Roman numeral 리스트 형태).
   - 권고: 선행 단락(L119-131)과 병합하거나, 4개의 한계점 (i) non-stationarity, (ii) catastrophic forgetting, (iii) sample inefficiency, (iv) Pareto boundary failure를 각각 독립된 학술 문장으로 전개하여 5문장 이상으로 확장.
2. **Section II-C 단락 (L173)**: 현재 2문장.
   - 권고: MADRL 및 시퀀스 트랜스포머의 OBU 탑재 병목점 4가지(통신 오버헤드, 토폴로지 동적 변화, 2차 복잡도 지연, 부분 관측성 붕괴)를 완전한 서술형 문장들로 풀어서 5문장 이상으로 확장.
3. **Section II-D 단락 (L182-183)**: 현재 4문장.
   - 권고: 기존 무선 MoE의 서버 집중형 한계와 차량용 경량화 MoE의 필요성을 논의하는 1~2문장을 추가하여 5문장 확보.
4. **Section V-C 단락 (L632)**: 현재 4문장.
   - 권고: MoE 라우터의 부드러운 상태 전이가 CBR 채널 변동성을 억제하는 물리적 메커니즘을 설명하는 1문장 보강.
5. **Section V-D 단락 (L636, L638)**: 현재 각각 4문장, 2문장으로 나뉘어 있음.
   - 권고: 하나의 연속된 문단으로 통합하여 6문장의 완결된 밀도별 PDR 분석 문단 구축.
6. **Section V-E 단락 (L706-716, L719-721)**: 수식 전후로 단문들이 분절되어 있음.
   - 권고: 수식 주변 텍스트를 자연스럽게 묶고 수치 비교를 풀어서 5문장 이상의 단락 2개로 완결.
7. **Section V-G 단락 (L822)**: 현재 3문장.
   - 권고: MCU 클럭 사이클 및 메모리 대역폭 측면에서의 실시간 안전 여유 마진 논의 2문장 추가하여 5문장 구성.
8. **Section V-H 단락 (L826, L915)**: 각각 4문장, 3문장.
   - 권고: ResNet과 MoE의 시너지 효과 및 t-SNE 클러스터 분리도 수치 해석을 보강하여 각 5문장 확보.
9. **Section VI 미래 연구 단락 (L935)**: 현재 1개의 긴 복합문장.
   - 권고: 3대 연구 방향 (5G-NR Mode 2(b) 통합, 멀티모달 센서 융합, 대규모 FOT 실증)을 각각 독립된 상세 문장으로 구성하여 4~5문장의 풍부한 향후 과제 단락으로 재작성.

---

## 6. 결론 및 종합 요약
- `main.tex` 파일에 대한 전수 조사를 완료하였으며, 식별된 모든 수정 항목(과장 어휘 6건, AI 상투어구 2건, 소괄호 남용/중복 16건, 파일명 누출 8건, 단락 구조 9건)에 대해 라인 번호와 명확한 Before/After 교정 권고안을 확립하였습니다.
