import re
with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'r') as f:
    content = f.read()

with open('bib_extracted.txt', 'r') as f:
    bib_text = f.read()
    
# Append bibitem 36 for Ericsson Mobility Report to bib_text
bib_text += "\n\\bibitem{36}\nEricsson, ``Ericsson Mobility Report,'' \\emph{Ericsson}, Stockholm, Sweden, 2023. [Online]. Available: https://www.ericsson.com/en/reports-and-papers/mobility-report\n"

# The original file has:
# \begin{thebibliography}{99}
# \bibitem{1}
# ...
# \end{thebibliography}

start_idx = content.find("\\begin{thebibliography}")
if start_idx == -1:
    print("Cannot find thebibliography start")
else:
    end_idx = content.find("\\end{thebibliography}", start_idx)
    if end_idx == -1:
        print("Cannot find thebibliography end")
    else:
        new_bib = "\\begin{thebibliography}{99}\n" + bib_text + "\n\\end{thebibliography}"
        content = content[:start_idx] + new_bib + content[end_idx + len("\\end{thebibliography}"):]
        with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'w') as f:
            f.write(content)
        print("Replaced bibliography")
