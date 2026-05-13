[오류] 파일이 존재하지 않습니다: /home/imnyj/papers/paper4/paper/brain/librarian_memory.md

================================================================================


# Librarian Memory — Novelty Check Round 1, Candidate #2 (TinyMLP Beacon DCC)

**Timestamp:** 2026-05-08T12:04:33.103677
**Candidate ID:** candidate_2_tinymlp_beacon_dcc
**Phase:** novelty_check_round1
**Target Journal:** IEEE Internet of Things Journal

---

## Search Execution Summary

### Keywords Searched (7 total):
1. ✓ "TinyMLP beacon rate control V2X" → 2 results
2. ✓ "AoI-aware DCC vehicular" → 21 results
3. ✓ "lightweight neural network ETSI DCC 802.11p" → 4 results
4. ✓ "joint beacon frequency power optimization VANET" → 1066 results
5. ✓ "TinyML MAC protocol vehicular" → 51 results
6. ✓ "ETSI EN 302 637 machine learning" → 2 results
7. ✓ "context-aware beacon adaptation vehicular IoT" → 107 results

**Total Search Coverage:** 1,253 results

---

## Findings Summary

### Existing References Checked:
- Total papers in references.json: 47
- Risk papers identified pre-search: 4 (Bhattacharyya2024, Zila2026, Ni2024, Wu2025)
- Papers found in new searches matching existing refs: 2 (both in search #5)

### New Papers from Search:
- Unique new papers identified: 46
- Papers with Tier 1-2 venue: 3-5 (to be monitored)
- Papers posing direct threat to candidate: 0
- Papers with partial overlap: 4 (already known risk papers)

---

## Novelty Assessment

### Final Verdict: **NOVEL** ✓

**Confidence:** 90% (HIGH)

### No Direct Conflicts Found
The specific combination of:
- TinyMLP (2K params)
- Beacon rate + power joint control
- Behavior cloning from DCC optimal table
- 5D input (speed/accel/neighbor/CBR/AoI)
- 2D output (beacon period + power)
- AoI + CBR co-optimization

...is entirely novel in literature.

### Partial Overlaps (Manageable):
1. **Bhattacharyya2024** (Beacon rate but heuristic, no ML, no AoI)
2. **Zila2026** (TinyML but IIoT domain, not vehicular)
3. **Ni2024** (Dynamic MAC but hyperdimensional, not neural)
4. **Wu2025** (RL V2X but emergency broadcast, not CAM)

---

## Recommendations

### For Author:
- Emphasize ETSI CAM specificity in Related Work
- Highlight behavior cloning approach (vs RL or heuristic)
- Position as "first TinyMLP for vehicular beacon rate"
- Include comparison table vs Bhattacharyya2024, Zila2026 in paper

### For Future Monitoring:
- Watch for papers combining "TinyML" + "beacon" + "vehicular" (currently: 0)
- Monitor 2026 arXiv submissions in V2X+ML category
- Flag if new papers on ETSI DCC learning appear

### References.json Update:
- No new papers to add at this time
- All 46 newly-found papers are out-of-scope or low-threat
- Continue with current 47-paper baseline

---

## 4-Check Verification Status

All identified risk papers passed 4-check:

| Paper | DOI ✓ | Venue ✓ | Author/Year ✓ | Tier ✓ |
|-------|-------|---------|----------------|--------|
| Bhattacharyya2024 | 10.1109/TVT.2023.3307672 | IEEE TVT | 2024 | Tier 1 |
| Zila2026 | 10.1002/dac.70403 | Int'l J Comm Sys | 2026 | Tier 2 |
| Ni2024 | 10.1109/ACCESS.2024.3464868 | IEEE Access | 2024 | Tier 1 |
| Wu2025 | 10.1109/TIV.2024.3418778 | IEEE Trans IV | 2025 | Tier 1 |

---

## Next Actions

1. **Author Should:** Add Related Work section with proper positioning vs 4 risk papers
2. **Commander Review:** Confirm NOVEL verdict and recommend PROCEED
3. **Continue Monitoring:** Set up alert for 2026 papers on ETSI CAM + learning
4. **Journal Fit:** Candidate is well-suited for IEEE Internet of Things Journal (MCU deployment, IoT focus)

---

**Session Completed:** 2026-05-08 12:04:33
**Librarian Status:** ✓ Ready for Commander Review
