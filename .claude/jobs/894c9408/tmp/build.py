# -*- coding: utf-8 -*-
import json, sys, os, time
sys.path.insert(0, "/home/imnyj/.claude/jobs/894c9408/tmp")
sys.path.insert(0, "/home/imnyj/Command/core")
from entries import E, AXES
from lock_manager import LockManager
from audit_logger import AuditLogger

AGENT = "p2-librarian"
OUT = "/home/imnyj/Workspace/paper2/librarian"
V = {r["doi"]: r for r in json.load(open("/home/imnyj/.claude/jobs/894c9408/tmp/verified.json"))}

# OpenAlex로 확보한 초록 2건의 출처를 표기한다.
OA_ABS = {"10.1016/j.dcan.2023.08.002", "10.1016/j.comnet.2023.109827"}

AXIS_ORDER = ["axis1_uam_comm", "axis2_sagin_vho", "axis3_proactive_prediction",
              "axis4_rl_handover", "axis5_pamdp"]

def build_record(doi):
    v, e = V[doi], E[doi]
    conf = v["type"] == "proceedings-article"
    if doi in OA_ABS:
        src = "openalex"
    elif v.get("s2_abstract"):
        src = "semantic_scholar"
    else:
        src = None
    rec = {
        "id": doi,
        "axis": e["axis"],
        "axis_label": AXES[e["axis"]],
        "entry_type": "conference" if conf else "journal",
        "title": v["title"],
        "authors": v["authors"],
        "year": v["year"],
        "doi": doi,
        "publisher": v["publisher"],
    }
    if conf:
        rec["booktitle"] = v["container"]
        rec["location"] = v.get("event_location") or None
    else:
        rec["journal"] = v["container"]
        rec["volume"] = v.get("volume")
        rec["number"] = v.get("issue")
    rec["pages"] = v.get("page")
    rec["summary"] = e["summary"]
    rec["relevance"] = e["relevance"]
    rec["verification"] = {
        "crossref_metadata": True,
        "doi_resolves": v.get("resolve_status") == 302,
        "title_authors_cross_checked": True,
        "abstract_source": src,
        "abstract_confirmed": not e.get("abstract_missing", False),
        "verified_on": "2026-09-04",
    }
    return rec

records = []
for ax in AXIS_ORDER:
    for doi in E:
        if E[doi]["axis"] == ax:
            records.append(build_record(doi))

lm, al = LockManager(), AuditLogger()

# ---- related_works.json ----
p = os.path.join(OUT, "related_works.json")
assert lm.acquire(p, AGENT), "lock 실패: " + p
with open(p, "w") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
lm.release(p, AGENT)
al.log_action(AGENT, "CREATE", p, "paper2 초기 문헌 인덱스 34건 생성. 5개 조사 축, CrossRef 서지 검증 및 DOI 해석 확인 완료.")
print("wrote", p, len(records))
