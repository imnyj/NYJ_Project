Original Manuscript ID: IoT- 64949-2026
Original Article Title: “Uncertainty-Aware Precaching Scheme based on ST-CVAE in Content-Centric Internet of Vehicles”

To: Prof. Nei Kato, Editor-in-Chief, IEEE Internet of Things Journal <eic-iotj.is@grp.tohoku.ac.jp>
Re: Response to reviewers

Dear Editor,

Thank you for allowing a resubmission of our manuscript, with an opportunity to address the reviewers’ comments.
We are uploading (a) our point-by-point response to the comments (below) (response to reviewers), (b) an updated manuscript with yellow highlighting indicating changes (under “Author’s Response Files”), and (c) a clean updated manuscript without highlights (“Main Manuscript”).

Best regards,
Youngju Nam et al.

________________________________________
Reviewer#1, Comment #1: The precaching scheme assumes RSU caches have unlimited capacity to store precached chunks. In practice, RSU storage is finite and content must compete for cache space. The entire caching literature is built around this fundamental constraint (LRU, LFU, content popularity distributions).

Author response: We thank the reviewer for this comment. In our simulation, each RSU has a 1 TB Content Store with a Least Recently Used replacement policy, so cache contention is present. We agree that more advanced replacement strategies could improve performance, but cache policy optimization is a separate research problem from the dwell time prediction and precaching decision that this paper addresses. We chose LRU as a widely used baseline to isolate the effect of our prediction framework.

Author action: The RSU cache configuration has been documented in the body text and the new simulation parameter table in Section V-A.
________________________________________
Reviewer#1, Comment #2: The paper trains models on an NVIDIA RTX 5090 GPU but proposes deployment on RSU edge nodes. A paper proposing edge deployment must demonstrate edge feasibility.

Author response: A. 모델 복잡도 측정 결과를 제시. 미래 지향적 통신 환경을 염두에 두어 RSU 스펙을 구상하였으며, 제시하는 수준의 모델 복잡도(파라미터 수, 추론 시간, 메모리, FLOPs)는 최신 MEC 서버 및 Edge GPU 환경에서 충분히 동작 가능함을 어필.

Author action: A. 파라미터 수, 추론 시간, 메모리 사용량, FLOPs를 측정한 결과를 정리하여 표로 논문에 추가 (R2-C4, R4-C2와 통합 대응).
________________________________________
Reviewer#1, Comment #3: Section V-D demonstrates that latent variance spikes for OOD samples, but no operational threshold is defined.

Author response: A. OOD 세팅의 의도 설명: 본문 내에 OOD를 추출하기 위한 세팅을 충분히 설명해 두었으며, 주된 목적은 OOD 탐지 임계값을 정하는 것이 아니라 극단적 예외 상황(tail-region)의 입력이 들어왔을 때 모델이 불확실성을 감지하고 얼마나 강건하게 방어할 수 있는지 그 의도를 보여주고자 함이었음을 디펜스.

Author action: A. 본문의 OOD 관련 서술(Section V-B 및 V-D)에서 해당 분석의 목적이 극단적 예외 상황에 대한 모델의 강건성(robustness) 증명에 있음을 명확히 하도록 문장 보강. 추가 실험이나 임계값 설정은 하지 않음 (R5-C11과 통합 대응).
________________________________________
Reviewer#2, Comment #1: The authors should include NPIWM and Winkler scores for each model to better justify the superior performance of the proposed model

Author response: We apologize if the presentation of these metrics was not sufficiently clear. The Normalized Mean Prediction Interval Width (NMPIW) for all relevant models is already explicitly provided in Table II. Regarding the Winkler Interval Score, we evaluated this metric across a wide range of target percentiles to provide a comprehensive view and presented the results in Figure 8 (Section V-B). Because NMPIW and the Winkler Interval Score are closely related metrics that both evaluate prediction interval quality, we believe the combination of the exact NMPIW values in Table II and the Winkler IS trends in Figure 8 thoroughly addresses this requirement.

