# 논문 작성 공간 안내 (paper/)

이 디렉토리는 ST-MBAN 논문 산출물을 저장한다. 새 6-에이전트 시스템
(Librarian, Idea, Experimenter, Reviewer, Writer, Qwen) 기준으로 운영한다.

## 폴더 구조

```
paper/
├── CLAUDE.md                   ← 이 파일
├── IEEEtran.cls                ← IEEE 저널 클래스 (수정 금지)
├── idea/
│   └── research_overview.md    ← Main Idea + ST-CVAE 구조 통합본 (Idea 에이전트 입력)
├── references/
│   ├── references.json         ← Librarian 산출 (검증된 인용 후보)
│   └── bibitem.tex             ← Librarian 산출 (\thebibliography 엔트리)
├── experiment/
│   └── st_cvae_baseline/       ← 기존 ST-CVAE PyTorch baseline 코드
├── data/                       ← 시뮬레이션 CSV (수집 대기 중, RSU당 ~20만 sample 목표)
├── validation/                 ← Reviewer[validator] 산출 (validation_report.json)
├── draft/
│   ├── scheme_legacy.tex       ← 직전 논문(ST-CVAE) LaTeX 원본 — 참조용 보존
│   └── 초안/                    ← 진행 중인 신규 논문 섹션 마크다운 초안
│       ├── 01_introduction.md
│       ├── 02_system_model.md
│       └── related_work_draft.md
└── final/                      ← Reviewer[proofreader] 최종 교정본 (main.tex)
```

## 연구 컨텍스트
- 주제: CCVN(IoT 관점) V2I Precaching을 위한 RSU 체류 시간 예측
- 모델: ST-MBAN (Spatio-Temporal Multi-Branch Attention Network)
- 가정: RSU-Local 학습 (분산, snapshot 기반)
- 형식: IEEE Internet of Things Journal (IEEEtran.cls)

## 현재 진행 상태 (2026-04-30 시점)
- [x] 신규 모델(ST-MBAN) 설계 완료 → `idea/research_overview.md`
- [x] 기존 논문(ST-CVAE) LaTeX 보존 → `draft/scheme_legacy.tex`
- [x] Introduction, System Model, Related Work 1차 초안 (마크다운)
- [x] ST-CVAE baseline PyTorch 코드 (학습 미실행)
- [ ] **데이터셋 수집 대기 중** — RSU 1개가 약 20만 샘플을 모을 때까지
- [ ] 사용자 요청에 따른 Reference 보강 (Librarian 호출 필요)
- [ ] Baselines 추가 구현 (시뮬 데이터셋 도착 전 사전 제작)
- [ ] 신규 main.tex 작성 (Writer 분할 작업)

## 사용자 요청 핵심
세부 내용은 `.pipeline/annotations/user_directives.md` 참고.
- 요약은 현재의 60% 분량으로 축약
- 서론을 최신 트렌드에 맞춰 재작성
- `---` 표현, 불필요한 괄호 사용 지양
- Reference 보강 (CIoV, V2I/V2V Precaching, Popularity/Mobility/Hybrid/ML/DL precaching, snapshot 기반, RSU-Local 학습)
- Reference 비교 테이블 갱신 (Work→Paper, 저자명 제거 \cite{}만, D1~D6 설명, Detail 항목 추가)
- 시뮬: 신규 baseline 추가 구현 (데이터셋 도착 전 착수)
