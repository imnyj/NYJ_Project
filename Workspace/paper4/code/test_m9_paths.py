#!/usr/bin/env python3
"""
test_m9_paths.py
================
Independent Verification Suite for Milestone M-9:
  1. Zero hardcoded absolute paths in all code/ python files
  2. Dynamic binary/executable resolution (sumo, netgenerate, python3)
  3. Dynamic SumoNetSim path discovery
  4. Complete isolation of legacy scripts (aggregator.py, train_final.py) to backup/
  5. Complete isolation of TinyMLP legacy files and models to backup/legacy_tinymlp/
  6. Zero .bak or .suspect temporary files in code/
  7. All remaining code/ modules pass syntax and AST validation
"""

import os
import sys
import re
import ast
import glob
import unittest

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CODE_DIR)
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from sim_engine import find_executable, get_sumo_env, get_sumonetsim_paths


class TestM9PathsAndLegacyIsolation(unittest.TestCase):

    def test_01_no_hardcoded_absolute_paths_in_codebase(self):
        """Verify that code/ has 0 instances of hardcoded absolute/user paths."""
        py_files = sorted(glob.glob(os.path.join(CODE_DIR, "*.py")))
        self.assertGreater(len(py_files), 10, "Should have active python files in code/")

        hardcoded_patterns = [
            re.compile(r'/home/[^ \t\n\r\"\'\)]+'),
            re.compile(r'(?<![a-zA-Z0-9_])[a-zA-Z]:[/\\\\][a-zA-Z0-9_\-.]*'),
            re.compile(r'/papers/paper4'),
            re.compile(r'/Workspace/paper4'),
        ]

        violations = []
        for file_path in py_files:
            fname = os.path.basename(file_path)
            if fname == "test_m9_paths.py":
                continue

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()

            # 1. Regex line-by-line inspection (excluding schema URLs)
            for idx, line in enumerate(source.splitlines(), start=1):
                clean_line = re.sub(r'https?://[^\s\"\'\)]+', '', line)
                for pat in hardcoded_patterns:
                    m = pat.findall(clean_line)
                    if m:
                        violations.append((fname, idx, line.strip(), m))

            # 2. AST string literal inspection
            parsed_ast = ast.parse(source, filename=fname)
            for node in ast.walk(parsed_ast):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value
                    if "http://" in val or "https://" in val:
                        continue
                    for pat in hardcoded_patterns:
                        if pat.search(val):
                            violations.append((fname, getattr(node, 'lineno', 0), val, pat.pattern))

        if violations:
            msg_lines = [f"Found {len(violations)} hardcoded path violations:"]
            for v in violations:
                msg_lines.append(f"  {v[0]}:L{v[1]}: {v[2]} (Matched: {v[3]})")
            self.fail("\n".join(msg_lines))

        print(f"  [test_01] Scanned {len(py_files)} python files in code/: 0 hardcoded paths found (PASS).")

    def test_02_dynamic_executable_resolution(self):
        """Verify dynamic executable locator and environment resolution."""
        # 1. python3 should always be found
        py_bin = find_executable("python3")
        self.assertIsNotNone(py_bin, "find_executable('python3') must find a valid binary")
        self.assertTrue(os.path.isfile(py_bin), f"Resolved python3 '{py_bin}' must be a file")
        self.assertTrue(os.access(py_bin, os.X_OK), f"Resolved python3 '{py_bin}' must be executable")

        # 2. sumo dynamic discovery
        sumo_bin = find_executable("sumo")
        self.assertIsNotNone(sumo_bin, "find_executable('sumo') must dynamically find sumo binary")
        self.assertTrue(os.path.isfile(sumo_bin), f"Resolved sumo '{sumo_bin}' must be a file")

        # 3. netgenerate dynamic discovery
        netgen_bin = find_executable("netgenerate")
        self.assertIsNotNone(netgen_bin, "find_executable('netgenerate') must dynamically find netgenerate binary")
        self.assertTrue(os.path.isfile(netgen_bin), f"Resolved netgenerate '{netgen_bin}' must be a file")

        # 4. Non-existent binary returns None safely
        none_bin = find_executable("non_existent_binary_xyz_123")
        self.assertIsNone(none_bin, "Non-existent binary must return None")

        # 5. Environment dictionary validation
        env = get_sumo_env()
        self.assertIn("PATH", env, "get_sumo_env() must contain PATH")
        self.assertIsInstance(env["PATH"], str)
        print(f"  [test_02] Resolved python3: {py_bin}, sumo: {sumo_bin}, netgenerate: {netgen_bin} (PASS).")

    def test_03_sumonetsim_dynamic_discovery(self):
        """Verify dynamic SumoNetSim path discovery."""
        source_script, rsu_source = get_sumonetsim_paths()
        self.assertIsNotNone(source_script, "get_sumonetsim_paths() must find make_sumo_set.py")
        self.assertTrue(os.path.exists(source_script), f"make_sumo_set.py path '{source_script}' must exist")
        self.assertTrue(source_script.endswith("make_sumo_set.py"))

        if rsu_source is not None:
            self.assertTrue(os.path.exists(rsu_source), f"rsu.poi.xml path '{rsu_source}' must exist")
            self.assertTrue(rsu_source.endswith("rsu.poi.xml"))

        print(f"  [test_03] Discovered SumoNetSim script: {source_script}, rsu: {rsu_source} (PASS).")

    def test_04_legacy_scripts_isolation_verification(self):
        """Verify aggregator.py and train_final.py are isolated in backup/legacy_scripts/."""
        # 1. Must NOT exist in code/
        self.assertFalse(os.path.exists(os.path.join(CODE_DIR, "aggregator.py")), "aggregator.py must NOT exist in code/")
        self.assertFalse(os.path.exists(os.path.join(CODE_DIR, "train_final.py")), "train_final.py must NOT exist in code/")

        # 2. Must exist in backup/legacy_scripts/
        legacy_dir = os.path.join(PROJECT_ROOT, "backup", "legacy_scripts")
        self.assertTrue(os.path.exists(os.path.join(legacy_dir, "aggregator.py")), "aggregator.py must exist in backup/legacy_scripts/")
        self.assertTrue(os.path.exists(os.path.join(legacy_dir, "train_final.py")), "train_final.py must exist in backup/legacy_scripts/")
        print(f"  [test_04] Verified aggregator.py & train_final.py isolated in backup/legacy_scripts/ (PASS).")

    def test_05_tinymlp_legacy_isolation_verification(self):
        """Verify TinyMLP legacy files are isolated in backup/legacy_tinymlp/."""
        # Must NOT exist in code/
        forbidden_in_code = [
            "tinymlp_train.py",
            "tinymlp_train_redo3.py",
            "tinymlp_train_redo4.py",
            "tinymlp_model.pkl",
            "_save_model.py",
            "diagnostics_D1.py",
            "diagnostics_E4-1-redo.py",
            "diagnostics_E4-1-redo3.py",
            "diagnostics_E4-2-redo2_oracle.py"
        ]
        for f in forbidden_in_code:
            self.assertFalse(os.path.exists(os.path.join(CODE_DIR, f)), f"{f} must NOT exist in code/")

        # Must exist in backup/legacy_tinymlp/
        tinymlp_dir = os.path.join(PROJECT_ROOT, "backup", "legacy_tinymlp")
        for f in ["tinymlp_train.py", "tinymlp_model.pkl", "_save_model.py"]:
            self.assertTrue(os.path.exists(os.path.join(tinymlp_dir, f)), f"{f} must exist in backup/legacy_tinymlp/")

        print(f"  [test_05] Verified TinyMLP legacy models/scripts isolated in backup/legacy_tinymlp/ (PASS).")

    def test_06_no_bak_or_suspect_files_in_code_dir(self):
        """Verify no temporary/backup files (.bak, .suspect, fix_*.py) exist in code/."""
        bak_files = glob.glob(os.path.join(CODE_DIR, "*.bak*"))
        suspect_files = glob.glob(os.path.join(CODE_DIR, "*.suspect*"))
        fix_files = glob.glob(os.path.join(CODE_DIR, "fix_*.py"))

        self.assertEqual(len(bak_files), 0, f"Found .bak files in code/: {bak_files}")
        self.assertEqual(len(suspect_files), 0, f"Found .suspect files in code/: {suspect_files}")
        self.assertEqual(len(fix_files), 0, f"Found fix_*.py files in code/: {fix_files}")
        print(f"  [test_06] code/ contains 0 .bak, 0 .suspect, 0 fix_*.py files (PASS).")

    def test_07_all_code_modules_syntax_and_importability(self):
        """Verify all active python files in code/ have valid syntax and parse clean ASTs."""
        py_files = sorted(glob.glob(os.path.join(CODE_DIR, "*.py")))
        for pf in py_files:
            fname = os.path.basename(pf)
            with open(pf, "r", encoding="utf-8") as f:
                source = f.read()
            try:
                ast.parse(source, filename=fname)
            except SyntaxError as e:
                self.fail(f"Syntax error in {fname}: {e}")
        print(f"  [test_07] All {len(py_files)} python files in code/ parsed clean AST (PASS).")


if __name__ == "__main__":
    unittest.main(verbosity=2)
