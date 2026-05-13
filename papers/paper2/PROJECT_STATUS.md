# MAFAC 프로젝트 현황 정리

작성일: 2026-04-30
대상: `/home/imnyj/papers/paper2`

---

## 1. 파일 분류 결과

### ✅ 보존 (진짜 데이터 / 핵심 코드)

| 카테고리 | 경로 | 비고 |
|---|---|---|
| **진짜 시뮬레이션 결과** | `paper/data/model_verification_theorem1.csv` | Phase 1 — Theorem 1 검증 (libsumo + PyTorch로 실측) |
| | `paper/data/model_verification_theorem2.csv` | Phase 1 — Theorem 2 검증 |
| **시뮬레이션 코드** | `simulation/run_full_simulation.py` | 메인 파이프라인 (Phase 0~5) |
| | `simulation/run_simulation.sh` | bash 래퍼 |
| | `simulation/run_scenario.py` | 단일 시나리오 평가 |
| | `simulation/run_training.py` | 단일 알고리즘 학습 |
| | `simulation/setup_network.py` | SUMO 5×5 그리드 생성 |
| | `simulation/agents/`, `env/`, `training/`, `utils/` | 코어 모듈 |
| | `simulation/config/` | SUMO 네트워크/차량 설정 |
| | `simulation/requirements.txt` | 의존성 |
| **참고 자료** | `simulation/simulation_log.txt` | 이전 실행 로그 (디버깅용) |
| | `simulation/실행 명령어.txt` | 사용자가 작성한 메모 |
| **논문 자료** | `paper/idea/idea_spec.md` | 연구 아이디어 명세 |
| | `paper/experiment/experiment_spec.json` | 실험 명세 |
| | `paper/references/{references.json, bibitem.tex}` | 참고문헌 |
| | `paper/draft/main.tex` | 초안 (단, 합성 데이터 기반 → 데이터 교체 필요) |
| | `paper/validation/validation_report.json` | 검증 리포트 |

### 🗑️ 삭제 대상

| 카테고리 | 경로 | 이유 |
|---|---|---|
| **합성 CSV 20개** | `paper/data/S1_*.csv` ×6 | Phase 3 결과인데 Phase 3가 실행 안 됨 |
| | `paper/data/S2_*.csv` ×4 | 동일 |
| | `paper/data/S3_*.csv` ×4 | 동일 |
| | `paper/data/S4_*.csv` ×2 | 동일 |
| | `paper/data/ablation_component_analysis.csv` | Phase 4 미실행 |
| | `paper/data/communication_overhead.csv` | Phase 5 미실행 |
| | `paper/data/convergence_constraint_satisfaction.csv` | Phase 2 학습 미완료, cbr=0.0 일정 → 합성 |
| | `paper/data/convergence_training_curves.csv` | cache_hit_ratio=0.0 일정, throughput=4000+ 비현실적 → 합성 |
| **잘못된 nested 디렉토리** | `simulation/home/nyj/0_paper/` | OUTPUT_DIR 경로 오설정으로 잘못 생성됨 (시뮬레이션 일부가 여기 출력) |
| **이전 체크포인트** | `simulation/checkpoints/MAFAC/ep00050/` | 50ep에서 중단된 흔적 — 새로 학습 시 처음부터 |
| **중복 코드** | `simulation/run_all.py` | `run_full_simulation.py`의 구버전. 거의 동일하지만 후자가 더 정리됨 |
| **이전 paper1 잔여물** | `simulation/backup/` (21 파일) | 다른 프로젝트의 시뮬레이션 코드 — 현재 프로젝트와 무관 |
| **캐시** | `simulation/**/__pycache__/`, `.vs/`, `.vscode/` | Python/IDE 캐시 |

### 📝 요약 정리 권장 (현재는 OK, 길어지면 갱신)

`.pipeline/brain/` 의 메모리 파일들은 정상이며 추가 요약 불필요.
다만 학습 종료 후 `commander_memory.md`, `experiment_memory.md`, `validator_memory.md` 갱신 필요.

---

## 2. 시뮬레이션 실행 명령어

### 사전 준비

```bash
cd /home/imnyj/papers/paper2

# (1) 합성 데이터 + 중복 코드 정리 — 한 번만 실행
chmod +x cleanup_synthetic.sh
./cleanup_synthetic.sh

# (2) Python 의존성 확인
cd simulation
python3 -c "import libsumo, torch, numpy; \
            print('libsumo OK'); \
            print(f'torch {torch.__version__} cuda={torch.cuda.is_available()}')"
```

### 본 실행

```bash
cd /home/imnyj/papers/paper2/simulation
chmod +x run_simulation.sh

# 옵션 A: 단계별 실행 (권장 — 중간 점검 가능)
./run_simulation.sh --phases 0,1                  # 환경+모델 검증 (~5분)
./run_simulation.sh --phases 2 --p2-episodes 500  # MAFAC 500ep 학습 (~2-6h)
./run_simulation.sh --phases 3 --p3-episodes 100  # 4시나리오×6알고리즘 (~4-12h)
./run_simulation.sh --phases 4,5 --p3-episodes 100 # Ablation+Overhead (~3-6h)

# 옵션 B: 전체 한 번에 (~12-24시간)
./run_simulation.sh

# 옵션 C: 백그라운드 + 로그 모니터링
./run_simulation.sh --phases 2 --background
tail -f simulation_log.txt

# 옵션 D: 빠른 검증 (전체 파이프라인 동작 확인용 ~30분)
./run_simulation.sh --quick
```

### 결과 확인

```bash
ls -la /home/imnyj/papers/paper2/paper/data/
# 정상 종료 시 22개 CSV 생성됨
# theorem1, theorem2, S1_*×6, S2_*×4, S3_*×4, S4_*×2,
# ablation_component_analysis, communication_overhead,
# convergence_training_curves, convergence_constraint_satisfaction
```

### 권장 실행 순서

1. `./cleanup_synthetic.sh`         ← 정리
2. `./run_simulation.sh --phases 0,1`  ← 5분, 환경 OK 확인
3. `./run_simulation.sh --phases 2 --background`  ← 2~6시간
   - 끝나면 `paper/data/convergence_training_curves.csv` 의 mean_reward가 증가 추세인지 확인
4. `./run_simulation.sh --phases 3 --background`  ← 4~12시간
5. `./run_simulation.sh --phases 4,5 --background`  ← 3~6시간

각 단계 종료 후 `tail -100 simulation_log.txt` 로 에러 없는지 확인.

---

## 3. 안전 메모

- **백업**: `simulation/checkpoints/MAFAC/` 에 학습 중간본이 저장됨. 외부 디스크/클라우드에 주기적으로 복사 권장.
- **중단 시**: `kill $(cat simulation/simulation.pid)` 로 안전 종료 가능.
- **재개**: trainer.py가 체크포인트를 자동 로드하지 않으므로 처음부터 재실행 필요. (재개 기능을 원하면 별도 구현 필요)
