# Milestone 1 적대적 테스트 리포트 (Challenge Report)

- **작성자**: `teamwork_preview_challenger_m1_2` (Empirical Challenger)
- **작성 일시**: 2026-08-18T16:02:00+09:00
- **대상 작업 공간**: `/home/imnyj/Workspace/paper4/latex/`
- **검증 범위**: Milestone 1 (LaTeX 인프라, 서지 데이터베이스, Overleaf 패키징 및 자체 포함성, Makefile 타깃)

---

## 1. Challenge Summary (적대적 테스트 요약)

**종합 위험도 평가 (Overall Risk Assessment)**: **LOW (안전)**

Milestone 1에서 구축된 LaTeX 컴파일 환경, 서지 데이터베이스(`references.bib`), 그림 자산(`figures/`), 그리고 Overleaf 배포 패키지(`paper4_latex_overleaf.zip`) 및 빌드 자동화(`Makefile`)에 대해 심층 적대적 테스트 및 샌드박스 격리 실증 검증을 수행하였습니다. 총 20개 테스트 항목 중 19개 패스(95%), 1개 사소한 개선점 발견(GNU 표준 `make check` 타깃 별칭 누락)을 확인하였으며, 주요 핵심 요구사항(Overleaf 독립 배포성, 27개 서지 무결성, 그림 자산 유효성, Makefile 멱등성)이 완벽하게 충족됨을 실증하였습니다.

---

## 2. Challenges & Attack Scenarios (도전 과제 및 공격 시나리오)

### [Low] Challenge 1: `make check` 타깃 부재로 인한 CI/표준 빌드 도구 호출 실패 가능성
- **도전한 가정 (Assumption challenged)**: 사용자가 `make check` 명령으로 검증 스위트를 실행할 수 있다는 기대
- **공격 시나리오 (Attack scenario)**: 표준 GNU Makefile 규칙 또는 사용자/스크립트가 `make check`를 실행했을 때 타깃 미정의 에러(`make: *** No rule to make target 'check'. Stop.`, exit code 2) 발생.
- **영향 범위 (Blast radius)**: `make all` 또는 `make validate`를 호출하는 환경에서는 영향 없음. `make check`를 직접 호출하는 자동화 스크립트에서만 실패 발생.
- **완화 조치 (Mitigation)**: `Makefile`에 `check: validate` 타깃 별칭을 한 줄 추가하여 표준 호환성 제고 권장.

### [Resolved/Passed] Challenge 2: Overleaf 배포 zip 패키지의 불완전한 자체 포함성 및 개발 아티팩트 유출
- **도전한 가정 (Assumption challenged)**: Zip 패키지 내부에 외부 절대 경로 참조나 개발 임시 파일(`etc/`, `.pytest_cache`, `__pycache__`)이 혼입되지 않고, 독립적인 환경에서 즉시 컴파일 가능해야 함.
- **공격 시나리오 (Attack scenario)**: 압축 파일 내부 경로 트래버설(`../`), 루트 절대 경로(`/...`), 불필요한 스크립트 혼입 여부 전수 검사 및 독립 임시 샌드박스 압축 해제 검증.
- **실증 결과 (Empirical Result)**:
  - 총 21개 엔트리 압축: `IEEEtran.cls` (281,957 bytes), `references.bib` (11,247 bytes), `figures/` 디렉토리 및 18개 PNG 이미지.
  - 절대 경로 및 상위 경로 트래버설: 0건.
  - 개발 임시 파일 혼입: 0건.
  - 샌드박스 내에서 합성 `main.tex`를 생성하여 검증 스위트 실행 시 0 에러로 완전 통과.

### [Resolved/Passed] Challenge 3: `main.tex` 부재 시 및 생성 후 `make zip`의 동작 안정성
- **도전한 가정 (Assumption challenged)**: M1 단계에서 `main.tex`가 없는 상태와 향후 M2~M5에서 `main.tex`가 생성된 상태 모두에서 `make zip`이 안전하게 작동해야 함.
- **공격 시나리오 (Attack scenario)**:
  1. `main.tex` 부재 상태에서 `make zip` 실행 시 exit code 0 및 올바른 아카이브 생성 여부.
  2. 샌드박스에서 실제 `main.tex` 생성 후 `make zip` 실행 시 아카이브 루트에 `main.tex`가 자동 포함되는지 여부.
- **실증 결과 (Empirical Result)**: 두 시나리오 모두 정상 작동(exit code 0) 확인. `main.tex` 생성 시 자동으로 최상위 루트에 포함되어 22개 아이템으로 패키징됨.

### [Resolved/Passed] Challenge 4: 서지 파일(`references.bib`) 내 특수 문자 및 중괄호 불균형으로 인한 파싱 오류
- **도전한 가정 (Assumption challenged)**: 27개 서지 항목의 LaTeX 특수문자(`&`, `%`, `_`), 중괄호 균형(`{`, `}`), 대문자 보존 표기(`{DSRC}`, `{V2V}`, `{LIMERIC}`)가 완벽히 포맷팅되어 있어야 함.
- **공격 시나리오 (Attack scenario)**: 27개 전 항목을 파싱하여 미이스케이프 특수문자, 중괄호 개수 일치성(`{` vs `}`), 필수 필드(`author`, `title`, `year`) 누락 여부 적대적 검증.
- **실증 결과 (Empirical Result)**:
  - 총 열린 중괄호 271개 vs 닫힌 중괄호 271개로 100% 균형 일치.
  - 27개 항목 모두 필수 필드 완전 포함.
  - 18개 이상의 주요 약어(`{DSRC}`, `{V2V}`, `{LIMERIC}`, `{ITS}`, `{Dec-MDP}`, `{MoE}` 등) 대문자 보존 괄호 적용 확인.
  - 텍스트 필드 내 미이스케이프 특수문자 0건.

