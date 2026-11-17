"""Ordered, factual sequence dossier and deterministic cycle-reading prose.

All dates/cards come from the existing engine. The prose is editorial: it
connects energies, not inferred events or inferred lived polarities.
"""

from collections import defaultdict
from copy import deepcopy
from datetime import date

from interpretation_text import card_focus, expression_text, PLANET_IDS, CLOCK_LABELS


CYCLE_TITLES = {"life_path": "Chemin de vie", "seven_year": "Cycle de 7 ans",
                "annual": "Cycle annuel", "week": "Cycle semaine"}
CYCLE_FOCUS = {"life_path": "life_path", "seven_year": "year",
               "annual": "fifty_two_days", "week": "week"}


class CycleCalendarMismatch(ValueError):
    """The existing clock and its calendar rows disagree at an age boundary."""


def timing_at(period, target):
    if target < period["start"]:
        return "upcoming"
    return "past" if target >= period["end"] else "current"


def present_status(reading, today=None):
    """Status against real today, not the explored date; injectable for tests."""
    today = date.today() if today is None else today
    today = date.fromisoformat(today) if isinstance(today, str) else today
    reference = today.isoformat()
    timings = [timing_at(step["period"], reference) for step in reading["steps"]]
    return {"date": reference, "current_step_index": next(
        (i for i, timing in enumerate(timings) if timing == "current"), None
    ), "step_timings": timings}


def transition_text(left, right, knowledge):
    """An articulation between two different stages, not a causal prediction."""
    a, b = left["card"], right["card"]
    source = knowledge.planets[PLANET_IDS[left["sequence_planet"]]]["name"]
    destination = knowledge.planets[PLANET_IDS[right["sequence_planet"]]]["name"]
    if a["rank"] == b["rank"]:
        detail = (f"Une même valeur se retrouve dans une autre couleur : {a['label']} mobilise {card_focus(a)} ; "
                  f"{b['label']} déplace l’accent vers {card_focus(b)}.")
    elif a["suit"] == b["suit"]:
        suit = knowledge.suits[a["suit"]]
        detail = (f"La couleur {suit['name']}–{suit['element']} se prolonge, mais le mouvement évolue : "
                  f"{a['label']} mobilise {card_focus(a)} ; {b['label']} met en avant {card_focus(b)}.")
    else:
        detail = f"{a['label']} mobilise {card_focus(a)} ; {b['label']} déplace l’accent vers {card_focus(b)}."
    if a["rank"] in {"4", "6"} and b["rank"] in {"5", "9"}:
        detail += " Les appuis et la continuité rencontrent alors un besoin de mouvement ou d’achèvement."
    elif a["rank"] in {"3", "5"} and b["rank"] in {"4", "6"}:
        detail += " L’exploration rencontre une recherche d’appuis, de continuité ou d’équilibre."
    elif b["rank"] in {"8", "10"} and a["rank"] not in {"8", "10"}:
        detail += " La nouvelle étape concentre davantage la question de la puissance ou de l’accomplissement."
    return f"De {a['label']} / {source} à {b['label']} / {destination} — {detail}"


