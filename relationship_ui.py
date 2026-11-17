"""Scrollable Tk presentation of one deterministic relationship dossier."""

from __future__ import annotations

import tkinter as tk
from brand_theme import LIGHT
from tkinter import ttk


ACCENTS = {
    "primary": "#2F80ED",
    "secondary": "#9B51E0",
    "relationship": "#2C8F60",
    "path": "#D7A83E",
    "clock": "#00A6A6",
}


def _card_ink(card, dark_mode, on_accent=False):
    if on_accent:
        return "#FFFFFF"
    if "♥" in str(card) or "♦" in str(card):
        return "#FF8787" if dark_mode else "#C62828"
    return "#EAF2F8" if dark_mode else "#111827"


class RelationshipDetailView(ttk.Frame):
    """A read-only view; persistence and navigation remain app concerns."""

    def __init__(self, parent, *, dark_mode_getter):
        super().__init__(parent)
        self.dark_mode_getter = dark_mode_getter
        self.package = None
        self._summary_shell = None
        self._relation_panel = None
        self._clock_panel = None
        self._identity = None
        self._identity_panels = []
        self._paths_shell = None
        self._path_panels = []
        self._relationship_text_labels = []
        self._activation_labels = []
        self._detail_text_labels = []
        self._detail_text_labels = []
        self._relationship_path_cards = []
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = tk.Frame(self.canvas)
        self.window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")
        self.content.bind("<Configure>", self._sync_scroll)
        self.canvas.bind("<Configure>", self._fit_width)
        self.canvas.bind("<MouseWheel>", self._wheel)

    @property
    def dark_mode(self):
        return bool(self.dark_mode_getter())

    def _sync_scroll(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _fit_width(self, event):
        width = max(event.width, 760)
        self.canvas.itemconfigure(self.window, width=width)
        self._layout_for_width(width)

    def _layout_for_width(self, width):
        """Reflow dense relation blocks instead of extending past the viewport."""
        if self._summary_shell is not None and self._relation_panel is not None:
            stacked = width < 1220
            self._summary_shell.grid_columnconfigure(0, weight=1, uniform="summary")
            self._summary_shell.grid_columnconfigure(
                1, weight=0 if stacked else 1, uniform="summary"
            )
            self._relation_panel.grid_configure(
                row=0, column=0, columnspan=2 if stacked else 1, sticky="nsew"
            )
            self._clock_panel.grid_configure(
                row=1 if stacked else 0, column=0 if stacked else 1,
                columnspan=2 if stacked else 1, sticky="nsew",
            )
            panel_width = width - 50 if stacked else max(520, (width - 35) // 2)
            relation_wrap = max(300, panel_width - 245)
            activation_wrap = max(420, panel_width - 50)
            for label in self._relationship_text_labels:
                label.configure(wraplength=relation_wrap)
            for label in self._activation_labels:
                label.configure(wraplength=activation_wrap)
        detail_wrap = max(500, width - 95)
        for label in self._detail_text_labels:
            label.configure(wraplength=detail_wrap)

        if self._identity is not None and self._identity_panels:
            stacked = width < 860
            for index, panel in enumerate(self._identity_panels):
                panel.grid_configure(
                    row=index if stacked else 0,
                    column=0 if stacked else index,
                    columnspan=2 if stacked else 1,
                )

        if self._paths_shell is not None and self._path_panels:
            stacked = width < 1350
            for index, panel in enumerate(self._path_panels):
                panel.grid_configure(
                    row=index if stacked else 0,
                    column=0 if stacked else index,
                    columnspan=2 if stacked else 1,
                )

        if self._relationship_path_cards:
            columns = 5 if width < 1040 else 9
            for index, card in enumerate(self._relationship_path_cards):
                card.grid_configure(row=index // columns, column=index % columns)

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self._wheel)
        for child in widget.winfo_children():
            self._bind_wheel(child)

    def _palette(self):
        if self.dark_mode:
            return {
                "page": "#0D141C", "panel": "#151F29", "panel2": "#182631",
                "text": "#E7EEF5", "muted": "#A8BAC8", "border": "#405465",
                "soft": "#233444",
            }
        return {
            "page": LIGHT["bg"], "panel": LIGHT["panel"], "panel2": LIGHT["field"],
            "text": LIGHT["text"], "muted": LIGHT["muted"], "border": LIGHT["line"],
            "soft": LIGHT["raised"],
        }

    def _panel(self, parent, title, accent, *, column=0, columnspan=1):
        palette = self._palette()
        panel = tk.Frame(
            parent, background=palette["panel"], highlightthickness=1,
            highlightbackground=palette["border"], padx=12, pady=11,
        )
        panel.grid(row=0, column=column, columnspan=columnspan, sticky="nsew", padx=5, pady=5)
        tk.Label(
            panel, text=title.upper(), background=accent, foreground="#FFFFFF",
            font=("Segoe UI", 9, "bold"), padx=9, pady=5,
        ).pack(fill="x", pady=(0, 9))
        return panel

    def _card_pill(self, parent, card, caption, accent, *, command=None):
        palette = self._palette()
        frame = tk.Frame(
            parent, background=palette["panel2"], highlightthickness=1,
            highlightbackground=accent, padx=8, pady=6,
        )
        tk.Label(
            frame, text=card, background=palette["panel2"],
            foreground=_card_ink(card, self.dark_mode),
            font=("Segoe UI Symbol", 18, "bold"),
        ).pack()
        caption_label = tk.Label(
            frame, text=caption, background=palette["panel2"],
            foreground=palette["muted"], font=("Segoe UI", 7, "bold"),
            wraplength=120, justify="center",
        )
        caption_label.pack()
        if command is not None:
            frame.configure(cursor="hand2")
            for widget in (frame, *frame.winfo_children()):
                widget.configure(cursor="hand2")
                widget.bind("<Button-1>", lambda _event: command())
                widget.bind("<Return>", lambda _event: command())
        return frame

    def _link_panel(self, title, accent, links, empty_text, *, group_names=None):
        """Render rich relationship roles without compressing them into one line."""
        palette = self._palette()
        shell = tk.Frame(self.content, background=palette["page"])
        shell.pack(fill="x")
        shell.grid_columnconfigure(0, weight=1)
        panel = self._panel(shell, title, accent, column=0)
        if not links:
            tk.Label(
                panel, text=empty_text, background=palette["panel"],
                foreground=palette["muted"], font=("Segoe UI", 9, "italic"),
                padx=12, pady=12,
            ).pack(fill="x")
            return panel

        current_group = None
        for index, link in enumerate(links):
            group = link.get("comparison_pair")
            if group_names and group != current_group:
                current_group = group
                tk.Label(
                    panel, text=group_names.get(group, str(group)).upper(),
                    background=palette["panel"], foreground=accent,
                    font=("Segoe UI", 9, "bold"), anchor="w", pady=6,
                ).pack(fill="x", padx=4, pady=(5 if index else 0, 1))
            row_bg = palette["panel2"] if index % 2 else palette["soft"]
            row = tk.Frame(panel, background=row_bg, padx=10, pady=8)
            row.pack(fill="x", pady=1)
            source = link["source_card"]
            target = link["target_card"]
            arrow = "↔" if link.get("reciprocal") else "→"
            top = tk.Frame(row, background=row_bg)
            top.pack(fill="x")
            tk.Label(
                top,
                text=f'{link["role_label"]}  •  {source["card"]} {arrow} {target["card"]}',
                background=row_bg, foreground=palette["text"],
                font=("Segoe UI Symbol", 9, "bold"), anchor="w",
            ).pack(side="left")
            routes = " + ".join(
                route["axis"].replace("_", " ")
                for route in link.get("routes", [{"axis": link["axis"]}])
            )
            tk.Label(
                top, text=f'{routes} · {link["direction"]}',
                background=row_bg, foreground=palette["muted"],
                font=("Segoe UI", 8), anchor="e",
            ).pack(side="right", padx=(12, 0))
            main = tk.Label(
                row, text=link["interpretation"], background=row_bg,
                foreground=palette["text"], font=("Segoe UI", 9),
                wraplength=1120, justify="left", anchor="w",
            )
            main.pack(fill="x", pady=(4, 2))
            self._detail_text_labels.append(main)
            reading = link.get("role_reading", {})
            for label, key in (("RESSOURCE", "resource"), ("TENSION", "tension")):
                if not reading.get(key):
                    continue
                detail = tk.Label(
                    row, text=f'{label} — {reading[key]}', background=row_bg,
                    foreground=palette["muted"], font=("Segoe UI", 8),
                    wraplength=1120, justify="left", anchor="w",
                )
                detail.pack(fill="x", pady=1)
                self._detail_text_labels.append(detail)
        return panel

    def update(self, package):
        self.package = package
        self.render()

    def apply_theme(self):
        self.render()

    def render(self):
        for child in self.content.winfo_children():
            child.destroy()
        self._summary_shell = None
        self._relation_panel = None
        self._clock_panel = None
        self._identity = None
        self._identity_panels = []
        self._paths_shell = None
        self._path_panels = []
        self._relationship_text_labels = []
        self._activation_labels = []
        self._relationship_path_cards = []
        palette = self._palette()
        self.canvas.configure(background=palette["page"])
        self.content.configure(background=palette["page"])
        if not self.package:
            tk.Label(
                self.content, text="Sélectionne une relation.",
                background=palette["page"], foreground=palette["muted"],
                font=("Segoe UI", 12), pady=30,
            ).pack(fill="x")
            return

        package = self.package
        relation = package.get("relationship", {})
        subjects = package["subjects"]
        heading = tk.Frame(self.content, background=palette["page"], padx=8, pady=8)
        heading.pack(fill="x")
        title = relation.get("title") or f'{subjects[0]["name"]} × {subjects[1]["name"]}'
        tk.Label(
            heading, text=title, background=palette["page"], foreground=palette["text"],
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            heading,
            text=f'{relation.get("relationship_type", "Relation")}  •  '
                 f'Date commune : {package["target_date"]}',
            background=palette["page"], foreground=palette["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        identity = tk.Frame(self.content, background=palette["page"])
        identity.pack(fill="x")
        self._identity = identity
        identity.grid_columnconfigure(0, weight=1, uniform="subject")
        identity.grid_columnconfigure(1, weight=1, uniform="subject")
        for index, subject in enumerate(subjects):
            panel = self._panel(identity, subject["name"], ACCENTS["primary"], column=index)
            self._identity_panels.append(panel)
            top = tk.Frame(panel, background=palette["panel"])
            top.pack(anchor="center")
            self._card_pill(
                top, subject["birth_card"]["card"], "CARTE DE NAISSANCE",
                ACCENTS["primary"],
            ).pack(side="left", padx=(0, 7))
            for card in subject["secondary_cards"]:
                ruler = card.get("ruler", "").upper()
                self._card_pill(
                    top, card["card"], f"SECONDAIRE · {ruler}", ACCENTS["secondary"]
                ).pack(side="left", padx=3)

        summary_shell = tk.Frame(self.content, background=palette["page"])
        summary_shell.pack(fill="x")
        summary_shell.grid_columnconfigure(0, weight=1, uniform="summary")
        summary_shell.grid_columnconfigure(1, weight=1, uniform="summary")
        self._summary_shell = summary_shell
        relation_panel = self._panel(
            summary_shell, "Carte de la relation", ACCENTS["relationship"], column=0
        )
        self._relation_panel = relation_panel
        relation_card = package["relationship_card"]
        card_row = tk.Frame(relation_panel, background=palette["panel"])
        card_row.pack(fill="x")
        relation_pill = self._card_pill(
            card_row, relation_card["card"], "ÉNERGIE CENTRALE DE LA RELATION",
            ACCENTS["relationship"],
        )
        relation_pill.pack(side="left", padx=(0, 12))
        reading = relation_card.get("relationship_reading") or {
            "energy": "Cette carte décrit l’énergie propre créée par la relation."
        }
        reading_frame = tk.Frame(card_row, background=palette["panel"])
        reading_frame.pack(side="left", fill="both", expand=True)
        if reading.get("title"):
            tk.Label(
                reading_frame, text=reading["title"].upper(),
                background=palette["panel"], foreground=ACCENTS["relationship"],
                font=("Segoe UI", 10, "bold"), anchor="w",
            ).pack(fill="x", pady=(0, 5))
        for label, key in (
            ("ÉNERGIE DU LIEN", "energy"),
            ("RESSOURCE", "constructive"),
            ("TENSION", "tension"),
            ("FORMES POSSIBLES", "manifestations"),
        ):
            if not reading.get(key):
                continue
            tk.Label(
                reading_frame, text=label, background=palette["panel"],
                foreground=palette["muted"], font=("Segoe UI", 7, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(4, 0))
            text_label = tk.Label(
                reading_frame, text=reading[key], background=palette["panel"],
                foreground=palette["text"], font=("Segoe UI", 9),
                wraplength=430, justify="left", anchor="w",
            )
            text_label.pack(fill="x")
            self._relationship_text_labels.append(text_label)

        clock_panel = self._panel(
            summary_shell, "Horloges synchronisées", ACCENTS["clock"], column=1
        )
        self._clock_panel = clock_panel
        # ``_panel`` uses ``pack`` for its title; the table therefore lives in
        # its own child, where ``grid`` can safely organise the clock cells.
        clock_grid = tk.Frame(clock_panel, background=palette["panel"])
        clock_grid.pack(fill="x")
        headers = ("PROFIL", "CHEMIN DE VIE", "ANNÉE", "52 JOURS", "JOUR", "HEURE")
        for column, text in enumerate(headers):
            tk.Label(
                clock_grid, text=text, background=palette["soft"],
                foreground=palette["text"], font=("Segoe UI", 8, "bold"),
                padx=7, pady=6,
            ).grid(row=0, column=column, sticky="nsew", padx=1, pady=1)
            clock_grid.grid_columnconfigure(column, weight=1)
        clock_rows = package.get("current_clocks", [])
        for row_index, item in enumerate(clock_rows, start=1):
            values = (
                item["name"], item.get("chemin_de_vie", "—"), item.get("année", "—"),
                item.get("52_jours", "—"), item.get("jour", "—"), item.get("heure") or "—",
            )
            for column, value in enumerate(values):
                tk.Label(
                    clock_grid, text=value, background=palette["panel2"],
                    foreground=_card_ink(value, self.dark_mode),
                    font=("Segoe UI Symbol", 10, "bold" if column else "normal"),
                    padx=7, pady=8,
                ).grid(row=row_index, column=column, sticky="nsew", padx=1, pady=1)

        activations = package.get("temporal_activations", [])
        if activations:
            activation_title_row = len(clock_rows) + 1
            tk.Label(
                clock_grid, text="ACTIVATIONS RELATIONNELLES À CETTE DATE",
                background=palette["panel"], foreground=ACCENTS["clock"],
                font=("Segoe UI", 9, "bold"), pady=8,
            ).grid(
                row=activation_title_row, column=0, columnspan=6,
                sticky="w", padx=4, pady=(6, 0),
            )
            for offset, activation in enumerate(activations[:8], start=1):
                activation_label = tk.Label(
                    clock_grid, text=f'• {activation["interpretation"]}',
                    background=palette["panel2"], foreground=palette["text"],
                    font=("Segoe UI", 9), wraplength=650, justify="left", anchor="w",
                    padx=8, pady=5,
                )
                activation_label.grid(
                    row=activation_title_row + offset, column=0, columnspan=6,
                    sticky="nsew", padx=1, pady=1,
                )
                self._activation_labels.append(activation_label)

        relationship_path = package.get("relationship_life_path") or {}
        relationship_path_rows = relationship_path.get("rows", [])
        if relationship_path_rows:
            relation_path_shell = tk.Frame(self.content, background=palette["page"])
            relation_path_shell.pack(fill="x")
            relation_path_shell.grid_columnconfigure(0, weight=1)
            relation_path_panel = self._panel(
                relation_path_shell, "Chemin de vie de la relation",
                ACCENTS["path"], column=0,
            )
            relation_path_row = tk.Frame(
                relation_path_panel, background=palette["panel"]
            )
            relation_path_row.pack(anchor="center")
            for index, card in enumerate(relationship_path_rows):
                pill = self._card_pill(
                    relation_path_row, card["card"], card["slot"].upper(),
                    ACCENTS["path"],
                )
                pill.grid(row=0, column=index, padx=2, pady=2)
                self._relationship_path_cards.append(pill)

        links = [
            item for item in package.get("permanent_links", [])
            if item.get("table") == "ordre_manifeste"
            and item.get("source_card", {}).get("origin") == "carte_de_naissance"
            and item.get("target_card", {}).get("origin") == "carte_de_naissance"
        ]
        self._link_panel(
            "Structure relationnelle · ordre manifesté", "#6C7FA3", links[:24],
            "Aucune correspondance planétaire directe n’apparaît entre ces deux "
            "cartes de naissance dans l’ordre manifesté.",
        )

        natural_group_names = {
            "birth_birth": (
                f'Cartes de naissance · {subjects[0]["name"]} et {subjects[1]["name"]}'
            ),
            "first_relationship": (
                f'{subjects[0]["name"]} et la carte de relation '
                f'{package["relationship_card"]["card"]}'
            ),
            "second_relationship": (
                f'{subjects[1]["name"]} et la carte de relation '
                f'{package["relationship_card"]["card"]}'
            ),
        }
        self._link_panel(
            "Comparatif · ordre naturel", "#3F7C85",
            package.get("natural_order_links", [])[:36],
            "Aucune correspondance de distance 1 à 9 n’apparaît dans l’ordre naturel "
            "pour ces trois comparaisons.",
            group_names=natural_group_names,
        )

        annual_roles = package.get("annual_relationship_roles", [])
        annual_shell = tk.Frame(self.content, background=palette["page"])
        annual_shell.pack(fill="x")
        annual_shell.grid_columnconfigure(0, weight=1)
        annual_panel = self._panel(
            annual_shell, "Rôle de chacun dans l’année de l’autre", "#8B6FA8", column=0
        )
        if not annual_roles:
            tk.Label(
                annual_panel,
                text=(
                    "À cette date, aucune carte de naissance ou carte secondaire de "
                    "l’un n’apparaît dans les neuf positions du chemin annuel de l’autre."
                ),
                background=palette["panel"], foreground=palette["muted"],
                font=("Segoe UI", 9, "italic"), padx=12, pady=12,
            ).pack(fill="x")
        for index, role in enumerate(annual_roles):
            row_bg = palette["panel2"] if index % 2 else palette["soft"]
            row = tk.Frame(annual_panel, background=row_bg, padx=10, pady=8)
            row.pack(fill="x", pady=1)
            tk.Label(
                row,
                text=(
                    f'{role["appearing_subject"]} est {role["role_label"]} pour '
                    f'{role["host_subject"]}  •  {role["card"]}'
                ),
                background=row_bg, foreground=palette["text"],
                font=("Segoe UI Symbol", 9, "bold"), anchor="w",
            ).pack(fill="x")
            main = tk.Label(
                row, text=role["interpretation"], background=row_bg,
                foreground=palette["text"], font=("Segoe UI", 9),
                wraplength=1120, justify="left", anchor="w",
            )
            main.pack(fill="x", pady=(4, 2))
            self._detail_text_labels.append(main)
            for label, key in (("RESSOURCE", "resource"), ("TENSION", "tension")):
                detail = tk.Label(
                    row, text=f'{label} — {role["role_reading"][key]}',
                    background=row_bg, foreground=palette["muted"],
                    font=("Segoe UI", 8), wraplength=1120,
                    justify="left", anchor="w",
                )
                detail.pack(fill="x", pady=1)
                self._detail_text_labels.append(detail)
        paths_shell = tk.Frame(self.content, background=palette["page"])
        paths_shell.pack(fill="x")
        self._paths_shell = paths_shell
        paths_shell.grid_columnconfigure(0, weight=1, uniform="path")
        paths_shell.grid_columnconfigure(1, weight=1, uniform="path")
        for index, subject in enumerate(subjects):
            panel = self._panel(
                paths_shell, f'Chemin de vie · {subject["name"]}', ACCENTS["path"],
                column=index,
            )
            self._path_panels.append(panel)
            path = subject["life_path"]
            row = tk.Frame(panel, background=palette["panel"])
            row.pack(anchor="center")
            for card in path["palette"]:
                self._card_pill(
                    row, card["card"], card["slot"].upper(), ACCENTS["path"]
                ).pack(side="left", padx=2)

        common_events = package.get("common_events", [])
        if common_events:
            event_shell = tk.Frame(self.content, background=palette["page"])
            event_shell.pack(fill="x")
            event_panel = self._panel(
                event_shell, "Événements communs enregistrés", "#8D6E63", column=0
            )
            for event in common_events:
                event_bg = palette["panel2"]
                row = tk.Frame(event_panel, background=event_bg, padx=8, pady=7)
                row.pack(fill="x", pady=1)
                tk.Label(
                    row, text=event.get("date_start", "—"), background=event_bg,
                    foreground=palette["muted"], font=("Segoe UI", 9, "bold"), width=13,
                ).pack(side="left")
                tk.Label(
                    row, text=event.get("title", "Événement"), background=event_bg,
                    foreground=palette["text"], font=("Segoe UI", 9, "bold"), anchor="w",
                ).pack(side="left", fill="x", expand=True)

        notes = str(relation.get("notes") or "").strip()
        if notes:
            notes_shell = tk.Frame(self.content, background=palette["page"])
            notes_shell.pack(fill="x")
            panel = self._panel(notes_shell, "Notes sur la relation", "#7A8B99", column=0)
            tk.Label(
                panel, text=notes, background=palette["panel"], foreground=palette["text"],
                font=("Segoe UI", 9), wraplength=1000, justify="left", anchor="w",
            ).pack(fill="x")

        self._bind_wheel(self.content)
        self._layout_for_width(max(self.canvas.winfo_width(), 760))
        self._sync_scroll()
