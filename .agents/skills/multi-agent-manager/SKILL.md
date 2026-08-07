---
name: multi-agent-manager
description: Skill for Team Leader agents to orchestrate subagents hierarchically.
---
# Multi-Agent Manager Skill

- **Delegation Protocol**: Never execute complex tasks manually (e.g., writing papers or writing code yourself). Break the problem down into distinct, atomic sub-tasks.
- **Worker Instantiation**: Use `define_subagent` and `invoke_subagent` to spawn specialized subordinate agents (e.g., `worker_writer`, `worker_critic`, `worker_coder`).
- **Context Injection**: Always ensure that subordinates are equipped with project-specific rules (from `.rules` or `.agents/skills`) in their system prompts.
- **Schema/Interface Pre-alignment**: Before spawning parallel worker agents to build interdependent modules, the manager MUST define and share a common Data Schema or Interface Definition (e.g., shared object models, data types) with all workers to prevent cross-agent object mismatch and integration errors.
- **Hierarchical Review**: Once a subordinate finishes, verify their work. If there are flaws (e.g., hallucinations, rule violations), reject the work and instruct them to fix it before reporting to the CEO.
