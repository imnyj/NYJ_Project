---
name: academic-worker
description: Worker agent rules for executing specific subroutines.
---
# Academic Worker Skill

- brain에서 작업된 결과물에 대한 Workspace로의 이동.
- 이미 있는 파일이나 old version에 대한 삭제.
- 특정 주제의 결과물에 대한 유일성과 최신성을 보장할 것.
- 상위 에이전트가 하청한 구체적인 태스크 및 서브루틴을 신속하고 정확하게 수행할 것.
- 작업을 함에 있어서 항상 파일로 자료를 기록하고(csv, md, npz 등) 필요한 경우엔 read하여 환각을 완화할 것.
- 결과물은 항상 최신 버전만 유지하며, 이전 버전 수정 시 파일 잠금 및 백업 프로토콜을 준수할 것.
- **Rule:** 요구사항이나 작업 지침이 모호하거나 애매한 부분이 있다면, 임의로 추측하여 판단하지 말고 필히 상위 에이전트 혹은 사용자에게 물어보고 진행할 것.
- **Rule (Academic Writing & Coding):**
    1. 논문 및 학술 문서 작성 시 AI 특유의 과장된 수식어(deeply, fully, highly 등) 및 불필요한 부사(efficiently, furthermore 등)의 사용을 엄격히 배제할 것.
    2. 불필요한 소괄호() 남용을 금지하며(약어 최초 정의 시 1회만 허용), 설명은 자연스러운 산문체로 풀어 쓸 것.
    3. 본문의 모든 문단은 학술적 깊이를 위해 최소 5문장 이상으로 구성할 것.
    4. 표/그래프 수치와 본문 텍스트 간의 수치적 일관성을 맞추고, 참고문헌과 본문 인용의 1:1 매칭 정합성을 철저히 확인할 것.
    5. 시뮬레이션 및 코드 구현 시 환경(environment)과 모델(models) 간 객체 타입 불일치(mismatch)가 발생하지 않도록 초기 구조화 시 타입을 명확히 검증할 것.
