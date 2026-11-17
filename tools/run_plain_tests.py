"""Run Olney's zero-argument assertion tests without requiring pytest."""

from __future__ import annotations

from pathlib import Path
import inspect
import runpy
import sys
import traceback


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def main() -> int:
    passed = 0
    failed = 0
    for path in sorted((PROJECT_DIR / "tests").glob("test_*.py")):
        namespace = runpy.run_path(str(path))
        tests = [
            (name, value)
            for name, value in namespace.items()
            if name.startswith("test_")
            and callable(value)
            and not inspect.signature(value).parameters
        ]
        for name, test in sorted(tests):
            try:
                test()
                passed += 1
            except Exception:
                failed += 1
                print(f"FAILED {path.name}::{name}")
                traceback.print_exc()
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
