"""Open the Relations page invisibly and verify its principal blocks."""

from pathlib import Path
import os
import sys
import tkinter as tk
from tempfile import TemporaryDirectory
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
test_directory = TemporaryDirectory()
os.environ["OLNEY_PROFILE_DB"] = str(Path(test_directory.name) / "relations.db")
original_tk = tk.Tk


def hidden_tk(*args, **kwargs):
    root = original_tk(*args, **kwargs)
    root.withdraw()
    return root


def inspect_and_close(root, *args, **kwargs):
    app = sys.modules["app"]
    root.update_idletasks()
    base = {
        "last_name": "Test", "profile_type": "Humain", "birth_time": "12:00",
        "birth_place": "Paris, FR", "latitude": 48.8566, "longitude": 2.3522,
        "timezone": "Europe/Paris", "country_code": "FR", "notes": "",
    }
    first = app.profile_store.create_profile({
        **base, "name": "Alice", "birth_date": "1988-10-27",
    })
    second = app.profile_store.create_profile({
        **base, "name": "Bob", "birth_date": "1990-02-03",
    })
    relation = app.profile_store.create_relationship({
        "profile_a_id": first["id"], "profile_b_id": second["id"],
        "relationship_type": "Amitié", "title": "Alice et Bob",
        "notes": "Un vécu commun à conserver séparément.",
    })
    app._refresh_relationship_menu()
    assert app.relationship_menu.index("end") >= 4
    app.manage_relationships(relation["id"])
    root.update_idletasks()
    assert app.relationships_page is not None
    assert app.input_frame.winfo_manager() == ""

    texts = []
    def collect(widget):
        try:
            text = widget.cget("text")
        except tk.TclError:
            text = ""
        if text:
            texts.append(str(text))
        for child in widget.winfo_children():
            collect(child)
    collect(app.relationships_page)
    joined = "\n".join(texts)
    for expected in (
        "RELATIONS", "Alice et Bob", "CARTE DE LA RELATION",
        "ÉNERGIE DU LIEN", "RESSOURCE", "TENSION", "FORMES POSSIBLES",
        "CHEMIN DE VIE DE LA RELATION",
        "CORRESPONDANCES · ORDRE MANIFESTÉ", "CHEMIN DE VIE · ALICE TEST",
        "CHEMIN DE VIE · BOB TEST", "HORLOGES SYNCHRONISÉES",
    ):
        assert expected in joined, expected
    assert joined.index("CARTE DE LA RELATION") < joined.index(
        "CHEMIN DE VIE DE LA RELATION"
    )
    assert "ASSOCIÉE ·" not in joined
    assert "COMPATIBILITÉ" not in joined.upper()

    app.toggle_dark_mode()
    root.update_idletasks()
    app.relationships_page_return()
    assert app.relationships_page is None
    assert app.clock.winfo_manager() == "pack"
    root.destroy()


with patch("tkinter.Tk", side_effect=hidden_tk), patch(
    "tkinter.Tk.mainloop", new=inspect_and_close
):
    import app  # noqa: F401,E402
