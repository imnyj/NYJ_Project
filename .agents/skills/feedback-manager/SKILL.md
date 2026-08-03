---
name: feedback-manager
description: Skill for autonomously extracting, recording, and managing user feedback for continuous learning.
---
# Feedback Manager Skill

- **목적**: 사용자와의 일상적인 대화나 에이전트의 실수에서 발생하는 피드백을 실시간으로 포착하여 자율 성장 파이프라인(Continuous Learning)에 태우는 역할을 명세합니다.

- **1. 대화 중 로그 쌓기 (Daytime Extraction)**:
  - 작업 수행 중 사용자가 행동을 교정해주거나, 불편함을 호소하거나, 에이전트가 환각(Hallucination)/오류를 범했을 경우, 메인 에이전트(CEO)는 즉시 백그라운드에서 `/home/imnyj/feedback_backlog.md` 파일에 해당 사안을 기록해야 합니다.
  - 기록 형식은 [문제 상황]과 [사용자가 원하는 올바른 행동 양식]을 명확히 분리하여 기술합니다.

- **2. 업그레이드 시 읽기 (Nightly Read & Execution)**:
  - 5시간 이상의 유휴 상태(Idle)가 감지되어 `schedule` 타이머가 발동하거나 사용자의 명시적인 지시가 있을 경우, `view_file` 도구를 사용해 누적된 백로그를 읽어 들입니다.
  - 이후 `skill-crafter` 스킬을 연계하여 백로그의 내용을 실질적인 시스템 룰(`GEMINI.md` 수정)이나 새로운 스킬 파일(`SKILL.md` 생성)로 승화시킵니다.

- **3. 업그레이드 후 초기화 (Reset Protocol)**:
  - 모든 시스템 업그레이드와 아티팩트(업그레이드 리포트) 작성이 완료되고 검증되면, 반드시 `/home/imnyj/feedback_backlog.md` 파일을 `write_to_file` 도구(Overwrite: true)를 사용하여 초기화해야 합니다.
  - 기존의 누적된 텍스트를 비우고, 시스템이 인식할 수 있는 파일 헤더(Header)만 남겨두어 다음 세션을 대비합니다.

- **4. 자동화 강제 룰 (Automation Automation)**:
  - 대화 종료 전 항상 `schedule` 도구를 호출하여 5시간 타이머를 리셋하고, 피드백 자동 업그레이드 사이클이 끊기지 않도록 강제합니다.
