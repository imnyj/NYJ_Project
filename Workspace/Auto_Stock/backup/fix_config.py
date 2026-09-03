import re
with open("core/config.py", "r") as f:
    code = f.read()

# Replace base URLs
code = code.replace('"https://openapi.kiwoom.com"', '"https://api.kiwoom.com"')
code = code.replace('"https://openapivts.kiwoom.com"', '"https://mockapi.kiwoom.com"')

# Replace TR IDs
code = re.sub(r'return "FHKST01010100"', 'return "ka10001"', code)
code = re.sub(r'return "VTTC0802U" if is_buy else "VTTC0801U"', 'return "kt10000" if is_buy else "kt10001"', code)
code = re.sub(r'return "TTTC0802U" if is_buy else "TTTC0801U"', 'return "kt10000" if is_buy else "kt10001"', code)
code = re.sub(r'return "VTTC8434R" if self.use_mock_server else "TTTC8434R"', 'return "kt00018"', code)

with open("core/config.py", "w") as f:
    f.write(code)

