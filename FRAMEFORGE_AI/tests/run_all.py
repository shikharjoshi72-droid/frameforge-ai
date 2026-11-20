"""Dependency-free test runner (pytest also works): python -m tests.run_all"""
import importlib
import sys
import traceback

MODS = ["test_chunking", "test_parser", "test_scheduler", "test_loader", "test_e2e"]
passed = failed = 0
for m in MODS:
    mod = importlib.import_module(f"tests.{m}")
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        try:
            getattr(mod, name)()
            passed += 1
            print(f"PASS {m}.{name}")
        except Exception:
            failed += 1
            print(f"FAIL {m}.{name}")
            traceback.print_exc()
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
