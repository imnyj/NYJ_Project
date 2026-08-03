# Harness Inventory

## 1. File Structure
(Files in .agents and .gemini)
- `.agents/skills/academic-coder/SKILL.md`
- `.agents/skills/academic-critic/SKILL.md`
- `.agents/skills/academic-idea/SKILL.md`
- `.agents/skills/academic-librarian/SKILL.md`
- `.agents/skills/academic-visualizer/SKILL.md`
- `.agents/skills/academic-worker/SKILL.md`
- `.agents/skills/academic-writer/SKILL.md`
- `.agents/skills/anti-hallucination/SKILL.md`
- `.agents/skills/feedback-manager/SKILL.md`
- `.agents/skills/gpu-balancer/SKILL.md`
- `.agents/skills/instructional-designer/SKILL.md`
- `.agents/skills/multi-agent-manager/SKILL.md`
- `.agents/skills/session-harness/SKILL.md`
- `.agents/skills/simulation-tuner/SKILL.md`
- `.agents/skills/skill-crafter/SKILL.md`
- `.gemini/antigravity-cli/builtin/skills/antigravity_guide/SKILL.md`

## 2. Rules, Skills, Subagents
### Rules (from GEMINI.md)
1. Recursive Task Atomization
2. Hierarchical Review System
3. Concurrency & Safety (Locking)
4. Accountability (Audit Logging)
5. Workspace & Deliverables (Project Folder)
6. Subagent Creation (Agent Factory)
7. SSH Reconnection & Input Handling
8. Memory Management & Fact-Checking (RAG)
9. Clarification & User Confirmation
10. Visualization Rules
11. Path Verification & Anti-Hallucination
12. Persistent Session Harness

### Skills
- academic-coder: Coder agent rules for writing clean Python simulation code.
- academic-critic: Critic agent rules for reviewing papers and code.
- academic-idea: Idea agent rules for managing research directions.
- academic-librarian: Librarian agent rules for searching and managing references.
- academic-visualizer: Visualizer agent rules for plotting academic charts.
- academic-worker: Worker agent rules for executing specific subroutines.
- academic-writer: Academic Writer agent rules for drafting papers.
- anti-hallucination: Skill for enforcing strict path verification and eliminating AI hallucinations.
- antigravity-guide: Guide for Antigravity system.
- feedback-manager: Autonomously extracting, recording, and managing user feedback.
- gpu-balancer: Manage and distribute GPU workloads across a 4-GPU workstation.
- instructional-designer: Designing presentations and planning classes.
- multi-agent-manager: Orchestrate subagents hierarchically.
- session-harness: Automatically initialize workspace directories.
- simulation-tuner: Running continuous hyperparameter tuning simulation loops.
- skill-crafter: Autonomously creating or updating other skills.

### Subagents
- manager_paperX: Team Leader
- worker_writer: Writes prose
- worker_critic: Reviews changes
- worker_librarian: Searches references
- worker_coder: Writes code
- worker_analyst: Analyzes data
- worker_worker: General tasks

### Hooks / MCP Servers
- None currently registered
