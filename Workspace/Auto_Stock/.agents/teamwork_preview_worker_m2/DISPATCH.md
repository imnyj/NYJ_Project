# DISPATCH — Worker M2 (Data Engine & Resource Safety)

## 2026-09-02T17:17:05+09:00

당신은 Auto_Stock 프로젝트의 **Milestone 2: Data Engine & Resource Safety**을 전담하여 구현 및 검증하는 Worker 에이전트입니다.

### 작업 환경 및 메타데이터
- 프로젝트 루트: /home/imnyj/Workspace/Auto_Stock
- 에이전트 전용 작업 디렉토리: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2
- 원본 요구사항: /home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md (반드시 먼저 읽으십시오)
- 프로젝트 명세: /home/imnyj/Workspace/Auto_Stock/PROJECT.md
- 디스패치 지침: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2/DISPATCH.md
- 시스템 조사 분석 보고서: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_sys_1/analysis.md
- 룰: /home/imnyj/GEMINI.md 준수 (파일 락 및 변경 로그 준수)

### 수행할 구체적 작업 내역
1. **modules/data/collector_price.py 리팩토링**:
   - validate_and_clean_ohlcv에서 가격 결측치 처리 시 fillna(0.0)로 인한 low 가격 0원 오염 방어 (ffill/bfill 및 유효 양수 기준 정제, 가격 0원 왜곡 원천 차단)
   - NaverPriceFetcher 및 PriceDataCollector에 close() 및 Context Manager (__enter__, __exit__) 추가하여 requests.Session() 정상 해제 및 소켓 누수 방지
2. **modules/data/collector_fundamental.py 리팩토링**:
   - 영업이익 0원(손익분기점) 또는 0% 지표 계산 시 불리언 Falsy 오작동 방어 (if stmt.revenue is not None and stmt.operating_profit is not None and stmt.revenue != 0:)
   - OpenDartCollector 및 NaverFinanceCollector에 close() 및 Context Manager 추가하여 리소스 정리
3. **modules/data/consolidator.py 리팩토링**:
   - consolidate_point_in_time에서 pd.merge_asof 수행 시 by='symbol' 또는 종목별 사전 필터링을 통해 다중 종목 펀더멘털 교차 오염 방지
4. **modules/data/streamer.py 리팩토링**:
   - NaverPollingStreamer.stop() 호출 시 세션 즉시 닫기 및 thread.join(timeout=self.timeout + 1.0)으로 좀비 스레드 방지
   - CircularBuffer 메모리 관리 및 종목별 정리 로직 강화
5. **검증 및 빌드/테스트**:
   - pytest tests/test_phase1_data.py tests/test_phase1_data_adv.py tests/test_phase1_pipeline.py tests/test_phase1_streamer.py 실행하여 데이터 엔진 전체 테스트 100% 통과 확인
   - 핸드오프 보고서(/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2/handoff.md) 작성
