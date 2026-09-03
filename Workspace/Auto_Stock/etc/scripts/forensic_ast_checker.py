#!/usr/bin/env python3
"""
Forensic AST static analysis for Milestone 3 HPO components.
"""
import ast
import os
import sys

TARGET_FILES = [
    "modules/hpo/metrics.py",
    "modules/hpo/optuna_pipeline.py",
    "modules/hpo/exporter.py",
    "scripts/run_hpo.py",
    "tests/test_hpo.py"
]

class ForensicASTVisitor(ast.NodeVisitor):
    def __init__(self, filepath):
        self.filepath = filepath
        self.violations = []
        self.functions_checked = []
        self.classes_checked = []

    def visit_FunctionDef(self, node):
        self.functions_checked.append(node.name)
        # Check if function body is just a pass or docstring + pass
        non_doc_body = [stmt for stmt in node.body if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Str, ast.Constant)))]
        
        if len(non_doc_body) == 0:
            self.violations.append(f"Function {node.name} at line {node.lineno} has an empty/docstring-only body.")
        elif len(non_doc_body) == 1:
            stmt = non_doc_body[0]
            if isinstance(stmt, ast.Pass):
                self.violations.append(f"Function {node.name} at line {node.lineno} is a dummy pass.")
            elif isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call) and getattr(stmt.exc.func, 'id', '') == 'NotImplementedError':
                self.violations.append(f"Function {node.name} at line {node.lineno} raises NotImplementedError.")
            elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                # Check if it's a suspicious constant return (unless it's a trivial helper)
                self.violations.append(f"Function {node.name} at line {node.lineno} returns constant literal: {stmt.value.value}")

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes_checked.append(node.name)
        self.generic_visit(node)

def run_ast_audit():
    print("=== [Forensic Audit] AST Static Code Analysis ===")
    all_clean = True
    for rel_path in TARGET_FILES:
        full_path = os.path.abspath(rel_path)
        if not os.path.exists(full_path):
            print(f"[-] Missing target file: {rel_path}")
            all_clean = False
            continue
        
        with open(full_path, "r", encoding="utf-8") as f:
            code = f.read()
        
        tree = ast.parse(code, filename=rel_path)
        visitor = ForensicASTVisitor(rel_path)
        visitor.visit(tree)
        
        print(f"\nFile: {rel_path}")
        print(f"  • Functions checked ({len(visitor.functions_checked)}): {', '.join(visitor.functions_checked)}")
        print(f"  • Classes checked ({len(visitor.classes_checked)}): {', '.join(visitor.classes_checked)}")
        
        if visitor.violations:
            print(f"  [!] Potential violations found ({len(visitor.violations)}):")
            for v in visitor.violations:
                print(f"      - {v}")
            # Analyze if violations are genuine dummy facades or standard defaults
            all_clean = False
        else:
            print("  [+] Clean: No dummy bodies or constant-return facades detected.")

    return all_clean

if __name__ == "__main__":
    success = run_ast_audit()
    sys.exit(0 if success else 1)
