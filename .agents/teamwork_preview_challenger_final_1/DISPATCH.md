## 2026-08-18T07:06:01Z
You are teamwork_preview_challenger_final_1.
Your working directory is: /home/imnyj/.agents/teamwork_preview_challenger_final_1

MANDATORY FIRST STEP: Read the user request at /home/imnyj/.agents/ORIGINAL_REQUEST.md.
Read /home/imnyj/.agents/PROJECT.md and /home/imnyj/.agents/TEST_INFRA.md.

Scope: Adversarial Syntax, Cross-Reference & Citation Stress Testing:
1. Write and execute an independent Python AST / regex test script to parse /home/imnyj/Workspace/paper4/latex/main.tex:
   - Check balanced LaTeX environments (\begin{} and \end{} pairs for all 50+ environments).
   - Check balanced math delimiters ($, $$, \begin{equation}, etc.).
   - Verify every \cite{...} matches an entry in references.bib (no undefined citations).
   - Verify all 27 references in references.bib are cited in main.tex (100% citation coverage).
   - Verify every \ref{...} and \eqref{...} has a matching \label{...} in main.tex (0 dangling references).
   - Verify all \includegraphics references point to existing files in figures/.
2. Document empirical test results in /home/imnyj/.agents/teamwork_preview_challenger_final_1/challenge_report.md.
3. Provide explicit verdict: APPROVE or REQUEST_CHANGES in /home/imnyj/.agents/teamwork_preview_challenger_final_1/handoff.md.
4. Send completion message to parent.

Follow all rules in GEMINI.md.
