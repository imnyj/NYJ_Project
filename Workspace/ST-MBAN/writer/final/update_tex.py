import re

with open('main.tex', 'r') as f:
    content = f.read()

# Math replacements
math_replacements = [
    (r"tensor as \$\\mathbf\{Z\} = \[Z_k;\\, Z_t;\\, Z_s\] \\in \\mathbb\{R\}\^\{3 \\times d_\\text\{branch\}\}\$, and",
     "tensor as\n\\begin{equation}\n\\mathbf{Z} = [Z_k;\\, Z_t;\\, Z_s] \\in \\mathbb{R}^{3 \\times d_\\text{branch}}\n\\end{equation}\nand"),
    
    (r"denoted as \$P_\\text\{XGB\} = \\text\{XGBoost\}\(\\mathbf\{X\}\) \\in \\mathbb\{R\}\^2\$\.",
     "denoted as\n\\begin{equation}\nP_\\text{XGB} = \\text{XGBoost}(\\mathbf{X}) \\in \\mathbb{R}^2.\n\\end{equation}"),
    
    (r"formulated as \$Z_s = \\text\{ResBlock\}_\\text\{S\}\\!\\left\(W_S\\,\(\\mathbf\{a\} \\odot \\mathbf\{x\}\^S\) \+ b_S\\right\)\$,",
     "formulated as\n\\begin{equation}\nZ_s = \\text{ResBlock}_\\text{S}\\!\\left(W_S\\,(\\mathbf{a} \\odot \\mathbf{x}^S) + b_S\\right),\n\\end{equation}"),
    
    (r"formulated as \$\\mathbf\{a\} = \\sigma\\!\\left\(W_2 \\cdot \\text\{ReLU\}\(W_1 \\cdot \\mathbf\{x\}\^S \+ b_1\) \+ b_2\\right\)\$,",
     "formulated as\n\\begin{equation}\n\\mathbf{a} = \\sigma\\!\\left(W_2 \\cdot \\text{ReLU}(W_1 \\cdot \\mathbf{x}^S + b_1) + b_2\\right),\n\\end{equation}"),
     
    (r"computed as \$\\text\{head\}_i = \\text\{softmax\}\\!\\left\(\\frac\{Q_i K_i\^\\top\}\{\\sqrt\{d_k\}\}\\right\) V_i\$\.",
     "computed as\n\\begin{equation}\n\\text{head}_i = \\text{softmax}\\!\\left(\\frac{Q_i K_i^\\top}{\\sqrt{d_k}}\\right) V_i.\n\\end{equation}"),
     
    (r"calculated as \$N_\{cur, chunk\} = \\lfloor \\frac\{\\eta \\cdot B_\{avg\}\^\{cur\} \\cdot t_\{cur, dw\}\}\{S_\{chunk\}\} \\rfloor\$\.",
     "calculated as\n\\begin{equation}\nN_{cur, chunk} = \\left\\lfloor \\frac{\\eta \\cdot B_{avg}^{cur} \\cdot t_{cur, dw}}{S_{chunk}} \\right\\rfloor.\n\\end{equation}"),
     
    (r"formulated as \$\\eta\(t\) = \\alpha \\cdot \\bar\{P\}_\{success\}\(t\) - \\beta \\cdot f\(\\sigma_\{channel\}\^2\(t\)\)\$, where",
     "formulated as\n\\begin{equation}\n\\eta(t) = \\alpha \\cdot \\bar{P}_{success}(t) - \\beta \\cdot f(\\sigma_{channel}^2(t)),\n\\end{equation}\nwhere")
]

for old, new in math_replacements:
    content = re.sub(old, lambda m, n=new: n, content)

# 2. Related Work update
content = content.replace("\\paragraph{Category 1: CIoV and Content-Centric Networking} Content-Centric IoV (CIoV) embeds", "Regarding network architectures and content distribution mechanisms, Content-Centric IoV (CIoV) embeds")
content = content.replace("\\paragraph{Category 2: V2I Precaching} V2I precaching exploits", "In the domain of content delivery triggers, V2I precaching exploits")
content = content.replace("\\paragraph{Category 3: Popularity-Based and Hybrid Precaching} Popularity-based schemes predict", "Concerning the metrics used to schedule caching, popularity-based schemes predict")
content = content.replace("\\paragraph{Category 4: Mobility Prediction and Combined Caching} Mobility-aware caching couples", "Addressing the integration of vehicle movement, mobility-aware caching couples")
content = content.replace("\\paragraph{Category 5: RSU-Local and Snapshot-Based Learning} A growing body of work deploys", "Focusing on the computational constraints at the network edge, a growing body of work deploys")


# 3. Evaluation update
content = content.replace("\\subsection{G1: Learning Curves}", "\\subsection{Learning Curves}")
content = content.replace("G1 (Learning Curves): ", "")
content = content.replace("\\subsection{G2: Ablation Study}", "\\subsection{Ablation Study}")
content = content.replace("G2 (Ablation Study): ", "")
content = content.replace("\\subsection{G3: Prediction Accuracy}", "\\subsection{Prediction Accuracy}")
content = content.replace("G3 (Prediction Accuracy): ", "")
content = content.replace("\\subsection{G4: Optimal Queue Size Analysis}", "\\subsection{Optimal Queue Size Analysis}")
content = content.replace("G4 (Optimal Queue Size Analysis): ", "") 
content = content.replace("\\subsection{G5: Online Fine-Tuning Performance}", "\\subsection{Online Fine-Tuning Performance}")
content = content.replace("G5 (Online Fine-Tuning Performance): ", "")
content = content.replace("\\subsection{G6: Cache Hit Ratio and Delay}", "\\subsection{Cache Hit Ratio and Delay}")
content = content.replace("G6 (Average Cache Performance Metrics): ", "")
content = content.replace("\\subsection{G7: Cache Metrics by Vehicle Density}", "\\subsection{Cache Metrics by Vehicle Density}")
content = content.replace("G7 (Cache Metrics by Vehicle Density): ", "")
content = content.replace("represented by G1 to G7, ", "")


# 4. Title update
old_title = "\\title{Deterministic RSU Dwell Time Prediction via\\\\Hybrid Multi-Branch Attention Network in Content-Centric Vehicular Networks}"
new_title = "\\title{Proactive Content Precaching via Deterministic Dwell Time Prediction\\\\in Telecommunication-Enabled Vehicular Networks}"
content = content.replace(old_title, new_title)


with open('main.tex', 'w') as f:
    f.write(content)
