#!/usr/bin/env python3
"""Semantic Scholar에서 초록 수집. 서지 정보는 CrossRef를 정본으로 두고 초록만 병합한다."""
import json, time, urllib.request, urllib.error, urllib.parse

recs = json.load(open("/home/imnyj/.claude/jobs/894c9408/tmp/verified.json"))
UA = "paper2-librarian/1.0 (mailto:imnyj1992@gmail.com)"
base = "https://api.semanticscholar.org/graph/v1/paper/DOI:%s?fields=title,abstract,venue,year"
for r in recs:
    url = base % urllib.parse.quote(r["doi"])
    ok = False
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            m = json.load(urllib.request.urlopen(req, timeout=30))
            r["s2_title"] = m.get("title")
            r["s2_abstract"] = m.get("abstract")
            r["s2_venue"] = m.get("venue")
            ok = True
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(6); continue
            r["s2_error"] = "HTTP %d" % e.code
            break
        except Exception as e:
            r["s2_error"] = str(e); break
    time.sleep(1.5)
json.dump(recs, open("/home/imnyj/.claude/jobs/894c9408/tmp/verified.json", "w"), ensure_ascii=False, indent=1)
for r in recs:
    a = r.get("s2_abstract")
    print("%-38s %s" % (r["doi"], ("abs %d chars" % len(a)) if a else ("NONE " + str(r.get("s2_error","")))))
