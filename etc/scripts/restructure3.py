import re

with open('/home/imnyj/papers/paper1/paper/draft/main.tex', 'r') as f:
    text = f.read()

def get_block(start_marker, end_marker):
    start = text.find(start_marker)
    if end_marker:
        end = text.find(end_marker)
        if end == -1: end = len(text)
    else:
        end = len(text)
    if start == -1: return ""
    return text[start:end]

sec3_intro = get_block(r'\section{System Model}', r'\subsection{Network Model and RSU Deployment}')
sec3_1 = get_block(r'\subsection{Network Model and RSU Deployment}', r'\subsection{Event-Driven Snapshot Definition}')
sec3_2 = get_block(r'\subsection{Event-Driven Snapshot Definition}', r'\subsection{Prediction Task Formulation}')
sec3_3 = get_block(r'\subsection{Prediction Task Formulation}', r'\subsection{Input Feature Enumeration}')
sec3_4 = get_block(r'\subsection{Input Feature Enumeration}', r'\subsection{Target Variables}')
sec3_5 = get_block(r'\subsection{Target Variables}', r'\section{H-ST-MBAN Architecture}')

sec4_intro = get_block(r'\section{H-ST-MBAN Architecture}', r'\subsection{Overview and Design Rationale}')
sec4_1 = get_block(r'\subsection{Overview and Design Rationale}', r'\subsection{Multi-Branch Encoding}')
sec4_2 = get_block(r'\subsection{Multi-Branch Encoding}', r'\subsection{Feature Fusion with Multi-Head Attention}')
sec4_3 = get_block(r'\subsection{Feature Fusion with Multi-Head Attention}', r'\subsection{Spatio-Temporal Residual Decoder}')
sec4_4 = get_block(r'\subsection{Spatio-Temporal Residual Decoder}', r'\subsection{GBDT Prior Stream and Learnable Gating Fusion}')
sec4_5 = get_block(r'\subsection{GBDT Prior Stream and Learnable Gating Fusion}', r'\subsection{Loss Function}')
sec4_6 = get_block(r'\subsection{Loss Function}', r'\subsection{Posterior Collapse Analysis of ST-CVAE (Motivation)}')
sec4_7 = get_block(r'\subsection{Posterior Collapse Analysis of ST-CVAE (Motivation)}', r'\section{Experiments and Results}')

def remove_header(block, header_name):
    pattern = r'(% ============================================================\n)?\\' + header_name + r'.*?\n(\\label\{.*?\}\n)?(% ============================================================\n)?\n*'
    return re.sub(pattern, '\n', block)

sec3_intro = sec3_intro.replace(r'\section{System Model}', r'\section{Network Model and Scheme Overview}')
sec3_1 = sec3_1.replace(r'\subsection{Network Model and RSU Deployment}', r'\subsection{Vehicular Network Environment}')

sec3_3 = sec3_3.replace(r'\subsection{Prediction Task Formulation}', r'\subsection{Scheme Overview and Task Formulation}')
sec3_5 = remove_header(sec3_5, 'subsection{Target Variables}')

sec4_intro = sec4_intro.replace(r'\section{H-ST-MBAN Architecture}', r'\section{Proposed Precaching Scheme}')
sec4_intro = sec4_intro.replace(
    'In this section, we present H-ST-MBAN, a deterministic regression architecture for RSU dwell time prediction in snapshot-based CCVN environments.',
    'In this section, we present the proposed RSU-driven precaching scheme designed to support seamless content delivery in snapshot-based CCVN environments.'
)

sec3_2 = sec3_2.replace(r'\subsection{Event-Driven Snapshot Definition}', r'\subsection{Request Handling and Feature Acquisition}')
sec3_4 = remove_header(sec3_4, 'subsection{Input Feature Enumeration}')

sec4_1 = sec4_1.replace(r'\subsection{Overview and Design Rationale}', r'\subsection{H-ST-MBAN Dwell Time Estimation}')
sec4_2 = remove_header(sec4_2, 'subsection{Multi-Branch Encoding}')
sec4_3 = remove_header(sec4_3, 'subsection{Feature Fusion with Multi-Head Attention}')
sec4_4 = remove_header(sec4_4, 'subsection{Spatio-Temporal Residual Decoder}')

sec4_5 = sec4_5.replace(r'\subsection{GBDT Prior Stream and Learnable Gating Fusion}', r'\subsection{Dual-Model Asynchronous Update}')
sec4_6 = remove_header(sec4_6, 'subsection{Loss Function}')
sec4_7 = remove_header(sec4_7, 'subsection{Posterior Collapse Analysis of ST-CVAE \\(Motivation\\)}') # regex escape for parens


part1 = text[:text.find(r'\section{System Model}')]
part2 = text[text.find(r'\section{Experiments and Results}'):]

new_text = (
    part1 +
    sec3_intro +
    sec3_1 +
    sec3_3 +
    sec3_5 +
    sec4_intro +
    sec3_2 +
    sec3_4 +
    sec4_1 +
    sec4_2 +
    sec4_3 +
    sec4_4 +
    sec4_5 +
    sec4_6 +
    sec4_7 +
    part2
)

with open('/home/imnyj/papers/paper1/paper/draft/main.tex', 'w') as f:
    f.write(new_text)
print("Done")
