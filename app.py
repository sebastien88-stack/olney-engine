import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import os
import sys
from brand_theme import LIGHT
from olney_engine import OlneyEngine
from interpretation_runtime import InterpretationContextBuilder, InterpretationKnowledge
from interpretation_ui import CycleInterpretationView, GlobalInterpretationView
from cycle_reading_ui import CycleReadingView
from natal_card_ui import NatalCardView
from cycle_reading import CYCLE_FOCUS, CycleCalendarMismatch
from timeline_runtime import TimelineEngine
from timeline_ui import TimelineView
from ui_jobs import LatestJobs, BusyIndicator, DeferredView
from analysis_work import AnalysisWork
from navigation import NavigationHistory, temporal_label
from profile_store import PROFILE_FIELDS, ProfileStore
from relationship_runtime import RelationshipEngine
from relationship_ui import RelationshipDetailView
from olney_chat import OlneyChatService, OpenAIResponsesClient
from chat_ui import OlneyChatView
from wrapped_list import WrappedList
from astro_engine import (
    calculate_ascendant,
    parse_birth_time,
    resolve_place,
    suggest_places,
)

engine = OlneyEngine()
CARD_NUMBER_BY_LABEL = {label: number for number, label in engine.cards.items()}
interpretation_knowledge = InterpretationKnowledge.load()
interpretation_builder = InterpretationContextBuilder(engine, interpretation_knowledge)
timeline_engine = TimelineEngine(engine)
profile_store = ProfileStore()
relationship_engine = RelationshipEngine(engine, interpretation_knowledge)
olney_chat_service = OlneyChatService(
    profile_store, knowledge=interpretation_knowledge
)
olney_openai_client = OpenAIResponsesClient()
active_profile_id = profile_store.get_last_profile_id()
profile_dirty = False
current_target_date = None
current_interpretation_context = None
current_interpretation_state = None
current_reading_material = None
cycle_reading_cache = {}
pending_cycle_cards = {}
navigation_history = NavigationHistory()
committed_navigation = None
navigation_dirty = True
navigation_restore = None
history_record_job = None
analysis_work = AnalysisWork(interpretation_knowledge)
deferred_views = {}
dark_mode = True
analysis_time_linked = False
analysis_place_linked = True
profiles_page = None
profiles_page_apply_theme = None
profiles_page_return = None
events_page = None
events_page_apply_theme = None
events_page_return = None
relationships_page = None
relationships_page_apply_theme = None
relationships_page_return = None
chat_page = None
chat_page_apply_theme = None
chat_page_return = None

PLANET_ROWS = ("mercure", "vénus", "mars", "jupiter", "saturne", "uranus", "neptune")
PLANET_COLUMNS = ("neptune", "uranus", "saturne", "jupiter", "mars", "vénus", "mercure")
SLOT_COLORS = {
    "lune": "#DDDDDD",
    "soleil": "#FFFF00",
    "mercure": "#FFE994",
    "vénus": "#FFB66C",
    "mars": "#FFAA95",
    "jupiter": "#EC9BA4",
    "saturne": "#BF819E",
    "uranus": "#B7B3CA",
    "neptune": "#B4C7DC",
    "défi": "#AFD095",
    "résultat": "#D4EA6B",
}
SLOT_SYMBOLS = {
    "lune": "☾",
    "soleil": "☉",
    "mercure": "☿",
    "vénus": "♀",
    "mars": "♂",
    "jupiter": "♃",
    "saturne": "♄",
    "uranus": "♅",
    "neptune": "♆",
    "pluton": "♇",
    "défi": "⚔",
    "résultat": "★",
}
FIXED_CARDS = ("R♠", "V♥", "8♣")
SEMI_FIXED_CARDS = ("A♣", "2♥", "7♦", "9♥")
PROFILE_TYPES = ("Humain", "Ville", "Pays", "Organisation", "Projet", "Animal")
CLOCK_TAB_TARGETS = {
    "birth": "Chemin de vie",
    "year": "Cycle 7 ans",
    "fifty": "Cycle annuel",
    "week": "Cycle semaine",
}

def parse_date(value: str):
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError("Format de date invalide. Utilise JJ/MM/AAAA ou AAAA-MM-JJ.")

def fmt_date(value):
    if not value:
        return "—"
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(value)


def fmt_period(start, end):
    if not start or not end:
        return "—"
    return f"{fmt_date(start)}  →  {fmt_date(end)}"


def zodiac_sign(value):
    """Return the western zodiac sign for a birth date."""
    symbols = {
        "Bélier": "♈",
        "Taureau": "♉",
        "Gémeaux": "♊",
        "Cancer": "♋",
        "Lion": "♌",
        "Vierge": "♍",
        "Balance": "♎",
        "Scorpion": "♏",
        "Sagittaire": "♐",
        "Capricorne": "♑",
        "Verseau": "♒",
        "Poissons": "♓",
    }
    sign = engine.zodiac_sign(value)
    return f"{symbols[sign]} {sign}"


def set_clock_card(key, variable, card):
    card = str(card or "—")
    variable.set(card)
    if "♥" in card or "♦" in card:
        color = "#FF6B6B" if dark_mode else "#C62828"
    else:
        color = "#EAF2F8" if dark_mode else "#111827"
    widget = clock_card_labels.get(key)
    if widget:
        widget.configure(foreground=color)


def set_profile_birth_card(card):
    card = str(card or "—")
    birth_card_var.set(card)
    color = "#FFB7B7" if "♥" in card or "♦" in card else "#FFFFFF"
    birth_profile_card_label.configure(foreground=color)


def set_secondary_cards(cards):
    for child in secondary_cards_holder.winfo_children():
        child.destroy()

    if not cards:
        tk.Label(
            secondary_cards_holder,
            text="—",
            background="#173F5F",
            foreground="#8FA8BC",
            font=("Segoe UI", 15, "bold"),
        ).pack()
        return

    for item in cards:
        card = str(item["card"])
        ink = "#FFB7B7" if "♥" in card or "♦" in card else "#FFFFFF"
        tk.Label(
            secondary_cards_holder,
            text=card,
            background="#173F5F",
            foreground=ink,
            font=("Segoe UI Symbol", 16, "bold"),
        ).pack(side="left", padx=7)


def refresh_ascendant(birth):
    time_text = birth_time_entry.get().strip()
    place_text = birth_place_entry.get().strip()
    if not time_text or not place_text:
        ascendant_var.set("—")
        return None
    result = calculate_ascendant(birth, time_text, place_text)
    ascendant_var.set(result["display_sign"])
    return result

def clear_tree(tree):
    for item in tree.get_children():
        tree.delete(item)

def fill_tree(tree, rows, mode):
    clear_tree(tree)

    if mode == "seven_year":
        for r in rows:
            tree.insert("", "end", values=(
                str(r.get("slot", "—")).capitalize(),
                r.get("card", "—"),
                r.get("card_number", "—"),
                r.get("year") if r.get("year") is not None else "—",
                r.get("position", "—"),
            ), tags=(r.get("slot", ""),))

    elif mode == "year":
        for r in rows:
            tree.insert("", "end", values=(
                str(r.get("slot", "—")).capitalize(),
                r.get("card", "—"),
                r.get("card_number", "—"),
                fmt_date(r.get("period_start")),
                fmt_date(r.get("period_end")),
                r.get("position", "—"),
            ), tags=(r.get("slot", ""),))

    elif mode == "week":
        for r in rows:
            tree.insert("", "end", values=(
                str(r.get("slot", "—")).capitalize(),
                r.get("card", "—"),
                r.get("card_number", "—"),
                fmt_date(r.get("date")),
                r.get("position", "—"),
            ), tags=(r.get("slot", ""),))

    elif mode == "day":
        for r in rows:
            tree.insert("", "end", values=(
                str(r.get("slot", "—")).capitalize(),
                r.get("card", "—"),
                r.get("card_number", "—"),
                fmt_date(r.get("date")),
                r.get("position", "—"),
            ), tags=(r.get("slot", ""),))

    elif mode == "base":
        for r in rows:
            tree.insert("", "end", values=(
                str(r.get("slot", "—")).capitalize(),
                r.get("card", "—"),
                r.get("card_number", "—"),
                r.get("position", "—"),
            ), tags=(r.get("slot", ""),))


def complete_result_rows(rows, series_id, birth_card_number):
    """Add Moon and Sun to the visible result without changing engine output."""
    relative = engine.relative_cards(series_id, birth_card_number)
    prefix = []
    for slot in ("lune", "soleil"):
        card = relative[slot]
        prefix.append({
            "slot": slot,
            "card": card.card_label,
            "card_number": card.card_number,
            "position": card.position_1based,
        })
    return prefix + list(rows)


def relative_result_rows(series_id, birth_card_number):
    """Return the complete Moon-to-Result reading for a fixed base order."""
    return [
        {
            "slot": slot,
            "card": card.card_label,
            "card_number": card.card_number,
            "position": card.position_1based,
        }
        for slot, card in engine.relative_cards(series_id, birth_card_number).items()
    ]


