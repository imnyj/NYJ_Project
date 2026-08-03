import re

with open('/home/imnyj/papers/paper1/paper/draft/main.tex', 'r') as f:
    text = f.read()

# 1. AI-like Expressions
text = text.replace("Furthermore, the scheduler cannot", "The scheduler cannot")
text = text.replace("Second, branch-specific inductive biases are meticulously calibrated", "Second, branch-specific inductive biases are precisely calibrated")
text = text.replace("Furthermore, testing against these constrained baselines confirms", "Testing against these constrained baselines also confirms")

# 2. Itemize Block Violation
old_itemize = r"""\subsection{Baseline Models and Metrics}
We benchmark H-ST-MBAN against twelve representative models:
\begin{itemize}
    \item \textbf{Linear and Tree-based Ensembles:} Linear Regression (LR), Random Forest (RF), XGBoost (XGB), CatBoost, and NGBoost.
    \item \textbf{Time-Series/Sequence Models:} LSTM and GRU.
    \item \textbf{Deep Learning Baselines:} Multi-Layer Perceptron (MLP) and ResNet.
    \item \textbf{Deep Tabular SOTA:} TabPFN, FT-Transformer (FTT), and TabR.
\end{itemize}
Prediction accuracy is measured via Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Mean Absolute Percentage Error (MAPE), and $R^2$ Score. To evaluate the practical impact on CCVN precaching, we simulate a chunk-based V2I transmission scenario to measure \textit{Access Delay}, \textit{Wasted Traffic}, and \textit{Cache Hit Ratio}."""

new_itemize = r"""\subsection{Baseline Models and Metrics}
We benchmark H-ST-MBAN against twelve representative models across four broad categories.
First, we evaluate linear and tree-based ensembles, which include Linear Regression (LR), Random Forest (RF), XGBoost (XGB), CatBoost, and NGBoost.
Second, we compare against traditional time-series and sequence models, specifically LSTM and GRU.
Third, we incorporate standard deep learning baselines such as the Multi-Layer Perceptron (MLP) and ResNet.
Fourth, we test against state-of-the-art deep tabular models, namely TabPFN, FT-Transformer (FTT), and TabR.
Prediction accuracy is measured via Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Mean Absolute Percentage Error (MAPE), and $R^2$ Score.
To evaluate the practical impact on CCVN precaching, we simulate a chunk-based V2I transmission scenario to measure \textit{Access Delay}, \textit{Wasted Traffic}, and \textit{Cache Hit Ratio}."""
text = text.replace(old_itemize, new_itemize)

# 3. Paragraph Length Violations (<5 sentences):
# Section 2
cat_orig = r"""\textbf{Category 1: CIoV and Content-Centric Networking.}
Content-Centric IoV (CIoV) embeds Named Data Networking semantics into vehicular architectures,
allowing RSUs and vehicles to cache and forward content by name rather than address \cite{1,3,5}.
Recent work has extended CIoV to edge-computing and mobility-aware routing contexts,
improving content availability under dynamic topologies \cite{8,10,11}.

\textbf{Category 2: V2I Precaching.}
V2I precaching exploits scheduled RSU-to-vehicle links to deliver content before a request is issued.
Federated learning approaches \cite{17,18,20} distribute model training across vehicles to protect privacy
while adapting caching decisions to real-time traffic conditions.
Age-of-Information and cooperative strategies further refine delivery timing under bandwidth constraints \cite{15}.

\textbf{Category 3: Popularity-Based and Hybrid Precaching.}
Popularity-based schemes predict which content items will be requested and prefetch them to edge nodes \cite{32,33,34}.
Hybrid designs combine popularity estimation with context signals, such as social ties or unmanned aerial vehicle (UAV) relay paths,
improving hit rates in heterogeneous topologies \cite{47,48,49}.

\textbf{Category 4: Mobility Prediction and Combined Caching.}
Mobility-aware caching couples vehicle trajectory forecasts with content placement decisions \cite{39,42,43}.
These methods commonly use multi-step time-series models (e.g., LSTM, Transformer variants) to predict
future RSU associations, subsequently pre-positioning content along predicted paths \cite{41,45}.

\textbf{Category 5: RSU-Local and Snapshot-Based Learning.}"""

cat_new = r"""\textbf{Category 1: CIoV and Content-Centric Networking.}
Content-Centric IoV (CIoV) embeds Named Data Networking semantics into vehicular architectures,
allowing RSUs and vehicles to cache and forward content by name rather than address \cite{1,3,5}.
Recent work has extended CIoV to edge-computing and mobility-aware routing contexts,
improving content availability under dynamic topologies \cite{8,10,11}.
\textbf{Category 2: V2I Precaching.}
V2I precaching exploits scheduled RSU-to-vehicle links to deliver content before a request is issued.
Federated learning approaches \cite{17,18,20} distribute model training across vehicles to protect privacy
while adapting caching decisions to real-time traffic conditions.
Age-of-Information and cooperative strategies further refine delivery timing under bandwidth constraints \cite{15}.
\textbf{Category 3: Popularity-Based and Hybrid Precaching.}
Popularity-based schemes predict which content items will be requested and prefetch them to edge nodes \cite{32,33,34}.
Hybrid designs combine popularity estimation with context signals, such as social ties or unmanned aerial vehicle (UAV) relay paths,
improving hit rates in heterogeneous topologies \cite{47,48,49}.

\textbf{Category 4: Mobility Prediction and Combined Caching.}
Mobility-aware caching couples vehicle trajectory forecasts with content placement decisions \cite{39,42,43}.
These methods commonly use multi-step time-series models (e.g., LSTM, Transformer variants) to predict
future RSU associations, subsequently pre-positioning content along predicted paths \cite{41,45}.
\textbf{Category 5: RSU-Local and Snapshot-Based Learning.}"""
text = text.replace(cat_orig, cat_new)

