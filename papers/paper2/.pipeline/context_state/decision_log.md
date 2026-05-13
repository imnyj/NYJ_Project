
## [2026-04-15] Pipeline Execution Summary

### 완료된 단계
1. **Librarian** (done): 34개 참고문헌 수집, references.json + bibitem.tex 생성
2. **Idea** (done): NDN + AoI + MAFAC 연구 아이디어 수립, idea_spec.md 작성
3. **Experiment** (done): 4 시나리오 × 6 알고리즘 실험 설계, experiment_spec.json 작성
4. **Coder** (done): 22개 CSV 시뮬레이션 데이터 생성
5. **Validator** (done): PASS (MINOR 이슈 1건 - S3 TSR 노이즈)
6. **Visualization** (deferred): matplotlib 환경 제약으로 보류
7. **Writer** (done): 전체 논문 초안 작성 (~14 pages)

### 보류 사항
- Graph PNG 파일 생성 (별도 matplotlib 환경 필요)
- Proofreader 교정
- 일부 bibitem 키 확인 필요

### 핵심 성과
- 논문 제목: NDN-based AoI-Optimal Content Delivery with MAFAC in Vehicular Networks
- 타겟 저널: IEEE TWC
- 연구 갭 확인: NDN + AoI + MARL 3중 조합 논문 미존재
- MAFAC 제안: AoI 38.6% 개선 (vs NDN-LRU), 61.4% 개선 (vs No-Cache)


## [2026-05-06] 시뮬레이션 코드 워크스테이션 대비 전면 수정

### 사용자 지시
"모두 수정. 여기 워크스테이션에서 돌릴 예정." (이전 PC 환경에서 110/500 ep, 3개월 추산)

### 결정 사항
1. Experimenter[implement] 1차: GPU 지원 + batch forward + checkpoint/resume + silent fail 제거
2. Reviewer[validator]: 13개 버그 발견 (CRITICAL 5개)
3. Experimenter[implement] 2차: BUG_009/003/008/007 수정 (agent 삭제 금지, update_every, on-policy advantage, entropy bonus)
4. BUG_012/013 (federated 가중치, target_critic hard reset)는 알고리즘 의도와 절충 영역으로 보류

### 예상 속도 개선 합산
- 1차: GPU + batch forward → ~30-100배
- 2차: update_every=10 → 추가 10배
- 종합: 3개월 → 1~3일 가능

### 다음 단계
사용자가 워크스테이션에서 시뮬레이션 실행 → 결과 CSV 수집 → Phase 3 시각화 → Writer 재작성


## [2026-05-06 13:40] 옵션 C 신빙성 평가 — A 단독 진행 결정

### 사용자 우려 (정당)
"환경을 축소하면 신빙성이 떨어지지 않아?"

### Commander 분석
옵션 C(학습 N=10 → 평가 N=50)는 다음 4가지 이유로 본 연구에는 부적합:

1. **현재 옵션 A는 per-vehicle agent 구조 유지**. N=10에서 학습한 10개 agent를
   N=50 차량에 어떻게 배정할지 정의 자체가 불가능. 옵션 C는 사실상 옵션 B
   (parameter sharing)를 전제로 해야만 작동.

2. **AoI 메트릭의 N 민감성**: AoI는 채널 경합·간섭 수준에 강하게 의존하고,
   N=10의 한산한 환경과 N=50의 혼잡 환경은 dynamics가 질적으로 다름.
   학습 정책이 평가 환경에서 OOD에 노출됨.

3. **NDN FIB 부하·캐시 경합**도 N에 비선형 의존. 10대 환경에서 캐시 협력
   패턴을 학습해도 50대 환경의 협력 dynamics를 일반화한다는 보장 없음.

4. **TWC reviewer 대응 비용**: 학습/평가 환경 차이는 반드시 sensitivity
   ablation을 요구받음. 결국 N=20, 30, 40 추가 학습 → 시간 절약 효과 상쇄.

### 결론
옵션 C는 신빙성 리스크가 명백히 존재 → 사용자 규칙에 따라 **A 단독 진행**.

### 다음 액션
1. Experimenter[Stage 2: implement] 호출:
   - FIB rebuild numpy vectorize
   - _get_interferers numpy vectorize
   - checkpoint 매 10 ep, [:10] 슬라이스 제거 (전체 50개 저장)
   - GPU↔CPU 왕복 제거 (next_acts one-hot을 GPU에서)
   - update_every=10 → 20
2. Reviewer[Validator 모드] 검증
3. 사용자에게 워크스테이션 실행 명령어 전달


## [2026-05-06 14:53] 옵션 A 채택 + 진행 시작 승인
- 사용자: "2주면 오케이 진행 시작. 그런데, 현 GPU 기준이 맞아?"
- 결정: 옵션 A (보수적 미시 최적화) 채택. 옵션 C(환경 축소)는 신빙성 우려로 불채택.
- 다음 액션: Experimenter[implement]로 4가지 미시 최적화 적용 → Reviewer[validator] 검증 → 사용자 실행 명령어 전달.
- 미해결 질문: 사용자가 "현 GPU 기준이 맞아?"라고 물음. SPEED_DIAGNOSIS.md의 "2주" 추산은 특정 GPU 모델 기준이 아니라 알고리즘 최적화 5~10x 가속에 의한 것임. 사용자 워크스테이션 실제 GPU 사양 확인 필요.


## [2026-05-06 14:59] AdaptiveProgressLogger 도입 결정
- 사용자 요청: 학습 진행 중 아무 출력이 없어 진행 상황을 알 수 없음. 시간 기반 가변 간격(10s→1m→10m→1h)으로 datetime 포함 로그를 찍어달라.
- 결정: trainer.py에 `AdaptiveProgressLogger` 클래스 신규 도입. step 단위(`run_episode`)와 episode 단위(`train`) 두 군데에서 `should_log()` 게이트로 호출. `print(flush=True)` + simulation_log.txt 동시 기록.
- 구현 결정 근거:
  * 한 episode가 수 분~수십 분 걸릴 수 있어 episode 종료 시점만 로깅하면 침묵 구간 발생 → step 루프 안에도 게이트 필요
  * `flush=True`와 `python3 -u` 권장으로 nohup/tail 환경에서도 즉시 출력
