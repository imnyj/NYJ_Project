with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'r') as f:
    content = f.read()

# 1. CCVN
content = content.replace(
    'In Content-Centric Vehicular Networks, proactive edge caching',
    'In Content-Centric Vehicular Networks (CCVNs), proactive edge caching'
)
content = content.replace(
    'We consider a Content-Centric Vehicular Network (CCVN) in which a set of Road-Side Units (RSUs)',
    'We consider a CCVN in which a set of RSUs'
)
content = content.replace(
    'dwell-time prediction in Content-Centric Vehicular Networks.',
    'dwell-time prediction in CCVNs.'
)
# Note: Line 98 already has 'CCVNs', and Line 176 has 'CCVN'

# 2. RSU
content = content.replace(
    'single-snapshot RSU inference setting.',
    'single-snapshot Road-Side Unit (RSU) inference setting.'
)

# 3. MHA
content = content.replace(
    'A three-token multi-head self-attention layer integrates',
    'A three-token Multi-Head Attention (MHA) layer integrates'
)
# Replace other occurrences of multi-head self-attention with MHA
content = content.replace(
    'fused by a multi-head self-attention layer.',
    'fused by an MHA layer.'
)
content = content.replace(
    'fused by multi-head self-attention.',
    'fused by MHA.'
)
content = content.replace(
    'applies multi-head self-attention~\\cite{30}',
    'applies MHA~\\cite{30}'
)
content = content.replace(
    'replaces the multi-head self-attention mechanism',
    'replaces the MHA mechanism'
)
content = content.replace(
    'showing that multi-head self-attention routes',
    'showing that MHA routes'
)
content = content.replace(
    'fused via multi-head self-attention,',
    'fused via MHA,'
)

# 4. CTE
content = content.replace(
    'The T Branch applies Cyclical Temporal Encoding to signal phase variables.',
    'The T Branch applies Cyclical Temporal Encoding (CTE) to signal phase variables.'
)

# 5. MAE, RMSE, MAPE
content = content.replace(
    'Table~\\ref{tab:accuracy} summarizes the global prediction performance. H-ST-MBAN yields an MAE',
    'Table~\\ref{tab:accuracy} summarizes the global prediction performance, evaluated using Mean Absolute Error (MAE), Root Mean Square Error (RMSE), and Mean Absolute Percentage Error (MAPE). H-ST-MBAN yields an MAE'
)

with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'w') as f:
    f.write(content)

