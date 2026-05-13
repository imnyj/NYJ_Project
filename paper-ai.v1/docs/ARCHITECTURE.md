# paper-ai — 통합 설계도 (Final Architecture)

> Multi-Agent LLM 시스템. Windows WSL2 + Python venv에서 SCIE급 논문을
> 자동 생성. Anthropic Claude API 기반. 5 phases, 53 Python 파일.

---

## 🎯 설계 목표 요약

| 목표 | 달성 방식 |
|---|---|
| **토큰 효율성 최우선** | Prompt caching × Agent Skills × Haiku/Sonnet/Opus 라우팅 × Batches × ReWOO × Blackboard — 이론적 누적 절감 ~80-92% |
| **전반적 성능 향상** | Contextual Retrieval + PaperQA2 + Hybrid Search + 기계적 인용 검증 + VLM 도표 비평 + Selective CoVe |
| **단일 사용자 WSL2 친화** | 단일 프로세스 + SQLite + 로컬 venv; 마이크로서비스·K8s·메시지 큐 없음 |
| **손상 방지 자가 업그레이드** | 사용자 승인 게이트 + 스냅샷 + 원자적 교체 + 스모크 테스트 + 롤백 |

---

## 🏛️ 9계층 아키텍처 (post-refactor)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [L0] Watchdog — Commander 프로세스 감시 + 재시작 정책                   │
│   monitoring/watchdog.py · 종료 코드 프로토콜 (0/10/20/30/99)          │
│   paths.watchdog_state, paths.rollback_flag 사용                      │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ spawn (python cli.py ...)
┌──────────────────────────────────────────────────────────────────────┐
│ [Entry] cli.py (얇은 argparse 라우터) → cli_commands/*.py              │
│   config_verify / demo / command / interactive / pipeline             │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ instantiates
┌──────────────────────────────────────────────────────────────────────┐
│ [L1] Commander (프로젝트 루트) — 총괄 지휘 + 업그레이드 요청            │
│   commander.py (Opus 4.7) · 도구 0개, 순수 오케스트레이션              │
│   블랙보드 아티팩트 발행 없음 (directive-only)                         │
│   core/self_upgrader.py + core/upgrade_approval.py                  │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ drives
┌──────────────────────────────────────────────────────────────────────┐
│ [L2] Orchestrator — 파이프라인 실행                                    │
│   core/orchestrator.py (production path)                            │
│   core/orchestrator_langgraph.py (EXPERIMENTAL)                      │
│   core/task_ledger.py (외부 루프)                                     │
│   core/progress_ledger.py (내부 루프: 3-stall 감지)                   │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ plans
┌──────────────────────────────────────────────────────────────────────┐
│ [L3] ReWOO Planner + LLMCompiler DAG Executor                        │
│   core/planner.py · plan 1회 + solve 1회 (−64% tokens)                │
│   core/dag_executor.py · wave 단위 병렬 (6.7× cheaper)                │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ make_worker(role, client)
┌──────────────────────────────────────────────────────────────────────┐
│ [L4] 5 Worker Agents (agents/WORKER_REGISTRY)                        │
│   agents/idea.py       (Sonnet)  · 기여도, 스토리텔링                  │
│   agents/librarian.py  (Haiku)   · SCIE 검색 + DOI 검증               │
│   agents/experimenter  (Sonnet)  · Designer↔Engineer 2-모드           │
│   agents/reviewer.py   (Sonnet)  · QA↔Proofreader 2-모드              │
│   agents/writer.py     (Sonnet)  · LaTeX + matplotlib                 │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ publish / subscribe
┌──────────────────────────────────────────────────────────────────────┐
│ [L5] Blackboard — 구조화 문서 pub/sub                                  │
│   core/blackboard.py · 채팅 메시지 폐기, 12개 typed artifact          │
│   core/artifacts.py  · PRODUCER 계약 + SUBSCRIBERS 세트               │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ writes to / reads from
┌──────────────────────────────────────────────────────────────────────┐
│ [L6] Memory — SQLite 기반 단일 파일 저장 (경로는 core/paths.py)        │
│   memory/corpus_store.py      · FTS5(BM25) + sqlite-vec               │
│   memory/cache.py             · ResponseCache (AnthropicClient 연동)   │
│   memory/skill_library.py     · Voyager 스킬 축적                      │
│   memory/workflow_memory.py   · AWM: N단계 → 단일 호출                 │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ consults / invokes
┌──────────────────────────────────────────────────────────────────────┐
│ [L7] Tools — 외부 환경 어댑터                                          │
│   tools/anthropic_client.py   ★ 5층 캐싱 + ResponseCache 연동         │
│   tools/batch_client.py         Batches API (−50%, 캐싱과 스택)       │
│   tools/code_executor.py        샌드박스 실행 (Python/bash/Octave)     │
│   tools/sumo_runner.py          libsumo + traci 폴백                  │
│   tools/latex_compiler.py       pdflatex 4-pass + bibtex              │
│   tools/web_search.py           Crossref + S2, SCIE 화이트리스트       │
│   tools/pdf_reader.py           GROBID + pypdf 폴백                   │
│   tools/embeddings.py           SPECTER2 + Hash 폴백                  │
│   tools/reranker.py             bge-reranker-v2-m3 + NoOp 폴백        │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ retrieval operations
┌──────────────────────────────────────────────────────────────────────┐
│ [L8] Retrieval — 고급 RAG 파이프라인                                   │
│   retrieval/contextual_retrieval.py · 청크당 50-100 토큰 문맥 prefix  │
│   retrieval/hybrid_search.py        · BM25 + 벡터 + RRF + rerank      │
│   retrieval/citation_verifier.py    · DOI + retraction + 메타검증     │
│   retrieval/paperqa_adapter.py      · PaperQA2 SOTA 래퍼              │
└──────────────────────────────────────────────────────────────────────┘
                               ↓ evaluation gates
┌──────────────────────────────────────────────────────────────────────┐
│ [L9] Evaluation + Monitoring                                         │
│   evaluation/citation_check.py    · \cite{} 마커별 sBERT + 메타 감사   │
│   evaluation/vlm_figure_critique.py · Claude vision으로 도표 검수     │
│   evaluation/selective_cove.py    · 신뢰도 <0.7 클레임만 CoVe         │
│   evaluation/confidence_tracker.py · 티어 라우팅 (deep/block)          │
│   monitoring/watchdog.py          · Commander 프로세스 supervision    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 핵심 결정사항 (모두 시행 완료)

### 에이전트 9 → 6 통합
- **병합**: Experiment+Coder → Experimenter (Designer↔Engineer 모드)
- **병합**: Validator+Proofreader → Reviewer (QA↔Proofreader 모드)
- **강등**: Visualization → Writer의 도구로 흡수
- **이유**: MoA 연구가 세분화된 다수 에이전트의 토큰 낭비 + 품질 저하를 증명

### 도구 권한 강제
- `config/agents.yaml:tools[<agent>]` = 단일 진실 원천
- 런타임 권한 = `ALLOWED_TOOLS_NATIVE ∩ YAML allow-list`
- 모드 게이팅: Experimenter DESIGNER ≠ ENGINEER 권한, Reviewer PROOFREADER ≠ QA 권한

### Librarian SCIE 전용
- **허용**: IEEE, Elsevier, ACM, Nature, MDPI, Springer, Wiley, T&F, APS, Oxford, Cambridge
- **차단**: arXiv, bioRxiv, ResearchGate, Academia.edu, Scopus, Google Scholar
- 차단은 `tools/web_search.py`와 `retrieval/citation_verifier.py` 두 곳에서 이중 집행

### 자가 업그레이드 정책
- **매번 사용자 승인 필수** (자율 수정 금지)
- 승인 프로토콜: `y` / `N` / `d(diff)` / `r(reason)`
- 실행 단계: snapshot → atomic replace → smoke test → 실패 시 롤백
- 재시작 쿨다운 30s, 10분 내 최대 5회

### 토큰 예산 감시
- 논문당 예산: 2M 입력 토큰, 300K 출력, $50
- 라우팅 분포 목표: Haiku 60% / Sonnet 30% / Opus 10%
- 실시간 드리프트 경고 (±15% 허용 오차)

---

## 📐 데이터 흐름: 한 편의 논문 생성

```
User: "V2X AoI-aware beaconing 논문 써줘"
  │
  ├─▶ Watchdog spawns Commander (Opus)
  │     │
  │     ▼
  ├─▶ TaskLedger.set_plan(default_paper_plan) — 8단계
  │     │
  ├─▶ S1: Idea      → main_idea.md, storyline.md
  ├─▶ S2: Librarian → refs.json (SCIE만, DOI 검증됨)
  ├─▶ S3: Idea      → novelty_check.md  (refs 대조)
  ├─▶ S4: Experimenter [DESIGNER] → experiment_spec.yaml
  ├─▶ S5: Experimenter [ENGINEER] → sim_results.npz (libsumo 실행)
  ├─▶ S6: Reviewer [QA] → qa_report.md (공정성/버그/수치 검증)
  │     │       ↓ FAIL이면 S5 재작업 (최대 2회)
  ├─▶ S7: Writer    → drafts/main.tex + figures/*.pdf
  │     │       ↓ Writer가 자체 compile로 pre-check
  ├─▶ S8: Reviewer [PROOFREADER] → polish_report.md
  │     │       ↓ 동시: CitationAuditor가 \cite{} 전수 검사
  │     │         VLMFigureCritic이 도표 감사
  │     │         SelectiveCoVe가 신뢰도 <0.7 클레임 검증
  │     │
  │     ▼
  └─▶ Commander 품질 게이트 통과 → output/final/*.pdf
```

---

## 🛡️ 다층 방어 체계

### Hallucination 방지 (4층)
1. **ID-only 인용**: `\cite{corpusID:N}` / `\cite{doi:X}` — BibTeX는 절대 LLM이 만들지 않음
2. **DOI 실존 검증**: Crossref API로 모든 참고문헌 resolve 확인
3. **Retraction 체크**: Crossref Labs로 철회 논문 자동 배제
4. **sBERT 클레임 검증**: 인용 주변 문장 ↔ 초록 유사도 < 0.2면 flag

### 무한 루프 차단 (4층)
1. **Per-step 정체**: 3회 무진전 → StallDetected → 계획 재생성
2. **Per-step 하드캡**: 5회 시도 → 즉시 차단
3. **Global 재생성 제한**: 3회 재생성 → GlobalStallDetected → 사용자 에스컬레이션
4. **Watchdog 윈도**: 10분 내 5회 재시작 → 프로세스 중단 + 사용자 알림

### 예산 폭주 방지 (3층)
1. **Per-turn**: 180K 입력 / 16K 출력 토큰 하드 캡
2. **Per-session**: 500K / 80K / $15
3. **Per-paper**: 2M / 300K / $50 + 60% 경고

---

## 🚀 WSL2 운영 명령어

```bash
# 초기 셋업
bash scripts/setup_venv.sh
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY 편집

# 구조 검증 (API 불필요)
python cli.py --verify-config
pytest tests/ -v

# 일회성 Commander 명령
python cli.py --command "V2X AoI 논문 기획"
python cli.py Command.md                # 레거시 호환 (positional arg)

# REPL 대화
python cli.py --interactive

# 풀 파이프라인
python cli.py --pipeline "age-of-information V2X beaconing"
python cli.py --pipeline "..." --langgraph   # 실험적 체크포인트 모드

# Watchdog + Commander (프로덕션 모드)
python -m monitoring.watchdog
```

---

## 📊 파일 현황

| 구분 | 파일 수 |
|---|---|
| Python 소스 | 53 |
| YAML 설정 | 5 |
| 에이전트 프롬프트 | 6 |
| Agent Skills (SKILL.md) | 6 |
| 총 (including 스크립트/README/tests) | **75+** |

---

## 📚 연구 근거 (전체 기법 인용)

| 기법 | 구현 위치 | 출처 |
|---|---|---|
| Multi-breakpoint caching | `tools/anthropic_client.py` | Anthropic docs 2026 |
| Agent Skills | `skills/*/SKILL.md` | Anthropic Oct 2025 |
| Model routing | `config/routing.yaml` | RouteLLM 2406.18665 |
| Batches API | `tools/batch_client.py` | Anthropic 2024 |
| Contextual Retrieval | `retrieval/contextual_retrieval.py` | Anthropic Sept 2024 |
| Hybrid BM25+SPECTER2+RRF | `retrieval/hybrid_search.py` | Cormack+2009 / AI2 EMNLP 2023 |
| bge-reranker-v2-m3 | `tools/reranker.py` | BAAI |
| PaperQA2 | `retrieval/paperqa_adapter.py` | arXiv:2409.13740 |
| ID-only citations + verify | `retrieval/citation_verifier.py` | GhostCite 2025 |
| sBERT claim check | `evaluation/citation_check.py` | FActScore 2305.14251 |
| MetaGPT blackboard | `core/blackboard.py` | ICLR 2024 2308.00352 |
| Magentic-One dual ledger | `core/task_ledger.py` + `core/progress_ledger.py` | 2411.04468 |
| ReWOO planner | `core/planner.py` | arXiv:2305.18323 |
| LLMCompiler DAG | `core/dag_executor.py` | ICML 2024 2312.04511 |
| Voyager skill library | `memory/skill_library.py` | arXiv:2305.16291 |
| Agent Workflow Memory | `memory/workflow_memory.py` | ICML 2025 2409.07429 |
| VLM figure critique | `evaluation/vlm_figure_critique.py` | AI Scientist v2 2504.08066 |
| Chain-of-Verification | `evaluation/selective_cove.py` | arXiv:2309.11495 |

---

*Final architecture rev — 5 phases, all pass integration testing.*
