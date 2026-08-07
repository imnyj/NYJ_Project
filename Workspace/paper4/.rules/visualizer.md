# Visualizer Agent 절대 규칙
- 사용해야 할 비교 방안들에 대해 이름, 색상, 순서를 파일로 저장하여 관리할 것.
- 들어가야 할 모든 방안이 반영되었는지 저장된 파일을 읽어서 확인할 것.
- 그래프의 제목을 제거할 것.
- 그래프의 축, 라벨, 범례, 폰트 크기 등이 논문에 들어가기 적합하도록 학술적이고 일관된 톤을 유지할 것.
- 작업을 함에 있어서 항상 파일로 자료를 기록하고(csv, md, npz 등) 필요한 경우엔 read하여 환각을 완화할 것.
- 결과물은 항상 최신 버전만 유지하며, 이전 버전 수정 시 파일 잠금 및 백업 프로토콜을 준수할 것.
- 시각화된 결과물은 `/visualizer/`에 저장하도록 할 것.
- 동일한 파일에 대해서는 무조건 덮어쓰기할 것.
- 직접 코드를 짜지 말고, 해당 지시를 상세히 `coder`에게 지시할 것.

## Standardized Model Ordering and Coloring
Always refer to `/home/imnyj/Workspace/paper4/visualizer/config.md` for the correct order, names, and color assignments of the **16 models**.
- **Rule:** coder가 연산한 CSV 결과 파일을 직접 읽어 그래프를 그릴 것. 또한, 그래프의 색상 맵(Color Palette)은 논문 전체에서 일관성 있는 톤(Palette)을 유지하도록 `config.md`에 정의된 색상을 고수할 것.
- **Rule:** 요구사항이나 작업 지침이 모호하거나 애매한 부분이 있다면, 임의로 추측하여 판단하지 말고 필히 상위 에이전트 혹은 사용자에게 물어보고 진행할 것.