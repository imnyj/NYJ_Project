"""
Empirical Harness 2 & 3: Adversarial Testing on Static Parsers
Tests html_parser.py and report_parser.py against malformed inputs, missing elements, false positives, etc.
"""

import os
import sys
import tempfile
import pytest

# Add helpers to sys.path
sys.path.insert(0, "/home/imnyj/Workspace/House/etc/tests")

from helpers.html_parser import parse_html_simulator
from helpers.report_parser import parse_budget_reference, parse_report_markdown

def test_html_parser_missing_dom_elements():
    """Verify html_parser with missing DOM elements."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write("<html><body><div id='price-slider'></div></body></html>")
        tmp_path = f.name

    try:
        parsed = parse_html_simulator(tmp_path)
        print("=== Test 2A: HTML Parser Missing DOM Elements ===")
        print(f"exists: {parsed['exists']}")
        print(f"dom_ids: {parsed['dom_ids']}")
        print(f"all_required_ids_present: {parsed['all_required_ids_present']}")
        assert parsed['exists'] is True
        assert parsed['dom_ids']['price-slider'] is True
        assert parsed['dom_ids']['cash-slider'] is False
        assert parsed['all_required_ids_present'] is False
    finally:
        os.remove(tmp_path)


def test_html_parser_false_positive_ids():
    """Verify html_parser false positives with partial container IDs."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        # Notice id='price-slider-wrapper-div' instead of 'price-slider'
        f.write("<html><body><div id='price-slider-wrapper-div'></div></body></html>")
        tmp_path = f.name

    try:
        parsed = parse_html_simulator(tmp_path)
        print("=== Test 2B: HTML Parser False Positive IDs ===")
        print(f"dom_ids for price-slider: {parsed['dom_ids']['price-slider']}")
        # The parser's lambda `elem_id.replace('-', '') in x.replace('-', '').replace('_', '')`
        # causes 'priceslider' in 'pricesliderwrapperdiv' -> True!
        print("Parser returned TRUE for wrapper div due to substring match!")
    finally:
        os.remove(tmp_path)


def test_html_parser_script_string_none():
    """Verify html_parser when script tag contains comments/children making script.string None."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write("<html><body><script><!-- inline Chart.js code --> console.log('chart');</script></body></html>")
        tmp_path = f.name

    try:
        parsed = parse_html_simulator(tmp_path)
        print("=== Test 2C: HTML Parser script.string None ===")
        print(f"chart_js_found: {parsed['chart_js_found']}")
    finally:
        os.remove(tmp_path)


def test_html_parser_fake_dark_and_glass():
    """Verify html_parser false positives on CSS comments / unrelated text."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        # File has comment saying 'dark mode not supported' and background color rgba
        f.write("<!-- dark mode is not supported --> <style> body { color: rgba(0,0,0,1); } </style>")
        tmp_path = f.name

    try:
        parsed = parse_html_simulator(tmp_path)
        print("=== Test 2D: HTML Parser Fake Dark and Glass ===")
        print(f"dark_mode_found: {parsed['dark_mode_found']}")
        print(f"glassmorphism_found: {parsed['glassmorphism_found']}")
    finally:
        os.remove(tmp_path)


def test_html_parser_encoding_error():
    """Verify html_parser behavior on non-UTF8 / binary files."""
    with tempfile.NamedTemporaryFile("wb", suffix=".html", delete=False) as f:
        f.write(b"\x80\x81\xff\xfe\xfa")
        tmp_path = f.name

    try:
        print("=== Test 2E: HTML Parser Binary / Non-UTF8 File ===")
        try:
            parsed = parse_html_simulator(tmp_path)
            print(f"Parsed successfully? {parsed}")
        except Exception as e:
            print(f"Caught Exception: {type(e).__name__}: {e}")
    finally:
        os.remove(tmp_path)


def test_report_parser_budget_hardcoded_stub():
    """Verify parse_budget_reference when markdown file has rows deleted or modified."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        # Completely empty file or completely different file
        f.write("# Dummy Budget\nNo tables here!\n")
        tmp_path = f.name

    try:
        parsed = parse_budget_reference(tmp_path)
        print("=== Test 3A: Budget Parser Hardcoded Stub ===")
        print(f"total_living_expenses: {parsed['total_living_expenses']}")
        print(f"categories_count: {parsed['categories_count']}")
        print("Notice: Even though markdown file is empty, total_living_expenses=2390708 and categories_count=13!")
    finally:
        os.remove(tmp_path)


def test_report_parser_markdown_keyword_only():
    """Verify parse_report_markdown when report contains keywords only in headers without actual scenarios/tables."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# 3.5억 3.75억 4.0억 잔금 등기 취득세 전입신고 확정일자 재산세\n")
        tmp_path = f.name

    try:
        parsed = parse_report_markdown(tmp_path)
        print("=== Test 3B: Report Parser Keyword Only ===")
        print(f"has_scenarios: {parsed['has_scenarios']}")
        print(f"checklist_complete: {parsed['checklist_complete']}")
    finally:
        os.remove(tmp_path)


if __name__ == "__main__":
    test_html_parser_missing_dom_elements()
    test_html_parser_false_positive_ids()
    test_html_parser_script_string_none()
    test_html_parser_fake_dark_and_glass()
    test_html_parser_encoding_error()
    test_report_parser_budget_hardcoded_stub()
    test_report_parser_markdown_keyword_only()
