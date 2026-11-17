"""Deterministic editorial summaries, shared by the local UI and the LLM dossier.

No card calculation and no free-form prediction lives here. Observations retain
their evidence paths; active energy profiles are separate from archived drafts.
"""

from collections import defaultdict


CLOCK_LABELS = {"natal": "Naissance", "life_path": "Chemin de vie", "seven_year": "Année", "annual": "52 jours", "week": "Jour", "hour": "Heure"}
PLANET_IDS = {"lune": "moon", "soleil": "sun", "mercure": "mercury", "vénus": "venus", "mars": "mars", "jupiter": "jupiter", "saturne": "saturn", "uranus": "uranus", "neptune": "neptune", "pluton": "pluto"}


def card_focus(card, limit=3):
    """Prefer an incarnated faculty to a literal external person for court cards."""
    return card.get("energy_focus") or card.get("incarnated_faculty") or ", ".join(card.get("keywords", [])[:limit])


def card_essential(card, knowledge, *, permanent=False):
    profile = knowledge.profiles.get(card["id"])
    if profile:
        suit = knowledge.suits[card["suit"]]
        paragraphs = [profile["energy"],
                      f"{suit['name']} · {suit['element']} — {suit['element_reading']['individual']}"]
        if profile.get("special_note"):
            paragraphs.append(profile["special_note"])
        return "\n\n".join(paragraphs)
    opening = f"{card['label']} met au premier plan {card_focus(card, 5)}."
    movement = knowledge.editorial["rank_movements"].get(card.get("rank"), "")
    theme = knowledge.editorial["suit_themes"].get(card.get("suit"), {})
    sentences = [opening, movement]
    if theme:
        sentences.append(f"Cette dynamique concerne notamment {theme['facets']}.")
    if "semi_fixed" in card.get("special", []):
        sentences.append("Sa nature semi-fixe apporte une dynamique duale, dont les deux pôles se répondent.")
    if "fixed" in card.get("special", []):
        sentences.append("Sa fixité constitue un repère durable." if permanent else "Cette activation met en avant une qualité fortement ancrée, propre à sa nature fixe.")
    if "most_powerful_and_dense" in card.get("special", []):
        sentences.append("Le Roi de pique porte la puissance et la densité maximales du jeu.")
    return " ".join(s for s in sentences if s)


def expression_text(cycle, knowledge):
    planet = cycle.get("sequence_planet")
    if not planet:
        return "Aucune planète de séquence n’est associée à cette carte."
    pid = PLANET_IDS[planet]
    info = knowledge.planets[pid]
    active = cycle["active_card"]
    return (
        f"{active['label']} est la carte {info['name']} de cette séquence. "
        f"Elle incarne {card_focus(active)}.\n\n"
        f"{knowledge.editorial['planet_modes'][pid]}\n\n"
        f"Repères de {info['name']} : {', '.join(info['keywords'][:6])}. "
        "Cette fonction colore l’expression de la carte ; les planètes de sa case décrivent séparément le contexte."
    )


def build_element_summary(context, knowledge):
    """Count active occurrences, not displays, natal palette or inferred forces."""
    groups = {}
    active = [(c["id"], c["active_card"]) for c in context.get("cycles", []) if c["id"] != "natal"]
    if context.get("hour_card") and not context.get("joker"):
        active.append(("hour", context["hour_card"]["card"]))
    evidence = []
    for cid, card in active:
        suit_id = card.get("suit")
        if suit_id not in knowledge.suits:
            continue
        suit = knowledge.suits[suit_id]
        ref = "hour_card.card" if cid == "hour" else f"cycles.{cid}.active_card"
        group = groups.setdefault(suit_id, {
            "suit": suit_id, "element": suit["element"], "count": 0,
            "cycle_ids": [], "evidence": [], "cards": [],
            "meaning": suit["element_reading"]["cycle"],
        })
        group["count"] += 1
        group["cycle_ids"].append(cid)
        group["cards"].append({"id": card["id"], "label": card["label"], "cycle_id": cid})
        group["evidence"].append(ref)
        evidence.append(ref)
    values = list(groups.values())
    if len(values) == 1:
        group = values[0]
        summary = (f"Les cartes actives partagent la couleur {knowledge.suits[group['suit']]['name']}–{group['element']}. "
                   f"{group['meaning']} Chaque carte en déploie un mouvement propre, de la période longue à l’expression immédiate.")
    elif values:
        layers = []
        for group in values:
            periods = ", ".join(CLOCK_LABELS[cid] for cid in group["cycle_ids"])
            meaning = knowledge.suits[group["suit"]]["element_reading"]["bridge"]
            layers.append(f"{group['element']} ({periods}) : {meaning}")
        summary = "La configuration met en dialogue plusieurs couleurs : " + " ; ".join(layers) + ". Les périodes longues donnent un fond à ce que les temps courts mettent en jeu concrètement."
    else:
        summary = ""
    return {"scope": "active_clock_without_natal_or_palette", "total_active_cards": sum(g["count"] for g in values),
            "groups": values, "summary": summary, "evidence": evidence}


