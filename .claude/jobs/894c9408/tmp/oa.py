#!/usr/bin/env python3
import json, sys, time, urllib.request, urllib.parse
UA = "paper2-librarian/1.0 (mailto:imnyj1992@gmail.com)"
for doi in sys.argv[1:]:
    try:
        req = urllib.request.Request("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi),
                                     headers={"User-Agent": UA})
        m = json.load(urllib.request.urlopen(req, timeout=30))
        inv = m.get("abstract_inverted_index")
        ab = ""
        if inv:
            pos = {}
            for w, idxs in inv.items():
                for i in idxs:
                    pos[i] = w
            ab = " ".join(pos[k] for k in sorted(pos))
        print("=== %s" % doi)
        print("TITLE :", m.get("title"))
        print("VENUE :", ((m.get("primary_location") or {}).get("source") or {}).get("display_name"))
        print("YEAR  :", m.get("publication_year"), "| BIB:", json.dumps(m.get("biblio"), ensure_ascii=False))
        print("AUTH  :", ", ".join(a["author"]["display_name"] for a in (m.get("authorships") or [])))
        print("ABS   :", ab[:1400] if ab else "(없음)")
        print()
    except Exception as e:
        print("=== %s -> ERROR %s\n" % (doi, e))
    time.sleep(1.0)
