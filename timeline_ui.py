"""Tkinter view for exploring deterministic Olney cycle periods."""

from __future__ import annotations

import tkinter as tk
from brand_theme import LIGHT
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from tkinter import ttk


LEVELS = (
    ("life_path", "CHEMIN DE VIE", "#2474C8"),
    ("annual", "ANNÉE", "#F2994A"),
    ("fifty_two_day", "52 JOURS", "#9B51E0"),
    ("day", "JOUR", "#27AE60"),
    ("hour", "HEURE", "#00A6A6"),
)
ZOOM_SPANS = (
    timedelta(days=365 * 28),
    timedelta(days=365 * 14),
    timedelta(days=365 * 7),
    timedelta(days=365 * 3),
    timedelta(days=365),
    timedelta(days=120),
    timedelta(days=31),
    timedelta(days=7),
    timedelta(days=2),
    timedelta(hours=12),
)
ZOOM_LABELS = (
    "28 ans", "14 ans", "7 ans", "3 ans", "1 an",
    "4 mois", "1 mois", "1 semaine", "2 jours", "12 heures",
)
VISIBLE_LEVELS = (
    ("life_path", "annual"),
    ("life_path", "annual"),
    ("life_path", "annual", "fifty_two_day"),
    ("life_path", "annual", "fifty_two_day"),
    ("life_path", "annual", "fifty_two_day", "day"),
    ("life_path", "annual", "fifty_two_day", "day"),
    ("life_path", "annual", "fifty_two_day", "day"),
    ("life_path", "annual", "fifty_two_day", "day", "hour"),
    ("life_path", "annual", "fifty_two_day", "day", "hour"),
    ("life_path", "annual", "fifty_two_day", "day", "hour"),
)
MOVE_STEPS = (
    ("years", 7),
    ("years", 3),
    ("years", 1),
    ("months", 6),
    ("months", 3),
    ("days", 45),
    ("days", 7),
    ("days", 1),
    ("hours", 6),
    ("hours", 1),
)


def shift_date_for_zoom(value, zoom_index: int, direction: int):
    """Move a date or datetime by the step associated with the current zoom."""
    unit, amount = MOVE_STEPS[zoom_index]
    signed = amount * (1 if direction >= 0 else -1)
    if unit == "days":
        return value + timedelta(days=signed)
    if unit == "hours":
        return value + timedelta(hours=signed)
    if unit == "years":
        target_year = value.year + signed
        target_day = min(value.day, monthrange(target_year, value.month)[1])
        return value.replace(year=target_year, day=target_day)

    absolute_month = value.year * 12 + value.month - 1 + signed
    target_year, month_index = divmod(absolute_month, 12)
    target_month = month_index + 1
    target_day = min(value.day, monthrange(target_year, target_month)[1])
    return value.replace(year=target_year, month=target_month, day=target_day)


