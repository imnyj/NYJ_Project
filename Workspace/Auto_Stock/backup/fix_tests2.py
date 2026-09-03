import re

with open("tests/test_phase3_api.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix remaining "rt_cd" to "return_code"
content = content.replace('"rt_cd": "0"', '"return_code": 0')
content = content.replace('"rt_cd": "1"', '"return_code": 3')

# Fix pdno to stk_cd, prdt_name to stk_nm, hld_qty to hld_qty, pchs_avg_pric to pchs_avg_uv, prpr to cur_prc
content = content.replace('"pdno":', '"stk_cd":')
content = content.replace('"prdt_name":', '"stk_nm":')
content = content.replace('"pchs_avg_pric":', '"pchs_avg_uv":')
content = content.replace('"prpr":', '"cur_prc":')

# Fix output1 to acnt_evlt_remn_indv_tot
content = content.replace('"output1":', '"acnt_evlt_remn_indv_tot":')

# Fix output2 array to single fields: dnca_tot_amt -> prsm_dpst_aset_amt
content = re.sub(
    r'"output2":\s*\[\s*\{\s*"dnca_tot_amt":\s*"(\d+)",\s*"nxdy_excc_amt":\s*"\d+"\s*\}\s*\]',
    r'"prsm_dpst_aset_amt": "\1", "tot_evlt_amt": "0", "tot_evlt_pl": "0"',
    content
)

# Fix order mock output ODNO
content = re.sub(
    r'"output":\s*\{\s*"ODNO":\s*"(\d+)",\s*"ORD_TMD":\s*"\d+"\s*\}',
    r'"ord_no": "\1"',
    content
)

# Fix price mock
content = re.sub(
    r'"output":\s*\{\s*"stck_prpr":\s*"(\d+)",\s*"acml_vol":\s*"(\d+)"\s*\}',
    r'"cur_prc": "\1", "trde_qty": "\2", "pred_pre": "0", "flu_rt": "0.0", "open_pric": "\1", "high_pric": "\1", "low_pric": "\1"',
    content
)

with open("tests/test_phase3_api.py", "w", encoding="utf-8") as f:
    f.write(content)
