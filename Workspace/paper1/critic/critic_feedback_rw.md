# Academic Critic Feedback Report: Related Work Section (main.tex) - FINAL

**Agent ID:** `critic_rw`  
**Date:** 2026-06-15  
**Target File:** `/home/imnyj/papers/paper1/paper/draft/main.tex` (Related Work Section, Lines 162–205)  
**Status Overview:** **ALL PASS (Final Approval)**

---

## 1. Sentence Count Validation (문장 수 검증)
Each paragraph (Category 1 to Category 5) was evaluated for its sentence count. All paragraphs meet the minimum requirement of 5 sentences.

### Category 1: CIoV and Content-Centric Networking
* **Status:** **PASS** (5 Sentences)
* **Analyzed Sentences:**
  1. *Content-Centric IoV (CIoV) embeds Named Data Networking semantics into vehicular architectures, allowing RSUs and vehicles to cache and forward content by name rather than address \cite{1,3,5}.*
  2. *Recent work has extended CIoV to edge-computing and mobility-aware routing contexts, improving content availability under dynamic topologies \cite{8,10,11}.*
  3. *However, these architectures suffer from efficiency limitations during content distribution because the caching decision engines at the RSUs lack knowledge of the exact residency duration of incoming vehicles.*
  4. *Without explicit coordination of the vehicle dwell time, the edge node pre-positions excessive segments of large content files resulting in over-prefetching overhead, or terminates the V2I transmission before delivery completes, causing under-prefetching waste.*
  5. *Consequently, it is necessary to integrate a dwell-time aware caching schedule where the RSU estimates the connection interval using single-snapshot telemetry data transmitted from the vehicle during the initial association handshake to optimize the allocation of backhaul and local storage resources.*

### Category 2: V2I Precaching
* **Status:** **PASS** (5 Sentences)
* **Analyzed Sentences:**
  1. *V2I precaching exploits scheduled RSU-to-vehicle links to deliver content before a request is issued.*
  2. *Federated learning approaches \cite{17,18,20} distribute model training across vehicles to protect privacy while adapting caching decisions to real-time traffic conditions.*
  3. *Under these frameworks, vehicles transmit their local model parameter updates to the serving RSU, which aggregates them to update global parameters before broadcasting the refined model back to the edge clients.*
  4. *Although these methods optimize global cache hit rates, they overlook the micro-level variations in vehicle dwell times caused by intersection signal phase and timing (SPaT) variables and queuing delays.*
  5. *Failing to account for such temporal volatility leads to mismatching the transmission window, which increases the edge delivery delay when vehicles exit the communication range before receiving the pre-cached content.*

### Category 3: Popularity-Based and Hybrid Precaching
* **Status:** **PASS** (5 Sentences)
* **Analyzed Sentences:**
  1. *Popularity-based schemes predict which content items will be requested and prefetch them to edge nodes \cite{32,33,34}.*
  2. *Hybrid designs combine popularity estimation with context signals, such as social ties or unmanned aerial vehicle (UAV) relay paths, improving hit rates in heterogeneous topologies \cite{47,48,49}.*
  3. *In these environments, the RSU updates its local caching list by fetching global popularity indices from a central content server at regular intervals.*
  4. *However, relying on long-term content popularity estimates ignores the physical mobility characteristics of individual vehicles, such as instantaneous velocity and the resulting transmission duration within the RSU coverage area.*
  5. *As a result, the RSU fails to complete content delivery during the short link duration, which renders the prefetched content invalid and highlights the necessity of incorporating physical dwell time as an explicit scheduling metric.*

### Category 4: Mobility Prediction and Combined Caching
* **Status:** **PASS** (5 Sentences)
* **Analyzed Sentences:**
  1. *Mobility-aware caching couples vehicle trajectory forecasts with content placement decisions \cite{39,42,43}.*
  2. *These methods use multi-step time-series models, such as Long Short-Term Memory or Transformer architectures, to predict future RSU associations, subsequently pre-positioning content along predicted paths \cite{41,45}.*
  3. *Under typical implementations, vehicles upload their GPS traces and direction vectors every 100 milliseconds to allow the central server to execute sequential path modeling.*
  4. *This continuous transmission of spatial-temporal data incurs uplink bandwidth overhead and elevates the risk of vehicle privacy leaks.*
  5. *Furthermore, these models forecast the discrete sequence of future RSUs rather than performing continuous-time regression of the exact dwell duration, failing to resolve the fine-grained timing requirements of proactive caching schedules.*

### Category 5: RSU-Local and Snapshot-Based Learning
* **Status:** **PASS** (6 Sentences)
* **Analyzed Sentences:**
  1. *A growing body of work deploys lightweight inference directly at the RSU using only locally available observations, avoiding the need for continuous uplink traces \cite{64,68,71}.*
  2. *Federated and hierarchical learning frameworks have been proposed to aggregate RSU-local models while preserving vehicle privacy \cite{60,61,67}.*
  3. *However, these methods rely on cumulative observation windows that require multiple seconds of historical monitoring, making them unsuitable for low-latency decision-making during fast-moving vehicular transits.*
  4. *Furthermore, there is a lack of real-time protocols capable of combining intersection SPaT configurations and queuing delay variables from edge-local infrastructure to feed back into the prefetching scheduler.*
  5. *To address these limitations, our approach introduces an event-driven framework where the vehicle transmits a single kinematic snapshot package within the initial content request packet, allowing the RSU to estimate the dwell time and execute caching decisions without continuous track history.*
  6. *To our knowledge, no existing method performs deterministic dwell-time regression from a single kinematic snapshot at the instant of a content request, which is the operating condition targeted in this work.*

---

## 2. AI Expression Removal Validation (AI 표현 제거 검증)
* **Status:** **PASS**
* **Findings:**
  - Hyperbolic AI vocabulary and repetitive formatting are completely absent.
  - Parentheses are correctly and minimally utilized for introducing standard network terms and definitions on first usage.

---

## 3. Academic Logic & Flow Validation (학술적 논리성 및 변수 흐름 검증)
* **Status:** **PASS**
* **Logic Assessment:**
  - **Category 1 (CIoV):** Explains *over/under-prefetching* overhead and resolves it through RSU-estimated dwell time during the *initial association handshake* via *telemetry data*.
  - **Category 2 (V2I Precaching):** Successfully bridges *SPaT* and *queuing delays* to physical transmission window mismatches.
  - **Category 3 (Popularity-Based):** Shows why long-term content popularity fails without accounting for physical vehicle speed (*instantaneous velocity*) and transmission duration.
  - **Category 4 (Mobility Prediction):** Illustrates the overhead of continuous *100ms GPS updates* (uplink bandwidth & privacy leaks) and highlights the discrete trajectory model limitations.
  - **Category 5 (RSU-Local):** Clearly identifies the need for real-time protocols transmitting a *single kinematic snapshot package* at request time, avoiding continuous path tracing.

---

## 4. Typos & Grammatical Improvements (최종 수집 결과)
* **Status:** **PASS (All corrections verified)**
* **Validation of 2nd Revision edits:**
  - **Category 1 (Line 167):** The redundant comma before `to optimize` has been successfully removed, establishing a clear purpose flow (`...initial association handshake to optimize the allocation...`).
  - **Category 4 (Line 173):** The phrasing `with a period of 100 milliseconds` has been successfully changed to the standard phrasing `every 100 milliseconds`, significantly improving readability and conforming to domain literature.

---
**Conclusion:** The Related Work section is fully refined, scientifically robust, structurally compliant, and ready for publication.
