"""Compile tracked project Python sources without executing them."""
import py_compile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = subprocess.check_output(["git", "ls-files", "-z", "--", "*.py"], cwd=ROOT)
    files = [ROOT / p for p in paths.decode().split("\0") if p]
    for path in files:
        py_compile.compile(str(path), doraise=True)
    print(f"Compiled {len(files)} tracked Python files.")


if __name__ == "__main__":
    main()