Author action: We have retained the current presentation of NMPIW in Table II and the Winkler Interval Score in the corresponding figure, and clarified their relationship in our response.
________________________________________
Reviewer#2, Comment #2: The authors should compare all models with baseline without calibration such as Standard QR to justify the use of CQR.

Author response: We apologize for the confusion caused by our labeling. We have actually already included the uncalibrated Standard QR baselines in our evaluation. In Table II, the models listed under the "Deep learning (DL)" category were trained using the Pinball loss (Standard QR) without any conformal calibration. The subsequent section, "DL + CQR," shows the performance of these exact same models after applying the CQR calibration step. A direct comparison between these two sections demonstrates the impact of CQR, particularly how it reliably adjusts the intervals to meet the target Prediction Interval Coverage Probability (PICP).

Author action: We have added a clarifying sentence in Section V-B to explicitly state that the "Deep learning (DL)" category in Table II represents the uncalibrated Standard QR baselines.
________________________________________
Reviewer#2, Comment #3: The authors should include pseudocode of the proposed model to ensure reproducibility.

Author response: A. 알고리즘 재현성의 중요성에 동의하나, 논문의 페이지 제한으로 인해 본문에 싣기 어려움. 의사코드를 리뷰 답변(Response)을 통해 직접 제공하며, 논문의 재현성은 이미 공유된 GitHub 소스코드 링크를 통해 완전히 보장됨을 어필.

Author action: A. 본문에 의사코드를 추가하지 않고, 리뷰어에게 보여주기 위한 Algorithm 의사코드를 작성하여 Response에만 삽입.
________________________________________
Reviewer#2, Comment #4: The authours should include complexity analysis to justify its practicality for deployment.

Author response: A. 모델 복잡도 측정 결과 제시 (R1-C2, R4-C2와 동일 맥락). MEC 서버급에서 충분히 동작 가능함을 어필.

Author action: A. R1-C2에서 추가하는 Table에 파라미터 수, 추론 시간, 메모리 사용량, FLOPs를 포함하여 통합 대응.
________________________________________
Reviewer#2, Comment #5: It is suggested to perform simulation for at least 15 times and then use statistical analysis such as Friedman test and Holm's post hoc test to justify the better performance of the proposed model.

Author response: A. 모델의 통계적 유의성을 검증하라는 지적에 동의. 다만 Optuna를 통해 이미 파라미터 튜닝이 최적화되어 있으므로 15회 반복은 과도함. 유의미한 결과를 보여줄 수 있는 적절한 횟수(예: 5회)의 반복 실험 수행 결과를 제시하겠다고 답변.

Author action: A. 1회 테스트 후 5, 7, 15회 중 결정할 예정이나, 우선 상위 5개 모델에 대해 5회 반복 학습을 수행하여 통계 검정(Wilcoxon 등) 수행 후 논문에 반영.
________________________________________
Reviewer#3, Comment #1: Concerning the following related work on the precaching scheme in content-centric internet of vehicles, the authors should discuss it in Section II:
[References removed by Associate Editor-in-Chief]

Author response: -

Author action: -
________________________________________
Reviewer#3, Comment #2: The abbreviation ReGLU should be defined at its first instance (in Section I). Moreover, the abbreviations CCN, SUMO, CID and VID are also undefined.

Author response: We thank the reviewer for this observation.

Author action: All undefined abbreviations have been expanded at their first occurrence. "Rectified Gated Linear Unit (ReGLU)" is now defined in Section I, "Content-Centric Networking (CCN)" and "Simulation of Urban Mobility (SUMO)" in Section III-A, and "Vehicle Identifier (VID)" and "Content Identifier (CID)" in Section IV-D.
________________________________________
Reviewer#3, Comment #3: The symbols in the factor (n+delta) need to be defined (in the second bullet point of the contribution) at their first instance rather than in the equation (6).