def build_cycle_reading(builder, context, cycle_id):
    knowledge = builder.knowledge
    cycle = next(c for c in context["cycles"] if c["id"] == cycle_id)
    target = context["target_date"]
    birth = context["profile"]["birth_card"]
    birth_number = builder._number_by_label[birth["label"]]
    steps = []
    features = []

    def feature(kind, message, refs, indices):
        features.append({"kind": kind, "message": message, "evidence": refs,
                         "step_indices": indices})

    for index, row in enumerate(cycle["sequence_cards"]):
        detail = builder._cycle_context(
            cycle_id=cycle_id, parent=cycle["parent"], scope=cycle["scope"],
            series_id=cycle["series_id"], reference_series_id=cycle["position"]["reference_series_id"],
            active_label=row["label"], sequence_planet=row["sequence_planet"],
            birth_number=birth_number, period=row["period"], history=context["profile_history"],
            profile_key=context["profile"]["profile_key"],
        )
        card = detail["active_card"]
        planet = knowledge.planets[PLANET_IDS[row["sequence_planet"]]]
        profile = knowledge.profiles[card["id"]]
        step = {
            "index": index, "card": card, "sequence_planet": row["sequence_planet"],
            "period": deepcopy(row["period"]), "timing": timing_at(row["period"], target),
            "occurrence_id": detail["occurrence_id"], "position": detail["position"],
            "lived_polarity": detail["lived_polarity"], "lived_evidence": detail["lived_evidence"],
            "title": profile["title"],
            "summary": (f"{card['label']}, carte {planet['name']}, incarne {card_focus(card)}. "
                        f"Cette énergie s’exprime à travers {', '.join(planet['keywords'][:3])}."),
            "expression": expression_text(detail, knowledge),
            "from_previous": None, "into_next": None, "badges": [],
            "evidence": [f"cycles.{cycle_id}.sequence_cards.{index}", card["profile_ref"],
                         f"knowledge_bundle.planets.{PLANET_IDS[row['sequence_planet']]}"]
        }
        position = step["position"]
        refs = [f"cycle_reading.steps.{index}.card", f"cycle_reading.steps.{index}.position"]
        if position["zone"] == "couronne":
            step["badges"].append("♛ Couronne")
            feature("crown", f"{card['label']} / {planet['name']} occupe la Couronne : cette étape porte une influence dominante dans la séquence.", refs + ["rule:special_cards"], [index])
        if position["context_amplified"]:
            name = knowledge.planets[PLANET_IDS[position["context_planets"][0]]]["name"]
            step["badges"].append(f"◇ {name} ×2")
            feature("double_planet", f"{card['label']} / {planet['name']} : la case {name}/{name} amplifie cette couleur de contexte, distincte de la fonction de séquence.", refs + ["rule:positions"], [index])
        if "semi_fixed" in card["special"]:
            step["badges"].append("↔ Semi-fixe")
            feature("semi_fixed", f"{card['label']} / {planet['name']} exprime une nature duale : ses deux pôles participent au vécu de l’étape.", refs + ["rule:mobility"], [index])
        if "fixed" in card["special"]:
            step["badges"].append("◆ Fixe")
            feature("fixed", f"{card['label']} / {planet['name']} mobilise une énergie fortement ancrée, liée à sa nature fixe.", refs + ["rule:mobility"], [index])
        if "most_powerful_and_dense" in card["special"]:
            step["badges"].append("R♠ · Maîtrise")
            feature("king_spades", f"R♠ / {planet['name']} concentre la puissance et la densité maximales du jeu, quelle que soit la durée de cette étape.", refs + ["rule:special_cards"], [index])
        if position["home_state"] == "at_reference_position":
            step["badges"].append("⌂ Place d’origine")
            feature("home_position", f"{card['label']} / {planet['name']} est à sa place dans {position['reference_label']} : son énergie s’exprime dans son propre territoire.", refs + ["rule:positions"], [index])
        steps.append(step)

    current = next((s for s in steps if s["timing"] == "current"), None)
    if current is None or current["card"]["id"] != cycle["active_card"]["id"] or current["sequence_planet"] != cycle["sequence_planet"]:
        raise CycleCalendarMismatch(
            "À cette date limite, l’âge calculé par le moteur et les bornes calendaires du tableau ne coïncident pas. "
            "La lecture complète de ce cycle est suspendue pour éviter d’associer la mauvaise carte à la période. "
            "L’horloge et les autres vues conservent leurs calculs habituels."
        )
    transitions = []
    for left, right in zip(steps, steps[1:]):
        articulation = transition_text(left, right, knowledge)
        transition = {"from_index": left["index"], "to_index": right["index"], "text": articulation,
                      "evidence": [f"cycle_reading.steps.{left['index']}.card",
                                   f"cycle_reading.steps.{right['index']}.card", "rule:cycles"]}
        transitions.append(transition)
        left["into_next"] = articulation
        right["from_previous"] = articulation

    by_suit, by_rank = defaultdict(list), defaultdict(list)
    for step in steps:
        by_suit[step["card"]["suit"]].append(step["index"])
        by_rank[step["card"]["rank"]].append(step["index"])
    elements = []
    for sid, indices in by_suit.items():
        suit = knowledge.suits[sid]
        elements.append({"suit": sid, "element": suit["element"], "count": len(indices),
                         "step_indices": indices, "meaning": suit["element_reading"]["cycle"],
                         "evidence": [f"cycle_reading.steps.{i}.card" for i in indices]})
    for rank, indices in by_rank.items():
        if len(indices) > 1:
            labels = ", ".join(steps[i]["card"]["label"] for i in indices)
            feature("shared_rank", f"{labels} partagent une même valeur : le mouvement se retrouve dans plusieurs couleurs du parcours.",
                    [f"cycle_reading.steps.{i}.card" for i in indices], indices)

    beginning = transition_text(steps[0], steps[1], knowledge)
    middle = " ; ".join(f"{s['card']['label']} / {knowledge.planets[PLANET_IDS[s['sequence_planet']]]['name']} : {card_focus(s['card'])}" for s in steps[2:5])
    ending = transition_text(steps[5], steps[6], knowledge)
    summary = [
        f"L’ouverture du parcours — {beginning}",
        f"Le cœur de la séquence met en jeu {middle}. Ces étapes donnent des formes successives à ce qui se développe dans le cycle.",
        f"Les dernières étapes — {ending} Le Résultat {cycle['result']['label']} donne un aboutissement distinct de cette dernière carte planétaire : {card_focus(cycle['result'])}.",
    ]
    here = (f"À la date étudiée, l’étape {current['index'] + 1} sur 7 met au premier plan "
            f"{current['card']['label']} / {knowledge.planets[PLANET_IDS[current['sequence_planet']]]['name']} : {card_focus(current['card'])}.")
    if current["from_previous"]:
        here += " " + current["from_previous"]
    if current["into_next"]:
        here += " " + current["into_next"]
    parent = next((c for c in context["cycles"] if c["id"] == cycle["parent"]), None)
    parent_context = None
    if parent:
        parent_context = {"cycle_id": parent["id"], "at_date": target, "scope": "at_analysis_date_only",
                          "card": deepcopy(parent["active_card"]),
                          "text": f"Repère à la date analysée : {CLOCK_LABELS[parent['id']]} — {parent['active_card']['label']}, {card_focus(parent['active_card'])}.",
                          "evidence": [f"cycles.{parent['id']}.active_card"]}
    reading = {
        "kind": "ordered_cycle_reading", "cycle_id": cycle_id, "title": CYCLE_TITLES[cycle_id],
        "series_id": cycle["series_id"], "target_date": target,
        "period": {"start": steps[0]["period"]["start"], "end": steps[-1]["period"]["end"], "end_exclusive": True},
        "reference_card_id": birth["id"], "current_step_index": current["index"],
        "steps": steps, "transitions": transitions, "summary": summary, "current_summary": here,
        "elements": elements, "features": features, "parent_context": parent_context,
        "moon_card": deepcopy(cycle["moon_card"]), "challenge": deepcopy(cycle["challenge"]),
        "result": deepcopy(cycle["result"]),
        "rule_refs": ["rule:cycles", "rule:roles", "rule:positions", "rule:mobility", "rule:synthesis"],
        "timing_is_not_lived_polarity": True,
        "summary_kind": "editorial_connections_not_observed_events",
    }
    reading["present"] = present_status(reading)
    return reading
