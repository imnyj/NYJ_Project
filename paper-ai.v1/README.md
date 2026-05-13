# paper-ai

> Multi-Agent LLM system for automated SCIE-grade paper writing, built on Anthropic Claude, designed for WSL2 + Python venv.

## 🎯 What it does

Given a research direction, paper-ai coordinates a **Commander + 5 worker agents** to produce a complete journal paper with:
- Literature review from SCIE-grade publishers only (IEEE, Elsevier, ACM, Nature, MDPI, Springer, Wiley, etc.)
- Experimental design + `libsumo`-based traffic/communication simulations
- Validated results with fair baselines
- Publication-ready figures (color-blind friendly, high DPI)
- LaTeX draft polished to journal style

## 🏗️ Architecture

Commander sits structurally **above** the workers, not beside them — it's the director, they execute. See `docs/ARCHITECTURE.md` for the full layered diagram.

| Role | File | Summary |
|---|---|---|
| **Commander** | `commander.py` (root) | Pipeline control, quality gates, arbiter between agents. No tools. |
| **Idea** | `agents/idea.py` | Contribution framing, novelty definition, storytelling |
| **Librarian** | `agents/librarian.py` | SCIE literature search + DOI verification + JSON citation |
| **Experimenter** | `agents/experimenter.py` | Dual-mode (Designer↔Engineer): design + libsumo implementation |
| **Reviewer** | `agents/reviewer.py` | Dual-mode (QA↔Proofreader): code audit + text polish |
| **Writer** | `agents/writer.py` | LaTeX integration + matplotlib figures + self-compile |

## 🚀 Quick start

```bash
# 1. Clone & enter
cd paper-ai

# 2. Create WSL2 venv
python -m venv .venv
source .venv/bin/activate

# 3. Install
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# edit .env: ANTHROPIC_API_KEY=sk-ant-... and (optional) CROSSREF_MAILTO=...

# 5. Verify offline (no API calls)
python cli.py --verify-config
pytest tests/ -v

# 6. Smoke-test the API (Phase 1 demo)
python cli.py --demo

# 7. One-shot Commander directive
python cli.py --command "Plan a paper on AoI-aware V2X beaconing"
python cli.py Command.md           # legacy: positional arg = file path

# 8. Interactive REPL
python cli.py --interactive

# 9. Full pipeline
python cli.py --pipeline "age-of-information V2X beaconing"
python cli.py --pipeline "..." --dry-run        # no LLM calls (structural test)
python cli.py --pipeline "..." --langgraph      # experimental LangGraph mode

# 10. Production: watchdog-supervised Commander
python -m monitoring.watchdog
```

## 📚 Implementation status

All 5 phases shipped; see `docs/ARCHITECTURE.md` for tech details and
`docs/REFACTORING.md` for the post-ship structural cleanup.

| Phase | Feature | Status |
|---|---|---|
| 1 | Prompt caching + model routing + skills | ✅ |
| 2 | Blackboard + dual ledger + orchestrator | ✅ |
| 2.5 | Tool permission enforcement + 6 agent subclasses | ✅ |
| 3 | Contextual Retrieval + PaperQA2 + hybrid search | ✅ |
| 4 | ReWOO + LLMCompiler + Batches API + executors | ✅ |
| 5 | Citation audit + VLM critique + CoVe + watchdog | ✅ |

## 🔑 Design principles

1. **Token efficiency is non-negotiable** — every feature must not increase per-paper cost significantly
2. **User approval for self-upgrade** — Commander must ask before modifying its own code
3. **No data destruction** — all upgrades are backed up with atomic replacement
4. **SCIE only for Librarian** — `arXiv`, `ResearchGate`, `Scopus` are blocked at two layers (search + verification)
5. **Hallucination-hard guards** — ID-only citations, deterministic BibTeX fetch, sentence-BERT claim checking
6. **Commander ≠ worker** — Commander lives at root, workers live in `agents/`; only workers go through `make_worker()`

## 📁 Project layout

```
paper-ai/
├── commander.py              # Director (above workers)
├── cli.py                    # thin argparse entrypoint
├── cli_commands/             # one module per subcommand
├── agents/                   # 5 worker agents + base class + registry
├── core/                     # orchestrator, ledgers, paths, planner, DAG
├── tools/                    # Anthropic client, code/SUMO/LaTeX runners
├── retrieval/                # Contextual RAG + hybrid search + verifier
├── memory/                   # SQLite-backed stores (corpus, skills, workflows)
├── evaluation/               # Citation audit, VLM critique, CoVe, confidence
├── monitoring/               # Watchdog
├── prompts/                  # 6 agent prompts (.txt, Korean + English)
├── skills/                   # 6 Agent Skills (SKILL.md + scripts)
├── config/                   # 5 YAMLs (settings/budgets/agents/routing/caching)
├── docs/                     # ARCHITECTURE.md, REFACTORING.md
├── scripts/                  # setup_venv.sh
└── tests/                    # pytest: test_phase{1,2,3,4,5}.py + conftest.py
```

## 📄 License

MIT
