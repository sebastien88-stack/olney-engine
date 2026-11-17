"""Start the real UI with an isolated database; no user data or API calls."""
import os
import runpy
import sys
import tkinter as tk
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(ROOT))
    original_tk = tk.Tk

    def hidden_root(*args, **kwargs):
        root = original_tk(*args, **kwargs)
        root.withdraw()
        return root

    def startup_only(root, *_args, **_kwargs):
        root.update_idletasks()
        assert root.winfo_children(), "Application did not construct its widgets"
        root.destroy()

    with TemporaryDirectory() as directory:
        with patch.dict(os.environ, {"OLNEY_PROFILE_DB": str(Path(directory) / "demo.db"),
                                     "OPENAI_API_KEY": "", "OPENROUTER_API_KEY": ""}):
            with patch.object(tk, "Tk", hidden_root), patch.object(tk.Misc, "mainloop", startup_only):
                runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
    print("Isolated application startup passed.")


if __name__ == "__main__":
    main()
