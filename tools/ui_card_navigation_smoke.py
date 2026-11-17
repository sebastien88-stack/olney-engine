"""Verify natal portraits and every result-card link in an isolated Tk instance."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import os
import sys
import tkinter as tk

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
test_directory = TemporaryDirectory()
os.environ["OLNEY_PROFILE_DB"] = str(Path(test_directory.name) / "profiles.db")
original_tk = tk.Tk


def hidden_tk(*args, **kwargs):
    root = original_tk(*args, **kwargs)
    root.withdraw()
    return root


def inspect(root, *args, **kwargs):
    app = sys.modules["app"]
    errors = []
    app.messagebox.showerror = lambda title, message: errors.append((title, message))
    root.report_callback_exception = lambda kind, error, tb: errors.append((str(kind), str(error)))

    def idle():
        deadline = monotonic() + 30
        while True:
            root.update()
            assert not errors, errors
            if not app.ui_jobs.busy():
                break
            assert monotonic() < deadline, "Calculation timed out"
            sleep(0.003)
        root.update_idletasks()

    def enter(widget, value):
        widget.delete(0, "end")
        widget.insert(0, value)

    def show(title, mode):
        app.notebook.select(app.cycle_tab_widgets[title])
        metadata = app.cycle_tab_views[title]
        metadata["selected"].set(mode)
        metadata["show"]()
        idle()

    def texts(widget):
        result = []
        for child in widget.winfo_children():
            try:
                result.append(str(child.cget("text")))
            except tk.TclError:
                pass
            result.extend(texts(child))
        return result

    try:
        root.update_idletasks()
        assert app.reset_today_label.cget("text") == "Aujourd’hui"
        assert app.reset_today_label.winfo_rooty() + app.reset_today_label.winfo_height() <= app.calculate_button.winfo_rooty()
        for widget, value in ((app.birth_entry, "27/10/1988"), (app.birth_time_entry, "07:51"),
                              (app.birth_place_entry, "Longjumeau, FR"),
                              (app.target_entry, "26/08/2026"), (app.target_time_entry, "17:51")):
            enter(widget, value)
        app.calculate()
        idle()
        metadata = app.cycle_tab_views["Ordre naturel"]
        assert metadata["available"] == ("table", "birth", "secondary", "secondary_two")
        assert metadata["buttons"]["secondary_two"].winfo_manager() == "pack"
        for mode, view, label in (("birth", app.birth_portrait, "8♥"),
                                   ("secondary", app.secondary_portrait, "D♥"),
                                   ("secondary_two", app.second_secondary_portrait, "A♣")):
            show("Ordre naturel", mode)
            assert view.context["card"]["label"] == label
            profile = view.knowledge.profiles[view.context["card"]["id"]]
            visible = "\n".join(texts(view.content))
            for key in ("energy", "manifestations", "constructive", "difficult"):
                assert profile[key] in visible
            suit = view.knowledge.suits[view.context["card"]["suit"]]
            assert suit["element"] in visible
            for dark in (False, True):
                app.dark_mode = dark
                app.apply_theme()
                assert view.canvas.cget("background") == view._palette()["bg"]
                assert profile["energy"] in "\n".join(texts(view.content))
            view.canvas.yview_moveto(1)
            assert view.canvas.canvasy(0) > 0
        print("Natal portraits: primary + both Scorpio secondary cards, themes and scroll OK")

        show("Ordre naturel", "birth")
        render_count = app.birth_portrait.render_count
        app.navigate_clock("day", 1)
        idle()
        assert app.birth_portrait.render_count == render_count
        assert app.birth_portrait.context["card"]["label"] == "8♥"
        app.calculate(date(2026, 8, 26))
        idle()
        app.notebook.select(app.global_interpretation_tab)
        app.refresh_visible_view()
        idle()
        app.global_interpretation.birth_card_button.invoke()
        idle()
        assert app.notebook.select() == str(app.cycle_tab_widgets["Ordre naturel"])
        assert metadata["selected"].get() == "birth"
        assert "← Retour à la lecture globale" in texts(app.birth_portrait.content)
        app.birth_portrait._return_to_global()
        idle()
        assert app.notebook.select() == str(app.global_interpretation_tab)
        app.open_global_cycle("natal")  # The birth card inside the global clock follows the same link.
        idle()
        assert metadata["selected"].get() == "birth"
        print("Global birth-card link, return link and permanent portrait cache OK")

        reference_date, reference_time = app.current_target_date, app.target_time_entry.get()
        for title, results in (("Chemin de vie", app.manifested_results), ("Cycle 7 ans", app.seven_results),
                               ("Cycle annuel", app.year_results), ("Cycle semaine", app.week_results)):
            cid = app.CYCLE_READING_IDS[title]
            show(title, "result")
            slots = tuple(results.card_canvases)
            assert len(slots) == 11
            for slot in slots:
                app.calculate(reference_date)
                idle()
                show(title, "result")
                cycle = next(item for item in app.current_interpretation_context["cycles"] if item["id"] == cid)
                period = next((item for item in cycle["sequence_cards"] if item["sequence_planet"] == slot), None)
                expected_date = date.fromisoformat(period["period"]["start"]) if period else reference_date
                canvas = results.card_canvases[slot]
                assert canvas.cget("cursor") == "hand2"
                assert canvas.bind("<Return>") and canvas.bind("<space>")
                canvas.event_generate("<Button-1>", x=35, y=45)
                idle()
                assert app.cycle_tab_views[title]["selected"].get() == "cycle", (title, slot)
                view = app.cycle_reading_views[cid]
                if slot in ("lune", "soleil", "défi", "résultat"):
                    assert view.selected_role == slot and view.selected_index is None, (title, slot, view.selected_role, view.selected_index, app.pending_cycle_cards)
                    expected = view._support_card(slot)
                else:
                    step = view.context["cycle_reading"]["steps"][view.selected_index]
                    assert step["sequence_planet"] == slot
                    expected = step["card"]
                assert expected["label"] in view.detail_heading.cget("text")
                assert view.canvas.canvasy(0) >= view.detail_box.winfo_y() - 20
                assert app.current_target_date == expected_date, (title, slot, expected_date)
                assert app.current_interpretation_state["target_date"] == expected_date.isoformat()
                assert view.context["target_date"] == expected_date.isoformat()
                if period:
                    active = next(item for item in app.current_interpretation_context["cycles"] if item["id"] == cid)
                    assert active["active_card"]["label"] == period["label"]
                    assert view.selected_index == view.context["cycle_reading"]["current_step_index"]
                assert app.target_time_entry.get() == reference_time
                assert view.present["date"] == date.today().isoformat()
            app.dark_mode = False
            app.apply_theme()
            assert view.selected_role == "résultat"
            app.dark_mode = True
            app.apply_theme()
        print("All 44 result cards: dated steps synchronize the clock; four support roles preserve time")

        # No orphaned second-secondary tab when switching away from Scorpio.
        show("Ordre naturel", "secondary_two")
        enter(app.birth_entry, "03/02/1990")
        app.calculate()
        idle()
        assert metadata["available"] == ("table", "birth", "secondary")
        assert metadata["selected"].get() == "birth"
        assert metadata["buttons"]["secondary_two"].winfo_manager() == ""
        show("Ordre naturel", "secondary")
        assert app.secondary_portrait.context["card"]["ruler"] == "uranus"
        assert "Uranus" in "\n".join(texts(app.secondary_portrait.content))
        enter(app.birth_entry, "31/12/1990")
        app.calculate()
        idle()
        show("Ordre naturel", "birth")
        assert app.birth_portrait.context is None
        assert "Joker" in "\n".join(texts(app.birth_portrait.content))
        print("Single-secondary and Joker transitions OK")
    finally:
        root.destroy()
        test_directory.cleanup()


tk.Tk = hidden_tk
tk.Misc.mainloop = inspect
import app  # noqa: E402,F401
