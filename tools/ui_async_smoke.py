"""Exercise actual Tk responsiveness with an isolated temporary profile database."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, get_ident
from time import monotonic, sleep
from unittest.mock import patch
from datetime import date, datetime, timedelta
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

    def pump(until=None, duration=0, timeout=45):
        started = monotonic()
        while True:
            root.update()
            assert monotonic() - started < timeout, "UI job timed out"
            if until is not None and until():
                return
            if until is None and monotonic() - started >= duration:
                return
            sleep(0.003)

    def idle():
        pump(until=lambda: not app.ui_jobs.busy())
        assert not errors, errors

    def set_entry(widget, value):
        widget.delete(0, "end")
        widget.insert(0, value)

    def open_view(title, mode=None):
        if title in app.cycle_tab_views:
            app.notebook.select(app.cycle_tab_widgets[title])
            app.cycle_tab_views[title]["selected"].set(mode)
            app.cycle_tab_views[title]["show"]()
        else:
            app.notebook.select(app.timeline_tab if title == "Frise chronologique" else app.global_interpretation_tab)
        app.refresh_visible_view()
        idle()

    try:
        root.update_idletasks()
        for widget, value in ((app.birth_entry, "27/10/1988"), (app.birth_time_entry, "07:51"),
                              (app.birth_place_entry, "Longjumeau, FR"),
                              (app.target_entry, "26/08/2026"), (app.target_time_entry, "23:51")):
            set_entry(widget, value)
        app.calculate()
        idle()
        assert app.current_interpretation_context["target_date"] == "2026-08-26"
        assert app.global_interpretation.render_count == 0
        assert all(v.render_count == 0 for v in app.cycle_reading_views.values())
        assert not app.timeline_view.periods
        old_hour = app.hour_card_var.get()
        gate, started = Event(), Event()
        real_work = app.analysis_work.analysis
        workers = []

        def slow(*values):
            workers.append(get_ident())
            started.set()
            assert gate.wait(10)
            return real_work(*values)

        with patch.object(app.analysis_work, "analysis", slow):
            before = monotonic()
            app.navigate_clock("hour", 1)
            assert monotonic() - before < 0.2
            pump(until=started.is_set)
            heartbeat = []
            root.after(30, lambda: heartbeat.append(True))
            pump(duration=0.3)
            assert heartbeat and "Mise à jour" in app.clock_busy_label.cget("text")
            frame = app.clock_busy_label.cget("text")
            pump(duration=0.12)
            assert app.clock_busy_label.cget("text") != frame
            assert app.hour_card_var.get() == old_hour  # Old frame remains intact.
            app.navigate_clock("hour", 1)
            app.navigate_clock("hour", 1)
            assert app.target_entry.get() == "27/08/2026"
            assert app.target_time_entry.get() == "02:51"
            app.toggle_dark_mode()
            gate.set()
            idle()
        assert all(worker != get_ident() for worker in workers)
        assert app.current_interpretation_context["target_date"] == "2026-08-27"
        assert app.current_interpretation_state["hour_card"]["time_local"] == "02:51"
        assert app.clock_busy_label.cget("text") == ""
        assert app.global_interpretation.render_count == 0
        print("UI responsive, animation and latest-request-wins: OK")

        open_view("Cycle annuel", "result")
        assert app.year_results.canvas.cget("background").upper() == "#DCE8F2"
        app.toggle_dark_mode()
        set_entry(app.target_time_entry, "03:51")
        app.calculate()
        idle()
        assert app.year_results.canvas.cget("background").upper() == "#101922"
        assert app.year_results.content.cget("background").upper() == "#101922"
        open_view("Lecture globale")
        assert app.global_interpretation.context["target_date"] == "2026-08-27"
        assert app.global_interpretation.canvas.cget("background") == app.global_interpretation._palette()["bg"]
        open_view("Cycle annuel", "cycle")
        assert app.year_cycle_reading.context["cycle_reading"]
        print("Lazy views, result theme and cycle reading: OK")

        open_view("Frise chronologique")
        assert app.timeline_view.periods and not app.timeline_view._loading
        # Navigate/zoom while a previous period request is still running.
        gate, started = Event(), Event()
        real_periods = app.analysis_work.periods
        def slow_periods(*values):
            started.set()
            assert gate.wait(10)
            return real_periods(*values)
        with patch.object(app.analysis_work, "periods", slow_periods):
            app.timeline_view._zoom(1)
            pump(until=started.is_set)
            app.timeline_view._zoom(1)
            app.timeline_view._shift(1)
            app.timeline_view._shift(1)
            wanted = app.target_entry.get()
            gate.set()
            idle()
        assert app.timeline_view.selected_date == app.parse_date(wanted)
        assert app.current_interpretation_context["target_date"] == app.parse_date(wanted).isoformat()
        assert not app.timeline_view._loading

        class FixedNow(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2031, 3, 3, 0, 4)

        app.analysis_place_linked = False
        app.analysis_place_var.set("New York City, US")
        with patch.object(app, "datetime", FixedNow):
            app.reset_to_origin()
        idle()
        assert app.current_target_date == date(2031, 3, 3)
        assert app.target_time_entry.get() == "00:04"
        assert app.birth_time_entry.get() == "07:51"
        assert app.analysis_place_var.get() == "New York City, US"
        assert app.timeline_view.selected_moment == datetime(2031, 3, 3, 0, 4)
        assert not hasattr(app, "saved_target_date")
        print("Timeline/clock synchronization and Reset to now: OK")

        # An invalid new request cancels the old one without replacing the display.
        context_before_error = app.current_interpretation_context
        set_entry(app.target_time_entry, "bad-time")
        app.calculate()
        pump(until=lambda: not app.ui_jobs.busy())
        assert errors and app.current_interpretation_context is context_before_error
        errors.clear()
        set_entry(app.target_time_entry, "12:00")
        app.calculate()
        idle()
        assert app.current_interpretation_state["hour_card"]["time_local"] == "12:00"
        print("Error recovery: OK")

        # Two different profiles and an event selected before either calculation
        # has finished must end on the event's owner, date and local time.
        profiles = [app.profile_store.create_profile({
            "name": name, "last_name": "Test", "birth_date": birth,
            "birth_time": "07:51", "birth_place": "Longjumeau, FR",
        }) for name, birth in (("Alice", "1988-10-27"), ("Bob", "1990-02-03"))]
        event = app.profile_store.create_event({
            "profile_id": profiles[1]["id"], "title": "Événement de test", "category": "Amour",
            "date_start": "2028-04-12", "event_time": "14:25", "place": "Longjumeau, FR",
            "notes": "Contenu à conserver",
        })
        app.load_profile(profiles[0]["id"])
        app.open_saved_event(event["id"])
        idle()
        assert app.active_profile_id == profiles[1]["id"]
        assert app.current_interpretation_context["target_date"] == "2028-04-12"
        assert app.current_interpretation_state["hour_card"]["time_local"] == "14:25"
        assert app.birth_entry.get() == "03/02/1990"
        assert app.timeline_view.events[0]["id"] == event["id"]
        with patch.object(app, "datetime", FixedNow):
            app.reset_to_origin()
        idle()
        assert app.active_profile_id == profiles[1]["id"]
        saved = app.profile_store.get_event(event["id"])
        assert (saved["date_start"], saved["event_time"], saved["notes"]) == (
            "2028-04-12", "14:25", "Contenu à conserver"
        )
        app.manage_profiles()
        assert not app.notebook.winfo_manager()
        app.open_profile_from_menu(profiles[0]["id"])
        idle()
        assert app.profiles_page is None and app.notebook.winfo_manager() == "pack"
        assert app.active_profile_id == profiles[0]["id"]
        assert app.birth_entry.get() == "27/10/1988"
        print("Profile switching, saved event and return from profiles page: OK")
    finally:
        gate.set() if "gate" in locals() else None
        root.destroy()
        test_directory.cleanup()


tk.Tk = hidden_tk
tk.Misc.mainloop = inspect
import app  # noqa: E402,F401
