# Commander Memory

## [2026-04-30] 세션 인수인계 — 진행 상황 파악

### 사용자 요청
- papers/paper2 내부 파일 검토하여 진행 상황 파악
- AoI 최적화 강화학습 논문 — 현재 사용자 PC에서 학습 진행 중
- 중간에 꺼지면 백업 안 됨 → 인수인계 필요

### 파악한 핵심 사실
1. **논문 주제 확정**: NDN + AoI + MAFAC (Multi-Agent Federated Actor-Critic) in Vehicular Networks (TWC 타겟)
2. **Phase 0+1 완료**: 2026-04-16 13:01 — SUMO 네트워크/PyTorch/libsumo 검증 + Theorem 1,2 검증 통과
3. **Phase 2 학습 중**: 2026-04-16 13:52 시작 — MAFAC 500 에피소드 학습
4. **체크포인트 발견**: simulation/checkpoints/MAFAC/ep00050/ — 5개 flow의 .pt 파일 (각 441KB)
   - 50 에피소드까지 학습된 상태가 디스크에 저장되어 있음
5. **실제 데이터 vs 합성 데이터 이슈**:
   - paper/data/의 22개 CSV는 이전에 Coder가 생성한 합성 데이터 (validator도 합성임을 명시)
   - 현재 사용자가 실행 중인 시뮬레이션이 끝나면 진짜 데이터로 교체될 예정
6. **draft/main.tex 존재**: 50KB, 14p — 합성 데이터 기반 v1.0 작성 완료. 진짜 데이터로 재작성 필요
7. **final/, figure/, graph/ 비어있음**: 시각화 + 교정 미수행

### 다음 액션 (사용자 학습 종료 후)
- Phase 2 결과로 학습 곡선 CSV 갱신
- Phase 3 (성능 평가), Phase 4-5 (ablation/overhead) 실행
- 실제 데이터 기반 그래프 생성 (matplotlib)
- main.tex 데이터 교체 + Proofreader 호출

### 백업 권장 사항 사용자에게 전달
- checkpoints/MAFAC/ep00050/ 외 다른 ep 폴더 생성 여부 확인
- simulation_log.txt를 외부에 복사 권장


## [2026-04-30] 파일 정리 + 시뮬레이션 재실행 준비

### 사용자 요청
- paper2 폴더 정리: 합성 데이터 삭제, 불필요 파일 제거, 시뮬레이션 실행 명령 제시

### 분석 결과
1. **paper/data/ 22개 CSV 진단**:
   - 진짜(2개): model_verification_theorem1.csv, theorem2.csv (Phase 1 실측 — simulation_log.txt에 일치하는 결과 기록 확인)
   - 합성(20개): S1_*, S2_*, S3_*, S4_*, ablation_*, communication_*, convergence_*
     - 근거: simulation_log.txt에 Phase 2/3/4/5는 시작만 되었거나 미실행. cbr=0.0 일정, cache_hit_ratio=0.0인데 결과 있음 → 이전 Coder 합성
2. **잘못된 nested 디렉토리**: simulation/home/nyj/0_paper/ — OUTPUT_DIR 경로 오설정 흔적
3. **중복 코드**: simulation/run_all.py ≈ run_full_simulation.py (후자가 최신)
4. **이전 paper1 잔여물**: simulation/backup/ — 별개 프로젝트
5. **체크포인트**: simulation/checkpoints/MAFAC/ep00050/ — 50ep에서 중단

### 산출물
- /home/imnyj/papers/paper2/cleanup_synthetic.sh — 일괄 정리 스크립트
- /home/imnyj/papers/paper2/PROJECT_STATUS.md — 현황 보고서 + 실행 명령어

### 사용자가 직접 해야 할 작업
1. `./cleanup_synthetic.sh` 실행 (sandbox에서 os.remove 막혀 직접 삭제 못함)
2. `./run_simulation.sh --phases 0,1` 부터 단계별 실행
3. 학습 완료 후 진짜 데이터로 main.tex 재작성 (Writer 호출)


## [2026-05-06 13:35] 시뮬레이션 속도 코드 전격 검토 — 진단 완료

### 사용자 메시지
"달라진 게 거의 없는 느낌인데, 여전히 오래 걸릴 것 같고, 느려보여.
 결과만 확실하다면 관없으니 코드를 다시 한 번 전격 검토해줘."

