"""Cross-check every librarian-produced citation against Crossref.

Reads the librarian JSON files and, for each entry that carries a DOI, asks Crossref for
the publisher's own record and compares title, year, volume, issue and pages against what
the entry claims. Exists because this project has a history of fabricated citations, so
agent-reported "verified" is not taken at face value.

Usage: verify_bibliography.py <json> [<json> ...]
"""
import json
import re
import sys
import time
import urllib.request

CROSSREF = "https://api.crossref.org/works/"
UA = "paper4-bibcheck/1.0 (mailto:imnyj@kunsan.ac.kr)"


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def fetch(doi):
    req = urllib.request.Request(CROSSREF + doi, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["message"]


def entries_of(path):
    d = json.load(open(path))
    if isinstance(d, list):
        return d
    for key in ("references", "related_works", "baselines", "entries", "works"):
        if isinstance(d.get(key), list):
            return d[key]
    return []


def check(e):
    doi = (e.get("doi") or "").strip()
    eid = e.get("id", "?")
    if not doi:
        return eid, "SKIP", "no DOI (expected for ICML proceedings)"
    try:
        m = fetch(doi)
    except Exception as exc:  # noqa: BLE001
        return eid, "FAIL", f"crossref lookup failed: {type(exc).__name__}"

    problems = []
    ct = (m.get("title") or [""])[0]
    if norm(ct)[:45] != norm(e.get("title"))[:45]:
        problems.append(f"title mismatch (crossref: {ct[:55]!r})")

    dp = (m.get("published-print") or m.get("published-online") or {}).get("date-parts", [[None]])
    cy = dp[0][0]
    if cy and str(cy) != str(e.get("year")):
        problems.append(f"year {e.get('year')} != crossref {cy}")

    for field, key in (("volume", "volume"), ("issue", "issue")):
        want, got = str(e.get(field) or "").strip(), str(m.get(key) or "").strip()
        if want and got and want != got:
            problems.append(f"{field} {want} != crossref {got}")

    want_pp = norm(e.get("pages"))
    got_pp = norm(m.get("page"))
    if want_pp and got_pp and want_pp != got_pp:
        problems.append(f"pages {e.get('pages')} != crossref {m.get('page')}")

    return eid, ("OK" if not problems else "DIFF"), "; ".join(problems) or "all fields match"


def main(paths):
    total = ok = diff = fail = skip = 0
    for path in paths:
        print(f"\n=== {path} ===")
        for e in entries_of(path):
            total += 1
            eid, status, note = check(e)
            if status == "OK":
                ok += 1
            elif status == "DIFF":
                diff += 1
            elif status == "FAIL":
                fail += 1
            else:
                skip += 1
            if status != "OK":
                print(f"  [{status}] {eid}: {note}")
            time.sleep(1.0)  # be polite to Crossref
        print(f"  ({len([1 for _ in entries_of(path)])} entries checked)")
    print(f"\nTOTAL {total}: OK={ok} DIFF={diff} FAIL={fail} SKIP={skip}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
