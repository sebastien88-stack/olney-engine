"""Exercise committed navigation history with a hidden Tk and an isolated DB."""
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic, sleep
from unittest.mock import patch
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

    def idle(allow_errors=False):
        deadline = monotonic() + 30
        while True:
            root.update()
            if not app.ui_jobs.busy():
                break
            assert monotonic() < deadline, "Calculation timed out"
            sleep(0.003)
        root.update_idletasks()
        if not allow_errors:
            assert not errors, errors

    def enter(widget, value):
        widget.delete(0, "end")
        widget.insert(0, value)

    def show(title, mode):
        app.notebook.select(app.cycle_tab_widgets[title])
        app.cycle_tab_views[title]["selected"].set(mode)
        app.cycle_tab_views[title]["show"]()
        idle()

    def assert_snapshot(snapshot):
        assert app.navigation_history.current == snapshot, (app.navigation_history.current, snapshot)
        assert app.current_target_date.isoformat() == snapshot["target_date"]
        assert app.current_interpretation_context["target_date"] == snapshot["target_date"]
        assert app.target_entry.get() == datetime.fromisoformat(snapshot["target_date"]).strftime("%d/%m/%Y")
        assert app.target_time_entry.get() == snapshot["target_time"]
        assert app.analysis_place_var.get() == snapshot["target_place"]
        assert app.analysis_place_linked == snapshot["place_linked"]
        assert app.analysis_time_linked == snapshot["time_linked"]
        assert app.visible_view_key() == (snapshot["title"], snapshot["mode"])
        assert app.active_profile_id == snapshot["profile_id"]

    try:
        root.update_idletasks()
        for widget, value in ((app.birth_entry, "27/10/1988"), (app.birth_time_entry, "07:51"),
                              (app.birth_place_entry, "Longjumeau, FR"),
                              (app.target_entry, "26/08/2026"), (app.target_time_entry, "23:51")):
            enter(widget, value)
        app.calculate()
        idle()
        show("Cycle annuel", "result")
        before = app.navigation_history.current
        cycle = next(item for item in app.current_interpretation_context["cycles"] if item["id"] == "annual")
        step = cycle["sequence_cards"][3]
        app.open_result_card("Cycle annuel", {"slot": step["sequence_planet"], "card": step["label"]})
        idle()
        after = app.navigation_history.current
        assert after["target_date"] == step["period"]["start"]
        assert after["mode"] == "cycle"
        count = len(app.navigation_history.entries)
        app.back_button.invoke()
        idle()
        assert_snapshot(before)
        app.forward_button.invoke()
        idle()
        assert_snapshot(after)
        assert len(app.navigation_history.entries) == count
        print("Result period → unified date/clock; Back/Forward restore date, time and view: OK")

        # Support roles are not dates; they are still distinct navigable readings.
        show("Cycle annuel", "result")
        before_support = app.navigation_history.current
        result = next(item for item in app.current_interpretation_context["cycles"] if item["id"] == "annual")["result"]
        app.open_result_card("Cycle annuel", {"slot": "résultat", "card": result["label"]})
        idle()
        support = app.navigation_history.current
        assert support["target_date"] == before_support["target_date"]
        assert support["role"] == "résultat"
        app.navigate_history(-1)
        idle()
        assert_snapshot(before_support)
        app.navigate_history(1)
        idle()
        assert_snapshot(support)
        assert app.year_cycle_reading.selected_role == "résultat"

        # A new branch removes the former forward path, including at midnight.
        app.navigate_history(-1)
        idle()
        app.navigate_clock("hour", 1)
        idle()
        assert app.target_time_entry.get() == "00:51"
        assert app.navigation_history.peek(1) is None
        branch = app.navigation_history.current
        assert branch["target_date"] == (date.fromisoformat(before_support["target_date"]) + timedelta(days=1)).isoformat()
        assert app.current_interpretation_state["hour_card"]["time_local"] == "00:51"
        print("Support inspection, branching and midnight/hour changes: OK")

        # Rejected requests are never recorded. Back recovers the last valid one.
        enter(app.target_time_entry, "bad-time")
        app.calculate()
        idle(allow_errors=True)
        assert errors
        errors.clear()
        assert app.navigation_history.current == branch
        app.back_button.invoke()
        idle()
        assert_snapshot(branch)

        # Superseded requests cannot contaminate session history.
        gate, started = Event(), Event()
        real_work = app.analysis_work.analysis
        def slow(*values):
            started.set()
            assert gate.wait(10)
            return real_work(*values)
        with patch.object(app.analysis_work, "analysis", slow):
            app.calculate(date(2030, 1, 10))
            deadline = monotonic() + 5
            while not started.is_set():
                root.update()
                assert monotonic() < deadline
                sleep(0.003)
            app.calculate(date(2030, 1, 12))
            assert str(app.back_button.cget("state")) == "disabled"
            gate.set()
            idle()
        assert not any(item["target_date"] == "2030-01-10" for item in app.navigation_history.entries)
        assert app.navigation_history.current["target_date"] == "2030-01-12"
        print("Invalid and superseded requests excluded from history: OK")

        profiles = [app.profile_store.create_profile({
            "name": name, "last_name": "Test", "birth_date": birth,
            "birth_time": "07:51", "birth_place": "Longjumeau, FR",
        }) for name, birth in (("Alice", "1988-10-27"), ("Bob", "1990-02-03"))]
        alice_memory = app.profile_store.add_memory(f"profile:{profiles[0]['id']}", {
            "kind": "observation", "text": "Retour propre à Alice", "perspective": "self"})
        bob_memory = app.profile_store.add_memory(f"profile:{profiles[1]['id']}", {
            "kind": "hypothesis", "text": "Hypothèse propre à Bob"})
        app.load_profile(profiles[0]["id"])
        idle()
        assert list(app.current_interpretation_context["personal"]["records"]) == [alice_memory["ref"]]
        show("Cycle annuel", "cycle")
        assert list(app.current_reading_material["records"])[0]["ref"] == alice_memory["ref"]
        show("Ordre naturel", "secondary_two")
        alice = app.navigation_history.current
        event = app.profile_store.create_event({
            "profile_id": profiles[1]["id"], "title": "Test histoire", "category": "Amour",
            "date_start": "2028-04-12", "event_time": "14:25", "place": "New York City, US",
        })
        app.open_saved_event(event["id"])
        idle()
        assert list(app.current_interpretation_context["personal"]["records"]) == [bob_memory["ref"]]
        assert f"event:{event['id']}" in app.current_interpretation_context["personal"]["events"]
        bob = app.navigation_history.current
        assert bob["profile_id"] == profiles[1]["id"] and bob["target_time"] == "14:25"
        app.navigate_history(-1)
        idle()
        assert_snapshot(alice)
        assert app.birth_entry.get() == "27/10/1988"
        assert app.cycle_tab_views["Ordre naturel"]["selected"].get() == "secondary_two"
        app.navigate_history(1)
        idle()
        assert_snapshot(bob)
        assert app.birth_entry.get() == "03/02/1990"
        app.manage_profiles()
        app.navigate_history(-1)
        idle()
        assert app.profiles_page is None
        assert_snapshot(alice)
        print("Cross-profile/event history, Scorpio's extra portrait and return from profiles: OK")

        app.reset_to_origin()
        idle()
        assert app.current_target_date == date.today()
        assert app.analysis_date_heading.get() == "DATE ANALYSÉE"
        assert app.analysis_group.cget("text").strip() == "ANALYSE (Aujourd’hui)"
        assert app.target_time_entry.get() == datetime.now().strftime("%H:%M")
        print("Reset → real current date/time and today label: OK")

        # The annotation belongs to the frame, not the field heading. Its three
        # values must not resize either theme or move any input/button.
        saved_date, saved_theme = app.current_target_date, app.dark_mode
        for dark in (True, False):
            app.dark_mode = dark
            app.apply_theme()
            geometries = []
            for offset, label in ((-1, "Passé"), (0, "Aujourd’hui"), (1, "Futur")):
                app.current_target_date = date.today() + timedelta(days=offset)
                app.refresh_temporal_label()
                root.update_idletasks()
                assert app.analysis_group.cget("text").strip() == f"ANALYSE ({label})"
                assert app.analysis_date_heading.get() == "DATE ANALYSÉE"
                geometries.append((app.input_frame.winfo_reqwidth(), app.analysis_group.winfo_reqwidth(),
                    root.geometry(), tuple((w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height())
                    for w in (app.target_entry, app.target_time_entry, app.calculate_button))))
            assert len(set(geometries)) == 1, geometries
        app.current_target_date, app.dark_mode = saved_date, saved_theme
        app.refresh_temporal_label()
        app.apply_theme()
        idle()
        print("ANALYSE title: Past/Today/Future have identical geometry in dark and light themes: OK")

        # Historical data never rewrites a profile that was edited meanwhile.
        old_alice = app.navigation_history.current
        app.load_profile(profiles[1]["id"])
        idle()
        revised = dict(profiles[0], birth_date="1988-10-28")
        app.profile_store.update_profile(profiles[0]["id"], revised)
        app.navigate_history(-1)
        idle()
        assert app.active_profile_id is None
        assert app.birth_entry.get() == "27/10/1988"
        assert app.current_target_date.isoformat() == old_alice["target_date"]
        assert app.profile_store.get_profile(profiles[0]["id"])["birth_date"] == "1988-10-28"
        app.load_profile(profiles[1]["id"])
        idle()
        app.navigate_clock("day", 1)
        idle()
        app.profile_store.delete_profile(profiles[1]["id"])
        app.navigate_history(-1)
        idle()
        assert app.active_profile_id is None and app.birth_entry.get() == "03/02/1990"
        assert app.profile_store.get_profile(profiles[1]["id"]) is None
        print("Edited/deleted profiles: old analysis restored without modifying saved data: OK")
    finally:
        if "gate" in locals():
            gate.set()
        root.destroy()
        test_directory.cleanup()


tk.Tk = hidden_tk
tk.Misc.mainloop = inspect
import app  # noqa: E402,F401
