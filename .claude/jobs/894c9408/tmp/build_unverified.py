# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, "/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

AGENT = "p2-librarian"
p = "/home/imnyj/Workspace/paper2/librarian/unverified.md"

BODY = """# paper2 미검증 및 제외 항목

`related_works.json`에 넣지 않은 항목을 사유별로 정리하였다. 조사 기준일은 2026년 9월 4일이다.
여기에 적힌 항목은 어떤 경우에도 논문 본문에 그대로 인용하면 안 되며, 필요하면 원문을 다시 확보한 뒤 인덱스로 옮겨야 한다.

## 1. 실존을 확인하지 못한 항목

`/home/imnyj/Workspace/paper5/related_works.json`에서 인계받은 세 건은 CrossRef에서 일치하는 문헌을 찾지 못하였다.
세 건 모두 저자명이 `A. Smith`, `B. Doe`, `C. Lee`, `D. Kim`, `E. Wang`, `F. Chen`처럼 이름 대신 자리를 채우는 형태이고,
DOI와 게재지, 권호 정보가 아예 없으며, 제목으로 검색해도 같은 제목의 문헌이 나오지 않는다.
따라서 이 세 건은 실재하지 않는 서지 정보로 판단하여 전부 제외하였다.
paper5 원본 파일은 그대로 두었으므로, paper5 작업에서도 같은 항목이 인용되지 않도록 별도로 확인할 필요가 있다.

| 원본에 적힌 제목 | 원본에 적힌 저자 | 원본에 적힌 연도 | 판단 |
|---|---|---|---|
| Proactive Context-Aware Handover for Urban Air Mobility | A. Smith, B. Doe | 2024 | 일치하는 문헌 없음 |
| Machine Learning for Predictive Handover in Aerial Networks | C. Lee, D. Kim | 2025 | 일치하는 문헌 없음 |
| Integrated Space-Air-Ground Networks for UAM: Challenges and Solutions | E. Wang, F. Chen | 2025 | 일치하는 문헌 없음 |

다만 두 번째 항목이 가리키려 한 내용과 가장 가까운 실제 문헌으로 Aydin과 Dreo Rodosek의 DASC 2023 논문
(DOI 10.1109/DASC58513.2023.10311303)을 확인하여 인덱스의 축 3에 넣었다.

## 2. 서지 정보는 확인하였으나 초록을 확보하지 못한 항목

아래 세 건은 CrossRef에서 저자와 제목, 게재지, 연도를 확인하였고 DOI도 정상적으로 해석된다.
그런데 출판사 사이트가 자동 접근을 차단하고 Semantic Scholar와 OpenAlex에도 초록이 등록되어 있지 않아 내용을 확인하지 못하였다.
서지 정보 자체는 검증되었으므로 `related_works.json`에는 포함하되 `abstract_confirmed` 필드를 거짓으로 두었고,
요약란에는 내용을 추측해 채우지 않고 초록 미확보 사실을 적어 두었다.
본문에서 이 세 건의 내용을 근거로 삼으려면 기관 구독 계정으로 원문을 먼저 확보해야 한다.

| 제목 | 게재지 | DOI |
|---|---|---|
| Multi-Beamforming enhanced Multi-Layer Aerial Corridor Coverage for Urban Air Mobility | IEEE Transactions on Vehicular Technology, 2026 | 10.1109/TVT.2026.3710554 |
| 5G deployment and positioning analysis for Urban Air Mobility vertiport operations | IEEE Access, 2026 | 10.1109/ACCESS.2026.3725460 |
| LBHO-RL: GPS Trajectory Prediction and Reinforcement Learning for Proactive Handover Management in 5G Heterogeneous Networks | Wireless Personal Communications, vol. 146, no. 7, 2026 | 10.1007/s11277-026-12132-y |

앞의 두 건은 조기 공개 단계여서 권호와 페이지가 아직 확정되지 않았다는 점도 함께 기록해 둔다.

## 3. 출처 제한 규칙 때문에 제외한 항목

`librarian` 규칙은 arXiv와 MDPI, Scopus를 검색 대상에서 제외하도록 정하고 있다.
그런데 조사 축 5의 핵심 원전 두 건은 정식 출판본이 존재하지 않고 프리프린트로만 유통되고 있어 이 규칙과 충돌한다.
두 건 모두 실존은 확인하였으나 DOI가 부여된 출판본이 없으므로 인덱스에는 넣지 않았다.

| 제목 | 저자 | 상태 |
|---|---|---|
| Parametrized Deep Q-Networks Learning: Reinforcement Learning with Discrete-Continuous Hybrid Action Space | Jiechao Xiong 외 9인 | arXiv:1810.06394, 2018년 제출. 학술지나 학회 게재 정보가 없음 |
| Deep Reinforcement Learning in Parameterized Action Space | Matthew Hausknecht, Peter Stone | arXiv:1511.04143, 2015년 제출. ICLR 2016으로 색인되나 DOI가 부여된 출판본이 없음 |

이 두 건은 P-DQN과 PA-DDPG의 원전이어서 방법론을 서술할 때 언급을 피하기 어렵다.
따라서 상위 에이전트의 판단이 필요하며, 이에 관한 질의를 최종 보고의 `## 질의` 항목에 올렸다.
대안으로는 인덱스에 이미 포함한 Fan 외의 IJCAI 2019 논문(DOI 10.24963/ijcai.2019/316)과
Fu 외의 IJCAI 2019 논문(DOI 10.24963/ijcai.2019/323)으로 혼성 행동 알고리즘 계열을 대신 인용하는 방법이 있다.

MDPI에서 출판된 아래 항목들도 주제 적합성은 높았으나 출처 제한 규칙에 따라 제외하였다.

| 제목 | 게재지 |
|---|---|
| Urban Air Mobility Communications and Networking: Recent Advances, Techniques, and Challenges | Drones |
| A Vertiport Design Heuristic to Ensure Efficient Ground Operations for Urban Air Mobility | Applied Sciences |
| UAM Vertiport Network Design Considering Connectivity | Systems |
| Real-Time Handover in LEO Satellite Networks via Markov Chain-Guided Simulated Annealing | Network |
| Proactive Handover Decision for UAVs with Deep Reinforcement Learning | Sensors |
| Discretionary Lane-Change Decision and Control via Parameterized Soft Actor-Critic for Hybrid Action Space | Machines |

이 가운데 `Proactive Handover Decision for UAVs with Deep Reinforcement Learning`은 인덱스에 넣은
IMCOM 2022 논문(DOI 10.1109/IMCOM53663.2022.9721627)과 저자가 같은 확장판에 해당하므로, 학회판을 대신 인용하면 내용을 대체할 수 있다.

## 4. 정식 출판되지 않아 제외한 항목

검색 과정에서 아래 유형의 항목이 다수 확인되었으나 전부 preprint 또는 posted-content 상태여서 제외하였다.
축 3의 예측 기반 핸드오버 영역에서 특히 이런 항목이 많았고, 그 결과 축 3은 다른 축보다 확보 건수가 적다.

- A Decision-Tree-Based Algorithm for Proactive Handover Prediction in Multi-RAT Cellular Networks (Preprints.org)
- A Novel Framework for Multi-UAV Trajectory Prediction and Handover Optimization in 5G Networks (Preprints.org)
- Accurate Seamless Vertical Handover Prediction Using Peephole LSTM based on Light-GBM Algorithm (Research Square)
- Intelligent Blockage Prediction and Proactive Handover for Seamless Connectivity in Vision-Aided 5G/6G UDNs (TechRxiv)
- Enhanced Throughput and Seamless Handover Solutions for Urban 5G-Vehicle C-Band Integrated Satellite-Terrestrial Networks (TechRxiv)
- Self-Optimized Handover in 5G/Beyond Heterogeneous Networks Using Actor-Critic Deep Reinforcement Learning (SSRN)
- Parameterized Action Deep Reinforcement Learning for Joint Resource Allocation in V2X-NOMA Systems (기관 저장소 게재본)

## 5. 조사 축별로 남은 공백

- 축 1에서 PSU 기반 4D 궤적 관리를 정면으로 다루면서 통신 관점을 함께 서술한 문헌은 확인하지 못하였다.
  현재는 항공 교통 관리 관점의 문헌(DOI 10.1109/TITS.2026.3651399, 10.1109/DASC58513.2023.10311299)으로 대신하고 있다.
- 축 1의 C2 링크 신뢰도 표준을 다룬 문헌 역시 3년 이내 조건을 만족하는 항목을 찾지 못하였다.
  검색에 걸린 항목은 2019년 VTC 논문(Dual-Network Connectivity 기반 드론 C2 링크 신뢰도)으로 5년 조건도 넘어선다.
- 축 3에서 Transformer와 그래프 신경망을 예측 모듈로 사용한 핸드오버 문헌은 정식 출판본을 확인하지 못하였다.
"""

lm, al = LockManager(), AuditLogger()
assert lm.acquire(p, AGENT)
open(p, "w").write(BODY)
lm.release(p, AGENT)
al.log_action(AGENT, "CREATE", p, "미검증 및 제외 항목 정리. paper5 인계 3건 환각 판정 포함.")
print("wrote", p)
