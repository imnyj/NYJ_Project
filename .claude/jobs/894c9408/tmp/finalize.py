# -*- coding: utf-8 -*-
import json, sys, os, shutil
sys.path.insert(0, "/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

AGENT = "p2-librarian"
OUT = "/home/imnyj/Workspace/paper2/librarian"
lm, al = LockManager(), AuditLogger()

# 1) parameter_sources.md 배치
src = "/home/imnyj/.claude/jobs/894c9408/tmp/out/parameter_sources.md"
dst = os.path.join(OUT, "parameter_sources.md")
assert lm.acquire(dst, AGENT), "lock 실패"
shutil.copyfile(src, dst)
lm.release(dst, AGENT)
al.log_action(AGENT, "CREATE", dst,
    "파라미터 근거 대장 생성. 7개 조사 항목, 1차 자료 8종 원문 확인, 미확인 7건 명시.")
print("wrote", dst)

# 2) Verma 2022를 축1에 추가
v = json.load(open("/home/imnyj/.claude/jobs/894c9408/tmp/verified2.json"))[0]
rec = {
 "id": v["doi"], "axis": "axis1_uam_comm", "axis_label": "UAM 통신 및 항공 회랑 네트워크",
 "entry_type": "conference", "title": v["title"], "authors": v["authors"],
 "year": v["year"], "doi": v["doi"], "publisher": v["publisher"],
 "booktitle": v["container"], "location": v["event_location"], "pages": v["page"],
 "summary": (
  "저자들은 UAM 운항을 위한 회랑을 실제 공역에 배치할 때 적용할 설계 원칙을 제시하고 댈러스 포트워스 공항 주변 공역을 대상으로 분석하였다. "
  "기존 항공 교통의 표준 계기 출발 절차와 계기 접근 절차를 분석하여 공역 수요를 파악한 뒤, 후류 난기류 권고 기준인 횡방향 2,500 ft 또는 수직 1,000 ft 분리를 충족하도록 회랑을 반복적으로 조정하였다. "
  "이 연구에서 UAM 운항은 지표 위 500 ft 고도로 계획하였고 회랑의 폭은 3,000 ft로 두었으며 그 안에 반대 방향 항로 두 개를 1,500 ft 간격으로 배치하였다."),
 "relevance": (
  "회랑의 폭과 항로 간격, 계획 고도를 구체적인 수치로 제시한 몇 안 되는 자료이다. "
  "paper2의 회랑 허용 편차와 순항 고도를 설정하는 직접적 근거가 되므로 parameter_sources.md의 1절과 6절에서 인용하고 있다."),
 "verification": {
  "crossref_metadata": True, "doi_resolves": v["resolve_status"] == 302,
  "title_authors_cross_checked": True, "abstract_source": "ntrs_fulltext",
  "abstract_confirmed": True, "verified_on": "2026-09-04"},
}

pj = os.path.join(OUT, "related_works.json")
recs = json.load(open(pj))
assert not any(r["id"] == rec["id"] for r in recs), "중복"
# 축1 블록의 끝에 삽입하여 축별 정렬을 유지한다.
last = max(i for i, r in enumerate(recs) if r["axis"] == "axis1_uam_comm")
recs.insert(last + 1, rec)
assert lm.acquire(pj, AGENT)
json.dump(recs, open(pj, "w"), ensure_ascii=False, indent=2)
lm.release(pj, AGENT)
al.log_action(AGENT, "MODIFY", pj, "Verma 외 DASC 2022 회랑 설계 논문을 축1에 추가. 총 35건.")
print("related_works.json ->", len(recs), "건")
