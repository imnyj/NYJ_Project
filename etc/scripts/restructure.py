import re

with open('/home/imnyj/papers/paper1/paper/draft/main.tex', 'r') as f:
    text = f.read()

# Locate indices of sections
def get_idx(pattern):
    m = re.search(pattern, text)
    if m:
        return m.start()
    return -1

sec3_start = get_idx(r'\\section\{System Model\}')
sec3_1_start = get_idx(r'% ============================================================\n\\subsection\{Network Model and RSU Deployment\}')
sec3_2_start = get_idx(r'% ============================================================\n\\subsection\{Event-Driven Snapshot Definition\}')
sec3_3_start = get_idx(r'% ============================================================\n\\subsection\{Prediction Task Formulation\}')
sec3_4_start = get_idx(r'% ============================================================\n\\subsection\{Input Feature Enumeration\}')
sec3_5_start = get_idx(r'% ============================================================\n\\subsection\{Target Variables\}')
sec4_start = get_idx(r'\\section\{H-ST-MBAN Architecture\}')
sec4_1_start = get_idx(r'% ============================================================\n\\subsection\{Overview and Design Rationale\}')
sec4_2_start = get_idx(r'% ============================================================\n\\subsection\{Multi-Branch Encoding\}')
sec4_3_start = get_idx(r'% ============================================================\n\\subsection\{Feature Fusion with Multi-Head Attention\}')
sec4_4_start = get_idx(r'% ============================================================\n\\subsection\{Spatio-Temporal Residual Decoder\}')
sec4_5_start = get_idx(r'% ============================================================\n\\subsection\{GBDT Prior and Learnable Gating Fusion\}')
sec4_6_start = get_idx(r'% ============================================================\n\\subsection\{Dual-Model Update and Loss Formulation\}')
sec5_start = get_idx(r'% ============================================================\n\\section\{Experiments and Results\}')

# Extract blocks
block_sec3_intro = text[sec3_start:sec3_1_start]
block_3_1 = text[sec3_1_start:sec3_2_start]
block_3_2 = text[sec3_2_start:sec3_3_start]
block_3_3 = text[sec3_3_start:sec3_4_start]
block_3_4 = text[sec3_4_start:sec3_5_start]
block_3_5 = text[sec3_5_start:sec4_start]
block_sec4_intro = text[sec4_start:sec4_1_start]
block_4_1 = text[sec4_1_start:sec4_2_start]
block_4_2 = text[sec4_2_start:sec4_3_start]
block_4_3 = text[sec4_3_start:sec4_4_start]
block_4_4 = text[sec4_4_start:sec4_5_start]
block_4_5 = text[sec4_5_start:sec4_6_start]
block_4_6 = text[sec4_6_start:sec5_start]

# Modify Headers
block_sec3_intro = block_sec3_intro.replace(r'\section{System Model}', r'\section{Network Model and Scheme Overview}')
block_3_1 = block_3_1.replace(r'\subsection{Network Model and RSU Deployment}', r'\subsection{Vehicular Network Environment}')

block_3_3 = block_3_3.replace(r'\subsection{Prediction Task Formulation}', r'\subsection{Scheme Overview and Task Formulation}')
block_3_5 = block_3_5.replace(r'% ============================================================\n\subsection{Target Variables}\n\label{sec.net.E}\n% ============================================================\n\n', '')

block_sec4_intro = block_sec4_intro.replace(r'\section{H-ST-MBAN Architecture}', r'\section{Proposed Precaching Scheme}')
block_sec4_intro = block_sec4_intro.replace(r'In this section, we present H-ST-MBAN, a deterministic regression architecture for RSU dwell time prediction in snapshot-based CCVN environments.', r'In this section, we present the proposed RSU-driven precaching scheme designed to support seamless content delivery in snapshot-based CCVN environments.')

block_3_2 = block_3_2.replace(r'\subsection{Event-Driven Snapshot Definition}', r'\subsection{Request Handling and Feature Acquisition}')
block_3_4 = block_3_4.replace(r'% ============================================================\n\subsection{Input Feature Enumeration}\n\label{sec.net.D}\n% ============================================================\n\n', '')

block_4_1 = block_4_1.replace(r'\subsection{Overview and Design Rationale}', r'\subsection{H-ST-MBAN Dwell Time Estimation}')
block_4_2 = block_4_2.replace(r'% ============================================================\n\subsection{Multi-Branch Encoding}\n\label{sec.prop.B}\n% ============================================================\n\n', '')
block_4_3 = block_4_3.replace(r'% ============================================================\n\subsection{Feature Fusion with Multi-Head Attention}\n\label{sec.prop.C}\n% ============================================================\n\n', '')
block_4_4 = block_4_4.replace(r'% ============================================================\n\subsection{Spatio-Temporal Residual Decoder}\n\label{sec.prop.D}\n% ============================================================\n\n', '')

block_4_5 = block_4_5.replace(r'\subsection{GBDT Prior and Learnable Gating Fusion}', r'\subsection{Dual-Model Asynchronous Update}')
block_4_6 = block_4_6.replace(r'% ============================================================\n\subsection{Dual-Model Update and Loss Formulation}\n\label{sec.prop.F}\n% ============================================================\n\n', '')

# Reconstruct
new_text = text[:sec3_start] + \
           block_sec3_intro + \
           block_3_1 + \
           block_3_3 + \
           block_3_5 + \
           block_sec4_intro + \
           block_3_2 + \
           block_3_4 + \
           block_4_1 + \
           block_4_2 + \
           block_4_3 + \
           block_4_4 + \
           block_4_5 + \
           block_4_6 + \
           text[sec5_start:]

with open('/home/imnyj/papers/paper1/paper/draft/main.tex', 'w') as f:
    f.write(new_text)

print("Restructure complete.")