### 검토 결과 — 4가지 진짜 병목 발견 (이전 리팩터로는 해결 안 됨)
1. ★★★ per-vehicle agent: 50대 = actor 50개 + critic 50개 + target 50개. select_action·update가 50번 sequential. GPU 활용도 1/30 수준
2. ★★★ FIB rebuild O(N²) 순수 파이썬 — 매 FIB_UPDATE_PERIOD step 3132회 sqrt
3. ★★ _get_interferers O(N²) per step
4. ★★ checkpoint slice [:10] silent bug — 50개 중 10개만 저장, resume 시 데이터 누락

### 이전 Coder 주장 ("200~500x") 평가
update 1회 미시 측정 한정. episode-level wall-time에는 거의 영향 없음. 사용자 체감과 일치.

### 산출물
/home/imnyj/papers/paper2/SPEED_DIAGNOSIS.md — 진단 보고서 + 4가지 옵션(A/A+C/B/B+C) 제안

### 다음 액션 (사용자 결정 대기)
사용자가 옵션 선택하면:
- A 또는 A+C → Experimenter[implement] 미시 최적화만
- B 또는 B+C → Idea 호출하여 idea_spec 1차 수정 + Experimenter[implement] 구조 변경
- 어느 경우든 Reviewer[validator]로 검증 후 실행 명령어 사용자에게 전달


## [2026-05-06 14:53] 옵션 A 진행 승인 + GPU 기준 질문
- 사용자가 "2주면 오케이 진행 시작"으로 옵션 A 채택. C는 거부 (신빙성 우려).
- 사용자가 "현 GPU 기준이 맞아?" 질문 — 솔직히 답해야 함:
  SPEED_DIAGNOSIS.md의 추산은 GPU 모델이 아니라 알고리즘 가속률 기준.
  실제 워크스테이션 GPU 사양(GPU 모델, VRAM)을 받아야 정확한 시간 산출 가능.
- 다음 단계: 사용자에게 정직하게 설명 + GPU 사양 받기 + 받으면 Experimenter[implement] 호출.


## [2026-05-06 14:59] 적응형 시간 기반 로깅 추가 + 실행 안내

### 사용자 메시지
"실행해줘. 그리고, 학습이 진행되는 순간 아무것도 보이지 않아서 진행이 순조롭게 되는지 모르겠단 말이야. 따라서, 로그를 print하도록 해줘. 10초마찍다가, 1분 뒤엔 1분마다, 10분 뒤엔 10분 마다, 1시간 뒤엔 1시간 마다 찍어주면 돼. 이때, 로그 찍히는 날짜 시간도 포함되면 좋겠어."

### 수행한 변경 (simulation/training/trainer.py)
1. `AdaptiveProgressLogger` 클래스 추가
   - 인터벌 규칙: <60s → 10s마다, <600s → 60s마다, <3600s → 600s마다, ≥3600s → 3600s마다
   - 모든 로그에 wall-clock datetime (YYYY-MM-DD HH:MM:SS) + 경과 시간 포함
   - print(flush=True) + simulation_log.txt에도 append 저장
2. `Trainer.__init__()`: progress_logger 인스턴스 생성
3. `Trainer.train()`:
   - 시작 시 force log "TRAIN START | algo=... | ep N/M | device=..."
   - 매 episode 종료 시 adaptive emit (간격이 충족될 때만 출력 → 빠른 ep는 묶임)
   - 학습 종료 시 force log "TRAIN END"
4. `Trainer.run_episode()`:
   - 매 step 후 should_log 체크 → 충족 시 in-episode 진행 로그 출력
     (현재 ep, step, n_veh, running_AoI, running_R)

### 사용자에게 안내한 실행 명령
```bash
cd /home/imnyj/papers/paper2/simulation

# 포어그라운드 (실시간 콘솔 확인)
python3 -u run_full_simulation.py --phases 2 --device cuda --p2-episodes 500 --resume

# 또는 백그라운드 + 로그 tail
nohup python3 -u run_full_simulation.py --phases 2 --device cuda --p2-episodes 500 --resume > simulation_log.txt 2>&1 &
tail -f simulation_log.txt
```
- `python3 -u`: stdout 버퍼링 비활성화 (즉시 출력)
- `--resume`: ep00050 체크포인트에서 이어서 학습

### 다음 액션 (사용자 학습 진행 후)
- Phase 2 종료 시 paper/data/convergence_*.csv 확인
- Phase 3 (4시나리오 × 6알고리즘) 실행 안내
- 진짜 데이터 기반 그래프 + main.tex 재작성
