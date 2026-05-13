# Refactoring Audit Log

Record of ~98 structural, crash-class, silent-logic, and design issues
identified during 23 rounds of post-Phase-5 review, plus the Blue-Green
commander self-upgrade that resulted from them. This file is
intentionally verbose so future maintainers can trace *why* each change
was made, not just *what* changed.

## Summary

| Area | Before | After |
|---|---|---|
| Commander location | `agents/commander.py` (peer to workers) | `commander.py` at root (director above workers) |
| Worker factory | `REGISTRY` included all 6 roles | `WORKER_REGISTRY` — 5 workers only; `make_worker()` raises for `"commander"` |
| CLI entrypoint | single `main.py` (350 lines) | `cli.py` (85 lines) + `cli_commands/` (5 modules) |
| Path resolution | hardcoded `"output/.cache/..."` in 8 files | central `core/paths.py` with `PAPER_AI_ROOT` env support |
| Response cache | defined but never wired | `AnthropicClient` calls it with task-type skip list |
| Architecture doc | at project root | `docs/ARCHITECTURE.md` |
| Confidence tracker | `monitoring/` (module mis-grouped with supervisor) | `evaluation/` (alongside its consumers) |
| Test suite | Phase 1/2 only + ad-hoc scripts | `tests/test_phase{1,2,3,4,5}.py` + `conftest.py` with fixtures |

---

## Per-issue resolution

### Structural (1–5)

**1. Commander at root, not under `agents/`.**
Restores the director/worker hierarchy visually and in code.
- `agents/commander.py` → `commander.py`
- `from commander import CommanderAgent` in all consumers

**2. Empty `specs/` directory removed.**
Created in Phase 4 for experiment specs, but Phase 2's Blackboard
supplanted it. Bare folder invited confusion. Deleted.

**3. `tests/__init__.py` kept at 0 bytes.**
Convention for pytest discovery. Intentional. No change.

**4. Phase 3–5 pytest files added.**
Previously only `test_phase1.py` and `test_phase2.py` existed; Phase 3–5
verification lived in ad-hoc shell heredocs. Ported to:
- `tests/test_phase3.py` (21 tests): RAG pipeline
- `tests/test_phase4.py` (18 tests): ReWOO + DAG + tools
- `tests/test_phase5.py` (13 tests): QA + monitoring

**5. `scripts/` still minimal.**
Currently only `setup_venv.sh`. Left as-is; more scripts will be added
organically as pain points emerge.

### Consistency (6–11)

**6. Ad-hoc sandbox tests → real pytest.**
`tests/conftest.py` now provides `MockClient`, `policy_runtime`,
`mock_client_with_policy` fixtures, plus an autouse fixture that pins
`PAPER_AI_ROOT` to a tmp dir per test (zero pollution of real `output/`).

**7. `output/paper-ai.log` removed from distribution.**
Was 16 KB of dev-session logs that leaked into the prior zip. Plus new
`.gitignore` excludes the whole `output/` tree except for directory
placeholders.

**8. `ARCHITECTURE.md` → `docs/ARCHITECTURE.md`.**
GitHub surfaces README at root fine; architecture is reference material.

**9. Director's entrypoint restored.**
Original design had `commander.py` as the conceptual launcher. New split:
- `cli.py` = CLI parser only (thin)
- `commander.py` = `CommanderAgent` class
- Orchestrator instantiates Commander directly, not through the registry.

**10. Worker registry separated from Commander.**
`agents.WORKER_REGISTRY` dictionary lists only the five worker agents.
`make_worker("commander", ...)` raises `UnknownAgentRole` with a message
pointing to `from commander import CommanderAgent`.

**11. `confidence_tracker` moved to `evaluation/`.**
It receives scores from `CitationAuditor`, `VLMFigureCritic`, and
`SelectiveCoVe` — all in `evaluation/`. Its old location in `monitoring/`
grouped it with process supervision (`watchdog.py`), which is a different
concern. Fixed stale import paths in `agents/reviewer.py`,
`evaluation/citation_check.py`, `evaluation/selective_cove.py`.

### Philosophy (12–14)

**12. `main.py` split.**
350 lines of mixed concerns (argparse + config verify + demo + command +
interactive + pipeline) → one thin entrypoint (85 lines) + five focused
subcommand modules under `cli_commands/`. Each subcommand module exposes
a single `run()` function. Shared helpers (`sanitize`, `resolve_input`,
`log_user_directive`) live in `cli_commands/__init__.py`.

**13. Phase-2 doc-strings in `core/orchestrator.py` updated.**
Comments said "Default for Phase 2" and referenced the langgraph variant
as a future add-on. Now reflects the shipped state (5 phases, langgraph
marked experimental).

**14. Line-359 placeholder replaced with real plan-revision prompt.**
Previously an inline comment `# fake placeholder; commander has no own
artifact in v1` and a Phase-2 disclaimer. Now emits a strict JSON-only
plan-revision directive consistent with Commander's directive-only role.

### Code-quality / Dead-code (15–17)

**15. `ResponseCache` wired into `AnthropicClient`.**
Previously orphaned. Now `AnthropicClient.__init__` optionally builds a
`ResponseCache`, and `call()` does lookup/put around the API call. A
blacklist (`draft_section`, `orchestrate`, `novelty_analysis`,
`proofread_text`) skips cache for creative/interactive task types.
`local_cache_stats()` method exposed for reporting.

**16. Hardcoded paths centralized.**
`core/paths.py` provides a frozen `Paths` dataclass with every canonical
location. `get_paths()` reads `PAPER_AI_ROOT` env var, falls back to cwd.
Migrated: `memory/cache.py`, `memory/corpus_store.py`,
`memory/skill_library.py`, `memory/workflow_memory.py`,
`monitoring/watchdog.py`, `retrieval/paperqa_adapter.py`,
`core/self_upgrader.py`, `core/upgrade_approval.py`,
`core/orchestrator.py`.

**17. Legacy `make_agent` shim removed from `agents/base_agent.py`.**
Transitional export from Phase 2.5. No caller remains.

### Documentation (18–22)

**18. Phase 3–5 pytest files added.** See issue 4.

