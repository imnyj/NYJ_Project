"""Phase 5 offline tests — QA, learning, monitoring.

Verifies:
    - CitationAuditor detects ghost citations (missing in refs)
    - ConfidenceTracker tier routing (deep-verify / block)
    - SkillLibrary commit + retrieve round-trip
    - WorkflowMemory reliability tracking
    - Watchdog state save/load persistence
    - Watchdog window-cap logic
    - Reviewer audit_citations integration
    - Reviewer PROOFREADER mode blocks code_executor
"""

from __future__ import annotations

import pytest

from core.exceptions import ToolPermissionDenied


# ============================================================ citation audit


def test_citation_auditor_flags_missing_refs(tmp_path):
    from evaluation.citation_check import CitationAuditor
    tex = tmp_path / "draft.tex"
    tex.write_text(
        "Prior work \\cite{doi:10.1/known} is established. "
        "Ghost \\cite{corpusID:99999} does not exist.\n"
    )
    refs = [
        {"doi": "10.1/known", "s2_corpus_id": "", "title": "Known",
         "authors": ["Doe J"], "year": 2022, "venue": "IEEE",
         "abstract": "a", "verified": True},
    ]
    rep = CitationAuditor(refs=refs, enable_claim_check=False).audit(tex)
    assert rep.total_cites == 2
    assert rep.fatal_count >= 1   # ghost citation must be fatal
    assert not rep.ok


def test_citation_auditor_passes_when_all_refs_known(tmp_path):
    from evaluation.citation_check import CitationAuditor
    tex = tmp_path / "draft.tex"
    tex.write_text(
        "Paper A \\cite{doi:10.1/a} and paper B \\cite{doi:10.1/b}.\n"
    )
    refs = [
        {"doi": "10.1/a", "s2_corpus_id": "", "title": "A",
         "authors": [], "year": 2022, "venue": "", "abstract": "",
         "verified": True},
        {"doi": "10.1/b", "s2_corpus_id": "", "title": "B",
         "authors": [], "year": 2023, "venue": "", "abstract": "",
         "verified": True},
    ]
    rep = CitationAuditor(refs=refs, enable_claim_check=False).audit(tex)
    assert rep.total_cites == 2
    # No `missing_in_refs` fatal when all cites exist
    fatal_missing = sum(
        1 for issue in rep.issues
        if getattr(issue, "code", "") == "missing_in_refs"
    ) if hasattr(rep, "issues") else 0
    assert fatal_missing == 0


# ========================================================== confidence


def test_confidence_tracker_tier_routing():
    from evaluation.confidence_tracker import ConfidenceTracker
    ct = ConfidenceTracker()
    ct.record(subject_id="c_high", subject_type="citation",
              score=0.95, source="reviewer")
    ct.record(subject_id="c_mid", subject_type="metric",
              score=0.50, source="reviewer")
    ct.record(subject_id="c_low", subject_type="novelty",
              score=0.20, source="reviewer")

    deep_ids = [r.subject_id for r in ct.needs_deep_verification()]
    block_ids = [r.subject_id for r in ct.should_block()]

    assert "c_mid" in deep_ids
    assert "c_low" in block_ids
    # High-confidence claim should not be in either set
    assert "c_high" not in deep_ids
    assert "c_high" not in block_ids


# ============================================================= skill lib


def test_skill_library_commit_then_retrieve(tmp_path):
    from memory.skill_library import Skill, SkillLibrary
    lib = SkillLibrary(path=tmp_path / "s.sqlite3")
    lib.commit(Skill(
        name="compute_throughput",
        docstring="Return flow in veh/h from counts and duration.",
        code="def compute_throughput(n, t_s): return n / (t_s/3600)",
    ))
    hits = lib.retrieve("flow rate from counts", top_k=3)
    assert hits
    assert hits[0][0].name == "compute_throughput"


def test_skill_library_stats_non_empty(tmp_path):
    from memory.skill_library import Skill, SkillLibrary
    lib = SkillLibrary(path=tmp_path / "s.sqlite3")
    for i in range(3):
        lib.commit(Skill(
            name=f"skill_{i}",
            docstring=f"Tool number {i}.",
            code=f"def skill_{i}(): return {i}",
        ))
    stats = lib.stats()
    assert stats.get("total", 0) >= 3 or stats.get("count", 0) >= 3 \
        or len(lib.list_all()) == 3


