"""Deterministic relationship facts built from Olney's card tables.

This module calculates relationship geometry and packages facts.  It never
assigns a compatibility score and never selects a lived polarity.
"""

from __future__ import annotations

from datetime import date


ROLE_BY_DISTANCE = {
    1: "lune_soleil",
    2: "vénus",
    3: "mars",
    4: "jupiter",
    5: "saturne",
    6: "uranus",
    7: "neptune",
    8: "pluton",
    9: "résultat",
}

ROLE_LABELS = {
    "mercure": "Mercure",
    "lune_soleil": "Lune–Soleil",
    "vénus": "Vénus",
    "mars": "Mars",
    "jupiter": "Jupiter",
    "saturne": "Saturne",
    "uranus": "Uranus",
    "neptune": "Neptune",
    "pluton": "Pluton / Défi",
    "résultat": "Résultat",
}

ROLE_DETAILS = {
    "mercure": {
        "essence": "Échange, compréhension, circulation des idées et mise en relation.",
        "resource": "La personne peut faciliter la parole, l’apprentissage, les contacts et l’adaptation.",
        "tension": "Le lien peut devenir nerveux, dispersé, trop mental ou soumis aux malentendus.",
    },
    "lune_soleil": {
        "essence": "Soutien et direction : la carte placée derrière nourrit, soutient et encourage celle qui la précède ; la carte placée devant guide, décide et montre le chemin.",
        "resource": "La relation peut créer une complémentarité très naturelle entre appui et impulsion, chacun aidant l’autre depuis une fonction différente.",
        "tension": "L’équilibre devient plus délicat si les rôles sont refusés, figés ou si la personne placée derrière vit mal de ne pas conduire la relation.",
    },
    "vénus": {
        "essence": "Affinité, attraction, goûts partagés et plaisir d’être ensemble.",
        "resource": "Le lien favorise l’accord, la douceur, la proximité et le sentiment d’aimer les mêmes choses.",
        "tension": "Le désir de plaire ou de préserver l’harmonie peut masquer un désaccord, créer de la dépendance ou éviter une confrontation utile.",
    },
    "mars": {
        "essence": "Passion, désir, stimulation et mise en mouvement entre les deux personnes.",
        "resource": "Cette intensité donne de l’élan, du courage et une forte capacité à agir ou à se mobiliser ensemble.",
        "tension": "La même force peut se traduire par la rivalité, l’impatience, les heurts ou des conflits ouverts.",
    },
    "jupiter": {
        "essence": "Expansion, confiance et effet de bénédiction d’une personne dans la vie de l’autre.",
        "resource": "Le lien peut soutenir la réussite, l’ouverture et former un partenariat fécond dans le travail comme dans une autre association.",
        "tension": "L’enthousiasme peut conduire à l’excès, à la surestimation du lien ou à des promesses plus grandes que ce qui peut être tenu.",
    },
    "saturne": {
        "essence": "Lucidité, exigence et influence structurante : l’un voit facilement les défauts de l’autre et ses paroles peuvent avoir beaucoup de poids.",
        "resource": "La relation peut enseigner, responsabiliser, consolider et faire de l’un un professeur ou un repère pour l’autre.",
        "tension": "Elle peut aussi être vécue comme sévère, critique, inhibante ou marquée par une autorité trop lourde.",
    },
    "uranus": {
        "essence": "Surprise, liberté et imprévisibilité : l’autre échappe aux attentes et renouvelle sans cesse la relation.",
        "resource": "Le lien stimule l’indépendance, l’originalité et une amitié vivante qui laisse respirer chacun.",
        "tension": "L’instabilité, les changements brusques ou l’impossibilité d’anticiper l’autre peuvent rendre la relation difficile à sécuriser.",
    },
    "neptune": {
        "essence": "Idéal, rêve, inspiration et projection d’une image très élevée sur l’autre.",
        "resource": "La personne peut représenter un idéal, ouvrir l’imaginaire et nourrir une profonde sensibilité commune.",
        "tension": "L’idéalisation rend parfois difficile de voir l’autre avec objectivité et peut entretenir attente, confusion ou désillusion.",
    },
    "pluton": {
        "essence": "Transformation profonde : la relation confronte à une force qui oblige quelque chose à évoluer.",
        "resource": "Le lien peut révéler ce qui était enfoui et permettre une reconstruction essentielle dans la vie de chacun.",
        "tension": "La transformation peut passer par la crise, la perte de contrôle, des rapports de force ou la résistance à ce qui doit changer.",
    },
    "résultat": {
        "essence": "Attraction vers une direction d’accomplissement que le parcours cherche à rendre possible.",
        "resource": "La personne peut incarner ou stimuler une qualité vers laquelle l’autre tend et donner au lien un fort sentiment de direction.",
        "tension": "Projeter sur l’autre un aboutissement attendu peut charger la relation d’espoirs excessifs ou lui demander de réaliser ce qui appartient au parcours personnel.",
    },
}

