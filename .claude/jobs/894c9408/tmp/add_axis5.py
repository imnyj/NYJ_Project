# -*- coding: utf-8 -*-
import json, sys, os
sys.path.insert(0, "/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

AGENT = "p2-librarian"
OUT = "/home/imnyj/Workspace/paper2/librarian"
V = {r["doi"]: r for r in json.load(open("/home/imnyj/.claude/jobs/894c9408/tmp/verified3.json"))}

SUM = {
"10.1145/3508546.3508598": dict(summary=(
 "저자들은 심층 강화학습 알고리즘을 행동 공간의 관점에서 조사하고 분석하여, 문제의 성격에 따라 어떤 알고리즘이 적합한지 정리하였다. "
 "행동 공간을 이산 행동 공간과 연속 행동 공간, 그리고 이산 연속 혼성 행동 공간의 세 범주로 나누고 각 범주의 차이와 연결 관계를 설명한 뒤, 범주마다 적합한 알고리즘들을 서술하였다. "
 "이산 연속 혼성 행동 공간은 파라미터화 행동 공간이라고도 불리며, 알고리즘이 이산 행동과 그 행동이 취할 연속 파라미터를 함께 출력해야 한다는 점에서 다른 두 범주와 구별된다."),
 relevance=(
 "혼성 행동 공간 알고리즘 계열을 통째로 정리한 개관 문헌이다. "
 "P-DQN의 원전이 정식 출판되지 않아 인용할 수 없는 상황에서 P-DQN을 포함한 계열 전체를 이 문헌으로 대신 서술할 수 있으므로, 방법론 절의 기준 인용이 된다."),
 abs_ok=True),

"10.1016/j.engappai.2025.112499": dict(summary=(
 "파라미터화 행동 공간에서의 혼성 강화학습을 변동 제약이라는 방식으로 다룬 논문이다. "
 "Engineering Applications of Artificial Intelligence 제162권에 게재되었으며 서지 정보와 DOI는 검증하였으나 초록 원문을 확보하지 못하였다. "
 "따라서 제목과 게재지에서 확인된 사실만 기재하며, 본문 인용 전에 원문을 직접 확인해야 한다."),
 relevance=(
 "파라미터화 행동 강화학습이 2025년까지 이어지는 활발한 연구 주제임을 보이는 최신 저널 논문이다. "
 "방법론의 최신성을 주장할 때 근거가 되므로 우선적으로 원문을 확보할 필요가 있다."),
 abs_ok=False),

"10.1109/COG52621.2021.9619068": dict(summary=(
 "저자들은 이산 행동 집합과 각 이산 행동에 대응하는 연속 파라미터 집합으로 이루어진 파라미터화 행동 공간에서 성능을 높이기 위해 이점 함수의 계층적 구조를 제안하였다. "
 "이 구조는 행위자 비평자 구조를 확장하여 이산 행동용 이점 함수와 연속 파라미터용 이점 함수를 따로 두고 더 나은 기준선을 추정한다. "
 "이 구조를 근접 정책 최적화에 결합한 방법을 HA-PPO라 부르고 하프 필드 오펜스 영역에서 평가하였다."),
 relevance=(
 "H-PPO의 후속 연구로서 파라미터화 행동 공간에서 이산 부분과 연속 부분을 어떻게 분리하여 다룰지에 관한 설계 선택을 보여준다. "
 "paper2가 망 선택과 대기 시간을 서로 다른 성격의 행동으로 다루는 구조를 정당화할 때 참고가 된다."),
 abs_ok=True),

"10.1109/MILCOM61039.2024.10774010": dict(summary=(
 "다중 셀 망의 간섭 완화에 다중 에이전트 심층 강화학습을 적용한 기존 연구들은 이산 행동 공간이나 연속 행동 공간 가운데 하나만 사용해 왔다. "
 "저자들은 행동에 이산 성분과 연속 성분이 함께 있는 경우에는 두 공간을 결합한 혼성 행동 공간이 자연스럽다고 보고, 전력 할당은 연속으로 빔포밍 선택은 이산으로 두는 혼성 다중 에이전트 알고리즘을 밀리미터파 다중 셀 망에 적용하였다. "
 "각 기지국에 배치한 에이전트가 신호 대 간섭 잡음비를 받아 행동을 결정하는 구조이다."),
 relevance=(
 "무선 통신에서 이산 선택과 연속 조절을 한 정책으로 결정하는 최신 사례이며, paper2의 행동 구조와 문제의식이 같다. "
 "통신 영역에서 혼성 행동 공간이 자연스러운 선택임을 뒷받침하는 근거로 인용할 수 있다."),
 abs_ok=True),
}

ORDER = ["10.1145/3508546.3508598", "10.1109/COG52621.2021.9619068",
         "10.1109/MILCOM61039.2024.10774010", "10.1016/j.engappai.2025.112499"]

def build(doi):
    v, s = V[doi], SUM[doi]
    conf = v["type"] == "proceedings-article"
    rec = {"id": doi, "axis": "axis5_pamdp", "axis_label": "파라미터화 행동 강화학습",
           "entry_type": "conference" if conf else "journal",
           "title": v["title"], "authors": v["authors"], "year": v["year"],
           "doi": doi, "publisher": v["publisher"]}
    if conf:
        rec["booktitle"] = v["container"]; rec["location"] = v.get("event_location") or None
    else:
        rec["journal"] = v["container"]; rec["volume"] = v.get("volume"); rec["number"] = v.get("issue")
    rec["pages"] = v.get("page")
    rec["summary"] = s["summary"]; rec["relevance"] = s["relevance"]
    rec["verification"] = {"crossref_metadata": True, "doi_resolves": v.get("resolve_status") == 302,
        "title_authors_cross_checked": True,
        "abstract_source": "semantic_scholar" if s["abs_ok"] else None,
        "abstract_confirmed": s["abs_ok"], "verified_on": "2026-09-04"}
    return rec

pj = os.path.join(OUT, "related_works.json")
recs = json.load(open(pj))
have = {r["id"] for r in recs}
new = [build(d) for d in ORDER if d not in have]
recs.extend(new)   # 축5가 마지막 축이므로 뒤에 붙이면 정렬이 유지된다
lm, al = LockManager(), AuditLogger()
assert lm.acquire(pj, AGENT)
json.dump(recs, open(pj, "w"), ensure_ascii=False, indent=2)
lm.release(pj, AGENT)
al.log_action(AGENT, "MODIFY", pj, "축5에 혼성 행동 공간 서베이 포함 %d건 추가. 총 %d건." % (len(new), len(recs)))
print("추가", len(new), "| 총", len(recs))