---

## 3. Stress Test Results (실증 스트레스 테스트 결과)

| # | 테스트 시나리오 | 기대 동작 | 실제 관측 동작 | 결과 |
|---|----------------|-----------|----------------|------|
| T1 | `make help` 실행 | 도움말 및 타깃 목록 출력 (exit 0) | 타깃 목록 정상 출력, exit code 0 | **PASS** |
| T2 | `make validate` 실행 | 검증 스크립트 실행 및 0 에러 통과 | 4개 티어 전체 검증 통과 (exit 0) | **PASS** |
| T3 | `make all` 실행 | 기본 타깃 validate 실행 (exit 0) | validate 실행 후 0 에러 통과 (exit 0) | **PASS** |
| T4 | `make check` 실행 | 타깃 실행 또는 validate 별칭 | `No rule to make target 'check'` (exit 2) | **FAIL (Minor)** |
| T5 | `make compile` (pdflatex 미설치 시) | 우아한 안내 메시지 출력 후 실패 | 안내 메시지 출력 후 exit code 2 반환 | **PASS** |
| T6 | `make zip` 패키징 | `paper4_latex_overleaf.zip` 생성 | 782,353 바이트 zip 파일 생성 (exit 0) | **PASS** |
| T7 | `make clean` 실행 | 빌드 아티팩트 및 zip 삭제 | zip 및 로그 정리 완료 (exit 0) | **PASS** |
| T8 | 타깃 멱등성 (`make zip && make zip`) | 연속 실행 시 정상 완료 | 오류 없이 연속 패키징 및 삭제 완료 | **PASS** |
| T9 | `unzip -t` 구조적 무결성 | 아카이브 무결성 100% | No errors detected in compressed data | **PASS** |
| T10 | 경로 안전성 검사 | `..` 또는 `/` 경로 부재 | 트래버설/절대경로 0건 | **PASS** |
| T11 | 아카이브 청결성 검사 | 개발 임시 파일 부재 | `etc/`, `.pytest_cache` 등 혼입 0건 | **PASS** |
| T12 | `IEEEtran.cls` 바이트 일치성 | 원본과 동일한 해시 및 크기 (>200KB) | SHA-256 일치, 281,957 바이트 | **PASS** |
| T13 | `references.bib` 바이트 일치성 | 원본과 동일한 해시 및 서지 내용 | SHA-256 일치, 11,247 바이트 | **PASS** |
| T14 | `figures/` 18개 PNG 유효성 | 18개 파일 모두 올바른 PNG 헤더 | `\x89PNG\r\n\x1a\n` 매직바이트 100% 일치 | **PASS** |
| T15 | 샌드박스 합성 `main.tex` 모의 검증 | 27개 서지 인용 및 9개 그림 링크 검증 | validate_latex.py 0 에러 통과 | **PASS** |
| T16 | 서지 항목 개수 및 중복 검사 | 정확히 27개 엔트리, 0 중복 키 | 정확히 27개, 중복 0건 | **PASS** |
| T17 | 필수 서지 키 목록 일치 | PROJECT.md 27개 키와 100% 일치 | 27개 키 전원 일치 | **PASS** |
| T18 | 서지 중괄호 균형 및 필드 검사 | 중괄호 균형 및 author/title/year 존재 | 271 열림/271 닫힘, 필드 완비 | **PASS** |
| T19 | 그림 별칭(alias) 해시 일치성 | `fig*.png`와 원본 `*_*.png` 동일 | 9개 페어 SHA-256 100% 일치 | **PASS** |
| T20 | 그림 해상도 및 PIL 렌더링 검사 | 600x300 ~ 1000x600 유효 해상도 | 전 그림 손상 없이 PIL 로드 완료 | **PASS** |

---

## 4. Unchallenged Areas (미도전 영역 및 사유)

- **LaTeX 로컬 PDF 바이너리 컴파일 (`pdflatex / bibtex`)**:
  - 사유: 로컬 리눅스 호스트에 `pdflatex` 패키지가 미설치되어 있어 최종 PDF 렌더링은 Overleaf 모의 환경(샌드박스 AST/구문 파서 검증)으로 대체 검증함. (프로젝트 설계 상 Overleaf 클라우드 렌더링이 목표임).
- **본문 내용(Section I ~ VI) 수학 수식 일치성**:
  - 사유: 이는 Milestone 2 ~ Milestone 5의 영역이며, Milestone 1 범위(인프라, 서지, 그림, 패키징)에 해당하지 않음.

---

## 5. 결론 및 권고사항

Milestone 1의 모든 전달 산출물은 IEEE TWC 기준 및 Overleaf 패키징 규격을 완벽하게 충족하며 신뢰성이 입증되었습니다. 사소한 편의성 개선을 위해 `Makefile`에 `check: validate` 별칭을 추가할 것을 권장하며, 전체적인 M1 결과물에 대해 **APPROVE** 판정을 내립니다.
