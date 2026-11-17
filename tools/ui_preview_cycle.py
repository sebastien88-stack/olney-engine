"""Interactive visual check with a disposable DB; never loads real profiles."""

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys
import tkinter as tk


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
preview_directory = TemporaryDirectory(prefix="olney-cycle-preview-")
os.environ["OLNEY_PROFILE_DB"] = str(Path(preview_directory.name) / "profiles.db")
original_tk = tk.Tk
original_mainloop = tk.Misc.mainloop


def hidden_tk(*args, **kwargs):
    root = original_tk(*args, **kwargs)
    root.withdraw()
    return root


def preview(root, *args, **kwargs):
    app = sys.modules["app"]
    for entry, value in (
        (app.birth_entry, "27/10/1988"),
        (app.birth_time_entry, "07:51"),
        (app.birth_place_entry, "Longjumeau, FR"),
        (app.target_entry, "31/08/2026"),
        (app.target_time_entry, "12:00"),
    ):
        entry.delete(0, "end")
        entry.insert(0, value)
    app.analysis_place_var.set("Longjumeau, FR")
    app.target_date_manual_dirty = True
    app.calculate()
    title = "Cycle annuel"
    app.notebook.select(app.cycle_tab_widgets[title])
    app.cycle_tab_views[title]["selected"].set("cycle")
    app.cycle_tab_views[title]["show"]()
    root.title("Olney — aperçu Lecture du cycle · base temporaire")
    root.geometry("1400x1000+20+20")
    root.deiconify()
    root.after(600000, root.destroy)
    try:
        original_mainloop(root, *args, **kwargs)
    finally:
        preview_directory.cleanup()


tk.Tk = hidden_tk
tk.Misc.mainloop = preview
import app  # noqa: E402,F401
