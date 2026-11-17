"""Full-cycle reading: a fixed compact position header above scrolling text."""

from datetime import date, timedelta
import tkinter as tk

from interpretation_ui import ScrollableInterpretationView, _fmt_date
from interpretation_text import card_focus
from cycle_reading import present_status


TIMING_LABELS = {"past": "Écoulée", "current": "En cours", "upcoming": "À venir"}


def period_label(period, compact=False):
    start = date.fromisoformat(period["start"])
    last = date.fromisoformat(period["end"]) - timedelta(days=1)
    if start == last:
        return _fmt_date(start.isoformat())
    return (_fmt_date(start.isoformat()) + ("\n→ " if compact else " → ") + _fmt_date(last.isoformat()))


class CycleReadingView(ScrollableInterpretationView):
    def __init__(self, parent, knowledge, dark_mode_getter, today_getter=None, on_period_selected=None):
        self.today_getter = today_getter or date.today
        self.on_period_selected = on_period_selected
        self.present = None
        self.selected_index = None
        self.selected_role = None
        self.step_buttons = []
        self.status_labels = []
        self.step_tiles = []
        self.container = tk.Frame(parent)
        self.container._olney_owns_theme = True
        self.container.pack(fill="both", expand=True)
        # Outside the scroll canvas: the reference stays visible at any scroll.
        self.band = tk.Frame(self.container, padx=14, pady=8)
        self.band.pack(fill="x")
        super().__init__(self.container, knowledge, dark_mode_getter)
        self.container.after(60000, self._check_today)

    def refresh_today(self):
        """Refresh at midnight without moving the inspected card or scroll."""
        if self.context and self.present and self.present["date"] != self.today_getter().isoformat():
            scroll = self.canvas.yview()[0]
            self._render()
            self.canvas.yview_moveto(scroll)

    def _check_today(self):
        self.refresh_today()
        self.container.after(60000, self._check_today)

    def _step_timing(self, index):
        return self.present["step_timings"][index]

    def update(self, context):
        reading = context.get("cycle_reading")
        self.selected_index = reading["current_step_index"] if reading else None
        self.selected_role = None
        super().update(context if reading else None)

    def _text(self, parent, text, *, bg, fg=None, bold=False, size=10):
        p = self._palette()
        label = self._label(parent, text, bg=bg, fg=fg or p["text"],
                            font=("Segoe UI", size, "bold" if bold else "normal"),
                            anchor="w", justify="left", wraplength=1000)
        label.pack(fill="x", pady=(0, 5))
        label.bind("<Configure>", lambda event: label.configure(wraplength=max(80, event.width - 8)))
        return label

    def _render(self):
        p = self._palette()
        self.container.configure(background=p["bg"])
        self.band.configure(background=p["blue_soft"], highlightthickness=1,
                            highlightbackground=p["line"])
        for child in self.band.winfo_children():
            child.destroy()
        if self.context:
            self.band.pack(fill="x", before=self.canvas.master)
        else:
            self.band.pack_forget()
        self.present = None
        self.step_buttons = []
        self.status_labels = []
        self.step_tiles = []
        super()._render()

    def _render_band(self, reading):
        p = self._palette()
        active = reading["steps"][reading["current_step_index"]]
        self._text(self.band,
                   f"{reading['title']}  ·  {active['card']['label']} — carte {self._planet_name(active['sequence_planet'])}  ·  Étape {active['index'] + 1}/7",
                   bg=p["blue_soft"], bold=True, size=12)
        self._text(self.band,
                   f"{period_label(active['period'])}   ·   Analyse au {_fmt_date(reading['target_date'])}",
                   bg=p["blue_soft"], fg=p["muted"], size=9)
        if self.selected_role:
            card = self._support_card(self.selected_role)
            detail = f"Fiche consultée : {card['label']} — {self.selected_role.capitalize()} du cycle"
        else:
            today_index = self.present["current_step_index"]
            if today_index is None:
                detail = "Ce cycle n’est pas en cours aujourd’hui."
            else:
                today_step = reading["steps"][today_index]
                detail = f"En cours aujourd’hui : {today_step['card']['label']} — carte {self._planet_name(today_step['sequence_planet'])}"
        self._text(self.band, detail, bg=p["blue_soft"], fg=p["muted"], size=9)

    def explore_step(self, index):
        """User navigation goes through the app's single analysis date."""
        if self.context and self.on_period_selected and 0 <= index < 7:
            step = self.context["cycle_reading"]["steps"][index]
            self.on_period_selected({"slot": step["sequence_planet"], "card": step["card"]["label"]})

    def select_step(self, index):
        if not self.context or not 0 <= index < 7:
            return
        self.selected_index = index
        self.selected_role = None
        self._render()
        self._scroll_to_detail()

    def _support_card(self, slot):
        reading = self.context["cycle_reading"]
        if slot == "soleil":
            return self.context["profile"]["birth_card"]
        key = {"lune": "moon_card", "défi": "challenge", "résultat": "result"}.get(slot)
        return reading.get(key) if key else None

    def select_slot(self, slot, expected_card=None):
        """Use the occurrence's role, not its label: one card can have two roles."""
        if not self.context:
            return False
        steps = self.context["cycle_reading"]["steps"]
        step = next((item for item in steps if item["sequence_planet"] == slot), None)
        card = step["card"] if step else self._support_card(slot)
        if card is None or (expected_card is not None and card["label"] != expected_card):
            return False
        if step:
            self.select_step(step["index"])
        else:
            self.selected_index = None
            self.selected_role = slot
            self._render()
            self._scroll_to_detail()
        return True

    def _scroll_to_detail(self):
        # This only scrolls; period navigation has already committed its date.
        self.canvas.update_idletasks()
        height = max(1, self.content.winfo_reqheight())
        self.canvas.yview_moveto(max(0, self.detail_box.winfo_y() - 10) / height)

    def _render_context(self, context):
        reading = context["cycle_reading"]
        p = self._palette()
        self.present = present_status(reading, self.today_getter())
        self._render_band(reading)
        summary = self._section(self.content, "Le mouvement du cycle", bg=p["green_soft"], accent=p["good_line"])
        summary.pack(fill="x", pady=(0, 10))
        for paragraph in reading["summary"]:
            self._text(summary, paragraph, bg=p["green_soft"])
        self._text(summary, reading["current_summary"], bg=p["green_soft"], bold=True)

        step = reading["steps"][self.selected_index] if self.selected_index is not None else None
        card = step["card"] if step else self._support_card(self.selected_role)
        profile = self.knowledge.profiles[card["id"]]
        self.detail_box = self._section(self.content, "Étape consultée", bg=p["blue_soft"])
        self.detail_box.pack(fill="x", pady=(0, 10))
        heading = tk.Frame(self.detail_box, background=p["blue_soft"])
        heading.pack(fill="x")
        if step:
            heading_text = f"{step['index'] + 1}. {card['label']} — carte {self._planet_name(step['sequence_planet'])} · {profile['title']}"
            period_text = f"{period_label(step['period'])} · {TIMING_LABELS[self._step_timing(step['index'])]}"
            expression = step["expression"]
        else:
            roles = {
                "lune": ("Lune du cycle", "La Lune accompagne le vécu intérieur du cycle : sensibilité, besoins, réactions et appuis. Cette énergie colore la manière dont les différentes étapes sont ressenties."),
                "soleil": ("Soleil · carte de naissance", "Le Soleil est la carte de naissance, le repère à partir duquel cette séquence se déploie. Il porte l’identité, la volonté et ce que la personne cherche à développer et à manifester."),
                "défi": ("Défi · Pluton", "Le Défi porte l’enjeu de transformation du cycle : ce qui demande à être rencontré, travaillé et intégré. La qualité de cette carte peut elle-même être ce que le parcours invite à développer."),
                "résultat": ("Résultat du cycle", "Le Résultat donne l’aboutissement de la séquence : une énergie vers laquelle contribuent les étapes et le travail du Défi. Il prend sa couleur dans la manière dont le cycle est vécu."),
            }
            role_name, expression = roles[self.selected_role]
            heading_text = f"{card['label']} — {role_name} · {profile['title']}"
            period_text = f"{reading['title']} · {period_label(reading['period'])}"
        self.detail_heading = self._text(heading, heading_text, bg=p["blue_soft"], bold=True, size=12)
        self._text(heading, period_text, bg=p["blue_soft"], fg=p["muted"], size=9)
        self._text(self.detail_box, profile["energy"], bg=p["blue_soft"])
        self._text(self.detail_box, expression, bg=p["blue_soft"])
        suit = self.knowledge.suits[card["suit"]]
        self._text(self.detail_box, f"{suit['name']}–{suit['element']} · {suit['element_reading']['cycle']}", bg=p["blue_soft"], fg=p["muted"])
        if step and step["badges"]:
            self._text(self.detail_box, " · ".join(step["badges"]), bg=p["blue_soft"], fg=p["accent"], bold=True)
        if step:
            position = step["position"]
            if position["zone"] == "couronne":
                location = "Couronne : influence dominante, hors grille planétaire ; la fonction de séquence est conservée."
            else:
                location = "Case " + "/".join(self._planet_name(name) for name in position["context_planets"]) + " : "
                location += "; ".join(f"{self._planet_name(name)} — {', '.join(self._planet_info(name)['keywords'][:3])}" for name in dict.fromkeys(position["context_planets"])) + "."
            if position["home"]:
                location += f" {card['label']} est à sa place de référence."
            elif position.get("owner_card"):
                owner, support = position["owner_card"], position["support_card"]
                location += (f" {card['label']} déplace {owner['label']} ({card_focus(owner)}). "
                             f"{support['label']} occupe sa place d’origine et lui prête une force liée à {card_focus(support)}.")
            self._text(self.detail_box, location, bg=p["blue_soft"], fg=p["muted"])
        elif profile.get("special_note"):
            self._text(self.detail_box, profile["special_note"], bg=p["blue_soft"], fg=p["muted"])
        if step and step["from_previous"]:
            self._text(self.detail_box, "Ce qui précède — " + step["from_previous"], bg=p["blue_soft"])
        if step and step["into_next"]:
            self._text(self.detail_box, "Ce qui suit — " + step["into_next"], bg=p["blue_soft"])
        polarities = tk.Frame(self.detail_box, background=p["blue_soft"])
        polarities.pack(fill="x", pady=(5, 0))
        for index, (field, title, bg, accent) in enumerate((
            ("constructive", "Vécu constructif", p["good"], p["good_line"]),
            ("difficult", "Vécu difficile", p["hard"], p["hard_line"]),
        )):
            box = self._section(polarities, title, bg=bg, accent=accent)
            box.grid(row=0, column=index, sticky="nsew", padx=(0, 5) if index == 0 else (5, 0))
            polarities.columnconfigure(index, weight=1, uniform="branches")
            self._text(box, profile[field], bg=bg)

        path = self._section(self.content, "Le parcours, étape par étape", bg=p["panel"])
        path.pack(fill="x", pady=(0, 10))
        for item in reading["steps"]:
            timing = self._step_timing(item["index"])
            bg = p["good"] if timing == "current" else p["panel"]
            row = tk.Frame(path, background=bg, padx=10, pady=9, highlightthickness=1,
                           highlightbackground=p["good_line"] if timing == "current" else p["line"])
            row.pack(fill="x", pady=(0, 6))
            self.step_tiles.append(row)
            button = tk.Button(row,
                text=f"{item['index'] + 1} · {item['card']['label']} — carte {self._planet_name(item['sequence_planet'])}  ›",
                command=lambda i=item["index"]: self.explore_step(i),
                background=bg, foreground=p["accent"], activebackground=p["alt"],
                activeforeground=p["text"], font=("Segoe UI", 10, "bold"),
                relief="flat", bd=0, anchor="w", cursor="hand2")
            button.pack(anchor="w")
            button.bind("<Return>", lambda event, i=item["index"]: (self.explore_step(i), "break")[1])
            self.step_buttons.append(button)
            self.status_labels.append(self._text(row, TIMING_LABELS[timing] + (
                " · Étape analysée" if item["index"] == reading["current_step_index"] else ""),
                bg=bg, fg=p["good_line"] if timing == "current" else p["muted"], size=9))
            self._text(row, period_label(item["period"]), bg=bg, fg=p["muted"], size=9)
            self._text(row, item["summary"], bg=bg)
            if item["from_previous"]:
                self._text(row, item["from_previous"], bg=bg, fg=p["muted"])
            if item["badges"]:
                self._text(row, " · ".join(item["badges"]), bg=bg, fg=p["accent"], size=9)

        features = self._section(self.content, "Couleurs et particularités du cycle", bg=p["gold_soft"])
        features.pack(fill="x", pady=(0, 10))
        for group in reading["elements"]:
            cards = ", ".join(reading["steps"][i]["card"]["label"] for i in group["step_indices"])
            self._text(features, f"{group['element']} — {cards}. {group['meaning']}", bg=p["gold_soft"])
        for item in reading["features"]:
            self._text(features, "◆ " + item["message"], bg=p["gold_soft"])

        outcome = tk.Frame(self.content, background=p["bg"])
        outcome.pack(fill="x", pady=(0, 10))
        for col, (key, title, intro, bg) in enumerate((
            ("moon_card", "Lune du cycle", "Vécu intérieur, besoins et appuis qui accompagnent la séquence.", p["blue_soft"]),
            ("challenge", "Défi · Pluton", "L’enjeu de transformation à rencontrer au fil du parcours.", p["rose_soft"]),
            ("result", "Résultat du cycle", "L’aboutissement vers lequel contribuent les différentes étapes.", p["green_soft"]),
        )):
            card = reading[key]
            box = self._section(outcome, title, bg=bg)
            box.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 5, 0))
            outcome.columnconfigure(col, weight=1, uniform="outcomes")
            self._text(box, f"{card['label']} — {card_focus(card)}", bg=bg, bold=True, size=11)
            self._text(box, intro, bg=bg, fg=p["muted"])
            self._text(box, card["constructive"], bg=bg)
            self._text(box, card["difficult"], bg=bg, fg=p["muted"])
        if reading["parent_context"]:
            self._text(self.content, reading["parent_context"]["text"], bg=p["bg"], fg=p["muted"])