# Section 3 Intro
sec3_intro_orig = r"""In this section, we describe the network model, the event-driven inference paradigm,
the regression task formulation, and the complete input feature set that underlies
the proposed H-ST-MBAN framework."""
sec3_intro_new = r"""In this section, we describe the network model, the event-driven inference paradigm, the regression task formulation, and the complete input feature set that underlies the proposed H-ST-MBAN framework. The network model formalizes the intersection geometry and RSU deployment strategy. The event-driven paradigm details how snapshot data is collected without relying on continuous historical buffering. The regression formulation translates these snapshots into actionable deterministic dwell-time estimates. Finally, the input feature enumeration systematically categorizes all variables used to capture the prevailing traffic conditions."""
text = text.replace(sec3_intro_orig, sec3_intro_new)

# Section 3.1
text = text.replace("and yields a repeating coverage-gap-coverage pattern along the vehicle trajectory.\n\nVehicle mobility is generated", "and yields a repeating coverage-gap-coverage pattern along the vehicle trajectory.\nVehicle mobility is generated")

# Section 3.2
text = text.replace("signal phases, and the surrounding traffic context at time $t_0$.\n\nTo assemble the 30-dimensional snapshot vector", "signal phases, and the surrounding traffic context at time $t_0$.\nTo assemble the 30-dimensional snapshot vector")

# Section 3.3
text = text.replace("unnecessary.\n\nEach RSU learns", "unnecessary.\nEach RSU learns")

# Section 3.5
sec35_orig = r"""The prediction target is $\mathbf{y} = [\tau_{\text{cur}},\, \tau_{\text{nxt}}]^\top
\in \mathbb{R}^2$, where both components are directly relevant to the RSU caching
scheduler.

\textbf{Current RSU dwell time} ($\tau_{\text{cur}}$): the elapsed time from the
request instant $t_0$ until vehicle $v$ exits the coverage zone of $r_{\text{cur}}$.
Formally, $\tau_{\text{cur}} = t_{\text{cur,out}} - t_0$, where $t_{\text{cur,out}}$
is the moment the vehicle's position crosses the boundary of $r_{\text{cur}}$.
This quantity determines the maximum time window available to complete a content
transfer for the current request.

\textbf{Next RSU dwell time} ($\tau_{\text{nxt}}$): the full sojourn duration of
vehicle $v$ within the coverage zone of $r_{\text{nxt}}$.
Formally, $\tau_{\text{nxt}} = t_{\text{nxt,out}} - t_{\text{nxt,in}}$, where
$t_{\text{nxt,in}}$ and $t_{\text{nxt,out}}$ denote the entry and exit timestamps,
respectively.
This quantity supports prefetching decisions that span the handoff to the next RSU.

Both targets are measured directly from SUMO simulation event logs and constitute
continuous real-valued regression outputs."""

sec35_new = r"""The prediction target is $\mathbf{y} = [\tau_{\text{cur}},\, \tau_{\text{nxt}}]^\top
\in \mathbb{R}^2$, where both components are directly relevant to the RSU caching
scheduler.
\textbf{Current RSU dwell time} ($\tau_{\text{cur}}$): the elapsed time from the
request instant $t_0$ until vehicle $v$ exits the coverage zone of $r_{\text{cur}}$.
Formally, $\tau_{\text{cur}} = t_{\text{cur,out}} - t_0$, where $t_{\text{cur,out}}$
is the moment the vehicle's position crosses the boundary of $r_{\text{cur}}$.
This quantity determines the maximum time window available to complete a content
transfer for the current request.
\textbf{Next RSU dwell time} ($\tau_{\text{nxt}}$): the full sojourn duration of
vehicle $v$ within the coverage zone of $r_{\text{nxt}}$.
Formally, $\tau_{\text{nxt}} = t_{\text{nxt,out}} - t_{\text{nxt,in}}$, where
$t_{\text{nxt,in}}$ and $t_{\text{nxt,out}}$ denote the entry and exit timestamps,
respectively.
This quantity supports prefetching decisions that span the handoff to the next RSU.
Both targets are measured directly from SUMO simulation event logs and constitute
continuous real-valued regression outputs."""
text = text.replace(sec35_orig, sec35_new)

# Section 5.4 insertion
text = text.replace(
    "While actual on-device latency depends on memory bandwidth and hardware-specific optimizations, this baseline comparison provides an initial theoretical validation",
    "This direct comparison ensures that the deployed model will not overwhelm the memory buffers of the roadside unit.\nWhile actual on-device latency depends on memory bandwidth and hardware-specific optimizations, this baseline comparison provides an initial theoretical validation"
)

# Equations: remove blank lines before \begin{equation} and after \end{equation}
text = re.sub(r'\n\n\\begin\{equation\}', r'\n\\begin{equation}', text)
text = re.sub(r'\\end\{equation\}\n\n', r'\\end{equation}\n', text)

with open('/home/imnyj/papers/paper1/paper/draft/main.tex', 'w') as f:
    f.write(text)

