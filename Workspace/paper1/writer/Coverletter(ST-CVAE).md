Cover Letter
[14 April, 2026]
IEEE Internet of Things Journal
Dear Editor-in-Chief,
We are pleased to submit our manuscript entitled "Uncertainty-Aware Precaching Scheme based on ST-CVAE in Content-Centric Internet of Vehicles" for consideration as a regular paper in the IEEE Internet of Things Journal.
Modern vehicular networks face unprecedented strain from bandwidth-heavy services. While edge precaching in the Content-Centric Internet of Vehicles (CIoV) mitigates handover disruptions, existing strategies rely on deterministic predictions and continuous trajectory tracking. This incurs prohibitive communication overhead and fails to capture the stochastic, multi-modal nature of urban traffic (e.g., stopping at red lights vs. passing through green lights), invariably leading to severe backhaul waste or playback stalls.
In this manuscript, we present a paradigm shift by introducing a Spatio-Temporal Conditional Variational Autoencoder (ST-CVAE) that explicitly captures and quantifies the inherent uncertainty of vehicle dwell times. The core innovations and contributions of our work include:
	Snapshot-based Efficient Data Collection: We eliminate the need for continuous periodic trajectory reporting by relying exclusively on instantaneous communication snapshots, drastically reducing wireless congestion.
	Uncertainty-aware Generative Prioritization: Our ST-CVAE models the full conditional probability distribution of dwell times. Utilizing conformal prediction and a tailored ReGLU-augmented Residual Backbone, it sets mathematical precaching thresholds (n+δ) that preserve service continuity and mitigate backhaul waste.
	Decentralized, Asynchronous Learning: Each Roadside Unit (RSU) independently trains its predictive model using local features. Our asynchronous update protocol ensures zero service downtime and offers a scalable solution for dense urban grids.
Evaluated on a dense SUMO Manhattan grid dataset comprising 375,400 snapshots, our ST-CVAE significantly outperforms 10 state-of-the-art deterministic and probabilistic baselines (including NGBoost, TabPFN, and ResNet) with superior accuracy (R^2-score of 0.8153), tighter safety bounds, and substantially lower network access delay.
By marrying advanced generative AI with content-centric networking, our practical framework addresses fundamental mobility challenges directly aligned with the scope of the IEEE Transactions on Wireless Communications. We confirm this manuscript is original, has not been published previously, and is not under consideration elsewhere. All authors have approved submission to your esteemed journal. 
Thank you for your time, consideration, and editorial leadership. We look forward to your feedback.
Sincerely,
Porf. Youngju Nam
the School of Software, Kunsan National University, Gunsan, South Korea
Email: imnyj@kunsan.ac.kr