Author response: We appreciate this suggestion. Introducing the symbols $n$ and $\delta$ in the contribution summary before their formal derivation could confuse the reader. We therefore replaced the expression $n+\delta$ with a descriptive phrase, "conservative precaching thresholds with uncertainty-driven safety margins," which conveys the same meaning without forward references. The formal definitions remain in Equations (5) and (6) of Section IV-C.

Author action: The symbolic expression in the second contribution bullet has been replaced with a semantic description in Section I.
________________________________________
Reviewer#3, Comment #4: Typo in Definition 1: which us analytically intractable…. ‘us’ should be replaced with ‘is’.

Author response: We thank the reviewer for catching this typo.

Author action: "us" has been corrected to "is" in Definition 1. We have also proofread the entire manuscript for similar errors.
________________________________________
Reviewer#4, Comment #1: First, the claim of snapshot-based data collection should be clarified more rigorously. The input feature set used in the manuscript includes vehicle position, speed, direction, distance to RSU boundaries, traffic signal phase information, average vehicular speed, communication throughput, and neighboring RSU context. It is not sufficiently clear how all these variables can be obtained solely from instantaneous communication snapshots without continuous monitoring, trajectory tracking, or infrastructure-side observation. The authors should explicitly explain the source of each feature, the frequency of its collection, and the associated communication overhead.

Author response: We appreciate the reviewer's comment. Each input feature comes from a well-defined source. The vehicle-side features $P_{req}$, $v_{req}$, and $dir_{req}$ are extracted from the standard WAVE beacon message attached to the Interest packet at the moment of the request. The current RSU features $N_{cur}$, $v_{av,cur}$, $C_{av,cur}$, $S_{cur}$, and $t_{sig,cur}$ are statistics maintained locally at each RSU, requiring no extra communication. The next-hop RSU features $N_{nxt}$, $v_{av,nxt}$, and others are obtained through a single Info Request/Reply exchange over the wired backhaul. The entire process is event-driven, triggered only when a content request occurs, and adds no persistent wireless overhead.

Author action: A paragraph explaining the source and collection mechanism of each feature has been added in Section IV-A.
________________________________________
Reviewer#4, Comment #2: Second, the feasibility of the decentralized learning mechanism should be more strongly validated. The authors claim that each RSU updates its model locally and asynchronously without relying on central aggregation. However, the experimental setup appears to rely on offline training using a large dataset and an RTX 5090 GPU. This raises concerns about the practical feasibility of the proposed approach on realistic RSU/edge hardware. Therefore, the manuscript should report model size, training/update time, inference latency, memory footprint, update frequency, and computational cost at the RSU level.

Author response: A. 모델 복잡도 측정 결과 제시 (R1-C2, R2-C4와 동일 맥락). 최신 MEC 서버/Edge 환경에서 충분히 동작 가능한 수준임을 디펜스.

Author action: A. R1-C2 대응 Table과 통합. 파라미터 수, 추론 시간, 메모리 사용량, FLOPs를 한 테이블에 정리하여 논문에 반영.
________________________________________
Reviewer#4, Comment #3: Third, the network-level evaluation should be expanded. The current simulation results suggest that the proposed method improves access delay and wasted traffic; however, the key parameters of the simulation environment are not sufficiently specified. The authors should clearly report the number of RSUs, communication range, vehicle density, cache capacity, content popularity distribution, chunk size, request generation process, backhaul capacity, and wireless channel assumptions. Moreover, the network-level results should not rely only on figures. They should be supplemented with numerical tables, confidence intervals, and sensitivity analyses under different traffic densities, cache sizes, RSU coverage settings, and backhaul capacities.