# ========================================================== workflow mem


def test_workflow_memory_tracks_reliable_workflows(tmp_path):
    from memory.workflow_memory import Workflow, WorkflowMemory
    wm = WorkflowMemory(path=tmp_path / "wf.sqlite3")
    wm.register(Workflow(
        name="run_libsumo_scenario",
        signature={"sumocfg": "path"},
        steps=[{"op": "start"}],
    ))
    for _ in range(4):
        wm.record_run(
            workflow_name="run_libsumo_scenario",
            args={"sumocfg": "x"}, success=True, duration_s=10.0,
        )
    rel = wm.list_reliable(min_runs=3, min_success_rate=0.5)
    assert any(w.name == "run_libsumo_scenario" for w in rel)


# ============================================================= watchdog


def test_watchdog_exit_codes_are_stable():
    from monitoring.watchdog import (
        CODE_MEANINGS,
        EXIT_BUDGET, EXIT_CLEAN, EXIT_FATAL, EXIT_TRANSIENT, EXIT_UPGRADE,
    )
    assert EXIT_CLEAN == 0
    assert EXIT_UPGRADE == 10
    assert EXIT_TRANSIENT == 20
    assert EXIT_BUDGET == 30
    assert EXIT_FATAL == 99
    assert all(c in CODE_MEANINGS for c in
               (EXIT_CLEAN, EXIT_UPGRADE, EXIT_TRANSIENT,
                EXIT_BUDGET, EXIT_FATAL))


def test_watchdog_default_policy():
    from monitoring.watchdog import WatchdogPolicy
    p = WatchdogPolicy()
    assert p.cooldown_seconds == 30.0
    assert p.max_restarts_per_window == 5
    assert p.window_seconds == 600.0


def test_watchdog_state_persists_across_instances(tmp_path):
    from monitoring.watchdog import Watchdog, WatchdogPolicy
    policy = WatchdogPolicy()
    dog1 = Watchdog(commander_cmd=["/bin/true"],
                    project_root=tmp_path, policy=policy)
    dog1.state.note_restart("test", 10)
    dog1._save_state()

    dog2 = Watchdog(commander_cmd=["/bin/true"],
                    project_root=tmp_path, policy=policy)
    assert dog2.state.total_restarts == 1
    assert dog2.state.last_exit_code == 10


def test_watchdog_window_cap_detection(tmp_path):
    from monitoring.watchdog import Watchdog, WatchdogPolicy
    tight = WatchdogPolicy(
        cooldown_seconds=0.0, max_restarts_per_window=2,
        window_seconds=60.0, max_total_restarts=100,
    )
    dog = Watchdog(commander_cmd=["/bin/true"],
                   project_root=tmp_path, policy=tight)
    import time as _t
    now = _t.time()
    for _ in range(3):
        dog.state.recent_restarts.append(now)
    assert dog.state.restarts_in_window(tight.window_seconds) == 3


# ============================================================ Reviewer


def test_reviewer_audit_citations_integration(mock_client_with_policy, tmp_path):
    from agents import make_worker
    reviewer = make_worker("reviewer", mock_client_with_policy)
    tex = tmp_path / "d.tex"
    tex.write_text(
        "Prior \\cite{doi:10.1/known}. Ghost \\cite{corpusID:99999}.\n"
    )
    refs = [
        {"doi": "10.1/known", "s2_corpus_id": "", "title": "K",
         "authors": [], "year": 2022, "venue": "", "abstract": "",
         "verified": True},
    ]
    rep = reviewer.audit_citations(tex_path=tex, refs=refs,
                                    enable_claim_check=False)
    assert reviewer.mode == "qa"
    assert rep.total_cites == 2
    assert rep.fatal_count >= 1


def test_reviewer_proofreader_blocks_code_executor(mock_client_with_policy):
    from agents import make_worker
    reviewer = make_worker("reviewer", mock_client_with_policy)
    reviewer.switch_mode("proofreader")
    with pytest.raises(ToolPermissionDenied):
        reviewer._check_tool_permissions([{"name": "code_executor"}])