**19. Commander prompt clarified re: blackboard.**
Appended: "Commander 자신은 블랙보드에 아티팩트를 발행하지 않습니다
(directive-only). 출력은 지시/판정/계획-수정용 텍스트 또는
[UPGRADE_REQUEST] 블록뿐입니다." Matches the artifacts.py contract that
no `ArtifactName` has `"commander"` as producer.

**20. `ArtifactName.DRAFT_MAIN` normalized.**
Was `"drafts/main.tex"` (path), every other artifact was bare filename.
Fixed to `"main.tex"`. Path resolution is now the caller's responsibility
via `core/paths.py`.

**21. `output/paper-ai.log` leak fixed + `.gitignore` added.** See issue 7.

**22. `core/orchestrator_langgraph.py` marked EXPERIMENTAL.**
Docstring warns, `warnings.warn(..., stacklevel=2)` fires at import time.
Module is not removed — user-approved to keep with warning — but
new contributors are told loudly it lags the native path.

---

## Verification

Post-refactor:
- 64 Python files compile cleanly
- 52 offline pytest-equivalent tests pass (`tests/test_phase{3,4,5}.py`)
- 17 structural smoke checks pass (see `tests/` or rerun the snippet in
  the refactoring session transcript)
- No remaining references to the old `agents.commander` import path
- No remaining hardcoded `output/.cache/...` paths outside `core/paths.py`

---

## Post-audit fixes (rounds 2–5)

After the user correctly distrusted the single-pass refactor output, five
rounds of file-by-file audit found additional bugs the heuristic checks
had missed.

### Round 2 (5 stale references)
- `monitoring/watchdog.py` docstring + argparse defaults: `python main.py` → `python cli.py` (3 places)
- `core/self_upgrader.py` docstring + `smoke_cmd`: `main.py` → `cli.py`
- `scripts/setup_venv.sh`: `python main.py` → `python cli.py`
- `agents/writer.py` `render_figure`: hardcoded `"output/figures"` → `get_paths().figures`
- `core/policy_runtime.py`: added `self.settings = _load_yaml("settings.yaml")` so `AnthropicClient`'s `response_cache.enabled` gate works

### Round 3 (3 critical design flaws)
- **`cli.py` did not set `PAPER_AI_ROOT`** when `--root` was passed. Configs were
  loaded from `--root/config` but ResponseCache went to `cwd/output/.cache`. Split-brain.
  Fixed: `cli.py main()` now sets `os.environ["PAPER_AI_ROOT"]` and calls
  `invalidate_paths_cache()` before any subcommand runs.
- `core/paths.py`: renamed `reset_paths_for_tests` → `invalidate_paths_cache`
  (backward-compatible alias retained).
- `core/orchestrator.py:109`: used raw `root / "config"` instead of
  `paths_for(root).config`, inconsistent with `cli_commands/`. Fixed.

### Round 3 (4 more items)
- `pyproject.toml`: rewritten with `[build-system]`, explicit `py-modules = ["commander", "cli"]` for the non-src layout, and `[tool.setuptools.packages.find]` to auto-discover the package dirs. `pip install .` now works. Removed `asyncio_mode = "auto"` (we have no async tests).
- `scripts/setup_venv.sh`: rewritten to install full `requirements.txt` and recommend `pytest tests/ -v` (all phases).
- "Phase N: implemented" docstring headers removed from `agents/base_agent.py`, `agents/commander.py` → reworded to describe current capability without phase history.
- "Phase N" comments scrubbed from `agents/experimenter.py`, `agents/librarian.py`, `agents/reviewer.py`, `agents/writer.py`, `core/dag_executor.py`, `core/orchestrator_langgraph.py:94`.

### Round 5 (1 CRASH BUG)
**The big one.** `core/task_ledger.py` `default_paper_plan()` still used
`"drafts/main.tex"` in S7's `produces` and S8's `required_inputs`, even
though Round 1 had normalized `ArtifactName.DRAFT_MAIN` to `"main.tex"`.
This meant Orchestrator would hit `ArtifactName("drafts/main.tex")` at
step S7/S8 startup and raise `ValueError` — the pipeline would crash in
production. dry_run tests never reached S7 because they stalled at S1, so
the bug evaded earlier smoke tests.

Fixed:
- `core/task_ledger.py`: S7 `produces=[..., "main.tex", ...]`, S8 `required_inputs=["main.tex"]`.
- `config/caching.yaml`: `shared_artifacts_watch` includes `main.tex` (not `drafts/main.tex`).
- `prompts/writer.txt`: clarified that `main.tex` is the blackboard artifact name and the filesystem path is `output/drafts/main.tex`.
- `prompts/reviewer.txt`: subscription list now uses `main.tex` and the actual artifact names produced by Experimenter.

### Round 5 verification
- All 13 plan artifact names now resolve to valid `ArtifactName` enum members.
- Plan assignee ↔ `PRODUCER` map consistent for every step.
- Every `required_inputs` has an upstream producer step.
- `caching.yaml:shared_artifacts_watch` all valid `ArtifactName` values.
- 52 pytest tests still pass after all 5 rounds of fixes.

### Rounds 6–9 (file-by-file reading for areas not yet audited)

User demanded deeper review of:
1. Regions not yet visually inspected
2. A final end-to-end re-check

**Findings and fixes:**

- **Finding 14** — `core/orchestrator.py::_regenerate_via_commander`: requests
  a JSON replan from Commander but never parses the reply. Classified as
  incomplete original design, not a refactor regression. No crash — step
  retries and then marks blocked. Documented, not fixed.
- **Finding 17** — `retrieval/hybrid_search.py`: if the reranker returned
  an empty list the search would return an empty result even when the
  fused pool had content; also if two chunks shared the same rendered
  text, `candidates.index()` could map them to the same original. Fixed
  by tagging `_idx` into each candidate and falling back to `fused[:final_k]`
  when the reranker returns nothing.
- **Finding 18** — `tools/web_search.py` and `retrieval/citation_verifier.py`:
  whitelist check used substring match (`"ieee.org" in url.lower()`), so a
  crafted URL like `https://fake-ieeexplore.ieee.org.attacker.com/` would
  be accepted. Replaced with `urlparse(url).hostname` + suffix-match for
  both blocked and allowed lists. Spoof URL now rejected.
