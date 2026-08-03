# Introduction Draft (intro.md)

## Paragraph 1: The IoT Context and Systemic Bottleneck

The development of the Internet of Vehicles (IoV) and autonomous driving has increased vehicular data generation. According to the Ericsson Mobility Report, global mobile network data traffic is projected to reach 515 Exabytes per month by 2031 \cite{ericsson2026}. To deliver high-bandwidth content to moving vehicles without overloading the core network, proactive edge caching via Road-Side Units (RSUs) in Content-Centric Vehicular Networks (CCVNs) is utilized as a foundational infrastructure \cite{1,2,3}. However, the Vehicle-to-Infrastructure (V2I) transmission window is constrained by the dynamic dwell time of the vehicle at the intersection, which fluctuates between 100 to 300 seconds due to traffic signal phases and queueing densities. If this residency duration is not accurately predicted, the RSU misallocates local resources, resulting in either over-prefetching that wastes edge storage and backhaul bandwidth, or under-prefetching that causes service interruptions when vehicles exit the coverage area \cite{4,5,6}. Therefore, real-time dwell-time prediction at the edge is a prerequisite for optimizing proactive caching schedules and ensuring service continuity in CCVNs.

## Paragraph 2: The Research Gap

Designing a mobility prediction model for proactive edge caching requires balancing low-latency constraints with the need for adaptability to local traffic dynamics. To maximize predictive accuracy, recent sequence-based forecasting architectures and federated learning frameworks extract continuous temporal dependencies \cite{9,10}. However, the continuous uplink tracking and repetitive parameter exchanges required by these models increase V2I bandwidth usage and introduce buffering delays, which contradicts the event-driven nature of immediate edge caching \cite{14,15}. Conversely, gradient-boosted decision trees (GBDTs) can eliminate tracking latency by executing inferences on a single snapshot without historical buffering. Despite their communication efficiency, these tree ensembles are constrained by static global weights, limiting their capacity to adapt to the localized spatio-temporal conditions of individual intersections. Furthermore, mapping heterogeneous tabular data directly through standard deep neural networks results in gradient interference and degraded learning performance. Therefore, existing methodologies remain confined within a structural trade-off, where they either prioritize communication efficiency at the cost of adaptive local precision, or vice versa.

## Paragraph 3: The Solution and Contributions

To address these structural and algorithmic limitations, this paper proposes the Hybrid Spatio-Temporal Multi-Branch Attention Network (H-ST-MBAN) for proactive edge caching in CCVNs. The primary contributions of this paper are organized as follows:

*   **Data Collection Protocol:** We design a specialized vehicular communication protocol and edge table management scheme that autonomously constructs local datasets by piggybacking state variables onto content request packets and logging targets via asynchronous exit events.
*   **Event-Driven Snapshot Inference:** We propose an event-driven regression framework that predicts intersection dwell time using a single vehicular snapshot extracted from the initial content request packet, thereby eliminating the need for continuous historical buffering.
*   **Dual-Stream Architecture:** To process this snapshot data without gradient interference, we design a dual-stream architecture that combines a gradient boosting ensemble with a multi-branch neural network to isolate and learn the complex spatio-temporal dynamics of heterogeneous traffic variables.
*   **Decentralized Local Fine-Tuning:** We introduce a decentralized updating strategy that fine-tunes the network using strictly local intersection data, allowing the model to adapt to localized traffic variations without incurring uplink parameter exchange overheads.
*   **Simulation Validation:** We validate the proposed framework using microscopic traffic traces generated via the SUMO simulator to confirm that the localized architecture maintains target cache hit rates while satisfying the strict latency constraints of vehicular environments.

\begin{thebibliography}{31}

\bibitem{ericsson2026}
Ericsson, ``Ericsson Mobility Report,'' \emph{Ericsson}, June 2026. [Online]. Available: https://www.ericsson.com/en/reports-and-papers/mobility-report/reports/june-2026

\bibitem{1}
Z. Su, Y. Hui and Q. Yang, ``The Next Generation Vehicular Networks: A Content-Centric Framework,'' \emph{IEEE Wireless Communications}, vol. 24, no. 1, pp. 60--66, 2017.

\bibitem{2}
M. Wang, J. Wu, G. Li, J. Li, Q. Li and S. Wang, ``Toward mobility support for information-centric IoV in smart city using fog computing,'' \emph{2017 IEEE International Conference on Smart Energy Grid Engineering (SEGE)}, Oshawa, ON, Canada, 2017, pp. 357--361.

\bibitem{3}
Y. Nam, H. Choi and E. Lee, ``Content Storage Management and Precaching Scheme in Content-Centric-Network-Based Internet of Vehicles,'' \emph{IEEE Internet of Things Journal}, vol. 12, no. 9, pp. 12927--12947, 2025.

\bibitem{4}
Z. Su, Y. Hui, Q. Xu, T. Yang, J. Liu and Y. Jia, ``An Edge Caching Scheme to Distribute Content in Vehicular Networks,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 67, no. 6, pp. 5346--5356, 2018.

\bibitem{5}
W. Huang, T. Song, Y. Yang and Y. Zhang, ``Cluster-Based Cooperative Caching With Mobility Prediction in Vehicular Named Data Networking,'' \emph{IEEE Access}, vol. 7, pp. 23442--23458, 2019.

\bibitem{6}
B. Feng, C. Feng, D. Feng, Y. Wu and X. Xia, ``Proactive Content Caching Scheme in Urban Vehicular Networks,'' \emph{IEEE Transactions on Communications}, vol. 71, no. 7, pp. 4165--4180, 2023.

\bibitem{9}
J. Cheng, K. Li, Y. Liang, L. Sun, J. Yan and Y. Wu, ``Rethinking Urban Mobility Prediction: A Multivariate Time Series Forecasting Approach,'' \emph{IEEE Transactions on Intelligent Transportation Systems}, vol. 26, no. 2, pp. 2543--2557, 2025.

\bibitem{10}
G. Yu, J. Wu, R. Liu, Y. He, Z. Chen and J. Pan, ``Joint Cooperative Caching and UAV Trajectory Optimization Based on Mobility Prediction in the Internet of Connected Vehicles,'' \emph{IEEE Transactions on Intelligent Transportation Systems}, vol. 25, no. 11, pp. 17392--17406, 2024.

\bibitem{14}
X. Zhang, Z. Chang, T. Hu, W. Chen, X. Zhang and G. Min, ``Vehicle Selection and Resource Allocation for Federated Learning-Assisted Vehicular Network,'' \emph{IEEE Transactions on Mobile Computing}, vol. 23, no. 5, pp. 3817--3829, 2024.

\bibitem{15}
R. Liu and J. Pan, ``CRS: A Privacy-Preserving Two-Layered Distributed Machine Learning Framework for IoV,'' \emph{IEEE Internet of Things Journal}, vol. 11, no. 1, pp. 1080--1095, 2024.

\end{thebibliography}
