import re

with open('main.tex', 'r') as f:
    content = f.read()

# Fix newline and insert Baseline Models
old_text = r"Standard scaling is applied exclusively using the statistics derived from the training set to prevent any forward-looking bias during the validation and testing phases\. \\subsection\{Learning Curves\}"

new_text = r"""Standard scaling is applied exclusively using the statistics derived from the training set to prevent any forward-looking bias during the validation and testing phases.

\subsection{Baseline Models}
To rigorously evaluate the predictive performance of H-ST-MBAN, we benchmark the proposed architecture against four mobility prediction baselines. First, we compare against a Conditional Variational Autoencoder (ST-CVAE) augmented with posterior information, which handles spatial-temporal uncertainty by learning a probabilistic latent space to generate multimodal future paths \cite{32}. Second, we incorporate a Time-Frequency Wavelet Transformer model designed to capture both time and frequency domain features through attention mechanisms, serving as a robust sequence-based long-term forecaster \cite{33}. Third, we evaluate a Gated Recurrent Unit (GRU) neural network, which efficiently processes sequential movement data and temporal dependencies while maintaining lower computational overhead than traditional recurrent architectures \cite{34}. Fourth, we include a fundamental Long Short-Term Memory (LSTM) framework that learns historical motion states and environmental cues to simultaneously forecast future positions and driver intentions \cite{35}. These representative models span generative, attention-based, and recurrent sequence paradigms, providing a comprehensive evaluation baseline for assessing the real-time deterministic regression capabilities of H-ST-MBAN.

\subsection{Learning Curves}"""

content = content.replace("Standard scaling is applied exclusively using the statistics derived from the training set to prevent any forward-looking bias during the validation and testing phases. \\subsection{Learning Curves}", new_text)


# Append Bibliography
bib_items = r"""\bibitem{32}
Yuxuan Wu, Le Wang, Sanping Zhou, Ning Ding, Gang Hua, ``Posterior Augmented CVAE for Pedestrian Trajectory Prediction with Momentary Observation,'' \textit{IEEE Transactions on Multimedia}, 2026, doi: 10.1109/tmm.2026.3673507.

\bibitem{33}
Marina Kurilova, Howard Li, ``Time-Frequency Wavelet Transformer Forecasting for Hypersonic Glide Vehicle Trajectory Prediction,'' \textit{2026 IEEE Aerospace Conference}, 2026, doi: 10.1109/aero66936.2026.11519972.

\bibitem{34}
Yue Liu, Hongjian Wang, Kai Zhang, Jingfei Ren, ``UUV Trajectory Prediction Based on GRU Neural Network,'' \textit{2021 40th Chinese Control Conference (CCC)}, 2021, doi: 10.23919/ccc52363.2021.9549995.

\bibitem{35}
Fatimetou El Jili, ``An Effective Driver Intention and Trajectory Prediction for Autonomous Vehicle based on LSTM,'' \textit{Proceedings of the 13th International Conference on Agents and Artificial Intelligence}, 2021, doi: 10.5220/0010321710901096.

\end{thebibliography}"""

content = content.replace("\\end{thebibliography}", bib_items)

with open('main.tex', 'w') as f:
    f.write(content)

