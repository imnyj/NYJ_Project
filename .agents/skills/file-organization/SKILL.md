---
name: file-organization
description: Skill for autonomously maintaining a clean workspace by categorically storing all miscellaneous and temporary files into an 'etc' directory.
---

# File Organization & Workspace Cleanliness Skill

## Purpose
This skill ensures that the agent keeps the project workspace clean and uncluttered. It prevents the root directory and main project folders from being polluted with temporary scripts, debug logs, intermediate datasets, and backup files.

## Core Directives

1. **The `etc/` Directory Mandate**
   Whenever generating a file that is not the final product, main codebase, or officially requested deliverable, you MUST route it to an `etc/` directory within the project's root folder.

2. **Categorical Sub-directories**
   Do not just dump files into `etc/`. You must categorize them using specific sub-directories. Examples include:
   - `etc/scripts/`: For temporary python or bash scripts written to process data, scrape the web, or perform one-off tasks.
   - `etc/logs/`: For execution outputs, stdout captures, and error logs.
   - `etc/temp/` or `etc/data/`: For intermediate data processing files, downloaded zips, or temporary scratchpads.
   - `etc/backups/`: For saving original copies of files before risky overwrites.

3. **Agent Accountability**
   - Before executing a `write_to_file` or running a python script that outputs a file, explicitly check your target path.
   - If the path is in the root directory (e.g., `workspace/paper1/test_script.py`), STOP. Redirect it to `workspace/paper1/etc/scripts/test_script.py`.

4. **Self-Correction**
   - If you notice that you or another agent have already cluttered the workspace with miscellaneous files, take a moment to move them into the appropriate `etc/` sub-directories using `mv` commands.

## When to use this skill
Activate this skill whenever you are about to create new files in a repository, write intermediate scripts, or when the user complains about workspace clutter. Always adhere to these rules implicitly during any workflow.
