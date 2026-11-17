"""Offline checks for Olney's two JSON contracts and their evidence references.

This is a validator for the deliberately small vocabulary used by our schemas,
not a general JSON Schema implementation. Unsupported keywords fail explicitly.
It verifies structure/references, not the truth of a symbolic interpretation.
"""

from datetime import date
from pathlib import Path
import json


SCHEMA_DIR = Path(__file__).with_name("interpretation") / "schemas"
KEYWORDS = {"$schema", "$id", "$defs", "$ref", "title", "description", "type",
            "required", "properties", "additionalProperties", "const", "enum",
            "oneOf", "items", "minItems", "maxItems", "minimum", "maximum", "format"}


def _is_type(value, name):
    return {"object": isinstance(value, dict), "array": isinstance(value, list),
            "string": isinstance(value, str), "null": value is None,
            "boolean": type(value) is bool, "integer": type(value) is int,
            "number": type(value) in {int, float}}[name]


def _equal(left, right):
    # JSON booleans must not compare equal to numbers as they do in Python.
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    return left == right


def validate_schema(value, schema, *, root=None, path="$"):
    root = schema if root is None else root
    unknown = set(schema) - KEYWORDS
    if unknown:
        raise ValueError(f"Unsupported schema keywords: {sorted(unknown)}")
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"Only local schema references are supported: {ref}")
        target = root
        for key in ref[2:].split("/"):
            target = target[key.replace("~1", "/").replace("~0", "~")]
        validate_schema(value, target, root=root, path=path)
    if "oneOf" in schema:
        matches = 0
        for option in schema["oneOf"]:
            try:
                validate_schema(value, option, root=root, path=path)
                matches += 1
            except ValueError:
                pass
        if matches != 1:
            raise ValueError(f"{path}: expected exactly one schema branch, got {matches}")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, name) for name in types):
            raise ValueError(f"{path}: expected {types}, got {type(value).__name__}")
    if "const" in schema and not _equal(value, schema["const"]):
        raise ValueError(f"{path}: wrong constant")
    if "enum" in schema and not any(_equal(value, item) for item in schema["enum"]):
        raise ValueError(f"{path}: invalid enum {value!r}")
    if isinstance(value, dict):
        missing = set(schema.get("required", [])) - set(value)
        if missing:
            raise ValueError(f"{path}: missing {sorted(missing)}")
        properties = schema.get("properties", {})
        extra = set(value) - set(properties)
        if schema.get("additionalProperties") is False and extra:
            raise ValueError(f"{path}: unexpected fields {sorted(extra)}")
        for key, item in value.items():
            subschema = properties.get(key, schema.get("additionalProperties", {}))
            if isinstance(subschema, dict):
                validate_schema(item, subschema, root=root, path=f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            raise ValueError(f"{path}: invalid item count {len(value)}")
        for index, item in enumerate(value):
            validate_schema(item, schema.get("items", {}), root=root, path=f"{path}[{index}]")
    if type(value) in {int, float}:
        if value < schema.get("minimum", -float("inf")) or value > schema.get("maximum", float("inf")):
            raise ValueError(f"{path}: value outside bounds")
    if isinstance(value, str) and "format" in schema:
        if schema["format"] != "date":
            raise ValueError(f"Unsupported schema format: {schema['format']}")
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError(f"{path}: expected YYYY-MM-DD")


def _schema(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def resolve_evidence(context, reference):
    """Resolve a brief evidence path; cycles use stable IDs, not array offsets."""
    if reference.startswith("rule:"):
        return context["knowledge_bundle"]["rules"][reference]
    if reference.startswith("history:"):
        index = int(reference.split(":", 1)[1])
        if index < 0:
            raise ValueError("Negative history index")
        return context["profile_history"][index]
    if reference.startswith("memory:"):
        return context["personal"]["records"][reference]
    if reference.startswith("event:"):
        return context["personal"]["events"][reference]
    parts = reference.split(".")
    if parts[0] == "cycles" and len(parts) > 1:
        value = next(c for c in context["cycles"] if c["id"] == parts[1])
        parts = parts[2:]
    else:
        value = context
    for part in parts:
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _require_reference(context, reference):
    try:
        resolve_evidence(context, reference)
    except (KeyError, IndexError, StopIteration, TypeError, ValueError) as exc:
        raise ValueError(f"Unresolved evidence: {reference}") from exc


def validate_context(context):
    validate_schema(context, _schema("context.schema.json"))
    validate_personal_context(context)
    validate_cycle_reading(context)
    cycles = context["cycles"]
    if context["joker"]:
        if cycles or context["global_direction"] is not None:
            raise ValueError("Joker must not receive a table interpretation")
    elif [c["id"] for c in cycles] != ["natal", "life_path", "seven_year", "annual", "week"]:
        raise ValueError("Unexpected cycle hierarchy")
    else:
        if len(context["profile"].get("life_path_palette", [])) != 7:
            raise ValueError("Missing permanent life-path palette")
    target = date.fromisoformat(context["target_date"])
    for cycle in cycles:
        if cycle["sequence_reference_card_id"] != context["profile"]["birth_card"]["id"]:
            raise ValueError("Sequence root differs from birth card")
        if cycle["period"]:
            period = cycle["period"]
            if not date.fromisoformat(period["start"]) <= target < date.fromisoformat(period["end"]):
                raise ValueError(f"Target outside active period: {cycle['id']}")
        position = cycle["position"]
        pair = position["context_planets"]
        if position["zone"] == "couronne" and pair:
            raise ValueError("Crown cannot have grid planets")
        if position["context_amplified"] != (len(pair) == 2 and pair[0] == pair[1]):
            raise ValueError("Incorrect double-planet flag")
        for ref in cycle["rule_refs"] + cycle["lived_evidence"]:
            _require_reference(context, ref)
    for observation in context["synthesis"]["observations"]:
        for ref in observation["evidence"]:
            _require_reference(context, ref)
    from interpretation_text import build_element_summary
    from types import SimpleNamespace
    bundle = context["knowledge_bundle"]
    expected_elements = build_element_summary(context, SimpleNamespace(suits=bundle["suits"]))
    if context["synthesis"]["elements"] != expected_elements:
        raise ValueError("Element summary differs from active clock occurrences")
    expected_mapping = {"hearts": "Feu", "clubs": "Air", "diamonds": "Eau", "spades": "Terre"}
    if {sid: info.get("element") for sid, info in bundle["suits"].items()} != expected_mapping:
        raise ValueError("Incorrect Olney element correspondence")
    profile_ids = set()

    def check_card_profiles(value):
        if isinstance(value, dict):
            if "profile_ref" in value:
                cid = value["id"]
                if value["profile_ref"] != f"knowledge_bundle.card_profiles.{cid}":
                    raise ValueError("Card points to another energy profile")
                _require_reference(context, value["profile_ref"])
                profile = resolve_evidence(context, value["profile_ref"])
                if (value["energy_focus"] != profile["movement"] or
                        any(value[field] != profile[field] for field in ("constructive", "difficult"))):
                    raise ValueError("Card summary differs from energy profile")
                sid = value["suit"]
                if value["element"] != expected_mapping[sid] or value["element_ref"] != f"knowledge_bundle.suits.{sid}":
                    raise ValueError("Card element differs from its suit")
                profile_ids.add(cid)
            elif "meaning_status" in value and value.get("id") != "JOKER":
                raise ValueError("Card is missing its energy profile reference")
            for child in value.values():
                check_card_profiles(child)
        elif isinstance(value, list):
            for child in value:
                check_card_profiles(child)

    for key in ("profile", "cycles", "hour_card", "global_direction", "cycle_reading"):
        check_card_profiles(context.get(key))
    if profile_ids != set(bundle["card_profiles"]):
        raise ValueError("Profile bundle must contain exactly the referenced energy profiles")
    sources = context["knowledge_bundle"]["sources"]

    def check_sources(value):
        if isinstance(value, dict):
            for ref in value.get("source_refs", []):
                source_id = ref if isinstance(ref, str) else ref["source_id"]
                if source_id not in sources:
                    raise ValueError(f"Unknown source {source_id}")
            for key, child in value.items():
                if key not in {"profile_history", "personal"}:  # User data is not a knowledge document.
                    check_sources(child)
        elif isinstance(value, list):
            for child in value:
                check_sources(child)
    check_sources(context)


def validate_relationship_context(context):
    """Validate the compact two-subject package used by relationship readings."""
    validate_schema(context, _schema("relationship_context.schema.json"))
    if context.get("compatibility_score") is not None:
        raise ValueError("Relationship contexts must not contain a compatibility score")
    subjects = context["subjects"]
    subject_ids = [item["profile_id"] for item in subjects]
    if len(set(subject_ids)) != 2:
        raise ValueError("A relationship must preserve two distinct subjects")
    clock_ids = [item["profile_id"] for item in context["current_clocks"]]
    if clock_ids != subject_ids:
        raise ValueError("Relationship clocks must follow the two subject identities")
    index = context["permanent_link_index"]
    if index["selected_for_llm"] != len(context["permanent_links"]):
        raise ValueError("Relationship link index does not match the selected links")
    if index["selected_for_llm"] > index["total"]:
        raise ValueError("Selected relationship links exceed all calculated links")
    natural_links = context["natural_order_links"]
    allowed_pairs = {"birth_birth", "first_relationship", "second_relationship"}
    if any(link.get("table_id") != 90 for link in natural_links):
        raise ValueError("Natural comparison must use table 90 only")
    if any(link.get("comparison_pair") not in allowed_pairs for link in natural_links):
        raise ValueError("Unexpected natural-order comparison pair")
    allowed_origins = {"carte_de_naissance", "carte_de_relation"}
    if any(
        link[side].get("origin") not in allowed_origins
        for link in natural_links for side in ("source_card", "target_card")
    ):
        raise ValueError("Natural comparison must use birth and relationship cards only")
    for role in context["annual_relationship_roles"]:
        if role.get("type") != "annual_relationship_role":
            raise ValueError("Unexpected annual relationship role")
        if role.get("role") not in {
            "mercure", "lune_soleil", "vénus", "mars", "jupiter",
            "saturne", "uranus", "neptune", "pluton", "résultat",
        }:
            raise ValueError("Unknown annual relationship role")
    if not context["llm_policy"].get("no_compatibility_score"):
        raise ValueError("Missing no-score doctrine")
    relationship_path = context["relationship_life_path"]
    if relationship_path["reference_card"] != context["relationship_card"]["card"]:
        raise ValueError("Relationship life path must be generated by the relationship card")
    if [row.get("slot") for row in relationship_path["rows"]] != [
        "mercure", "vénus", "mars", "jupiter", "saturne", "uranus",
        "neptune", "défi", "résultat",
    ]:
        raise ValueError("Relationship life path must run from Mercury to Result")


def validate_personal_context(context):
    from personal_context import reading_intent
    from reading_store import HYPOTHESIS_STATES
    subject, personal = context["subject"], context["personal"]
    if subject["key"] != context["profile"]["profile_key"] or subject["origin"]["date"] != context["birth_date"]:
        raise ValueError("Subject differs from calculation")
    intent = context["reading"]["intent"]
    expected = reading_intent({key: intent[key] for key in ("angle", "question", "domain", "include_patterns")}, intent["preferences"])
    if intent != expected:
        raise ValueError("Inconsistent reading intent")
    records = personal["records"]
    for ref, record in records.items():
        if (ref != record["ref"] or ref != f"memory:{record['id']}" or record["subject_key"] != subject["key"]
                or record["reader_key"] != personal["reader_key"]):
            raise ValueError("Memory identity/perspective mismatch")
        states = HYPOTHESIS_STATES if record["kind"] == "hypothesis" else {"reported", "retracted"}
        if record["status"] not in states or (record["kind"] != "hypothesis" and record["source_type"] == "model_proposed"):
            raise ValueError("A model hypothesis cannot be a reported fact")
    expected_exclusions = [ref for ref, r in records.items() if r["status"] in {"rejected", "abandoned", "retracted"}]
    if personal["excluded_refs"] != expected_exclusions:
        raise ValueError("Missing memory exclusions")
    for ref, event in personal["events"].items():
        associated = {f"profile:{event['profile_id']}", f"event:{event['id']}"}
        associated.update(f"profile:{p['profile_id']}" for p in event["participants"])
        if ref != event["ref"] or ref != f"event:{event['id']}" or subject["key"] not in associated:
            raise ValueError("Event belongs to another subject")
    for ref in context["learning_frame"]["resources"] + [context["learning_frame"]["challenge"], context["learning_frame"]["direction"]]:
        if ref:
            _require_reference(context, ref)
    for entry in personal["longitudinal"]["event_states"]:
        _require_reference(context, entry["event_ref"])
    for entry in personal["longitudinal"]["calculated_repetitions"]:
        if len(set(entry["occurrence_ids"])) < 2:
            raise ValueError("A repetition requires distinct periods")
        for ref in entry["event_refs"]:
            _require_reference(context, ref)
    for entry in personal["longitudinal"]["recorded_themes"]:
        for ref in entry["evidence"]:
            _require_reference(context, ref)
            record = resolve_evidence(context, ref)
            if record["kind"] == "hypothesis" or record["status"] != "reported" or entry["theme"] not in record["themes"]:
                raise ValueError("Recorded theme is not an attributed report")


def validate_cycle_reading(context):
    """Check order, facts, chronology and references against the source cycle."""
    from cycle_reading import timing_at, present_status
    reading = context["cycle_reading"]
    if context["reading"]["mode"] != "cycle" or context["joker"]:
        if reading is not None:
            raise ValueError("Unexpected full-cycle reading")
        return
    if reading is None:
        raise ValueError("Missing full-cycle reading")
    cid = context["reading"]["focal_cycle_id"]
    if reading["cycle_id"] != cid or reading["target_date"] != context["target_date"]:
        raise ValueError("Cycle reading differs from requested focus/date")
    cycle = next(c for c in context["cycles"] if c["id"] == cid)
    if reading["series_id"] != cycle["series_id"] or reading["reference_card_id"] != context["profile"]["birth_card"]["id"]:
        raise ValueError("Wrong cycle reading table or root")
    current_indices = []
    for index, (step, row) in enumerate(zip(reading["steps"], cycle["sequence_cards"])):
        if (step["index"] != index or step["card"]["id"] != row["card_id"] or
                step["card"]["label"] != row["label"] or step["sequence_planet"] != row["sequence_planet"] or
                step["period"] != row["period"] or step["position"]["position"] != row["position"]):
            raise ValueError("Cycle step differs from the calculated sequence")
        period = step["period"]
        if period is None or period["end"] <= period["start"]:
            raise ValueError("Missing or empty cycle step period")
        if index and reading["steps"][index - 1]["period"]["end"] != period["start"]:
            raise ValueError("Cycle periods are not contiguous")
        if step["timing"] != timing_at(period, context["target_date"]):
            raise ValueError("Incorrect cycle step timing")
        if step["timing"] == "current":
            current_indices.append(index)
            if (step["card"] != cycle["active_card"] or step["sequence_planet"] != cycle["sequence_planet"] or
                    step["occurrence_id"] != cycle["occurrence_id"] or step["position"] != cycle["position"] or
                    step["lived_polarity"] != cycle["lived_polarity"]):
                raise ValueError("Current step differs from the clock")
        pair = step["position"]["context_planets"]
        if step["position"]["zone"] == "couronne" and pair:
            raise ValueError("Crown step cannot have grid planets")
        if step["position"]["context_amplified"] != (len(pair) == 2 and pair[0] == pair[1]):
            raise ValueError("Incorrect step double-planet flag")
        for ref in step["evidence"] + step["lived_evidence"]:
            _require_reference(context, ref)
    if current_indices != [reading["current_step_index"]]:
        raise ValueError("Expected exactly the highlighted current step")
    if reading["present"] != present_status(reading, reading["present"]["date"]):
        raise ValueError("Present status must follow the real-date snapshot, not the explored date")
    expected_period = {"start": reading["steps"][0]["period"]["start"], "end": reading["steps"][-1]["period"]["end"], "end_exclusive": True}
    if reading["period"] != expected_period:
        raise ValueError("Wrong full-cycle period")
    for field in ("moon_card", "challenge", "result"):
        if reading[field] != cycle[field]:
            raise ValueError("Wrong Moon/challenge/result for the sequence")
    for index, transition in enumerate(reading["transitions"]):
        if transition["from_index"] != index or transition["to_index"] != index + 1:
            raise ValueError("Transitions must connect consecutive steps")
        if (reading["steps"][index]["into_next"] != transition["text"] or
                reading["steps"][index + 1]["from_previous"] != transition["text"]):
            raise ValueError("Step and transition prose differ")
        for ref in transition["evidence"]:
            _require_reference(context, ref)
    covered = []
    for group in reading["elements"]:
        actual = [s["index"] for s in reading["steps"] if s["card"]["suit"] == group["suit"]]
        if group["step_indices"] != actual or group["count"] != len(actual):
            raise ValueError("Element summary must describe the seven ordered steps")
        if group["element"] != context["knowledge_bundle"]["suits"][group["suit"]]["element"]:
            raise ValueError("Wrong cycle element correspondence")
        covered.extend(actual)
        for ref in group["evidence"]:
            _require_reference(context, ref)
    if sorted(covered) != list(range(7)):
        raise ValueError("Missing or duplicated steps in cycle element summary")
    for item in reading["features"]:
        for ref in item["evidence"]:
            _require_reference(context, ref)
    parent = reading["parent_context"]
    if parent:
        source = next(c for c in context["cycles"] if c["id"] == cycle["parent"])
        if parent["cycle_id"] != source["id"] or parent["card"] != source["active_card"] or parent["at_date"] != context["target_date"]:
            raise ValueError("Parent context must describe only the analysis date")
        for ref in parent["evidence"]:
            _require_reference(context, ref)
    for ref in reading["rule_refs"]:
        _require_reference(context, ref)


def validate_llm_output(output, context):
    """Future adapter hook: shape and provenance checks, not semantic truth."""
    validate_schema(output, _schema("llm_output.schema.json"))
    if output["knowledge_version"] != context["knowledge_version"]:
        raise ValueError("Output uses another knowledge version")
    if output["reading_focus"] != context["reading"]["focus"]:
        raise ValueError("Output ignores requested focus")
    if output.get("reading_mode", "current") != context["reading"]["mode"]:
        raise ValueError("Output ignores requested reading mode")
    if output.get("reading_angle", context["reading"]["intent"]["angle"]) != context["reading"]["intent"]["angle"]:
        raise ValueError("Output ignores requested reading angle")
    if context["reading"]["mode"] == "cycle" and not context["joker"]:
        reading = output.get("cycle_reading")
        source = context["cycle_reading"]
        if not reading or reading["cycle_id"] != source["cycle_id"]:
            raise ValueError("Missing requested full-cycle output")
        for index, step in enumerate(reading["steps"]):
            if step["step_index"] != index or step["card_id"] != source["steps"][index]["card"]["id"]:
                raise ValueError("Output cycle steps are not in source order")
            if not step["evidence"]:
                raise ValueError("An interpreted step needs evidence")
            for ref in step["evidence"]:
                _require_reference(context, ref)
        for ref in reading["evidence"]:
            _require_reference(context, ref)
    elif output.get("cycle_reading"):
        raise ValueError("Full-cycle output was not requested")
    for ref in output["rule_ids_used"]:
        if not ref.startswith("rule:"):
            raise ValueError("Expected canonical rule IDs")
        _require_reference(context, ref)
    for claim in output["claims"]:
        if claim["kind"] != "missing_information" and not claim["evidence"]:
            raise ValueError("A claim needs evidence")
        if claim["kind"] in {"symbolic_interpretation", "illustrative_scenario"} and not claim["rule_refs"]:
            raise ValueError("An interpretation needs a rule reference")
        for ref in claim["evidence"] + claim["rule_refs"]:
            _require_reference(context, ref)
        if claim["kind"] in {"user_report", "calculated_fact"}:
            for ref in claim["evidence"]:
                source = resolve_evidence(context, ref)
                if isinstance(source, dict) and (source.get("kind") == "hypothesis" or source.get("status") in {"rejected", "abandoned", "retracted"}):
                    raise ValueError("Hypotheses/retracted reports cannot ground a factual claim")
                if claim["kind"] == "calculated_fact" and ref.startswith(("memory:", "event:", "history:", "personal.records", "personal.events", "personal.profile_notes")):
                    raise ValueError("Reported data is not a calculated fact")
        for ref in claim["rule_refs"]:
            if not ref.startswith("rule:"):
                raise ValueError("Expected a canonical rule reference")
    for block in [output.get("identity", {}), output.get("challenge_result", {}), output.get("learning_synthesis", {}), *output.get("current_cycles", []), *output.get("practice_suggestions", []), *output.get("theme_hypotheses", [])]:
        for ref in block.get("evidence", []):
            _require_reference(context, ref)
            if ref in context["personal"]["excluded_refs"]:
                raise ValueError("An excluded hypothesis is counterevidence, not support")
        for ref in block.get("counterevidence", []) + block.get("rule_refs", []):
            _require_reference(context, ref)
        if any(not ref.startswith("rule:") for ref in block.get("rule_refs", [])):
            raise ValueError("Expected canonical rule IDs")