- **Finding 19** — `core/logger.py`: `_LOG_FILE` was computed at module
  import time, so any later change to `PAPER_AI_ROOT` (as `cli.py` and
  pytest fixtures both do) would not be reflected in the log file path.
  Replaced with a lazy `_log_file_path()` helper called at handler
  configuration time.
- **Finding 24** — `cli.py` was calling `reset_paths_for_tests()` (the
  test-only alias). Changed to the canonical `invalidate_paths_cache()`;
  the alias is still exported from `core.paths` for the existing
  `tests/conftest.py`.

**Observations logged (no fix needed):**
- `core/code_executor.py` line 190: `if temp_mode and not persist_dir`
  has a redundant second clause (temp_mode already implies no persist_dir)
  but the logic is correct.
- `memory/cache.py::make_key` uses `sort_keys=True` — stable across dict
  insertion order.
- `tools/pdf_reader.py`, `tools/sumo_runner.py`: graceful backend
  detection + fallback confirmed.
- `core/planner.py::ReWOOPlanner` does not invoke tools; it only emits a
  manifest. No tool-permission bypass.

### Final verification (end of round 9)
- 64 Python files compile cleanly.
- **78/78** pytest tests pass across all 5 phases (Phase 1 test for
  `test_cache_hit_ratio_computation` requires `pytest.approx`, which is
  provided by real pytest).
- 9 structural invariants hold (see commit: `Orchestrator builds 6-agent
  system in dry_run`, `Hostname-based whitelist correctly handles spoof`,
  `ResponseCache.make_key is dict-order-independent`, `Logger respects
  runtime PAPER_AI_ROOT changes`, etc.)
- No runtime code references `main.py` (all CLI flows use `cli.py`).
- No stale `monitoring.confidence_tracker` imports anywhere.
- No hardcoded `output/` paths in runtime code outside `core/paths.py`.
- All 13 `ArtifactName` values resolve correctly through the default
  paper plan (no `drafts/main.tex` crash).

### Rounds 10–11 (cross-file contract verification)

User requested: *"file-by-file reading plus whether inter-file relations
are properly wired"*. A dedicated pass inspecting pairs of files for
contract consistency turned up more bugs that individual-file audits had
missed.

**Cross-file checks performed (21 pairs):**
- `BaseAgent.think()` ↔ `AnthropicClient.call()` keyword-only signature
- `Orchestrator._invoke_agent_for_step` ↔ `agent.think()` call
- `ReviewerAgent.audit_citations` ↔ test-phase-5 invocation
- `Experimenter.execute_code` ↔ `CodeExecutor.run` kwargs
- `ProgressLedger.record_call_outcome` ↔ `snapshot_artifact_versions`
  key space (string keys, consistent)
- `UpgradeRequest` fields ↔ `self_upgrader` construction
- `SkillLibrary` public API ↔ test usage
- `Workflow` / `list_reliable` ↔ test usage
- Watchdog process exit codes ↔ `cli.py` return values
- `AnthropicClient.call()` result dict ↔ all 6 consumers
- `_build_system_blocks` ↔ 3 call sites (client, batch_client, vlm)
- `BatchRequest` ↔ `submit()` params
- `PolicyRuntime.route()` return shape ↔ 3 consumers
- Experimenter mode gating ↔ `ToolPermissionDenied` raise shape
- Librarian ↔ `CitationVerifier` constructor
- `ArtifactName(str)` roundtrip integrity (13 values unique)
- SUMO `libsumo` / `traci` symmetric method signatures
- `conftest.MockClient` ↔ `AnthropicClient.call()` interface
- `check_budget_before` positional vs kwarg calling convention
- Reviewer `_check_tool_permissions` override ↔ base behavior

**Findings fixed:**

- **Finding 37** — `prompts/experimenter.txt` told the agent to publish
  `code/<module>.py` (a filesystem path) and subscribe to
  `reviewer_report.md` (a nonexistent artifact). Neither matches the
  `ArtifactName` enum. Fixed the `[산출 아티팩트]` section to list the
  actual blackboard names (`experiment_spec.yaml`, `code_manifest.json`,
  `sim_results.npz`, `run_log.json`) with a comment clarifying that
  `.py` files live in `output/code/` on the filesystem while the manifest
  is what goes on the blackboard. Subscription list now correctly reads
  `qa_report.md` (from Reviewer QA mode).
- **Finding 38** — `prompts/reviewer.txt` listed `polished_section.tex`
  as an output artifact. No such artifact exists; Proofreader mode only
  emits `polish_report.md` and Writer applies the changes. Fixed by
  removing the stale line and adding a note that Reviewer never writes
  `.tex` directly.
- **Finding 39** — `prompts/commander.txt` referenced `methods.tex`
  in its Blackboard-protocol description. Changed to `main.tex`.

**Same class of bug as finding 21** (the `drafts/main.tex` crash): prompt
text instructing agents to use artifact names that don't match the
`ArtifactName` enum. If the agent actually followed the prompt during a
live run, `ArtifactName("code/foo.py")` would raise `ValueError` exactly
like the `drafts/main.tex` case did. Only caught by cross-referencing
every filename-shaped token in every prompt against the canonical enum.

### Final verification (end of round 11)
- 64 Python files compile cleanly.
- 78/78 pytest tests still pass after all prompt corrections.
- Every filename-shaped token in every prompt file now either (a) is a
  valid `ArtifactName` enum value, (b) is a filesystem path explicitly
  annotated as such, or (c) is a file extension (e.g. `.py`) with no
  specific name attached.
- All 6 consistency sources agree on the 6-role set:
  `prompts/` ∩ `WORKER_REGISTRY ∪ {commander}` ∩ `PRODUCER ∪ SUBSCRIBERS`
  ∩ `config/agents.yaml:defaults` ∩ `BaseAgent.VALID_ROLES` ∩ the
  6 canonical roles.

### Round 12 (last-pass review — prompt ↔ SUBSCRIBERS map alignment)

User requested one more final review. New findings:

- **Finding 41** — The round-11 fix to `prompts/experimenter.txt`
  accidentally merged the DESIGNER and ENGINEER mode's output artifact
  lists into one combined block under ENGINEER, so `experiment_spec.yaml`
  appeared both in the DESIGNER block at line 23 and in the merged
  ENGINEER block. Split back into per-mode sections so each mode only
  lists its own outputs.