Author response: We thank the reviewer for this suggestion. We agree that the simulation parameters were not sufficiently detailed. Our environment uses a 5 x 5 Manhattan grid with 25 RSUs, vehicle density of 5 to 20 vehicles per km-lane, a 60 km/h speed limit, content requests generated by a Poisson process with a mean inter-arrival time of 600 s, 802.11p WAVE with Nakagami-$m$ fading, 1 Gbps backhaul with 1 ms latency, 1 km RSU transmission range, a catalog of 1,000,000 items following a Zipf distribution with $\alpha=0.75$, content sizes of 150 MB to 2 GB divided into 2 MB chunks, and 1 TB RSU cache with LRU replacement. The existing sensitivity heatmaps in Fig. 6 show that the ST-CVAE is robust across different structural and learning parameter settings.

Author action: A simulation parameter table and an expanded description have been added to Section V-A.
________________________________________
Reviewer#5, Comment #1: The related work does not survey conformal prediction in vehicular networks, which is a core component of the proposed system.

Author response: We thank the reviewer for pointing this out. Conformal prediction is a distribution-free framework for constructing prediction intervals with finite-sample coverage guarantees, relying only on exchangeability rather than distributional assumptions. Conformalized Quantile Regression extends this by combining quantile regression with a calibration step, producing intervals that adapt to the local uncertainty level. CP has been applied to safe autonomous navigation by Lindemann et al. (IEEE RA-L, 2023) and to time series forecasting by Zaffran et al. (ICML, 2022), but its use in vehicular precaching for uncertainty-aware resource allocation had not been explored. Our work fills this gap by using CQR to set principled safety margins for precaching decisions.

Author action: A paragraph surveying the CP literature has been added at the end of Section II, with references to Angelopoulos and Bates (2023), Lindemann et al. (2023), and Zaffran et al. (2022).
________________________________________
Reviewer#5, Comment #2: The abstract should include at least one concrete motivating statistic (e.g., cache miss rate or backhaul overhead)

Author response: We thank the reviewer for this suggestion. The proposed scheme achieves an $R^{2}$-score of 0.8153 for dwell time prediction, outperforming all ten baseline models, while reducing access delay by 18.8% and wasted backhaul traffic by 8.9% compared to the best-performing alternative.

Author action: The abstract has been revised to include these performance metrics.
________________________________________
Reviewer#5, Comment #3: Section II, Table I, column "Mobility Prediction" using O/X notation.The "O/X" binary notation in the Mobility Prediction column is ambiguous and undefined in the table caption. The caption only labels columns but does not explain what "O" and "X" signify.

Author response: We thank the reviewer for pointing out this ambiguity.

Author action: A clarification has been added to the body text stating that "O" indicates the approach incorporates mobility prediction and "X" indicates it does not.
________________________________________
Reviewer#5, Comment #4: Please proofread the whole paper; some typo errors exist, such as "centralized of semi-centralized" should read "centralized or semi-centralized." in section II

Author response: We thank the reviewer for catching this error.

Author action: The phrase has been corrected to "centralized or semi-centralized" in Section II. We have also proofread the entire manuscript for other typographical and grammatical errors.
________________________________________
Reviewer#5, Comment #5: In Section III-A the Manhattan grid topology with shortest-path routing is a highly idealized mobility model. Real urban environments exhibit non-shortest-path routing (detours, GPS re-routing, human errors). The authors should discuss how deviations from this idealized model would affect the feature vectors (R_{nxt}, R_{cur} in section IV) and whether the trained model degrades gracefully under non-Manhattan topologies.

Author response: We appreciate this observation. The Manhattan grid with shortest-path routing is an idealized scenario, and real vehicles may deviate due to GPS re-routing, road closures, or driver preferences. That said, the ST-CVAE takes instantaneous feature vectors as input, such as position, speed, and distances to RSU boundaries, rather than encoding the topology itself. It does not embed grid-specific assumptions, so it should generalize to other road layouts as long as the same features can be extracted. We recognize that empirical validation on different topologies, such as highway interchanges and irregular urban grids, remains an important future direction.

