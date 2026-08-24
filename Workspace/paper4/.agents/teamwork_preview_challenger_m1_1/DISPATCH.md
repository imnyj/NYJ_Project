## 2026-08-24T01:33:54Z

<USER_REQUEST>
당신은 Milestone 1 적대적 검증 챌린저(challenger_m1_1)입니다.

## 작업 환경 및 파일
- 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/teamwork_preview_challenger_m1_1
- 원본 요구사항: /home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md
- 프로젝트 명세: /home/imnyj/Workspace/paper4/PROJECT.md
- 공통 규칙: /home/imnyj/GEMINI.md

## 적대적 스트레스 테스트 임무
1. `code/aoi_tracker.py`, `code/sim_engine.py`, `code/resnet_moe_agent.py`에 대해 경험적/적대적 스트레스 테스트를 작성 및 실행하십시오.
2. 검증 항목:
   - 차량 수가 0대이거나 1대일 때, 밀도가 극도로 높을 때 `distance_aoi`와 `distance_pdr`에서 ZeroDivision/IndexError/NaN이 발생하지 않는지.
   - `get_latent_and_gate`에 단일 텐서(1D), 배치 텐서(2D), 비정상 범위 상태값이 입력되었을 때의 출력 shape (128차원, 3차원) 및 softmax 가중치 합이 1.0(정밀도 1e-5 이내)인지.
   - PDR이 거리(0~300m) 및 CBR에 따라 수학적으로 단조 감소하는 경향을 보이는지.
3. 결과를 `stress_test.md` 및 `handoff.md`에 기록하고 최종 판정(APPROVE 또는 REQUEST_CHANGES)을 내리십시오.
4. send_message로 부모에게 보고하십시오. 한국어로 작성하십시오.
</USER_REQUEST>