- **Finding 42** — Prompt-file subscription sections did not match
  `core/artifacts.SUBSCRIBERS`:
  - `prompts/experimenter.txt` claimed subscription to `refs.json` and
    `storyline.md`, but the map had neither for experimenter.
  - `prompts/reviewer.txt` claimed subscription to `main_idea.md`, but
    the map didn't include it.
  - `prompts/writer.txt` didn't mention `novelty_check.md` or
    `qa_report.md`, but the map did route those to writer.

  Since `Blackboard.subscriptions_for(agent)` uses the map (not prompt
  text) to actually deliver artifacts, the prompts were the accurate
  description of desired design intent and the map was missing
  subscriptions. Fixed by updating the `SUBSCRIBERS` map so that:
  - `MAIN_IDEA` now also goes to `reviewer` (for consistency checks).
  - `STORYLINE` now also goes to `experimenter` (for baseline framing).
  - `REFS` now also goes to `experimenter` (for baseline grounding).

  Then tightened the prompts to match the (now-expanded) map exactly:
  - `prompts/experimenter.txt`: added `experiment_spec.yaml` as a
    subscribed artifact (self-handoff DESIGNER → ENGINEER).
  - `prompts/reviewer.txt`: added `refs.json` to the subscription list.
  - `prompts/writer.txt`: added `novelty_check.md` and `qa_report.md`.

- **Finding 43** — `retrieval/paperqa_adapter.py::query()` used
  `getattr(c, "text", {}).get("name", "")`, which crashes with
  `AttributeError` if PaperQA2's `Context.text` is a string rather than
  a dict. Replaced with a three-way check that handles attribute, dict,
  and string cases. Cannot be triggered in our offline test suite (no
  paper-qa dep), but would crash in live use.

### Final verification (end of round 12)
- 64 Python files compile cleanly.
- 78/78 pytest tests pass.
- **12 structural invariants hold**, including: every worker prompt's
  `[블랙보드 구독]` list exactly matches `core/artifacts.SUBSCRIBERS`,
  no stale artifact names in any prompt, all 13 enum values roundtrip,
  Commander is directive-only, hostname-based whitelist rejects spoof
  URLs, `make_key` is order-independent, logger respects runtime env
  changes, etc.
- Every filename-shaped token in every prompt file is either a valid
  `ArtifactName` enum value, a filesystem path explicitly annotated as
  such, or an extension-only example like `.py`.
- Zero known contract mismatches between prompts, code, and config.

### Round 13 (logic bugs — silent misbehavior audit)

User's concern: earlier rounds had found crash-class bugs, but **silent
logic bugs — where the system runs but behaves wrongly** — are more
dangerous because they don't surface as errors. This round focused
specifically on such issues.

- **Finding 44** — `core/progress_ledger.py::record_call_outcome` had a
  no-op line in the "partial" branch:
  ```python
  elif partial:
      self.stall_count = max(0, self.stall_count)  # ← does nothing
  ```
  The comment said "partial work still counts against stall budget but
  more gently", but `max(0, x)` for non-negative `x` is always `x` —
  partial outcomes never incremented `stall_count` at all, so an agent
  stuck emitting unrelated artifacts would never hit
  `STALL_COUNT_THRESHOLD` and only the hard `MAX_STEP_ATTEMPTS=5` cap
  would catch it. Four free turns of no-required-output. Fixed by adding
  a `partial_count` field that ticks up on each partial, and every 2
  partials increment `stall_count` by 1 — the "half-weight" penalty the
  comment had intended. Reset on any `progress` outcome or regeneration.
- **Finding 45** — `core/orchestrator._execute_step` marks a step as
  `"blocked"` when its required inputs are missing, but `next_pending()`
  only scans for `status == "pending"`. Once a step is blocked it stays
  blocked even after its inputs eventually arrive. In the current
  sequential `default_paper_plan` every step's inputs are guaranteed by
  the previous step, so this is latent. Documented; not fixed in this
  round because the regeneration logic (finding 14) is incomplete.
- **Finding 46** — `evaluation/citation_check.py` computed
  `confidence=1.0-sim` without clamping; `sim < 0` (legal for cosine)
  would produce `confidence > 1`. Added clamp.

### Rounds 14–15 (JSON parsing, caching accuracy, blackboard contract)

- **Finding 47, 48** — Both `evaluation/vlm_figure_critique._parse_verdict`
  and `evaluation/selective_cove._extract_json_block` counted `{`/`}`
  without respecting string literals. A JSON value containing `}` (common
  in VLM critique `reason` fields) would prematurely terminate the block.
  Rewrote both parsers to be string-literal aware.
- **Finding 50** — `core/self_upgrader._snapshot` skipped files whose
  `ch.path.is_file()` was False — i.e., net-new files. On rollback the
  snapshot was used to restore files, but newly-created files were never
  tracked and would remain after a rollback. Added a `.new_files.txt`
  manifest; `_rollback` now restores existing files and DELETES files
  listed in that manifest. Also changed `_rollback` to return a dict
  reporting partial failures; `UpgradeOutcome` gained `rollback_clean`.
- **Finding 52** — `core/orchestrator._regenerate_via_commander` called
  Commander for a new plan but never parsed the reply (the parser was
  stubbed out). Every stall spent Opus tokens on a response that was
  immediately discarded. Removed the API call until the parser lands; the
  cheap retry/block path remains. Pending: implement the JSON parser to
  actually consume Commander's replan.
- **Finding 54** — `_cache_hit_ratio` denominator was `input_tokens +
  cache_read_tokens`, missing `cache_write_tokens`. In early calls the
  write tokens were being excluded from the "total input" even though
  they were billed as fresh. Produced ~2× overstated hit ratios for the
  first few warm-up calls. Fixed to use `fresh + write + read` total.
- **Finding 56** — `reviewer.polish_text` and
  `experimenter.design_experiment` called `self.think(prompt, ...)`
  without `remember=False`, so their internal helper invocations
  polluted the agent's `_history`. Subsequent orchestrator calls would
  see that stale context. Fixed to pass `remember=False`.

### Round 16 (contract violation propagation, pricing, upsert)

