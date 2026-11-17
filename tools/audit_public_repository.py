"""Report credential-like findings in tracked files and all local Git history.

Never print matched values. This heuristic is not a proof that no secret exists.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "openai_or_openrouter_key": re.compile(rb"\bsk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{24,}"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(rb"\bAKIA[A-Z0-9]{16}\b"),
    "literal_credential": re.compile(
        rb"(?i)(?:api_key|password|access_token)\s*[:=]\s*[\"'][^\"'\r\n]{16,}[\"']"
    ),
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    paths = git("ls-files", "-z").decode().split("\0")
    private_paths = [p for p in paths if p and (
        Path(p).suffix.lower() in {".db", ".sqlite", ".sqlite3", ".pem", ".key"}
        or (Path(p).name.startswith(".env") and Path(p).name != ".env.example")
    )]
    findings = []
    historical_private_paths = set()
    checked = set()
    objects = git("rev-list", "--objects", "--all").decode().splitlines()
    for entry in objects:
        oid, _, path = entry.partition(" ")
        if not path or oid in checked:
            continue
        if (Path(path).suffix.lower() in {".db", ".sqlite", ".sqlite3", ".pem", ".key"}
                or (Path(path).name.startswith(".env") and Path(path).name != ".env.example")):
            historical_private_paths.add(path)
        if git("cat-file", "-t", oid).strip() != b"blob":
            continue
        checked.add(oid)
        data = git("cat-file", "blob", oid)
        if b"\0" in data:
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append({"path": path, "blob": oid, "rule": name})
    # Include new/modified tracked working files, not only committed snapshots.
    for path in filter(None, paths):
        file = ROOT / path
        if file.is_file():
            data = file.read_bytes()
            if b"\0" not in data:
                for name, pattern in PATTERNS.items():
                    if pattern.search(data):
                        findings.append({"path": path, "scope": "working_tree", "rule": name})
    print(json.dumps({"tracked_files": len(list(filter(None, paths))),
                      "historical_blobs_scanned": len(checked),
                      "private_file_paths": private_paths,
                      "historical_private_file_paths": sorted(historical_private_paths),
                      "findings": findings}, indent=2))
    return int(bool(private_paths or historical_private_paths or findings))


if __name__ == "__main__":
    raise SystemExit(main())