ROLE_MEANINGS = {key: value["essence"] for key, value in ROLE_DETAILS.items()}

MANIFESTED_TABLE = (1, "ordre_manifeste", "Ordre manifesté")
NATURAL_TABLE = (90, "ordre_naturel", "Ordre naturel")
AXES = (
    ("horizontal", 1, False),
    ("vertical", 7, False),
    ("diagonale_6", 6, True),
    ("diagonale_8", 8, True),
)

ORIGIN_PRIORITY = {
    "carte_de_naissance": 0,
    "carte_de_relation": 0,
    "carte_secondaire": 1,
}


def relationship_card_number(first_card_number, second_card_number):
    """Morera solar-value addition: 1..52, with 52 preserved as K♠."""
    first = int(first_card_number)
    second = int(second_card_number)
    if not 1 <= first <= 52 or not 1 <= second <= 52:
        raise ValueError("Les valeurs solaires doivent être comprises entre 1 et 52.")
    return ((first + second - 1) % 52) + 1


class RelationshipEngine:
    def __init__(self, engine, knowledge=None):
        self.engine = engine
        self.knowledge = knowledge

    @staticmethod
    def _profile_name(profile):
        return " ".join(
            part for part in (profile.get("name", ""), profile.get("last_name", ""))
            if part
        )

    def _card_fact(self, card_number, origin, *, ruler=None):
        label = self.engine.card_label(int(card_number))
        fact = {
            "card_number": int(card_number),
            "card": label,
            "origin": origin,
            "origin_priority": ORIGIN_PRIORITY[origin],
        }
        if ruler:
            fact["ruler"] = ruler
        if self.knowledge is not None:
            description = self.knowledge.describe_card(label)
            fact["card_id"] = description.get("id")
            fact["energy_focus"] = description.get("energy_focus")
        return fact

    def subject(self, profile):
        birth_state = self.engine.full_state(profile["birth_date"], profile["birth_date"])
        birth_number = int(birth_state["birth"]["card_number"])
        primary = self._card_fact(birth_number, "carte_de_naissance")
        secondaries = [
            self._card_fact(
                item["card_number"], "carte_secondaire", ruler=item.get("ruler")
            )
            for item in birth_state["secondary_cards"]["cards"]
        ]
        life_path = self._life_path(profile["birth_date"])
        return {
            "profile_id": profile["id"],
            "name": self._profile_name(profile),
            "birth_date": profile["birth_date"],
            "birth_card": primary,
            "secondary_cards": secondaries,
            # Only the two birth cards are compared geometrically. Secondary
            # cards remain separate natal references for temporal activation.
            "permanent_reference_cards": [primary],
            "activation_reference_cards": [primary, *secondaries],
            "reference_cards": [primary, *secondaries],
            "life_path": life_path,
        }

    def _life_path(self, birth_date):
        state = self.engine.full_state(birth_date, birth_date)["life_path"]
        rows = []
        for row in state["rows"]:
            fact = self._card_fact(row["card_number"], "carte_de_naissance")
            rows.append({
                "slot": row["slot"],
                "card_number": row["card_number"],
                "card": row["card"],
                "card_id": fact.get("card_id"),
                "energy_focus": fact.get("energy_focus"),
            })
        return {
            "palette": [row for row in rows if row["slot"] in {
                "mercure", "vénus", "mars", "jupiter", "saturne", "uranus", "neptune"
            }],
        }

    def _relationship_life_path(self, card_number):
        """Return the manifested sequence belonging to the relationship card.

        Unlike a person's dated active cycle, this is the permanent palette
        generated by the relationship card itself.  It therefore needs no
        invented birthday to be calculated.
        """
        relative = self.engine.relative_cards(1, int(card_number))
        rows = []
        for slot in (
            "mercure", "vénus", "mars", "jupiter", "saturne", "uranus",
            "neptune", "défi", "résultat",
        ):
            item = relative[slot]
            fact = self._card_fact(item.card_number, "carte_de_naissance")
            rows.append({
                "slot": slot,
                "card_number": item.card_number,
                "card": item.card_label,
                "position": item.position_1based,
                "card_id": fact.get("card_id"),
                "energy_focus": fact.get("energy_focus"),
            })
        return {
            "series_id": 1,
            "reference_card_number": int(card_number),
            "reference_card": self.engine.card_label(int(card_number)),
            "belongs_to": "relationship",
            "reading_scope": (
                "Chaque carte décrit une faculté, une tension ou une direction "
                "du lien ; elle n’appartient individuellement à aucun participant."
            ),
            "individual_resonance": (
                "Lorsqu’une de ces cartes appartient aussi à un participant, "
                "décrire une résonance avec lui, pas une appropriation de l’étape."
            ),
            "palette": rows[:7],
            "challenge": rows[7],
            "result": rows[8],
            "rows": rows,
        }

    @staticmethod
    def _forward(position, stride, distance):
        return ((int(position) - 1 + stride * distance) % 52) + 1

    def _link_fact(self, *, table, axis, reciprocal, distance, source, target,
                   source_subject, target_subject):
        role = ROLE_BY_DISTANCE[distance]
        details = ROLE_DETAILS[role]
        if reciprocal:
            direction = "réciproque"
            interpretation = (
                f'{source_subject["name"]} et {target_subject["name"]} portent '
                f'réciproquement la fonction {ROLE_LABELS[role]}. '
                f'{details["essence"]}'
            )
        elif role == "lune_soleil":
            direction = "directionnelle"
            interpretation = (
                f'{source_subject["name"]} porte la fonction Lune pour '
                f'{target_subject["name"]}, qui porte la fonction Soleil : '
                + ROLE_MEANINGS[role]
            )
        else:
            direction = "directionnelle"
            interpretation = (
                f'{target_subject["name"]} représente {ROLE_LABELS[role]} pour '
                f'{source_subject["name"]}. {ROLE_MEANINGS[role]}'
            )
        return {
            "table_id": table[0],
            "table": table[1],
            "table_label": table[2],
            "axis": axis,
            "reciprocal": reciprocal,
            "direction": direction,
            "distance": distance,
            "role": role,
            "role_label": ROLE_LABELS[role],
            "role_reading": {
                "essence": details["essence"],
                "resource": details["resource"],
                "tension": details["tension"],
            },
            "source_subject_id": source_subject["profile_id"],
            "source_subject": source_subject["name"],
            "source_card": source,
            "target_subject_id": target_subject["profile_id"],
            "target_subject": target_subject["name"],
            "target_card": target,
            "interpretation": interpretation,
            "priority": source["origin_priority"] + target["origin_priority"],
            "provenance": "morera_relations_151_155",
        }

    def _geometry_links(self, first, second, tables):
        links = []
        seen = set()
        cards_a = first.get("permanent_reference_cards", first["reference_cards"])
        cards_b = second.get("permanent_reference_cards", second["reference_cards"])
        for table in tables:
            positions_a = {
                item["card_number"]: self.engine.find_card_position(table[0], item["card_number"])
                for item in cards_a
            }
            positions_b = {
                item["card_number"]: self.engine.find_card_position(table[0], item["card_number"])
                for item in cards_b
            }
            for card_a in cards_a:
                for card_b in cards_b:
                    pos_a = positions_a[card_a["card_number"]]
                    pos_b = positions_b[card_b["card_number"]]
                    for axis, stride, reciprocal in AXES:
                        matches = []
                        for distance in range(1, 10):
                            if pos_b == self._forward(pos_a, stride, distance):
                                matches.append((distance, card_a, card_b, first, second))
                            if pos_a == self._forward(pos_b, stride, distance):
                                matches.append((distance, card_b, card_a, second, first))
                        for distance, source, target, source_subject, target_subject in matches:
                            if reciprocal:
                                signature = (
                                    table[0], axis, distance,
                                    *sorted((card_a["card_number"], card_b["card_number"])),
                                    card_a["origin"], card_b["origin"],
                                )
                            else:
                                signature = (
                                    table[0], axis, distance,
                                    source_subject["profile_id"], source["card_number"],
                                    target_subject["profile_id"], target["card_number"],
                                    source["origin"], target["origin"],
                                )
                            if signature in seen:
                                continue
                            seen.add(signature)
                            links.append(self._link_fact(
                                table=table, axis=axis, reciprocal=reciprocal,
                                distance=distance, source=source, target=target,
                                source_subject=source_subject, target_subject=target_subject,
                            ))
        links = self._deduplicate_definitions(links)
        links.sort(key=lambda item: (
            item.get("priority", 9), item.get("distance", 99),
            item.get("axis", "")
        ))
        return links

    def permanent_links(self, first, second):
        """Primary Morera comparison: both birth cards in manifested order."""
        return self._geometry_links(first, second, (MANIFESTED_TABLE,))

    def natural_order_links(self, first, second, relation_card):
        """Secondary comparison in natural order, kept separate from the main reading.

        It compares the two birth cards, then each birth card with the
        relationship card. No secondary or displaced card is introduced.
        """
        relation_subject = {
            "profile_id": "relationship",
            "name": f'Carte de la relation {relation_card["card"]}',
            "reference_cards": [relation_card],
            "permanent_reference_cards": [relation_card],
        }
        pairs = (
            ("birth_birth", first, second),
            ("first_relationship", first, relation_subject),
            ("second_relationship", second, relation_subject),
        )
        result = []
        for comparison_pair, source, target in pairs:
            for link in self._geometry_links(source, target, (NATURAL_TABLE,)):
                result.append({**link, "comparison_pair": comparison_pair})
        result.sort(key=lambda item: (
            {"birth_birth": 0, "first_relationship": 1,
             "second_relationship": 2}.get(item["comparison_pair"], 9),
            item.get("distance", 99), item.get("axis", ""),
        ))
        return result

    @staticmethod
    def _deduplicate_definitions(links):
        """Merge geometric routes that would repeat the same relationship text."""
        unique = {}
        for link in links:
            if link.get("reciprocal"):
                participants = tuple(sorted((
                    (link["source_subject_id"], link["source_card"]["card_number"]),
                    (link["target_subject_id"], link["target_card"]["card_number"]),
                ), key=lambda item: (str(item[0]), item[1])))
            else:
                participants = (
                    (link["source_subject_id"], link["source_card"]["card_number"]),
                    (link["target_subject_id"], link["target_card"]["card_number"]),
                )
            signature = (link["role"], link["reciprocal"], participants)
            route = {
                "table": link["table"], "axis": link["axis"],
                "distance": link["distance"],
            }
            if signature not in unique:
                unique[signature] = {**link, "routes": [route], "route_count": 1}
                continue
            if route not in unique[signature]["routes"]:
                unique[signature]["routes"].append(route)
                unique[signature]["route_count"] = len(unique[signature]["routes"])
        return list(unique.values())

    def _relationship_reading(self, card, first, second):
        """Adapt the card's energy profile to the relationship itself."""
        if self.knowledge is None or not card.get("card_id"):
            return {
                "energy": (
                    f'{card["card"]} représente la dynamique créée entre '
                    f'{first["name"]} et {second["name"]}.'
                )
            }
        profile = self.knowledge.profiles[card["card_id"]]
        return {
            "title": profile["title"],
            "energy": (
                f'Entre {first["name"]} et {second["name"]}, {card["card"]} décrit '
                "l’énergie propre du lien : ce que leur rencontre met en mouvement "
                "et leur manière particulière de faire relation. "
                f'{profile["energy"]}'
            ),
            "constructive": (
                "Quand cette énergie circule de manière constructive dans la relation, "
                f'{profile["constructive"]}'
            ),
            "tension": (
                "Quand la même dynamique se tend ou se déséquilibre entre eux, "
                f'{profile["difficult"]}'
            ),
            "manifestations": (
                "Dans leur histoire commune, elle peut prendre des formes très différentes. "
                f'{profile["manifestations"]}'
            ),
        }

    @staticmethod
    def _slot_role(slot):
        return "pluton" if slot == "défi" else slot

    def _annual_relationship_roles(self, host_profile, host, other, target_date):
        """Find how the other's natal references appear in the host's annual path."""
        if date.fromisoformat(host_profile["birth_date"]) > date.fromisoformat(str(target_date)):
            return []
        state = self.engine.full_state(host_profile["birth_date"], str(target_date))
        references = {}
        for card in other["activation_reference_cards"]:
            references.setdefault(card["card_number"], []).append(card)
        period_rows = [row for row in state["year"]["rows"] if row.get("period_start")]
        period_start = period_rows[0]["period_start"] if period_rows else None
        period_end = period_rows[-1]["period_end"] if period_rows else None
        roles = []
        seen = set()
        for row in state["year"]["rows"]:
            matched = references.get(row["card_number"], [])
            if not matched:
                continue
            role = self._slot_role(row["slot"])
            details = ROLE_DETAILS.get(role)
            if details is None:
                continue
            origins = []
            for card in matched:
                label = (
                    "carte de naissance" if card["origin"] == "carte_de_naissance"
                    else f'carte secondaire {card.get("ruler", "").strip()}'.strip()
                )
                if label not in origins:
                    origins.append(label)
            signature = (host["profile_id"], other["profile_id"], row["slot"], row["card_number"])
            if signature in seen:
                continue
            seen.add(signature)
            roles.append({
                "type": "annual_relationship_role",
                "date": str(target_date),
                "host_subject_id": host["profile_id"],
                "host_subject": host["name"],
                "appearing_subject_id": other["profile_id"],
                "appearing_subject": other["name"],
                "card": row["card"],
                "card_number": row["card_number"],
                "matched_references": matched,
                "matched_reference_labels": origins,
                "role": role,
                "role_label": ROLE_LABELS[role],
                "slot": row["slot"],
                "series_id": state["year"]["series_id"],
                "period_start": period_start,
                "period_end": period_end,
                "role_reading": {**details},
                "interpretation": (
                    f'Dans le chemin annuel de {host["name"]}, {other["name"]} '
                    f'apparaît par sa {" / ".join(origins)} {row["card"]} à la '
                    f'place {ROLE_LABELS[role]}. Pour cette année, cette personne '
                    f'active donc une fonction {ROLE_LABELS[role]} dans la relation. '
                    f'{details["essence"]}'
                ),
                "provenance": "morera_relations_151_155",
            })
        return roles

    def _clock(self, profile, target_date, target_time=None, target_place=None):
        if date.fromisoformat(profile["birth_date"]) > date.fromisoformat(str(target_date)):
            return {"status": "avant_naissance"}
        state = self.engine.full_state(profile["birth_date"], str(target_date))
        hour = None
        if target_time and target_place:
            try:
                hour = self.engine.hour_card(target_date, target_time, target_place)["card"]
            except ValueError:
                hour = None
        # The active annual card is the sequence reference of the annual table;
        # locate it directly in the seven-year rows rather than infer from a date label.
        annual_row = next(
            (row for row in state["seven_year"]["rows"]
             if row["card"] == state["year"]["year_card"]),
            None,
        )
        day_row = next(
            (row for row in state["week"]["rows"] if row.get("date") == str(target_date)),
            None,
        )
        active_cycles = [
            {
                "cycle": "chemin_de_vie", "card": state["life_path"]["card"],
                "card_number": state["life_path"]["card_number"],
                "sequence_planet": state["life_path"]["active_slot"],
                "series_id": state["life_path"]["series_id"],
                "position": state["life_path"]["position"],
                "period_start": state["life_path"]["active_start_date"],
                "period_end": state["life_path"]["active_end_date"],
            },
            {
                "cycle": "année", "card": state["year"]["year_card"],
                "card_number": annual_row.get("card_number") if annual_row else None,
                "sequence_planet": annual_row.get("slot") if annual_row else None,
                "series_id": state["seven_year"]["series_id"],
                "position": annual_row.get("position") if annual_row else None,
                "period_start": state["year"]["rows"][0].get("period_start"),
                "period_end": state["year"]["rows"][-3].get("period_end"),
            },
            {
                "cycle": "52_jours", "card": state["fifty_two_day"]["card"],
                "card_number": state["fifty_two_day"]["card_number"],
                "sequence_planet": state["fifty_two_day"]["selected_slot"],
                "series_id": state["fifty_two_day"]["series_id"],
                "position": state["fifty_two_day"]["position"],
                "period_start": state["fifty_two_day"]["window"]["start"],
                "period_end": state["fifty_two_day"]["window"]["end"],
            },
            {
                "cycle": "jour", "card": state["week"]["day_card"],
                "card_number": day_row.get("card_number") if day_row else None,
                "sequence_planet": day_row.get("slot") if day_row else None,
                "series_id": state["week"]["series_id"],
                "position": day_row.get("position") if day_row else None,
                "period_start": str(target_date), "period_end": str(target_date),
            },
        ]
        for cycle in active_cycles:
            if cycle.get("position"):
                cycle["position_context"] = self.engine.table_coordinates(cycle["position"])
        return {
            "status": "calculé",
            "chemin_de_vie": state["life_path"]["card"],
            "année": state["year"]["year_card"],
            "52_jours": state["fifty_two_day"]["card"],
            "jour": state["week"]["day_card"],
            "heure": hour,
            "active_cycles": active_cycles,
        }

    @staticmethod
    def links_for_llm(links, limit=32):
        """Keep direct evidence first and bound secondary geometry for prompt size."""
        ordered = sorted(
            links,
            key=lambda item: (
                item.get("priority", 9), item.get("distance", 99),
                0 if item.get("table_id") == 90 else 1,
            ),
        )
        direct = [item for item in ordered if item.get("priority", 9) <= 1]
        remaining = [item for item in ordered if item.get("priority", 9) > 1]
        return [*direct, *remaining[:max(0, int(limit) - len(direct))]]

    def build(self, first_profile, second_profile, target_date, *, target_time=None,
              target_place=None, relationship=None):
        first = self.subject(first_profile)
        second = self.subject(second_profile)
        number = relationship_card_number(
            first["birth_card"]["card_number"], second["birth_card"]["card_number"]
        )
        relation_card = self._card_fact(number, "carte_de_relation")
        relation_card["relationship_reading"] = self._relationship_reading(
            relation_card, first, second
        )
        relationship_life_path = self._relationship_life_path(number)
        clocks = [
            {"profile_id": first_profile["id"], "name": first["name"],
             **self._clock(first_profile, target_date, target_time, target_place)},
            {"profile_id": second_profile["id"], "name": second["name"],
             **self._clock(second_profile, target_date, target_time, target_place)},
        ]
        manifested_links = self.permanent_links(first, second)
        relation_reference = {
            key: value for key, value in relation_card.items()
            if key != "relationship_reading"
        }
        natural_links = self.natural_order_links(first, second, relation_reference)
        annual_relationship_roles = [
            *self._annual_relationship_roles(first_profile, first, second, target_date),
            *self._annual_relationship_roles(second_profile, second, first, target_date),
        ]
        temporal_activations = []
        for clock, other in ((clocks[0], second), (clocks[1], first)):
            reference_by_card = {}
            for card in other["activation_reference_cards"]:
                reference_by_card.setdefault(card["card"], []).append(card)
            path_cards = [
                *other["life_path"]["palette"],
            ]
            for card in path_cards:
                path_reference = {
                    **card,
                    "origin": "chemin_de_vie_manifeste",
                    "origin_priority": 1,
                }
                reference_by_card.setdefault(card["card"], []).append(path_reference)
            for cycle in clock.get("active_cycles", []):
                if cycle["card"] in reference_by_card:
                    matched = reference_by_card[cycle["card"]]
                    matched_labels = []
                    for item in matched:
                        origin = item.get("origin")
                        if origin == "carte_de_naissance":
                            label = "carte de naissance"
                        elif origin == "carte_secondaire":
                            label = "carte secondaire"
                        else:
                            label = "chemin de vie manifesté"
                        if label not in matched_labels:
                            matched_labels.append(label)
                    temporal_activations.append({
                        "type": "other_reference_card_active",
                        "date": str(target_date),
                        "active_subject_id": clock["profile_id"],
                        "active_subject": clock["name"],
                        "cycle": cycle["cycle"],
                        "active_card": cycle["card"],
                        "other_subject_id": other["profile_id"],
                        "other_subject": other["name"],
                        "matched_references": matched,
                        "interpretation": (
                            f'{clock["name"]} incarne actuellement {cycle["card"]} '
                            f'comme carte {str(cycle.get("sequence_planet") or "").capitalize()} '
                            f'du cycle {cycle["cycle"]}. Cette carte rejoint la '
                            f'{" / ".join(matched_labels)} de {other["name"]} : '
                            "leur dynamique est donc particulièrement activée à cette échelle."
                        ),
                        "provenance": "morera_relations_151_155"
                        if cycle["cycle"] == "année" else "olney_relationships_2026_09",
                    })
        return {
            "schema_version": "1.2.0",
            "mode": "relationship",
            "relationship": relationship or {},
            "target_date": str(target_date),
            "subjects": [first, second],
            "relationship_card": {
                **relation_card,
                "calculation": {
                    "first_solar_value": first["birth_card"]["card_number"],
                    "second_solar_value": second["birth_card"]["card_number"],
                    "rule": "addition puis retrait de 52 uniquement si le total dépasse 52",
                },
            },
            "relationship_life_path": relationship_life_path,
            "permanent_links": manifested_links,
            "natural_order_links": natural_links,
            "annual_relationship_roles": annual_relationship_roles,
            "current_clocks": clocks,
            "temporal_activations": temporal_activations,
            "interpretation_order": [
                "birth_cards", "relationship_card", "relationship_life_path",
                "manifested_order_structure", "natural_order_comparison",
                "annual_bidirectional_roles", "manifested_life_path_palettes",
                "current_relational_climate", "recorded_events_and_lived_accounts",
            ],
            "llm_policy": {
                "no_compatibility_score": True,
                "cards_are_energies_not_fixed_events": True,
                "separate_each_subjects_facts_and_accounts": True,
                "current_cycles_are_context_not_proof": True,
                "annual_reactivation_is_book_sourced": True,
                "extension_to_other_cycles_is_olney_fractal_convention": True,
                "manifested_order_is_primary_relationship_geometry": True,
                "natural_order_is_separate_comparison": True,
                "natural_order_scope": "birth_birth_and_each_birth_with_relationship_card",
                "relationship_geometry_compares_birth_cards_only": True,
                "duplicate_relationship_definitions_are_merged": True,
                "challenge_and_result_are_not_relationship_comparators": True,
                "relationship_challenge_and_result_belong_to_relationship_life_path": True,
                "relationship_life_path_cards_belong_to_the_link": True,
                "individual_card_repetition_means_resonance_not_ownership": True,
                "temporal_activation_scope": "birth_secondary_and_manifested_life_path_palette",
                "annual_roles_compare_birth_and_secondary_cards": True,
                "relationship_card_has_no_invented_calendar_origin": True,
                "ask_for_lived_context_when_needed": True,
            },
        }
