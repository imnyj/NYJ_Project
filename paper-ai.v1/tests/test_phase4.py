"""Phase 4 offline tests — ReWOO planner + DAG executor + tools.

Verifies:
    - ReWOO plan parsing + validation + ref substitution
    - DAGExecutor wave-based parallelism
    - DAGExecutor error propagation (upstream fails → dependent skipped)
    - CodeExecutor Python/timeout/exit-code
    - SumoRunner preflight returns structured info
    - LaTeXCompiler preflight returns binary paths
    - Experimenter DESIGNER↔ENGINEER mode permission gating
    - Writer allowlist + render_figure artifact capture
    - BatchRequest construct + unique custom_id
"""

from __future__ import annotations

import time

import pytest

from core.dag_executor import DAGExecutor, ToolRegistry
from core.exceptions import AgentModeError, ToolPermissionDenied
from core.planner import parse_plan, substitute_refs


# ================================================================= planner


def test_parse_plan_extracts_steps_and_deps():
    raw = """
Plan: find, verify, summarize.
#E1 = web_search[V2X AoI]
#E2 = citation_verify[#E1]
#E3 = summarize[#E2]
"""
    plan = parse_plan(raw, question="what's new?")
    assert len(plan.steps) == 3
    assert plan.steps[0].id == "#E1"
    assert plan.steps[0].tool == "web_search"
    assert plan.steps[1].depends_on == ["#E1"]
    assert plan.steps[2].depends_on == ["#E2"]


def test_parse_plan_multi_dependency():
    raw = """Plan: parallel
#E1 = a[x]
#E2 = b[y]
#E3 = c[#E1 + #E2]
"""
    plan = parse_plan(raw, question="q")
    assert plan.steps[2].depends_on == ["#E1", "#E2"]


def test_plan_validate_rejects_unknown_tools():
    plan = parse_plan(
        "Plan: x\n#E1 = known[x]\n#E2 = unknown_tool[y]\n",
        question="q",
    )
    errors = plan.validate({"known"})
    assert errors
    assert any("unknown" in e for e in errors)


def test_substitute_refs_replaces_tokens():
    resolved = {"#E1": "alpha", "#E2": "beta"}
    result = substitute_refs("src=#E1 dst=#E2 keep=#E9", resolved)
    assert "alpha" in result
    assert "beta" in result
    assert "#E9" in result   # unresolved tokens left in place


# =============================================================== DAG exec


def _make_registry_with_fake_tools():
    reg = ToolRegistry()

    def tool_a(args):
        """tool_a docstring"""
        return f"A({args[:20]})"

    def tool_b(args):
        """tool_b slow"""
        time.sleep(0.02)
        return f"B({args[:20]})"

    def tool_err(args):
        """tool_err always fails"""
        raise RuntimeError("boom")

    reg.register("a", tool_a)
    reg.register("b", tool_b)
    reg.register("err", tool_err)
    return reg


def test_dag_runs_parallel_independent_steps_in_two_waves():
    reg = _make_registry_with_fake_tools()
    plan = parse_plan(
        "Plan: parallel\n#E1 = a[x]\n#E2 = b[y]\n#E3 = a[#E1 #E2]\n",
        question="q",
    )
    ex = DAGExecutor(reg, max_parallel=4, per_step_timeout=5.0)
    result = ex.execute(plan)
    assert result.succeeded == 3
    assert result.waves == 2
    assert "A(x)" in plan.steps[2].result
    assert "B(y)" in plan.steps[2].result


def test_dag_skips_dependents_when_upstream_fails():
    reg = _make_registry_with_fake_tools()
    plan = parse_plan(
        "Plan: err\n#E1 = err[x]\n#E2 = a[#E1]\n#E3 = a[independent]\n",
        question="q",
    )
    result = DAGExecutor(reg).execute(plan)
    assert result.failed == 1
    assert result.skipped == 1
    assert result.succeeded == 1
    # Independent step #E3 must still complete
    assert plan.steps[2].result is not None


# =============================================================== CodeExecutor


def test_code_executor_python_stdout_captured():
    from tools.code_executor import CodeExecutor
    ex = CodeExecutor(default_timeout=10.0)
    r = ex.run("print('hi', 40+2)", language="python")
    assert r.success
    assert "hi 42" in r.stdout


def test_code_executor_respects_timeout():
    from tools.code_executor import CodeExecutor
    ex = CodeExecutor(default_timeout=10.0)
    r = ex.run("import time; time.sleep(5)", language="python", timeout=0.5)
    assert r.timed_out
    assert not r.success


def test_code_executor_captures_nonzero_exit():
    from tools.code_executor import CodeExecutor
    ex = CodeExecutor(default_timeout=10.0)
    r = ex.run("import sys; sys.exit(3)", language="python")
    assert not r.success
    assert r.returncode == 3


# ============================================================== SUMO / LaTeX


def test_sumo_preflight_returns_structured_info():
    from tools.sumo_runner import SumoRunner
    pre = SumoRunner().preflight()
    for key in ("libsumo_importable", "traci_importable",
                "sumo_home", "sumo_home_exists"):
        assert key in pre


def test_latex_preflight_returns_binary_paths():
    from tools.latex_compiler import LaTeXCompiler
    pre = LaTeXCompiler().preflight()
    assert "pdflatex" in pre
    assert "bibtex" in pre


# =========================================================== Experimenter


def test_experimenter_designer_mode_blocks_sumo_runner(mock_client_with_policy):
    from agents import make_worker
    exp = make_worker("experimenter", mock_client_with_policy)
    assert exp.mode == "designer"
    with pytest.raises(ToolPermissionDenied):
        exp._check_tool_permissions([{"name": "sumo_runner"}])


def test_experimenter_engineer_mode_allows_sumo_runner(mock_client_with_policy):
    from agents import make_worker
    exp = make_worker("experimenter", mock_client_with_policy)
    exp.switch_mode("engineer")
    # Should NOT raise
    exp._check_tool_permissions([{"name": "sumo_runner"}])


def test_experimenter_require_mode_raises_when_wrong(mock_client_with_policy):
    from agents import make_worker
    exp = make_worker("experimenter", mock_client_with_policy)
    with pytest.raises(AgentModeError):
        exp.require_mode("engineer")   # it's in designer


def test_experimenter_execute_code_refuses_designer_mode(
    mock_client_with_policy,
):
    from agents import make_worker
    exp = make_worker("experimenter", mock_client_with_policy)
    with pytest.raises(AgentModeError):
        exp.execute_code("print(1)")


# ================================================================ Writer


def test_writer_allowlist(mock_client_with_policy):
    from agents import make_worker
    writer = make_worker("writer", mock_client_with_policy)
    assert "latex_compiler" in writer.allowed_tools()
    assert "code_executor" in writer.allowed_tools()


def test_writer_render_figure_writes_artifact(
    mock_client_with_policy, tmp_path,
):
    from agents import make_worker
    writer = make_worker("writer", mock_client_with_policy)
    r = writer.render_figure(
        "open('out.txt','w').write('ok')",
        output_dir=tmp_path,
    )
    assert r.success
    assert any("out.txt" in a for a in r.artifacts)


# ================================================================= Batches


def test_batch_request_has_unique_custom_id():
    from tools.batch_client import BatchRequest, new_custom_id
    a = BatchRequest(custom_id=new_custom_id("x"), agent="librarian",
                     user_turn="hi", task_type="classify")
    b = BatchRequest(custom_id=new_custom_id("x"), agent="librarian",
                     user_turn="hi", task_type="classify")
    assert a.custom_id != b.custom_id
    assert a.custom_id.startswith("x_")
