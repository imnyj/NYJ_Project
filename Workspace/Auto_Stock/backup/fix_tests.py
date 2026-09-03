import re

with open("tests/test_phase3_api.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace mock_base_url
content = content.replace('"https://openapivts.kiwoom.com"', '"https://mockapi.kiwoom.com"')
content = content.replace('"https://openapi.kiwoom.com"', '"https://api.kiwoom.com"')

# Replace token mock
content = content.replace('"access_token": "mock_token"', '"token": "mock_token"')
content = content.replace('"expires_in": 86400', '"expires_dt": "20260903102555"')

# Replace price mock
content = re.sub(
    r'{"rt_cd": "0", "output": {"stck_prpr": "(\d+)", "acml_vol": "(\d+)"}}',
    r'{"return_code": 0, "cur_prc": "\1", "trde_qty": "\2", "open_pric": "\1", "high_pric": "\1", "low_pric": "\1", "pred_pre": "0", "flu_rt": "0.0"}',
    content
)

# Replace order mock
content = re.sub(
    r'{"rt_cd": "0", "msg1": "주문 전송이 완료되었습니다.", "output": {"ODNO": "(\d+)", "ORD_TMD": "\d+"}}',
    r'{"return_code": 0, "return_msg": "주문 접수", "ord_no": "\1"}',
    content
)

# Replace balance mock (empty)
content = re.sub(
    r'{"rt_cd": "0", "output1": \[\](.*?)"dnca_tot_amt": "(\d+)"(.*?)}',
    r'{"return_code": 0, "acnt_evlt_remn_indv_tot": [], "prsm_dpst_aset_amt": "\2", "tot_evlt_amt": "0", "tot_evlt_pl": "0"}',
    content, flags=re.DOTALL
)

# Replace balance mock (with position)
content = re.sub(
    r'{"rt_cd": "0", "output1": \[\{"pdno": "005930", "prdt_name": "삼성전자", "hld_qty": "(\d+)", "pchs_avg_pric": "(\d+)", "prpr": "(\d+)"\}\](.*?)"dnca_tot_amt": "(\d+)"(.*?)\]}',
    r'{"return_code": 0, "acnt_evlt_remn_indv_tot": [{"stk_cd": "005930", "stk_nm": "삼성전자", "hld_qty": "\1", "pchs_avg_uv": "\2", "cur_prc": "\3", "pchs_amt": str(int("\1")*int("\2")), "evlt_amt": str(int("\1")*int("\3")), "evlt_pl": "0", "prft_rt": "0.0"}], "prsm_dpst_aset_amt": "\5", "tot_evlt_amt": str(int("\1")*int("\3")), "tot_evlt_pl": "0"}',
    content, flags=re.DOTALL
)

# Fix test_business_rejection_rt_cd_nonzero
content = content.replace('"rt_cd": "1"', '"return_code": 3')

# Check TR IDs
content = content.replace("FHKST01010100", "ka10001")
content = content.replace("TTTC8434R", "kt00018")
content = content.replace("VTTC8434R", "kt00018")
content = content.replace("TTTC0802U", "kt10000")
content = content.replace("TTTC0801U", "kt10001")
content = content.replace("VTTC0802U", "kt10000")
content = content.replace("VTTC0801U", "kt10001")

with open("tests/test_phase3_api.py", "w", encoding="utf-8") as f:
    f.write(content)

