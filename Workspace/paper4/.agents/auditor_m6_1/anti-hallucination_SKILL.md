# Anti-Hallucination Skill

- **Path Verification**: Before reporting that a file operation is complete, explicitly double-check the absolute path of the file. Never assume the path was correct. Run a terminal command (e.g., `ls` or `view_file`) to verify the file was actually modified in the intended directory.
- **Strict Tone Formatting**: For all writing tasks, eliminate AI-like exaggerated adverbs and adjectives (e.g., "significant", "powerful synergy", "completely independent"). Use a dry, factual, and objective academic tone.
- **Evidence-Based Reporting**: When citing experimental results or writing down data, physically read the output logs or CSV files using `view_file`. Do not estimate or guess values.

## 11. Path Verification & Anti-Hallucination (환각 방지 및 경로 검증)
- **Rule:** 서브 에이전트가 파일 수정/생성 작업을 수행할 때는 **반드시** 지정된 정확한 절대 경로(Absolute Path)를 재확인하고 검증해야 한다. 존재하지 않거나 임의의 가상 경로(예: `papers/...`)에 작업해 놓고 완료했다고 허위 보고하는 환각(Hallucination)을 엄격히 금지한다.
- **Rule:** 작업 완료 전 반드시 실제 타겟 파일이 물리적으로 올바르게 변경되었는지 직접 확인(Double Check)한 뒤에 상위 에이전트에게 보고할 것.
