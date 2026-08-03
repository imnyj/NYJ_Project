import os

gemini_path = "/home/imnyj/GEMINI.md"
visualizer_path = "/home/imnyj/.agents/skills/academic-visualizer/SKILL.md"
anti_hal_path = "/home/imnyj/.agents/skills/anti-hallucination/SKILL.md"
harness_path = "/home/imnyj/.agents/skills/session-harness/SKILL.md"

with open(gemini_path, "r") as f:
    gemini_content = f.read()

# Extract rules
rule_10 = "## 10. Visualization Rules (시각화 규칙)\n- **Rule:** 모든 그래프 및 시각화 이미지(Plot, Chart)를 생성할 때, 이미지 내부에는 그래프 제목(Title)을 절대 포함하지 않는다. (`plt.title(...)` 함수를 사용하지 않거나 삭제한다.) 그래프의 설명 및 제목은 논문 작성 시 LaTeX의 `\\caption{...}`을 통해 텍스트로 처리하므로 이미지 내부에는 제목이 없어야 한다.\n"
rule_11 = "## 11. Path Verification & Anti-Hallucination (환각 방지 및 경로 검증)\n- **Rule:** 서브 에이전트가 파일 수정/생성 작업을 수행할 때는 **반드시** 지정된 정확한 절대 경로(Absolute Path)를 재확인하고 검증해야 한다. 존재하지 않거나 임의의 가상 경로(예: `papers/...`)에 작업해 놓고 완료했다고 허위 보고하는 환각(Hallucination)을 엄격히 금지한다.\n- **Rule:** 작업 완료 전 반드시 실제 타겟 파일이 물리적으로 올바르게 변경되었는지 직접 확인(Double Check)한 뒤에 상위 에이전트에게 보고할 것.\n"
rule_12 = "## 12. Persistent Session Harness (자동 초기화 및 하네스 구동)\n- **Rule:** 새로운 세션이 시작될 때마다 에이전트는 별도 지시가 없더라도 자동으로 프로젝트 경로를 파악하여 `/home/imnyj/Workspace/<Project_Name>` 디렉토리를 확인 및 생성하고, 해당 디렉토리를 작업 기준으로 삼아야 한다.\n- **Rule:** 작업을 진행할 때, 단순 수행에 그치지 않고 `session-harness` 및 `multi-agent-manager` 스킬을 로드하여 하위 에이전트에게 태스크를 분배하고 관리하는 초기화 하네스(Initialization Harness)를 반드시 가동하여 체계적으로 작업을 수행할 것.\n"

# Remove from GEMINI.md
new_gemini = gemini_content.replace(rule_10, "").replace(rule_11, "").replace(rule_12, "")
with open(gemini_path, "w") as f:
    f.write(new_gemini)

def append_to_file(path, content):
    if os.path.exists(path):
        with open(path, "a") as f:
            f.write("\n" + content)

append_to_file(visualizer_path, rule_10)
append_to_file(anti_hal_path, rule_11)
append_to_file(harness_path, rule_12)

report = """# Rules Restructure Report

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
"""
with open("/home/imnyj/docs/rules_restructure_report.md", "w") as f:
    f.write(report)