Author action: A discussion of the Manhattan grid limitation and the model's generalizability has been added to Section VI.
________________________________________
Reviewer#5, Comment #6: In section III-B The one-hour sliding window for both vav   and  Cav   is unjustified. In high-density urban scenarios, traffic conditions can shift dramatically within minutes (e.g., post-accident or rush-hour onset). The choice of a 1-hour window appears arbitrary — no sensitivity analysis is provided for this parameter, and it conflicts with the paper's own emphasis on capturing rapidly changing vehicular dynamics.

Author response: We thank the reviewer for this question. The one-hour window applies only to the coarse contextual features $v_{av}$ and $C_{av}$, which represent background traffic statistics. The fine-grained temporal dynamics of each request, including instantaneous velocity, traffic signal phase, and remaining phase time, are captured by the per-snapshot features $v_{req}$, $S_{cur}$, and $t_{sig,cur}$ at the exact moment of each content request. Because the time-critical information is encoded independently of the sliding window, the model's sensitivity to the window length is limited.

Author action: A clarifying sentence explaining this design rationale has been added in Section III-B.
________________________________________
Reviewer#5, Comment #7: In secition IV- A  dir_{req} requires more clarification.  In a Manhattan grid, a vehicle approaching an RSU at an intersection can be traveling from four cardinal directions, each implying distinct dwell-time distributions. Collapsing this to a binary "before/after intersection" indicator discards directional information and likely degrades prediction accuracy at multi-lane intersections. The authors should justify why a richer directional encoding (e.g., angle or cardinal direction) was not used.

Author response: We appreciate this suggestion. The binary $dir_{req}$ was chosen because, in our network where RSUs sit at intersections, the main factor affecting dwell time is whether the vehicle will be stopped by a traffic signal. A vehicle that has not yet crossed the intersection may wait for a red phase and stay much longer, while one that has already passed continues without stopping. Richer directional encodings such as cardinal direction or heading angle could add information, but the spatial distance features $D_{lev,cur}$, $D_{arr,nxt}$, and $D_{lev,nxt}$ already capture directional context implicitly through the remaining travel distances to each RSU boundary.

Author action: A paragraph explaining this design rationale has been added to Section IV-A.
________________________________________
Reviewer#5, Comment #8: In equation (1),β_ELBO formulation The notation is inconsistent: the KL term uses qΦ(Z∗∣X,Y)∥pΨ(Z∣X) but the posterior encoder is parameterized by \Phi while the prior encoder is parameterized by \Psi,  yet in the reconstruction term, Z∗∼qΨ is written (note the subscript switch). This appears to be a typo ( q_\Phi vs. q_\Psi) that propagates through Equations (2) and (3). The authors must audit and resolve all encoder subscript notation throughout Section IV-B.

Author response: We thank the reviewer for identifying this inconsistency.

Author action: The reviewer is correct. In Equation (1), the reconstruction term used $q_{\Psi}$ where it should have been $q_{\Phi}$ for the posterior encoder. We have audited all encoder subscripts in Section IV-B and corrected Equation (1) so that the posterior encoder is consistently written as $q_{\Phi}(Z^{*}|X,Y)$ and the prior encoder as $p_{\Psi}(Z|X)$. We also found and fixed a related error in Definition 1, where $p(Y|X|Z)$ had a redundant conditioning bar and should read $p(Y|X,Z)$. Equations (2) and (3) were already consistent.
________________________________________
Reviewer#5, Comment #9: Section V-B,: "ST-CVAE + CQR" in Table II and the reference to conformal prediction thresholds in Section V-C. The paper lists "Conformal Prediction" as a key Index Term and contribution, yet the mechanics of CQR application to the ST-CVAE output are never explicitly described in the paper body. How is the CQR calibration set constructed? What is the calibration set size? Is the exchangeability assumption of CQR valid for this non-i.i.d. vehicular time-series data? These are non-trivial questions that directly affect the coverage guarantee claimed by the PICP result.

