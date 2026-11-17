"""Personal reading payloads and bounded, factual cross-period comparisons.

No model, no persistence and no inferred psychology: proposed themes stay proposed.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import date

from reading_store import DEFAULT_PREFERENCES, PREFERENCE_VALUES


ANGLES = {"temporal", "behavioral", "developmental", "existential"}


def reading_intent(options=None, preferences=None):
    options, preferences = dict(options or {}), {**DEFAULT_PREFERENCES, **(preferences or {})}
    if set(preferences) - set(PREFERENCE_VALUES) or any(v not in PREFERENCE_VALUES[k] for k, v in preferences.items()):
        raise ValueError("Préférences de lecture invalides.")
    if set(options) - {"angle", "question", "domain", "include_patterns"}:
        raise ValueError("Option de lecture inconnue.")
    angle = options.get("angle", "temporal")
    if angle not in ANGLES or type(options.get("include_patterns", False)) is not bool:
        raise ValueError("Angle de lecture invalide.")
    if angle == "existential" and preferences["existential"] == "never":
        raise ValueError("La préférence actuelle désactive la lecture existentielle.")
    question, domain = str(options.get("question", "")), str(options.get("domain", ""))
    if len(question) > 4000 or len(domain) > 120:
        raise ValueError("Demande de lecture trop longue.")
    return {"angle": angle, "question": question, "domain": domain, "preferences": preferences,
            "include_patterns": options.get("include_patterns", angle in {"behavioral", "developmental", "existential"}),
            "existential_policy": preferences["existential"], "mandatory_progression": False,
            "practical_suggestions_are_optional": True}


def memory_history(material):
    """Only self-reported exact observations can supplement the legacy lived API."""
    if not material:
        return []
    key = material["subject"]["key"]
    return [{**{k: record[k] for k in ("occurrence_id", "cycle_id", "card_id", "source_type", "polarity")},
             "memory_ref": record["ref"], "user_note": record["text"][:500]} for record in material.get("records", [])
            if record["subject_key"] == key and record["kind"] == "observation" and record["status"] == "reported"
            and record["source_type"] == "user_reported" and record["perspective"] == "self"
            and record["date_precision"] == "exact" and record.get("polarity") in {"constructive", "difficult", "mixed"}
            and all(record.get(k) for k in ("date_start", "occurrence_id", "cycle_id", "card_id"))]


def attach_personal_context(builder, context, material=None, options=None):
    material = deepcopy(material or {})
    key = context["profile"]["profile_key"]
    subject = material.get("subject", {"key": key, "type": "Humain", "name": "", "relationship_to_user": "unspecified",
        "origin": {"date": context["birth_date"], "time": None, "place": None, "label": "Naissance",
                   "precision": "exact", "source": "Paramètres de calcul", "basis_confirmed": True}})
    if subject["key"] != key or subject["origin"]["date"] != context["birth_date"]:
        raise ValueError("Le sujet et les données calculées ne correspondent pas.")
    if subject["origin"]["precision"] not in {"exact", "approximate"}:
        raise ValueError("Précision de la date d’origine invalide.")
    context["subject"] = subject
    context["profile"]["subject_type"] = subject["type"]
    context["reading"]["intent"] = reading_intent(options, material.get("preferences"))
    records = {record["ref"]: record for record in material.get("records", [])}
    if len(records) > 100 or any(r["subject_key"] != key or r["reader_key"] != material.get("reader_key", "local_user") for r in records.values()):
        raise ValueError("Mémoire trop volumineuse ou issue d’un autre sujet.")
    events = {event["ref"]: event for event in material.get("events", [])}
    if len(events) > 80:
        raise ValueError("Trop d’événements dans cette lecture.")
    # Context is bounded independently of the full stored content; clipping is explicit.
    budget = 24000
    text_fields = ("text", "notes", "people", "tags")
    field_count = 1 + sum(field in row for row in [*records.values(), *events.values()] for field in text_fields)
    field_budget = min(2400, budget // field_count)
    for row in [*records.values(), *events.values()]:
        for field in text_fields:
            if field in row:
                original = str(row[field] or "")
                value = original[:min(field_budget, max(0, budget))]
                budget -= len(value)
                row[field] = value
                if value != original:
                    row.setdefault("truncated_fields", []).append(field)
    context["personal"] = {
        "records": records, "events": events,
        "profile_notes": str(material.get("profile_notes", ""))[:min(3000, max(0, budget))],
        "profile_notes_truncated": len(str(material.get("profile_notes", ""))) > min(3000, max(0, budget)),
        "profile_notes_are_undated_background": True,
        "retrieval": material.get("retrieval", {"not_exhaustive": True, "selection": "none"}),
        "reader_key": material.get("reader_key", "local_user"),
        "hypotheses_are_not_facts": True,
        "unresolved_links": sorted({f"memory:{mid}" for r in records.values()
            for mid in r["evidence_ids"] + r["counterexample_ids"] if f"memory:{mid}" not in records}
            | {f"event:{eid}" for r in records.values() for eid in r["event_ids"] if f"event:{eid}" not in events}),
        "excluded_refs": [ref for ref, r in records.items() if r["status"] in {"rejected", "abandoned", "retracted"}],
        "longitudinal": {"event_states": [], "calculated_repetitions": [], "recorded_themes": [],
                         "hypothesis_refs": [ref for ref, r in records.items() if r["kind"] == "hypothesis"],
                         "not_exhaustive": True, "semantic_inference_performed": False},
    }
    human = subject["type"] == "Humain"
    context["reading"]["subject_policy"] = "person_with_attributed_perspectives" if human else "nonhuman_no_intimate_psychology"
    context["reading"]["origin_assumption"] = (
        "reference_date_only" if subject["origin"]["precision"] == "approximate" else "declared_exact_date")
    if not subject["origin"]["basis_confirmed"]:
        context["reading"]["missing_data"].append("origin_basis")
    context["learning_frame"] = {
        "resources": ["profile.birth_card", "profile.secondary_cards", "profile.life_path_palette"] if not context["joker"] else [],
        "contribution": "Ways these resources may be expressed with others or in the world; no assigned mission.",
        "challenge": "profile.life_path_challenge" if not context["joker"] else None,
        "direction": "profile.life_path_result" if not context["joker"] else None,
        "not_linear_or_compulsory": True, "multiple_threads_allowed": True,
        "no_maturity_score": True,
    }
    if context["reading"]["intent"]["include_patterns"] and not context["joker"]:
        _add_patterns(builder, context)
    return context


def _add_patterns(builder, context):
    longitudinal = context["personal"]["longitudinal"]
    occurrences = defaultdict(dict)
    snapshots = {}
    for ref, event in list(context["personal"]["events"].items())[:12]:
        entry = {"event_ref": ref, "target_date": event["date_start"], "cycles": [], "status": "calculated",
                 "event_state": event["event_state"], "at_event_start_only": True}
        if event["date_precision"] != "exact":
            entry.update(status="not_calculated", reason="approximate_event_date")
        elif date.fromisoformat(event["date_start"]) < date.fromisoformat(context["birth_date"]):
            entry.update(status="not_calculated", reason="before_subject_origin")
        else:
            try:
                if event["date_start"] not in snapshots:
                    state = builder.engine.full_state(context["birth_date"], event["date_start"])
                    # Subject identity only: no events/options, so no recursive comparisons.
                    snapshot = builder.from_state(state, reading_material={"subject": context["subject"]})
                    snapshots[event["date_start"]] = snapshot
                for cycle in snapshots[event["date_start"]]["cycles"]:
                    if cycle["id"] == "natal":
                        continue
                    fact = {"cycle_id": cycle["id"], "card_id": cycle["active_card"]["id"],
                            "label": cycle["active_card"]["label"], "sequence_planet": cycle["sequence_planet"],
                            "period": cycle["period"], "occurrence_id": cycle["occurrence_id"],
                            "zone": cycle["position"]["zone"], "context_planets": cycle["position"]["context_planets"]}
                    entry["cycles"].append(fact)
                    occurrence_key = (cycle["id"], fact["card_id"])
                    occurrences[occurrence_key].setdefault(fact["occurrence_id"], []).append(ref)
            except ValueError as error:
                entry.update(status="not_calculated", reason=str(error))
        longitudinal["event_states"].append(entry)
    for (cid, card), seen in sorted(occurrences.items()):
        if len(seen) > 1:
            longitudinal["calculated_repetitions"].append({
                "kind": "same_card_distinct_periods", "cycle_id": cid, "card_id": card,
                "occurrence_ids": sorted(seen), "event_refs": sorted({ref for refs in seen.values() for ref in refs}),
                "does_not_establish_same_experience": True})
    themes = defaultdict(list)
    for ref, record in context["personal"]["records"].items():
        if record["kind"] in {"observation", "action"} and record["status"] == "reported":
            for theme in record["themes"]:
                themes[theme].append(ref)
    longitudinal["recorded_themes"] = [{"theme": theme, "evidence": refs, "kind": "explicit_record_labels"}
                                          for theme, refs in sorted(themes.items()) if len(refs) > 1]
