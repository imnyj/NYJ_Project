# Plan — Auto_Stock Full Codebase Review & Direct Refactoring

## Objectives
1. Comprehensive code review across 3 core defect domains:
   - Area 1: Fatal defects (logical bugs, memory leaks, multiprocessing/concurrency issues)
   - Area 2: ML/RL structural defects (training pipeline bottlenecks, RL architectural anti-patterns)
   - Area 3: API compliance (Kiwoom REST API specification match)
2. Direct code refactoring & bug fixing preserving original design intent and robustness.
3. 100% pytest test suite pass with zero regressions.
4. Comprehensive Markdown report `Report/codebase_review_and_fixes.md`.

## Execution Steps
1. **Phase 1: Deep Codebase Survey (3 Parallel Explorers)**
   - Explorer 1: System/Architecture/Concurrency/Memory/Logic Defects
   - Explorer 2: ML/RL Training Pipeline, Model Architectures, RL Anti-patterns
   - Explorer 3: Kiwoom REST API Integration & Spec Verification
2. **Phase 2: Synthesis & Milestone Plan (`PROJECT.md`)**
   - Synthesize all findings into prioritized defect catalog.
   - Decompose into actionable, bounded milestones.
3. **Phase 3: Direct Refactoring Execution per Milestone**
   - Direct iteration loop: Explorer -> Worker -> Reviewer -> Challenger -> Auditor.
4. **Phase 4: Global Regression & Adversarial Testing**
   - Run full `pytest` suite across the entire repository.
   - Verify all tests pass 100%.
5. **Phase 5: Report Delivery & Final Communication**
   - Generate `Report/codebase_review_and_fixes.md` with detailed Before/After analysis (>=3 major issues).
   - Report completion to Sentinel with verified evidence.