class FullTableView:
    """52-card grid matching the layout and highlights of the Excel sheet."""

    def __init__(self, parent, title, show_legend=True, show_exchange=True):
        self.title = title
        self.series_var = tk.StringVar(value="Tableau —")
        self.active_var = tk.StringVar(value="")
        self.card_labels = {}

        outer = ttk.Frame(parent, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text=title, font=("Segoe UI", 15, "bold")).pack(side="left")
        header_right = ttk.Frame(header)
        header_right.pack(side="right")
        ttk.Label(header_right, textvariable=self.series_var, font=("Segoe UI", 12, "bold")).pack(
            anchor="e"
        )
        if show_legend:
            ttk.Label(
                header_right,
                textvariable=self.active_var,
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="e")

        self.content = ttk.Frame(outer)
        self.content.pack(fill="both", expand=True)
        self.content.columnconfigure(0, weight=1, uniform="table_side")
        self.content.columnconfigure(1, weight=0)
        self.content.columnconfigure(2, weight=1, uniform="table_side")
        self.content.rowconfigure(0, weight=1)

        # Keep the table on the exact horizontal centre line.  Each legend lives
        # in its own equally-sized side zone and is centred within that zone.
        self.left_zone = ttk.Frame(self.content)
        self.left_zone.grid(row=0, column=0, sticky="nsew")
        self.right_zone = ttk.Frame(self.content)
        self.right_zone.grid(row=0, column=2, sticky="nsew")

        if show_exchange:
            self._make_exchange_panel(self.left_zone)

        if show_legend:
            self._make_legend(self.right_zone)

        self.table = tk.Frame(self.content, background="#FFFFFF")
        self.table.grid(row=0, column=1)

        for visual_col, position in zip((2, 3, 4), (1, 52, 51)):
            self._make_card(self.table, 0, visual_col, position)

        grid_positions = [
            list(range(block_end, block_end - 7, -1))
            for block_end in (8, 15, 22, 29, 36, 43, 50)
        ]
        for row_index, positions in enumerate(grid_positions):
            for col_index, position in enumerate(positions):
                self._make_card(self.table, row_index + 1, col_index, position)
            tk.Label(
                self.table,
                text=PLANET_ROWS[row_index],
                font=("Segoe UI", 9, "bold"),
                background="#DCE8F5",
                foreground="#1F2937",
                anchor="w",
                padx=8,
                pady=3,
                relief="solid",
                borderwidth=1,
            ).grid(row=row_index + 1, column=7, sticky="nsew")

        for col_index, planet in enumerate(PLANET_COLUMNS):
            tk.Label(
                self.table,
                text=planet,
                font=("Segoe UI", 9, "bold"),
                background="#DCE8F5",
                foreground="#1F2937",
                anchor="center",
                padx=3,
                pady=3,
                relief="solid",
                borderwidth=1,
            ).grid(row=8, column=col_index, sticky="nsew")

        self.content.update_idletasks()
        left_width = getattr(self, "exchange_panel", None)
        right_width = getattr(self, "legend", None)
        side_width = max(
            left_width.winfo_reqwidth() if left_width is not None else 0,
            right_width.winfo_reqwidth() if right_width is not None else 0,
        ) + 24
        row_height = max(
            self.table.winfo_reqheight(),
            left_width.winfo_reqheight() if left_width is not None else 0,
            right_width.winfo_reqheight() if right_width is not None else 0,
        ) + 16
        self.left_zone.configure(width=side_width, height=row_height)
        self.right_zone.configure(width=side_width, height=row_height)
        self.left_zone.grid_propagate(False)
        self.right_zone.grid_propagate(False)
        self.content.columnconfigure(0, minsize=side_width)
        self.content.columnconfigure(2, minsize=side_width)
        self.content.rowconfigure(0, minsize=row_height)

    @staticmethod
    def _card_ink(card):
        card = str(card or "—")
        return "#D83232" if "♥" in card or "♦" in card else "#15191D"

    def _make_exchange_card(self, parent, caption, row):
        tk.Label(
            parent,
            text=caption,
            background="#EEF4FA",
            foreground="#52606D",
            font=("Segoe UI", 8, "bold"),
        ).grid(row=row, column=0, sticky="ew", pady=(4, 2))
        card = tk.Label(
            parent,
            text="—",
            width=5,
            height=2,
            background="#FFFFFF",
            foreground="#15191D",
            font=("Segoe UI Symbol", 18, "bold"),
            relief="solid",
            borderwidth=1,
            highlightthickness=3,
            highlightbackground="#9FB3C8",
        )
        card.grid(row=row + 1, column=0, pady=(0, 3))
        return card

    def _make_exchange_panel(self, parent):
        self.exchange_panel = tk.LabelFrame(
            parent,
            text="Échange de place",
            background="#EEF4FA",
            foreground="#173F5F",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=8,
        )
        self.exchange_panel.place(relx=0.5, rely=0.5, anchor="center")
        self.exchange_personal_label = tk.Label(
            self.exchange_panel,
            text="CARTE ACTIVE\n—",
            background="#173F5F",
            foreground="#FFFFFF",
            font=("Segoe UI Symbol", 10, "bold"),
            padx=8,
            pady=5,
            justify="center",
        )
        self.exchange_personal_label.grid(row=0, column=0, sticky="ew", pady=(2, 5))
        self.displacement_label = self._make_exchange_card(
            self.exchange_panel, "OCCUPE LA PLACE DE · CARTE DÉPLACÉE", 1
        )
        self.environment_label = self._make_exchange_card(
            self.exchange_panel, "OCCUPE SA PLACE D’ORIGINE", 3
        )
    def _update_exchange_panel(self, exchange, reference=False):
        if not hasattr(self, "exchange_panel"):
            return

        if reference:
            self.displacement_label.configure(text="—", foreground="#9AA7B2")
            self.environment_label.configure(text="—", foreground="#9AA7B2")
            self.exchange_personal_label.configure(text="CARTE D’ORIGINE\n—")
            return

        if not exchange:
            self.displacement_label.configure(text="—", foreground="#9AA7B2")
            self.environment_label.configure(text="—", foreground="#9AA7B2")
            self.exchange_personal_label.configure(text="CARTE ACTIVE\n—")
            return

        personal = exchange["card"]
        displacement = exchange["displacement"]["card"]
        environment = exchange["environment"]["card"]
        self.displacement_label.configure(
            text=displacement, foreground=self._card_ink(displacement)
        )
        self.environment_label.configure(
            text=environment, foreground=self._card_ink(environment)
        )
        self.exchange_personal_label.configure(text=f"CARTE ACTIVE\n{personal}")

    def _make_legend(self, parent):
        self.legend = tk.LabelFrame(
            parent,
            text="Légende",
            background="#FFFFFF",
            foreground="#1F2937",
            font=("Segoe UI", 10, "bold"),
            padx=7,
            pady=7,
        )
        self.legend.place(relx=0.5, rely=0.5, anchor="center")
        for index, slot in enumerate(SLOT_COLORS):
            item = tk.Label(
                self.legend,
                text=slot.capitalize(),
                width=10,
                background=SLOT_COLORS[slot],
                foreground="#111111",
                font=("Segoe UI", 8),
                padx=3,
                pady=2,
                relief="solid",
                borderwidth=1,
            )
            item.grid(row=index // 2, column=index % 2, padx=2, pady=2, sticky="ew")
        tk.Label(
            self.legend,
            text="Cadre rouge\n= carte active",
            background="#FFFFFF",
            foreground="#B00020",
            font=("Segoe UI", 8, "bold"),
            padx=3,
            pady=3,
            relief="solid",
            borderwidth=2,
            highlightthickness=2,
            highlightbackground="#E00000",
        ).grid(row=6, column=0, columnspan=2, padx=2, pady=(7, 2), sticky="ew")
        tk.Label(
            self.legend,
            text=f"Cartes fixes  ·  {'  '.join(FIXED_CARDS)}",
            background="#F4D58D",
            foreground="#3D2B00",
            font=("Segoe UI Symbol", 8, "bold"),
            padx=5,
            pady=4,
            relief="solid",
            borderwidth=1,
        ).grid(row=7, column=0, columnspan=2, padx=2, pady=(5, 2), sticky="ew")
        tk.Label(
            self.legend,
            text=f"Cartes semi-fixes  ·  {'  '.join(SEMI_FIXED_CARDS)}",
            background="#DED5F2",
            foreground="#3F2A68",
            font=("Segoe UI Symbol", 8, "bold"),
            padx=5,
            pady=4,
            relief="solid",
            borderwidth=1,
        ).grid(row=8, column=0, columnspan=2, padx=2, pady=2, sticky="ew")

    def _make_card(self, parent, row, column, position):
        label = tk.Label(
            parent,
            text="—",
            width=7,
            height=1,
            font=("Segoe UI Symbol", 13),
            background="#FFFFFF",
            foreground="#111111",
            relief="solid",
            borderwidth=1,
            highlightthickness=2,
            highlightbackground="#FFFFFF",
            highlightcolor="#FFFFFF",
            padx=4,
            pady=2,
        )
        label.grid(row=row, column=column, sticky="nsew")
        self.card_labels[position] = label

    def update(self, series_id, slot_cards=None, active_card=None, display_name=None,
               exchange=None, reference=False):
        layout = engine.full_table_layout(series_id)
        cards_by_position = {
            cell["position"]: cell
            for cell in layout["top"] + [cell for row in layout["grid"] for cell in row]
        }
        slot_cards = slot_cards or {}
        slots_by_number = {
            number: slot
            for slot, number in slot_cards.items()
            if slot in SLOT_COLORS
        }

        for position, label in self.card_labels.items():
            cell = cards_by_position[position]
            slot = slots_by_number.get(cell["card_number"])
            fill = SLOT_COLORS.get(slot, "#FFFFFF")
            is_active = cell["card"] == active_card
            label.configure(
                text=cell["card"],
                background=fill,
                foreground="#111111",
                highlightbackground=(
                    "#E00000" if is_active else ("#18232E" if dark_mode else "#FFFFFF")
                ),
                highlightcolor=(
                    "#E00000" if is_active else ("#18232E" if dark_mode else "#FFFFFF")
                ),
            )

        self.series_var.set(display_name or engine.table_name(series_id))
        self.active_var.set(f"Carte active : {active_card}" if active_card else "")
        self._update_exchange_panel(exchange, reference=reference)


class ResultCardsView:
    """Horizontal, illustrated reading inspired by the card spread view."""

    def __init__(self, parent, on_card_selected=None):
        self.on_card_selected = on_card_selected
        self.card_canvases = {}
        self.canvas = tk.Canvas(
            parent,
            background="#DCE8F2",
            highlightthickness=0,
            height=315,
        )
        self.canvas.pack(fill="both", expand=True)

        self.content = tk.Frame(self.canvas, background="#DCE8F2", padx=8, pady=10)
        self.window = self.canvas.create_window((0, 0), window=self.content, anchor="center")
        self.canvas.bind("<Configure>", self._fit_content)

        self.placeholder = tk.Label(
            self.content,
            text="Calcule les dates pour afficher les résultats.",
            background="#DCE8F2",
            foreground="#52606D",
            font=("Segoe UI", 11, "italic"),
            padx=20,
            pady=40,
        )
        self.placeholder.pack()

    def _fit_content(self, event):
        self.canvas.coords(self.window, event.width / 2, event.height / 2)

    @staticmethod
    def _period_text(row, mode):
        if mode == "seven_year":
            year = row.get("year")
            return str(year) if year is not None else ""
        if mode == "year":
            start = row.get("period_start")
            end = row.get("period_end")
            return f"{fmt_date(start)}\n{fmt_date(end)}" if start and end else ""
        if mode in ("week", "day"):
            return fmt_date(row.get("date")) if row.get("date") else ""
        if mode == "life_path":
            return row.get("age_range") or ""
        return ""

    @staticmethod
    def _draw_card(canvas, card, accent, active):
        width, height = 92, 130
        outline = "#E00000" if active else "#AAB5BF"
        line_width = 3 if active else 1
        canvas.create_rectangle(
            3, 3, width - 3, height - 3,
            fill="#FFFFFF",
            outline=outline,
            width=line_width,
        )

        card = str(card or "—")
        suit = card[-1] if card[-1:] in ("♥", "♦", "♣", "♠") else ""
        rank = card[:-1] if suit else card
        ink = "#D83232" if suit in ("♥", "♦") else "#15191D"

        canvas.create_text(
            12, 10,
            text=f"{rank}{suit}",
            anchor="nw",
            fill=ink,
            font=("Segoe UI Symbol", 15, "bold"),
        )
        canvas.create_text(
            width / 2, height / 2 + 3,
            text=suit or rank,
            fill=ink,
            font=("Segoe UI Symbol", 39, "bold"),
        )
        canvas.create_text(
            width - 12, height - 10,
            text=f"{rank}{suit}",
            anchor="se",
            fill=ink,
            font=("Segoe UI Symbol", 15, "bold"),
        )
        canvas.create_line(4, height - 4, width - 4, height - 4, fill=accent, width=5)

    def update(self, rows, mode, active_card=None):
        self.card_canvases = {}
        for child in self.content.winfo_children():
            child.destroy()

        column = 0
        for row in rows:
            slot = str(row.get("slot", "—")).lower()
            accent = SLOT_COLORS.get(slot, "#DCE8F2")
            card = str(row.get("card", "—"))
            active = card == active_card

            if slot in ("mercure", "défi"):
                separator = tk.Frame(
                    self.content,
                    background="#DCE8F2",
                    width=34,
                    height=270,
                )
                separator.grid(row=0, column=column, sticky="ns", padx=4, pady=7)
                separator.grid_propagate(False)
                tk.Label(
                    separator,
                    text="◆",
                    background="#DCE8F2",
                    foreground="#6D8FA8",
                    font=("Segoe UI Symbol", 12),
                ).place(relx=0.5, rely=0.66, anchor="center")
                column += 1

            panel = tk.Frame(
                self.content,
                background="#DCE8F2",
                padx=6,
                pady=2,
            )
            panel.grid(row=0, column=column, sticky="n", padx=1)

            tk.Label(
                panel,
                text=SLOT_SYMBOLS.get(slot, "•"),
                background="#FFFFFF",
                foreground="#111111",
                font=("Segoe UI Symbol", 28),
                width=3,
                height=1,
                highlightthickness=3,
                highlightbackground=accent,
            ).pack(pady=(0, 2))
            tk.Label(
                panel,
                text=slot.capitalize(),
                background="#DCE8F2",
                foreground="#111827",
                font=("Segoe UI", 11, "bold"),
            ).pack()

            column += 1
            tk.Label(
                panel,
                text=self._period_text(row, mode),
                background="#DCE8F2",
                foreground="#263746",
                font=("Segoe UI", 8),
                justify="center",
                height=2,
            ).pack(pady=(2, 3))

            card_canvas = tk.Canvas(
                panel,
                width=92,
                height=130,
                background="#DCE8F2",
                highlightthickness=0,
            )
            card_canvas.pack()
            self._draw_card(card_canvas, card, accent, active)
            self.card_canvases[slot] = card_canvas
            if self.on_card_selected:
                card_canvas.configure(cursor="hand2", takefocus=1)

                def open_card(_event=None, selected=dict(row)):
                    self.on_card_selected(selected)
                    return "break"

                card_canvas.bind("<Button-1>", open_card)
                card_canvas.bind("<Return>", open_card)
                card_canvas.bind("<space>", open_card)
                card_canvas.bind("<FocusIn>", lambda _event, canvas=card_canvas:
                                 canvas.itemconfigure(1, outline="#267DB6", width=3))
                card_canvas.bind("<FocusOut>", lambda _event, canvas=card_canvas, selected=active:
                                 canvas.itemconfigure(1, outline="#E00000" if selected else "#AAB5BF",
                                                      width=3 if selected else 1))

            coordinates = engine.table_coordinates(int(row.get("position")))
            row_name = coordinates.get("row_planet")
            column_name = coordinates.get("column_planet")
            if row_name:
                coordinate_text = f"{SLOT_SYMBOLS[row_name]}    {SLOT_SYMBOLS[column_name]}"
            else:
                coordinate_text = "♛    ♛"
            tk.Label(
                panel,
                text=coordinate_text,
                background="#DCE8F2",
                foreground="#173F5F",
                font=("Segoe UI Symbol", 17, "bold"),
                justify="center",
                pady=5,
            ).pack()

        # Apply the palette before yielding to Tk: no light frame in dark mode.
        self.apply_theme()
        self.canvas.coords(
            self.window,
            self.canvas.winfo_width() / 2,
            self.canvas.winfo_height() / 2,
        )

    def show_message(self, message):
        self.card_canvases = {}
        for child in self.content.winfo_children():
            child.destroy()
        tk.Label(
            self.content,
            text=message,
            background="#DCE8F2",
            foreground="#52606D",
            font=("Segoe UI", 12, "italic"),
            justify="center",
            padx=30,
            pady=70,
        ).pack()
        self.apply_theme()
        self.canvas.coords(
            self.window,
            self.canvas.winfo_width() / 2,
            self.canvas.winfo_height() / 2,
        )

    def apply_theme(self):
        _configure_tk_widget(self.canvas)

def update_interpretation_views(context, state=None):
    """Feed the same structured facts to local cycle and global views."""
    global current_interpretation_context, current_interpretation_state
    current_interpretation_context = context
    current_interpretation_state = state
    cycle_reading_cache.clear()
    update_natal_card_views(context)
    if context.get("joker"):
        message = (
            "Joker — interprétation manifestée laissée en attente de la règle "
            "canonique définitive."
        )
        natural_interpretation.show_message(message)
        manifested_interpretation.show_message(message)
        seven_interpretation.show_message(message)
        year_interpretation.show_message(message)
        week_interpretation.show_message(message)
        global_interpretation.show_message(message)
        for view in cycle_reading_views.values():
            view.show_message(message)
        return

    cycles = {cycle["id"]: cycle for cycle in context["cycles"]}
    natural_interpretation.update(cycles["natal"])
    manifested_interpretation.update(cycles["life_path"])
    seven_interpretation.update(cycles["seven_year"])
    year_interpretation.update(cycles["annual"])
    week_interpretation.update(cycles["week"])
    global_interpretation.update(context)
    refresh_selected_cycle_reading()


def _display_target_date(value):
    """Show the explored date without treating it as a manual edit."""
    target_entry.delete(0, "end")
    target_entry.insert(0, value.strftime("%d/%m/%Y"))


def calculate(target_override=None, *, restoring_history=False):
    """Capture a request on Tk; calculate off-thread; commit only the latest one."""
    global current_target_date, auto_calculate_job, navigation_dirty, navigation_restore
    record_navigation()
    navigation_dirty = True
    if not restoring_history:
        navigation_restore = None
    pending_cycle_cards.clear()
    if auto_calculate_job is not None:
        root.after_cancel(auto_calculate_job)
        auto_calculate_job = None
    ui_jobs.cancel()
    timeline_view.cancel_navigation()
    timeline_view.last = None  # A cancelled period job must be requested again.
    try:
        birth = parse_date(birth_entry.get())
        if target_override is not None:
            target = (
                target_override.date()
                if isinstance(target_override, datetime)
                else target_override
            )
            _display_target_date(target)
        else:
            entered_date = target_entry.get().strip()
            target = parse_date(entered_date) if entered_date else datetime.today().date()
            if not entered_date:
                _display_target_date(target)

        # Advance immediately so rapid arrow presses accumulate from the request,
        # not from the last completed (possibly older) calculation.
        current_target_date = target
        refresh_temporal_label()

        analyzed_time = target_time_entry.get().strip()
        analyzed_place = analysis_place_var.get().strip()
        if analysis_place_linked or not analyzed_place:
            analyzed_place = birth_place_entry.get().strip()
            analysis_place_var.set(analyzed_place)

        material = profile_store.reading_material(f"profile:{active_profile_id}", target.isoformat()) if active_profile_id else None
        request = (birth, target, birth_time_entry.get().strip(),
                   birth_place_entry.get().strip(), analyzed_time, analyzed_place,
                   active_profile_id, material)
        snapshot = dict(birth_date=birth.isoformat(), birth_time=request[2], birth_place=request[3],
                        target_date=target.isoformat(), target_time=analyzed_time,
                        target_place=analyzed_place, profile_id=active_profile_id,
                        place_linked=analysis_place_linked, time_linked=analysis_time_linked)
        ui_jobs.submit(
            "analysis", lambda: analysis_work.analysis(*request),
            lambda result: _apply_analysis(result, birth, target, analyzed_place, snapshot),
            _analysis_failed,
        )
    except Exception as error:
        _analysis_failed(error)


def _analysis_failed(error):
    global navigation_restore
    navigation_restore = None
    refresh_navigation_buttons()
    status_var.set(f"Analyse non mise à jour : {error}")
    messagebox.showerror("Erreur", str(error))


def _apply_analysis(result, birth, target, analyzed_place, snapshot):
    global current_reading_material
    try:
        current_reading_material = result.get("reading_material")
        state = result["state"]
        hour_state = state["hour_card"]
        hour_card_error = result["hour_error"]
        ascendant_error = result["ascendant_error"]
        ascendant_var.set(result["ascendant"])
        if state.get("joker"):
            render_joker_state(birth, target, result)
            commit_navigation(snapshot)
            return
        set_joker_mode(False)

        # Clock-style cycle dashboard.
        age_var.set(f'{state["time"]["age"]} ans')
        zodiac_var.set(zodiac_sign(birth))
        set_profile_birth_card(state["birth"]["card"])
        set_secondary_cards(state["secondary_cards"]["cards"])
        life_path = state["life_path"]
        set_clock_card("birth", life_path_card_var, life_path["card"])
        set_clock_card("year", year_card_var, state["year"].get("year_card"))
        set_clock_card("fifty", fifty_card_var, state["fifty_two_day"].get("card"))
        set_clock_card("week", week_card_var, state["week"].get("day_card"))
        if hour_state:
            set_clock_card("hour", hour_card_var, hour_state["card"])
            hour_cycle_var.set(
                f'{hour_state["time_local"]} locale\n'
                f'{hour_state["solar_time"]} solaire'
            )
        else:
            set_clock_card("hour", hour_card_var, "—")
            hour_cycle_var.set("Heure ou lieu\nà vérifier")

        life_path_cycle_var.set(
            f'{life_path["active_age_range"]}\n{fmt_date(life_path["active_start_date"])}'
        )
        year_period_rows = [
            row for row in state["year"]["rows"]
            if row.get("period_start") and row.get("period_end")
        ]
        if year_period_rows:
            year_cycle_var.set(fmt_period(
                year_period_rows[0]["period_start"],
                year_period_rows[-1]["period_end"],
            ))
        else:
            year_cycle_var.set("—")

        fw = state["fifty_two_day"]["window"]
        fifty_cycle_var.set(fmt_period(fw.get("start"), fw.get("end")))
        week_cycle_var.set(target.strftime("%d/%m/%Y"))

        birth_number = state["birth"]["card_number"]
        seven_sid = state["seven_year"]["series_id"]
        year_sid = state["year"]["series_id"]
        week_sid = state["week"]["series_id"]

        natural_rows = relative_result_rows(90, birth_number)
        manifested_rows = life_path["rows"]
        seven_rows = complete_result_rows(
            state["seven_year"]["rows"], seven_sid, birth_number
        )
        year_rows = complete_result_rows(state["year"]["rows"], year_sid, birth_number)
        week_rows = complete_result_rows(state["week"]["rows"], week_sid, birth_number)

        natural_results.update(natural_rows, "base", state["birth"]["card"])
        manifested_results.update(manifested_rows, "life_path", life_path["card"])
        seven_results.update(seven_rows, "seven_year", state["year"].get("year_card"))
        year_results.update(year_rows, "year", state["fifty_two_day"].get("card"))
        week_results.update(week_rows, "week", state["day"].get("card"))

        seven_slots = {
            slot: card.card_number
            for slot, card in engine.relative_cards(seven_sid, birth_number).items()
        }
        year_slots = {
            slot: card.card_number
            for slot, card in engine.relative_cards(year_sid, birth_number).items()
        }
        week_slots = {
            slot: card.card_number
            for slot, card in engine.relative_cards(week_sid, birth_number).items()
        }

        natural_slots = {r["slot"]: r["card_number"] for r in natural_rows}
        manifested_slots = {r["slot"]: r["card_number"] for r in manifested_rows}

        birth_card = state["birth"]["card"]
        natural_full.update(
            90, natural_slots, birth_card, display_name="Tableau 0", reference=True
        )
        manifested_full.update(
            1, manifested_slots, life_path["card"], display_name="Tableau 0.1",
            exchange=engine.positional_exchange(
                90, 1, int(life_path["card_number"])
            ),
        )
        seven_full.update(
            seven_sid, seven_slots, state["year"].get("year_card"),
            exchange=engine.positional_exchange(
                1, seven_sid, CARD_NUMBER_BY_LABEL[state["year"]["year_card"]]
            ),
        )
        year_full.update(
            year_sid, year_slots, state["fifty_two_day"].get("card"),
            exchange=engine.positional_exchange(
                1, year_sid, int(state["fifty_two_day"]["card_number"])
            ),
        )
        week_full.update(
            week_sid, week_slots, state["day"].get("card"),
            exchange=engine.positional_exchange(
                1, week_sid, int(state["day"]["card_number"])
            ),
        )

        update_interpretation_views(
            result["context"], state=state,
        )
        timeline_view.update(
            birth, target, state,
            result["clock_time"], analyzed_place,
        )
        timeline_view.set_events(
            profile_store.list_events(active_profile_id) if active_profile_id else []
        )

        status = (
            f'Calcul OK — naissance {birth.strftime("%d/%m/%Y")} | '
            f'analyse {target.strftime("%d/%m/%Y")}'
        )
        if ascendant_error:
            status += f" | Ascendant : {ascendant_error}"
        if hour_card_error:
            status += f" | Carte de l'heure : {hour_card_error}"
        status_var.set(status)
        refresh_visible_view()
        commit_navigation(snapshot)
    except Exception as e:
        _analysis_failed(e)


def navigate_clock(level, direction):
    global analysis_time_linked
    try:
        birth = parse_date(birth_entry.get())
        target = current_target_date or parse_date(target_entry.get())
        if level == "hour":
            analyzed_time = parse_birth_time(target_time_entry.get().strip())
            moved = datetime.combine(target, analyzed_time) + timedelta(hours=direction)
            _display_target_date(moved.date())
            target_time_entry.delete(0, "end")
            target_time_entry.insert(0, moved.strftime("%H:%M"))
            analysis_time_linked = False
            calculate(moved.date())
            return
        moved = engine.navigate_date(birth, target, level, direction)
        calculate(moved)
    except Exception as e:
        messagebox.showerror("Erreur", str(e))

root = tk.Tk()
root.title("Olney Engine V1.8.6 — Cycles du Biblaridion")


def resource_path(*parts):
    """Return a development or PyInstaller resource path."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


try:
    root.iconbitmap(resource_path("assets", "olney_icon.ico"))
except tk.TclError:
    pass

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = min(1360, int(screen_width * 0.86))
window_height = min(940, int(screen_height * 0.90))
window_x = max(0, (screen_width - window_width) // 2)
window_y = max(0, (screen_height - window_height) // 2)
root.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")
root.minsize(min(1050, screen_width - 40), min(720, screen_height - 60))

style = ttk.Style()
style.theme_use("clam")
style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
style.configure("Section.TLabelframe.Label", font=("Segoe UI", 11, "bold"))
style.configure("Value.TLabel", font=("Segoe UI", 11, "bold"))
style.configure("InputGroup.TLabelframe.Label", font=("Segoe UI", 9, "bold"))
style.configure("InputLabel.TLabel", font=("Segoe UI", 8, "bold"))
style.configure("Input.TEntry", padding=(7, 6))
style.configure("Calculate.TButton", font=("Segoe UI", 10, "bold"), padding=(16, 7))
style.configure("Reset.TButton", font=("Segoe UI Symbol", 8, "bold"), padding=(2, 0))
style.configure("Anchor.TLabel", font=("Segoe UI", 7, "bold"), padding=(4, 1))

main = ttk.Frame(root, padding=18)
main.pack(fill="both", expand=True)

theme_button_var = tk.StringVar(value="☀")


def _is_clock_descendant(widget):
    if "clock_tiles" not in globals():
        return False
    tile_frames = {item["frame"] for item in clock_tiles.values()}
    current = widget
    while current is not None:
        if current in tile_frames:
            return True
        current = getattr(current, "master", None)
    return False


def _configure_ttk_theme():
    bg = "#0D141C" if dark_mode else LIGHT["bg"]
    panel = "#151F29" if dark_mode else LIGHT["panel"]
    raised = "#1C2A36" if dark_mode else LIGHT["raised"]
    field = "#22313E" if dark_mode else LIGHT["field"]
    fg = "#E7EEF5" if dark_mode else LIGHT["text"]
    muted = "#AFC0CE" if dark_mode else LIGHT["muted"]
    selected = "#29465E" if dark_mode else LIGHT["selected"]

    root.configure(background=bg)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("Title.TLabel", background=bg, foreground=fg)
    style.configure("Value.TLabel", background=bg, foreground=fg)
    style.configure("TLabelframe", background=panel, foreground=fg)
    style.configure("TLabelframe.Label", background=bg, foreground=fg)
    style.configure("Section.TLabelframe", background=panel, foreground=fg)
    style.configure("Section.TLabelframe.Label", background=bg, foreground=fg)
    style.configure(
        "InputGroup.TLabelframe",
        background=bg,
        foreground=fg,
        bordercolor="#405465" if dark_mode else LIGHT["line"],
        relief="solid",
    )
    style.configure(
        "InputGroup.TLabelframe.Label",
        background=bg,
        foreground="#79B8EA" if dark_mode else LIGHT["accent"],
    )
    style.configure(
        "InputLabel.TLabel",
        background=bg,
        foreground="#AFC0CE" if dark_mode else LIGHT["muted"],
    )
    style.configure(
        "Anchor.TLabel",
        background=bg,
        foreground="#79B8EA" if dark_mode else LIGHT["accent"],
    )
    style.configure("TButton", background=raised, foreground=fg, bordercolor="#405465")
    style.map(
        "TButton",
        background=[("active", selected), ("pressed", selected)],
        foreground=[("disabled", muted)],
    )
    style.configure(
        "TEntry",
        fieldbackground=field,
        foreground=fg,
        insertcolor=fg,
        bordercolor="#405465",
    )
    style.configure(
        "Input.TEntry",
        fieldbackground=field,
        foreground=fg,
        insertcolor=fg,
        bordercolor="#587086" if dark_mode else LIGHT["line"],
        padding=(7, 6),
    )
    style.configure(
        "Calculate.TButton",
        background="#2F80ED",
        foreground="#FFFFFF",
        bordercolor="#1F67C8",
        font=("Segoe UI", 10, "bold"),
        padding=(16, 7),
    )
    style.map(
        "Calculate.TButton",
        background=[("active", "#4A93F2"), ("pressed", "#1F67C8")],
        foreground=[("disabled", "#D2D9E0")],
    )
    style.configure("TNotebook", background=bg, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=panel,
        foreground=muted,
        padding=(10, 5),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", selected), ("active", raised)],
        foreground=[("selected", fg), ("active", fg)],
    )
    style.configure("View.Toolbutton", background=raised, foreground=fg)
    style.map(
        "View.Toolbutton",
        background=[("selected", selected), ("active", selected)],
        foreground=[("selected", fg), ("active", fg)],
    )
    style.configure(
        "Theme.TButton",
        background="#FFFFFF" if dark_mode else LIGHT["accent"],
        foreground="#E3A008" if dark_mode else LIGHT["field"],
        bordercolor="#587086" if dark_mode else LIGHT["line"],
        font=("Segoe UI Symbol", 15, "bold"),
        padding=(3, 2),
        anchor="center",
    )
    style.map(
        "Theme.TButton",
        background=[
            ("active", "#FFF4C2" if dark_mode else "#8B5E27"),
            ("pressed", "#F7E7A0" if dark_mode else "#0D141C"),
        ],
        foreground=[
            ("active", "#D68A00" if dark_mode else "#FFFFFF"),
            ("pressed", "#B56F00" if dark_mode else "#FFFFFF"),
        ],
    )
    style.configure(
        "Profile.TMenubutton",
        background=raised,
        foreground=fg,
        bordercolor="#587086" if dark_mode else LIGHT["line"],
        font=("Segoe UI Symbol", 10, "bold"),
        padding=(9, 5),
    )
    style.map(
        "Profile.TMenubutton",
        background=[("active", selected), ("pressed", selected)],
        foreground=[("active", fg), ("pressed", fg)],
    )
    style.configure(
        "Olney.TButton",
        background="#197A58" if dark_mode else LIGHT["green_soft"],
        foreground="#FFFFFF" if dark_mode else LIGHT["green"],
        bordercolor="#48B98E" if dark_mode else LIGHT["green"],
        font=("Segoe UI Symbol", 10, "bold"),
        padding=(11, 5),
    )
    style.map(
        "Olney.TButton",
        background=[
            ("active", "#24936C" if dark_mode else "#C8EAD8"),
            ("pressed", "#126347" if dark_mode else "#AEDDC5"),
        ],
        foreground=[("active", "#FFFFFF" if dark_mode else "#124D37")],
    )
    style.configure(
        "Treeview",
        background=raised,
        fieldbackground=raised,
        foreground=fg,
    )
    style.configure("Treeview.Heading", background=panel, foreground=fg)


def _configure_tk_widget(widget):
    # Interpretation surfaces own their palette. Recolouring their descendants
    # here before rebuilding them caused intermediate flashes and duplicate work.
    if getattr(widget, "_olney_owns_theme", False):
        return
    result_bg = "#101922" if dark_mode else LIGHT["selected"]
    soft_bg = "#17232F" if dark_mode else LIGHT["raised"]
    clock_bg = "#151F29" if dark_mode else LIGHT["gold_soft"]
    planet_bg = "#24384A" if dark_mode else LIGHT["accent_soft"]
    panel_bg = "#18232E" if dark_mode else LIGHT["panel"]
    text = "#E7EEF5" if dark_mode else LIGHT["text"]
    muted = "#AFC0CE" if dark_mode else LIGHT["muted"]

    try:
        current_bg = str(widget.cget("background")).upper()
    except (tk.TclError, AttributeError):
        current_bg = ""

    result_colors = {"#DCE8F2", "#101922", LIGHT["selected"]}
    soft_colors = {"#EEF4FA", "#17232F", LIGHT["raised"]}
    clock_colors = {"#EEF3F7", "#151F29", LIGHT["gold_soft"]}
    planet_colors = {"#DCE8F5", "#24384A", LIGHT["accent_soft"]}
    panel_colors = {"#FFFFFF", "#18232E", LIGHT["panel"]}

    try:
        if current_bg in result_colors:
            widget.configure(background=result_bg)
            if isinstance(widget, tk.Label):
                widget.configure(foreground=muted)
        elif current_bg in soft_colors:
            widget.configure(background=soft_bg)
            if isinstance(widget, (tk.Label, tk.LabelFrame)):
                widget.configure(foreground=muted)
        elif current_bg in clock_colors:
            widget.configure(background=clock_bg)
            if isinstance(widget, tk.LabelFrame):
                widget.configure(foreground=text)
        elif current_bg in planet_colors:
            widget.configure(background=planet_bg)
            if isinstance(widget, tk.Label):
                widget.configure(foreground=text)
        elif current_bg in panel_colors and isinstance(widget, (tk.Frame, tk.LabelFrame)):
            widget.configure(background=panel_bg)
            if isinstance(widget, tk.LabelFrame):
                widget.configure(foreground=text)
        elif current_bg in panel_colors and isinstance(widget, tk.Label) and _is_clock_descendant(widget):
            widget.configure(background=panel_bg)
            widget.configure(foreground=text if dark_mode else muted)
        elif current_bg in {"#F5F7FA", "#24313D"} and isinstance(widget, tk.Button):
            widget.configure(background="#24313D" if dark_mode else "#F5F7FA")
    except tk.TclError:
        pass

    for child in widget.winfo_children():
        _configure_tk_widget(child)


def apply_theme():
    _configure_ttk_theme()
    _configure_tk_widget(root)

    place_suggestion_list.configure(
        background="#22313E" if dark_mode else LIGHT["field"],
        foreground="#E7EEF5" if dark_mode else LIGHT["text"],
        selectbackground="#35536B" if dark_mode else LIGHT["selected"],
        selectforeground="#FFFFFF" if dark_mode else LIGHT["text"],
    )
    clock_variables = {
        "birth": life_path_card_var,
        "year": year_card_var,
        "fifty": fifty_card_var,
        "week": week_card_var,
        "hour": hour_card_var,
    }
    for key, variable in clock_variables.items():
        set_clock_card(key, variable, variable.get())

    for view_name in ("natural_full", "manifested_full", "seven_full", "year_full", "week_full"):
        view = globals().get(view_name)
        if view:
            border = "#18232E" if dark_mode else LIGHT["panel"]
            for label in view.card_labels.values():
                if str(label.cget("highlightbackground")).upper() != "#E00000":
                    label.configure(highlightbackground=border, highlightcolor=border)

    for view_name in (
        "natural_interpretation",
        "manifested_interpretation",
        "seven_interpretation",
        "year_interpretation",
        "week_interpretation",
        "global_interpretation",
        "manifested_cycle_reading",
        "seven_cycle_reading",
        "year_cycle_reading",
        "week_cycle_reading",
        "birth_portrait", "secondary_portrait", "second_secondary_portrait",
        "timeline_view",
        "natural_results", "manifested_results", "seven_results", "year_results", "week_results",
    ):
        view = globals().get(view_name)
        if view:
            view.apply_theme()

    theme_button_var.set("☀" if dark_mode else "☾")
    if "profile_menu" in globals():
        _refresh_profile_menu()
    if "event_menu" in globals():
        _refresh_event_menu()
    if "relationship_menu" in globals():
        _refresh_relationship_menu()
    if "notebook" in globals():
        update_clock_tab_highlight()
    page_theme = globals().get("profiles_page_apply_theme")
    if page_theme:
        page_theme()
    event_theme = globals().get("events_page_apply_theme")
    if event_theme:
        event_theme()
    relationship_theme = globals().get("relationships_page_apply_theme")
    if relationship_theme:
        relationship_theme()
    chat_theme = globals().get("chat_page_apply_theme")
    if chat_theme:
        chat_theme()
    if "clock_heading_title" in globals():
        clock_heading_title.configure(foreground="#E7EEF5" if dark_mode else LIGHT["accent"])
    refresh_visible_view()


def toggle_dark_mode():
    global dark_mode
    dark_mode = not dark_mode
    apply_theme()


top_bar = ttk.Frame(main)
top_bar.pack(fill="x")
title_group = ttk.Frame(top_bar)
title_group.pack(side="left", anchor="w")
ttk.Label(title_group, text="OLNEY ENGINE V1.8.6", style="Title.TLabel").pack(anchor="w")
ttk.Label(
    title_group,
    text="Interface de calcul des cycles du Biblaridion.",
    font=("Segoe UI", 10)
).pack(anchor="w")
navigation_controls = ttk.Frame(top_bar)
navigation_controls.pack(side="left", anchor="center", padx=(20, 0))
back_button = ttk.Button(navigation_controls, text="← Retour", width=10,
                         command=lambda: navigate_history(-1), state="disabled")
back_button.pack(side="left", padx=(0, 5))
forward_button = ttk.Button(navigation_controls, text="Suivant →", width=10,
                            command=lambda: navigate_history(1), state="disabled")
forward_button.pack(side="left")
theme_button = ttk.Button(
    top_bar,
    textvariable=theme_button_var,
    command=toggle_dark_mode,
    width=3,
    style="Theme.TButton",
)
theme_button.pack(side="right", anchor="ne", pady=(3, 0))
olney_button = ttk.Button(
    top_bar,
    text="✦ EMMETT",
    command=lambda: manage_chat(),
    style="Olney.TButton",
)
olney_button.pack(side="right", anchor="ne", padx=(0, 8), pady=(3, 0))
profile_button_var = tk.StringVar(value="👤 Aucun profil")
profile_menu = tk.Menu(root, tearoff=False)
profile_button = ttk.Menubutton(
    top_bar,
    textvariable=profile_button_var,
    menu=profile_menu,
    style="Profile.TMenubutton",
)
event_button_var = tk.StringVar(value="◆ ÉVÉNEMENTS")
event_menu = tk.Menu(root, tearoff=False)
events_button = ttk.Menubutton(
    top_bar,
    textvariable=event_button_var,
    menu=event_menu,
    style="Profile.TMenubutton",
)
relationship_button_var = tk.StringVar(value="∞ RELATIONS")
relationship_menu = tk.Menu(root, tearoff=False)
relationships_button = ttk.Menubutton(
    top_bar,
    textvariable=relationship_button_var,
    menu=relationship_menu,
    style="Profile.TMenubutton",
)
relationships_button.pack(side="right", anchor="ne", padx=(0, 8), pady=(3, 0))
events_button.pack(side="right", anchor="ne", padx=(0, 8), pady=(3, 0))
profile_button.pack(side="right", anchor="ne", padx=(0, 8), pady=(3, 0))
ttk.Frame(main, height=12).pack()

# Dashboard variables
age_var = tk.StringVar(value="— ans")
zodiac_var = tk.StringVar(value="—")
ascendant_var = tk.StringVar(value="—")
birth_card_var = tk.StringVar(value="—")
life_path_card_var = tk.StringVar(value="—")
year_card_var = tk.StringVar(value="—")
fifty_card_var = tk.StringVar(value="—")
week_card_var = tk.StringVar(value="—")
hour_card_var = tk.StringVar(value="—")
life_path_cycle_var = tk.StringVar(value="Renseigne les dates")
year_cycle_var = tk.StringVar(value="—")
fifty_cycle_var = tk.StringVar(value="—")
week_cycle_var = tk.StringVar(value="—")
hour_cycle_var = tk.StringVar(value="Renseigne l'heure")
clock_card_labels = {}
clock_tiles = {}

# Inputs
input_frame = ttk.Frame(main)
input_frame.pack(fill="x")
input_frame.columnconfigure(2, weight=1)

birth_group = ttk.LabelFrame(
    input_frame,
    text="  NAISSANCE  ",
    style="InputGroup.TLabelframe",
    padding=(11, 8),
)
birth_group.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

ttk.Label(
    birth_group, text="DATE DE NAISSANCE", style="InputLabel.TLabel"
).grid(row=0, column=0, sticky="w")
birth_entry = ttk.Entry(
    birth_group, width=12, font=("Segoe UI", 11), style="Input.TEntry"
)
birth_entry.grid(row=1, column=0, padx=(0, 10), pady=(4, 0))
birth_entry.insert(0, "18/05/1965")

ttk.Label(birth_group, text="HEURE", style="InputLabel.TLabel").grid(
    row=0, column=1, sticky="w"
)
birth_time_entry = ttk.Entry(
    birth_group, width=6, font=("Segoe UI", 11), style="Input.TEntry"
)
birth_time_entry.grid(row=1, column=1, padx=(0, 10), pady=(4, 0))
birth_time_entry.insert(0, "00:00")

ttk.Label(birth_group, text="VILLE", style="InputLabel.TLabel").grid(
    row=0, column=2, sticky="w"
)
birth_place_entry = ttk.Entry(
    birth_group, width=14, font=("Segoe UI", 11), style="Input.TEntry"
)
birth_place_entry.grid(row=1, column=2, pady=(4, 0))

analysis_group = ttk.LabelFrame(
    input_frame,
    text="  ANALYSE (Aujourd’hui)  ",
    style="InputGroup.TLabelframe",
    padding=(11, 8),
)
analysis_group.grid(row=0, column=1, sticky="nsew", padx=(0, 8))

analysis_date_heading = tk.StringVar(value="DATE ANALYSÉE")
ttk.Label(
    analysis_group, textvariable=analysis_date_heading, style="InputLabel.TLabel", font=("Segoe UI", 8, "bold")
).grid(row=0, column=0, sticky="w")
target_entry = ttk.Entry(
    analysis_group, width=12, font=("Segoe UI", 11), style="Input.TEntry"
)
target_entry.grid(row=1, column=0, padx=(0, 10), pady=(4, 0))
target_entry.insert(0, datetime.today().strftime("%d/%m/%Y"))

ttk.Label(analysis_group, text="HEURE", style="InputLabel.TLabel").grid(
    row=0, column=1, sticky="w"
)
target_time_entry = ttk.Entry(
    analysis_group, width=6, font=("Segoe UI", 11), style="Input.TEntry"
)
target_time_entry.grid(row=1, column=1, padx=(0, 8), pady=(4, 0))
target_time_entry.insert(0, datetime.now().strftime("%H:%M"))

ttk.Label(analysis_group, text="LIEU", style="InputLabel.TLabel").grid(
    row=0, column=2, sticky="w"
)
analysis_place_var = tk.StringVar(value="")
analysis_place_button = ttk.Button(
    analysis_group,
    text="📍",
    width=3,
    command=lambda: open_analysis_place_dialog(),
)
analysis_place_button.grid(row=1, column=2, padx=(0, 8), pady=(4, 0), sticky="nw")

calculate_button = ttk.Button(
    analysis_group,
    text="CALCULER  ›",
    command=calculate,
    style="Calculate.TButton",
)
calculate_button.grid(row=1, column=3, pady=(4, 0), sticky="w")
analysis_anchor_frame = ttk.Frame(analysis_group)
analysis_anchor_frame.place(relx=1.0, x=-4, y=1, anchor="ne")
reset_today_label = ttk.Label(analysis_anchor_frame, text="Aujourd’hui", style="Anchor.TLabel")
reset_today_label.pack(side="left", padx=(0, 5))
reset_origin_button = ttk.Button(
    analysis_anchor_frame,
    text="↺",
    width=2,
    command=lambda: reset_to_origin(),
    style="Reset.TButton",
)
reset_origin_button.pack(side="left")

reset_tooltip = None


def show_reset_tooltip(_event=None):
    global reset_tooltip
    if reset_tooltip is not None:
        return
    reset_tooltip = tk.Toplevel(root)
    reset_tooltip.wm_overrideredirect(True)
    reset_tooltip.geometry(
        f"+{reset_origin_button.winfo_rootx() - 100}"
        f"+{reset_origin_button.winfo_rooty() + reset_origin_button.winfo_height() + 4}"
    )
    ttk.Label(reset_tooltip, text="Revenir à maintenant", padding=6).pack()


def hide_reset_tooltip(_event=None):
    global reset_tooltip
    if reset_tooltip is not None:
        reset_tooltip.destroy()
        reset_tooltip = None


reset_origin_button.bind("<Enter>", show_reset_tooltip)
reset_origin_button.bind("<Leave>", hide_reset_tooltip)
reset_origin_button.bind("<Button-1>", hide_reset_tooltip)

age_badge = tk.Frame(
    input_frame,
    background="#173F5F",
    highlightthickness=1,
    highlightbackground="#0F2C43",
    padx=7,
    pady=7,
)
age_badge.grid(row=0, column=2, padx=(0, 0), sticky="nsew")


def prepare_profile_part(part):
    """Create a shared centered two-row layout for every profile value."""
    part.columnconfigure(0, weight=1)
    part.rowconfigure(0, weight=1)
    part.rowconfigure(1, minsize=16)
    part.rowconfigure(2, minsize=42)
    part.rowconfigure(3, weight=1)


age_part = tk.Frame(age_badge, background="#173F5F")
age_part.pack(side="left", fill="both", expand=True, padx=(0, 4))
prepare_profile_part(age_part)
tk.Label(
    age_part,
    text="ÂGE ANALYSÉ",
    background="#173F5F",
    foreground="#BFD7EA",
    font=("Segoe UI", 7, "bold"),
).grid(row=1, column=0, sticky="s")
tk.Label(
    age_part,
    textvariable=age_var,
    background="#173F5F",
    foreground="#FFFFFF",
    font=("Segoe UI", 21, "bold"),
).grid(row=2, column=0, sticky="n")

tk.Frame(age_badge, background="#5B7890", width=1).pack(side="left", fill="y", pady=2)

birth_card_part = tk.Frame(age_badge, background="#173F5F")
birth_card_part.pack(side="left", fill="both", expand=True, padx=(5, 7))
prepare_profile_part(birth_card_part)
tk.Label(
    birth_card_part,
    text="NAISSANCE",
    background="#173F5F",
    foreground="#BFD7EA",
    font=("Segoe UI", 7, "bold"),
).grid(row=1, column=0, sticky="s")
birth_profile_card_label = tk.Label(
    birth_card_part,
    textvariable=birth_card_var,
    background="#173F5F",
    foreground="#FFFFFF",
    font=("Segoe UI Symbol", 20, "bold"),
)
birth_profile_card_label.grid(row=2, column=0, sticky="n")

tk.Frame(age_badge, background="#5B7890", width=1).pack(side="left", fill="y", pady=2)

secondary_part = tk.Frame(age_badge, background="#173F5F")
secondary_part.pack(side="left", fill="both", expand=True, padx=(6, 7))
prepare_profile_part(secondary_part)
tk.Label(
    secondary_part,
    text="SECONDAIRES",
    background="#173F5F",
    foreground="#BFD7EA",
    font=("Segoe UI", 7, "bold"),
).grid(row=1, column=0, sticky="s")
secondary_cards_holder = tk.Frame(secondary_part, background="#173F5F")
secondary_cards_holder.grid(row=2, column=0, sticky="n", pady=(2, 0))
set_secondary_cards([])

tk.Frame(age_badge, background="#5B7890", width=1).pack(side="left", fill="y", pady=2)

zodiac_part = tk.Frame(age_badge, background="#173F5F")
zodiac_part.pack(side="left", fill="both", expand=True, padx=(7, 7))
prepare_profile_part(zodiac_part)
tk.Label(
    zodiac_part,
    text="SIGNE",
    background="#173F5F",
    foreground="#BFD7EA",
    font=("Segoe UI", 7, "bold"),
).grid(row=1, column=0, sticky="s")
tk.Label(
    zodiac_part,
    textvariable=zodiac_var,
    background="#173F5F",
    foreground="#FFFFFF",
    font=("Segoe UI Symbol", 13, "bold"),
).grid(row=2, column=0, sticky="n", pady=(2, 0))

tk.Frame(age_badge, background="#5B7890", width=1).pack(side="left", fill="y", pady=2)

ascendant_part = tk.Frame(age_badge, background="#173F5F")
ascendant_part.pack(side="left", fill="both", expand=True, padx=(7, 0))
prepare_profile_part(ascendant_part)
tk.Label(
    ascendant_part,
    text="ASCENDANT",
    background="#173F5F",
    foreground="#BFD7EA",
    font=("Segoe UI", 7, "bold"),
).grid(row=1, column=0, sticky="s")
tk.Label(
    ascendant_part,
    textvariable=ascendant_var,
    background="#173F5F",
    foreground="#FFFFFF",
    font=("Segoe UI Symbol", 12, "bold"),
).grid(row=2, column=0, sticky="n", pady=(2, 0))

root.bind("<Return>", lambda event: calculate())

auto_calculate_job = None


def schedule_auto_calculate(_event=None):
    """Recalculate once both edited date fields contain complete valid dates."""
    global auto_calculate_job, navigation_dirty, navigation_restore
    record_navigation()
    navigation_dirty = True
    navigation_restore = None
    # An edited, not yet validated field invalidates older background results.
    ui_jobs.cancel()
    timeline_view.cancel_navigation()
    timeline_view.last = None
    if auto_calculate_job is not None:
        root.after_cancel(auto_calculate_job)

    def run_if_valid():
        global auto_calculate_job
        auto_calculate_job = None
        try:
            birth = parse_date(birth_entry.get())
            parse_date(target_entry.get())
            time_text = birth_time_entry.get().strip()
            analyzed_time = target_time_entry.get().strip()
            place_text = birth_place_entry.get().strip()
            if time_text:
                parse_birth_time(time_text)
            if analyzed_time:
                parse_birth_time(analyzed_time)
            if time_text and place_text:
                resolve_place(place_text)
        except Exception:
            return
        calculate()

    auto_calculate_job = root.after(450, run_if_valid)


def mark_target_date_edited(_event=None):
    schedule_auto_calculate()


def mark_profile_dirty(_event=None):
    """Detach edited birth data from any immutable saved profile."""
    global profile_dirty, active_profile_id
    if active_profile_id is not None:
        active_profile_id = None
        profile_store.set_last_profile_id(None)
    profile_dirty = False
    if "_refresh_profile_menu" in globals():
        _refresh_profile_menu()


def mark_profile_dirty_and_schedule(_event=None):
    mark_profile_dirty()
    schedule_auto_calculate()


def mark_analysis_time_edited(_event=None):
    global analysis_time_linked
    analysis_time_linked = False
    schedule_auto_calculate()


def _format_masked_entry(entry, group_lengths, separator):
    """Keep only digits and add date/time separators while preserving the cursor."""
    current = entry.get()
    cursor = entry.index("insert")
    digits_before_cursor = sum(char.isdigit() for char in current[:cursor])
    maximum = sum(group_lengths)
    digits = "".join(char for char in current if char.isdigit())[:maximum]

    chunks = []
    consumed = 0
    for index, length in enumerate(group_lengths):
        chunk = digits[consumed:consumed + length]
        if not chunk:
            break
        chunks.append(chunk)
        consumed += len(chunk)
        if len(chunk) < length:
            break
        if index < len(group_lengths) - 1:
            chunks.append(separator)
    formatted = "".join(chunks)

    entry.delete(0, "end")
    entry.insert(0, formatted)

    if digits_before_cursor <= 0:
        new_cursor = 0
    else:
        seen = 0
        new_cursor = len(formatted)
        for index, char in enumerate(formatted):
            if char.isdigit():
                seen += 1
            if seen == digits_before_cursor:
                new_cursor = index + 1
                if (
                    new_cursor < len(formatted)
                    and formatted[new_cursor] == separator
                ):
                    new_cursor += 1
                break
    entry.icursor(min(new_cursor, len(formatted)))


def _skip_separator_on_delete(entry, separator, event):
    """Make Backspace/Delete cross an automatic separator in one keystroke."""
    if entry.selection_present():
        return
    cursor = entry.index("insert")
    value = entry.get()
    if event.keysym == "BackSpace" and cursor > 0 and value[cursor - 1] == separator:
        entry.icursor(cursor - 1)
    elif event.keysym == "Delete" and cursor < len(value) and value[cursor] == separator:
        entry.icursor(cursor + 1)


def bind_masked_entry(
    entry, group_lengths, separator, callback, next_widget=None
):
    def on_key_press(event):
        _skip_separator_on_delete(entry, separator, event)

    def on_key_release(event):
        if event.keysym not in (
            "Left", "Right", "Home", "End", "Up", "Down",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
        ):
            _format_masked_entry(entry, group_lengths, separator)
            callback(event)
            digit_count = sum(char.isdigit() for char in entry.get())
            if (
                next_widget is not None
                and digit_count == sum(group_lengths)
                and bool(event.char)
                and event.char.isdigit()
            ):
                root.after_idle(next_widget.focus_set)

    entry.bind("<KeyPress>", on_key_press)
    entry.bind("<KeyRelease>", on_key_release)


def bind_select_all_on_focus(entry):
    """Select the complete value on keyboard focus or mouse click."""
    def select_all(_event=None):
        def apply_selection():
            if entry.winfo_exists():
                entry.selection_range(0, "end")
                entry.icursor("end")

        entry.after_idle(apply_selection)

    entry.bind("<FocusIn>", select_all, add="+")
    entry.bind("<ButtonRelease-1>", select_all, add="+")


def reset_to_origin():
    """Return to now, preserving the selected profile and analysis place."""
    global analysis_time_linked, current_target_date
    now = datetime.now()
    target = now.date()
    _display_target_date(target)
    target_time_entry.delete(0, "end")
    target_time_entry.insert(0, now.strftime("%H:%M"))
    analysis_time_linked = False
    current_target_date = target
    calculate(target)


bind_masked_entry(
    birth_entry, (2, 2, 4), "/", mark_profile_dirty_and_schedule, birth_time_entry
)
bind_masked_entry(
    birth_time_entry, (2, 2), ":", mark_profile_dirty_and_schedule, birth_place_entry
)
bind_masked_entry(
    target_entry, (2, 2, 4), "/", mark_target_date_edited, target_time_entry
)
bind_masked_entry(
    target_time_entry, (2, 2), ":", mark_analysis_time_edited, calculate_button
)
for selectable_entry in (
    birth_entry,
    birth_time_entry,
    birth_place_entry,
    target_entry,
    target_time_entry,
):
    bind_select_all_on_focus(selectable_entry)

place_suggestion_popup = tk.Toplevel(root)
place_suggestion_popup.withdraw()
place_suggestion_popup.overrideredirect(True)
place_suggestion_popup.transient(root)
place_suggestion_list = tk.Listbox(
    place_suggestion_popup,
    font=("Segoe UI", 10),
    background="#FFFFFF",
    foreground="#173F5F",
    selectbackground="#DCE8F2",
    selectforeground="#111827",
    relief="solid",
    borderwidth=1,
    activestyle="none",
    exportselection=False,
)
place_suggestion_list.pack(fill="both", expand=True)


def hide_place_suggestions():
    place_suggestion_popup.withdraw()


def select_place_suggestion(_event=None):
    selection = place_suggestion_list.curselection()
    if not selection and place_suggestion_list.size():
        selection = (0,)
    if not selection:
        value = birth_place_entry.get().strip()
        if not value:
            return "break"
        if analysis_place_linked:
            analysis_place_var.set(value)
        hide_place_suggestions()
        target_entry.focus_set()
        schedule_auto_calculate()
        return "break"

    value = place_suggestion_list.get(selection[0])
    birth_place_entry.delete(0, "end")
    birth_place_entry.insert(0, value)
    mark_profile_dirty()
    if analysis_place_linked:
        analysis_place_var.set(value)
    hide_place_suggestions()
    target_entry.focus_set()
    schedule_auto_calculate()
    return "break"


def hide_place_suggestions_if_focus_left():
    focused = root.focus_get()
    if focused not in (birth_place_entry, place_suggestion_list):
        hide_place_suggestions()


def update_place_suggestions(_event=None):
    if _event is not None and _event.keysym == "Escape":
        hide_place_suggestions()
        return "break"
    if _event is not None and _event.keysym == "Down" and place_suggestion_list.size():
        place_suggestion_list.focus_set()
        place_suggestion_list.selection_clear(0, "end")
        place_suggestion_list.selection_set(0)
        place_suggestion_list.activate(0)
        return "break"
    if _event is not None and _event.keysym in ("Up", "Return", "Tab"):
        schedule_auto_calculate()
        return

    typed = birth_place_entry.get()
    suggestions = suggest_places(typed)
    place_suggestion_list.delete(0, "end")
    for suggestion in suggestions:
        place_suggestion_list.insert("end", suggestion)

    if suggestions:
        root.update_idletasks()
        x = birth_place_entry.winfo_rootx()
        y = birth_place_entry.winfo_rooty() + birth_place_entry.winfo_height()
        width = max(birth_place_entry.winfo_width(), 230)
        height = min(len(suggestions), 6) * 25 + 4
        place_suggestion_popup.geometry(f"{width}x{height}+{x}+{y}")
        place_suggestion_popup.deiconify()
        place_suggestion_popup.lift()
        birth_place_entry.focus_set()
        birth_place_entry.icursor("end")
    else:
        hide_place_suggestions()
    schedule_auto_calculate()


birth_place_entry.bind("<KeyRelease>", update_place_suggestions)
birth_place_entry.bind("<KeyRelease>", mark_profile_dirty, add="+")
birth_place_entry.bind("<Return>", select_place_suggestion)
birth_place_entry.bind(
    "<FocusOut>", lambda _event: root.after(120, hide_place_suggestions_if_focus_left)
)
place_suggestion_list.bind("<ButtonRelease-1>", select_place_suggestion)
place_suggestion_list.bind("<Return>", select_place_suggestion)
place_suggestion_list.bind(
    "<Escape>", lambda _event: (hide_place_suggestions(), birth_place_entry.focus_set(), "break")[-1]
)


def open_analysis_place_dialog():
    """Open a compact offline place picker without crowding the main form."""
    dialog = tk.Toplevel(root)
    dialog.title("Lieu analysé")
    dialog.transient(root)
    dialog.resizable(False, False)
    dialog.configure(background="#0D141C" if dark_mode else "#F0F0F0")

    width, height = 440, 315
    root.update_idletasks()
    x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
    y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 3)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    body = ttk.Frame(dialog, padding=18)
    body.pack(fill="both", expand=True)
    ttk.Label(
        body,
        text="LIEU DU MOMENT ANALYSÉ",
        style="InputLabel.TLabel",
    ).pack(anchor="w")
    ttk.Label(
        body,
        text="Utilisé uniquement pour convertir l’heure analysée en heure solaire.",
        wraplength=390,
        justify="left",
    ).pack(anchor="w", pady=(3, 10))

    initial = analysis_place_var.get().strip() or birth_place_entry.get().strip()
    draft_var = tk.StringVar(value=initial)
    place_entry = ttk.Entry(
        body, textvariable=draft_var, font=("Segoe UI", 11), style="Input.TEntry"
    )
    place_entry.pack(fill="x")

    suggestions = tk.Listbox(
        body,
        height=6,
        font=("Segoe UI", 10),
        background="#22313E" if dark_mode else "#FFFFFF",
        foreground="#E7EEF5" if dark_mode else "#173F5F",
        selectbackground="#35536B" if dark_mode else "#DCE8F2",
        selectforeground="#FFFFFF" if dark_mode else "#111827",
        relief="solid",
        borderwidth=1,
        activestyle="none",
        exportselection=False,
    )
    suggestions.pack(fill="both", expand=True, pady=(6, 10))

    def refresh_suggestions(_event=None):
        if _event is not None and _event.keysym in ("Up", "Down", "Return"):
            if _event.keysym == "Down" and suggestions.size():
                suggestions.focus_set()
                suggestions.selection_set(0)
                suggestions.activate(0)
            return
        values = suggest_places(draft_var.get())
        suggestions.delete(0, "end")
        for value in values:
            suggestions.insert("end", value)

    def choose_suggestion(_event=None):
        selection = suggestions.curselection()
        if not selection:
            return
        draft_var.set(suggestions.get(selection[0]))
        place_entry.focus_set()
        place_entry.icursor("end")

    def accept(link_to_birth=False):
        global analysis_place_linked
        raw_value = birth_place_entry.get().strip() if link_to_birth else draft_var.get().strip()
        try:
            place = resolve_place(raw_value)
        except ValueError as exc:
            messagebox.showerror("Lieu analysé", str(exc), parent=dialog)
            return
        analysis_place_var.set(f"{place.name}, {place.country_code}")
        analysis_place_linked = bool(link_to_birth)
        dialog.destroy()
        calculate()

    place_entry.bind("<KeyRelease>", refresh_suggestions)
    bind_select_all_on_focus(place_entry)
    suggestions.bind("<ButtonRelease-1>", choose_suggestion)
    suggestions.bind("<Double-Button-1>", lambda _event: accept(False))
    suggestions.bind("<Return>", lambda _event: accept(False))
    place_entry.bind("<Return>", lambda _event: accept(False))

    controls = ttk.Frame(body)
    controls.pack(fill="x")
    ttk.Button(
        controls,
        text="VILLE DE NAISSANCE",
        command=lambda: accept(True),
    ).pack(side="left")
    ttk.Button(
        controls,
        text="VALIDER",
        command=lambda: accept(False),
        style="Calculate.TButton",
    ).pack(side="right")

    refresh_suggestions()
    place_entry.focus_set()
    place_entry.icursor("end")
    dialog.grab_set()


def _ask_profile_identity(title, initial_name="", initial_last_name=""):
    """Ask for the first and last names used to identify a profile."""
    result = {"value": None}
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.transient(root)
    dialog.resizable(False, False)
    dialog.configure(background="#0D141C" if dark_mode else "#F0F0F0")
    body = ttk.Frame(dialog, padding=18)
    body.pack(fill="both", expand=True)
    identity_row = ttk.Frame(body)
    identity_row.pack(fill="x", pady=(0, 14))
    first_column = ttk.Frame(identity_row)
    first_column.pack(side="left", fill="x", expand=True, padx=(0, 8))
    ttk.Label(first_column, text="PRÉNOM", style="InputLabel.TLabel").pack(anchor="w")
    name_var = tk.StringVar(value=initial_name)
    name_entry = ttk.Entry(
        first_column, textvariable=name_var, width=20,
        font=("Segoe UI", 11), style="Input.TEntry",
    )
    name_entry.pack(fill="x", pady=(5, 0))
    last_column = ttk.Frame(identity_row)
    last_column.pack(side="left", fill="x", expand=True, padx=(0, 8))
    ttk.Label(last_column, text="NOM DE FAMILLE", style="InputLabel.TLabel").pack(anchor="w")
    last_name_var = tk.StringVar(value=initial_last_name)
    last_name_entry = ttk.Entry(
        last_column, textvariable=last_name_var, width=20,
        font=("Segoe UI", 11), style="Input.TEntry",
    )
    last_name_entry.pack(fill="x", pady=(5, 0))
    controls = ttk.Frame(body)
    controls.pack(fill="x")

    def accept(_event=None):
        first_name = name_var.get().strip()
        if not first_name:
            messagebox.showerror(title, "Donne un prénom au profil.", parent=dialog)
            return
        result["value"] = (first_name, last_name_var.get().strip())
        dialog.destroy()

    ttk.Button(controls, text="ANNULER", command=dialog.destroy).pack(side="left")
    ttk.Button(
        controls, text="VALIDER", command=accept, style="Calculate.TButton"
    ).pack(side="right")
    name_entry.bind("<Return>", lambda _event: last_name_entry.focus_set())
    last_name_entry.bind("<Return>", accept)
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.grab_set()
    dialog.update_idletasks()
    width, height = 500, 165
    x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
    y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 3)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    name_entry.focus_set()
    name_entry.selection_range(0, "end")
    root.wait_window(dialog)
    return result["value"]


def _ask_new_profile_data(initial_profile=None, title="Nouveau profil"):
    """Collect the complete birth identity when creating a profile."""
    result = {"value": None}
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.transient(root)
    dialog.resizable(False, False)
    dialog.configure(background="#0D141C" if dark_mode else "#F0F0F0")
    body = ttk.Frame(dialog, padding=18)
    body.pack(fill="both", expand=True)

    heading = "MODIFIER LE PROFIL" if initial_profile else "NOUVEAU PROFIL"
    ttk.Label(body, text=heading, font=("Segoe UI", 13, "bold")).pack(
        anchor="w", pady=(0, 12)
    )
    identity_row = ttk.Frame(body)
    identity_row.pack(fill="x")
    first_column = ttk.Frame(identity_row)
    first_column.pack(side="left", fill="x", expand=True, padx=(0, 8))
    ttk.Label(first_column, text="PRÉNOM", style="InputLabel.TLabel").pack(anchor="w")
    name_entry = ttk.Entry(first_column, font=("Segoe UI", 11), style="Input.TEntry")
    name_entry.pack(fill="x", pady=(4, 10))
    last_column = ttk.Frame(identity_row)
    last_column.pack(side="left", fill="x", expand=True)
    ttk.Label(last_column, text="NOM DE FAMILLE", style="InputLabel.TLabel").pack(anchor="w")
    last_name_entry = ttk.Entry(last_column, font=("Segoe UI", 11), style="Input.TEntry")
    last_name_entry.pack(fill="x", pady=(4, 10))
    if initial_profile:
        name_entry.insert(0, initial_profile["name"])
        last_name_entry.insert(0, initial_profile.get("last_name", ""))
    type_column = ttk.Frame(identity_row)
    type_column.pack(side="left", fill="x", expand=True)
    ttk.Label(type_column, text="TYPE", style="InputLabel.TLabel").pack(anchor="w")
    type_var = tk.StringVar(
        value=initial_profile.get("profile_type", "Humain") if initial_profile else "Humain"
    )
    type_box = ttk.Combobox(
        type_column, textvariable=type_var, values=PROFILE_TYPES,
        state="readonly", font=("Segoe UI", 10), width=14,
    )
    type_box.pack(fill="x", pady=(4, 10))

    birth_row = ttk.Frame(body)
    birth_row.pack(fill="x")
    date_column = ttk.Frame(birth_row)
    date_column.pack(side="left", fill="x", expand=True, padx=(0, 8))
    ttk.Label(date_column, text="DATE DE NAISSANCE", style="InputLabel.TLabel").pack(
        anchor="w"
    )
    date_entry = ttk.Entry(date_column, font=("Segoe UI", 11), style="Input.TEntry")
    date_entry.pack(fill="x", pady=(4, 10))
    initial_date = (
        datetime.fromisoformat(initial_profile["birth_date"]).strftime("%d/%m/%Y")
        if initial_profile else birth_entry.get().strip()
    )
    date_entry.insert(0, initial_date)

    time_column = ttk.Frame(birth_row)
    time_column.pack(side="left", fill="x")
    ttk.Label(time_column, text="HEURE", style="InputLabel.TLabel").pack(anchor="w")
    time_entry = ttk.Entry(
        time_column, width=8, font=("Segoe UI", 11), style="Input.TEntry"
    )
    time_entry.pack(fill="x", pady=(4, 10))
    initial_time = initial_profile["birth_time"] if initial_profile else birth_time_entry.get().strip()
    time_entry.insert(0, initial_time or "00:00")

    ttk.Label(body, text="VILLE", style="InputLabel.TLabel").pack(anchor="w")
    place_entry = ttk.Entry(body, font=("Segoe UI", 11), style="Input.TEntry")
    place_entry.pack(fill="x", pady=(4, 5))
    initial_place = initial_profile["birth_place"] if initial_profile else birth_place_entry.get().strip()
    place_entry.insert(0, initial_place)
    suggestions = tk.Listbox(
        body,
        height=4,
        font=("Segoe UI", 10),
        background="#22313E" if dark_mode else "#FFFFFF",
        foreground="#E7EEF5" if dark_mode else "#173F5F",
        selectbackground="#35536B" if dark_mode else "#DCE8F2",
        selectforeground="#FFFFFF" if dark_mode else "#111827",
        relief="solid", borderwidth=1, activestyle="none", exportselection=False,
    )
    suggestions.pack(fill="both", expand=True, pady=(0, 12))

    def refresh_suggestions(_event=None):
        if _event is not None and _event.keysym in ("Up", "Down", "Return"):
            if _event.keysym == "Down" and suggestions.size():
                suggestions.focus_set()
                suggestions.selection_set(0)
                suggestions.activate(0)
            return
        suggestions.delete(0, "end")
        for value in suggest_places(place_entry.get()):
            suggestions.insert("end", value)

    def choose_suggestion(_event=None):
        selection = suggestions.curselection()
        if not selection:
            return
        place_entry.delete(0, "end")
        place_entry.insert(0, suggestions.get(selection[0]))
        place_entry.focus_set()
        place_entry.icursor("end")

    def accept(_event=None):
        try:
            birth = parse_date(date_entry.get())
            birth_time = parse_birth_time(time_entry.get().strip())
            place = resolve_place(place_entry.get().strip())
            name = name_entry.get().strip()
            if not name:
                raise ValueError("Donne un prénom au profil.")
        except ValueError as exc:
            messagebox.showerror(title, str(exc), parent=dialog)
            return
        result["value"] = {
            "name": name,
            "last_name": last_name_entry.get().strip(),
            "profile_type": type_var.get(),
            "birth_date": birth.isoformat(),
            "birth_time": birth_time.strftime("%H:%M"),
            "birth_place": f"{place.name}, {place.country_code}",
            "latitude": place.latitude,
            "longitude": place.longitude,
            "timezone": place.timezone,
            "country_code": place.country_code,
            "notes": "",
        }
        dialog.destroy()

    bind_masked_entry(date_entry, (2, 2, 4), "/", lambda _event=None: None, time_entry)
    bind_masked_entry(time_entry, (2, 2), ":", lambda _event=None: None, place_entry)
    bind_select_all_on_focus(name_entry)
    bind_select_all_on_focus(last_name_entry)
    bind_select_all_on_focus(date_entry)
    bind_select_all_on_focus(time_entry)
    bind_select_all_on_focus(place_entry)
    def focus_date(_event=None):
        date_entry.focus_set()
        date_entry.after_idle(lambda: date_entry.selection_range(0, "end"))
        return "break"

    type_box.bind("<Tab>", focus_date)
    place_entry.bind("<KeyRelease>", refresh_suggestions)
    place_entry.bind("<Return>", accept)
    suggestions.bind("<ButtonRelease-1>", choose_suggestion)
    suggestions.bind("<Double-Button-1>", lambda _event: accept())
    suggestions.bind("<Return>", lambda _event: accept())

    controls = ttk.Frame(body)
    controls.pack(fill="x")
    ttk.Button(controls, text="ANNULER", command=dialog.destroy).pack(side="left")
    ttk.Button(
        controls,
        text="ENREGISTRER" if initial_profile else "CRÉER LE PROFIL",
        command=accept,
        style="Calculate.TButton",
    ).pack(side="right")
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.grab_set()
    dialog.update_idletasks()
    width, height = 620, 430
    x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
    y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    refresh_suggestions()
    name_entry.focus_set()
    root.wait_window(dialog)
    return result["value"]


def _profile_payload(name, last_name=""):
    birth = parse_date(birth_entry.get())
    birth_time = parse_birth_time(birth_time_entry.get().strip())
    place = resolve_place(birth_place_entry.get().strip())
    current = profile_store.get_profile(active_profile_id) if active_profile_id else None
    return {
        "name": name.strip(),
        "last_name": last_name.strip(),
        "profile_type": current.get("profile_type", "Humain") if current else "Humain",
        "birth_date": birth.isoformat(),
        "birth_time": birth_time.strftime("%H:%M"),
        "birth_place": f"{place.name}, {place.country_code}",
        "latitude": place.latitude,
        "longitude": place.longitude,
        "timezone": place.timezone,
        "country_code": place.country_code,
        "notes": current.get("notes", "") if current else "",
    }


def _profile_display_name(profile):
    return " ".join(
        part for part in (profile.get("name", ""), profile.get("last_name", ""))
        if part
    )


def _refresh_profile_menu():
    profile = profile_store.get_profile(active_profile_id) if active_profile_id else None
    if profile:
        profile_button_var.set(f'👤 {_profile_display_name(profile)}')
    else:
        profile_button_var.set("👤 Aucun profil")

    palette_bg = "#151F29" if dark_mode else "#FFFFFF"
    palette_fg = "#E7EEF5" if dark_mode else "#111827"
    active_bg = "#29465E" if dark_mode else "#DCE8F2"
    profile_menu.configure(
        background=palette_bg,
        foreground=palette_fg,
        activebackground=active_bg,
        activeforeground=palette_fg,
    )
    profile_menu.delete(0, "end")
    profiles = profile_store.list_profiles()
    recent_profiles = profile_store.list_recent_profiles(5)
    for item in recent_profiles:
        prefix = "● " if item["id"] == active_profile_id else "   "
        profile_menu.add_command(
            label=f'{prefix}{_profile_display_name(item)}',
            command=lambda profile_id=item["id"]: open_profile_from_menu(profile_id),
        )
    if recent_profiles:
        profile_menu.add_separator()
    profile_menu.add_command(
        label=(
            f"Voir tous les profils… ({len(profiles)})"
            if len(profiles) > 5 else "Voir tous les profils…"
        ),
        command=manage_profiles,
    )
    if profiles:
        profile_menu.add_separator()
    profile_menu.add_command(label="Nouveau profil…", command=create_profile)
    profile_menu.add_command(
        label="Enregistrer…",
        command=save_active_profile,
        state="disabled" if profile else "normal",
    )


def _refresh_event_menu():
    palette_bg = "#151F29" if dark_mode else "#FFFFFF"
    palette_fg = "#E7EEF5" if dark_mode else "#111827"
    active_bg = "#29465E" if dark_mode else "#DCE8F2"
    event_menu.configure(
        background=palette_bg, foreground=palette_fg,
        activebackground=active_bg, activeforeground=palette_fg,
    )
    event_menu.delete(0, "end")
    recent = profile_store.list_recent_events(5)
    for event in recent:
        owner = " ".join(
            part for part in (
                event.get("profile_name", ""), event.get("profile_last_name", "")
            ) if part
        )
        event_menu.add_command(
            label=f'{event["title"]}  —  {owner}',
            command=lambda event_id=event["id"]: open_saved_event(event_id),
        )
    if recent:
        event_menu.add_separator()
    event_menu.add_command(label="Voir tous les événements…", command=manage_events)
    event_menu.add_separator()
    event_menu.add_command(label="Ajouter un événement…", command=add_event_from_menu)
    event_menu.add_command(
        label="Enregistrer l’analyse actuelle…",
        command=save_current_analysis_event,
        state="normal" if active_profile_id else "disabled",
    )


def _relationship_display_name(relationship):
    if relationship.get("title"):
        return relationship["title"]
    return _relationship_people_display_name(relationship)


def _relationship_people_display_name(relationship):
    first = " ".join(
        part for part in (
            relationship.get("profile_a_name", ""),
            relationship.get("profile_a_last_name", ""),
        ) if part
    )
    second = " ".join(
        part for part in (
            relationship.get("profile_b_name", ""),
            relationship.get("profile_b_last_name", ""),
        ) if part
    )
    return f"{first} × {second}"


def _relationship_search_text(relationship):
    """Search titles and both identities, even when a custom title is shown."""
    return " ".join(
        str(value or "") for value in (
            relationship.get("title"),
            relationship.get("profile_a_name"),
            relationship.get("profile_a_last_name"),
            relationship.get("profile_b_name"),
            relationship.get("profile_b_last_name"),
            relationship.get("relationship_type"),
            relationship.get("notes"),
        )
    ).casefold()


def _refresh_relationship_menu():
    palette_bg = "#151F29" if dark_mode else "#FFFFFF"
    palette_fg = "#E7EEF5" if dark_mode else "#111827"
    active_bg = "#29465E" if dark_mode else "#DCE8F2"
    relationship_menu.configure(
        background=palette_bg, foreground=palette_fg,
        activebackground=active_bg, activeforeground=palette_fg,
    )
    relationship_menu.delete(0, "end")
    recent = profile_store.list_recent_relationships(5)
    for relationship in recent:
        relationship_menu.add_command(
            label=(
                f'{"★ " if relationship.get("favorite") else ""}'
                f'{_relationship_display_name(relationship)}'
            ),
            command=lambda relation_id=relationship["id"]: manage_relationships(relation_id),
        )
    if recent:
        relationship_menu.add_separator()
    relationship_menu.add_command(
        label="Voir toutes les relations…", command=manage_relationships
    )
    relationship_menu.add_separator()
    relationship_menu.add_command(
        label="Nouvelle relation…", command=create_relationship
    )


def open_profile_from_menu(profile_id):
    if chat_page_return:
        chat_page_return()
    if relationships_page_return:
        relationships_page_return()
    if profiles_page_return:
        profiles_page_return()
    if events_page_return:
        events_page_return()
    load_profile(profile_id)


def load_profile(profile_id):
    global active_profile_id, profile_dirty, analysis_place_linked
    global analysis_time_linked, current_target_date
    profile = profile_store.get_profile(profile_id)
    if not profile:
        messagebox.showerror("Profils", "Ce profil n'existe plus.")
        _refresh_profile_menu()
        return

    birth = datetime.fromisoformat(profile["birth_date"]).date()
    for entry, value in (
        (birth_entry, birth.strftime("%d/%m/%Y")),
        (birth_time_entry, profile["birth_time"]),
        (birth_place_entry, profile["birth_place"]),
    ):
        entry.delete(0, "end")
        entry.insert(0, value)
    hide_place_suggestions()
    analysis_place_linked = True
    analysis_place_var.set(profile["birth_place"])

    now = datetime.now().replace(second=0, microsecond=0)
    _display_target_date(now.date())
    target_time_entry.delete(0, "end")
    target_time_entry.insert(0, now.strftime("%H:%M"))
    current_target_date = now.date()
    analysis_time_linked = False

    active_profile_id = profile["id"]
    profile_store.set_last_profile_id(active_profile_id)
    profile_dirty = False
    _refresh_profile_menu()
    calculate(now.date())
    status_var.set(f'Profil « {_profile_display_name(profile)} » chargé.')


def create_profile():
    global active_profile_id, profile_dirty
    data = _ask_new_profile_data()
    if not data:
        return
    try:
        profile = profile_store.create_profile(data)
    except ValueError as exc:
        messagebox.showerror("Nouveau profil", str(exc))
        return
    active_profile_id = profile["id"]
    profile_dirty = False
    load_profile(active_profile_id)
    status_var.set(f'Profil « {_profile_display_name(profile)} » créé et enregistré.')


def save_active_profile():
    global active_profile_id, profile_dirty
    if active_profile_id:
        return
    identity = _ask_profile_identity("Enregistrer le profil")
    if not identity:
        return
    name, last_name = identity
    try:
        saved = profile_store.create_profile(_profile_payload(name, last_name))
    except ValueError as exc:
        messagebox.showerror("Enregistrer le profil", str(exc))
        return
    active_profile_id = saved["id"]
    profile_dirty = False
    _refresh_profile_menu()
    status_var.set(f'Profil « {_profile_display_name(saved)} » enregistré.')


def duplicate_active_profile():
    global active_profile_id, profile_dirty
    profile = profile_store.get_profile(active_profile_id) if active_profile_id else None
    if not profile:
        return
    proposed = profile_store.available_name(f'{profile["name"]} — copie')
    identity = _ask_profile_identity(
        "Dupliquer le profil", proposed, profile.get("last_name", "")
    )
    if not identity:
        return
    name, last_name = identity
    try:
        data = {field: profile.get(field) for field in PROFILE_FIELDS}
        data["name"] = name
        data["last_name"] = last_name
        duplicate = profile_store.create_profile(data)
    except ValueError as exc:
        messagebox.showerror("Dupliquer le profil", str(exc))
        return
    active_profile_id = duplicate["id"]
    profile_dirty = False
    load_profile(active_profile_id)


def export_active_profile():
    profile = profile_store.get_profile(active_profile_id) if active_profile_id else None
    if not profile:
        return
    safe_name = "".join(
        char if char.isalnum() or char in "-_ " else "_"
        for char in _profile_display_name(profile)
    ).strip() or "profil"
    output = filedialog.asksaveasfilename(
        parent=root,
        title="Exporter le profil",
        defaultextension=".olney.json",
        initialfile=f"{safe_name}.olney.json",
        filetypes=(("Profil Olney", "*.olney.json"), ("JSON", "*.json")),
    )
    if not output:
        return
    try:
        profile_store.export_profile(active_profile_id, output)
    except (OSError, ValueError) as exc:
        messagebox.showerror("Exporter le profil", str(exc))
        return
    status_var.set(f'Profil « {_profile_display_name(profile)} » exporté.')


def import_profile():
    source = filedialog.askopenfilename(
        parent=root,
        title="Importer un profil",
        filetypes=(("Profil Olney", "*.olney.json"), ("JSON", "*.json")),
    )
    if not source:
        return
    try:
        profile = profile_store.import_profile(source)
    except (OSError, ValueError) as exc:
        messagebox.showerror("Importer un profil", str(exc))
        return
    load_profile(profile["id"])
    status_var.set(f'Profil « {_profile_display_name(profile)} » importé.')


def _profile_current_summary(profile, moment):
    """Build the compact current-time card summary shown in profile management."""
    try:
        birth = datetime.fromisoformat(profile["birth_date"]).date()
        if moment.date() < birth:
            raise ValueError
        sign = zodiac_sign(birth)
        try:
            ascendant = calculate_ascendant(
                birth, profile["birth_time"], profile["birth_place"]
            )["display_sign"]
        except (KeyError, TypeError, ValueError):
            ascendant = "—"
        state = engine.full_state(birth, moment.date())
        primary = state["birth"]["card"]
        secondary = "  ".join(
            item["card"] for item in state["secondary_cards"]["cards"]
        ) or "—"
        if state.get("joker"):
            clock = ("—", "—", "—", "—", "—")
            life_path_cards = ("—",) * 7
            challenge, result = "—", "—"
        else:
            try:
                hour = engine.hour_card(
                    moment.date(), moment.strftime("%H:%M"), profile["birth_place"]
                )["card"]
            except (KeyError, TypeError, ValueError):
                hour = "—"
            clock = (
                state["life_path"]["card"],
                state["year"]["year_card"],
                state["fifty_two_day"]["card"],
                state["week"]["day_card"],
                hour,
            )
            life_path_cards = tuple(
                row["card"]
                for row in state["life_path"]["rows"]
                if row.get("age_range")
            )
            life_path_by_slot = {
                row["slot"]: row["card"] for row in state["life_path"]["rows"]
            }
            challenge = life_path_by_slot.get("défi", "—")
            result = life_path_by_slot.get("résultat", "—")
        return (
            sign, ascendant, primary, secondary, *clock, *life_path_cards,
            challenge, result,
        )
    except (KeyError, TypeError, ValueError):
        return ("—",) * 18


EVENT_CATEGORIES = (
    "Amour", "Rencontre", "Relation", "Séparation", "Famille", "Naissance",
    "Déménagement", "Travail", "Études", "Projet", "Voyage",
    "Santé", "Décision", "Autre",
)


def _event_profile_choice(profile):
    """Unambiguous label for event ownership and participant selection."""
    try:
        birth = datetime.fromisoformat(profile["birth_date"]).strftime("%d/%m/%Y")
    except (KeyError, TypeError, ValueError):
        birth = "date inconnue"
    return f'{_profile_display_name(profile)} · {birth}'


def _event_people_display(event):
    """Combine explicit linked profiles with legacy/free-text people."""
    labels = []
    if event.get("id"):
        try:
            detailed = profile_store.reading_event(event["id"])
            labels.extend(
                " ".join(
                    part for part in (item.get("name", ""), item.get("last_name", ""))
                    if part
                )
                for item in detailed.get("participants", [])
            )
        except ValueError:
            pass
    free_text = str(event.get("people") or "").strip()
    if free_text:
        labels.append(free_text)
    return ", ".join(filter(None, labels))


def _store_event_dialog_result(dialog_result, event_id=None):
    """Persist the event, then its explicitly selected profile identities."""
    payload = dialog_result["event"]
    participants = dialog_result.get("participants", [])
    saved = (
        profile_store.update_event(event_id, payload)
        if event_id is not None else profile_store.create_event(payload)
    )
    profile_store.set_event_participants(saved["id"], participants)
    return saved


def _ask_event_data(initial_event=None):
    """Collect an event and let the user choose its owner profile."""
    profiles = profile_store.list_profiles()
    if not profiles:
        messagebox.showinfo(
            "Événements", "Crée d’abord au moins un profil."
        )
        return None

    profile_by_choice = {_event_profile_choice(item): item for item in profiles}
    initial_profile_id = (
        initial_event.get("profile_id") if initial_event else active_profile_id
    )
    initial_profile = next(
        (item for item in profiles if item["id"] == initial_profile_id), profiles[0]
    )

    event = initial_event or {}
    detailed_event = (
        profile_store.reading_event(event["id"])
        if event.get("id") else {**event, "participants": []}
    )
    is_editing = bool(event.get("id"))
    dialog = tk.Toplevel(root)
    dialog.title("Modifier l’événement" if is_editing else "Nouvel événement")
    dialog.transient(root)
    dialog.resizable(False, False)
    body = ttk.Frame(dialog, padding=18)
    body.pack(fill="both", expand=True)
    ttk.Label(
        body,
        text="MODIFIER L’ÉVÉNEMENT" if is_editing else "NOUVEL ÉVÉNEMENT",
        font=("Segoe UI", 16, "bold"),
    ).grid(row=0, column=0, columnspan=4, sticky="w")
    ttk.Label(body, text="PROFIL ASSOCIÉ", style="InputLabel.TLabel").grid(
        row=1, column=0, sticky="w", pady=(7, 2)
    )
    profile_var = tk.StringVar(value=_event_profile_choice(initial_profile))
    profile_box = ttk.Combobox(
        body, textvariable=profile_var, values=tuple(profile_by_choice),
        state="readonly", font=("Segoe UI", 10), width=27,
    )
    profile_box.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(7, 2))

    def input_label(text, row, column, columnspan=1):
        ttk.Label(body, text=text, style="InputLabel.TLabel").grid(
            row=row, column=column, columnspan=columnspan, sticky="w"
        )

    input_label("TITRE", 2, 0, 3)
    title_entry = ttk.Entry(body, width=42, font=("Segoe UI", 11), style="Input.TEntry")
    title_entry.grid(row=3, column=0, columnspan=3, sticky="ew", padx=(0, 10), pady=(4, 10))
    title_entry.insert(0, event.get("title", ""))
    input_label("CATÉGORIE", 2, 3)
    category_var = tk.StringVar(value=event.get("category") or "Autre")
    category_box = ttk.Combobox(
        body, textvariable=category_var, values=EVENT_CATEGORIES,
        state="readonly", width=17, font=("Segoe UI", 10),
    )
    category_box.grid(row=3, column=3, sticky="ew", pady=(4, 10))

    default_date = current_target_date or datetime.today().date()
    input_label("DATE", 4, 0)
    start_entry = ttk.Entry(body, width=12, font=("Segoe UI", 11), style="Input.TEntry")
    start_entry.grid(row=5, column=0, sticky="ew", padx=(0, 10), pady=(4, 10))
    start_value = event.get("date_start")
    start_entry.insert(
        0,
        datetime.fromisoformat(start_value).strftime("%d/%m/%Y")
        if start_value else default_date.strftime("%d/%m/%Y"),
    )
    input_label("HEURE", 4, 1)
    time_entry = ttk.Entry(body, width=7, font=("Segoe UI", 11), style="Input.TEntry")
    time_entry.grid(row=5, column=1, sticky="ew", padx=(0, 10), pady=(4, 10))
    time_entry.insert(0, event.get("event_time") or target_time_entry.get().strip())
    input_label("FIN (FACULTATIVE)", 4, 2)
    end_entry = ttk.Entry(body, width=12, font=("Segoe UI", 11), style="Input.TEntry")
    end_entry.grid(row=5, column=2, sticky="ew", padx=(0, 10), pady=(4, 10))
    if event.get("date_end"):
        end_entry.insert(0, datetime.fromisoformat(event["date_end"]).strftime("%d/%m/%Y"))
    input_label("IMPORTANCE", 4, 3)
    importance_var = tk.IntVar(value=int(event.get("importance") or 3))
    importance_box = ttk.Combobox(
        body, textvariable=importance_var, values=(1, 2, 3, 4, 5),
        state="readonly", width=6, font=("Segoe UI", 10),
    )
    importance_box.grid(row=5, column=3, sticky="ew", pady=(4, 10))

    input_label("LIEU (FACULTATIF)", 6, 0, 2)
    place_entry = ttk.Entry(body, font=("Segoe UI", 11), style="Input.TEntry")
    place_entry.grid(row=7, column=0, columnspan=2, sticky="ew", padx=(0, 10), pady=(4, 10))
    place_entry.insert(0, event.get("place") or analysis_place_var.get().strip())
    input_label("PERSONNES (FACULTATIF)", 6, 2, 2)
    people_block = ttk.Frame(body)
    people_block.grid(row=7, column=2, columnspan=2, sticky="nsew", pady=(4, 10))
    people_entry = ttk.Combobox(
        people_block, font=("Segoe UI", 10),
        values=tuple(profile_by_choice),
    )
    people_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
    people_block.columnconfigure(0, weight=1)
    selected_people = tk.Listbox(
        people_block, height=3, exportselection=False,
        font=("Segoe UI", 9), activestyle="none",
        background="#22313E" if dark_mode else "#FFFFFF",
        foreground="#E7EEF5" if dark_mode else "#111827",
        selectbackground="#2F80ED", selectforeground="#FFFFFF",
        relief="solid", borderwidth=1,
    )
    selected_people.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
    participant_profiles = {
        int(item["profile_id"]): next(
            profile for profile in profiles if profile["id"] == int(item["profile_id"])
        )
        for item in detailed_event.get("participants", [])
        if any(profile["id"] == int(item["profile_id"]) for profile in profiles)
    }
    free_people = [
        value.strip() for value in str(event.get("people") or "").split(",")
        if value.strip()
    ]

    def refresh_people_list():
        selected_people.delete(0, "end")
        for profile_id in participant_profiles:
            selected_people.insert(
                "end", f'PROFIL · {_profile_display_name(participant_profiles[profile_id])}'
            )
        for value in free_people:
            selected_people.insert("end", f'TEXTE · {value}')

    def add_person(_event=None):
        value = people_entry.get().strip()
        if not value:
            return "break"
        selected_profile = profile_by_choice.get(value)
        owner = profile_by_choice.get(profile_var.get())
        if selected_profile:
            if not owner or selected_profile["id"] != owner["id"]:
                participant_profiles[selected_profile["id"]] = selected_profile
        elif value.casefold() not in {item.casefold() for item in free_people}:
            free_people.append(value)
        people_entry.set("")
        refresh_people_list()
        return "break"

    def remove_person():
        selection = selected_people.curselection()
        if not selection:
            return
        index = selection[0]
        profile_ids = list(participant_profiles)
        if index < len(profile_ids):
            participant_profiles.pop(profile_ids[index], None)
        else:
            free_people.pop(index - len(profile_ids))
        refresh_people_list()

    ttk.Button(people_block, text="AJOUTER", command=add_person).grid(row=0, column=1)
    ttk.Button(people_block, text="RETIRER", command=remove_person).grid(
        row=2, column=1, sticky="e", pady=(4, 0)
    )
    people_entry.bind("<Return>", add_person)
    people_entry.bind("<<ComboboxSelected>>", add_person)
    refresh_people_list()

    input_label("MOTS-CLÉS (SÉPARÉS PAR DES VIRGULES)", 8, 0, 4)
    tags_entry = ttk.Entry(body, font=("Segoe UI", 11), style="Input.TEntry")
    tags_entry.grid(row=9, column=0, columnspan=4, sticky="ew", pady=(4, 10))
    tags_entry.insert(0, event.get("tags") or "")
    input_label("NOTES", 10, 0, 4)
    notes = tk.Text(
        body, height=5, wrap="word", font=("Segoe UI", 10),
        background="#22313E" if dark_mode else "#FFFFFF",
        foreground="#E7EEF5" if dark_mode else "#111827",
        insertbackground="#E7EEF5" if dark_mode else "#111827",
        relief="solid", borderwidth=1,
    )
    notes.grid(row=11, column=0, columnspan=4, sticky="nsew", pady=(4, 14))
    notes.insert("1.0", event.get("notes") or "")

    result = {"value": None}

    def accept(_event=None):
        try:
            selected_profile = profile_by_choice.get(profile_var.get())
            if not selected_profile:
                raise ValueError("Sélectionne le profil associé à l’événement.")
            if people_entry.get().strip():
                add_person()
            start = parse_date(start_entry.get())
            end_text = end_entry.get().strip()
            end = parse_date(end_text) if end_text else None
            time_text = time_entry.get().strip()
            if time_text:
                time_text = parse_birth_time(time_text).strftime("%H:%M")
            place_text = place_entry.get().strip()
            if place_text:
                resolved = resolve_place(place_text)
                place_text = f"{resolved.name}, {resolved.country_code}"
            payload = {
                "profile_id": selected_profile["id"],
                "title": title_entry.get().strip(),
                "category": category_var.get(),
                "date_start": start.isoformat(),
                "date_end": end.isoformat() if end else None,
                "event_time": time_text or None,
                "place": place_text or None,
                "people": ", ".join(free_people),
                "tags": tags_entry.get().strip(),
                "importance": importance_var.get(),
                "notes": notes.get("1.0", "end-1c").strip(),
            }
            # Reuse the store's canonical validation before closing the dialog.
            profile_store._clean_event(payload)
        except ValueError as exc:
            messagebox.showerror("Événement", str(exc), parent=dialog)
            return
        participants = [
            {"profile_id": profile_id, "role": "participant"}
            for profile_id in participant_profiles
            if profile_id != selected_profile["id"]
        ]
        result["value"] = {"event": payload, "participants": participants}
        dialog.destroy()

    for entry in (title_entry, start_entry, time_entry, end_entry, place_entry, people_entry, tags_entry):
        bind_select_all_on_focus(entry)
    bind_masked_entry(start_entry, (2, 2, 4), "/", lambda _event=None: None, time_entry)
    bind_masked_entry(time_entry, (2, 2), ":", lambda _event=None: None, end_entry)
    bind_masked_entry(end_entry, (2, 2, 4), "/", lambda _event=None: None, place_entry)

    controls = ttk.Frame(body)
    controls.grid(row=12, column=0, columnspan=4, sticky="ew")
    ttk.Button(controls, text="ANNULER", command=dialog.destroy).pack(side="left")
    ttk.Button(
        controls, text="ENREGISTRER", command=accept,
        style="Calculate.TButton",
    ).pack(side="right")
    for column in range(4):
        body.columnconfigure(column, weight=1)
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.grab_set()
    dialog.update_idletasks()
    width, height = 780, 700
    x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
    y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    title_entry.focus_set()
    root.wait_window(dialog)
    return result["value"]


def add_event_from_menu():
    form_result = _ask_event_data()
    if not form_result:
        return
    try:
        created = _store_event_dialog_result(form_result)
    except ValueError as exc:
        messagebox.showerror("Événement", str(exc))
        return
    _refresh_event_menu()
    status_var.set(f'Événement « {created["title"]} » enregistré.')


def save_current_analysis_event():
    if not active_profile_id:
        messagebox.showinfo("Événements", "Sélectionne d’abord un profil.")
        return
    target = current_target_date or datetime.today().date()
    form_result = _ask_event_data({
        "profile_id": active_profile_id,
        "title": f'Analyse du {target.strftime("%d/%m/%Y")}',
        "category": "Autre",
        "date_start": target.isoformat(),
        "event_time": target_time_entry.get().strip(),
        "place": analysis_place_var.get().strip(),
        "importance": 3,
    })
    if not form_result:
        return
    try:
        created = _store_event_dialog_result(form_result)
    except ValueError as exc:
        messagebox.showerror("Événement", str(exc))
        return
    _refresh_event_menu()
    status_var.set(f'Analyse enregistrée dans « {created["title"]} ».')


def open_saved_event(event_id):
    global analysis_time_linked, analysis_place_linked
    event = profile_store.get_event(event_id)
    if not event:
        messagebox.showerror("Événement", "Cet événement n’existe plus.")
        _refresh_event_menu()
        return
    if chat_page_return:
        chat_page_return()
    if events_page_return:
        events_page_return()
    if profiles_page_return:
        profiles_page_return()
    if relationships_page_return:
        relationships_page_return()
    if event["profile_id"] != active_profile_id:
        load_profile(event["profile_id"])
    selected_date = datetime.fromisoformat(event["date_start"]).date()
    _display_target_date(selected_date)
    if event.get("event_time"):
        target_time_entry.delete(0, "end")
        target_time_entry.insert(0, event["event_time"])
        analysis_time_linked = False
    if event.get("place"):
        analysis_place_var.set(event["place"])
        analysis_place_linked = False
    profile_store.touch_event(event_id)
    calculate(selected_date)
    _refresh_event_menu()
    status_var.set(
        f'Événement « {event["title"]} » — analyse du '
        f'{selected_date.strftime("%d/%m/%Y")}'
    )


RELATIONSHIP_TYPES = (
    "Amour", "Amitié", "Famille", "Professionnelle", "Créative",
    "Pédagogique", "Historique", "Autre",
)


def _ask_relationship_data(initial=None):
    profiles = profile_store.list_profiles()
    if len(profiles) < 2:
        messagebox.showinfo(
            "Relations", "Crée au moins deux profils pour étudier une relation."
        )
        return None
    profile_by_name = {_profile_display_name(item): item for item in profiles}
    relation = initial or {}
    first_default = next(
        (item for item in profiles if item["id"] == relation.get("profile_a_id")),
        next((item for item in profiles if item["id"] == active_profile_id), profiles[0]),
    )
    second_default = next(
        (item for item in profiles if item["id"] == relation.get("profile_b_id")),
        next(item for item in profiles if item["id"] != first_default["id"]),
    )

    dialog = tk.Toplevel(root)
    dialog.title("Modifier la relation" if relation.get("id") else "Nouvelle relation")
    dialog.transient(root)
    dialog.resizable(False, False)
    body = ttk.Frame(dialog, padding=20)
    body.pack(fill="both", expand=True)
    ttk.Label(
        body,
        text="MODIFIER LA RELATION" if relation.get("id") else "NOUVELLE RELATION",
        font=("Segoe UI", 16, "bold"),
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

    ttk.Label(body, text="PREMIER PROFIL", style="InputLabel.TLabel").grid(
        row=1, column=0, sticky="w"
    )
    ttk.Label(body, text="SECOND PROFIL", style="InputLabel.TLabel").grid(
        row=1, column=1, sticky="w"
    )
    first_var = tk.StringVar(value=_profile_display_name(first_default))
    second_var = tk.StringVar(value=_profile_display_name(second_default))
    first_box = ttk.Combobox(
        body, textvariable=first_var, values=tuple(profile_by_name), state="readonly",
        width=30, font=("Segoe UI", 10),
    )
    second_box = ttk.Combobox(
        body, textvariable=second_var, values=tuple(profile_by_name), state="readonly",
        width=30, font=("Segoe UI", 10),
    )
    first_box.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(4, 12))
    second_box.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(4, 12))

    ttk.Label(body, text="TYPE", style="InputLabel.TLabel").grid(row=3, column=0, sticky="w")
    ttk.Label(body, text="TITRE (FACULTATIF)", style="InputLabel.TLabel").grid(
        row=3, column=1, sticky="w"
    )
    type_var = tk.StringVar(value=relation.get("relationship_type") or "Autre")
    type_box = ttk.Combobox(
        body, textvariable=type_var, values=RELATIONSHIP_TYPES, state="readonly",
        font=("Segoe UI", 10),
    )
    type_box.grid(row=4, column=0, sticky="ew", padx=(0, 8), pady=(4, 12))
    title_entry = ttk.Entry(body, font=("Segoe UI", 10), style="Input.TEntry")
    title_entry.grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=(4, 12))
    title_entry.insert(0, relation.get("title") or "")
    bind_select_all_on_focus(title_entry)

    ttk.Label(body, text="NOTES SUR LA RELATION", style="InputLabel.TLabel").grid(
        row=5, column=0, columnspan=2, sticky="w"
    )
    notes = tk.Text(
        body, height=7, wrap="word", font=("Segoe UI", 10),
        background="#22313E" if dark_mode else "#FFFFFF",
        foreground="#E7EEF5" if dark_mode else "#111827",
        insertbackground="#E7EEF5" if dark_mode else "#111827",
        relief="solid", borderwidth=1,
    )
    notes.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(4, 16))
    notes.insert("1.0", relation.get("notes") or "")
    result = {"value": None}

    def accept():
        first = profile_by_name.get(first_var.get())
        second = profile_by_name.get(second_var.get())
        payload = {
            "profile_a_id": first["id"] if first else None,
            "profile_b_id": second["id"] if second else None,
            "relationship_type": type_var.get(),
            "title": title_entry.get().strip(),
            "notes": notes.get("1.0", "end-1c").strip(),
        }
        try:
            profile_store._clean_relationship(payload)
        except ValueError as exc:
            messagebox.showerror("Relation", str(exc), parent=dialog)
            return
        result["value"] = payload
        dialog.destroy()

    controls = ttk.Frame(body)
    controls.grid(row=7, column=0, columnspan=2, sticky="ew")
    ttk.Button(controls, text="ANNULER", command=dialog.destroy).pack(side="left")
    ttk.Button(
        controls, text="ENREGISTRER", command=accept, style="Calculate.TButton"
    ).pack(side="right")
    body.columnconfigure(0, weight=1)
    body.columnconfigure(1, weight=1)
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.grab_set()
    dialog.update_idletasks()
    width, height = 720, 500
    x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
    y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    first_box.focus_set()
    root.wait_window(dialog)
    return result["value"]


def create_relationship():
    payload = _ask_relationship_data()
    if not payload:
        return
    try:
        relation = profile_store.create_relationship(payload)
    except ValueError as exc:
        messagebox.showerror("Relation", str(exc))
        return
    _refresh_relationship_menu()
    manage_relationships(relation["id"])


def _current_chat_moment():
    """Return the date, time and place currently represented by the clock."""
    target = current_target_date or datetime.today().date()
    return {
        "date": target,
        "time": target_time_entry.get().strip() or None,
        "place": analysis_place_var.get().strip() or None,
    }


def manage_chat(initial_subject_key=None):
    """Open Emmett's full-page conversation workspace."""
    global chat_page, chat_page_apply_theme, chat_page_return
    if chat_page is not None and chat_page.winfo_exists():
        chat_page.destroy()
    for close_page in (
        profiles_page_return, events_page_return, relationships_page_return
    ):
        if close_page:
            close_page()
    for widget in (input_frame, clock, notebook, footer):
        widget.pack_forget()

    page_holder = {"widget": None}

    def return_to_clock():
        global chat_page, chat_page_apply_theme, chat_page_return
        page = page_holder["widget"]
        if page is not None and page.winfo_exists():
            page.destroy()
        chat_page = None
        chat_page_apply_theme = None
        chat_page_return = None
        input_frame.pack(fill="x")
        clock.pack(fill="x", pady=10)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        notebook.pack(side="top", fill="both", expand=True)
        apply_theme()

    if initial_subject_key is None and active_profile_id:
        initial_subject_key = f"profile:{active_profile_id}"
    page = OlneyChatView(
        main,
        store=profile_store,
        service=olney_chat_service,
        client=olney_openai_client,
        jobs=chat_jobs,
        dark_mode_getter=lambda: dark_mode,
        moment_getter=_current_chat_moment,
        on_return=return_to_clock,
        initial_subject_key=initial_subject_key,
    )
    page_holder["widget"] = page
    page.pack(fill="both", expand=True)
    chat_page = page
    chat_page_apply_theme = page.apply_theme
    chat_page_return = return_to_clock
    page.apply_theme()


def manage_relationships(relationship_id=None):
    """Open the full relationship page and its deterministic reading dossier."""
    global relationships_page, relationships_page_apply_theme, relationships_page_return
    relationships = profile_store.list_relationships()
    if not relationships:
        if len(profile_store.list_profiles()) < 2:
            messagebox.showinfo(
                "Relations", "Crée au moins deux profils pour étudier une relation."
            )
            return
        create_relationship()
        return
    if relationships_page is not None and relationships_page.winfo_exists():
        relationships_page.destroy()
    if chat_page_return:
        chat_page_return()
    if profiles_page_return:
        profiles_page_return()
    if events_page_return:
        events_page_return()
    for widget in (input_frame, clock, notebook, footer):
        widget.pack_forget()

    page = ttk.Frame(main, padding=(10, 9, 10, 5))
    page.pack(fill="both", expand=True)
    relationships_page = page

    def return_to_clock():
        global relationships_page, relationships_page_apply_theme, relationships_page_return
        if page.winfo_exists():
            page.destroy()
        relationships_page = None
        relationships_page_apply_theme = None
        relationships_page_return = None
        input_frame.pack(fill="x")
        clock.pack(fill="x", pady=10)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        notebook.pack(side="top", fill="both", expand=True)
        apply_theme()

    relationships_page_return = return_to_clock
    title_row = ttk.Frame(page)
    title_row.pack(fill="x", pady=(0, 9))
    heading = ttk.Frame(title_row)
    heading.pack(side="left", fill="x", expand=True)
    ttk.Label(heading, text="RELATIONS", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    moment = current_target_date or datetime.today().date()
    ttk.Label(
        heading,
        text=(
            f'Lecture commune au {moment.strftime("%d/%m/%Y")}  •  '
            "Ordre naturel + ordre manifesté + chemins de vie + horloges"
        ),
        style="InputLabel.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    body = ttk.Panedwindow(page, orient="horizontal")
    body.pack(fill="both", expand=True)
    sidebar = ttk.Frame(body, width=325, padding=(0, 0, 8, 0))
    detail_shell = ttk.Frame(body)
    body.add(sidebar, weight=0)
    body.add(detail_shell, weight=1)
    search_var = tk.StringVar()
    ttk.Label(sidebar, text="RECHERCHER", style="InputLabel.TLabel").pack(anchor="w")
    search = ttk.Entry(
        sidebar, textvariable=search_var, font=("Segoe UI", 10), style="Input.TEntry"
    )
    search.pack(fill="x", pady=(4, 7))
    bind_select_all_on_focus(search)
    relation_list = WrappedList(
        sidebar, exportselection=False, borderwidth=0, highlightthickness=1,
        font=("Segoe UI", 10), activestyle="none", width=315,
    )
    relation_list.pack(fill="both", expand=True)
    detail = RelationshipDetailView(
        detail_shell,
        dark_mode_getter=lambda: dark_mode,
    )
    detail.pack(fill="both", expand=True)
    visible = []
    selected = {"id": relationship_id or relationships[0]["id"]}
    favorite_var = tk.StringVar(value="☆ FAVORI")

    def highlight_search_results():
        query = search_var.get().strip().casefold()
        base_bg = "#151F29" if dark_mode else "#FFFFFF"
        base_fg = "#E7EEF5" if dark_mode else "#173F5F"
        match_bg = "#214D3B" if dark_mode else "#DDF3E7"
        match_fg = "#DDF8EA" if dark_mode else "#18573A"
        relation_list.configure(
            selectbackground=(
                match_bg if query else "#29465E" if dark_mode else "#DCE8F2"
            ),
            selectforeground=match_fg if query else "#FFFFFF" if dark_mode else "#111827",
        )
        for index, item in enumerate(visible):
            matched = bool(query and query in _relationship_search_text(item))
            relation_list.itemconfigure(
                index,
                background=match_bg if matched else base_bg,
                foreground=match_fg if matched else base_fg,
            )

    def selected_relation():
        return profile_store.get_relationship(selected["id"]) if selected["id"] else None

    def build_package(relation):
        first = profile_store.get_profile(relation["profile_a_id"])
        second = profile_store.get_profile(relation["profile_b_id"])
        target_time = target_time_entry.get().strip() or None
        target_place = analysis_place_var.get().strip() or None
        package = relationship_engine.build(
            first, second, moment, target_time=target_time,
            target_place=target_place, relationship=relation,
        )
        required_ids = {first["id"], second["id"]}
        common_events = []
        for saved_event in profile_store.list_events():
            detailed = profile_store.reading_event(saved_event["id"])
            linked_ids = {
                detailed["profile_id"],
                *(item["profile_id"] for item in detailed["participants"]),
            }
            if required_ids <= linked_ids:
                common_events.append(detailed)
        package["common_events"] = common_events
        return package

    def show_relation(relation_id, *, touch=True):
        relation = profile_store.get_relationship(relation_id)
        if not relation:
            return
        selected["id"] = relation_id
        if touch:
            profile_store.touch_relationship(relation_id)
            _refresh_relationship_menu()
        favorite_var.set(
            "★ RETIRER DES FAVORIS" if relation.get("favorite")
            else "☆ AJOUTER AUX FAVORIS"
        )
        detail.update(build_package(relation))
        for index, item in enumerate(visible):
            if item["id"] == relation_id:
                relation_list.selection_clear(0, "end")
                relation_list.selection_set(index)
                relation_list.see(index)
                break

    def refresh_list(select_id=None):
        query = search_var.get().strip().casefold()
        visible.clear()
        relation_list.delete(0, "end")
        for item in profile_store.list_relationships():
            name = _relationship_display_name(item)
            text = _relationship_search_text(item)
            if query and query not in text:
                continue
            people = _relationship_people_display_name(item)
            display_name = (
                f"{people}  ·  {name}"
                if query and item.get("title") and query in people.casefold()
                else name
            )
            visible.append(item)
            relation_list.insert(
                "end",
                f'{"★ " if item.get("favorite") else ""}{display_name}  —  '
                f'{item.get("relationship_type", "Autre")}',
            )
        highlight_search_results()
        chosen = select_id or selected["id"]
        if chosen not in {item["id"] for item in visible}:
            chosen = visible[0]["id"] if visible else None
        selected["id"] = chosen
        if chosen:
            show_relation(chosen, touch=False)
        elif not visible:
            detail.update(None)

    def on_select(_event=None):
        indices = relation_list.curselection()
        if indices:
            show_relation(visible[indices[0]]["id"])

    def new_relation():
        payload = _ask_relationship_data()
        if not payload:
            return
        try:
            relation = profile_store.create_relationship(payload)
        except ValueError as exc:
            messagebox.showerror("Relation", str(exc), parent=page)
            return
        _refresh_relationship_menu()
        refresh_list(relation["id"])

    def edit_relation():
        relation = selected_relation()
        if not relation:
            return
        payload = _ask_relationship_data(relation)
        if not payload:
            return
        try:
            updated = profile_store.update_relationship(relation["id"], payload)
        except ValueError as exc:
            messagebox.showerror("Relation", str(exc), parent=page)
            return
        _refresh_relationship_menu()
        refresh_list(updated["id"])

    def delete_relation():
        relation = selected_relation()
        if not relation:
            return
        if not messagebox.askyesno(
            "Supprimer la relation",
            f'Supprimer définitivement « {_relationship_display_name(relation)} » ?',
            parent=page,
        ):
            return
        profile_store.delete_relationship(relation["id"])
        selected["id"] = None
        _refresh_relationship_menu()
        if not profile_store.list_relationships():
            return_to_clock()
            return
        refresh_list()

    def toggle_favorite():
        relation = selected_relation()
        if not relation:
            return
        profile_store.set_relationship_favorite(
            relation["id"], not bool(relation.get("favorite"))
        )
        _refresh_relationship_menu()
        refresh_list(relation["id"])

    controls = ttk.Frame(page)
    controls.pack(fill="x", pady=(9, 0))
    ttk.Button(controls, text="SUPPRIMER", command=delete_relation).pack(side="left")
    ttk.Button(controls, text="MODIFIER", command=edit_relation).pack(side="left", padx=6)
    ttk.Button(controls, text="NOUVELLE", command=new_relation).pack(side="left")
    ttk.Button(controls, textvariable=favorite_var, command=toggle_favorite).pack(
        side="left", padx=(6, 0)
    )
    ttk.Button(
        controls, text="← RETOUR À L’HORLOGE", command=return_to_clock
    ).pack(side="right")
    relation_list.bind("<<ListboxSelect>>", on_select)
    search_var.trace_add("write", lambda *_args: refresh_list())

    def apply_relationships_theme():
        relation_list.configure(
            background="#151F29" if dark_mode else "#FFFFFF",
            foreground="#E7EEF5" if dark_mode else "#173F5F",
            selectbackground="#29465E" if dark_mode else "#DCE8F2",
            selectforeground="#FFFFFF" if dark_mode else "#111827",
            highlightbackground="#405465" if dark_mode else "#B9C7D3",
        )
        highlight_search_results()
        detail.apply_theme()

    relationships_page_apply_theme = apply_relationships_theme
    refresh_list(selected["id"])
    apply_relationships_theme()


def _manage_events_legacy():
    """Previous event list retained temporarily for database compatibility."""
    global events_page, events_page_apply_theme, events_page_return
    profile = profile_store.get_profile(active_profile_id) if active_profile_id else None
    if not profile:
        messagebox.showinfo(
            "Événements",
            "Sélectionne ou crée d’abord un profil pour gérer ses événements.",
        )
        return
    if events_page is not None and events_page.winfo_exists():
        return
    if chat_page_return:
        chat_page_return()
    if profiles_page_return:
        profiles_page_return()

    for widget in (input_frame, clock, notebook, footer):
        widget.pack_forget()
    page = ttk.Frame(main, padding=(14, 12, 14, 6))
    page.pack(fill="both", expand=True)
    events_page = page

    def return_to_clock():
        global events_page, events_page_apply_theme, events_page_return
        if page.winfo_exists():
            page.destroy()
        events_page = None
        events_page_apply_theme = None
        events_page_return = None
        input_frame.pack(fill="x")
        clock.pack(fill="x", pady=10)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        notebook.pack(side="top", fill="both", expand=True)
        apply_theme()

    events_page_return = return_to_clock
    title_row = ttk.Frame(page)
    title_row.pack(fill="x", pady=(0, 14))
    heading = ttk.Frame(title_row)
    heading.pack(side="left", fill="x", expand=True)
    ttk.Label(heading, text="ÉVÉNEMENTS", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(
        heading,
        text=(
            f'{_profile_display_name(profile)}  •  '
            "Ouvre un événement pour analyser précisément sa date"
        ),
        style="InputLabel.TLabel",
    ).pack(anchor="w", pady=(3, 0))
    search_var = tk.StringVar()
    search_group = ttk.Frame(title_row)
    search_group.pack(side="right", padx=(20, 0))
    ttk.Label(search_group, text="RECHERCHER", style="InputLabel.TLabel").pack(anchor="w")
    search_entry = ttk.Entry(
        search_group, textvariable=search_var, width=30,
        font=("Segoe UI", 11), style="Input.TEntry",
    )
    search_entry.pack(pady=(4, 0))
    bind_select_all_on_focus(search_entry)

    columns = ("start", "time", "title", "category", "period", "importance", "people", "tags")
    tree = ttk.Treeview(page, columns=columns, show="headings", selectmode="browse")
    headings = {
        "start": "DATE", "time": "HEURE", "title": "ÉVÉNEMENT",
        "category": "CATÉGORIE", "period": "FIN", "importance": "IMPORTANCE",
        "people": "PERSONNES", "tags": "MOTS-CLÉS",
    }
    widths = {
        "start": 100, "time": 65, "title": 230, "category": 115,
        "period": 100, "importance": 90, "people": 150, "tags": 180,
    }
    for column in columns:
        tree.heading(column, text=headings[column])
        tree.column(column, width=widths[column], minwidth=60, anchor="center" if column in ("start", "time", "period", "importance") else "w")
    scrollbar = ttk.Scrollbar(page, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    event_by_item = {}
    count_var = tk.StringVar()

    def refresh_events(select_event_id=None):
        query = search_var.get().strip().casefold()
        tree.delete(*tree.get_children())
        event_by_item.clear()
        visible = []
        for item in profile_store.list_events(profile["id"]):
            people_display = _event_people_display(item)
            haystack = " ".join(
                str(value or "") for value in (
                    item.get("title"), item.get("category"), item.get("date_start"),
                    people_display, item.get("tags"), item.get("notes"),
                )
            ).casefold()
            if not query or query in haystack:
                visible.append({**item, "people_display": people_display})
        for item in visible:
            start = datetime.fromisoformat(item["date_start"]).strftime("%d/%m/%Y")
            end = (
                datetime.fromisoformat(item["date_end"]).strftime("%d/%m/%Y")
                if item.get("date_end") else "—"
            )
            iid = str(item["id"])
            tree.insert(
                "", "end", iid=iid,
                values=(
                    start, item.get("event_time") or "—", item["title"],
                    item["category"], end,
                    "●" * int(item.get("importance") or 3),
                    item.get("people_display") or "—", item.get("tags") or "—",
                ),
            )
            event_by_item[iid] = item
        count_var.set(f"{len(visible)} événement{'s' if len(visible) != 1 else ''}")
        target_iid = str(select_event_id) if select_event_id else None
        if target_iid in event_by_item:
            tree.selection_set(target_iid)
            tree.focus(target_iid)
        elif visible:
            tree.selection_set(str(visible[0]["id"]))

    def selected_event():
        selection = tree.selection()
        return event_by_item.get(selection[0]) if selection else None

    def new_event():
        form_result = _ask_event_data()
        if not form_result:
            return
        try:
            created = _store_event_dialog_result(form_result)
        except ValueError as exc:
            messagebox.showerror("Événement", str(exc), parent=page)
            return
        refresh_events(created["id"])
        status_var.set(f'Événement « {created["title"]} » enregistré.')

    def edit_event():
        selected = selected_event()
        if not selected:
            return
        form_result = _ask_event_data(selected)
        if not form_result:
            return
        try:
            updated = _store_event_dialog_result(form_result, selected["id"])
        except ValueError as exc:
            messagebox.showerror("Événement", str(exc), parent=page)
            return
        refresh_events(updated["id"])

    def delete_event():
        selected = selected_event()
        if not selected:
            return
        if not messagebox.askyesno(
            "Supprimer l’événement",
            f'Supprimer définitivement « {selected["title"]} » ?',
            parent=page,
        ):
            return
        profile_store.delete_event(selected["id"])
        refresh_events()

    def open_event(_event=None):
        global analysis_time_linked, analysis_place_linked
        selected = selected_event()
        if not selected:
            return
        selected_date = datetime.fromisoformat(selected["date_start"]).date()
        return_to_clock()
        _display_target_date(selected_date)
        if selected.get("event_time"):
            target_time_entry.delete(0, "end")
            target_time_entry.insert(0, selected["event_time"])
            analysis_time_linked = False
        if selected.get("place"):
            analysis_place_var.set(selected["place"])
            analysis_place_linked = False
        calculate(selected_date)
        status_var.set(
            f'Événement « {selected["title"]} » — analyse du '
            f'{selected_date.strftime("%d/%m/%Y")}'
        )

    controls = ttk.Frame(page)
    controls.pack(side="bottom", fill="x", pady=(12, 0), before=tree)
    ttk.Label(controls, textvariable=count_var, style="InputLabel.TLabel").pack(side="left", padx=(0, 16))
    ttk.Button(controls, text="SUPPRIMER", command=delete_event).pack(side="left")
    ttk.Button(controls, text="MODIFIER", command=edit_event).pack(side="left", padx=6)
    ttk.Button(controls, text="NOUVEAU", command=new_event).pack(side="left")
    ttk.Button(controls, text="← RETOUR À L’HORLOGE", command=return_to_clock).pack(side="right", padx=(8, 0))
    ttk.Button(controls, text="OUVRIR À CETTE DATE", command=open_event, style="Calculate.TButton").pack(side="right")
    tree.bind("<Double-Button-1>", open_event)
    search_var.trace_add("write", lambda *_args: refresh_events())

    def apply_events_theme():
        # The shared Treeview style is recolored by apply_theme().
        tree.update_idletasks()

    events_page_apply_theme = apply_events_theme
    refresh_events()
    apply_events_theme()
    search_entry.focus_set()


def _event_clock_summary(profile, event):
    """Return the five clock cards at an event's date, time and place."""
    try:
        birth = datetime.fromisoformat(profile["birth_date"]).date()
        target = datetime.fromisoformat(event["date_start"]).date()
        if target < birth or engine.is_joker_birth_date(birth):
            return ("—",) * 5
        state = engine.full_state(birth, target)
        try:
            hour = engine.hour_card(
                target,
                event.get("event_time") or "00:00",
                event.get("place") or profile["birth_place"],
            )["card"]
        except ValueError:
            hour = "—"
        return (
            state["life_path"]["card"], state["year"]["year_card"],
            state["fifty_two_day"]["card"], state["week"]["day_card"], hour,
        )
    except (KeyError, TypeError, ValueError):
        return ("—",) * 5


def manage_events():
    """Show every saved event with its owner and historical clock state."""
    global events_page, events_page_apply_theme, events_page_return
    if not profile_store.list_profiles():
        messagebox.showinfo("Événements", "Crée d’abord au moins un profil.")
        return
    if events_page is not None and events_page.winfo_exists():
        return
    if chat_page_return:
        chat_page_return()
    if profiles_page_return:
        profiles_page_return()
    if relationships_page_return:
        relationships_page_return()
    for widget in (input_frame, clock, notebook, footer):
        widget.pack_forget()

    page = ttk.Frame(main, padding=(14, 12, 14, 6))
    page.pack(fill="both", expand=True)
    events_page = page

    def return_to_clock():
        global events_page, events_page_apply_theme, events_page_return
        if page.winfo_exists():
            page.destroy()
        events_page = None
        events_page_apply_theme = None
        events_page_return = None
        input_frame.pack(fill="x")
        clock.pack(fill="x", pady=10)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        notebook.pack(side="top", fill="both", expand=True)
        apply_theme()

    events_page_return = return_to_clock
    title_row = ttk.Frame(page)
    title_row.pack(fill="x", pady=(0, 14))
    title_group = ttk.Frame(title_row)
    title_group.pack(side="left", fill="x", expand=True)
    ttk.Label(title_group, text="ÉVÉNEMENTS", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(
        title_group,
        text="Tous les profils  •  Horloge calculée à la date exacte de chaque événement",
        style="InputLabel.TLabel",
    ).pack(anchor="w", pady=(3, 0))
    search_group = ttk.Frame(title_row)
    search_group.pack(side="right", padx=(20, 0))
    ttk.Label(search_group, text="RECHERCHER", style="InputLabel.TLabel").pack(anchor="w")
    search_var = tk.StringVar()
    search_entry = ttk.Entry(
        search_group, textvariable=search_var, width=32,
        font=("Segoe UI", 11), style="Input.TEntry",
    )
    search_entry.pack(pady=(4, 0))
    bind_select_all_on_focus(search_entry)

    table_frame = ttk.Frame(page)
    table_frame.pack(fill="both", expand=True)
    canvas = tk.Canvas(table_frame, highlightthickness=1, borderwidth=0)
    content = tk.Frame(canvas)
    window = canvas.create_window((0, 0), window=content, anchor="nw")
    vertical = ttk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
    horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=canvas.xview)
    canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    columns = (
        "profile", "title", "date", "time", "category", "importance",
        "life_path", "year", "fifty", "day", "hour", "people", "tags",
    )
    headings = (
        "PROFIL", "ÉVÉNEMENT", "DATE", "HEURE", "CATÉGORIE", "IMPORTANCE",
        "CHEMIN DE VIE", "ANNÉE", "52 JOURS", "JOUR", "HEURE",
        "PERSONNES", "MOTS-CLÉS",
    )
    widths = (150, 220, 100, 70, 110, 95, 115, 85, 90, 80, 80, 160, 180)
    clock_colors = {
        6: "#2F80ED", 7: "#F2994A", 8: "#9B51E0",
        9: "#27AE60", 10: "#00A6A6",
    }
    selected_id = {"value": None}
    sort_state = {"column": 2, "reverse": True}
    rows = []
    row_cells = {}
    count_var = tk.StringVar()

    def update_scroll(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def fit_width(event):
        canvas.itemconfigure(window, width=max(event.width, sum(widths)))

    def wheel(event):
        if event.state & 0x0001:
            canvas.xview_scroll(int(-event.delta / 120), "units")
        else:
            canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    content.bind("<Configure>", update_scroll)
    canvas.bind("<Configure>", fit_width)
    canvas.bind("<MouseWheel>", wheel)

    def select_event(event_id):
        selected_id["value"] = event_id
        for row_id, cells in row_cells.items():
            border = "#79B8EA" if row_id == event_id else (
                "#405465" if dark_mode else "#CBD5DF"
            )
            for cell in cells:
                cell.configure(
                    highlightbackground=border,
                    highlightthickness=2 if row_id == event_id else 1,
                )

    def selected_event():
        return next(
            (row["event"] for row in rows if row["event"]["id"] == selected_id["value"]),
            None,
        )

    def change_sort(column_index):
        if sort_state["column"] == column_index:
            sort_state["reverse"] = not sort_state["reverse"]
        else:
            sort_state["column"] = column_index
            sort_state["reverse"] = False
        render(selected_id["value"])

    def event_sort_key(row):
        index = sort_state["column"]
        if index == 2:
            return row["event"].get("date_start", "")
        value = str(row["values"][index] or "")
        if value in CARD_NUMBER_BY_LABEL:
            return f'{CARD_NUMBER_BY_LABEL[value]:03d}'
        return value.casefold()

    def open_event_by_id(event_id):
        open_saved_event(event_id)

    def render(select_id=None):
        for child in content.winfo_children():
            child.destroy()
        row_cells.clear()
        profile_map = {item["id"]: item for item in profile_store.list_profiles()}
        header_bg = "#151F29" if dark_mode else "#E6EEF5"
        header_fg = "#E7EEF5" if dark_mode else "#173F5F"
        groups = (
            ("ÉVÉNEMENT", 0, 6, header_bg),
            ("HORLOGE DES CYCLES À LA DATE DE L’ÉVÉNEMENT", 6, 5,
             "#23435D" if dark_mode else "#DDEAF5"),
            ("DÉTAILS", 11, 2, header_bg),
        )
        for title, column, span, background in groups:
            label = tk.Label(
                content, text=title, background=background, foreground=header_fg,
                font=("Segoe UI", 9, "bold"), pady=5,
            )
            label.grid(row=0, column=column, columnspan=span, sticky="nsew", padx=1, pady=1)
            label.bind("<MouseWheel>", wheel)
        for index, heading in enumerate(headings):
            content.grid_columnconfigure(index, minsize=widths[index])
            arrow = (
                " ▼" if sort_state["reverse"] else " ▲"
            ) if sort_state["column"] == index else " ↕"
            label = tk.Label(
                content, text=f"{heading}{arrow}", background=clock_colors.get(index, header_bg),
                foreground="#FFFFFF" if index in clock_colors else header_fg,
                font=("Segoe UI", 8, "bold"), padx=5, pady=8,
            )
            label.grid(row=1, column=index, sticky="nsew", padx=1, pady=1)
            label.bind("<MouseWheel>", wheel)
            label.bind("<Button-1>", lambda _e, column=index: change_sort(column))

        query = search_var.get().strip().casefold()
        rows.clear()
        for event in profile_store.list_events():
            profile = profile_map.get(event["profile_id"])
            if not profile:
                continue
            profile_name = _profile_display_name(profile)
            people_display = _event_people_display(event)
            search_text = " ".join(
                str(value or "") for value in (
                    profile_name, event.get("title"), event.get("category"),
                    event.get("date_start"), people_display,
                    event.get("tags"), event.get("notes"),
                )
            ).casefold()
            if query and query not in search_text:
                continue
            values = (
                profile_name, event["title"],
                datetime.fromisoformat(event["date_start"]).strftime("%d/%m/%Y"),
                event.get("event_time") or "—", event.get("category") or "Autre",
                "●" * int(event.get("importance") or 3),
                *_event_clock_summary(profile, event),
                people_display or "—", event.get("tags") or "—",
            )
            rows.append({"event": event, "values": values})

        rows.sort(key=event_sort_key, reverse=sort_state["reverse"])

        for row_number, row in enumerate(rows, start=2):
            event = row["event"]
            row_bg = (
                "#151F29" if dark_mode and row_number % 2
                else "#18232E" if dark_mode
                else "#F5F8FB" if row_number % 2 else "#FFFFFF"
            )
            cells = []
            content.grid_rowconfigure(row_number, minsize=60)
            for index, value in enumerate(row["values"]):
                colored = index in clock_colors
                foreground = "#FFFFFF" if colored else (
                    "#D83232" if "♥" in str(value) or "♦" in str(value)
                    else "#E7EEF5" if dark_mode else "#111827"
                )
                cell = tk.Label(
                    content, text=value,
                    background=clock_colors.get(index, row_bg), foreground=foreground,
                    font=("Segoe UI Symbol", 10, "bold" if colored or index < 2 else "normal"),
                    padx=6, pady=8,
                    anchor="w" if index in (0, 1, 11, 12) else "center",
                    highlightthickness=1,
                )
                cell.grid(row=row_number, column=index, sticky="nsew", padx=1, pady=1)
                cell.bind("<Button-1>", lambda _e, eid=event["id"]: select_event(eid))
                cell.bind("<Double-Button-1>", lambda _e, eid=event["id"]: open_event_by_id(eid))
                cell.bind("<MouseWheel>", wheel)
                cells.append(cell)
            row_cells[event["id"]] = cells
        count_var.set(f"{len(rows)} événement{'s' if len(rows) != 1 else ''}")
        chosen = select_id if select_id in row_cells else (
            rows[0]["event"]["id"] if rows else None
        )
        if chosen is not None:
            select_event(chosen)
        update_scroll()

    def new_event():
        form_result = _ask_event_data()
        if form_result:
            try:
                created = _store_event_dialog_result(form_result)
                _refresh_event_menu()
                render(created["id"])
            except ValueError as exc:
                messagebox.showerror("Événement", str(exc), parent=page)

    def edit_event():
        event = selected_event()
        if not event:
            return
        form_result = _ask_event_data(event)
        if form_result:
            try:
                updated = _store_event_dialog_result(form_result, event["id"])
                _refresh_event_menu()
                render(updated["id"])
            except ValueError as exc:
                messagebox.showerror("Événement", str(exc), parent=page)

    def delete_event():
        event = selected_event()
        if event and messagebox.askyesno(
            "Supprimer l’événement", f'Supprimer définitivement « {event["title"]} » ?',
            parent=page,
        ):
            profile_store.delete_event(event["id"])
            _refresh_event_menu()
            render()

    def open_selected():
        event = selected_event()
        if event:
            open_event_by_id(event["id"])

    controls = ttk.Frame(page)
    controls.pack(fill="x", pady=(12, 0))
    ttk.Label(controls, textvariable=count_var, style="InputLabel.TLabel").pack(side="left", padx=(0, 16))
    ttk.Button(controls, text="SUPPRIMER", command=delete_event).pack(side="left")
    ttk.Button(controls, text="MODIFIER", command=edit_event).pack(side="left", padx=6)
    ttk.Button(controls, text="NOUVEAU", command=new_event).pack(side="left")
    ttk.Button(controls, text="← RETOUR À L’HORLOGE", command=return_to_clock).pack(side="right", padx=(8, 0))
    ttk.Button(controls, text="OUVRIR À CETTE DATE", command=open_selected, style="Calculate.TButton").pack(side="right")
    search_var.trace_add("write", lambda *_args: render(selected_id["value"]))

    def apply_events_theme():
        background = "#0D141C" if dark_mode else "#F0F0F0"
        canvas.configure(
            background=background,
            highlightbackground="#405465" if dark_mode else "#B9C7D3",
        )
        content.configure(background=background)
        render(selected_id["value"])

    events_page_apply_theme = apply_events_theme
    apply_events_theme()
    search_entry.focus_set()


def manage_profiles():
    global active_profile_id, profile_dirty, profiles_page
    global profiles_page_apply_theme, profiles_page_return
    if profiles_page is not None and profiles_page.winfo_exists():
        return
    if chat_page_return:
        chat_page_return()
    if events_page_return:
        events_page_return()
    if relationships_page_return:
        relationships_page_return()

    for widget in (input_frame, clock, notebook, footer):
        widget.pack_forget()

    page = ttk.Frame(main, padding=(2, 8, 2, 0))
    page.pack(fill="both", expand=True)
    profiles_page = page
    body = ttk.Frame(page, padding=(12, 8, 12, 8))
    body.pack(fill="both", expand=True)

    def return_to_clock():
        global profiles_page, profiles_page_apply_theme, profiles_page_return
        if page.winfo_exists():
            page.destroy()
        profiles_page = None
        profiles_page_apply_theme = None
        profiles_page_return = None
        input_frame.pack(fill="x")
        clock.pack(fill="x", pady=10)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        notebook.pack(side="top", fill="both", expand=True)
        apply_theme()

    profiles_page_return = return_to_clock

    title_row = ttk.Frame(body)
    title_row.pack(fill="x", pady=(0, 14))
    title_group = ttk.Frame(title_row)
    title_group.pack(side="left", fill="x", expand=True)
    ttk.Label(
        title_group, text="PROFILS", font=("Segoe UI", 18, "bold")
    ).pack(anchor="w")
    moment = datetime.now().replace(second=0, microsecond=0)
    ttk.Label(
        title_group,
        text=(
            "Cartes calculées aujourd’hui — "
            f'{moment.strftime("%d/%m/%Y à %H:%M")}  •  '
            "Maj + molette : déplacement horizontal"
        ),
        style="InputLabel.TLabel",
    ).pack(anchor="w", pady=(3, 0))

    search_group = ttk.Frame(title_row)
    search_group.pack(side="right", padx=(20, 0))
    ttk.Label(search_group, text="RECHERCHER", style="InputLabel.TLabel").pack(
        anchor="w"
    )
    search_var = tk.StringVar()
    search_entry = ttk.Entry(
        search_group, textvariable=search_var, width=34,
        font=("Segoe UI", 11), style="Input.TEntry",
    )
    search_entry.pack(fill="x", pady=(4, 0))
    bind_select_all_on_focus(search_entry)

    table_frame = ttk.Frame(body)
    table_frame.pack(fill="both", expand=True)
    columns = (
        "first_name", "last_name", "profile_type", "birth_date", "sign", "ascendant",
        "birth_card", "secondary", "life_path", "year", "fifty", "day", "hour",
        "path_mercury", "path_venus", "path_mars", "path_jupiter",
        "path_saturn", "path_uranus", "path_neptune",
        "path_challenge", "path_result",
    )
    headings = {
        "first_name": "PRÉNOM",
        "last_name": "NOM",
        "profile_type": "TYPE",
        "birth_date": "NAISSANCE",
        "sign": "SIGNE",
        "ascendant": "ASCENDANT",
        "birth_card": "CARTE DE NAISSANCE",
        "secondary": "SECONDAIRE(S)",
        "life_path": "CHEMIN DE VIE",
        "year": "ANNÉE",
        "fifty": "52 JOURS",
        "day": "JOUR",
        "hour": "HEURE",
        "path_mercury": "MERCURE",
        "path_venus": "VÉNUS",
        "path_mars": "MARS",
        "path_jupiter": "JUPITER",
        "path_saturn": "SATURNE",
        "path_uranus": "URANUS",
        "path_neptune": "NEPTUNE",
        "path_challenge": "DÉFI",
        "path_result": "RÉSULTAT",
    }
    widths = {
        "first_name": 100, "last_name": 110, "profile_type": 95, "birth_date": 98,
        "sign": 125, "ascendant": 125,
        "birth_card": 125, "secondary": 115, "life_path": 105,
        "year": 80, "fifty": 90, "day": 80, "hour": 80,
        "path_mercury": 82, "path_venus": 82, "path_mars": 82,
        "path_jupiter": 82, "path_saturn": 82, "path_uranus": 82,
        "path_neptune": 82,
        "path_challenge": 82, "path_result": 82,
    }
    fixed_width = sum(widths[column] for column in columns[:2])
    fixed_canvas = tk.Canvas(
        table_frame, width=fixed_width, highlightthickness=1, borderwidth=0
    )
    table_canvas = tk.Canvas(table_frame, highlightthickness=1, borderwidth=0)
    fixed_content = tk.Frame(fixed_canvas)
    table_content = tk.Frame(table_canvas)
    fixed_window = fixed_canvas.create_window(
        (0, 0), window=fixed_content, anchor="nw", width=fixed_width
    )
    table_window = table_canvas.create_window((0, 0), window=table_content, anchor="nw")

    def scroll_vertical(*args):
        bbox = table_canvas.bbox("all")
        content_height = (bbox[3] - bbox[1]) if bbox else 0
        if content_height <= table_canvas.winfo_height():
            fixed_canvas.yview_moveto(0)
            table_canvas.yview_moveto(0)
            return
        if args[0] == "moveto":
            fixed_canvas.yview_moveto(args[1])
            table_canvas.yview_moveto(args[1])
        else:
            fixed_canvas.yview_scroll(int(args[1]), args[2])
            table_canvas.yview_scroll(int(args[1]), args[2])

    vertical = ttk.Scrollbar(table_frame, orient="vertical", command=scroll_vertical)
    horizontal = ttk.Scrollbar(
        table_frame, orient="horizontal", command=table_canvas.xview
    )
    table_canvas.configure(
        yscrollcommand=vertical.set, xscrollcommand=horizontal.set
    )
    fixed_canvas.grid(row=0, column=0, sticky="nsw")
    table_canvas.grid(row=0, column=1, sticky="nsew")
    vertical.grid(row=0, column=2, sticky="ns")
    horizontal.grid(row=1, column=1, sticky="ew")
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(1, weight=1)

    def update_scroll_region(_event=None):
        fixed_canvas.configure(scrollregion=fixed_canvas.bbox("all"))
        table_canvas.configure(scrollregion=table_canvas.bbox("all"))
        bbox = table_canvas.bbox("all")
        content_height = (bbox[3] - bbox[1]) if bbox else 0
        if content_height <= table_canvas.winfo_height():
            fixed_canvas.yview_moveto(0)
            table_canvas.yview_moveto(0)
            vertical.state(["disabled"])
        else:
            vertical.state(["!disabled"])

    def fit_content_width(event):
        required = sum(widths[column] for column in columns[2:])
        table_canvas.itemconfigure(table_window, width=max(event.width, required))

    fixed_content.bind("<Configure>", update_scroll_region)
    table_content.bind("<Configure>", update_scroll_region)
    table_canvas.bind("<Configure>", fit_content_width)

    def wheel_vertical(event):
        scroll_vertical("scroll", int(-event.delta / 120), "units")
        return "break"

    def wheel_horizontal(event):
        table_canvas.xview_scroll(int(-event.delta / 120), "units")
        return "break"

    def bind_table_scroll(widget):
        widget.bind("<MouseWheel>", wheel_vertical)
        widget.bind("<Shift-MouseWheel>", wheel_horizontal)

    bind_table_scroll(fixed_canvas)
    bind_table_scroll(table_canvas)

    all_rows = []
    count_var = tk.StringVar()
    selected_id = {"value": active_profile_id}
    sort_state = {"column": None, "reverse": False}
    favorite_button_var = tk.StringVar(value="☆ FAVORI")
    row_cells = {}

    clock_colors = {
        8: "#2F80ED", 9: "#F2994A", 10: "#9B51E0",
        11: "#27AE60", 12: "#00A6A6",
    }
    path_outline_colors = {
        13: SLOT_COLORS["mercure"], 14: SLOT_COLORS["vénus"],
        15: SLOT_COLORS["mars"], 16: SLOT_COLORS["jupiter"],
        17: SLOT_COLORS["saturne"], 18: SLOT_COLORS["uranus"],
        19: SLOT_COLORS["neptune"],
    }
    path_filled_colors = {20: SLOT_COLORS["défi"], 21: SLOT_COLORS["résultat"]}

    def card_ink(card, colored=False):
        if colored:
            return "#FFFFFF"
        return "#D83232" if "♥" in str(card) or "♦" in str(card) else (
            "#E7EEF5" if dark_mode else "#111827"
        )

    def select_row(profile_id):
        selected_id["value"] = profile_id
        profile = profile_store.get_profile(profile_id)
        favorite_button_var.set(
            "★ RETIRER DES FAVORIS" if profile and profile.get("favorite")
            else "☆ AJOUTER AUX FAVORIS"
        )
        for row_id, cells in row_cells.items():
            border = "#79B8EA" if row_id == profile_id else (
                "#405465" if dark_mode else "#CBD5DF"
            )
            thickness = 2 if row_id == profile_id else 1
            for column_index, cell in enumerate(cells):
                path_border = path_outline_colors.get(column_index)
                cell.configure(
                    highlightbackground=path_border or border,
                    highlightthickness=2 if path_border else thickness,
                )

    def make_label(
        parent, text, row, column, background, foreground, bold=False,
        grid_column=None,
    ):
        label = tk.Label(
            parent,
            text=text,
            background=background,
            foreground=foreground,
            font=("Segoe UI Symbol", 10, "bold" if bold else "normal"),
            padx=6,
            pady=8,
            anchor="w" if column in (0, 1) else "center",
            highlightthickness=1,
        )
        label.grid(
            row=row,
            column=column if grid_column is None else grid_column,
            sticky="nsew", padx=1, pady=1,
        )
        bind_table_scroll(label)
        return label

    def draw_headers():
        header_bg = "#151F29" if dark_mode else "#E6EEF5"
        header_fg = "#E7EEF5" if dark_mode else "#173F5F"
        clock_bg = "#23435D" if dark_mode else "#DDEAF5"
        path_bg = "#294C6B" if dark_mode else "#C9DDEF"
        for child in fixed_content.winfo_children():
            child.destroy()
        for child in table_content.winfo_children():
            child.destroy()
        previous_rows = max(
            fixed_content.grid_size()[1], table_content.grid_size()[1], 2
        )
        for row_index in range(previous_rows + 1):
            fixed_content.grid_rowconfigure(row_index, minsize=0)
            table_content.grid_rowconfigure(row_index, minsize=0)
        for frame in (fixed_content, table_content):
            frame.grid_rowconfigure(0, minsize=46)
            frame.grid_rowconfigure(1, minsize=52)
        for index, column in enumerate(columns[:2]):
            fixed_content.grid_columnconfigure(index, minsize=widths[column])
        for index, column in enumerate(columns[2:]):
            table_content.grid_columnconfigure(index, minsize=widths[column])
        fixed_title = tk.Label(
            fixed_content, text="PROFILS", background=header_bg,
            foreground=header_fg, font=("Segoe UI", 9, "bold"), pady=5,
        )
        fixed_title.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=1, pady=1)
        identity_title = tk.Label(
            table_content, text="DONNÉES NATALES", background=header_bg,
            foreground=header_fg, font=("Segoe UI", 9, "bold"), pady=5,
        )
        identity_title.grid(
            row=0, column=0, columnspan=6, sticky="nsew", padx=1, pady=1
        )
        clock_title = tk.Label(
            table_content,
            text=f'HORLOGE DES CYCLES — AUJOURD’HUI {moment.strftime("%d/%m/%Y")}',
            background=clock_bg, foreground=header_fg,
            font=("Segoe UI", 9, "bold"), pady=5,
        )
        clock_title.grid(
            row=0, column=6, columnspan=5, sticky="nsew", padx=1, pady=1
        )
        path_title = tk.Label(
            table_content,
            text="CARTES DU CHEMIN DE VIE",
            background=path_bg, foreground=header_fg,
            font=("Segoe UI", 9, "bold"), pady=5,
        )
        path_title.grid(
            row=0, column=11, columnspan=9, sticky="nsew", padx=1, pady=1
        )
        for title in (fixed_title, identity_title, clock_title, path_title):
            bind_table_scroll(title)
        for index, column in enumerate(columns):
            background = clock_colors.get(
                index, path_filled_colors.get(index, header_bg)
            )
            foreground = (
                "#111827" if index in path_filled_colors
                else "#FFFFFF" if index in clock_colors
                else header_fg
            )
            parent = fixed_content if index < 2 else table_content
            arrow = (
                " ▼" if sort_state["reverse"] else " ▲"
            ) if sort_state["column"] == index else " ↕"
            header = tk.Label(
                parent, text=f'{headings[column]}{arrow}', background=background,
                foreground=foreground, font=("Segoe UI", 8, "bold"),
                padx=4, pady=7,
                highlightbackground=path_outline_colors.get(index, background),
                highlightthickness=2 if index in path_outline_colors else 0,
            )
            header.grid(
                row=1,
                column=index if index < 2 else index - 2,
                sticky="nsew", padx=1, pady=1,
            )
            bind_table_scroll(header)
            header.bind(
                "<Button-1>",
                lambda _event, selected=index: change_sort(selected),
            )

    def change_sort(column_index):
        if sort_state["column"] == column_index:
            sort_state["reverse"] = not sort_state["reverse"]
        else:
            sort_state["column"] = column_index
            sort_state["reverse"] = False
        render_rows()

    def row_sort_key(row):
        column_index = sort_state["column"]
        if column_index is None:
            return (0, "")
        if column_index == 3:
            return (0, row["profile"].get("birth_date", ""))
        value = str(row["values"][column_index] or "")
        if value in CARD_NUMBER_BY_LABEL:
            return (0, CARD_NUMBER_BY_LABEL[value])
        return (1, value.casefold())

    def refresh_list(select_id=None):
        all_rows.clear()
        for item in profile_store.list_profiles():
            try:
                birth_label = datetime.fromisoformat(item["birth_date"]).strftime(
                    "%d/%m/%Y"
                )
            except (TypeError, ValueError):
                birth_label = item.get("birth_date", "—")
            cards = _profile_current_summary(item, moment)
            values = (
                item.get("name", ""), item.get("last_name", ""),
                item.get("profile_type", "Humain"), birth_label,
                *cards,
            )
            all_rows.append({
                "profile": item,
                "values": values,
                "search": " ".join(str(value) for value in values).casefold(),
            })
        render_rows(select_id)

    def render_rows(select_id=None):
        chosen = select_id if select_id is not None else selected_id["value"]
        query = search_var.get().strip().casefold()
        draw_headers()
        row_cells.clear()
        visible = [row for row in all_rows if not query or query in row["search"]]
        if sort_state["column"] is not None:
            visible.sort(key=row_sort_key, reverse=sort_state["reverse"])
        visible.sort(key=lambda row: not bool(row["profile"].get("favorite")))
        for index, row in enumerate(visible):
            item = row["profile"]
            profile_id = item["id"]
            row_bg = (
                "#20384C" if profile_id == active_profile_id and dark_mode
                else "#E5F0F9" if profile_id == active_profile_id
                else "#151F29" if dark_mode and index % 2
                else "#18232E" if dark_mode
                else "#F5F8FB" if index % 2
                else "#FFFFFF"
            )
            cells = []
            fixed_content.grid_rowconfigure(index + 2, minsize=62)
            table_content.grid_rowconfigure(index + 2, minsize=62)
            for column_index, value in enumerate(row["values"]):
                colored = (
                    column_index in clock_colors
                    or column_index in path_filled_colors
                )
                background = (
                    clock_colors[column_index]
                    if column_index in clock_colors
                    else path_filled_colors.get(column_index, row_bg)
                )
                display = str(value or "—")
                if column_index == 0:
                    markers = []
                    if profile_id == active_profile_id:
                        markers.append("●")
                    if item.get("favorite"):
                        markers.append("★")
                    if markers:
                        display = f'{" ".join(markers)} {display}'
                parent = fixed_content if column_index < 2 else table_content
                cell = make_label(
                    parent, display, index + 2, column_index,
                    background,
                    (
                        "#111827" if column_index in path_filled_colors
                        else card_ink(value, colored)
                    ),
                    bold=column_index >= 3,
                    grid_column=(
                        column_index if column_index < 2 else column_index - 2
                    ),
                )
                cell.bind(
                    "<Button-1>",
                    lambda _event, selected=profile_id: select_row(selected),
                )
                cell.bind(
                    "<Double-Button-1>",
                    lambda _event, selected=profile_id: open_profile_id(selected),
                )
                cells.append(cell)
            row_cells[profile_id] = cells
        count_var.set(
            f"{len(visible)} profil{'s' if len(visible) != 1 else ''}"
            + (f" sur {len(all_rows)}" if query else "")
        )
        visible_ids = {row["profile"]["id"] for row in visible}
        if chosen not in visible_ids:
            chosen = visible[0]["profile"]["id"] if visible else None
        selected_id["value"] = chosen
        if chosen is not None:
            select_row(chosen)
        update_scroll_region()

    def selected_profile():
        return (
            profile_store.get_profile(selected_id["value"])
            if selected_id["value"] is not None else None
        )

    def open_profile_id(profile_id):
        return_to_clock()
        load_profile(profile_id)

    def open_selected(_event=None):
        profile = selected_profile()
        if not profile:
            return
        open_profile_id(profile["id"])

    def modify_selected():
        profile = selected_profile()
        if not profile:
            return
        data = _ask_new_profile_data(profile, "Modifier le profil")
        if not data:
            return
        try:
            updated = profile_store.update_profile(profile["id"], data)
        except ValueError as exc:
            messagebox.showerror("Modifier le profil", str(exc), parent=page)
            return
        refresh_list(profile["id"])
        _refresh_profile_menu()
        if profile["id"] == active_profile_id:
            load_profile(updated["id"])
            refresh_list(updated["id"])

    def delete_selected():
        global active_profile_id, profile_dirty
        profile = selected_profile()
        if not profile:
            return
        if not messagebox.askyesno(
            "Supprimer le profil",
            f'Supprimer définitivement le profil « {_profile_display_name(profile)} » ?',
            parent=page,
        ):
            return
        profile_store.delete_profile(profile["id"])
        if active_profile_id == profile["id"]:
            active_profile_id = None
            profile_dirty = False
        refresh_list()
        _refresh_profile_menu()

    def create_from_profiles():
        create_profile()
        refresh_list(active_profile_id)

    def toggle_favorite():
        profile = selected_profile()
        if not profile:
            return
        profile_store.set_favorite(profile["id"], not bool(profile.get("favorite")))
        _refresh_profile_menu()
        refresh_list(profile["id"])
        fixed_canvas.yview_moveto(0)
        table_canvas.yview_moveto(0)

    def apply_profiles_theme():
        background = "#0D141C" if dark_mode else "#F0F0F0"
        border = "#405465" if dark_mode else "#B9C7D3"
        for canvas in (fixed_canvas, table_canvas):
            canvas.configure(background=background, highlightbackground=border)
        fixed_content.configure(background=background)
        table_content.configure(background=background)
        render_rows()

    profiles_page_apply_theme = apply_profiles_theme
    search_var.trace_add("write", lambda *_args: render_rows())
    controls = ttk.Frame(body)
    controls.pack(fill="x", pady=(14, 0))
    ttk.Label(controls, textvariable=count_var, style="InputLabel.TLabel").pack(
        side="left", padx=(0, 18)
    )
    ttk.Button(controls, text="SUPPRIMER", command=delete_selected).pack(side="left")
    ttk.Button(controls, text="MODIFIER", command=modify_selected).pack(side="left", padx=6)
    ttk.Button(controls, text="NOUVEAU", command=create_from_profiles).pack(side="left")
    ttk.Button(
        controls, textvariable=favorite_button_var, command=toggle_favorite
    ).pack(side="left", padx=(6, 0))
    ttk.Button(
        controls, text="← RETOUR À L’HORLOGE", command=return_to_clock
    ).pack(side="right", padx=(8, 0))
    ttk.Button(controls, text="OUVRIR", command=open_selected).pack(side="right")
    refresh_list()
    apply_profiles_theme()
    search_entry.focus_set()


def load_last_profile():
    if active_profile_id and profile_store.get_profile(active_profile_id):
        load_profile(active_profile_id)
    else:
        _refresh_profile_menu()

# Clock-style cycle dashboard
clock = tk.LabelFrame(
    main,
    text=" HORLOGE DES CYCLES ",
    background="#EEF3F7",
    foreground="#173F5F",
    font=("Segoe UI", 10, "bold"),
    padx=10,
    pady=9,
)
clock.pack(fill="x", pady=10)

for column in range(5):
    clock.columnconfigure(column, weight=1, uniform="clock")


def make_clock_tile(column, key, title, card_var, cycle_var, accent, navigation=None):
    tile = tk.Frame(
        clock,
        background="#FFFFFF",
        highlightthickness=2,
        highlightbackground=accent,
        padx=10,
        pady=6,
    )
    tile.grid(row=0, column=column, sticky="nsew", padx=4)
    title_label = tk.Label(
        tile,
        text=title.upper(),
        background=accent,
        foreground="#FFFFFF",
        font=("Segoe UI", 8, "bold"),
        padx=8,
        pady=3,
    )
    title_label.pack(fill="x")
    tab_target = CLOCK_TAB_TARGETS.get(key)
    card_label = tk.Label(
        tile,
        textvariable=card_var,
        background="#FFFFFF",
        foreground="#111827",
        font=("Segoe UI Symbol", 26, "bold"),
        pady=2,
        cursor="hand2" if tab_target else "arrow",
        highlightthickness=1,
        highlightbackground="#D9E1E8",
    )
    card_label.pack(pady=(5, 0))
    if tab_target:
        card_label.bind(
            "<Button-1>",
            lambda _event, target=tab_target: open_clock_table(target),
        )
        card_label.bind(
            "<Enter>",
            lambda _event, label=card_label: label.configure(
                background="#24313D" if dark_mode else "#F1F5F9"
            ),
        )
        card_label.bind(
            "<Leave>",
            lambda _event, label=card_label: label.configure(
                background="#18232E" if dark_mode else "#FFFFFF"
            ),
        )
    tk.Label(
        tile,
        textvariable=cycle_var,
        background="#FFFFFF",
        foreground="#52606D",
        font=("Segoe UI", 8),
        justify="center",
        wraplength=220,
        height=2,
    ).pack(fill="x")
    buttons = []
    if navigation:
        controls = tk.Frame(tile, background="#FFFFFF")
        controls.pack(pady=(1, 0))
        for label, direction in (("◀", -1), ("▶", 1)):
            button = tk.Button(
                controls,
                text=label,
                command=lambda d=direction, level=navigation: navigate_clock(level, d),
                background="#F5F7FA",
                foreground=accent,
                activebackground=accent,
                activeforeground="#FFFFFF",
                font=("Segoe UI Symbol", 9, "bold"),
                relief="solid",
                borderwidth=1,
                width=4,
                cursor="hand2",
            )
            button.pack(side="left", padx=3)
            buttons.append(button)
    else:
        tk.Frame(tile, background="#FFFFFF", height=27).pack()
    clock_card_labels[key] = card_label
    clock_tiles[key] = {
        "frame": tile,
        "title": title_label,
        "accent": accent,
        "buttons": buttons,
    }


make_clock_tile(
    0,
    "birth",
    "Carte chemin de vie",
    life_path_card_var,
    life_path_cycle_var,
    "#2F80ED",
    "life_path",
)
make_clock_tile(
    1, "year", "Carte année", year_card_var, year_cycle_var, "#F2994A", "year"
)
make_clock_tile(
    2, "fifty", "Carte 52 jours", fifty_card_var, fifty_cycle_var, "#9B51E0",
    "fifty_two_day",
)
make_clock_tile(
    3, "week", "Carte du jour", week_card_var, week_cycle_var, "#27AE60", "day"
)
make_clock_tile(
    4,
    "hour",
    "Carte de l’heure",
    hour_card_var,
    hour_cycle_var,
    "#00A6A6",
    "hour",
)

# Pied de page réservé avant la zone extensible afin qu'il reste toujours visible.
status_var = tk.StringVar(value="Entre les deux dates puis clique sur CALCULER.")
footer = ttk.Frame(main)
footer.pack(side="bottom", fill="x", pady=(8, 0))
ttk.Label(footer, textvariable=status_var, font=("Segoe UI", 9)).pack(side="left")
credit_label = ttk.Label(
    footer,
    text="Olney Engine V1.8.6 — développé par Sébastien",
    font=("Segoe UI", 9),
)
credit_label.pack(side="right")

# Notebook
notebook = ttk.Notebook(main)
notebook.pack(side="top", fill="both", expand=True)

style.configure("View.Toolbutton", font=("Segoe UI", 9, "bold"), padding=(12, 5))

cycle_tab_widgets = {}
cycle_tab_views = {}


def make_cycle_tab(title, available_views=("table", "result", "interpretation", "cycle")):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text=title)
    cycle_tab_widgets[title] = tab

    toolbar = ttk.Frame(tab, padding=(8, 7, 8, 2))
    toolbar.pack(fill="x")
    ttk.Label(toolbar, text="Affichage :", font=("Segoe UI", 9, "bold")).pack(
        side="left", padx=(0, 7)
    )

    stack = ttk.Frame(tab)
    stack.pack(fill="both", expand=True)
    stack.rowconfigure(0, weight=1)
    stack.columnconfigure(0, weight=1)

    result_panel = ttk.Frame(stack)
    table_panel = ttk.Frame(stack)
    interpretation_panel = ttk.Frame(stack)
    cycle_panel = ttk.Frame(stack)
    result_panel.grid(row=0, column=0, sticky="nsew")
    table_panel.grid(row=0, column=0, sticky="nsew")
    interpretation_panel.grid(row=0, column=0, sticky="nsew")
    cycle_panel.grid(row=0, column=0, sticky="nsew")
    panels = {"table": table_panel, "result": result_panel,
              "interpretation": interpretation_panel, "cycle": cycle_panel}
    for mode in available_views:
        if mode not in panels:
            panels[mode] = ttk.Frame(stack)
            panels[mode].grid(row=0, column=0, sticky="nsew")

    selected_view = tk.StringVar(value="table")

    def show_view():
        selected = selected_view.get()
        if selected not in cycle_tab_views[title]["available"]:
            selected = "table"
            selected_view.set(selected)
        panels[selected].tkraise()
        refresh_visible_view()

    view_labels = {
        "table": "Tableau",
        "result": "Résultat",
        "interpretation": "Interprétation",
        "cycle": "Lecture du cycle",
        "birth": "Carte principale",
        "secondary": "Carte secondaire",
        "secondary_two": "Carte secondaire 2",
    }
    view_buttons = {}
    for index, view_id in enumerate(available_views):
        button = ttk.Radiobutton(
            toolbar,
            text=view_labels[view_id],
            value=view_id,
            variable=selected_view,
            command=show_view,
            style="View.Toolbutton",
        )
        button.pack(side="left", padx=(0 if index == 0 else 5, 0))
        view_buttons[view_id] = button

    table_panel.tkraise()
    cycle_tab_views[title] = {
        "selected": selected_view,
        "show": show_view,
        "available": tuple(available_views),
        "buttons": view_buttons,
        "cycle_panel": cycle_panel,
        "toolbar": toolbar,
        "panels": panels,
    }
    return result_panel, table_panel, interpretation_panel

def make_tree(tab, columns, headings, widths):
    frame = ttk.Frame(tab, padding=8)
    frame.pack(fill="both", expand=True)

    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col, heading, width in zip(columns, headings, widths):
        tree.heading(col, text=heading)
        tree.column(col, width=width, anchor="center")

    for slot, color in SLOT_COLORS.items():
        tree.tag_configure(slot, background=color, foreground="#111111")

    yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)

    tree.pack(side="left", fill="both", expand=True)
    yscroll.pack(side="right", fill="y")
    return tree

natural_result_tab, natural_table_tab, natural_interpretation_tab = make_cycle_tab(
    "Ordre naturel", available_views=("table", "birth", "secondary", "secondary_two")
)
cycle_tab_views["Ordre naturel"]["available"] = ("table", "birth", "secondary")
cycle_tab_views["Ordre naturel"]["buttons"]["secondary_two"].pack_forget()
manifested_result_tab, manifested_table_tab, manifested_interpretation_tab = make_cycle_tab("Chemin de vie")

natural_results = ResultCardsView(natural_result_tab)
manifested_results = ResultCardsView(manifested_result_tab, lambda row: open_result_card("Chemin de vie", row))
natural_interpretation = CycleInterpretationView(
    natural_interpretation_tab, interpretation_knowledge, lambda: dark_mode
)
manifested_interpretation = CycleInterpretationView(
    manifested_interpretation_tab, interpretation_knowledge, lambda: dark_mode
)
birth_portrait = NatalCardView(cycle_tab_views["Ordre naturel"]["panels"]["birth"],
                              interpretation_knowledge, lambda: dark_mode)
secondary_portrait = NatalCardView(cycle_tab_views["Ordre naturel"]["panels"]["secondary"],
                                  interpretation_knowledge, lambda: dark_mode)
second_secondary_portrait = NatalCardView(cycle_tab_views["Ordre naturel"]["panels"]["secondary_two"],
                                         interpretation_knowledge, lambda: dark_mode)


def update_natal_card_views(context):
    profile = context["profile"]
    secondaries = profile.get("secondary_cards", [])
    metadata = cycle_tab_views["Ordre naturel"]
    modes = ("table", "birth", "secondary") + (("secondary_two",) if len(secondaries) > 1 else ())
    metadata["available"] = modes
    extra_button = metadata["buttons"]["secondary_two"]
    if len(secondaries) > 1:
        extra_button.pack(side="left", padx=(5, 0))
        metadata["buttons"]["secondary"].configure(text="Carte secondaire 1")
    else:
        extra_button.pack_forget()
        metadata["buttons"]["secondary"].configure(text="Carte secondaire")
    if metadata["selected"].get() not in modes:
        metadata["selected"].set("birth")
        metadata["panels"]["birth"].tkraise()
    if context.get("joker"):
        birth_portrait.show_message("Joker — la fiche de naissance reste en attente de la règle définitive.")
    else:
        payload = {"birth_date": context["birth_date"], "birth_card": profile["birth_card"],
                   "zodiac_sign": profile.get("zodiac_sign"), "secondary_cards": secondaries}
        birth_portrait.update({**payload, "card": profile["birth_card"], "role": "primary"})
    for index, view in enumerate((secondary_portrait, second_secondary_portrait)):
        if index < len(secondaries) and not context.get("joker"):
            view.update({**payload, "card": secondaries[index], "role": "secondary"})
        else:
            view.show_message("Aucune carte secondaire disponible pour ce profil.")

natural_full = FullTableView(
    natural_table_tab, "Ordre naturel", show_exchange=False
)
manifested_full = FullTableView(manifested_table_tab, "Chemin de vie")
natural_full.update(90, display_name="Tableau 0", reference=True)
manifested_full.update(1, display_name="Tableau 0.1")

tab7, tab7_full, tab7_interpretation = make_cycle_tab("Cycle 7 ans")
tab_year, tab_year_full, tab_year_interpretation = make_cycle_tab("Cycle annuel")
tab_week, tab_week_full, tab_week_interpretation = make_cycle_tab("Cycle semaine")

seven_results = ResultCardsView(tab7, lambda row: open_result_card("Cycle 7 ans", row))
year_results = ResultCardsView(tab_year, lambda row: open_result_card("Cycle annuel", row))
week_results = ResultCardsView(tab_week, lambda row: open_result_card("Cycle semaine", row))

seven_interpretation = CycleInterpretationView(
    tab7_interpretation, interpretation_knowledge, lambda: dark_mode
)
year_interpretation = CycleInterpretationView(
    tab_year_interpretation, interpretation_knowledge, lambda: dark_mode
)
week_interpretation = CycleInterpretationView(
    tab_week_interpretation, interpretation_knowledge, lambda: dark_mode
)

CYCLE_READING_IDS = {"Chemin de vie": "life_path", "Cycle 7 ans": "seven_year",
                     "Cycle annuel": "annual", "Cycle semaine": "week"}


def ensure_cycle_reading(title):
    cid = CYCLE_READING_IDS.get(title)
    if not cid or not current_interpretation_state or current_interpretation_context.get("joker"):
        return None
    if cid not in cycle_reading_cache:
        key = "cycle:" + cid
        if ui_jobs.busy("analysis") or ui_jobs.busy(key):
            return None
        state, profile_id, material = current_interpretation_state, active_profile_id, current_reading_material

        def ready(context):
            cycle_reading_cache[cid] = context
            cycle_reading_views[cid].update(context)
            refresh_visible_view()

        def failed(error):
            pending_cycle_cards.pop(cid, None)
            cycle_reading_views[cid].show_message(str(error))
            # Don't retry this same failed snapshot at each tab/configure event.
            cycle_reading_cache[cid] = None

        ui_jobs.submit(key, lambda: analysis_work.cycle(state, profile_id, CYCLE_FOCUS[cid], material),
                       ready, failed)
        return None
    context = cycle_reading_cache[cid]
    view = cycle_reading_views[cid]
    if context is not None and view.context != context:
        view.update(context)
    return context


def refresh_selected_cycle_reading(_event=None):
    title, mode = visible_view_key()
    if mode == "cycle":
        ensure_cycle_reading(title)


def visible_view_key():
    if not notebook.winfo_manager():
        return "", ""
    selected_tab = notebook.select()
    title = notebook.tab(selected_tab, "text") if selected_tab else ""
    mode = cycle_tab_views[title]["selected"].get() if title in cycle_tab_views else ""
    return title, mode


def refresh_visible_view(_event=None):
    if not deferred_views:
        return
    refresh_selected_cycle_reading()
    for view in deferred_views.values():
        view.flush()
    apply_pending_cycle_card()
    refresh_busy_indicators()
    schedule_navigation_record()


def open_result_card(title, row):
    """A dated step moves the clock; cycle-wide roles remain simple inspection."""
    if ui_jobs.busy("analysis"):
        return
    cid = CYCLE_READING_IDS[title]
    slot = str(row["slot"]).lower()
    if slot in PLANET_ROWS:
        cycle = next((item for item in current_interpretation_context["cycles"]
                      if item["id"] == cid), None)
        step = next((item for item in cycle["sequence_cards"]
                     if item["sequence_planet"] == slot and item["label"] == row["card"]), None) if cycle else None
        if step is None:
            return  # Ignore a stale result card rather than navigating another occurrence.
        calculate(datetime.fromisoformat(step["period"]["start"]).date())
    pending_cycle_cards[cid] = (slot, row["card"])
    notebook.select(cycle_tab_widgets[title])
    cycle_tab_views[title]["selected"].set("cycle")
    cycle_tab_views[title]["show"]()


def apply_pending_cycle_card():
    title, mode = visible_view_key()
    cid = CYCLE_READING_IDS.get(title)
    if mode != "cycle" or cid not in pending_cycle_cards or ui_jobs.busy("analysis"):
        return
    context = cycle_reading_cache.get(cid)
    view = cycle_reading_views[cid]
    if context is not None and view.context == context:
        slot, expected_card = pending_cycle_cards.pop(cid)
        view.select_slot(slot, expected_card=expected_card)


cycle_reading_views = {}
for cycle_title, cycle_id in CYCLE_READING_IDS.items():
    cycle_reading_views[cycle_id] = CycleReadingView(
        cycle_tab_views[cycle_title]["cycle_panel"], interpretation_knowledge, lambda: dark_mode,
        on_period_selected=lambda row, title=cycle_title: open_result_card(title, row),
    )
manifested_cycle_reading = cycle_reading_views["life_path"]
seven_cycle_reading = cycle_reading_views["seven_year"]
year_cycle_reading = cycle_reading_views["annual"]
week_cycle_reading = cycle_reading_views["week"]
notebook.bind("<<NotebookTabChanged>>", refresh_visible_view, add="+")

seven_full = FullTableView(tab7_full, "Tableau complet des 7 ans")
year_full = FullTableView(tab_year_full, "Tableau complet de l'année")
week_full = FullTableView(tab_week_full, "Tableau complet de la semaine")

timeline_tab = ttk.Frame(notebook)
notebook.add(timeline_tab, text="Frise chronologique")
global_interpretation_tab = ttk.Frame(notebook)
notebook.add(global_interpretation_tab, text="Lecture globale")

TAB_CLOCK_KEYS = {
    "Chemin de vie": "birth",
    "Cycle 7 ans": "year",
    "Cycle annuel": "fifty",
    "Cycle semaine": "week",
}


def update_clock_tab_highlight(_event=None):
    """Visually link the selected cycle tab with its card in the clock."""
    selected_tab = notebook.select()
    selected_title = notebook.tab(selected_tab, "text") if selected_tab else ""
    active_key = TAB_CLOCK_KEYS.get(selected_title)
    neutral_card_border = "#587086" if dark_mode else "#D9E1E8"

    for key, tile in clock_tiles.items():
        is_active = key == active_key
        accent = tile["accent"]
        tile["frame"].configure(
            highlightthickness=4 if is_active else 2,
            highlightbackground=accent,
            highlightcolor=accent,
        )
        clock_card_labels[key].configure(
            highlightthickness=3 if is_active else 1,
            highlightbackground=accent if is_active else neutral_card_border,
            highlightcolor=accent if is_active else neutral_card_border,
        )


notebook.bind("<<NotebookTabChanged>>", update_clock_tab_highlight, add="+")


def return_to_global_interpretation():
    for interpretation_view in (
        natural_interpretation,
        manifested_interpretation,
        seven_interpretation,
        year_interpretation,
        week_interpretation,
        birth_portrait, secondary_portrait, second_secondary_portrait,
    ):
        interpretation_view.hide_global_return()
    notebook.select(global_interpretation_tab)


def open_global_cycle(cycle_id):
    if cycle_id == "natal":
        notebook.select(cycle_tab_widgets["Ordre naturel"])
        cycle_tab_views["Ordre naturel"]["selected"].set("birth")
        birth_portrait.show_global_return()
        cycle_tab_views["Ordre naturel"]["show"]()
        return
    mapping = {
        "natal": "Ordre naturel",
        "life_path": "Chemin de vie",
        "seven_year": "Cycle 7 ans",
        "annual": "Cycle annuel",
        "week": "Cycle semaine",
    }
    title = mapping.get(cycle_id)
    if not title:
        return
    tab = cycle_tab_widgets[title]
    if notebook.tab(tab, "state") == "disabled":
        return
    view = cycle_tab_views[title]
    target_view = "interpretation" if "interpretation" in view["available"] else "table"
    view["selected"].set(target_view)
    view["show"]()
    interpretation_views = {
        "Ordre naturel": natural_interpretation,
        "Chemin de vie": manifested_interpretation,
        "Cycle 7 ans": seven_interpretation,
        "Cycle annuel": year_interpretation,
        "Cycle semaine": week_interpretation,
    }
    if target_view == "interpretation":
        interpretation_views[title].show_global_return()
    notebook.select(tab)


global_interpretation = GlobalInterpretationView(
    global_interpretation_tab,
    interpretation_knowledge,
    lambda: dark_mode,
    open_global_cycle,
)


def select_timeline_date(selected_moment):
    selected_date = selected_moment.date()
    _display_target_date(selected_date)
    target_time_entry.delete(0, "end")
    target_time_entry.insert(0, selected_moment.strftime("%H:%M"))
    calculate(selected_date)


timeline_view = TimelineView(
    timeline_tab,
    timeline_engine,
    select_timeline_date,
    lambda: dark_mode,
)
for interpretation_view in (
    natural_interpretation,
    manifested_interpretation,
    seven_interpretation,
    year_interpretation,
    week_interpretation,
    birth_portrait, secondary_portrait, second_secondary_portrait,
):
    interpretation_view.set_return_callback(return_to_global_interpretation)

def open_clock_table(title):
    """Open the result sequence associated with a card on the cycle clock."""
    tab = cycle_tab_widgets[title]
    if notebook.tab(tab, "state") == "disabled":
        return

    view = cycle_tab_views[title]
    target_view = "result" if "result" in view["available"] else "table"
    view["selected"].set(target_view)
    view["show"]()
    notebook.select(tab)


def set_joker_mode(active):
    state = "disabled" if active else "normal"
    for title in ("Cycle 7 ans", "Cycle annuel", "Cycle semaine"):
        notebook.tab(cycle_tab_widgets[title], state=state)

    if active:
        notebook.select(cycle_tab_widgets["Ordre naturel"])

    muted = "#A8B0B8"
    for key in ("year", "fifty", "week"):
        tile = clock_tiles[key]
        color = muted if active else tile["accent"]
        tile["frame"].configure(highlightbackground=color)
        tile["title"].configure(background=color)
        for button in tile["buttons"]:
            button.configure(state="disabled" if active else "normal")
    for button in clock_tiles["birth"]["buttons"]:
        button.configure(state="disabled" if active else "normal")


def render_joker_state(birth, target, result):
    set_joker_mode(True)
    hour_state = result["state"]["hour_card"]
    hour_card_error = result["hour_error"]
    ascendant_error = result["ascendant_error"]

    age_var.set(f"{engine.age(birth, target)} ans")
    zodiac_var.set(zodiac_sign(birth))
    set_profile_birth_card("JOKER")
    set_secondary_cards([])
    set_clock_card("birth", life_path_card_var, "—")
    life_path_cycle_var.set("Chemin indisponible")

    for variable in (year_card_var, fifty_card_var, week_card_var):
        variable.set("—")
    for variable in (year_cycle_var, fifty_cycle_var, week_cycle_var):
        variable.set("Cycle indisponible")
    for key in ("year", "fifty", "week"):
        clock_card_labels[key].configure(foreground="#8B949E")

    if hour_state:
        set_clock_card("hour", hour_card_var, hour_state["card"])
        hour_cycle_var.set(
            f'{hour_state["time_local"]} locale\n'
            f'{hour_state["solar_time"]} solaire'
        )
    else:
        set_clock_card("hour", hour_card_var, "—")
        hour_cycle_var.set("Heure ou lieu\nà vérifier")

    message = "Joker — aucune position dans le jeu de 52 cartes"
    natural_results.show_message(message)
    manifested_results.show_message(message)
    natural_full.update(90, display_name="Tableau 0", reference=True)
    manifested_full.update(1, display_name="Tableau 0.1")
    joker_state = result["state"]
    update_interpretation_views(
        result["context"], state=joker_state,
    )
    timeline_view.update(
        birth, target, joker_state,
        parse_birth_time(hour_state["time_local"]) if hour_state else None,
        hour_state.get("place", "") if hour_state else "",
    )

    status = "31 décembre : carte de naissance Joker — cycles ordinaires désactivés."
    if ascendant_error:
        status += f" Ascendant : {ascendant_error}"
    if hour_card_error:
        status += f" Carte de l'heure : {hour_card_error}"
    status_var.set(status)
    refresh_visible_view()

def _wrap_view(name, title, mode):
    wrapped = DeferredView(globals()[name], lambda: visible_view_key() == (title, mode))
    globals()[name] = wrapped
    deferred_views[(title, mode)] = wrapped
    return wrapped


for prefix, title in (("natural", "Ordre naturel"), ("manifested", "Chemin de vie"),
                      ("seven", "Cycle 7 ans"), ("year", "Cycle annuel"),
                      ("week", "Cycle semaine")):
    for suffix, mode in (("full", "table"), ("results", "result"),
                         ("interpretation", "interpretation")):
        _wrap_view(prefix + "_" + suffix, title, mode)
    if title in CYCLE_READING_IDS:
        cycle_reading_views[CYCLE_READING_IDS[title]] = _wrap_view(
            prefix + "_cycle_reading", title, "cycle"
        )
_wrap_view("global_interpretation", "Lecture globale", "")
_wrap_view("timeline_view", "Frise chronologique", "")
_wrap_view("birth_portrait", "Ordre naturel", "birth")
_wrap_view("secondary_portrait", "Ordre naturel", "secondary")
_wrap_view("second_secondary_portrait", "Ordre naturel", "secondary_two")

clock_heading = tk.Frame(clock, background="#EEF3F7")
clock_heading_title = tk.Label(
    clock_heading, text=" HORLOGE DES CYCLES ", font=("Segoe UI", 10, "bold"),
    background="#EEF3F7", foreground="#173F5F", borderwidth=0,
)
clock_heading_title.pack(side="left")
clock.configure(labelwidget=clock_heading)
clock_busy_label = tk.Label(clock_heading, text="", font=("Segoe UI", 9), borderwidth=0)


def show_clock_busy(text):
    clock_busy_label.configure(text=text, background="#151F29" if dark_mode else "#EEF3F7",
                               foreground="#AFC0CE" if dark_mode else "#52606D")
    if text:
        clock_busy_label.pack(side="left", padx=(10, 8))
    else:
        clock_busy_label.pack_forget()


clock_busy = BusyIndicator(root, show_clock_busy)
tab_busy = {}
for title, metadata in cycle_tab_views.items():
    variable = tk.StringVar(value="")
    ttk.Label(metadata["toolbar"], textvariable=variable, font=("Segoe UI", 9)).pack(side="right")
    tab_busy[title] = BusyIndicator(root, variable.set)
timeline_busy = BusyIndicator(root, timeline_view.busy_var.set)


def refresh_busy_indicators():
    if "ui_jobs" not in globals():
        return
    clock_busy.set_busy(ui_jobs.busy("analysis"))
    title, mode = visible_view_key()
    for name, indicator in tab_busy.items():
        cid = CYCLE_READING_IDS.get(name)
        indicator.set_busy(name == title and mode == "cycle" and ui_jobs.busy("cycle:" + str(cid)))
    timeline_busy.set_busy(title == "Frise chronologique" and ui_jobs.busy("timeline"))
    refresh_navigation_buttons()


def refresh_temporal_label():
    if current_target_date:
        analysis_group.configure(text="  ANALYSE (" + temporal_label(current_target_date) + ")  ")


def refresh_navigation_buttons():
    if "ui_jobs" not in globals():
        return
    busy = ui_jobs.busy("analysis")
    can_back = navigation_history.current is not None and (navigation_dirty or navigation_history.peek(-1) is not None)
    can_forward = not navigation_dirty and navigation_history.peek(1) is not None
    back_button.configure(state="normal" if can_back and not busy else "disabled")
    forward_button.configure(state="normal" if can_forward and not busy else "disabled")


def record_navigation():
    """Only record committed inputs, never an unfinished edit or stale worker result."""
    if navigation_dirty or navigation_restore is not None or committed_navigation is None:
        return
    title, mode = visible_view_key()
    if not title:
        return
    role = None
    if mode == "cycle":
        cid = CYCLE_READING_IDS.get(title)
        if cid in pending_cycle_cards:
            role = pending_cycle_cards[cid][0]
        elif cid in cycle_reading_views and cycle_reading_views[cid].context == cycle_reading_cache.get(cid):
            role = cycle_reading_views[cid].selected_role
        if role in PLANET_ROWS:
            role = None
    navigation_history.record(dict(committed_navigation, title=title, mode=mode, role=role))
    refresh_navigation_buttons()


def schedule_navigation_record():
    global history_record_job
    if history_record_job is not None:
        root.after_cancel(history_record_job)

    def record():
        global history_record_job
        history_record_job = None
        record_navigation()

    # Coalesce NotebookTabChanged and display-mode events from the same click.
    history_record_job = root.after_idle(record)


def commit_navigation(snapshot):
    global committed_navigation, navigation_dirty, navigation_restore
    committed_navigation = snapshot
    if navigation_restore is not None:
        offset, restored = navigation_restore
        title, mode = restored["title"], restored["mode"]
        if title in cycle_tab_views:
            cycle_tab_views[title]["selected"].set(mode)
            cycle_tab_views[title]["show"]()
        navigation_history.move(offset)
        navigation_restore = None
    navigation_dirty = False
    schedule_navigation_record()
    refresh_navigation_buttons()


def navigate_history(direction):
    global navigation_dirty, navigation_restore, active_profile_id, profile_dirty
    global analysis_time_linked, analysis_place_linked
    if ui_jobs.busy("analysis") or (navigation_dirty and direction > 0):
        return "break"
    record_navigation()
    offset = 0 if navigation_dirty and direction < 0 else direction
    snapshot = navigation_history.peek(offset)
    if snapshot is None:
        return "break"
    navigation_dirty = True
    navigation_restore = (offset, snapshot)
    for close_page in (
        profiles_page_return, events_page_return, relationships_page_return,
        chat_page_return,
    ):
        if close_page:
            close_page()
    for entry, value in ((birth_entry, datetime.fromisoformat(snapshot["birth_date"]).strftime("%d/%m/%Y")),
                         (birth_time_entry, snapshot["birth_time"]), (birth_place_entry, snapshot["birth_place"]),
                         (target_time_entry, snapshot["target_time"])):
        entry.delete(0, "end")
        entry.insert(0, value)
    active_profile_id = snapshot["profile_id"]
    saved_profile = profile_store.get_profile(active_profile_id) if active_profile_id else None
    # Restore historical birth data without overwriting a since-edited/deleted profile.
    if saved_profile is None or any(saved_profile[key] != snapshot[key] for key in ("birth_date", "birth_time", "birth_place")):
        active_profile_id = None
    profile_dirty = False
    profile_store.set_last_profile_id(active_profile_id)
    analysis_time_linked, analysis_place_linked = snapshot["time_linked"], snapshot["place_linked"]
    analysis_place_var.set(snapshot["target_place"])
    hide_place_suggestions()
    _refresh_profile_menu()
    title, mode = snapshot["title"], snapshot["mode"]
    tab = next((tab for tab in notebook.tabs() if notebook.tab(tab, "text") == title), None)
    if tab:
        notebook.select(tab)
    if title in cycle_tab_views:
        cycle_tab_views[title]["selected"].set(mode)
        cycle_tab_views[title]["show"]()
    calculate(datetime.fromisoformat(snapshot["target_date"]).date(), restoring_history=True)
    if mode == "cycle" and snapshot["role"]:
        pending_cycle_cards[CYCLE_READING_IDS[title]] = (snapshot["role"], None)
    return "break"


ui_jobs = LatestJobs(root, refresh_busy_indicators)
# A network reply must never delay deterministic clock calculations.  The chat
# therefore owns a separate single-worker queue from the rest of the interface.
chat_jobs = LatestJobs(root)


def request_timeline_periods(args, ready, failed):
    ui_jobs.submit("timeline", lambda: analysis_work.periods(*args), ready, failed)


timeline_view.view.request_periods = request_timeline_periods


def close_jobs(event):
    if event.widget is root:
        ui_jobs.close()
        chat_jobs.close()


root.bind("<Destroy>", close_jobs, add="+")
root.bind("<Alt-Left>", lambda event: navigate_history(-1))
root.bind("<Alt-Right>", lambda event: navigate_history(1))


def refresh_calendar_day():
    refresh_temporal_label()
    root.after(60000, refresh_calendar_day)


root.after(60000, refresh_calendar_day)
apply_theme()
birth_entry.focus()
root.after_idle(load_last_profile)
root.mainloop()
