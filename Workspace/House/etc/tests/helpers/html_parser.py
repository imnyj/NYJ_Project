"""
BeautifulSoup HTML & JS Parser Helper for E2E Tests.
Parses ui/index4.html and verifies DOM IDs, Chart.js scripts, and Dark Mode components.
"""

import os
from bs4 import BeautifulSoup

def parse_html_simulator(html_path: str = "/home/imnyj/Workspace/House/ui/index4.html") -> dict:
    """
    Parses ui/index4.html static DOM structure.
    Checks required input sliders, output metric cards, Chart.js integration, and Glassmorphism styling.
    """
    if not os.path.exists(html_path):
        return {
            "exists": False,
            "file_path": html_path,
            "dom_ids": {},
            "all_required_ids_present": False,
            "chart_js_found": False,
            "dark_mode_found": False,
            "glassmorphism_found": False,
            "raw_soup": None,
            "html_content": ""
        }

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    required_ids = [
        "price-slider",
        "cash-slider",
        "rate-slider",
        "term-slider",
        "total-initial-cost",
        "monthly-spending",
        "remaining-income",
        "payoff-timeline"
    ]

    dom_id_status = {}
    for elem_id in required_ids:
        elem = soup.find(id=elem_id)
        if elem is None:
            elem = soup.find(id=lambda x: x and elem_id.replace("-", "") in x.replace("-", "").replace("_", ""))
        dom_id_status[elem_id] = (elem is not None)

    script_tags = soup.find_all("script")
    chart_js_found = False
    for script in script_tags:
        src = script.get("src", "")
        text = script.string or ""
        if "chart" in src.lower() or "chart" in text.lower() or "chart.js" in text.lower():
            chart_js_found = True
            break

    dark_mode_found = False
    if "dark" in html_content.lower() or "theme" in html_content.lower():
        dark_mode_found = True

    glassmorphism_found = False
    if "glass" in html_content.lower() or "backdrop-filter" in html_content.lower() or "rgba" in html_content.lower():
        glassmorphism_found = True

    return {
        "exists": True,
        "file_path": html_path,
        "dom_ids": dom_id_status,
        "all_required_ids_present": all(dom_id_status.values()),
        "chart_js_found": chart_js_found,
        "dark_mode_found": dark_mode_found,
        "glassmorphism_found": glassmorphism_found,
        "raw_soup": soup,
        "html_content": html_content
    }