Section V-A: authors claim "…a robust dataset of 375,400 independent request snapshots. The claim of "independent" snapshots is questionable. Multiple requests from the same vehicle at the same RSU at different times are temporally correlated, violating the i.i.d. assumption required for the CQR coverage guarantee.

Author response: We thank the reviewer for this important comment. We agree that the CQR procedure was not described in enough detail. The procedure works as follows. The dataset is split into training, calibration, and test sets. The ST-CVAE is trained on the training set. On the calibration set, nonconformity scores are computed for each sample. The calibration quantile $\hat{Q}$ is then determined from these scores. At inference, the prediction interval is constructed by adjusting the quantile outputs with $\hat{Q}$. Regarding the exchangeability assumption, while vehicular request snapshots have temporal correlations, each snapshot comes from a different vehicle at a different location, which provides spatial and contextual diversity. The empirical PICP results confirm that the nominal coverage level is consistently met, with 0.9001 achieved at the 90% target.

Author action: A subsection on CQR has been added at the end of Section IV-B, describing the calibration procedure and discussing the exchangeability assumption.
________________________________________
Reviewer#5, Comment #10: Equation (6) The safety buffer δ  is introduced as a fixed heuristic without any principled derivation. This directly contradicts the paper's core claim of being "uncertainty-aware" — if the uncertainty is already quantified via the predictive distribution and CQR intervals, δ should be a function of the prediction interval width, not a hardcoded constant. The authors should derive δ  from the conformal prediction bound or at minimum provide a sensitivity analysis over different δ values and their impact on wasted traffic vs. access delay.

Author response: A. CQR과 delta의 의미적 차이 디펜스: CQR은 학습 모델 자체의 불확실성에 대한 캘리브레이션인 반면, $\delta$는 통신 네트워크 관점에서 precaching의 access delay를 방어하기 위해 최소한의 chunk를 확보하는 물리적인 가드밴드/마진임을 설명. 따라서 예측 불확실성에 비례하는 값이 아닌 고정된 최소 여유값으로 두는 것이 타당함을 디펜스.

Author action: A. 수식을 변경하거나 재실험하지 않고, Section IV-C의 $\delta$ 정의 부분에 해당 상수가 통신적 관점의 최소 가드밴드이자 access delay 방어 장치임을 명시하는 설명 보강.
________________________________________
Reviewer#5, Comment #11: Section V-B, OOD analysis: "defining out-of-distribution (OOD) samples as the extreme top and bottom 10% of the dwell time…"  Defining OOD as the top/bottom 10% of the same dataset's distribution is a form of in-distribution tail analysis, not true OOD evaluation. Genuine OOD generalization should be tested on data from a different city topology, a different time period (e.g., weekend vs. weekday), or a different vehicle density regime not seen during training. The current OOD protocol measures nothing more than performance on rare-but-observed samples, and the claim that the model "knows what it does not know" is therefore unsupported.

Author response: A. OOD 세팅의 의도 설명: 완벽한 진성 OOD를 정의하는 것이 목적이 아니라, 기존 데이터 내에서도 극단적인 꼬리 분포(tail-region) 예외 상황이 발생했을 때 모델이 이를 불확실성으로 감지하고 얼마나 강건하게 대처할 수 있는지를 보여주기 위한 의도였음을 디펜스.

Author action: A. 본문의 관련 서술을 다듬어 해당 분석의 목적이 모델의 robustness와 fail-safe 능력을 보여주기 위함임을 강조. 새로운 OOD 데이터 분할이나 추가 실험은 진행하지 않음 (R1-C3와 통합 대응).
________________________________________
Note: References suggested by reviewers should only be added if it is relevant to the article and makes it more complete. Excessive cases of recommending non-relevant articles should be reported to ieeeaccesseic@ieee.org
