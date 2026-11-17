"""Runtime and build metadata must follow the sole application version source."""
import ast
from pathlib import Path
import re
import subprocess

from version import APP_VERSION, WINDOWS_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_no_copied_application_versions():
    paths = subprocess.check_output(
        ["git", "ls-files", "--", "*.py"], cwd=ROOT, text=True
    ).splitlines()
    # Updater fixtures deliberately exercise older/newer releases, independently
    # of the installed application. Schema/corpus versions have their own lifecycle.
    independent = {"interpretation_runtime.py": {"0.5.0"},
                   "relationship_runtime.py": {"1.2.0"},
                   "tests/test_interpretation_contract.py": {"0.5.0", "0.7.4"},
                   "tests/test_relationships.py": {"1.2.0"}}
    for name in paths:
        if name in {"version.py", "tests/test_updates.py", "tests/test_version.py"}:
            continue
        for node in ast.walk(ast.parse((ROOT / name).read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                versions = re.findall(r"(?<![\d.])\d+\.\d+\.\d+(?![\d.])", node.value)
                assert set(versions) <= independent.get(name, set()), (name, node.lineno, versions)


def test_windows_metadata_uses_source_version():
    def record(kind):
        return lambda *args, **kwargs: (kind, args, kwargs)

    names = ("VSVersionInfo", "FixedFileInfo", "StringFileInfo", "StringTable",
             "StringStruct", "VarFileInfo", "VarStruct")
    metadata = eval((ROOT / "build_tools/windows_version_info.txt").read_text(encoding="utf-8"),
                    {name: record(name) for name in names})
    fixed = metadata[2]["ffi"][2]
    assert fixed["filevers"] == fixed["prodvers"] == WINDOWS_VERSION
    strings = metadata[2]["kids"][0][1][0][0][1][1]
    values = {item[1][0]: item[1][1] for item in strings}
    assert values["FileVersion"] == values["ProductVersion"] == APP_VERSION


def test_installer_reads_source_version():
    source = (ROOT / "build_tools/OlneyEngine.iss").read_text(encoding="utf-8")
    assert 'FileOpen(AddBackslash(SourcePath) + "..\\version.py")' in source
    assert "#define MyAppVersion StringChange(StringChange(FileRead(VersionSource), 'APP_VERSION = ', ''), '\"', '')" in source
    injected = (ROOT / "version.py").read_text(encoding="utf-8").splitlines()[0]
    injected = injected.replace("APP_VERSION = ", "").replace('"', "")
    assert injected == APP_VERSION
    assert "AppVersion={#MyAppVersion}" in source
    assert "VersionInfoVersion={#MyAppVersion}.0" in source
    assert "VersionInfoProductVersion={#MyAppVersion}" in source
    assert not re.search(r"\d+\.\d+\.\d+", source)
