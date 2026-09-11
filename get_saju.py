import datetime

# Julian day for 1900-01-01 is 2415020.5
# 1900-01-01 was 甲戌(Gap-Sul, 11th Ganji) day.
def get_ganji_day(y, m, d):
    dt = datetime.date(y, m, d)
    ref_dt = datetime.date(1900, 1, 1)
    diff = (dt - ref_dt).days
    ganji_idx = (10 + diff) % 60
    
    # 10 heavenly stems
    stems = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    # 12 earthly branches
    branches = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    
    stem = stems[ganji_idx % 10]
    branch = branches[ganji_idx % 12]
    return f"{stem}{branch}"

print(f"1992-04-28: {get_ganji_day(1992, 4, 28)}")
print(f"1995-06-07: {get_ganji_day(1995, 6, 7)}")
print(f"2026-04-22: {get_ganji_day(2026, 4, 22)}")
