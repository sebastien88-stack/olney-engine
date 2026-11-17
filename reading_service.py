"""Local backend entry points for the future chat/web adapter. No LLM calls."""
from datetime import date

from interpretation_runtime import InterpretationContextBuilder, InterpretationKnowledge
from olney_engine import OlneyEngine
from relationship_runtime import RelationshipEngine


class ReadingService:
    def __init__(self, store, *, engine=None, knowledge=None):
        self.store = store
        self.engine = engine or OlneyEngine()
        self.builder = InterpretationContextBuilder(self.engine, knowledge or InterpretationKnowledge.load())
        self.relationship_engine = RelationshipEngine(self.engine, self.builder.knowledge)

    def _context(self, origin, target, material, *, target_time=None, target_place=None, **kwargs):
        # Missing/unknown hour or location must not erase otherwise valid dated cycles.
        state = self.engine.full_state(origin, str(target))
        hour_input = {"time": target_time or None, "place": target_place or None, "status": "not_requested"}
        if target_time and target_place:
            try:
                state["hour_card"] = self.engine.hour_card(target, target_time, target_place)
                hour_input["status"] = "calculated"
            except ValueError as error:
                hour_input.update(status="unavailable", reason=str(error))
        elif target_time or target_place:
            hour_input["status"] = "incomplete"
        context = self.builder.from_state(state, reading_material=material, **kwargs)
        context["reading"]["hour_input"] = hour_input
        if hour_input["status"] in {"incomplete", "unavailable"}:
            context["reading"]["missing_data"] = list(dict.fromkeys(
                context["reading"]["missing_data"] + ["hour_time_and_place"]))
        return context

    def profile_context(self, profile_id, target_date, *, target_time=None, target_place=None,
                        reading_focus="general", reading_mode="current", options=None,
                        reader_key="local_user", event_ids=(), themes=()):
        profile = self.store.get_profile(profile_id)
        if not profile:
            raise ValueError("Profil introuvable.")
        material = self.store.reading_material(f"profile:{profile_id}", target_date,
                        reader_key=reader_key, event_ids=event_ids, themes=themes)
        return self._context(profile["birth_date"], target_date, material,
                    target_time=target_time, target_place=target_place,
                    profile_id=profile_id, reading_focus=reading_focus, reading_mode=reading_mode,
                    reading_options=options)

    def compare_profiles(self, profile_ids, target_date, *, options=None, reader_key="local_user"):
        ids = list(dict.fromkeys(int(pid) for pid in profile_ids))
        if not 1 <= len(ids) <= 8:
            raise ValueError("Choisir entre un et huit sujets.")
        return {"schema_version": "1.0", "mode": "subjects_at_date", "target_date": str(target_date),
                "contexts": [self.profile_context(pid, target_date, options=options, reader_key=reader_key) for pid in ids],
                "comparison_policy": "Separate subjects and accounts; no composite card or compatibility score is calculated."}

    def relationship_context(self, relationship_id, target_date, *, target_time=None,
                             target_place=None, options=None, reader_key="local_user"):
        """Return one deterministic relation dossier ready for a future LLM."""
        relationship = self.store.get_relationship(relationship_id)
        if not relationship:
            raise ValueError("Relation introuvable.")
        first = self.store.get_profile(relationship["profile_a_id"])
        second = self.store.get_profile(relationship["profile_b_id"])
        if not first or not second:
            raise ValueError("Un des profils de la relation n’existe plus.")
        facts = self.relationship_engine.build(
            first, second, target_date, target_time=target_time,
            target_place=target_place, relationship=relationship,
        )
        personal_contexts = []
        unavailable = []
        for profile in (first, second):
            if date.fromisoformat(profile["birth_date"]) > date.fromisoformat(str(target_date)):
                unavailable.append({
                    "subject_key": f'profile:{profile["id"]}',
                    "reason": "target_before_subject_origin",
                })
                continue
            personal_contexts.append({
                "profile_id": profile["id"],
                "name": self.relationship_engine._profile_name(profile),
                "material": self.store.reading_material(
                    f'profile:{profile["id"]}', target_date, reader_key=reader_key
                ),
            })
        all_links = facts["permanent_links"]
        selected_links = self.relationship_engine.links_for_llm(all_links)
        facts["permanent_link_index"] = {
            "total": len(all_links),
            "selected_for_llm": len(selected_links),
            "birth_to_birth": sum(
                link["source_card"].get("origin") == "carte_de_naissance"
                and link["target_card"].get("origin") == "carte_de_naissance"
                for link in all_links
            ),
            "selection_policy": (
                "ordre manifesté uniquement; comparaison des deux cartes de "
                "naissance; définitions équivalentes fusionnées"
            ),
        }
        facts["permanent_links"] = selected_links
        natural_links = facts["natural_order_links"]
        facts["natural_order_link_index"] = {
            "total": len(natural_links),
            "birth_to_birth": sum(
                link.get("comparison_pair") == "birth_birth" for link in natural_links
            ),
            "first_birth_to_relationship": sum(
                link.get("comparison_pair") == "first_relationship" for link in natural_links
            ),
            "second_birth_to_relationship": sum(
                link.get("comparison_pair") == "second_relationship" for link in natural_links
            ),
            "selection_policy": (
                "ordre naturel; cartes de naissance entre elles puis chacune avec "
                "la carte de relation; aucune carte secondaire ou déplacée"
            ),
        }
        facts["personal_contexts"] = personal_contexts
        common_events = []
        required_ids = {first["id"], second["id"]}
        for event in self.store.list_events():
            detailed = self.store.reading_event(event["id"])
            linked_ids = {
                detailed["profile_id"],
                *(item["profile_id"] for item in detailed["participants"]),
            }
            if required_ids <= linked_ids:
                common_events.append(detailed)
        facts["common_events"] = common_events
        facts["unavailable"] = unavailable
        # Full fiches are limited to the cards that drive the reading. Other
        # supporting cards retain their short energy_focus and can be retrieved
        # on demand instead of inflating every prompt.
        full_profile_ids = {facts["relationship_card"].get("card_id")}
        full_profile_ids.update(
            row.get("card_id")
            for row in facts["relationship_life_path"]["rows"]
        )
        for subject in facts["subjects"]:
            full_profile_ids.add(subject["birth_card"].get("card_id"))
            full_profile_ids.update(
                card.get("card_id") for card in subject["secondary_cards"]
            )
        for clock in facts["current_clocks"]:
            for label in (
                clock.get("chemin_de_vie"), clock.get("année"),
                clock.get("52_jours"), clock.get("jour"), clock.get("heure"),
            ):
                if label in self.engine.cards.values():
                    full_profile_ids.add(
                        self.builder.knowledge.describe_card(label)["id"]
                    )
        full_profile_ids.discard(None)
        card_profiles = {
            card_id: self.builder.knowledge.profiles[card_id]
            for card_id in sorted(full_profile_ids)
        }
        # Static knowledge is loaded once and only the relationship-specific
        # rules are attached here; card energy summaries already sit on facts.
        facts["knowledge_bundle"] = {
            "relationships": self.builder.knowledge.rules["relationships"],
            "pedagogy": self.builder.knowledge.rules["pedagogy"],
            "positions": self.builder.knowledge.rules["positions"],
            "roles": self.builder.knowledge.rules["roles"],
            "planets": self.builder.knowledge.planets,
            "suits": self.builder.knowledge.suits,
            "card_profiles": card_profiles,
            "profile_loading": {
                "full_card_ids": sorted(full_profile_ids),
                "other_relationship_cards": "energy_focus_only; retrieve the full fiche on demand",
            },
            "sources": {
                key: self.builder.knowledge.provenance["sources"][key]
                for key in ("morera_relations_151_155", "olney_relationships_2026_09")
            },
        }
        return facts

    def event_context(self, event_id, *, mode="participants", target_date=None,
                      participant_ids=None, options=None, reader_key="local_user"):
        event = self.store.reading_event(event_id)
        if mode == "origin":
            if not event["origin_label"]:
                raise ValueError("Précise d’abord ce que représente la date d’origine avec set_event_reading().")
            target = str(target_date or event["date_start"])
            material = self.store.reading_material(f"event:{event_id}", target, reader_key=reader_key)
            # An origin's recorded hour is not the hour of a later explored date.
            at_origin = target == event["date_start"]
            return self._context(event["date_start"], target, material,
                       target_time=event["event_time"] if at_origin else None,
                       target_place=event["place"] if at_origin else None, reading_options=options)
        if mode != "participants" or (target_date and str(target_date) != event["date_start"]):
            raise ValueError("La lecture des participants utilise la date de l’événement.")
        associated = {event["profile_id"], *(p["profile_id"] for p in event["participants"])}
        ids = sorted(associated) if participant_ids is None else list(dict.fromkeys(int(pid) for pid in participant_ids))
        if not ids or len(ids) > 8 or not set(ids) <= associated:
            raise ValueError("Participants non reliés à cet événement ou sélection trop grande.")
        contexts, unavailable = [], []
        for pid in ids:
            profile = self.store.get_profile(pid)
            if date.fromisoformat(profile["birth_date"]) > date.fromisoformat(event["date_start"]):
                unavailable.append({"subject_key": f"profile:{pid}", "reason": "event_before_subject_origin"})
                continue
            contexts.append(self.profile_context(pid, event["date_start"], target_time=event["event_time"],
                            target_place=event["place"], options=options, reader_key=reader_key, event_ids=[event_id]))
        return {"schema_version": "1.0", "mode": "event_participants", "target_date": event["date_start"],
                "event": event, "contexts": contexts, "unavailable": unavailable,
                "comparison_policy": "One recorded event, separate cycles and lived accounts for each subject; no inferred shared psychology."}
