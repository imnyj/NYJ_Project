#!/usr/bin/env python3
"""CrossRef 조회 헬퍼. 제목으로 검색하거나 DOI로 직접 조회한다."""
import sys, json, urllib.parse, urllib.request

UA = "paper2-librarian/1.0 (mailto:imnyj1992@gmail.com)"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def fmt(it):
    au = []
    for a in it.get("author", []) or []:
        given = a.get("given", "")
        fam = a.get("family", "")
        au.append((given + " " + fam).strip() or a.get("name", ""))
    ct = it.get("container-title") or []
    ev = (it.get("event") or {}).get("name", "")
    d = {
        "doi": it.get("DOI"),
        "title": (it.get("title") or [""])[0],
        "authors": au,
        "container": ct[0] if ct else ev,
        "event": ev,
        "type": it.get("type"),
        "volume": it.get("volume"),
        "issue": it.get("issue"),
        "page": it.get("page"),
        "year": (it.get("issued", {}).get("date-parts") or [[None]])[0][0],
        "publisher": it.get("publisher"),
    }
    return d

if sys.argv[1] == "doi":
    for doi in sys.argv[2:]:
        try:
            r = fetch("https://api.crossref.org/works/" + urllib.parse.quote(doi))
            print(json.dumps(fmt(r["message"]), ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"doi": doi, "error": str(e)}, ensure_ascii=False))
else:  # query
    q = " ".join(sys.argv[2:])
    rows = int(5)
    r = fetch("https://api.crossref.org/works?rows=%d&select=DOI,title,author,container-title,event,type,volume,issue,page,issued,publisher&query.bibliographic=%s" % (rows, urllib.parse.quote(q)))
    for it in r["message"]["items"]:
        print(json.dumps(fmt(it), ensure_ascii=False))