def build_synthesis(context, knowledge):
    cycles = context.get("cycles", [])
    elements = build_element_summary(context, knowledge)
    if not cycles:
        return {"kind": "rule_based_editorial_summary", "paragraphs": ["La lecture du Joker reste en attente de validation."], "observations": [], "elements": elements}
    active = [(c["id"], c["active_card"]) for c in cycles if c["id"] != "natal"]
    hour = context.get("hour_card")
    if hour:
        active.append(("hour", hour["card"]))
    observations = []

    def add(kind, message, evidence, **extra):
        observations.append({"id": f"observation:{len(observations) + 1}", "kind": kind,
                             "message": message, "evidence": evidence, **extra})

    def evidence(cid):
        return "hour_card.card" if cid == "hour" else f"cycles.{cid}.active_card"

    if hour and hour["card"]["id"] == "KS":
        add("king_spades", "R♠ actif à l’heure : une énergie de maîtrise particulièrement dense dans l’expression immédiate.", ["hour_card.card", "rule:special_cards"])

    by_card = defaultdict(list)
    for cid, card in active:
        by_card[card["id"]].append((cid, card))
    for items in by_card.values():
        if len(items) > 1:
            add("active_card_repetition",
                f"{items[0][1]['label']} est active dans plusieurs périodes : {', '.join(CLOCK_LABELS[cid] for cid, _ in items)}. Une même énergie se décline à plusieurs échelles et peut prendre des formes différentes dans le quotidien.",
                [evidence(cid) for cid, _ in items], card_id=items[0][1]["id"])
    natal = context["profile"]["birth_card"]
    secondary_ids = {c["id"] for c in context["profile"]["secondary_cards"]}
    for cid, card in active:
        if card["id"] == natal["id"]:
            add("natal_activation", f"{CLOCK_LABELS[cid]} réactive la carte de naissance {card['label']} : son expression permanente est mise au premier plan.", ["profile.birth_card", evidence(cid)])
        if card["id"] in secondary_ids:
            add("secondary_activation", f"{card['label']}, active dans {CLOCK_LABELS[cid]}, est aussi une carte secondaire natale : une composante du profil passe ainsi au premier plan.", ["profile.secondary_cards", evidence(cid)])

    by_planet = defaultdict(list)
    for cycle in cycles[1:]:
        if cycle.get("sequence_planet"):
            by_planet[cycle["sequence_planet"]].append(cycle)
    for group in elements["groups"]:
        if group["count"] > 1:
            suit = knowledge.suits[group["suit"]]
            add("shared_suit", f"{suit['name']}–{group['element']} relie {', '.join(CLOCK_LABELS[cid] for cid in group['cycle_ids'])}. {group['meaning']} Chaque carte conserve son mouvement propre.", group["evidence"] + [f"knowledge_bundle.suits.{group['suit']}", "rule:synthesis"], element=group["element"], suit=group["suit"])
    for planet, group in by_planet.items():
        if len(group) > 1:
            info = knowledge.planets[PLANET_IDS[planet]]
            add("sequence_planet_repetition", f"La fonction {info['name']} se retrouve dans {', '.join(CLOCK_LABELS[c['id']] for c in group)} : {', '.join(info['keywords'][:3])}. Cette manière d’agir relie les périodes concernées.", [f"cycles.{c['id']}.sequence_planet" for c in group])
    stable = [c for c in cycles[1:] if c["active_card"]["rank"] in {"4", "6"}]
    moving = [c for c in cycles[1:] if c["active_card"]["rank"] in {"5", "9"}]
    if stable and moving:
        add("stability_change_contrast", f"La configuration articule la continuité ({', '.join(c['active_card']['label'] for c in stable)}) et le changement ou l’achèvement ({', '.join(c['active_card']['label'] for c in moving)}). Ces énergies mettent en regard ce qui cherche à se stabiliser et ce qui demande à évoluer.", [evidence(c["id"]) for c in stable + moving])
    for cycle in cycles[1:]:
        cid, card, position = cycle["id"], cycle["active_card"], cycle["position"]
        if position["zone"] == "couronne":
            add("crown", f"{card['label']} active la Couronne dans {CLOCK_LABELS[cid]}. Sa portée est dominante pour cette lecture et reste reliée aux cycles plus longs.", [evidence(cid), f"cycles.{cid}.position.zone"])
        if position.get("context_amplified"):
            name = knowledge.planets[PLANET_IDS[position["context_planets"][0]]]["name"]
            add("double_planet", f"{CLOCK_LABELS[cid]} : la case {name}/{name} amplifie la couleur de cette planète dans le contexte de la carte.", [f"cycles.{cid}.position.context_planets"])
        if position.get("home_state") == "at_reference_position":
            add("home_position", f"{card['label']} est à sa place de référence dans {CLOCK_LABELS[cid]} ({position['reference_label']}).", [f"cycles.{cid}.position"])
        if "semi_fixed" in card.get("special", []):
            add("semi_fixed", f"{CLOCK_LABELS[cid]} : {card['label']} exprime une nature duale, avec un mouvement entre ses deux pôles.", [evidence(cid), "rule:mobility"])
        if "most_powerful_and_dense" in card.get("special", []):
            add("king_spades", f"R♠ actif dans {CLOCK_LABELS[cid]} : puissance et densité maximales dans l’énergie incarnée à cette échelle.", [evidence(cid), "rule:special_cards"])
        elif "fixed" in card.get("special", []):
            add("fixed", f"{CLOCK_LABELS[cid]} met en avant la nature ancrée de {card['label']}. Sa fixité donne à cette énergie un caractère durable.", [evidence(cid), "rule:mobility"])

    focus = context.get("reading", {}).get("focal_cycle_id")
    if focus == "hour":
        paragraphs = ([f"La carte horaire {hour['card']['label']} met au premier plan {card_focus(hour['card'])}. Cette expression immédiate s’inscrit dans la dynamique du jour et des périodes plus longues."] if hour else ["Une heure et un lieu d’analyse sont nécessaires pour une lecture horaire."])
    elif focus:
        selected = next(c for c in cycles if c["id"] == focus)
        paragraphs = [f"{CLOCK_LABELS[focus]} — {selected['active_card']['label']} : {card_focus(selected['active_card'])}. " + knowledge.editorial["planet_modes"][PLANET_IDS[selected["sequence_planet"]]]]
        if focus != "natal":
            paragraphs.append("Ce zoom met l’énergie de la période au premier plan, sur le fond de la carte de naissance et des cycles plus longs.")
    else:
        long, year = cycles[1:3]
        left, right = long["active_card"], year["active_card"]
        if left["suit"] == right["suit"]:
            theme = knowledge.editorial["suit_themes"][left["suit"]]["label"]
            paragraphs = [f"Les deux périodes longues actives partagent un thème : {theme}. {left['label']} porte {card_focus(left)} dans la tranche de treize ans ; {right['label']} met plus particulièrement en avant {card_focus(right)} cette année. La famille est commune, mais chaque carte conserve sa nuance."]
        else:
            paragraphs = [f"La tranche de treize ans met au premier plan {card_focus(left)} avec {left['label']}. Cette année, {right['label']} mobilise {card_focus(right)}. Ces deux énergies se rencontrent dans la manière de vivre la période."]
        repeat = next((o for o in observations if o["kind"] == "sequence_planet_repetition"), None)
        if repeat:
            paragraphs.append(repeat["message"])
        short, day = cycles[3:5]
        paragraphs.append(f"La période de 52 jours précise l’activation actuelle avec {short['active_card']['label']} : {card_focus(short['active_card'])}. Le jour ajoute {day['active_card']['label']} : {card_focus(day['active_card'])}. Ces énergies donnent une forme plus immédiate à la dynamique des périodes longues.")
        if hour:
            paragraphs[-1] += f" À l’heure étudiée, {hour['card']['label']} apporte une tonalité immédiate : {card_focus(hour['card'])}."
        contrast = next((o for o in observations if o["kind"] == "stability_change_contrast"), None)
        if contrast:
            paragraphs.append(contrast["message"])
    return {"kind": "rule_based_editorial_summary", "paragraphs": paragraphs,
            "observations": observations, "elements": elements, "rules_used": ["rule:synthesis", "rule:cycles"],
            "certainty": "symbolic_interpretation_not_event_prediction"}
