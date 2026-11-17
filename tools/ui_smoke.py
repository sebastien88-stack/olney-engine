"""Initialize the Tk interface invisibly and report its requested widths."""

from pathlib import Path
import os
import sys
import tkinter as tk
from datetime import date, datetime, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch
from time import monotonic, sleep


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
profile_test_directory = TemporaryDirectory()
os.environ["OLNEY_PROFILE_DB"] = str(
    Path(profile_test_directory.name) / "profiles.db"
)
original_tk = tk.Tk


def hidden_tk(*args, **kwargs):
    root = original_tk(*args, **kwargs)
    root.withdraw()
    return root


def inspect_and_close(root, *args, **kwargs):
    root.update_idletasks()
    app = sys.modules["app"]

    def wait_for_updates():
        deadline = monotonic() + 45
        while True:
            root.update()
            if not app.ui_jobs.busy():
                break
            assert monotonic() < deadline, "Background calculation did not finish"
            sleep(0.005)
        root.update_idletasks()

    def fail_ui(title, message):
        raise AssertionError(f"{title}: {message}")

    app.messagebox.showerror = fail_ui
    root.report_callback_exception = lambda kind, error, tb: fail_ui(kind, error)
    real_calculate = app.calculate

    def calculate_and_wait(*args, **kwargs):
        real_calculate(*args, **kwargs)
        wait_for_updates()

    # Legacy visual assertions inspect completed snapshots. The nonblocking
    # contract itself is exercised separately in ui_async_smoke.py.
    app.calculate = calculate_and_wait

    def show(title, mode=None):
        if title in app.cycle_tab_views:
            app.notebook.select(app.cycle_tab_widgets[title])
            app.cycle_tab_views[title]["selected"].set(mode)
            app.cycle_tab_views[title]["show"]()
        else:
            app.notebook.select(app.global_interpretation_tab)
        app.refresh_visible_view()
        wait_for_updates()

    def restore_sample():
        app.calculate(date(2026, 8, 26))

    def reset_with_current_time(hour=17, minute=51):
        # Simulate the real local clock, independently of both date entries.
        class FixedNow(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2031, 3, 3, hour, minute)

        with patch.object(app, "datetime", FixedNow):
            app.reset_origin_button.invoke()
        assert app.target_time_entry.get() == f"{hour:02}:{minute:02}"
        assert app.birth_time_entry.get() == "07:51"

    widths = {
        "birth": app.birth_group.winfo_reqwidth(),
        "analysis": app.analysis_group.winfo_reqwidth(),
        "profile": app.age_badge.winfo_reqwidth(),
        "inputs_total": app.input_frame.winfo_reqwidth(),
        "clock": app.clock.winfo_reqwidth(),
    }
    print(widths)
    field_y_positions = {
        "birth_date": app.birth_entry.winfo_rooty(),
        "birth_time": app.birth_time_entry.winfo_rooty(),
        "birth_place": app.birth_place_entry.winfo_rooty(),
        "target_date": app.target_entry.winfo_rooty(),
        "target_time": app.target_time_entry.winfo_rooty(),
        "target_place": app.analysis_place_button.winfo_rooty(),
        "calculate": app.calculate_button.winfo_rooty(),
    }
    print(field_y_positions)
    assert len(set(field_y_positions.values())) == 1
    assert app.dark_mode is True
    assert app.reset_origin_button.master is app.analysis_anchor_frame
    assert not hasattr(app, "saved_date_var")
    assert not hasattr(app, "saved_target_date")
    reset_bottom = (
        app.reset_origin_button.winfo_rooty()
        + app.reset_origin_button.winfo_height()
    )
    assert reset_bottom <= app.calculate_button.winfo_rooty()
    assert app.reset_origin_button.winfo_rootx() >= app.calculate_button.winfo_rootx()
    for profile_part in (
        app.age_part,
        app.birth_card_part,
        app.secondary_part,
        app.zodiac_part,
        app.ascendant_part,
    ):
        _, block_y, _, block_height = profile_part.grid_bbox(0, 1, 0, 2)
        assert abs(
            (block_y + block_height / 2.0) - profile_part.winfo_reqheight() / 2.0
        ) <= 1.0
    assert app.credit_label.cget("text") == "Olney Engine V1.8.5 — développé par Sébastien"
    assert app.theme_button.cget("width") == 3
    assert app.theme_button_var.get() == "☀"
    assert app.profile_button_var.get() == "👤 Aucun profil"
    assert app.cycle_tab_views["Ordre naturel"]["available"] == ("table", "birth", "secondary")
    assert set(app.cycle_tab_views["Ordre naturel"]["buttons"]) == {"table", "birth", "secondary", "secondary_two"}
    assert app.cycle_tab_views["Ordre naturel"]["buttons"]["secondary_two"].winfo_manager() == ""
    assert app.reset_today_label.cget("text") == "Aujourd’hui"
    assert app.notebook.tab(app.timeline_tab, "text") == "Frise chronologique"
    assert app.notebook.index(app.global_interpretation_tab) == app.notebook.index(app.timeline_tab) + 1
    assert app.footer.winfo_manager() == "pack"
    assert app.footer.pack_info()["side"] == "bottom"
    for table_view in (
        app.manifested_full,
        app.seven_full,
        app.year_full,
        app.week_full,
    ):
        left_column = table_view.content.grid_bbox(0, 0)
        table_column = table_view.content.grid_bbox(1, 0)
        right_column = table_view.content.grid_bbox(2, 0)
        print({
            "view": table_view.title,
            "columns": (left_column, table_column, right_column),
        })
        assert abs(left_column[2] - right_column[2]) <= 1
        assert abs(
            (table_column[0] + table_column[2] / 2.0)
            - (right_column[0] + right_column[2]) / 2.0
        ) <= 1

        exchange_center = (
            table_view.exchange_panel.winfo_x()
            + table_view.exchange_panel.winfo_width() / 2.0
        )
        legend_center = (
            table_view.legend.winfo_x()
            + table_view.legend.winfo_width() / 2.0
        )
        assert abs(exchange_center - table_view.left_zone.winfo_width() / 2.0) <= 1
        assert abs(legend_center - table_view.right_zone.winfo_width() / 2.0) <= 1
    initial_analyzed_moment = datetime.strptime(
        f"{app.target_entry.get()} {app.target_time_entry.get()}",
        "%d/%m/%Y %H:%M",
    )
    assert abs((datetime.now() - initial_analyzed_moment).total_seconds()) < 120

    app.birth_entry.delete(0, "end")
    app.birth_entry.insert(0, "27101988")
    app._format_masked_entry(app.birth_entry, (2, 2, 4), "/")
    assert app.birth_entry.get() == "27/10/1988"
    app.birth_time_entry.delete(0, "end")
    app.birth_time_entry.insert(0, "0751")
    app._format_masked_entry(app.birth_time_entry, (2, 2), ":")
    assert app.birth_time_entry.get() == "07:51"

    analyzed_time_before_birth_edit = app.target_time_entry.get()
    app.birth_time_entry.delete(0, "end")
    app.birth_time_entry.insert(0, "08:12")
    app.schedule_auto_calculate()
    assert app.target_time_entry.get() == analyzed_time_before_birth_edit

    for entry, value in (
        (app.birth_entry, "27/10/1988"),
        (app.birth_time_entry, "07:51"),
        (app.birth_place_entry, "Longjumeau, FR"),
        (app.target_entry, "26/08/2026"),
        (app.target_time_entry, "17:51"),
    ):
        entry.delete(0, "end")
        entry.insert(0, value)
    app.analysis_place_var.set("Longjumeau, FR")
    app.calculate()
    app.navigate_clock("day", 1)
    assert app.target_entry.get() == "27/08/2026"
    reset_with_current_time()
    assert app.target_entry.get() == "03/03/2031"
    restore_sample()
    assert app.target_entry.get() == "26/08/2026"
    assert app.hour_card_var.get() == "D♥"
    assert app.hour_cycle_var.get() == "17:51 locale\n15:58 solaire"
    assert app.current_interpretation_context is not None
    assert [
        cycle["id"] for cycle in app.current_interpretation_context["cycles"]
    ] == ["natal", "life_path", "seven_year", "annual", "week"]
    # Hidden views are populated on first visit, not at every clock update.
    for title in app.CYCLE_READING_IDS:
        for mode in ("table", "result", "interpretation"):
            show(title, mode)
    show("Lecture globale")
    assert app.manifested_interpretation.context["id"] == "life_path"
    assert app.seven_interpretation.context["id"] == "seven_year"
    assert app.year_interpretation.context["id"] == "annual"
    assert app.week_interpretation.context["id"] == "week"
    assert app.global_interpretation.context["target_date"] == "2026-08-26"
    cycle_by_id = {
        cycle["id"]: cycle
        for cycle in app.current_interpretation_context["cycles"]
    }
    for table_view, cycle_id in (
        (app.manifested_full, "life_path"),
        (app.seven_full, "seven_year"),
        (app.year_full, "annual"),
        (app.week_full, "week"),
    ):
        cycle = cycle_by_id[cycle_id]
        assert table_view.exchange_personal_label.cget("text") == (
            f"CARTE ACTIVE\n{cycle['active_card']['label']}"
        )
        assert table_view.displacement_label.cget("text") == (
            cycle["position"]["owner_card"]["label"]
        )
        assert table_view.environment_label.cget("text") == (
            cycle["position"]["support_card"]["label"]
        )
    for interpretation_view in (
        app.manifested_interpretation,
        app.seven_interpretation,
        app.year_interpretation,
        app.week_interpretation,
        app.global_interpretation,
    ):
        assert getattr(
            interpretation_view.content, "_olney_interpretation_view", None
        ) is interpretation_view.view
    assert root.bind_all("<MouseWheel>")

    def visible_texts(widget):
        texts = []
        for child in widget.winfo_children():
            try:
                text = child.cget("text")
            except tk.TclError:
                text = ""
            if text:
                texts.append(text)
            texts.extend(visible_texts(child))
        return texts

    cycle_text = "\n".join(visible_texts(app.year_interpretation.content))
    assert "SYNTHÈSE DE LA PÉRIODE" in cycle_text
    assert "EMPLACEMENT TABLEAU" in cycle_text
    assert "LUNE DU CYCLE" in cycle_text
    assert "DANS LA VIE" in cycle_text
    assert "AU FIL DES CYCLES" in cycle_text
    active_card = cycle_by_id["annual"]["active_card"]
    profile_text = app.year_interpretation.knowledge.profiles[active_card["id"]]
    assert profile_text["energy"] in cycle_text
    assert profile_text["manifestations"] in cycle_text
    assert profile_text["constructive"] in cycle_text
    assert profile_text["difficult"] in cycle_text
    assert "LIEN AVEC LE CYCLE SUPÉRIEUR" not in cycle_text
    assert "POURQUOI CETTE LECTURE ?" in cycle_text
    assert "POUR PRÉCISER LA LECTURE" not in cycle_text
    global_text = "\n".join(visible_texts(app.global_interpretation.content))
    assert "RÉSONANCES REMARQUABLES" in global_text
    assert "DÉFI DU CHEMIN DE VIE" in global_text
    assert "ÉLÉMENTS EN PRÉSENCE" in global_text
    assert ".." not in global_text
    assert app.current_interpretation_context["synthesis"]["elements"]["total_active_cards"] == 5
    assert "La fonction Mars se retrouve" in global_text
    assert "la carte Mars du cycle de 13 ans" not in global_text
    assert "lui donne sa manière d’agir" not in global_text
    assert "À l’intérieur de" not in global_text
    assert "QUESTION DE LECTURE" not in global_text

    # The fixed header stays visible; selecting a path step moves the whole clock.
    initial_date = app.current_target_date
    original_time = app.target_time_entry.get()
    for title, cid in app.CYCLE_READING_IDS.items():
        assert app.cycle_tab_views[title]["available"] == ("table", "result", "interpretation", "cycle")
        app.notebook.select(app.cycle_tab_widgets[title])
        app.cycle_tab_views[title]["selected"].set("cycle")
        app.cycle_tab_views[title]["show"]()
        wait_for_updates()
        view = app.cycle_reading_views[cid]
        reading = view.context["cycle_reading"]
        assert view.present["date"] == date.today().isoformat()
        view.today_getter = lambda: initial_date
        view._render()
        assert view.band.master is view.container
        assert not view.band.winfo_children() or all(not isinstance(child, tk.Button) for child in view.band.winfo_children())
        assert len(view.step_buttons) == 7
        assert not hasattr(view, "explore_button")
        assert not any("Explorer cette période" in text for text in visible_texts(view.content))
        assert "LE MOUVEMENT DU CYCLE" in "\n".join(visible_texts(view.content))
        assert "LE PARCOURS, ÉTAPE PAR ÉTAPE" in "\n".join(visible_texts(view.content))
        current_index = reading["current_step_index"]
        selected_index = (current_index + 1) % 7
        destination = reading["steps"][selected_index]["period"]["start"]
        view.step_buttons[selected_index].invoke()
        wait_for_updates()
        assert view.selected_index == selected_index
        assert app.current_target_date.isoformat() == destination
        assert app.target_time_entry.get() == original_time
        assert reading["current_step_index"] == current_index
        view.canvas.yview_moveto(0)
        root.update_idletasks()
        viewport_top = view.canvas.canvasy(0)
        band_top = view.band.winfo_rooty()
        view.canvas.yview_moveto(1)
        root.update_idletasks()
        # Canvas coordinates remain meaningful even with the test root withdrawn.
        assert view.canvas.canvasy(0) > viewport_top
        assert view.band.winfo_rooty() == band_top
        assert view.band.winfo_height() < 130
        assert view.band.winfo_rooty() + view.band.winfo_height() <= view.canvas.winfo_rooty()
        app.dark_mode = False
        app.apply_theme()
        assert view.selected_index == selected_index
        assert "RÉSULTAT DU CYCLE" in "\n".join(visible_texts(view.content))
        app.dark_mode = True
        app.apply_theme()
        assert view.selected_index == selected_index
        app.calculate(date.fromisoformat(destination))
        root.update_idletasks()
        assert app.current_target_date.isoformat() == destination
        assert app.target_time_entry.get() == original_time
        assert app.cycle_tab_views[title]["selected"].get() == "cycle"
        assert view.context["cycle_reading"]["current_step_index"] == selected_index
        assert view.present["current_step_index"] == current_index
        assert view.status_labels[current_index].cget("text").startswith("En cours")
        assert not view.status_labels[selected_index].cget("text").startswith("En cours")
        restore_sample()
        root.update_idletasks()
        assert app.current_target_date == initial_date
        assert view.selected_index == view.context["cycle_reading"]["current_step_index"]

    # A fully future or past week must never force a present-day highlight.
    for explored_date, expected in ((date(2040, 1, 1), "À venir"), (date(2000, 1, 1), "Écoulée")):
        app.calculate(explored_date)
        view = app.week_cycle_reading
        assert view.present["current_step_index"] is None
        assert all(label.cget("text").startswith(expected) for label in view.status_labels)
        assert all(tile.cget("highlightbackground") != view._palette()["good_line"] for tile in view.step_tiles)
    restore_sample()
    view = app.week_cycle_reading
    selected_before_midnight = view.selected_index
    view.canvas.yview_moveto(0.4)
    scroll_before_midnight = view.canvas.yview()[0]
    view.today_getter = lambda: initial_date + timedelta(days=1)
    view.refresh_today()
    assert view.present["date"] == (initial_date + timedelta(days=1)).isoformat()
    assert view.selected_index == selected_before_midnight
    assert app.current_target_date == initial_date
    assert abs(view.canvas.yview()[0] - scroll_before_midnight) < 0.01
    for view in app.cycle_reading_views.values():
        view.today_getter = date.today
        view.refresh_today()

    app.dark_mode = False
    app.apply_theme()
    show("Cycle annuel", "interpretation")
    show("Lecture globale")
    light_palette = app.global_interpretation._palette()
    light_text = "\n".join(visible_texts(app.year_interpretation.content))
    assert profile_text["energy"] in light_text
    assert profile_text["manifestations"] in light_text
    assert "ÉLÉMENTS EN PRÉSENCE" in "\n".join(visible_texts(app.global_interpretation.content))
    assert light_palette["blue_soft"] != light_palette["panel"]
    assert light_palette["gold_soft"] != light_palette["panel"]
    assert light_palette["violet_soft"] != light_palette["panel"]
    clock_card_buttons = []

    def collect_clock_buttons(widget):
        for child in widget.winfo_children():
            if isinstance(child, tk.Button) and int(child.cget("width")) == 6:
                clock_card_buttons.append(child)
            collect_clock_buttons(child)

    collect_clock_buttons(app.global_interpretation.content)
    assert len(clock_card_buttons) == 6
    assert all(button.cget("relief") == "solid" for button in clock_card_buttons)
    assert all(
        button.cget("highlightbackground").upper() == light_palette["card_line"]
        for button in clock_card_buttons
    )
    app.dark_mode = True
    app.apply_theme()

    app.open_clock_table("Cycle annuel")
    assert app.notebook.select() == str(app.cycle_tab_widgets["Cycle annuel"])
    assert app.cycle_tab_views["Cycle annuel"]["selected"].get() == "result"

    app.open_global_cycle("annual")
    wait_for_updates()
    assert app.notebook.select() == str(app.cycle_tab_widgets["Cycle annuel"])
    assert app.year_interpretation.return_visible is True
    assert "← Retour à la lecture globale" in "\n".join(
        visible_texts(app.year_interpretation.content)
    )
    app.return_to_global_interpretation()
    assert app.notebook.select() == str(app.global_interpretation_tab)
    assert app.year_interpretation.return_visible is False

    wheel_events = []
    original_wheel_handler = app.global_interpretation._on_mousewheel
    app.global_interpretation._on_mousewheel = (
        lambda event: wheel_events.append(event.delta)
    )
    app.global_interpretation._dispatch_mousewheel(
        type(
            "Wheel", (),
            {"delta": -120, "widget": app.global_interpretation.content},
        )()
    )
    assert wheel_events == [-120]
    app.global_interpretation._on_mousewheel = original_wheel_handler

    app.target_time_entry.delete(0, "end")
    app.target_time_entry.insert(0, "18:32")
    app.calculate()
    assert app.hour_card_var.get() == "7♥"
    assert app.birth_time_entry.get() == "07:51"

    app.target_time_entry.delete(0, "end")
    app.target_time_entry.insert(0, "17:51")
    app.calculate()
    app.navigate_clock("hour", 1)
    assert app.target_time_entry.get() == "18:51"
    assert app.hour_card_var.get() == "7♥"
    assert app.birth_time_entry.get() == "07:51"

    app.analysis_place_linked = False
    app.analysis_place_var.set("New York City, US")
    assert app.target_time_entry.get() == "18:51"
    reset_with_current_time()
    assert app.target_entry.get() == "03/03/2031"
    assert app.target_time_entry.get() == "17:51"
    assert app.analysis_place_var.get() == "New York City, US"
    assert app.analysis_time_linked is False
    assert app.analysis_place_linked is False
    reset_with_current_time(0, 4)
    assert app.target_entry.get() == "03/03/2031"
    assert app.analysis_place_var.get() == "New York City, US"
    print("Interface et indépendance naissance/analyse OK")
    root.destroy()
    profile_test_directory.cleanup()


tk.Tk = hidden_tk
tk.Misc.mainloop = inspect_and_close

import app  # noqa: E402,F401  (initialization is the purpose of this smoke test)
