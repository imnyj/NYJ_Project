Cover Letter
[Date]
IEEE Transactions on Intelligent Transportation Systems
Dear Editor-in-Chief,

We are pleased to submit our manuscript entitled "Edge-Assisted Content Precaching via Hybrid Spatio-Temporal Multi-Branched Attention Networks in CCVNs" for consideration as a regular paper in the IEEE Transactions on Intelligent Transportation Systems.

Modern vehicular networks face unprecedented strain from bandwidth-heavy services. While edge precaching mitigates handover disruptions, existing proactive strategies rely on continuous trajectory tracking or probabilistic sampling. This continuous tracking incurs prohibitive communication overhead, and directly mapping heterogeneous traffic variables often leads to gradient conflicts, limiting real-time adaptability at the network edge. 

In this manuscript, we present a paradigm shift by introducing a Hybrid Spatio-Temporal Multi-Branch Attention Network (H-ST-MBAN) that executes deterministic dwell-time regression from a single communication snapshot. The core innovations and contributions of our work include:

- Single-Snapshot Deterministic Regression: We eliminate the need for continuous periodic trajectory reporting by relying exclusively on instantaneous communication snapshots, drastically reducing uplink congestion while ensuring low-latency inference.
- Independent Residual Branches: To handle heterogeneous tabular data effectively, kinematic, traffic control, and social variables are partitioned into independent residual branches. This structurally isolates inputs and prevents gradient conflicts common in early-fusion architectures.
- Hybrid Model Architecture: Our framework fuses the unified neural network representations via a three-token Multi-Head Attention (MHA) layer with an XGBoost-based prior stream. A learnable gating mechanism merges these streams, combining complex feature interactions with sharp decision boundaries.
- Periodic Local Adaptation: We propose a localized adaptation strategy that piggybacks ground-truth exit timestamps onto V2I termination signals. Each Roadside Unit (RSU) independently fine-tunes its model without continuous central cloud exchanges, requiring minimal computational overhead.

Evaluated on a comprehensive SUMO Manhattan grid dataset comprising over 1,000,000 snapshot samples, H-ST-MBAN significantly outperforms 12 state-of-the-art baseline models, yielding a superior Mean Absolute Error (MAE) of 44.32 s. By accurately forecasting dwell times and utilizing a dynamic safety margin, the proposed framework eliminates over-prefetching waste and ultimately achieves an outstanding 90.7% average cache hit ratio.

By marrying advanced hybrid neural architectures with content-centric networking, our practical framework addresses fundamental mobility challenges directly aligned with the scope of the IEEE Transactions on Intelligent Transportation Systems. We confirm this manuscript is original, has not been published previously, and is not under consideration elsewhere. All authors have approved submission to your esteemed journal. 

Thank you for your time, consideration, and editorial leadership. We look forward to your feedback.

Sincerely,

Prof. Euisin Lee (Corresponding Author)
School of Information and Communication Engineering
Chungbuk National University, Cheongju, South Korea
Email: eslee@chungbuk.ac.kr

(Alternatively, on behalf of the authors:
Prof. Youngju Nam 
School of Software, Kunsan National University, Gunsan, South Korea
Email: imnyj@kunsan.ac.kr)
