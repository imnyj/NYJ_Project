# -*- coding: utf-8 -*-
import json, sys, os
sys.path.insert(0, "/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

AGENT = "p2-librarian"
OUT = "/home/imnyj/Workspace/paper2/librarian"
lm, al = LockManager(), AuditLogger()

pj = os.path.join(OUT, "related_works.json")
recs = json.load(open(pj))

# AAAI 논문은 CrossRef가 journal-article로 분류하지만 실제로는 학회 논문이므로 바로잡는다.
for r in recs:
    if r["id"] == "10.1609/aaai.v30i1.10226":
        r["entry_type"] = "conference"
        r["booktitle"] = r.pop("journal")
        r["location"] = "Phoenix, AZ, USA"
        r["note"] = "AAAI 논문집은 권/호 체계로도 색인되므로 vol. 30, no. 1 표기를 함께 보존한다."

assert lm.acquire(pj, AGENT)
json.dump(recs, open(pj, "w"), ensure_ascii=False, indent=2)
lm.release(pj, AGENT)
al.log_action(AGENT, "MODIFY", pj, "AAAI 2016 항목의 entry_type을 conference로 정정하고 개최지를 보완.")

AXIS_ORDER = ["axis1_uam_comm", "axis2_sagin_vho", "axis3_proactive_prediction",
              "axis4_rl_handover", "axis5_pamdp"]
AXIS_INTRO = {
 "axis1_uam_comm":
  "UAM 기체가 어떤 통신 요구 조건 아래에서 운항하며 항공 회랑과 버티포트가 지상망에 어떤 부담을 지우는지 정리한 문헌들이다. "
  "UAM 고유 문헌을 우선 확보하였고, 회랑 커버리지 최적화 한 건은 셀룰러 연결 무인기를 대상으로 하여 UAM이 아니라 UAS 범주에 속한다는 점을 밝혀 둔다. "
  "버티포트 운영과 4D 궤적 관리는 통신 문헌이 아니라 항공 교통 관리 문헌에서 확보하였다.",
 "axis2_sagin_vho":
  "지상 셀룰러와 저궤도 위성이 함께 존재하는 다중 계층 망에서 어떤 기준으로 계층을 넘나드는지 다룬 문헌들이다. "
  "위성 링크의 지연 특성과 잦은 핸드오버가 성능을 떨어뜨리는 구조, 그리고 표준화된 조건부 핸드오버가 비지상망에서 갖는 한계까지 포괄한다.",
 "axis3_proactive_prediction":
  "궤적이나 신호를 미리 예측하여 핸드오버 결정에 반영한 문헌들이다. "
  "장단기 기억 신경망을 신호 계열 예측에 사용한 사례와 시계열 예측을 셀 선택에 결합한 사례를 확보하였다. "
  "다만 Transformer나 그래프 신경망을 예측 모듈로 쓴 핸드오버 문헌은 이번 조사에서 신뢰할 수 있는 출판본을 확인하지 못하였고, 검색에 걸린 항목은 모두 preprint여서 제외하였다.",
 "axis4_rl_handover":
  "핸드오버 결정 자체를 강화학습으로 푼 문헌들이다. "
  "근접 정책 최적화와 심층 Q 신경망 계열이 주를 이루며, 핸드오버 횟수 감소를 성능 지표나 보상 항으로 명시한 사례를 우선 수집하였다. "
  "핑퐁 억제를 보상에 직접 넣은 강화학습 문헌보다는 핸드오프 억제를 목적 함수의 한 항으로 넣은 문헌이 더 많았다.",
 "axis5_pamdp":
  "PAMDP 정식화와 혼성 행동 공간 알고리즘의 원전, 그리고 통신 분야의 응용 사례이다. "
  "이 축은 방법론의 기초에 해당하므로 3년 이내 조건을 완화하여 2016년과 2019년의 원전을 포함하였다.",
}

def fmt(r):
    au = ", ".join(r["authors"]) if r["authors"] else "(저자 정보 없음)"
    if r["entry_type"] == "conference":
        venue = r.get("booktitle", "")
        loc = r.get("location")
        bits = [venue]
        if loc:
            bits.append(loc)
        if r.get("pages"):
            bits.append("pp. " + r["pages"])
        bits.append(str(r["year"]))
        line = ", ".join(b for b in bits if b)
    else:
        bits = [r.get("journal", "")]
        if r.get("volume"):
            bits.append("vol. " + str(r["volume"]))
        if r.get("number"):
            bits.append("no. " + str(r["number"]))
        if r.get("pages"):
            bits.append("pp. " + r["pages"])
        bits.append(str(r["year"]))
        line = ", ".join(b for b in bits if b)
    out = ["#### %s" % r["title"], "", "- 저자: %s" % au, "- 게재: %s" % line,
           "- DOI: [%s](https://doi.org/%s)" % (r["doi"], r["doi"])]
    v = r["verification"]
    if not v["abstract_confirmed"]:
        out.append("- 검증 상태: 서지 정보와 DOI는 확인하였으나 초록 원문을 확보하지 못하였다.")
    out += ["", r["summary"], "", "**paper2와의 관련성.** " + r["relevance"], ""]
    return "\n".join(out)

L = []
L.append("# paper2 관련 연구 인덱스")
L.append("")
L.append("UAM 환경의 선제적 핸드오버 스케줄링을 주제로 다섯 개 조사 축에 따라 문헌 34건을 정리하였다. "
         "모든 항목은 CrossRef에서 서지 정보를 대조하고 DOI가 실제로 해석되는지 확인하였으며, "
         "요약은 Semantic Scholar 또는 OpenAlex에서 확보한 초록에 근거하여 작성하였다. "
         "초록을 확보하지 못한 세 건은 요약 대신 그 사실을 명시하였고 `unverified.md`에도 같은 내용을 기록하였다. "
         "조사 기준일은 2026년 9월 4일이다.")
L.append("")
L.append("## 축별 문헌 수")
L.append("")
L.append("| 축 | 주제 | 건수 |")
L.append("|---|---|---|")
for ax in AXIS_ORDER:
    n = sum(1 for r in recs if r["axis"] == ax)
    lab = next(r["axis_label"] for r in recs if r["axis"] == ax)
    L.append("| `%s` | %s | %d |" % (ax, lab, n))
L.append("")
for i, ax in enumerate(AXIS_ORDER, 1):
    rs = [r for r in recs if r["axis"] == ax]
    L.append("## %d. %s" % (i, rs[0]["axis_label"]))
    L.append("")
    L.append(AXIS_INTRO[ax])
    L.append("")
    for r in rs:
        L.append(fmt(r))
    L.append("")

pm = os.path.join(OUT, "related_works.md")
assert lm.acquire(pm, AGENT)
open(pm, "w").write("\n".join(L))
lm.release(pm, AGENT)
al.log_action(AGENT, "CREATE", pm, "축별 문헌 요약본 생성. 34건.")
print("wrote", pm)
