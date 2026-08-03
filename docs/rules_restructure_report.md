# Rules Restructure Report

## Before
`GEMINI.md` contained 12 rules, including global constraints and domain-specific rules.

## After
- **Global Rules (Kept in GEMINI.md):** Rules 1 through 9.
- **Domain-specific Rules Moved:**
  - Rule 10 (Visualization) -> `academic-visualizer/SKILL.md`
  - Rule 11 (Anti-Hallucination) -> `anti-hallucination/SKILL.md`
  - Rule 12 (Session Harness) -> `session-harness/SKILL.md`
- **Deprecated Rules:** None (all rules preserved in specific skills).

Validation: `GEMINI.md` is shorter, and specific rules are successfully appended to target skills. Zero rule loss.
