"""
etc/scripts/forensic_auditor_scan.py
===================================
Forensic Auditor Static Analysis & Facade Detection Suite
Checks:
1. Hardcoded secrets / accounts / tokens across all source & config files (AST + Regex)
2. Facade / Dummy / Cheating functions (AST analysis for constant returns, pass-only bodies)
3. Test assertion strength & tautological assertion scan across tests/
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

PROJECT_ROOT = Path("/home/imnyj/Workspace/Auto_Stock")

def scan_for_secrets() -> List[Dict[str, Any]]:
    findings = []
    
    # Target directories
    target_dirs = ["core", "modules", "config", "tests"]
    
    # 32+ char alphanumeric string literal pattern
    raw_key_pattern = re.compile(r"['\"]([a-zA-Z0-9_\-]{32,})['\"]")
    # Account pattern: 8 digits - 2 digits (or 8~10 consecutive digits)
    account_pattern = re.compile(r"\b(\d{8}-\d{2})\b")
    # Potential password / secret assignment pattern
    secret_assign_pattern = re.compile(r"(?i)(app_?key|app_?secret|api_?key|api_?secret|account_?no|password|token)\s*=\s*['\"]([^'\"]+)['\"]")
    
    allowed_values = {
        "mock_test_app_key_12345",
        "mock_test_app_secret_67890",
        "mock_bearer_token_abc123",
        "mock_token",
        "renewed_token",
        "new_refreshed_token",
        "token_init",
        "token_refreshed",
        "valid_token",
        "old_expired_token",
        "expired_token",
        "test_app_key_12345",
        "test_app_secret_67890",
        "env_override_key_999",
        "env_override_secret_888",
        "your_app_key_here",
        "your_app_secret_here",
        "${KIWOOM_APP_KEY:}",
        "${KIWOOM_APP_SECRET:}",
        "${KIWOOM_ACCOUNT_NO:}",
        "${KIWOOM_ACCOUNT_PRODUCT_CODE:01}",
        "12345678-01",
        "00000000-01",
        "8765432102",
        "11223344",
        "https://openapi.kiwoom.com",
        "https://openapivts.kiwoom.com",
        "01",
        "00",
        "02",
        "P",
        "N",
        "J",
        "FHKST01010100",
        "VTTC0802U",
        "VTTC0801U",
        "TTTC0802U",
        "TTTC0801U",
        "VTTC8434R",
        "TTTC8434R",
        "AutoStockTrader",
        "1.0.0",
        "INFO",
        "MARKET",
        "LIMIT",
        "BUY",
        "SELL",
        "005930",
        "000660",
        "005380",
    }

    for t_dir in target_dirs:
        dir_path = PROJECT_ROOT / t_dir
        if not dir_path.exists():
            continue
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith((".py", ".yaml", ".yml", ".json", ".env")):
                    fpath = Path(root) / file
                    try:
                        content = fpath.read_text(encoding="utf-8")
                    except Exception as e:
                        findings.append({"file": str(fpath), "type": "READ_ERROR", "detail": str(e)})
                        continue
                    
                    lines = content.splitlines()
                    for lno, line in enumerate(lines, 1):
                        # Regex checks
                        for m in secret_assign_pattern.finditer(line):
                            var_name, val = m.group(1), m.group(2)
                            if val not in allowed_values and not val.startswith("${") and val != "":
                                findings.append({
                                    "file": str(fpath),
                                    "line": lno,
                                    "type": "SUSPICIOUS_SECRET_ASSIGNMENT",
                                    "detail": f"{var_name} = '{val[:4]}***{val[-2:] if len(val)>=6 else ''}'",
                                    "line_content": line.strip()
                                })
                        
                        for m in raw_key_pattern.finditer(line):
                            val = m.group(1)
                            if val not in allowed_values and "openapi" not in val and not val.startswith("test_") and not val.startswith("mock_"):
                                findings.append({
                                    "file": str(fpath),
                                    "line": lno,
                                    "type": "LONG_HEX_STRING_LITERAL",
                                    "detail": f"Length {len(val)}: '{val[:6]}***'",
                                    "line_content": line.strip()
                                })

                        for m in account_pattern.finditer(line):
                            val = m.group(1)
                            if val not in allowed_values:
                                findings.append({
                                    "file": str(fpath),
                                    "line": lno,
                                    "type": "ACCOUNT_NO_PATTERN",
                                    "detail": f"Account '{val}'",
                                    "line_content": line.strip()
                                })
    return findings


def scan_for_facades_and_dummies() -> List[Dict[str, Any]]:
    findings = []
    target_files = [
        PROJECT_ROOT / "core" / "config.py",
        PROJECT_ROOT / "core" / "kiwoom_api.py",
        PROJECT_ROOT / "modules" / "engine" / "manual_trader.py",
    ]

    for fpath in target_files:
        if not fpath.exists():
            findings.append({"file": str(fpath), "type": "MISSING_FILE", "detail": "Target file does not exist"})
            continue
        try:
            tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        except Exception as e:
            findings.append({"file": str(fpath), "type": "PARSE_ERROR", "detail": str(e)})
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for empty body / only pass / only return constant (excluding getters/properties/simple duffers)
                body = [stmt for stmt in node.body if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant)] # skip docstrings
                if not body:
                    findings.append({
                        "file": str(fpath),
                        "line": node.lineno,
                        "name": node.name,
                        "type": "EMPTY_FUNCTION_BODY",
                        "detail": f"Function {node.name} has empty body"
                    })
                elif len(body) == 1:
                    stmt = body[0]
                    if isinstance(stmt, ast.Pass):
                        findings.append({
                            "file": str(fpath),
                            "line": node.lineno,
                            "name": node.name,
                            "type": "PASS_ONLY_BODY",
                            "detail": f"Function {node.name} contains only pass"
                        })
                    elif isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Name) and stmt.exc.id == "NotImplementedError":
                        findings.append({
                            "file": str(fpath),
                            "line": node.lineno,
                            "name": node.name,
                            "type": "NOT_IMPLEMENTED_STUB",
                            "detail": f"Function {node.name} raises NotImplementedError"
                        })
                    elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                        # Filter out normal trivial methods like __str__, __len__, etc. or is_mock property
                        if node.name not in ("__str__", "__repr__", "__len__", "__bool__", "__hash__", "to_dict"):
                            # Check if it's a real business logic function
                            if node.name in ("get_current_price", "send_order", "get_account_balance", "refresh_token", "execute_order", "validate_inputs"):
                                findings.append({
                                    "file": str(fpath),
                                    "line": node.lineno,
                                    "name": node.name,
                                    "type": "CONSTANT_RETURN_FACADE",
                                    "detail": f"Critical function {node.name} returns hardcoded constant: {stmt.value.value}"
                                })

    return findings


def scan_test_assertion_strength() -> Dict[str, Any]:
    test_file = PROJECT_ROOT / "tests" / "test_phase3_api.py"
    if not test_file.exists():
        return {"error": "test_phase3_api.py not found"}

    tree = ast.parse(test_file.read_text(encoding="utf-8"))
    
    test_functions = []
    tautological_asserts = []
    total_asserts = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            func_asserts = 0
            for child in ast.walk(node):
                if isinstance(child, ast.Assert):
                    func_asserts += 1
                    total_asserts += 1
                    # Check if assert test is literal True or constant
                    if isinstance(child.test, ast.Constant) and child.test.value is True:
                        tautological_asserts.append({
                            "func": node.name,
                            "line": child.lineno,
                            "detail": "assert True"
                        })
            test_functions.append({
                "name": node.name,
                "line": node.lineno,
                "assert_count": func_asserts
            })

    return {
        "total_test_functions": len(test_functions),
        "total_assertions": total_asserts,
        "avg_assertions_per_test": round(total_asserts / max(1, len(test_functions)), 2),
        "tautological_assertions": tautological_asserts,
        "zero_assert_tests": [tf for tf in test_functions if tf["assert_count"] == 0],
    }


if __name__ == "__main__":
    print("=== 1. SECRET SCAN FINDINGS ===")
    secrets = scan_for_secrets()
    print(f"Total suspicious items found: {len(secrets)}")
    for s in secrets:
        print(s)

    print("\n=== 2. FACADE / DUMMY FINDINGS ===")
    facades = scan_for_facades_and_dummies()
    print(f"Total facade items found: {len(facades)}")
    for f in facades:
        print(f)

    print("\n=== 3. TEST ASSERTION STRENGTH ANALYSIS ===")
    test_analysis = scan_test_assertion_strength()
    print(f"Total test functions: {test_analysis.get('total_test_functions')}")
    print(f"Total assertions: {test_analysis.get('total_assertions')}")
    print(f"Avg assertions / test: {test_analysis.get('avg_assertions_per_test')}")
    print(f"Tautological assertions: {test_analysis.get('tautological_assertions')}")
    print(f"Tests with 0 assertions: {test_analysis.get('zero_assert_tests')}")
