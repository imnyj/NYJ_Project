이 디렉토리(papers/paper3)는 이전 'NewIdea' 세션의 작업이 그대로 옮겨진 곳이야.
다음 5단계로 현재 상태를 파악해줘:

1. directory_list로 PAPER_BASE_DIR 확인 (어떤 폴더·파일이 있는지)
2. .pipeline/context_state/pipeline_state.json 읽기 — 진행 단계 파악
3. .pipeline/brain/ 안의 모든 *_memory.md 읽기 — 각 에이전트가 어디까지 했는지 파악
4. .pipeline/annotations/agent_notes.md 읽기 — 보류된 작업·이슈 확인
5. paper/data/ 폴더 확인 — 시뮬레이션 결과가 들어왔는지 확인

종합 보고 형식:
## 파이프라인 상태
- Librarian: <상태>
- Idea: <상태>
- Experimenter [design/implement/visualize]: <상태>
- Reviewer [validator/proofreader]: <상태>
- Writer: <상태>

## 다음 가능한 작업
<현재 데이터 상태에 맞춰 어떤 작업이 가능한지 1-3개 후보>

## 중요한 메모
<발견된 보류 사항, 이슈, 사용자가 알아둘 것>

이 파악이 끝나면 사용자 다음 지시를 기다려줘.