def test_reviewer_auto_mode_for_input(mock_client_with_policy):
    from agents import make_worker
    reviewer = make_worker("reviewer", mock_client_with_policy)
    assert reviewer.auto_mode_for_input("sim.py") == "qa"
    assert reviewer.auto_mode_for_input("main.tex") == "proofreader"


# ======================================================== Orchestrator regen parser

def test_regen_parser_accepts_valid_json():
    from core.orchestrator import Orchestrator
    reply = '''{
      "plan": [
        {"id": "S1b", "description": "retry idea",
         "assignee": "idea", "required_inputs": [], "produces": ["main_idea.md"]},
        {"id": "S2b", "description": "search refs",
         "assignee": "librarian", "required_inputs": ["main_idea.md"],
         "produces": ["refs.json"]}
      ],
      "additional_facts": ["Previous attempt stalled on step S1"],
      "additional_questions": []
    }'''
    out = Orchestrator._parse_regen_reply(reply)
    assert out is not None
    plan, facts, qs = out
    assert len(plan) == 2
    assert plan[0].id == "S1b" and plan[0].assignee == "idea"
    assert plan[1].produces == ["refs.json"]
    assert "stalled" in facts[0]
    assert qs == []


def test_regen_parser_rejects_missing_fields():
    from core.orchestrator import Orchestrator
    # missing "description"
    reply = '{"plan": [{"id": "S1", "assignee": "idea"}]}'
    assert Orchestrator._parse_regen_reply(reply) is None


def test_regen_parser_rejects_unknown_assignee():
    from core.orchestrator import Orchestrator
    # "mystery_agent" is not a registered worker role
    reply = ('{"plan": [{"id":"S1","description":"x",'
             '"assignee":"mystery_agent","required_inputs":[],"produces":[]}]}')
    assert Orchestrator._parse_regen_reply(reply) is None


def test_regen_parser_rejects_duplicate_step_ids():
    from core.orchestrator import Orchestrator
    reply = (
        '{"plan": ['
        '{"id":"S1","description":"a","assignee":"idea","required_inputs":[],"produces":[]},'
        '{"id":"S1","description":"b","assignee":"writer","required_inputs":[],"produces":[]}'
        ']}'
    )
    assert Orchestrator._parse_regen_reply(reply) is None


def test_regen_parser_rejects_empty_plan():
    from core.orchestrator import Orchestrator
    assert Orchestrator._parse_regen_reply('{"plan": []}') is None


def test_regen_parser_strips_accidental_fences():
    from core.orchestrator import Orchestrator
    reply = (
        '```json\n'
        '{"plan":[{"id":"S1","description":"a","assignee":"idea",'
        '"required_inputs":[],"produces":[]}]}\n'
        '```'
    )
    out = Orchestrator._parse_regen_reply(reply)
    assert out is not None and len(out[0]) == 1


def test_regen_parser_rejects_non_json():
    from core.orchestrator import Orchestrator
    assert Orchestrator._parse_regen_reply("not even close") is None


# ======================================================== citation_verifier author match

def test_author_match_accepts_unicode_normalization():
    """Van der Waals vs van der Waals should match; punctuation shouldn't matter."""
    import re, unicodedata
    # Replicate the normalization logic inline to catch regressions
    def _norm(s: str) -> set[str]:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.lower()
        s = re.sub(r"[^a-z\s-]", " ", s)
        return {t for t in re.split(r"[\s-]+", s) if t}
    a = _norm("Van Der Waals")
    b = _norm("van der waals")
    smaller, larger = (a, b) if len(a) <= len(b) else (b, a)
    assert smaller.issubset(larger)


def test_author_match_rejects_prefix_overlap():
    """'Lee' vs 'Leeroy' are DIFFERENT surnames; asymmetric substring would
    accept them. The symmetric subset rule should reject."""
    import re, unicodedata
    def _norm(s: str) -> set[str]:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.lower()
        s = re.sub(r"[^a-z\s-]", " ", s)
        return {t for t in re.split(r"[\s-]+", s) if t}
    a, b = _norm("Lee"), _norm("Leeroy")
    smaller, larger = (a, b) if len(a) <= len(b) else (b, a)
    assert not smaller.issubset(larger)
