with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'r') as f:
    content = f.read()

# Fix citation mismatch 1
content = content.replace(
    'traffic is projected to reach 515 Exabytes per month by 2031 \\cite{1}',
    'traffic is projected to reach 515 Exabytes per month by 2031 \\cite{36}'
)

# Fix citation mismatch 2
content = content.replace(
    'architectures and federated learning frameworks extract continuous temporal dependencies \\cite{8,9}',
    'architectures and federated learning frameworks extract continuous temporal dependencies \\cite{9,12}'
)

with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'w') as f:
    f.write(content)
