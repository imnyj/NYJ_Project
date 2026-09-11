import re
with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'r') as f:
    content = f.read()

target = r"Table~\\ref\{tab:accuracy\} summarizes the global prediction performance\.\n+H-ST-MBAN yields an MAE"
replacement = r"Table~\\ref{tab:accuracy} summarizes the global prediction performance, evaluated using Mean Absolute Error (MAE), Root Mean Square Error (RMSE), and Mean Absolute Percentage Error (MAPE).\nH-ST-MBAN yields an MAE"

content = re.sub(target, replacement, content)

with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'w') as f:
    f.write(content)
