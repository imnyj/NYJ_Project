#!/usr/bin/env python3
"""구형 .doc(OLE)의 조각 테이블을 파싱하여 본문 텍스트를 원래 순서대로 추출한다.
strings로는 표 셀이 누락되므로 이 경로를 쓴다."""
import sys, struct, olefile

def extract(path):
    ole = olefile.OleFileIO(path)
    doc = ole.openstream("WordDocument").read()
    # FIB: fWhichTblStm 은 base FIB 의 flags(offset 0x000A) 의 bit 9
    flags = struct.unpack("<H", doc[0x000A:0x000C])[0]
    tbl_name = "1Table" if (flags & 0x0200) else "0Table"
    if not ole.exists(tbl_name):
        tbl_name = "0Table" if tbl_name == "1Table" else "1Table"
    table = ole.openstream(tbl_name).read()

    # FibRgFcLcb 로 이동: 32(base) + 2(csw) + csw*2 + 2(cslw) + cslw*4 + 2(cbRgFcLcb)
    p = 32
    csw = struct.unpack("<H", doc[p:p+2])[0]; p += 2 + csw*2
    cslw = struct.unpack("<H", doc[p:p+2])[0]; p += 2 + cslw*4
    p += 2                       # cbRgFcLcb
    fcClx, lcbClx = struct.unpack("<LL", doc[p + 33*8 : p + 33*8 + 8])
    clx = table[fcClx:fcClx+lcbClx]

    # Clx 순회: 0x01=Prc(건너뜀), 0x02=Pcdt
    i = 0
    while i < len(clx):
        if clx[i] == 0x01:
            cb = struct.unpack("<h", clx[i+1:i+3])[0]
            i += 3 + cb
        elif clx[i] == 0x02:
            lcb = struct.unpack("<L", clx[i+1:i+5])[0]
            plc = clx[i+5 : i+5+lcb]
            break
        else:
            raise ValueError("알 수 없는 Clx 항목 0x%02x" % clx[i])
    n = (len(plc) - 4) // 12
    cps = [struct.unpack("<L", plc[4*k:4*k+4])[0] for k in range(n+1)]
    out = []
    for k in range(n):
        pcd = plc[4*(n+1) + 8*k : 4*(n+1) + 8*k + 8]
        fc = struct.unpack("<L", pcd[2:6])[0]
        comp = bool(fc & 0x40000000)
        fc = fc & 0x3FFFFFFF
        ln = cps[k+1] - cps[k]
        if comp:
            raw = doc[fc//2 : fc//2 + ln]
            out.append(raw.decode("cp1252", "replace"))
        else:
            raw = doc[fc : fc + ln*2]
            out.append(raw.decode("utf-16-le", "replace"))
    txt = "".join(out)
    # Word 제어문자를 읽기 쉬운 구분자로 바꾼다. 0x07 = 셀/행 끝
    txt = txt.replace("\r", "\n").replace("\x07", " | ").replace("\x0b", "\n")
    txt = "".join(c if (c >= " " or c == "\n") else " " for c in txt)
    return txt

if __name__ == "__main__":
    open(sys.argv[2], "w").write(extract(sys.argv[1]))
    print("ok", sys.argv[2])
