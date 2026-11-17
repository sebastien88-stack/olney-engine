"""Permanent natal-card portraits, independent of the date being explored."""

import tkinter as tk

from interpretation_ui import CycleInterpretationView, _fmt_date
from interpretation_text import card_focus


class NatalCardView(CycleInterpretationView):
    def _text(self, parent, text, bg, *, muted=False, bold=False, size=11):
        palette = self._palette()
        label = self._label(
            parent, text, bg=bg, fg=palette["muted"] if muted else palette["text"],
            font=("Segoe UI", size, "bold" if bold else "normal"),
            justify="left", anchor="w", wraplength=1000,
        )
        label.pack(fill="x", pady=(0, 7))
        label.bind("<Configure>", lambda event: label.configure(wraplength=max(80, event.width - 8)))
        return label

    def _render_context(self, context):
        p = self._palette()
        card = context["card"]
        profile = self.knowledge.profiles[card["id"]]
        secondary = context["role"] == "secondary"
        if self.return_visible:
            tk.Button(
                self.content, text="← Retour à la lecture globale", command=self._return_to_global,
                background=p["alt"], foreground=p["accent"], activebackground=p["panel"],
                activeforeground=p["text"], relief="flat", cursor="hand2", padx=12, pady=6,
            ).pack(anchor="w", pady=(0, 10))

        title = "CARTE SECONDAIRE" if secondary else "CARTE PRINCIPALE · CARTE DE NAISSANCE"
        if secondary:
            title += " · " + self._planet_name(card["ruler"]).upper()
        self._text(self.content, title, p["bg"], bold=True, size=16)
        self._text(self.content, f"Naissance le {_fmt_date(context['birth_date'])}"
                   + (f" · {context['zodiac_sign']}" if context.get("zodiac_sign") else ""),
                   p["bg"], muted=True, size=10)

        header = self._section(self.content, profile["title"], bg=p["gold_soft"])
        header.pack(fill="x", pady=(4, 12))
        row = tk.Frame(header, background=p["gold_soft"])
        row.pack(fill="x")
        self._card(row, card, p["accent"], large=True).pack(side="left", padx=(0, 16))
        body = tk.Frame(row, background=p["gold_soft"])
        body.pack(side="left", fill="both", expand=True)
        self._text(body, f"{card['label']} — {card_focus(card, 6)}", p["gold_soft"], bold=True)
        if secondary:
            role = (f"Liée à {self._planet_name(card['ruler'])}, maître du signe {context['zodiac_sign']}, "
                    f"cette carte complète l’expression de ta carte de naissance {context['birth_card']['label']}. "
                    "Elle apporte une autre façon d’incarner tes qualités, de réagir et d’aborder les situations. "
                    "C’est une composante durable du profil, et non une carte temporaire de l’horloge.")
        else:
            role = ("Ta carte de naissance est ton Soleil : elle exprime ton identité, ta volonté et "
                    "ce que tu cherches à développer et à manifester. C’est le repère principal du profil, "
                    "celui à partir duquel se déploient les séquences des cycles.")
        self._text(body, role, p["gold_soft"], size=10)

        energy = self._section(self.content, "L’énergie que tu incarnes", bg=p["blue_soft"])
        energy.pack(fill="x", pady=(0, 10))
        self._text(energy, profile["energy"], p["blue_soft"])
        suit = self.knowledge.suits[card["suit"]]
        self._text(energy, f"{suit['name']} · {suit['element']} — {suit['element_reading']['individual']}",
                   p["blue_soft"], muted=True)
        if profile.get("special_note"):
            self._text(energy, profile["special_note"], p["blue_soft"])

        for field, heading, color in (
            ("manifestations", "Dans la vie", "panel"),
            ("constructive", "Vécu constructif", "good"),
            ("difficult", "Vécu difficile", "hard"),
        ):
            section = self._section(self.content, heading, bg=p[color])
            section.pack(fill="x", pady=(0, 10))
            self._text(section, profile[field], p[color])

        other_cards = context["secondary_cards"] if not secondary else [context["birth_card"]]
        if other_cards:
            complement = self._section(self.content, "Les autres couleurs du profil", bg=p["violet_soft"])
            complement.pack(fill="x", pady=(0, 10))
            for other in other_cards:
                label = "Carte de naissance" if "ruler" not in other else "Carte secondaire · " + self._planet_name(other["ruler"])
                self._text(complement, f"{label} — {other['label']} : {card_focus(other, 5)}.", p["violet_soft"])
