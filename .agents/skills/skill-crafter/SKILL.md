---
name: skill-crafter
description: Skill for autonomously creating or updating other skills based on user feedback during nightly upgrades.
---
# Skill Crafter Skill

- **목적**: 5시간 대기 후 Nightly Upgrade(자체 시스템 업그레이드)를 수행할 때, `feedback_backlog.md`에 누적된 피드백을 분석하여 단순히 룰을 추가하는 것에 그치지 않고, 특정 역할이나 반복적인 워크플로우로 묶일 수 있는 사안이라면 이를 **독립적인 신규 스킬(Skill)로 창설하거나 기존 스킬을 업데이트**하는 역할을 수행합니다.
- **판단 기준**: 
    - 피드백 내용이 시스템 전체에 적용되는 절대 규칙이라면 `GEMINI.md`에 반영.
    - 특정 에이전트(예: writer, coder)의 행동 양식에 관한 것이라면 해당 스킬 업데이트 (`replace_file_content` 사용).
    - 완전히 새로운 워크플로우나 기능적 요구사항이라면 새로운 스킬 생성.
- **스킬 생성 및 저장 규격**:
    - **경로**: 신규 스킬은 반드시 `/home/imnyj/.agents/skills/<새로운-스킬-이름>/SKILL.md` 경로에 생성할 것.
    - **형식**: 파일 최상단에 반드시 YAML frontmatter(`name`, `description`)를 포함하고, 그 아래 마크다운 형식으로 구체적인 작업 지침(Instruction)을 기재할 것.
- **절차**:
    1. 피드백 분석 후 스킬화 가능성 평가.
    2. 생성할 스킬의 이름과 역할 명세 도출.
    3. `write_to_file` 또는 `replace_file_content` 도구를 활용하여 스킬 파일 물리적 작성.
    4. 업그레이드 리포트(Artifact)에 어떤 스킬이 생성/업데이트 되었는지 명시.
