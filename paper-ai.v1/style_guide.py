# style_guide.py
"""
논문 작성 스타일 가이드.
사용자의 실제 논문(scheme.tex)에서 추출한 작성 패턴.
Writer와 Proofreader 에이전트에 주입됩니다.
"""

LATEX_STYLE_GUIDE = r"""
[LaTeX 스타일 가이드 — IEEE Transactions 형식]

1. 문서 클래스 및 필수 패키지
   \documentclass[journal]{IEEEtran}
   필수: cite, graphicx, amsmath, amssymb, algorithm, algpseudocode,
         array, subfigure, booktabs, multirow, makecell, pifont, url, orcidlink
   커스텀 컬럼:
     \newcolumntype{C}[1]{>{\centering\arraybackslash}m{#1}}
     \newcolumntype{L}[1]{m{#1}}

2. 논문 구조 (반드시 이 순서를 따를 것)
   \begin{abstract} ... \end{abstract}
   \begin{IEEEkeywords} ... \end{IEEEkeywords}
   \section{Introduction} \label{sec:introduction}
     → \IEEEPARstart{첫글자}{나머지} 로 시작
     → 마지막 단락: "The remainder of the paper is organized as follows."
     → 기여도: \begin{itemize} \item \textbf{Label:} Description \end{itemize}
   \section{Related Work} \label{sec2}
     → 비교 테이블(table*) 포함 권장
   \section{Network Model and Scheme Overview} \label{sec.net}
     → \subsection{Vehicular Network Environment}
     → \subsection{CCN-based ... Protocol}
     → \subsection{Scheme Overview}
   \section{Proposed Scheme} \label{sec.prop}
     → \subsection{...}\label{subsec:1} (각 단계별 subsection)
   \section{Performance Evaluation} \label{sec.s}
     → \subsection{Simulation Environment and Datasets} \label{sec.s0}
     → \subsection{Model Verification} \label{sec.s1}
     → \subsection{Network Performance Evaluation} \label{sec.s2}
   \section{Conclusion} \label{sec.c}
   \begin{thebibliography}{00} ... \end{thebibliography}
   \begin{IEEEbiography}[...]{Name} ... \end{IEEEbiography}

3. 참고문헌 (BibTeX 미사용)
   반드시 \begin{thebibliography}{00} ... \end{thebibliography} 사용
   \bibitem{key} 형식으로 직접 작성
   IEEE 스타일 수동 포맷:
     저널: A. Author and B. Author, ``Title,'' \emph{Journal}, vol. X, no. Y, pp. Z--W, Mon. Year.
     학회: A. Author, ``Title,'' in \emph{Proc. Conference}, City, Country, Mon. Year, pp. Z--W.
     프리프린트: A. Author, ``Title,'' \emph{arXiv preprint}, Year.
     URL: Name. [Online]. Available: \underline{URL}, Accessed on: Mon. DD, Year.
   섹션별 주석 헤더로 구분:
     % ********** Introduction **********
     % Intro: CIoV
     \bibitem{...} ...
     % ********** Related Work **********
     % RW: ML Precaching in CIoV
     \bibitem{...} ...

4. 수학적 서술 형식 (별도 LaTeX 환경 없이 볼드 텍스트 사용)
   \textbf{Definition 1 (제목).} 본문...
   \textbf{Theorem 1 (제목).} 본문...
   \textbf{Proposition 1 (제목).} 본문...
   \textbf{Proof.} 본문...

5. 분석 소제목 (Performance Evaluation 내부)
   \textbf{Implementation details.} 본문...
   \textbf{Comparative performance analysis.} 본문...
   \textbf{Ablation study.} 본문...
   \textbf{Uncertainty quantification.} 본문...
   \textbf{Sensitivity and robustness analysis.} 본문...

6. 테이블 형식
   booktabs 사용: \toprule, \midrule, \bottomrule (세로선 최소화)
   비교 테이블: table* (전체 너비) + \multirow, \cmidrule
   최우수: \textbf{값}, 차우수: \underline{값}, 비해당: -

7. Figure 경로 규칙
   시스템 구조도/다이어그램: ./figure/xxx.png 또는 .jpg
   시뮬레이션 결과 그래프: ./graph/xxx.png
   저자 사진: ./photo/xxx.jpg
   캡션: 상세하고 구체적으로 작성. 서브피규어는 (a), (b), (c) 등으로 설명.

8. 라벨 규칙
   섹션: \label{sec:introduction}, \label{sec2}, \label{sec.net}, \label{sec.prop}
   서브섹션: \label{subsec:1}, \label{subsec:2}, ...
   Figure: \label{fig:xxx}
   Table: \label{tab:tableN} 또는 \label{ta:xx}
   수식: \label{eq:xxx}

9. 섹션 시작 패턴
   "In this section, we ..."
   "This subsection describes/explains ..."
   각 섹션 시작 시 해당 섹션에서 다룰 내용을 개조식으로 미리 안내

10. 인용 스타일
    단일: \cite{key}
    복수: \cite{key1, key2, key3}
    (cite 패키지가 자동으로 정렬 및 압축)
"""

REFERENCE_FORMAT_GUIDE = r"""
[참고문헌 포맷 가이드]

Librarian이 생성하는 \bibitem 엔트리 형식:

1. 저널 논문:
\bibitem{AuthorYear} A. B. Author, C. D. Author and E. F. Author, ``Paper Title Here,'' \emph{IEEE Trans. Veh. Technol.}, vol. 00, no. 0, pp. 000--000, Mon. Year.

2. 학회 논문 (Proceedings):
\bibitem{AuthorYear} A. B. Author, ``Paper Title,'' in \emph{Proc. IEEE Conference Name}, City, Country, Mon. Year, pp. 000--000.

3. 학회 논문 (Presented):
\bibitem{AuthorYear} A. B. Author, ``Paper Title,'' presented at the \emph{Conference Name,} City, Country, Mon. DD--DD, Year.

4. 프리프린트:
\bibitem{AuthorYear} A. B. Author, ``Paper Title,'' \emph{arXiv preprint}, Year.

5. 온라인 자료:
\bibitem{key} Name. [Online]. Available: \underline{URL}, Accessed on: Mon. DD, Year.

참고문헌 키 규칙:
- 저자성Year 형식: \bibitem{Nam2023}, \bibitem{Wang2025}
- 동일 저자+연도 시 알파벳 추가: \bibitem{Wang2025a}, \bibitem{Wang2025b}
- 기관/도구: 약칭 사용: \bibitem{WAVE}, \bibitem{Ericsson}
- ML/DL 도구: 짧은 키: \bibitem{x1}, \bibitem{a1} (보조 참고문헌)
"""
