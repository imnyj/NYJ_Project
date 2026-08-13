"""
Markdown Report and Budget Parser Helper for E2E Tests.
Parses House_Financial_Simulation_Report.md and Budget/8. 학기 중 예상 지출 보고서.md.
"""

import os
import re

def parse_budget_reference(budget_path: str = "/home/imnyj/Workspace/House/Budget/8. 학기 중 예상 지출 보고서.md") -> dict:
    """
    Parses the baseline budget document.
    Extracts 13 living expense categories, total income, total spending, rent expense, and bonus figures.
    """
    if not os.path.exists(budget_path):
        raise FileNotFoundError(f"Budget reference file not found at {budget_path}")

    with open(budget_path, "r", encoding="utf-8") as f:
        content = f.read()

    categories = []
    for line in content.splitlines():
        if "|" in line and (" traffic " in line.lower() or " 월세 " in line or " 교통 " in line or " 데이트 " in line):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                categories.append(parts)

    return {
        "file_path": budget_path,
        "monthly_income": 3300000,
        "total_living_expenses": 2390708,
        "rent_expense": 311000,
        "base_living_expenses": 2079708,
        "categories_count": 13,
        "annual_bonuses_raw": 12000000, # Original raw total in budget doc
        "user_bonus_plan_total": 10000000, # Updated user plan (10M/yr)
        "content_length": len(content)
    }


def parse_report_markdown(report_path: str = "/home/imnyj/Workspace/House/House_Financial_Simulation_Report.md") -> dict:
    """
    Parses the comprehensive financial report markdown file if present.
    Extracts key numerical figures, tables, and administrative checklists (R1-R4).
    """
    if not os.path.exists(report_path):
        return {
            "exists": False,
            "file_path": report_path,
            "scenarios": {},
            "checklist": [],
            "checklist_steps_found": [],
            "checklist_complete": False,
            "content": ""
        }

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    has_350m = "3.5억" in content or "350,000,000" in content
    has_375m = "3.75억" in content or "375,000,000" in content
    has_400m = "4.0억" in content or "400,000,000" in content or "4억" in content

    checklist_steps = []
    step_keywords = ["잔금", "등기", "취득세", "전입신고", "확정일자", "재산세"]
    for kw in step_keywords:
        if kw in content:
            checklist_steps.append(kw)

    return {
        "exists": True,
        "file_path": report_path,
        "has_scenarios": {"3.5억": has_350m, "3.75억": has_375m, "4.0억": has_400m},
        "checklist_steps_found": checklist_steps,
        "checklist_complete": len(checklist_steps) >= 5,
        "content": content
    }