class TimelineView:
    def __init__(self, parent, timeline_engine, on_date_selected, is_dark):
        self.timeline_engine = timeline_engine
        self.on_date_selected = on_date_selected
        self.is_dark = is_dark
        self.birth_date: date | None = None
        self.selected_date: date | None = None
        self.selected_moment: datetime | None = None
        self.view_start: datetime | None = None
        self.view_end: datetime | None = None
        self.analyzed_place = ""
        self.periods = []
        self.convergences = []
        self.events = []
        self.state = None
        self.birth_card_number_override = None
        self.zoom_index = 3
        self._dragging = False
        self._pending_callback = None
        self._wheel_callback = None
        self._wheel_target = None
        self.request_periods = None
        self._period_generation = 0
        self._loading = False
        self.message = "La frise apparaîtra après le calcul."

        self.frame = ttk.Frame(parent, padding=(12, 10))
        self.frame.pack(fill="both", expand=True)

        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(
            toolbar, text="FRISE CHRONOLOGIQUE", font=("Segoe UI", 12, "bold")
        ).pack(side="left")
        self.busy_var = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self.busy_var, font=("Segoe UI", 9)).pack(
            side="left", padx=16
        )
        controls = ttk.Frame(toolbar)
        controls.pack(side="right")
        self.zoom_var = tk.StringVar(value=ZOOM_LABELS[self.zoom_index])
        ttk.Label(controls, textvariable=self.zoom_var, width=10, anchor="center").pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(controls, text="−", width=3, command=lambda: self._zoom(-1)).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(controls, text="＋", width=3, command=lambda: self._zoom(1)).pack(
            side="left"
        )
        ttk.Button(controls, text="◀", width=3, command=lambda: self._shift(-1)).pack(
            side="left", padx=(12, 4)
        )
        ttk.Button(controls, text="▶", width=3, command=lambda: self._shift(1)).pack(
            side="left"
        )

        self.canvas = tk.Canvas(
            self.frame,
            height=420,
            highlightthickness=1,
            borderwidth=0,
            cursor="sb_h_double_arrow",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)
        self.canvas.bind("<MouseWheel>", self._mousewheel)
        self.apply_theme()

    def _palette(self):
        if self.is_dark():
            return {
                "background": "#0D141C",
                "panel": "#151F29",
                "line": "#405465",
                "text": "#E7EEF5",
                "muted": "#AFC0CE",
                "cursor": "#FFFFFF",
                "return": "#F2C94C",
                "cycle": "#8FD3FF",
            }
        return {
            "background": LIGHT["bg"],
            "panel": LIGHT["panel"],
            "line": LIGHT["line"],
            "text": LIGHT["text"],
            "muted": LIGHT["muted"],
            "cursor": LIGHT["accent"],
            "return": "#D99B00",
            "cycle": LIGHT["accent"],
        }

    def apply_theme(self):
        palette = self._palette()
        self.canvas.configure(
            background=palette["panel"],
            highlightbackground=palette["line"],
            highlightcolor=palette["line"],
        )
        self.redraw()

    def show_message(self, message):
        self._period_generation += 1
        self._loading = False
        self.birth_date = None
        self.selected_date = None
        self.selected_moment = None
        self.periods = []
        self.convergences = []
        self.message = message
        self.redraw()

    def update(self, birth_date, selected_date, state, selected_time=None, place=""):
        palette = self._palette()
        self.canvas.configure(background=palette["panel"], highlightbackground=palette["line"],
                              highlightcolor=palette["line"])
        self.birth_date = birth_date
        self.selected_date = selected_date
        self.selected_moment = datetime.combine(
            selected_date, selected_time or time.min
        )
        self.analyzed_place = place or ""
        self.state = state
        self.birth_card_number_override = (
            state["birth"]["card_number"] if state.get("birth_card_override") else None
        )
        self.message = ""
        if state.get("joker"):
            self.show_message("Joker — frise des cycles ordinaires indisponible")
            return

        if not self._dragging or not self.view_start or not self.view_end:
            self._set_window(self.selected_moment)
        self._refresh_periods()
        self.redraw()

    def set_events(self, events):
        """Display profile events without making the timeline own persistence."""
        self.events = list(events or [])
        if getattr(self, "is_currently_visible", lambda: True)():
            self.redraw()

    def cancel_navigation(self):
        """An explicit clock/reset request supersedes pending wheel/drag timers."""
        for name in ("_pending_callback", "_wheel_callback"):
            job = getattr(self, name)
            if job is not None:
                self.canvas.after_cancel(job)
                setattr(self, name, None)
        self._wheel_target = None

    def _set_window(self, center):
        span = ZOOM_SPANS[self.zoom_index]
        start = center - span / 2
        birth_moment = datetime.combine(self.birth_date, time.min) if self.birth_date else None
        if birth_moment and start < birth_moment:
            start = birth_moment
        self.view_start = start
        self.view_end = start + span

    def _zoom(self, direction):
        new_index = max(0, min(len(ZOOM_SPANS) - 1, self.zoom_index + direction))
        if new_index == self.zoom_index or not self.selected_moment:
            return
        self.zoom_index = new_index
        self.zoom_var.set(ZOOM_LABELS[self.zoom_index])
        self._set_window(self.selected_moment)
        self._refresh_periods()
        self.redraw()

    def _visible_levels(self):
        return VISIBLE_LEVELS[self.zoom_index]

    def _refresh_periods(self):
        if not self.birth_date or not self.view_start or not self.view_end:
            self.periods = []
            self.convergences = []
            return
        visible = self._visible_levels()
        if self.request_periods is not None:
            self._period_generation += 1
            generation = self._period_generation
            self._loading = True

            def ready(result):
                if generation != self._period_generation:
                    return
                self.periods, self.convergences = result
                self._loading = False
                self.redraw()

            def failed(error):
                if generation == self._period_generation:
                    self.show_message(f"Frise indisponible : {error}")

            self.request_periods(
                (
                    self.birth_date, self.view_start, self.view_end, visible,
                    self.analyzed_place, self.birth_card_number_override,
                ),
                ready, failed,
            )
            return
        self.periods = self.timeline_engine.get_periods(
            self.birth_date, self.view_start.date(),
            (self.view_end + timedelta(days=1)).date(),
            levels=tuple(level for level in visible if level != "hour"),
            birth_card_number=self.birth_card_number_override,
        )
        if "hour" in visible and self.analyzed_place:
            self.periods.extend(self.timeline_engine.get_hour_periods(
                self.view_start, self.view_end, self.analyzed_place
            ))
        self.convergences = (
            self.timeline_engine.find_convergences(
                self.birth_date, self.view_start.date(),
                (self.view_end + timedelta(days=1)).date(),
                tuple(level for level in visible if level not in ("hour", "life_path")),
                self.birth_card_number_override,
            )
            if "annual" in visible and "fifty_two_day" in visible
            else []
        )

    def _shift(self, direction):
        if not self.selected_moment or not self.birth_date:
            return
        selected = shift_date_for_zoom(
            self.selected_moment, self.zoom_index, direction
        )
        birth_moment = datetime.combine(self.birth_date, time.min)
        if selected < birth_moment:
            selected = birth_moment
        self.selected_moment, self.selected_date = selected, selected.date()
        self.on_date_selected(selected)

    def _date_from_x(self, x):
        if not self.view_start or not self.view_end:
            return None
        width = max(1, self.canvas.winfo_width())
        left, right = 145, width - 24
        ratio = max(0.0, min(1.0, (x - left) / max(1, right - left)))
        selected = self.view_start + (self.view_end - self.view_start) * ratio
        selected = selected.replace(second=0, microsecond=0)
        if self.zoom_index < 7 and self.selected_moment:
            selected = datetime.combine(selected.date(), self.selected_moment.time())
        birth_moment = datetime.combine(self.birth_date, time.min) if self.birth_date else None
        if birth_moment and selected < birth_moment:
            selected = birth_moment
        return selected

    def _start_drag(self, event):
        self._dragging = True
        self._select_from_x(event.x, delayed=True)

    def _drag(self, event):
        self._select_from_x(event.x, delayed=True)

    def _end_drag(self, event):
        if self._pending_callback:
            self.canvas.after_cancel(self._pending_callback)
            self._pending_callback = None
        selected = self._date_from_x(event.x)
        self._dragging = False
        if selected:
            self.on_date_selected(selected)

    def _select_from_x(self, x, delayed=False):
        selected = self._date_from_x(x)
        if not selected:
            return
        self.selected_date = selected.date()
        self.selected_moment = selected
        self.redraw()
        if delayed:
            if self._pending_callback:
                self.canvas.after_cancel(self._pending_callback)
            self._pending_callback = self.canvas.after(
                140, lambda value=selected: self._emit_delayed(value)
            )

    def _emit_delayed(self, selected):
        self._pending_callback = None
        if self._dragging:
            self.on_date_selected(selected)

    def _mousewheel(self, event):
        if not self.selected_moment or not self.birth_date:
            return "break"
        direction = -1 if event.delta > 0 else 1
        base = self._wheel_target or self.selected_moment
        selected = shift_date_for_zoom(base, self.zoom_index, direction)
        birth_moment = datetime.combine(self.birth_date, time.min)
        if selected < birth_moment:
            selected = birth_moment
        self._wheel_target = selected
        self.selected_date = selected.date()
        self.selected_moment = selected
        self.redraw()
        if self._wheel_callback:
            self.canvas.after_cancel(self._wheel_callback)
        self._wheel_callback = self.canvas.after(90, self._emit_wheel)
        return "break"

    def _emit_wheel(self):
        self._wheel_callback = None
        selected = self._wheel_target
        self._wheel_target = None
        if selected:
            self.on_date_selected(selected)

    def _x_for_date(self, value, left, right):
        total = max(1.0, (self.view_end - self.view_start).total_seconds())
        return left + ((value - self.view_start).total_seconds() / total) * (right - left)

    @staticmethod
    def _as_moment(value):
        parsed = datetime.fromisoformat(value)
        return parsed

    @staticmethod
    def _suit(card):
        return card[-1] if card else None

    def redraw(self):
        if self._loading:
            return  # Retain the complete old frame until the replacement is ready.
        self.canvas.delete("all")
        palette = self._palette()
        width = max(400, self.canvas.winfo_width())
        left, right = 145, width - 24
        if not self.birth_date or not self.view_start or not self.view_end:
            self.canvas.create_text(
                width / 2, 150, text=self.message or "La frise apparaîtra après le calcul.",
                fill=palette["muted"], font=("Segoe UI", 11)
            )
            return

        birth_card = self.state.get("birth", {}).get("card") if self.state else None
        convergence_keys = {
            (item["date"], item["end_exclusive"], item["card"])
            for item in self.convergences
        }

        active_levels = set(self._visible_levels())
        visible_specs = list(LEVELS)
        canvas_height = max(260, self.canvas.winfo_height())
        row_step = min(70, max(52, (canvas_height - 90) / len(visible_specs)))
        total_height = row_step * len(visible_specs)
        first_y = max(34, (canvas_height - total_height - 35) / 2)
        bar_height = min(42, row_step - 12)
        date_y = min(canvas_height - 17, first_y + total_height + 8)

        for row_index, (level, title, accent) in enumerate(visible_specs):
            y1 = first_y + row_index * row_step
            y2 = y1 + bar_height
            self.canvas.create_text(
                18, (y1 + y2) / 2, text=title, anchor="w",
                fill=palette["text"],
                font=("Segoe UI", 9, "bold")
            )
            self.canvas.create_line(
                left, y2 + 7, right, y2 + 7,
                fill=accent,
                width=2,
            )
            if level not in active_levels:
                self.canvas.create_rectangle(
                    left, y1, right, y2,
                    fill=accent,
                    outline=palette["panel"],
                    width=1,
                )
            rows = [period for period in self.periods if period["level"] == level]
            rows.sort(key=lambda item: item["start"])
            previous_period = None
            for period in rows:
                start = self._as_moment(period["start"])
                end = self._as_moment(period["end_exclusive"])
                x1 = max(left, self._x_for_date(start, left, right))
                x2 = min(right, self._x_for_date(end, left, right))
                if x2 <= x1:
                    continue
                is_return = bool(birth_card and period.get("card") == birth_card)
                is_convergence = any(
                    card == period.get("card")
                    and self._as_moment(conv_start) < end
                    and self._as_moment(conv_end) > start
                    for conv_start, conv_end, card in convergence_keys
                )
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=accent,
                    outline=palette["return"] if is_convergence else palette["panel"],
                    width=3 if is_convergence else 1,
                )
                coordinates = period.get("coordinates") or {}
                is_crown = coordinates.get("zone") == "couronne"
                is_double = bool(
                    coordinates.get("row_planet")
                    and coordinates.get("row_planet") == coordinates.get("column_planet")
                )
                marker_label = None
                is_cycle_boundary = False
                if level == "annual" and period.get("age", 0) % 7 == 0:
                    is_cycle_boundary = True
                    marker_label = f'Tableau {period["series_id"]}'
                elif level == "fifty_two_day" and period.get("window_index") == 0:
                    is_cycle_boundary = True
                    marker_label = f'Année {period.get("age", 0)}'
                elif level == "day" and period.get("weekday_position") == 1:
                    is_cycle_boundary = True

                if is_cycle_boundary and start >= self.view_start:
                    self.canvas.create_line(
                        x1, y1 - 4, x1, y2 + 4,
                        fill=palette["cycle"], width=3,
                    )
                    if marker_label and x2 - x1 >= 26:
                        self.canvas.create_text(
                            x1 + 4, y1 + 7, text=marker_label, anchor="w",
                            fill="#FFFFFF", font=("Segoe UI", 6, "bold")
                        )
                label = period["label"]
                if is_return:
                    label = f"★ {label}"
                minimum_label_width = {
                    "life_path": 18,
                    "annual": 18,
                    "fifty_two_day": 14,
                    "day": 10,
                    "hour": 16,
                }.get(level, 24)
                if x2 - x1 >= minimum_label_width:
                    self.canvas.create_text(
                        (x1 + x2) / 2, (y1 + y2) / 2 - 4 + (5 if marker_label else 0),
                        text=label, fill="#FFFFFF",
                        font=("Segoe UI Symbol", 7 if level in ("day", "hour") else 9, "bold")
                    )

                badges = []
                if is_crown:
                    badges.append("♛")
                if is_convergence:
                    badges.append("✦")
                if is_double:
                    badges.append("◎")
                if badges and x2 - x1 >= 10:
                    badge_text = " ".join(badges)
                    if x2 - x1 >= 84:
                        names = []
                        if is_crown:
                            names.append("COURONNE")
                        if is_convergence:
                            names.append("CONVERGENCE")
                        if is_double:
                            names.append("CASE DOUBLE")
                        badge_text = " · ".join(names)
                    self.canvas.create_text(
                        (x1 + x2) / 2, y2 - 7, text=badge_text,
                        fill="#FFFFFF", font=("Segoe UI Symbol", 6, "bold")
                    )

                if (
                    previous_period
                    and self._suit(previous_period.get("card")) != self._suit(period.get("card"))
                    and start >= self.view_start
                    and x2 - x1 >= 18
                ):
                    transition = (
                        f'{self._suit(previous_period.get("card"))}→'
                        f'{self._suit(period.get("card"))}'
                    )
                    self.canvas.create_text(
                        x1, y1 - 5, text=transition,
                        fill=accent, font=("Segoe UI Symbol", 6, "bold")
                    )
                previous_period = period

        for fraction in (0, .25, .5, .75, 1):
            value = self.view_start + (self.view_end - self.view_start) * fraction
            x = left + (right - left) * fraction
            date_format = "%d/%m %H:%M" if self.zoom_index >= 7 else "%d/%m/%Y"
            self.canvas.create_text(
                x, date_y, text=value.strftime(date_format),
                fill=palette["muted"], font=("Segoe UI", 8)
            )

        if self.selected_moment:
            x = self._x_for_date(self.selected_moment, left, right)
            x = max(left, min(right, x))
            self.canvas.create_line(
                x, first_y - 12, x, date_y - 17, fill=palette["cursor"], width=3
            )
            self.canvas.create_polygon(
                x - 6, first_y - 14, x + 6, first_y - 14, x, first_y - 5,
                fill=palette["cursor"], outline=""
            )

        # Personal events sit above every cycle: they annotate time without
        # replacing any deterministic Olney period.
        for personal_event in self.events:
            try:
                event_date = datetime.fromisoformat(personal_event["date_start"])
                if personal_event.get("event_time"):
                    parsed_time = datetime.strptime(
                        personal_event["event_time"], "%H:%M"
                    ).time()
                    event_date = datetime.combine(event_date.date(), parsed_time)
            except (KeyError, TypeError, ValueError):
                continue
            if not self.view_start <= event_date <= self.view_end:
                continue
            x = self._x_for_date(event_date, left, right)
            importance = max(1, min(5, int(personal_event.get("importance") or 3)))
            color = "#F2C94C" if self.is_dark() else "#B7791F"
            top = first_y - 24
            self.canvas.create_line(
                x, top + 8, x, first_y - 13, fill=color,
                width=1 + importance // 2,
            )
            self.canvas.create_polygon(
                x, top, x + 6, top + 6, x, top + 12, x - 6, top + 6,
                fill=color, outline="",
            )
            title = str(personal_event.get("title") or "Événement")
            if self.zoom_index >= 4 or importance >= 4:
                self.canvas.create_text(
                    x + 9, top + 6, text=title, anchor="w",
                    fill=palette["text"], font=("Segoe UI", 7, "bold"),
                )
