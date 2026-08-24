---
name: anti-hallucination
description: Skill for enforcing strict path verification and eliminating AI hallucinations.
---
# Anti-Hallucination Skill

- **Path Verification**: Before reporting that a file operation is complete, explicitly double-check the absolute path of the file. Never assume the path was correct. Run a terminal command (e.g., `ls` or `view_file`) to verify the file was actually modified in the intended directory.
- **Strict Tone Formatting**: For all writing tasks, eliminate AI-like exaggerated adverbs and adjectives (e.g., "significant", "powerful synergy", "completely independent"). Use a dry, factual, and objective academic tone.
- **Evidence-Based Reporting**: When citing experimental results or writing down data, physically read the output logs or CSV files using `view_file`. Do not estimate or guess values.
