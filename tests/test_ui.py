"""Critical real-Tk journeys, isolated per process and bounded in time."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.ui
@pytest.mark.parametrize("journey", ["startup", "cards", "conversation"])
def test_ui_journey(journey, tmp_path):
    environment = dict(os.environ, OLNEY_PROFILE_DB=str(tmp_path / "profiles.db"),
                       OPENAI_API_KEY="", OPENROUTER_API_KEY="", PYTHONUTF8="1")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), journey], cwd=ROOT,
        env=environment, capture_output=True, text=True, encoding="utf-8", timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"UI journey passed: {journey}" in result.stdout


def run_journey(journey):
    from datetime import timedelta
    import runpy
    import tkinter as tk
    from time import monotonic, sleep
    from unittest.mock import patch

    sys.path.insert(0, str(ROOT))
    original_tk = tk.Tk

    def hidden_root(*args, **kwargs):
        root = original_tk(*args, **kwargs)
        root.withdraw()
        return root

    def inspect(root, *_args, **_kwargs):
        app = sys._getframe(1).f_globals
        errors = []
        root.report_callback_exception = lambda *error: errors.append(error)
        app["messagebox"].showerror = lambda *error: errors.append(error)

        def settle():
            deadline = monotonic() + 30
            while True:
                root.update()
                assert not errors, errors
                if not app["ui_jobs"].busy():
                    break
                assert monotonic() < deadline, "UI calculation timed out"
                sleep(0.005)
            root.update_idletasks()

        try:
            settle()
            assert root.winfo_children()
            if journey == "cards":
                for name, value in (("birth_entry", "27/10/1988"),
                                    ("target_entry", "26/08/2026")):
                    entry = app[name]
                    entry.delete(0, "end")
                    entry.insert(0, value)
                app["calculate"]()
                settle()
                original = app["current_target_date"]
                app["navigate_clock"]("day", 1)
                settle()
                assert app["current_target_date"] == original + timedelta(days=1)
                assert app["current_interpretation_state"]["target_date"] == app["current_target_date"].isoformat()
                app["navigate_clock"]("day", -1)
                settle()
                assert app["current_target_date"] == original
            elif journey == "conversation":
                app["manage_chat"]()
                settle()
                page = app["chat_page"]
                assert page.winfo_exists()
                page.input.insert("1.0", "Bonjour Emmett")
                assert page.input.get("1.0", "end").strip() == "Bonjour Emmett"
                page.new_thread(preserve_subject=True)
                assert page.current_thread_id is None
                assert not page.waiting
                app["chat_page_return"]()
                settle()
                assert app["chat_page"] is None
                assert app["notebook"].winfo_manager() == "pack"
        finally:
            root.destroy()

    with patch.object(tk, "Tk", hidden_root), patch.object(tk.Misc, "mainloop", inspect):
        runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
    print(f"UI journey passed: {journey}")


if __name__ == "__main__":
    run_journey(sys.argv[1])
