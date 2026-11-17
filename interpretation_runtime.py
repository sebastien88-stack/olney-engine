"""Structured interpretation context for Olney.

This module never recalculates cards.  It enriches deterministic facts produced
by :mod:`olney_engine` with the versioned knowledge stored in ``interpretation``.
The resulting dictionary is suitable for the future local interpretation tabs
and for an external LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json
from personal_context import attach_personal_context, memory_history


SCHEMA_VERSION = "0.5.0"
DEFAULT_BASE_PATH = Path(__file__).with_name("interpretation")
PLANET_IDS = {"lune": "moon", "soleil": "sun", "mercure": "mercury", "vénus": "venus", "mars": "mars", "jupiter": "jupiter", "saturne": "saturn", "uranus": "uranus", "neptune": "neptune", "pluton": "pluto"}
PLANET_SLOTS = ("mercure", "vénus", "mars", "jupiter", "saturne", "uranus", "neptune")
FOCUS_CYCLES = {"general": None, "natal": "natal", "life_path": "life_path", "year": "seven_year", "fifty_two_days": "annual", "week": "week", "day": "week", "hour": "hour"}
PERIOD_KINDS = {"natal": "permanent", "life_path": "thirteen_year", "seven_year": "year", "annual": "fifty_two_days", "week": "day"}
SEQUENCE_LABELS = {"natal": "Ordre naturel / référence natale", "life_path": "Chemin de vie", "seven_year": "Séquence de 7 ans", "annual": "Séquence annuelle", "week": "Séquence semaine"}

RANK_FROM_ENGINE = {"A": "A", "V": "J", "D": "Q", "R": "K"}
SUIT_FROM_SYMBOL = {"♥": "H", "♣": "C", "♦": "D", "♠": "S"}


class InterpretationDataError(ValueError):
    """Raised when the interpretation knowledge is incomplete or inconsistent."""


def card_id_from_label(label: str) -> str:
    """Convert an engine label such as ``V♥`` to the stable id ``JH``."""
    if label.upper() == "JOKER":
        return "JOKER"
    if len(label) < 2 or label[-1] not in SUIT_FROM_SYMBOL:
        raise InterpretationDataError(f"Unsupported Olney card label: {label!r}")
    engine_rank = label[:-1]
    rank = RANK_FROM_ENGINE.get(engine_rank, engine_rank)
    return f"{rank}{SUIT_FROM_SYMBOL[label[-1]]}"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InterpretationDataError(f"Cannot load {path}: {exc}") from exc


@dataclass(frozen=True)
class InterpretationKnowledge:
    """Loaded and validated static knowledge used by every interpretation."""

    base_path: Path
    manifest: dict[str, Any]
    cards: dict[str, Any]
    polarities: dict[str, Any]
    ranks: dict[str, Any]
    suits: dict[str, Any]
    planets: dict[str, Any]
    rules: dict[str, Any]
    provenance: dict[str, Any]
    editorial: dict[str, Any]
    profiles: dict[str, Any]

    @classmethod
    def load(cls, base_path: str | Path | None = None) -> "InterpretationKnowledge":
        base = Path(base_path) if base_path is not None else DEFAULT_BASE_PATH
        rule_dir = base / "rules"
        rules = {
            path.stem: _read_json(path)
            for path in sorted(rule_dir.glob("*.json"))
        }
        knowledge = cls(
            base_path=base,
            manifest=_read_json(base / "manifest.json"),
            cards=_read_json(base / "cards.json")["cards"],
            polarities=_read_json(base / "card_polarities.json")["cards"],
            ranks=_read_json(base / "ranks.json")["ranks"],
            suits=_read_json(base / "suits.json")["suits"],
            planets=_read_json(base / "planets.json")["planets"],
            rules=rules,
            provenance=_read_json(base / "provenance.json"),
            editorial=_read_json(base / "editorial.json"),
            profiles=_read_json(base / "card_profiles.json")["cards"],
        )
        knowledge.validate()
        return knowledge

    @property
    def version(self) -> str:
        return str(self.manifest["version"])

    def validate(self) -> None:
        errors: list[str] = []
        if len(self.cards) != 52:
            errors.append(f"cards.json contains {len(self.cards)} cards instead of 52")
        if set(self.cards) != set(self.polarities):
            missing = sorted(set(self.cards) - set(self.polarities))
            extra = sorted(set(self.polarities) - set(self.cards))
            errors.append(f"polarity mismatch; missing={missing}, extra={extra}")
        if set(self.cards) != set(self.profiles):
            errors.append("card_profiles.json must contain exactly the 52 referenced cards")
        for card_id, profile in self.profiles.items():
            for field in ("title", "movement", "energy", "constructive", "difficult", "manifestations", "cycles"):
                if not isinstance(profile.get(field), str) or not profile[field].strip():
                    errors.append(f"{card_id}: missing profile field {field}")
            if profile.get("review_status") not in {"user_validated_pilot", "editorial_extension"}:
                errors.append(f"{card_id}: unknown profile review status")
            if not profile.get("source_refs"):
                errors.append(f"{card_id}: missing profile sources")
            for ref in profile.get("source_refs", []):
                if ref.get("source_id") not in self.provenance["sources"]:
                    errors.append(f"{card_id}: unknown profile source")
        for card_id, card in self.cards.items():
            if card.get("rank") not in self.ranks:
                errors.append(f"{card_id}: unknown rank {card.get('rank')!r}")
            if card.get("suit") not in self.suits:
                errors.append(f"{card_id}: unknown suit {card.get('suit')!r}")
            polarity = self.polarities.get(card_id, {})
            if not polarity.get("constructive") or not polarity.get("difficult"):
                errors.append(f"{card_id}: incomplete polarity")
        expected_densities = [1, 2, 3, 4]
        densities = sorted(int(suit["density_rank"]) for suit in self.suits.values())
        if densities != expected_densities:
            errors.append(f"invalid suit density ranks: {densities}")
        for suit_id, element in {"hearts": "Feu", "clubs": "Air", "diamonds": "Eau", "spades": "Terre"}.items():
            suit = self.suits.get(suit_id, {})
            if suit.get("element") != element or not suit.get("element_reading", {}).get("individual"):
                errors.append(f"{suit_id}: missing or incorrect Olney element correspondence")
        required_rules = {"core", "cycles", "mobility", "positions", "roles", "special_cards", "synthesis", "pedagogy", "relationships"}
        if set(self.rules) != required_rules:
            errors.append(
                f"rule files mismatch; missing={sorted(required_rules - set(self.rules))}, "
                f"extra={sorted(set(self.rules) - required_rules)}"
            )
        mobility_ids = set(self.rules.get("mobility", {}).get("fixed_cards", {}).get("cards", []))
        for pair in self.rules.get("mobility", {}).get("semi_fixed_pairs", []):
            mobility_ids.update(pair.get("cards", []))
        unknown_mobility = sorted(mobility_ids - set(self.cards))
        if unknown_mobility:
            errors.append(f"unknown fixed/semi-fixed cards: {unknown_mobility}")
        for name, group in self.rules.items():
            if group.get("rule_id") != f"rule:{name}":
                errors.append(f"{name}: missing stable rule id")
            for source in group.get("source_refs", []):
                if source not in self.provenance["sources"]:
                    errors.append(f"{name}: unknown source {source}")
        if errors:
            raise InterpretationDataError("; ".join(errors))

    def describe_card(self, label: str) -> dict[str, Any]:
        card_id = card_id_from_label(label)
        if card_id == "JOKER":
            joker = self.rules["special_cards"]["joker"]
            return {
                "id": "JOKER",
                "label": "Joker",
                "rank": None,
                "suit": None,
                "keywords": list(joker["keywords"]),
                "domains": ["hors système", "couronne"],
                "constructive": None,
                "difficult": None,
                "density_rank": None,
                "special": ["joker"],
                "source_refs": [{"source_id": "randall_joker_photo", "pages": [336], "kind": "editorial_paraphrase"}],
                "meaning_status": "pending_user_decision",
            }

        card = self.cards[card_id]
        profile = self.profiles[card_id]
        suit = self.suits[card["suit"]]
        special: list[str] = []
        mobility = self.rules["mobility"]
        if card_id in mobility["fixed_cards"]["cards"]:
            special.append("fixed")
        if any(card_id in pair["cards"] for pair in mobility["semi_fixed_pairs"]):
            special.append("semi_fixed")
        if card_id == self.rules["special_cards"]["king_of_spades"]["card"]:
            special.append("most_powerful_and_dense")
        partner = next((other for pair in mobility["semi_fixed_pairs"] if card_id in pair["cards"] for other in pair["cards"] if other != card_id), None)
        return {
            "id": card_id,
            "label": label,
            "rank": card["rank"],
            "suit": card["suit"],
            "keywords": list(card.get("keywords", [])),
            "domains": list(card.get("domains", [])),
            "constructive": profile["constructive"],
            "difficult": profile["difficult"],
            "energy_focus": profile["movement"],
            "profile_ref": f"knowledge_bundle.card_profiles.{card_id}",
            "element_ref": f"knowledge_bundle.suits.{card['suit']}",
            "density_rank": suit["density_rank"],
            "element": suit["element"],
            "special": special,
            "dual_partner_id": partner,
            "incarnated_faculty": self.editorial["figure_faculties"].get(card_id),
            "meaning_status": "editorial_paraphrase",
            "source_refs": [
                {"source_id": "morera_photos", "pages": list(card.get("source_pages", [])), "kind": "editorial_paraphrase", "fields": ["keywords", "domains"]},
                {"source_id": "olney_card_profiles_2026_08", "pages": [], "kind": "editorial_paraphrase", "fields": ["energy_focus", "constructive", "difficult", "profile_ref"]},
                {"source_id": "olney_user_2026_08", "pages": [], "kind": "validated_olney_rule", "fields": ["element", "density_rank"]},
            ],
            "documentary_note": deepcopy(self.provenance["documentary_notes"].get(card_id)),
        }


class InterpretationContextBuilder:
    """Build the single source of facts consumed by UI and LLM."""

    def __init__(self, engine: Any, knowledge: InterpretationKnowledge | None = None):
        self.engine = engine
        self.knowledge = knowledge or InterpretationKnowledge.load()
        self._number_by_label = {label: number for number, label in engine.cards.items()}

    def from_dates(
        self,
        birth_date: str,
        target_date: str,
        target_time: str | None = None,
        target_place: str | None = None,
        profile_history: Iterable[dict[str, Any]] | None = None,
        *,
        reading_focus: str = "general",
        profile_id: str | None = None,
        reading_mode: str = "current",
        reading_material: dict[str, Any] | None = None,
        reading_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = self.engine.full_state(birth_date, target_date, target_time, target_place)
        return self.from_state(state, profile_history=profile_history,
                               reading_focus=reading_focus, profile_id=profile_id, reading_mode=reading_mode,
                               reading_material=reading_material, reading_options=reading_options)

    def from_state(
        self,
        state: dict[str, Any],
        profile_history: Iterable[dict[str, Any]] | None = None,
        *,
        reading_focus: str = "general",
        profile_id: str | None = None,
        reading_mode: str = "current",
        reading_material: dict[str, Any] | None = None,
        reading_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if reading_focus not in FOCUS_CYCLES:
            raise InterpretationDataError(f"Unsupported reading focus: {reading_focus}")
        if reading_mode not in {"current", "cycle"}:
            raise InterpretationDataError(f"Unsupported reading mode: {reading_mode}")
        if reading_mode == "cycle" and FOCUS_CYCLES[reading_focus] not in {"life_path", "seven_year", "annual", "week"}:
            raise InterpretationDataError("A cycle reading requires a life-path, year, 52-day or week/day focus")
        # Notes remain untrusted data; no instruction or inferred polarity is executed.
        history = deepcopy(list(profile_history or [])) + memory_history(reading_material)
        if any(not isinstance(item, dict) for item in history):
            raise InterpretationDataError("History entries must be objects")
        profile_key = f"profile:{profile_id}" if profile_id is not None else f"birth:{state['birth_date']}"
        if reading_material:
            supplied_key = reading_material["subject"]["key"]
            if profile_id is not None and supplied_key != profile_key:
                raise InterpretationDataError("Reading material belongs to another subject")
            profile_key = supplied_key
        birth_label = state["birth"]["card"]
        profile = {
            "profile_key": profile_key,
            "identity_scope": "subject_id" if reading_material else "profile_id" if profile_id is not None else "birth_date_only",
            "birth_card": self.knowledge.describe_card(birth_label),
            "secondary_cards": [
                {
                    **self.knowledge.describe_card(item["card"]),
                    "ruler": item.get("ruler"),
                    "position": item.get("position"),
                    "origin": "astrological_ruler_in_life_path_sequence",
                    "role": "secondary_natal_reference_not_temporary_activation",
                }
                for item in (state.get("secondary_cards") or {}).get("cards", [])
            ],
            "zodiac_sign": (state.get("secondary_cards") or {}).get("sign"),
        }
        context = {
            "schema_version": SCHEMA_VERSION,
            "knowledge_version": self.knowledge.version,
            "engine_version": state["engine_version"],
            "birth_date": state["birth_date"],
            "target_date": state["target_date"],
            "joker": bool(state.get("joker")),
            "profile": profile,
            "cycles": [],
            "hour_card": self._hour_context(state.get("hour_card")),
            "global_direction": None,
            "cycle_reading": None,
            "profile_history": history,
            "history_policy": {
                "data_not_instructions": True,
                "matching": "exact_occurrence_and_user_report_only",
                "undated_notes": "background_only",
                "profile_identity": "Pass profile_id for persisted personal memory; birth_date_only is a calculation/demo namespace, not a unique person.",
            },
            "reading": {
                "focus": reading_focus,
                "mode": reading_mode,
                "focal_cycle_id": FOCUS_CYCLES[reading_focus],
                "presentation": "natural_summary_with_brief_evidence",
                "larger_cycles_remain_context": True,
                "order_is_not_mandatory_output": True,
            },
            "pending_rules": ["joker_interpretation_choice"] if state.get("joker") else [],
        }
        if state.get("joker"):
            return self._finish_context(context, reading_material=reading_material, reading_options=reading_options)

        birth_number = int(state["birth"]["card_number"])
        natural = self.engine.relative_cards(90, birth_number)
        manifested = self.engine.relative_cards(1, birth_number)
        profile.update({
            "moon_card": self.knowledge.describe_card(natural["lune"].card_label),
            "moon_reference": {"series_id": 90, "label": "Ordre naturel"},
            "life_path_palette": [
                {"sequence_planet": slot, "card": self.knowledge.describe_card(manifested[slot].card_label),
                 "position": manifested[slot].position_1based, "permanent": True}
                for slot in PLANET_SLOTS
            ],
            "life_path_moon": self.knowledge.describe_card(manifested["lune"].card_label),
            "life_path_challenge": self.knowledge.describe_card(manifested["défi"].card_label),
            "life_path_result": self.knowledge.describe_card(manifested["résultat"].card_label),
            "palette_presentation": "background_unless_relevant_or_reactivated",
        })
        life_path, seven, annual, week = (state[k] for k in ("life_path", "seven_year", "year", "week"))
        fifty_two, day = state["fifty_two_day"], state["day"]
        birth = date.fromisoformat(state["birth_date"])
        year_start, year_end = annual["rows"][0]["period_start"], annual["rows"][6]["period_end"]
        day_start = date.fromisoformat(day["date"])
        week_start = date.fromisoformat(week["rows"][0]["date"])
        seven_base_age = (int(seven["age"]) // 7) * 7

        def window(start: str, end: str, **extra: Any) -> dict[str, Any]:
            return {"start": start, "end": end, "end_exclusive": True, **extra}

        specs = [
            ("natal", None, 90, None, birth_label, "soleil", None, None),
            ("life_path", "natal", int(life_path["series_id"]), 90, life_path["card"], life_path["active_slot"],
             window(life_path["active_start_date"], life_path["active_end_date"], age_range=life_path["active_age_range"]),
             None),
            ("seven_year", "life_path", int(seven["series_id"]), 1, annual["year_card"],
             self._relative_slot(int(seven["series_id"]), birth_number, annual["year_card"]),
             window(year_start, year_end, age=annual["age"]),
             window(self.engine.anniversary_date(birth, seven_base_age).isoformat(),
                    self.engine.anniversary_date(birth, seven_base_age + 7).isoformat())),
            ("annual", "seven_year", int(annual["series_id"]), 1, fifty_two["card"], fifty_two["selected_slot"],
             window(fifty_two["window"]["start"], fifty_two["window"]["end"]), window(year_start, year_end)),
            ("week", "annual", int(week["series_id"]), 1, day["card"],
             self._relative_slot(int(week["series_id"]), birth_number, day["card"]),
             window(day_start.isoformat(), (day_start + timedelta(days=1)).isoformat(), date=day["date"]),
             window(week_start.isoformat(), (week_start + timedelta(days=7)).isoformat())),
        ]
        scopes = {item["id"]: item["scope"] for item in self.knowledge.rules["cycles"]["hierarchy"]}
        for cid, parent, sid, reference, label, slot, period, sequence_period in specs:
            cycle = self._cycle_context(
                cycle_id=cid, parent=parent, scope=scopes[cid], series_id=sid,
                reference_series_id=reference, active_label=label, sequence_planet=slot,
                birth_number=birth_number, period=period, history=history, profile_key=profile_key,
            )
            cycle["sequence_period"] = sequence_period
            cycle["sequence_cards"] = self._sequence_cards(
                cid, sid, birth_number, state, include_meanings=FOCUS_CYCLES[reading_focus] == cid
            )
            context["cycles"].append(cycle)
        context["global_direction"] = {
            "source_cycle": "life_path",
            "result": profile["life_path_result"],
            "challenge": profile["life_path_challenge"],
            "rule": self.knowledge.rules["cycles"]["results"]["final_direction"],
        }
        if reading_mode == "cycle":
            from cycle_reading import build_cycle_reading
            context["cycle_reading"] = build_cycle_reading(self, context, FOCUS_CYCLES[reading_focus])
        return self._finish_context(context, reading_material=reading_material, reading_options=reading_options)

    def _sequence_cards(self, cid, sid, birth_number, state, *, include_meanings):
        relative = self.engine.relative_cards(sid, birth_number)
        rows = {
            "life_path": state["life_path"]["rows"], "seven_year": state["seven_year"]["rows"],
            "annual": state["year"]["rows"], "week": state["week"]["rows"],
        }.get(cid, [])
        by_slot = {row["slot"]: row for row in rows}
        birth = date.fromisoformat(state["birth_date"])
        result = []
        for slot in PLANET_SLOTS:
            card = relative[slot]
            row = by_slot.get(slot, {})
            start = end = None
            if cid == "life_path":
                start = self.engine.anniversary_date(birth, row["age_start"]).isoformat()
                end = self.engine.anniversary_date(birth, row["age_end"] + 1).isoformat()
            elif cid == "seven_year":
                offset = row["year"] - birth.year
                start = self.engine.anniversary_date(birth, offset).isoformat()
                end = self.engine.anniversary_date(birth, offset + 1).isoformat()
            elif cid == "annual":
                start, end = row["period_start"], row["period_end"]
            elif cid == "week":
                start = row["date"]
                end = (date.fromisoformat(start) + timedelta(days=1)).isoformat()
            item = {
                "sequence_planet": slot, "card_id": card_id_from_label(card.card_label),
                "label": card.card_label, "position": card.position_1based,
                "period": {"start": start, "end": end, "end_exclusive": True} if start else None,
                "meaning_included": include_meanings,
            }
            if include_meanings:
                item["card"] = self.knowledge.describe_card(card.card_label)
            result.append(item)
        return result

    def _finish_context(self, context, *, reading_material=None, reading_options=None):
        from interpretation_text import build_synthesis
        # Only engine-produced roles participate. History is untrusted data and
        # must neither request arbitrary profiles nor inflate this dictionary.
        used_cards = set()

        def collect_cards(value):
            if isinstance(value, dict):
                if value.get("id") in self.knowledge.profiles and "profile_ref" in value:
                    used_cards.add(value["id"])
                for child in value.values():
                    collect_cards(child)
            elif isinstance(value, list):
                for child in value:
                    collect_cards(child)

        for key in ("profile", "cycles", "hour_card", "global_direction", "cycle_reading"):
            collect_cards(context.get(key))
        used_planets = {"moon", "sun"}
        for cycle in context["cycles"]:
            used_planets.update(PLANET_IDS[p] for p in cycle["position"]["context_planets"])
            if cycle["sequence_planet"]:
                used_planets.add(PLANET_IDS[cycle["sequence_planet"]])
            used_planets.update(PLANET_IDS[item["sequence_planet"]] for item in cycle["sequence_cards"])
        if context["cycles"]:
            used_planets.add("pluto")
        # Special cards may occur as a Moon, palette card or support, not only
        # as the current card. Keep their rules available for these roles too.
        groups = ["core", "roles", "cycles", "positions", "mobility", "synthesis", "special_cards", "pedagogy"]
        context["knowledge_bundle"] = {
            "rules": {f"rule:{name}": deepcopy(self.knowledge.rules[name]) for name in groups},
            "planets": {
                pid: {**deepcopy(self.knowledge.planets[pid]),
                      "sequence_expression": self.knowledge.editorial["planet_modes"].get(pid),
                      "meaning_kind": "editorial_paraphrase",
                      "source_id": "olney_user_2026_08_31" if pid == "moon" else
                                   "olney_user_2026_08" if pid in {"sun", "pluto"} else "morera_photos"}
                for pid in sorted(used_planets)
            },
            "sources": deepcopy(self.knowledge.provenance["sources"]),
            "card_profiles": {cid: deepcopy(self.knowledge.profiles[cid]) for cid in sorted(used_cards)},
            "profile_loading": "unique_profiles_for_referenced_cards",
            "suits": deepcopy(self.knowledge.suits),
            "retired_claims": deepcopy(self.knowledge.provenance["retired_claims"]),
            "editorial_policy": deepcopy(self.knowledge.provenance["policy"]),
            "pilot_drafts_included": False,
        }
        context["synthesis"] = build_synthesis(context, self.knowledge)
        context["reading"]["missing_data"] = (
            ["hour_time_and_place"] if context["reading"]["focus"] == "hour" and not context["hour_card"] else []
        )
        return attach_personal_context(self, context, reading_material, reading_options)

    def _relative_slot(self, series_id: int, birth_number: int, label: str) -> str:
        for slot, card in self.engine.relative_cards(series_id, birth_number).items():
            if card.card_label == label:
                return slot
        raise InterpretationDataError(
            f"{label} is not in the relative sequence for series {series_id}"
        )

    def _cycle_context(
        self,
        *,
        cycle_id: str,
        parent: str | None,
        scope: str,
        series_id: int,
        reference_series_id: int | None,
        active_label: str,
        sequence_planet: str | None,
        birth_number: int,
        period: dict[str, Any] | None,
        history: list[dict[str, Any]],
        profile_key: str,
    ) -> dict[str, Any]:
        active_number = self._number_by_label[active_label]
        position = self.engine.find_card_position(series_id, active_number)
        coordinates = self.engine.table_coordinates(position)
        context_planets = [
            value
            for value in (coordinates.get("row_planet"), coordinates.get("column_planet"))
            if value is not None
        ]
        if coordinates["zone"] == "couronne":
            context_planets = []

        owner = support = None
        home = reference_series_id is None
        if reference_series_id is not None:
            exchange = self.engine.positional_exchange(
                reference_series_id, series_id, active_number
            )
            owner = self.knowledge.describe_card(exchange["displacement"]["card"])
            support = self.knowledge.describe_card(exchange["environment"]["card"])
            home = owner["id"] == card_id_from_label(active_label)

        relative = self.engine.relative_cards(series_id, birth_number)
        challenge = self.knowledge.describe_card(relative["défi"].card_label)
        result = self.knowledge.describe_card(relative["résultat"].card_label)
        active = self.knowledge.describe_card(active_label)
        occurrence_parts = [profile_key, cycle_id, series_id, active["id"],
                            (period or {}).get("start"), (period or {}).get("end")]
        occurrence_id = "occurrence:" + sha256(json.dumps(occurrence_parts).encode("utf-8")).hexdigest()[:24]
        matched = [
            index for index, item in enumerate(history)
            if item.get("occurrence_id") == occurrence_id
            and item.get("cycle_id") == cycle_id
            and item.get("card_id") == active["id"]
            and item.get("source_type") == "user_reported"
            and item.get("polarity") in {"constructive", "difficult", "mixed"}
        ]
        polarities = {history[index]["polarity"] for index in matched}
        lived = "unknown" if not polarities else next(iter(polarities)) if len(polarities) == 1 else "mixed"
        home_state = ("reference_only" if reference_series_id is None else
                      "fixed_home" if home and "fixed" in active["special"] else
                      "at_reference_position" if home else "away")

        return {
            "id": cycle_id,
            "parent": parent,
            "scope": scope,
            "sequence_label": SEQUENCE_LABELS[cycle_id],
            "active_period_kind": PERIOD_KINDS[cycle_id],
            "series_id": series_id,
            "sequence_reference_card_id": card_id_from_label(self.engine.cards[birth_number]),
            "occurrence_id": occurrence_id,
            "active_card": active,
            "sequence_planet": sequence_planet,
            "moon_card": self.knowledge.describe_card(relative["lune"].card_label),
            "moon_rule_ref": "rule:roles",
            "position": {
                "position": position,
                "zone": coordinates["zone"],
                "home": home,
                "home_state": home_state,
                "return_transition": None,
                "reference_series_id": reference_series_id,
                "reference_label": "Ordre naturel" if reference_series_id == 90 else "Ordre manifesté / chemin de vie" if reference_series_id == 1 else None,
                "context_planets": context_planets,
                "context_amplified": len(context_planets) == 2 and len(set(context_planets)) == 1,
                "owner_card": owner,
                "support_card": support,
            },
            "challenge": challenge,
            "result": result,
            "period": period,
            "lived_polarity": lived,
            "lived_evidence": [f"history:{index}" for index in matched],
            "rule_refs": ["rule:core", "rule:roles", "rule:positions", "rule:cycles", "rule:mobility", "rule:synthesis"],
        }

    def _hour_context(self, hour_card: dict[str, Any] | None) -> dict[str, Any] | None:
        if not hour_card:
            return None
        return {
            "card": self.knowledge.describe_card(hour_card["card"]),
            "solar_time": hour_card.get("solar_time"),
            "solar_hour": hour_card.get("solar_hour"),
            "date": hour_card.get("date"),
            "place": hour_card.get("place"),
            "scope": "tonalité immédiate indépendante des 90 tableaux",
            "system": "hour_cards",
            "parent_context": "week",
            "no_table_sequence_metadata": True,
        }


def build_interpretation_context(
    engine: Any,
    state: dict[str, Any],
    profile_history: Iterable[dict[str, Any]] | None = None,
    *,
    reading_focus: str = "general",
    profile_id: str | None = None,
    reading_mode: str = "current",
    reading_material: dict[str, Any] | None = None,
    reading_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Functional convenience wrapper used by UI, API and tests."""
    return InterpretationContextBuilder(engine).from_state(
        state, profile_history=profile_history, reading_focus=reading_focus, profile_id=profile_id, reading_mode=reading_mode,
        reading_material=reading_material, reading_options=reading_options,
    )
