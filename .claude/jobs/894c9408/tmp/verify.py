#!/usr/bin/env python3
"""DOI 해석 확인 + CrossRef 서지/초록 수집."""
import json, sys, time, urllib.request, urllib.error, urllib.parse

UA = "paper2-librarian/1.0 (mailto:imnyj1992@gmail.com)"
DOIS = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]

def resolve(doi):
    """doi.org가 실제로 목적지로 리다이렉트하는지 확인."""
    req = urllib.request.Request("https://doi.org/" + urllib.parse.quote(doi),
                                 headers={"User-Agent": UA}, method="HEAD")
    class NoRedir(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise urllib.error.HTTPError(req.full_url, code, newurl, headers, fp)
    op = urllib.request.build_opener(NoRedir)
    try:
        r = op.open(req, timeout=25)
        return r.status, r.geturl()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e.code, e.reason  # reason에 newurl이 담김
        return e.code, str(e)
    except Exception as e:
        return None, str(e)

out = []
for doi in DOIS:
    rec = {"doi": doi}
    try:
        req = urllib.request.Request("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                                     headers={"User-Agent": UA})
        m = json.load(urllib.request.urlopen(req, timeout=30))["message"]
        au = []
        for a in m.get("author", []) or []:
            au.append(((a.get("given", "") + " " + a.get("family", "")).strip()) or a.get("name", ""))
        ct = m.get("container-title") or []
        rec.update({
            "title": (m.get("title") or [""])[0],
            "authors": au,
            "container": ct[0] if ct else (m.get("event") or {}).get("name", ""),
            "type": m.get("type"), "volume": m.get("volume"), "issue": m.get("issue"),
            "page": m.get("page"),
            "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
            "publisher": m.get("publisher"),
            "event_location": (m.get("event") or {}).get("location", ""),
            "abstract": (m.get("abstract") or "")[:1500],
        })
    except Exception as e:
        rec["crossref_error"] = str(e)
    st, dest = resolve(doi)
    rec["resolve_status"] = st
    rec["resolve_dest"] = dest
    out.append(rec)
    time.sleep(1.0)

json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
for r in out:
    print("%-38s %-4s %s" % (r["doi"], r.get("resolve_status"), (r.get("title") or r.get("crossref_error", ""))[:70]))
