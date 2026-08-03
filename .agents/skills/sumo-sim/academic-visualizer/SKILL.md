---
name: academic-visualizer
description: Visualizer agent rules for plotting academic charts.
---
# Academic Visualizer Skill

- 사용해야 할 비교 방안들에 대해 이름, 색상, 순서를 파일로 저장하여 관리할 것.
- 들어가야 할 모든 방안이 반영되었는지 저장된 파일을 읽어서 확인할 것.
- 그래프의 제목을 제거할 것 (plt.title 사용 금지, LaTeX caption 이용).
- 그래프의 축, 라벨, 범례, 폰트 크기 등이 논문에 들어가기 적합하도록 학술적이고 일관된 톤을 유지할 것.
- 시각화된 결과물은 `/visualizer/`에 저장하도록 할 것. 동일한 파일에 대해서는 무조건 덮어쓰기할 것.
- 직접 코드를 짜지 말고, 해당 지시를 상세히 `coder`에게 전달할 것.

## Standardized Model Ordering and Coloring
Always use the following order and RGB color values for the 13 models:
1. LR: RGB(109,106,106) -> #6D6A6A
2. RF: RGB(237,125,49) -> #ED7D31
3. XGBoost: RGB(255,153,102) -> #FF9966
4. CatBoost: RGB(255,192,0) -> #FFC000
5. NGBoost: RGB(204,204,0) -> #CCCC00
6. MLP: RGB(112,173,71) -> #70AD47
7. FTT: RGB(0,204,153) -> #00CC99
8. ResNet: RGB(51,153,255) -> #3399FF
9. LSTM: RGB(0,102,255) -> #0066FF
10. GRU: RGB(102,102,255) -> #6666FF
11. TabR: RGB(204,102,255) -> #CC66FF
12. TabPFN: RGB(255,102,255) -> #FF66FF
13. H-ST-MBAN: RGB(255,0,0) -> #FF0000

- **Rule:** coder가 연산한 CSV 결과 파일을 직접 읽어 그래프를 그릴 것. 논문 전체에서 일관성 있는 팔레트를 유지할 것.
- **Rule:** 요구사항이나 지침이 모호하면 상위 에이전트나 사용자에게 질문할 것.

## 10. Visualization Rules (시각화 규칙)
- **Rule:** 모든 그래프 및 시각화 이미지(Plot, Chart)를 생성할 때, 이미지 내부에는 그래프 제목(Title)을 절대 포함하지 않는다. (`plt.title(...)` 함수를 사용하지 않거나 삭제한다.) 그래프의 설명 및 제목은 논문 작성 시 LaTeX의 `\caption{...}`을 통해 텍스트로 처리하므로 이미지 내부에는 제목이 없어야 한다.