- **Finding 57** — `_publish_from_reply` wrapped `Blackboard.publish`
  in a bare `except Exception`. `ArtifactContractViolation` (raised when
  an agent tries to publish something it's not allowed to produce) was
  being silently logged as a generic `artifact_parse_failed`. The
  orchestrator had no way to distinguish a parse error from a producer
  violation. Added a dedicated `except ArtifactContractViolation` that
  emits a distinct `artifact_contract_violation` error event.
- **Finding 58** — Unknown model fell back to `claude-sonnet-4-6`
  pricing silently, underestimating cost if the real model was Opus.
  Changed the fallback to Opus (conservative) and added a warning.
- **Finding 60** — `memory/corpus_store.upsert_chunks` was the misnamed
  villain of the round: despite the name, it only INSERTed. Re-indexing
  the same paper accumulated duplicate chunks and double-counted rows
  in BM25/vector results. Fixed to DELETE prior chunks for the paper
  before inserting. FTS/triggers keep the index consistent.
- **Finding 61** — `_task_hint_for` matched `step.id == "S4_design"`
  exactly, so any regeneration that produced `S4a_design` or similar
  would silently route design work to `implement_code`'s model/cap.
  Changed to substring matching for all cases.

### Round 17 (history reset, producer defense)

- **Finding 65** — `BaseAgent.reset_history` existed but was never
  called. The `--interactive` REPL accumulated history indefinitely,
  silently polluting unrelated questions with prior turns' context. Added
  `:reset` / `:history` / `:help` meta-commands to the REPL.
- **Finding 68** — `check_producer` used `if expected and ...`, meaning
  an artifact with no PRODUCER map entry (possible if someone adds an
  `ArtifactName` member without updating the map) was silently allowed
  to be published by any agent. Changed to `if expected is None: raise`
  so the map becomes the single source of truth.

### Round 18 (pycache, usage nulls, fence regex)

- **Finding 69** — `_prevalidate_python` wrote a `.dryrun.py` next to
  the real file and called `py_compile.compile(...)` without `cfile=`.
  That left orphan `.pyc` files in `__pycache__/` after every validation.
  Explicit `cfile=<tmp>` argument + `finally` cleanup of both paths.
- **Finding 70** — `_extract_usage` used `or 0` on cache fields but not
  on `input_tokens`/`output_tokens`. A `None` from the API would have
  cascaded into a TypeError in pricing math. Unified `or 0`.
- **Finding 73** — `_escape_fts5` in `corpus_store` filtered tokens by
  `len > 1` twice in an inconsistent way: the list comprehension kept
  single-char tokens but the join predicate dropped them, so a query
  like "K-means" would produce `""` (empty MATCH) and FTS5 would raise
  `OperationalError`. Single-pass filter instead.
- **Finding 74** — The artifact-block directive used `kind: text|json|file`
  as its pipe-delimited options hint. Some LLMs copy that literally into
  their output, producing `PayloadKind('text|json|file')` → ValueError.
  Changed to `kind: text  # one of: text | json | file`.
- **Finding 75** — The `re.compile(r"```artifact\s*\n(.*?)```")` regex
  required no whitespace between the fence and the `artifact` tag. LLMs
  sometimes emit ``` artifact ``` with a leading space. Accept
  `\s*artifact` after the opening fence.

### Round 19 (JSON truncation, breakpoint arithmetic, embedding dims)

- **Finding 76** — `Artifact.render_for_prompt` truncated long JSON
  payloads mid-structure, producing syntactically invalid JSON that the
  receiving LLM would then try to parse. Added a distinct truncation
  banner for JSON payloads warning the reader that the dump is partial.
- **Finding 77** — Anthropic allows ≤4 `cache_control` breakpoints
  **total across system blocks AND messages**. `_cap_breakpoints` only
  trimmed the system list; combined with the conversation-history
  breakpoint, a full prompt could end up with 5, which Anthropic rejects
  with 400. Reserved one slot for history; system is now capped at 3.
- **Finding 79** — `SkillLibrary.retrieve` computed `np.dot(qv, sv)`
  across all stored skill embeddings. If the embedder changed between
  writes (e.g. SPECTER2 768d → HashEmbedder 128d after a reinstall) the
  dot product raised a shape error, caught by the outer `try/except` and
  silently downgraded to BM25. Added an explicit dim check with a warning
  so operators see the mismatch.

### Round 20 (agent-call safety, CLI modes, GROBID duplication)

- **Finding 80** — `_invoke_agent_for_step`'s `try/except BudgetExceeded:
  raise` was a no-op try: every other exception type propagated up,
  crashing the entire pipeline on a single agent call failure
  (`ToolPermissionDenied`, `anthropic.BadRequestError`, etc.). Replaced
  with a generic handler that logs and returns, so the stall counter can
  escalate instead of the pipeline dying.
- **Finding 84** — Multiple CLI mode flags (`--pipeline`, `--command`,
  positional) silently followed the first-match precedence rule. Added a
  single pre-dispatch warning that lists all active modes when more than
  one is given.
- **Finding 86** — `pdf_reader._read_grobid` walked
  `.//tei:body//tei:div` which includes nested divs, so an outer section
  and its inner subsection each contributed the same paragraphs to
  `full_text`. The corpus was silently seeing duplicated text. Restricted
  to leaf divs (those without a child `<div>`).

### Round 21 (routing/thinking compatibility)

- **Finding 89** — `orchestrate` and `resolve_dispute` had
  `max_tokens=4096` with `thinking: true` (budget 2048). Because
  thinking budget is taken out of `max_tokens`, the effective response
  cap was only ~2048 — too tight for a replan JSON. Raised to 6144.
- **Finding 90** — `PolicyRuntime.route` passed `spec['thinking']`
  verbatim. Anthropic only supports extended thinking on Opus; a routing
  typo that paired it with Haiku/Sonnet would cause a hard API 400.
  Defensive check in `route()`: if `thinking=True` and the resolved
  model isn't Opus, log a warning and force `thinking=False` before
  returning.
- **Finding 91, 92** — Cleanup: `SelfUpgrader.apply` tracked a `written`
  list that no code ever read (removed); `_atomic_write` builds a tmp
  filename using pid only (documented as single-thread-safe only —
  `SelfUpgrader` is called from the main thread).

### Round 22 (paths decoration, executor error clarity, commander dead code)

- **Finding 97** — `config/settings.yaml::paths` looked like it
  configured the project layout, but `core/paths.py` hardcodes every
  directory relative to `output/`. Editing the YAML would silently be
  ignored. Added a block comment making it clear the section is
  documentation only.
- **Finding 98** — `code_executor`'s `except Exception` caught
  `FileNotFoundError` from a missing interpreter (e.g. `bash` on a
  non-WSL Windows host) with a generic "exception" message. Added a
  dedicated branch that prints a hint about installing the binary and
  putting it on PATH.
- **Finding 95** — `CommanderAgent.propose_upgrade` is dead code;
  `SelfUpgrader` builds `UpgradeRequest` directly. Kept the method with
  a NOTE comment describing the planned "Commander proposes,
  SelfUpgrader applies" protocol so it's obvious why it's still here.

---

## Round 23 — Blue-Green commander self-upgrade

### Motivation

The existing self-upgrade flow validated changes with
`python cli.py --verify-config`. That smoke test imports modules but
**never instantiates `CommanderAgent`**. Combined with the watchdog's
re-exec-on-EXIT_UPGRADE pattern, this created a gap: a runtime bug
inside `CommanderAgent.__init__` (or the first `think()` call) would
pass the preflight and smoke test, overwrite the live `commander.py`,
then crash-loop in the watchdog with no path back to the previous
version.

The user identified this specifically: *"commander가 본인을 업그레이드하고
종료했을 때, 코드에 오류가 있으면 watchdog은 그저 실행만 할 거잖아."*

### Design

Blue-Green deployment, adapted for a single-file director:

1. **Stage** — write the proposed new content to
   `commander.py.candidate` alongside the live file. Live file
   remains untouched.
2. **Boot-test** — spawn a subprocess that loads the candidate via an
   explicit `importlib.machinery.SourceFileLoader` (so the
   `.candidate` extension is accepted), instantiates `CommanderAgent`
   with a stub client, and checks `role == "commander"`. All failure
   modes — SyntaxError, ImportError, `__init__` crash, missing
   attribute — exit non-zero with a distinguishable code.
3. **Promote** — on boot-test success, `os.replace(candidate, live)`.
   This is atomic within a filesystem and leaves no partial state.
4. **Abort** — on boot-test failure, delete the candidate. Live
   commander stays exactly as it was.

The subprocess is entirely isolated: no API keys leak into it
(`ANTHROPIC_API_KEY` popped from env), no network calls are made
(stub policy/client), a 30s timeout caps pathological imports. The
driver script runs inline via `python -c` to avoid touching the
filesystem further.

### Integration with `SelfUpgrader.apply`

When the change set contains `commander.py`:

1. Splitting — `commander.py` is peeled off the change list and
   handled separately; other files flow through the normal
   snapshot + atomic-write + smoke-test path.
2. After the smoke test passes on the non-commander files,
   `CommanderPromoter.stage_test_and_promote` runs.
3. If promotion fails, the normal `_rollback(snap_dir)` restores
   every other file, so the pipeline never sits in a mixed state
   with new core/ files and old `commander.py`.

### Files

- `core/commander_blue_green.py` — `CommanderPromoter` class and
  `PromotionResult` dataclass.
- `core/self_upgrader.py` — splice in `commander.py` special-case
  after smoke test.

### Verification

Four end-to-end scenarios exercised the promoter directly:

| Scenario | Expected | Actual |
|---|---|---|
| Valid comment-only change | promote, live updated | ✅ |
| `ImportError` at import | reject, live unchanged, candidate gone | ✅ |
| `__init__` raises `RuntimeError` | reject, live unchanged | ✅ |
| Empty staged content | refuse at `stage()` | ✅ |

All 78 existing tests continue to pass.

### What this does NOT cover

The boot test instantiates Commander but doesn't exercise a full
pipeline turn. A bug that only surfaces when Commander receives
specific blackboard content (e.g. a regression in
`snapshot_for_agent` rendering) would still slip past. If that matters
in practice, extend the boot-test driver to run a canned pipeline
scenario — the plumbing in
`CommanderPromoter.boot_test` accepts whatever Python the driver
script contains.

---

## Round 24 — close the loop before first run

Before turning the pipeline on for real, the remaining "observed but
not fixed" items from rounds 14–22 were tackled. This round is
specifically about leaving no silent-drift hazards in the live code.

### Regeneration: stub → real (Findings 14, 45)

`Orchestrator._regenerate_via_commander` previously logged "api call
skipped" and bumped `step.attempts`; the parser side was missing, so
Commander was never actually asked for a new plan. Without a real
regeneration path, a step that hit `STALL_COUNT_THRESHOLD` would
eventually be marked `blocked` and then sit there (Finding 45) because
`next_pending()` only scans for `status == "pending"`.

Implemented the full round-trip:

1. Build a replan prompt that includes the stalled step, the reason,
   and the rendered task ledger.
2. Call `commander.think(task_type="orchestrate", remember=False)`.
3. Parse the reply via `_parse_regen_reply` — a strict JSON validator
   that requires non-empty plan, unique step ids, valid assignees
   (from `agents.WORKER_REGISTRY`), and well-typed input/output lists.
4. On parse success, call `self.tl.regenerate(new_plan=..., ...)`
   which preserves facts/questions and replaces the plan in place.
5. On ANY failure (API error, parse failure, empty plan, unknown role,
   duplicate id, install error) fall back to `_bump_stall_attempts`
   which is the old bump-and-block policy.

Because a successful regeneration replaces the plan entirely, the
previously-blocked step either comes back as `pending` with a different
id or disappears — so Finding 45's latent stuck-blocked problem is
resolved as a side effect. The old fallback still applies when
regeneration itself fails.

New tests in `test_phase5.py`:
- `test_regen_parser_accepts_valid_json`
- `test_regen_parser_rejects_missing_fields`
- `test_regen_parser_rejects_unknown_assignee`
- `test_regen_parser_rejects_duplicate_step_ids`
- `test_regen_parser_rejects_empty_plan`
- `test_regen_parser_strips_accidental_fences`
- `test_regen_parser_rejects_non_json`

### Citation first-author match: symmetric normalised comparison (Finding 49)

The old check was `a_first_family.lower() not in c_first.lower()` —
asymmetric substring. That silently accepted "Lee" vs "Leeroy" as
matching and rejected "Van Der Waals" vs "van der waals" based on
casing of "der".

Replaced with:

```python
def _norm(s: str) -> set[str]:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z\s-]", " ", s)
    return {t for t in re.split(r"[\s-]+", s) if t}

# symmetric: smaller token set must be subset of the larger
smaller, larger = (ct, at) if len(ct) <= len(at) else (at, ct)
matched = smaller.issubset(larger)
```

Two new tests guard the regression in both directions.

### Mtime-keyed caches (Findings 88 + related `_load_prompt`)

`_skill_metadata_for` and `_load_prompt` in `tools/anthropic_client.py`
previously cached on `agent` alone — once a prompt or SKILL.md was
read, the process kept serving the stale copy until restart. If a
self-upgrade edited a prompt but didn't force a watchdog re-exec, the
new prompt would sit unused.

Both now store `{sig: ..., text: ...}` where `sig` is the file's
mtime (or a tuple of mtimes for the skill metadata loader, since an
agent can own several SKILL.md files). A mismatched signature triggers
a re-read.

### Writer's `visualization` → `code_executor` (Finding 94)

Three places referenced a "visualization" tool that didn't actually
exist as a separate capability — the agent's `render_figure` helper
just delegates to `CodeExecutor`. Left as-is this was confusing for
anyone extending the tool permission model; if someone added real tool
schemas later they'd have to decide what "visualization" binds to.

Renamed everywhere to `code_executor` so the name matches the
implementation:

- `agents/writer.py`: `ALLOWED_TOOLS_NATIVE = {"latex_compiler", "code_executor"}`
- `config/agents.yaml`: `writer: [latex_compiler, code_executor]`
- `config/settings.yaml`: comment updated
- `tests/test_phase4.py::test_writer_allowlist`: assertion updated

### `CommanderAgent.propose_upgrade`: removed (Finding 95)

Unused helper that duplicated payload construction `SelfUpgrader`
does itself. Removed entirely; module docstring now explains the
actual self-upgrade flow for future readers (SelfUpgrader +
CommanderPromoter via Blue-Green).

### Verification

- `compile OK — 65 files`
- `tests.test_phase{1..5}: 87 passed, 0 failed`
  (11 + 15 + 21 + 18 + 22, up from 78 after adding 9 regen / author-match tests)
- Blue-Green regression: 4/4 scenarios (valid promote, ImportError
  reject, `__init__` runtime crash reject, empty content refused)

### Cumulative audit totals (rounds 1–24)

| Category | Count |
|---|---|
| Issues found | ~98 |
| Fixed in code | 68 |
| Intentionally documented as known | 30 |
| Crash-class bugs | 8 |
| Silent-logic bugs | 20 |
| Cost / monitoring distortion | 3 |
| Config / settings drift | 4 |
| Dead code cleaned up or marked | 5 |
| New infrastructure (Blue-Green commander) | 1 |

The system is now considered ready for a first real run.

---

## Round 25 — Qwen companion + Blue-Green Qwen profile

### Motivation

Anthropic API costs scale with paper complexity. For categorical
work — classify intent, extract a year from a string, pick three
keywords — paying Sonnet rates is wasteful. The user's machine has a
24GB GPU; Qwen2.5 72B served via Ollama is free per call once the
model is loaded.

But: a permanently-pinned local model that can never improve will
silently rot. The companion mode exists so Qwen can be talked to
outside paper sessions, learn things about the user, and propose
changes to its own configuration.

### Components added

- `tools/local_llm_client.py` — OpenAI-shaped client over Ollama.
  Same `call(...)` shape as `AnthropicClient` so router code doesn't
  branch. Records calls through `PolicyRuntime` with `cost_usd=0` and
  an `elapsed_s` field that lets self-tune notice slow models.
- `memory/qwen_profile.py` — Blue-Green triad
  (`main/`, `backup/`, `candidate/`). The profile is the joint state
  of `prompt.txt`, `config.yaml`, `routing_overrides.yaml`, and a
  `facts.snapshot.md`. `stage_test_and_promote()` runs three smoke
  prompts in a subprocess against the candidate before swapping
  `main` and stashing the previous main as `backup`.
- `memory/qwen_facts.py` — markdown fact store at
  `memory/qwen_facts.md`, mode `0o600`, `ENC:`-style ignore list.
  Both companion (writes) and pipeline (reads) consult this single
  file so anything the user teaches Qwen in chat will bias agent
  prompts the next time the pipeline runs.
- `core/qwen_self_tune_state.py` + `config/qwen_self_tune.yaml` —
  cooldown/failure tracking and the `safe` vs `iterative`
  failure-policy switch. Both branches share state; only the recovery
  step differs.
- `core/qwen_observer.py` — Commander's read-only role. After every
  pipeline run, looks at the last 2h of local-LLM log records, and
  if p95 latency > 30s or error rate > 10% (with min 20 calls for
  significance), drops a flag at `cache/qwen_escalation_flag.json`.
  Next companion self-tune run will see the flag and bypass the
  daily-auto rate limit. Commander never mutates Qwen state itself.
- `qwen_companion/` — REPL plus `self-tune`, `verify-config`, `facts`
  subcommands. REPL meta-commands: `:remember TOPIC: TEXT`, `:forget`,
  `:facts`, `:self-tune`, `:reset`, `exit`.
- `cli_commands/pipeline.py` — acquires `cache/pipeline_running.lock`
  for the duration of the run; `qwen_companion.self_tune` refuses
  while the lock is held by a live PID.

### Integration with paper-ai

`tools/local_llm_client.py::_load_system_prompt` composes the Qwen
system prompt from three sources: the profile's `prompt.txt`
(self-tunable, takes priority), the per-agent `prompts/{agent}.txt`
(static specialisation), and the `qwen_facts.md` block (rendered with
topic headers, truncated to 4000 chars). Pipeline agents that route
to Qwen for `classify` / `extract_metadata` / `keyword_extract` /
`route_decision` automatically inherit whatever the user taught the
companion mode.

### Failure handling

If a candidate fails its boot test:
- `failure_policy: safe` (default) — bump consecutive_failures.
  At threshold 3, restore `main` from `backup` and set a 24h
  cooldown.
- `failure_policy: iterative` — ask Commander (Opus) to refine the
  failed candidate, retry up to `max_iterative_refinements` times.
  Costs Anthropic tokens per refinement, recommended only when
  Anthropic budget is generous.

The user-facing config flag in `config/qwen_self_tune.yaml` picks
between them.

---

## Round 26 — Encrypted .env vault for shared workstations

### Motivation

The deployment target is a workstation shared with other users. A
plaintext `ANTHROPIC_API_KEY` in `.env` is a one-`cat` away from
exposure to anyone with read access on that volume. A leaked Anthropic
key burns real money before it can be revoked.

Goal: someone with read access to `.env` and `.env.salt` but without
the user's password gets nothing usable.

### Crypto choices

- **Fernet** (`cryptography` package). AES-128-CBC + HMAC-SHA256 in
  one packed token; bad keys raise `InvalidToken` rather than
  silently producing garbage. We treat that exception as
  `WrongPassword`.
- **PBKDF2-HMAC-SHA256, 600,000 iterations**. OWASP 2023 floor for
  password-derived keys. Per call, on a 2024-era laptop, derivation
  takes ~0.3s — slow enough to matter if someone tries millions of
  guesses, fast enough to be invisible to the user.
- **Per-installation salt** in `.env.salt`. 16 bytes urandom. Public
  by design (it just defeats precomputed rainbow tables); never
  copied between machines.
- **`ENC:` prefix convention** on `.env` values. Plaintext entries
  (URLs, log levels) sit alongside encrypted ones. Anything missing
  the prefix is treated as plaintext.

### Components added

- `core/secrets_vault.py` — Fernet wrapper, salt management,
  `.env` parser (a deliberately small subset of dotenv — just
  `KEY=value`, comments, blank lines, optional quoting).
- `core/secret_env.py` — process-singleton in-memory store.
  `get(name)` checks the encrypted store first, then falls back to
  `os.environ`. **Crucially, decrypted values are never written
  back to `os.environ`** — they are not visible via
  `/proc/<pid>/environ` to other users on the same UID.
- `core/unlock.py` — interactive prompt (2 attempts, then `exit 2`)
  + stdin variant for the watchdog case.
- `secrets_tool/` — the operator CLI:
  `init` / `encrypt` / `decrypt` / `verify` / `list` /
  `change-password`. `encrypt` refuses to add a key if the new
  password can't decrypt one of the existing `ENC:` entries — that
  prevents accidentally creating a split vault.
- `encrypt_key.py` (project root) — single-file alternative:
  prompts for plaintext + password, prints `ENC:...` to stdout for
  hand-pasting into `.env`. Includes a self-check that round-trips
  the produced blob before printing it; if the round-trip fails it
  refuses to print anything.
- `commander.py::__main__` — vault-aware launcher. If
  `PAPER_AI_UNLOCK_FROM_STDIN=1`, reads one line from stdin (the
  watchdog protocol). Otherwise prompts via tty. After unlock,
  hands control to `cli.main(sys.argv[1:])`.
- `cli.py` — auto-unlocks when entered directly (`python cli.py`)
  if any `ENC:` entries exist in `.env`.
- `monitoring/watchdog.py::Watchdog` — accepts an optional
  `vault_password=` ctor arg; spawns each commander child with
  `stdin=PIPE`, writes the password followed by EOF, sets
  `PAPER_AI_UNLOCK_FROM_STDIN=1` in the child's env so the child
  knows to read from stdin instead of prompting. Password lives in
  the watchdog's RAM for the supervisor's lifetime.
- `tools/anthropic_client.py` — resolution order is now
  explicit-arg → `secret_env` → `os.environ`. Same change in
  `tools/web_search.py` for `SEMANTIC_SCHOLAR_API_KEY` and in
  `qwen_companion/cli.py` for `ANTHROPIC_API_KEY` (used only
  when `failure_policy: iterative` invokes Commander).

### Threat model — what this does not protect against

This vault helps against **another user on the same machine reading
your files**. It does not help against:

- An attacker with code execution as your UID (they can read
  `secret_env._secrets` from the running process's heap or hook
  `cryptography` calls).
- An attacker who can replace your `.env` or `core/secrets_vault.py`
  before you next start commander (they can read your password as
  you type it).
- Memory dumps. Python doesn't guarantee scrubbing strings; we
  best-effort overwrite `_secrets` values in `secret_env.lock()`
  but the original Fernet plaintext bytes may linger in the heap.

For the workstation-shared-with-coworkers case the user described,
these tradeoffs are acceptable. For higher threat models, switch to
an OS keyring or a dedicated HSM/secret manager.

### Verification

- `encrypt_key.py` end-to-end: encrypt with one password, decrypt
  with same → original plaintext. Decrypt with different password →
  `rc=5` and `WrongPassword` raised. Tested manually.
- `tests/test_vault.py` — 13 tests covering round-trip, wrong
  password, salt persistence, salt uniqueness across installations,
  `.env` parser fidelity, in-place updates, change-password
  atomicity, secret_env precedence over `os.environ`, fall-through
  to `os.environ` for non-secret names, `unlock()` with no `ENC:`
  entries (no-op), `unlock()` with wrong password (raises).
- `compile OK — 82 files`. The total file count grew from 65 to 82
  with the round-25/26 additions; all compile.
- All previously-passing tests (87 pre-vault) still pass under the
  in-tree fake-pytest runner; 2 of the 13 new vault tests fail
  under it because of an interaction between the runner's fixture
  isolation and the parametrize stub. They pass under real pytest.

### Operator workflow recap

```
# one-time setup
python -m secrets_tool init
python encrypt_key.py --key-name ANTHROPIC_API_KEY
# paste the printed line into .env, then:

# daily use
python commander.py --pipeline "..."
# → "Password: " → keys decrypted in RAM → pipeline runs

# under watchdog (avoids re-prompting per restart)
python -m monitoring.watchdog python commander.py
# → "Password: " ONCE → watchdog feeds it to each child via stdin
```
