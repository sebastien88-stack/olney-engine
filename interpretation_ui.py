"""Tkinter views for Olney's local structured interpretations."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from brand_theme import LIGHT
from tkinter import ttk
from interpretation_text import card_essential, card_focus, expression_text


SYMBOLS = {
    "lune": "☾", "soleil": "☉", "mercure": "☿", "vénus": "♀",
    "mars": "♂", "jupiter": "♃", "saturne": "♄", "uranus": "♅",
    "neptune": "♆", "pluton": "♇",
}

PLANET_ALIASES = {
    "lune": "moon", "soleil": "sun", "mercure": "mercury",
    "vénus": "venus", "venus": "venus", "mars": "mars",
    "jupiter": "jupiter", "saturne": "saturn", "uranus": "uranus",
    "neptune": "neptune", "pluton": "pluto",
}

SUIT_LABELS = {
    "hearts": "Cœur", "clubs": "Trèfle",
    "diamonds": "Carreau", "spades": "Pique",
}

CYCLE_LABELS = {
    "natal": "Ordre naturel",
    "life_path": "Chemin de vie",
    "seven_year": "Cycle 7 ans",
    "annual": "Cycle annuel",
    "week": "Cycle semaine",
}

CLOCK_LABELS = {
    "natal": "Naissance",
    "life_path": "Chemin de vie",
    "seven_year": "Année",
    "annual": "52 jours",
    "week": "Jour",
    "hour": "Heure",
}

SEQUENCE_CYCLE_LABELS = {
    "life_path": "cycle de 13 ans",
    "seven_year": "cycle de 7 ans",
    "annual": "cycle annuel · période de 52 jours",
    "week": "cycle semaine · carte du jour",
}


def _fmt_date(value):
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(value)


class ScrollableInterpretationView:
    """Vertical interpretation surface with responsive width."""

    def __init__(self, parent, knowledge, dark_mode_getter):
        self.knowledge = knowledge
        self.dark_mode_getter = dark_mode_getter
        self.context = None
        self.message = "Calcule les dates pour afficher l’interprétation."
        self.details_open = False

        outer = ttk.Frame(parent)
        outer.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
        self.canvas._olney_owns_theme = True
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self.canvas, padx=18, pady=14)
        self.window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(self.window, width=max(1, event.width)),
        )
        self.canvas.winfo_toplevel().bind_all(
            "<MouseWheel>", ScrollableInterpretationView._dispatch_mousewheel
        )
        self.canvas._olney_interpretation_view = self
        self.content._olney_interpretation_view = self
        self._render()

    @staticmethod
    def _dispatch_mousewheel(event):
        widget = event.widget
        while widget is not None:
            view = getattr(widget, "_olney_interpretation_view", None)
            if view is not None:
                return view._on_mousewheel(event)
            widget = getattr(widget, "master", None)
        return None

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _bind_mousewheel_tree(self, widget):
        widget._olney_interpretation_view = self
        for child in widget.winfo_children():
            self._bind_mousewheel_tree(child)

    def _planet_info(self, name):
        key = PLANET_ALIASES.get((name or "").lower(), (name or "").lower())
        return self.knowledge.planets.get(key, {})

    def _planet_name(self, name):
        info = self._planet_info(name)
        return info.get("name", (name or "").capitalize())

    def _collapsible_details(self, parent, lines):
        p = self._palette()
        frame = tk.Frame(
            parent, background=p["panel"], highlightthickness=1,
            highlightbackground=p["line"], padx=14, pady=10,
        )
        header = tk.Frame(frame, background=p["panel"])
        header.pack(fill="x")
        self._label(
            header, "POURQUOI CETTE LECTURE ?", bg=p["panel"], fg=p["accent"],
            font=("Segoe UI", 9, "bold"), anchor="w",
        ).pack(side="left", fill="x", expand=True)
        toggle = tk.Button(
            header, relief="flat", bd=0, cursor="hand2", padx=10, pady=3,
            background=p["alt"], foreground=p["text"],
            activebackground=p["line"], activeforeground=p["text"],
            font=("Segoe UI", 9, "bold"),
        )
        toggle.pack(side="right")
        body = tk.Frame(frame, background=p["panel"])
        for line in lines:
            self._label(
                body, f"• {line}", bg=p["panel"], fg=p["muted"],
                font=("Segoe UI", 9), justify="left", anchor="w",
                wraplength=1030,
            ).pack(fill="x", pady=2)

        def set_open(opened):
            self.details_open = opened
            if opened:
                body.pack(fill="x", pady=(9, 0))
                toggle.configure(text="Masquer  ▲")
            else:
                body.pack_forget()
                toggle.configure(text="Afficher  ▼")
            frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        toggle.configure(command=lambda: set_open(not self.details_open))
        set_open(self.details_open)
        return frame

    def _palette(self):
        if self.dark_mode_getter():
            return {
                "bg": "#101922", "panel": "#172532", "alt": "#1D2E3C",
                "text": "#E7EEF5", "muted": "#AFC0CE", "line": "#365066",
                "accent": "#5CB6F2", "good": "#173936", "good_line": "#43C2B2",
                "hard": "#3A272C", "hard_line": "#E08A91", "white": "#FFFFFF",
                "crown": "#956BD8", "result": "#7CA54D",
                "blue_soft": "#172532", "gold_soft": "#172532",
                "violet_soft": "#172532", "green_soft": "#172532",
                "rose_soft": "#172532", "card_line": "#365066",
            }
        return {
            "bg": LIGHT["bg"], "panel": LIGHT["panel"], "alt": LIGHT["raised"],
            "text": LIGHT["text"], "muted": LIGHT["muted"], "line": LIGHT["line_soft"],
            "accent": LIGHT["accent"], "good": LIGHT["green_soft"], "good_line": LIGHT["green"],
            "hard": LIGHT["rose_soft"], "hard_line": "#A85E52", "white": LIGHT["white"],
            "crown": "#8054C5", "result": "#789C48",
            "blue_soft": LIGHT["blue_soft"], "gold_soft": LIGHT["gold_soft"],
            "violet_soft": LIGHT["violet_soft"], "green_soft": LIGHT["green_soft"],
            "rose_soft": LIGHT["rose_soft"], "card_line": LIGHT["line"],
        }

    @staticmethod
    def _ink(label):
        return "#D83232" if "♥" in label or "♦" in label else "#111827"

    def _label(self, parent, text, *, bg, fg, font, **kwargs):
        return tk.Label(
            parent, text=text, background=bg, foreground=fg, font=font, **kwargs
        )

    def _section(self, parent, title, bg=None, accent=None):
        p = self._palette()
        bg = bg or p["panel"]
        frame = tk.Frame(
            parent, background=bg, highlightthickness=1,
            highlightbackground=p["line"], padx=14, pady=11,
        )
        self._label(
            frame, title.upper(), bg=bg, fg=accent or p["accent"],
            font=("Segoe UI", 9, "bold"), anchor="w",
        ).pack(fill="x", pady=(0, 7))
        return frame

    def _card(self, parent, card, accent, large=False, command=None):
        p = self._palette()
        label = card.get("label", "—") if card else "—"
        frame = tk.Frame(
            parent, background=p["white"], highlightthickness=3,
            highlightbackground=accent, padx=8, pady=7,
        )
        if command is not None:
            frame.card_button = tk.Button(
                frame, text=label, command=command, cursor="hand2", relief="flat",
                background=p["white"], foreground=self._ink(label),
                activebackground=p["alt"], activeforeground=self._ink(label),
                font=("Segoe UI Symbol", 28 if large else 19, "bold"), width=7 if large else 5,
            )
            frame.card_button.pack(expand=True)
        else:
            self._label(
                frame, label, bg=p["white"], fg=self._ink(label),
                font=("Segoe UI Symbol", 28 if large else 19, "bold"),
                width=7 if large else 5,
            ).pack(expand=True)
        return frame

    def show_message(self, message):
        self.context = None
        self.message = message
        self._render()

    def update(self, context):
        self.context = context
        self.message = None
        self._render()

    def apply_theme(self):
        self._render()

    def _render(self):
        p = self._palette()
        self.canvas.configure(background=p["bg"])
        self.content.configure(background=p["bg"])
        for child in self.content.winfo_children():
            child.destroy()
        if not self.context:
            self._label(
                self.content, self.message or "Aucune interprétation disponible.",
                bg=p["bg"], fg=p["muted"], font=("Segoe UI", 12, "italic"),
                pady=80,
            ).pack(fill="x")
            return
        self._render_context(self.context)
        self._bind_mousewheel_tree(self.content)
        self.content.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(0)

    def _render_context(self, _context):
        raise NotImplementedError


class CycleInterpretationView(ScrollableInterpretationView):
    def __init__(self, parent, knowledge, dark_mode_getter):
        self.return_callback = None
        self.return_visible = False
        super().__init__(parent, knowledge, dark_mode_getter)

    def set_return_callback(self, callback):
        self.return_callback = callback

    def show_global_return(self):
        self.return_visible = True
        if self.context:
            self._render()

    def hide_global_return(self):
        self.return_visible = False

    def _return_to_global(self):
        self.return_visible = False
        if self.return_callback:
            self.return_callback()

    def _render_context(self, cycle):
        p = self._palette()
        active = cycle["active_card"]
        position = cycle["position"]
        sequence = cycle.get("sequence_planet")
        sequence_info = self._planet_info(sequence)

        header = tk.Frame(self.content, background=p["bg"])
        header.pack(fill="x", pady=(0, 10))
        header.columnconfigure(1, weight=1)
        self._card(
            header, active,
            p["crown"] if position["zone"] == "couronne" else p["accent"],
            large=True,
        ).grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 14))
        title_row = tk.Frame(header, background=p["bg"])
        title_row.grid(row=0, column=1, sticky="ew")
        self._label(
            title_row, f"INTERPRÉTATION — {CYCLE_LABELS[cycle['id']].upper()}",
            bg=p["bg"], fg=p["text"], font=("Segoe UI", 16, "bold"), anchor="w",
        ).pack(side="left", fill="x", expand=True)
        if self.return_visible and self.return_callback:
            tk.Button(
                title_row, text="← Retour à la lecture globale",
                command=self._return_to_global, cursor="hand2", relief="flat", bd=0,
                background=p["alt"], foreground=p["text"],
                activebackground=p["line"], activeforeground=p["text"],
                font=("Segoe UI", 9, "bold"), padx=12, pady=6,
            ).pack(side="right")
        period = cycle.get("period") or {}
        period_text = period.get("age_range") or _fmt_date(period.get("date"))
        if not period_text and period.get("start") and period.get("end"):
            period_text = f"{_fmt_date(period['start'])}  →  {_fmt_date(period['end'])}"
        subtitle = f"Carte active : {active['label']}"
        if period_text:
            subtitle += f"   ·   {period_text}"
        self._label(
            header, subtitle, bg=p["bg"], fg=p["muted"],
            font=("Segoe UI", 10), anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(3, 0))

        synthesis = self._section(
            self.content, "Synthèse de la période", bg=p["alt"], accent=p["good_line"]
        )
        synthesis.pack(fill="x", pady=(0, 9))
        core_words = card_focus(active)
        sequence_words = ", ".join(sequence_info.get("keywords", [])[:3])
        summary = (
            f"À l’instant étudié, {active['label']} incarne {core_words} "
            f"dans {CYCLE_LABELS[cycle['id']].lower()}."
        )
        if sequence:
            summary += (
                f" En tant que carte {self._planet_name(sequence)} du cycle en cours, "
                f"elle reçoit une couleur liée à {sequence_words or 'la fonction de cette planète'}."
            )
        if position["zone"] == "couronne":
            summary += " Elle se trouve dans la Couronne : son influence domine l’ensemble du tableau."
        elif position["home"]:
            summary += " Elle est à sa place de référence et exprime plus directement sa nature."
        elif position.get("owner_card"):
            support = position.get("support_card")
            summary += (
                f" Elle déplace {position['owner_card']['label']}"
                + (
                    f", tandis que {support['label']} occupe la place d’origine "
                    f"de {active['label']}."
                    if support else "."
                )
            )
        self._label(
            synthesis, summary, bg=p["alt"], fg=p["text"],
            font=("Segoe UI", 11, "bold"), justify="left", anchor="w",
            wraplength=1040,
        ).pack(fill="x")

        essential_bg = p["blue_soft"]
        essential = self._section(self.content, "L’essentiel", bg=essential_bg)
        essential.pack(fill="x", pady=(0, 9))
        energy_profile = self.knowledge.profiles.get(active["id"], {})
        if energy_profile:
            self._label(
                essential, energy_profile["title"], bg=essential_bg, fg=p["accent"],
                font=("Segoe UI", 12, "bold"), anchor="w", wraplength=1040,
            ).pack(fill="x", pady=(0, 6))
        text = card_essential(active, self.knowledge, permanent=cycle["id"] == "natal")
        self._label(
            essential, text, bg=essential_bg, fg=p["text"], font=("Segoe UI", 10),
            justify="left", anchor="w", wraplength=1040,
        ).pack(fill="x")

        moon = cycle.get("moon_card")
        if moon:
            moon_box = self._section(self.content, "Lune du cycle", bg=p["blue_soft"])
            moon_box.pack(fill="x", pady=(0, 9))
            moon_row = tk.Frame(moon_box, background=p["blue_soft"])
            moon_row.pack(fill="x")
            self._card(moon_row, moon, p["muted"]).pack(side="left", padx=(0, 12))
            self._label(
                moon_row, f"{moon['label']} — {card_focus(moon)}.\n"
                "Cette carte accompagne le vécu intérieur de la séquence : appuis, besoins ou tensions qui se mêlent à l’expression de la carte active.",
                bg=p["blue_soft"], fg=p["text"], font=("Segoe UI", 10),
                justify="left", anchor="w", wraplength=900,
            ).pack(side="left", fill="both", expand=True)

        polarities = tk.Frame(self.content, background=p["bg"])
        polarities.pack(fill="x", pady=(0, 9))
        polarities.columnconfigure((0, 1), weight=1, uniform="polarity")
        for col, title, key, bg, accent in (
            (0, "Vécu constructif", "constructive", p["good"], p["good_line"]),
            (1, "Vécu difficile", "difficult", p["hard"], p["hard_line"]),
        ):
            box = self._section(polarities, title, bg=bg, accent=accent)
            box.grid(row=0, column=col, sticky="nsew", padx=(0, 5) if col == 0 else (5, 0))
            self._label(
                box, active.get(key) or "À documenter.", bg=bg, fg=p["text"],
                font=("Segoe UI", 10), justify="left", anchor="nw", wraplength=485,
            ).pack(fill="both", expand=True)

        for title, field, background in (
            ("Dans la vie", "manifestations", p["gold_soft"]),
            ("Au fil des cycles", "cycles", p["violet_soft"]),
        ):
            if energy_profile.get(field):
                profile_section = self._section(self.content, title, bg=background)
                profile_section.pack(fill="x", pady=(0, 9))
                self._label(
                    profile_section, energy_profile[field], bg=background, fg=p["text"],
                    font=("Segoe UI", 10), justify="left", anchor="w", wraplength=1040,
                ).pack(fill="x")

        middle = tk.Frame(self.content, background=p["bg"])
        middle.pack(fill="x", pady=(0, 9))
        middle.columnconfigure((0, 1), weight=1, uniform="middle")

        expression_title = (
            f"Carte {self._planet_name(sequence).upper()} du cycle en cours"
            if sequence else "Carte du cycle en cours"
        )
        expression_bg = p["violet_soft"]
        expression = self._section(middle, expression_title, bg=expression_bg)
        expression.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        expression_body = expression_text(cycle, self.knowledge)
        self._label(
            expression, expression_body, bg=expression_bg, fg=p["text"],
            font=("Segoe UI", 10), justify="left", anchor="nw", wraplength=485,
        ).pack(fill="both", expand=True)

        territory_bg = p["gold_soft"]
        territory = self._section(middle, "Emplacement tableau", bg=territory_bg)
        territory.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        territory_cards = tk.Frame(territory, background=territory_bg)
        territory_cards.pack(fill="x", pady=(0, 8))
        if position["home"]:
            home_tile = tk.Frame(territory_cards, background=territory_bg)
            home_tile.pack(side="left")
            self._label(
                home_tile, "PLACE D’ORIGINE", bg=territory_bg, fg=p["muted"],
                font=("Segoe UI", 8, "bold"),
            ).pack(pady=(0, 3))
            self._card(home_tile, active, p["good_line"]).pack()
            territory_text = (
                f"{active['label']} occupe sa propre place dans le tableau de référence "
                f"({position.get('reference_label') or 'ordre naturel'}). "
                "Aucune autre carte n’est déplacée dans cette comparaison."
            )
        elif position.get("owner_card"):
            owner = position["owner_card"]
            support = position.get("support_card")
            for heading, card, accent in (
                ("PLACE OCCUPÉE", owner, p["crown"]),
                ("À SA PLACE D’ORIGINE", support, p["good_line"]),
            ):
                if not card:
                    continue
                tile = tk.Frame(territory_cards, background=territory_bg)
                tile.pack(side="left", padx=(0, 18))
                self._label(
                    tile, heading, bg=territory_bg, fg=p["muted"],
                    font=("Segoe UI", 8, "bold"),
                ).pack(pady=(0, 3))
                self._card(tile, card, accent).pack()
            territory_text = (
                f"{active['label']} déplace {owner['label']}. "
                f"Cette place apporte en arrière-plan : {card_focus(owner, 4)}."
            )
            if support:
                territory_text += (
                    f" Dans le même mouvement, {support['label']} occupe la place d’origine "
                    f"de {active['label']} et lui prête une force liée à "
                    f"{card_focus(support, 4)}. Les deux déplacements "
                    "se lisent ensemble, avec les ressources et les tensions de chacune."
                )
        else:
            territory_text = "Position de référence de la carte."
        self._label(
            territory, territory_text, bg=territory_bg, fg=p["text"],
            font=("Segoe UI", 10), justify="left", anchor="nw", wraplength=485,
        ).pack(fill="both", expand=True)

        case = self._section(
            self.content, "Contexte de la case",
            bg=p["blue_soft"],
            accent=p["crown"] if position["zone"] == "couronne" else p["accent"],
        )
        case.pack(fill="x", pady=(0, 9))
        if position["zone"] == "couronne":
            case_text = (
                "♛  COURONNE — ligne la plus puissante, hors du tableau planétaire. "
                "Elle domine la lecture et donne à la carte une portée générale sur le cycle. "
                "La Couronne remplace ici le couple de planètes de case ; seule la planète "
                "de séquence continue de préciser comment la carte agit."
            )
        else:
            planets = position.get("context_planets", [])
            pair = " + ".join(
                f"{SYMBOLS.get(name, '•')} {self._planet_name(name)}" for name in planets
            )
            details = []
            for name in dict.fromkeys(planets):
                info = self._planet_info(name)
                words = ", ".join(info.get("keywords", [])[:6])
                details.append(
                    f"{SYMBOLS.get(name, '•')} {self._planet_name(name)} : "
                    f"{words or info.get('function', 'influence à documenter')}"
                )
            case_text = (
                f"{pair} — ce couple indique OÙ et DANS QUEL CONTEXTE "
                f"{active['label']} évolue. Les deux planètes ont le même statut :\n"
                + "\n".join(details)
            )
            if position.get("context_amplified"):
                case_text += "\nPlanètes identiques : la couleur de cette planète imprègne plus fortement le contexte de la carte."
        self._label(
            case, case_text, bg=p["blue_soft"], fg=p["text"],
            font=("Segoe UI", 10), justify="left", anchor="w",
            wraplength=1040,
        ).pack(fill="x")

        outcome = tk.Frame(self.content, background=p["bg"])
        outcome.pack(fill="x", pady=(0, 9))
        outcome.columnconfigure((0, 1), weight=1, uniform="outcome")
        for col, key, title, accent in (
            (0, "challenge", "Défi · Pluton", p["hard_line"]),
            (1, "result", "Résultat", p["result"]),
        ):
            card = cycle[key]
            box_bg = p["rose_soft"] if key == "challenge" else p["green_soft"]
            box = self._section(outcome, title, bg=box_bg, accent=accent)
            box.grid(row=0, column=col, sticky="nsew", padx=(0, 5) if col == 0 else (5, 0))
            row = tk.Frame(box, background=box_bg)
            row.pack(fill="both", expand=True)
            self._card(row, card, accent).pack(side="left", padx=(0, 10))
            meaning = card_focus(card, 4)
            detail = (
                f"Ce qui demande à être rencontré ou transformé : {meaning}."
                if key == "challenge" else
                f"Direction d’aboutissement : {meaning}."
            )
            self._label(
                row, detail, bg=box_bg, fg=p["text"], font=("Segoe UI", 10),
                justify="left", anchor="nw", wraplength=385,
            ).pack(side="left", fill="both", expand=True)

        owner = position.get("owner_card")
        support = position.get("support_card")
        context_label = (
            "Couronne"
            if position["zone"] == "couronne"
            else " + ".join(self._planet_name(name) for name in position.get("context_planets", []))
        )
        details = [
            f"Tableau utilisé : {cycle['series_id']} · cycle : {CYCLE_LABELS[cycle['id']]}",
            f"Carte active : {active['label']} · planète de séquence : {self._planet_name(sequence) if sequence else 'aucune'}",
            f"Position : {position['position']} · contexte : {context_label or 'aucun'}",
            f"Emplacement tableau : {'position d’origine' if position['home'] else (owner['label'] if owner else 'référence')}",
            f"Carte de soutien : {support['label'] if support else 'aucune'}",
            f"Défi : {cycle['challenge']['label']} · Résultat : {cycle['result']['label']}",
        ]
        self._collapsible_details(self.content, details).pack(fill="x")


class GlobalInterpretationView(ScrollableInterpretationView):
    def __init__(self, parent, knowledge, dark_mode_getter, open_cycle_callback):
        self.open_cycle_callback = open_cycle_callback
        super().__init__(parent, knowledge, dark_mode_getter)

    def _resonance_lines(self, context):
        # The same evidence-backed observations feed the UI and the LLM dossier.
        lines = [
            item["message"] for item in context.get("synthesis", {}).get("observations", [])
            if item["kind"] not in {"sequence_planet_repetition", "stability_change_contrast", "shared_suit"}
        ]
        return lines or ["Aucune résonance particulière détectée par les règles actuelles."]

    def _render_context(self, context):
        p = self._palette()
        self._label(
            self.content, "LECTURE GLOBALE", bg=p["bg"], fg=p["text"],
            font=("Segoe UI", 17, "bold"), anchor="w",
        ).pack(fill="x")
        self._label(
            self.content,
            f"Horloge interprétative au {_fmt_date(context.get('target_date'))}",
            bg=p["bg"], fg=p["muted"], font=("Segoe UI", 10), anchor="w",
        ).pack(fill="x", pady=(2, 11))

        profile_bg = p["blue_soft"]
        profile = self._section(self.content, "Profil essentiel", bg=profile_bg)
        profile.pack(fill="x", pady=(0, 9))
        row = tk.Frame(profile, background=profile_bg)
        row.pack(fill="x")
        birth = context["profile"]["birth_card"]
        birth_tile = self._card(row, birth, p["accent"], command=lambda: self.open_cycle_callback("natal"))
        self.birth_card_button = birth_tile.card_button
        birth_tile.pack(side="left", padx=(0, 12))
        profile_text = (
            f"Soleil / naissance {birth['label']} — "
            f"{card_focus(birth, 4)}."
        )
        if birth.get("suit"):
            suit = self.knowledge.suits[birth["suit"]]
            profile_text += f" {suit['name']}–{suit['element']} : {suit['element_reading']['bridge']}."
        moon = context["profile"].get("moon_card")
        if moon:
            profile_text += (
                f"  Lune {moon['label']} — "
                f"{card_focus(moon, 3)}."
            )
        secondary = context["profile"].get("secondary_cards", [])
        if secondary:
            profile_text += "  Cartes secondaires : " + " ; ".join(
                f"{item['label']} ({card_focus(item, 4)})"
                for item in secondary
            ) + "."
        self._label(
            row, profile_text, bg=profile_bg, fg=p["text"], font=("Segoe UI", 10),
            justify="left", anchor="w", wraplength=900,
        ).pack(side="left", fill="both", expand=True)

        clock_bg = p["gold_soft"]
        clock = self._section(self.content, "Horloge des cycles", bg=clock_bg)
        clock.pack(fill="x", pady=(0, 9))
        clock_row = tk.Frame(clock, background=clock_bg)
        clock_row.pack(fill="x")
        items = list(context["cycles"])
        if context.get("hour_card"):
            items.append({
                "id": "hour", "active_card": context["hour_card"]["card"],
                "sequence_planet": None,
            })
        for index, cycle in enumerate(items):
            tile = tk.Frame(clock_row, background=clock_bg, padx=4)
            tile.grid(row=0, column=index, sticky="nsew")
            clock_row.columnconfigure(index, weight=1, uniform="clock")
            self._label(
                tile, CLOCK_LABELS[cycle["id"]].upper(), bg=clock_bg, fg=p["muted"],
                font=("Segoe UI", 8, "bold"),
            ).pack(pady=(0, 3))
            clickable = cycle["id"] != "hour"
            tk.Button(
                tile, text=cycle["active_card"]["label"],
                command=(
                    (lambda cid=cycle["id"]: self.open_cycle_callback(cid))
                    if clickable else None
                ),
                background=p["white"], foreground=self._ink(cycle["active_card"]["label"]),
                activebackground="#E8EEF3",
                activeforeground=self._ink(cycle["active_card"]["label"]),
                font=("Segoe UI Symbol", 18, "bold"), relief="solid", bd=1,
                highlightthickness=2, highlightbackground=p["card_line"],
                highlightcolor=p["card_line"],
                cursor="hand2" if clickable else "arrow", width=6, pady=6,
            ).pack()
            sequence = cycle.get("sequence_planet")
            self._label(
                tile, SYMBOLS.get(sequence, " "), bg=clock_bg, fg=p["accent"],
                font=("Segoe UI Symbol", 14, "bold"), height=1,
            ).pack(pady=(3, 0))

        thread_bg = p["green_soft"]
        thread = self._section(
            self.content, "Fil rouge actuel", bg=thread_bg, accent=p["good_line"]
        )
        thread.pack(fill="x", pady=(0, 9))
        for index, paragraph in enumerate(context.get("synthesis", {}).get("paragraphs", [])):
            self._label(
                thread, paragraph, bg=thread_bg,
                fg=p["text"] if index == 0 else p["muted"],
                font=("Segoe UI", 10, "bold") if index == 0 else ("Segoe UI", 10),
                justify="left", anchor="w", wraplength=1040,
            ).pack(fill="x", pady=(0, 7))

        elements = context.get("synthesis", {}).get("elements", {})
        if elements.get("groups"):
            element_box = self._section(self.content, "Éléments en présence", bg=p["blue_soft"])
            element_box.pack(fill="x", pady=(0, 9))
            self._label(
                element_box, elements["summary"], bg=p["blue_soft"], fg=p["text"],
                font=("Segoe UI", 10), justify="left", anchor="w", wraplength=1040,
            ).pack(fill="x", pady=(0, 6))
            for group in elements["groups"]:
                suit = self.knowledge.suits[group["suit"]]
                occurrences = " · ".join(
                    f"{item['label']} ({CLOCK_LABELS[item['cycle_id']]})" for item in group["cards"]
                )
                self._label(
                    element_box, f"{suit['symbol']} {suit['name']} — {group['element']} : {occurrences}",
                    bg=p["blue_soft"], fg=p["muted"], font=("Segoe UI", 10),
                    justify="left", anchor="w", wraplength=1040,
                ).pack(fill="x", pady=2)

        cascade_bg = p["violet_soft"]
        cascade = self._section(self.content, "Cascade des cycles", bg=cascade_bg)
        cascade.pack(fill="x", pady=(0, 9))
        for depth, cycle in enumerate(context["cycles"][1:]):
            line = tk.Frame(cascade, background=cascade_bg)
            line.pack(fill="x", padx=(depth * 18, 0), pady=5)
            self._label(
                line, "└─" if depth else "●", bg=cascade_bg, fg=p["accent"],
                font=("Consolas", 11, "bold"), width=3,
            ).pack(side="left")
            body = tk.Frame(line, background=cascade_bg)
            body.pack(side="left", fill="x", expand=True)
            sequence = cycle.get("sequence_planet")
            active = cycle["active_card"]
            challenge = cycle["challenge"]
            result = cycle["result"]
            planet_info = self._planet_info(sequence)
            self._label(
                body,
                f"{CLOCK_LABELS[cycle['id']]} · carte active {active['label']} "
                f"({card_focus(active, 4)})",
                bg=cascade_bg, fg=p["text"], font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).pack(fill="x")
            self._label(
                body,
                f"Carte {self._planet_name(sequence)} · {SYMBOLS.get(sequence, '•')} "
                f"{self._planet_name(sequence)} ({', '.join(planet_info.get('keywords', [])[:4])})\n"
                f"Défi {challenge['label']} ({card_focus(challenge, 4)})  ·  "
                f"Résultat {result['label']} ({card_focus(result, 4)})",
                bg=cascade_bg, fg=p["muted"], font=("Segoe UI", 9),
                justify="left", anchor="w", wraplength=930,
            ).pack(fill="x", pady=(2, 0))

        resonances = self._section(
            self.content, "Résonances remarquables", bg=p["gold_soft"], accent=p["crown"]
        )
        resonances.pack(fill="x", pady=(0, 9))
        for line_text in self._resonance_lines(context):
            self._label(
                resonances, f"◆  {line_text}", bg=p["gold_soft"], fg=p["text"],
                font=("Segoe UI", 10), justify="left", anchor="w", wraplength=1040,
            ).pack(fill="x", pady=2)

        life_path = next(cycle for cycle in context["cycles"] if cycle["id"] == "life_path")
        challenge = life_path["challenge"]
        challenge_box = self._section(
            self.content, "Défi du chemin de vie", bg=p["rose_soft"], accent=p["hard_line"]
        )
        challenge_box.pack(fill="x", pady=(0, 9))
        challenge_row = tk.Frame(challenge_box, background=p["rose_soft"])
        challenge_row.pack(fill="x")
        self._card(challenge_row, challenge, p["hard_line"]).pack(side="left", padx=(0, 12))
        challenge_text = (
            f"{challenge['label']} — {card_focus(challenge, 6)}.\n"
            f"Cette carte désigne le point de transformation majeur du chemin de vie. "
            f"\nRessources à mobiliser — {challenge.get('constructive') or 'À préciser.'}"
            f"\nTensions à traverser — {challenge.get('difficult') or 'À préciser.'}"
        )
        self._label(
            challenge_row, challenge_text, bg=p["rose_soft"], fg=p["text"],
            font=("Segoe UI", 10), justify="left", anchor="w", wraplength=900,
        ).pack(side="left", fill="both", expand=True)

        direction = self._section(
            self.content, "Direction du chemin de vie", bg=p["green_soft"], accent=p["result"]
        )
        direction.pack(fill="x", pady=(0, 9))
        result = context["global_direction"]["result"]
        result_row = tk.Frame(direction, background=p["green_soft"])
        result_row.pack(fill="x")
        self._card(result_row, result, p["result"]).pack(side="left", padx=(0, 12))
        self._label(
            result_row,
            f"{result['label']} — {card_focus(result, 6)}.\n"
            f"En résultat du chemin de vie, cette carte donne une direction centrée sur "
            f"{', '.join(result.get('domains', [])[:5]) or 'ses thèmes fondamentaux'}. "
            f"\nExpression constructive — {result.get('constructive') or 'À préciser.'}"
            f"\nExpression difficile — {result.get('difficult') or 'À préciser.'}",
            bg=p["green_soft"], fg=p["text"], font=("Segoe UI", 10),
            justify="left", anchor="w", wraplength=900,
        ).pack(side="left", fill="both", expand=True)

        detail_lines = [
            f"Ancrage natal : {context['profile']['birth_card']['label']}",
            "Hiérarchie utilisée : " + " → ".join(
                f"{CLOCK_LABELS[cycle['id']]} {cycle['active_card']['label']}"
                for cycle in context["cycles"]
            ),
            "Défis : " + " · ".join(
                f"{CLOCK_LABELS[cycle['id']]} {cycle['challenge']['label']}"
                for cycle in context["cycles"][1:]
            ),
            "Résultats des cycles : " + " · ".join(
                f"{CLOCK_LABELS[cycle['id']]} {cycle['result']['label']}"
                for cycle in context["cycles"][1:]
            ),
            f"Direction finale du chemin de vie : {result['label']}",
            f"Versions : moteur {context.get('engine_version')} · base d’interprétation {context.get('knowledge_version')}",
        ]
        if context.get("hour_card"):
            detail_lines.insert(
                2, f"Carte de l’heure : {context['hour_card']['card']['label']} "
                f"à {context['hour_card'].get('solar_time') or 'heure solaire non disponible'}"
            )
        self._collapsible_details(self.content, detail_lines).pack(fill="x")
