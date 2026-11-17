# Base d’interprétation Olney — V0.7.4

La révision 0.6 ajoute la pédagogie, les intentions de lecture, les sujets typés,
les événements et une mémoire attribuée et révisable. Les 52 fiches d’énergies,
les correspondances enseignes–éléments et la lecture des sept étapes sont
conservées. Contexte 0.5.0 : les faits calculés et le matériau personnel restent
distincts. Voir `../BACKEND_LECTURE.md` pour le service et ses limites.

Référence commune aux vues locales et au futur LLM. Moteur et tables restent
inchangés ; cette couche enrichit leurs faits, sans accès réseau ni modèle intégré.

La révision 0.7 ajoute le dossier relationnel : deux profils conservés séparément,
carte de relation développée comme énergie commune, comparaison directe des deux
cartes de naissance dans l’ordre manifesté, deux palettes de chemin de vie et deux
horloges synchronisées. Les répétitions géométriques sont fusionnées.
La carte de relation possède aussi un chemin de vie propre de Mercure au
Résultat, distinct des deux palettes personnelles, et peut alimenter une
horloge relationnelle temporaire ancrée sur la date commune choisie.
`ReadingService.relationship_context()` produit ce dossier sans score de
compatibilité. `rules/relationships.json` distingue les règles photographiées
des extensions fractales propres à Olney.

## Fichiers actifs

- `cards.json`, `card_polarities.json` : repères et polarités de référence conservés.
- `card_profiles.json` : 52 fiches actives, noyau, mouvement, deux vécus,
  manifestations, cycles, particularités et statut de relecture.
- `FICHES_CARTES.md` : présentation lisible des 52 fiches, pour relecture.
- `ranks.json`, `suits.json`, `planets.json` : mouvement, domaine, densité et fonctions.
- `rules/` : conventions validées, identifiants stables et références.
- `provenance.json` : sources, adaptations documentaires et hypothèses retirées.
- `editorial.json` : formulations communes complémentaires aux fiches actives.
- `rules/pedagogy.json` : conventions validées du compagnon, pas des citations historiques.
- `schemas/context.schema.json` : contexte version 0.5.0.
- `schemas/llm_output.schema.json` : future réponse structurée version 0.4.0.
- `llm/INSTRUCTIONS.md`, `llm/STYLE.json` : consignes à transmettre au futur LLM.

Les dossiers `drafts/` et anciens `REVIEW_*.md` ne sont pas chargés. Les cinq
textes validés ont été promus dans `card_profiles.json`, avec les 47 nouvelles
fiches. `review_status` distingue `user_validated_pilot` et `editorial_extension`.
Les développements ne sont pas des portraits transcrits de Sacred Symbols.

## Contexte prêt à consommer

`InterpretationContextBuilder.from_state` enrichit un état déjà calculé ;
`engine.tool_get_interpretation_context` calcule puis enrichit cet état.
Les arguments optionnels `reading_focus`, `reading_mode` et `profile_id`
complètent l’API existante.

```python
context = engine.tool_get_interpretation_context(
    "1988-10-27", "2026-08-31", reading_focus="week", profile_id="profil-local"
)
```

Le dossier comprend le profil, la palette permanente de sept cartes, les cartes
secondaires avec leur rôle natal explicite, les Lunes de chaque séquence,
positions, Défi/Résultat, périodes, significations, règles, planètes, sources,
observations et synthèse locale. Aucun calcul ne doit être refait par le LLM.

Chaque objet carte expose `energy_focus`, les deux vécus et un `profile_ref`.
Les fiches complètes sont regroupées **une seule fois par carte référencée** dans
`knowledge_bundle.card_profiles`. Ainsi, la même carte en Lune, active ou Défi
ne multiplie pas les copies de sa fiche. Les rôles restent pourtant distincts.

```python
birth = context["profile"]["birth_card"]
profile = context["knowledge_bundle"]["card_profiles"][birth["id"]]
print(profile["energy"])
print(profile["manifestations"])
print(context["synthesis"]["elements"])
```

`element_ref` pointe vers `knowledge_bundle.suits`. Les éléments suivent
Cœur–Feu, Trèfle–Air, Carreau–Eau, Pique–Terre, avec des développements
individuels et transversaux. `synthesis.elements` regroupe les occurrences
actives par enseigne/élément, sans compter le natal ou la palette permanente.
L’heure est incluse si disponible. Les comptes ne sont pas des scores : aucune
compatibilité ou incompatibilité élémentaire automatique n’est introduite.

Les identifiants historiques sont conservés pour éviter de casser l’interface :

| Identifiant | Séquence étudiée | Carte active dans l’horloge |
| --- | --- | --- |
| natal | Ordre naturel | Naissance |
| life_path | Chemin de vie | Tranche de 13 ans |
| seven_year | Séquence de 7 ans | Année |
| annual | Séquence annuelle | Période de 52 jours |
| week | Séquence semaine | Jour |

`active_period_kind`, `sequence_label`, `period` et `sequence_period` enlèvent
l’ambiguïté. Les bornes de fin sont exclusives. La planète de séquence reste
distincte de la paire de planètes de case. La Couronne n’a pas de paire de case.

Focus disponibles : `general`, `natal`, `life_path`, `year`, `fifty_two_days`,
`week`, `day`, `hour`. Les cartes des autres séquences restent identifiées ; les
sept cartes reçoivent leurs significations uniquement pour la séquence focalisée,
et leurs fiches sont ajoutées au dictionnaire commun sans doublon.
Le focus général conserve les cycles parents, sans imposer leur récitation.

La carte de naissance génère toutes les séquences de tableau, même lorsqu’une
autre carte est active. `sequence_reference_card_id` le rend explicite.
`profile.moon_card` conserve sa référence Ordre naturel ; `life_path_moon` et
`cycle.moon_card` ne doivent pas être remplacées par cette seule carte.

La carte horaire reste un système indépendant : pas de case ou de métadonnées de
séquence inventées. Le Joker attend toujours une décision d’interprétation.

## Lecture du cycle complet

Le mode par défaut `reading_mode="current"` conserve le dossier habituel avec
`cycle_reading: null`. Pour obtenir le parcours complet :

```python
context = engine.tool_get_interpretation_context(
    "1988-10-27", "2026-08-31",
    reading_focus="fifty_two_days", reading_mode="cycle", profile_id="profil-local",
)
reading = context["cycle_reading"]
print(reading["summary"])
print(reading["steps"][reading["current_step_index"]])
```

| Focus demandé | Parcours complet |
| --- | --- |
| `life_path` | Sept cartes de 13 ans du chemin de vie |
| `year` | Sept cartes annuelles du cycle de 7 ans |
| `fifty_two_days` | Sept périodes de la séquence annuelle |
| `week` ou `day` | Sept cartes du jour de la semaine |

`cycle_reading.py` construit sept étapes, six transitions, une synthèse du
parcours, les couleurs/éléments, les particularités de position et les cartes
Lune/Défi/Résultat. Les positions, périodes et cartes viennent du moteur ; les
liaisons narratives sont éditoriales. Les fiches utiles restent dédupliquées
dans le dictionnaire commun. Aucun appel LLM n’est effectué.

Les couleurs du parcours portent sur ses sept étapes, pas sur les seules cartes
actives de l’horloge. Le contexte parent est un instantané à la date analysée,
et non une influence supposée constante pendant tout le parcours. Les statuts
écoulé/en cours/à venir ne sélectionnent jamais un vécu positif ou difficile.

Dans l’interface, **Affichage → Lecture du cycle** fait défiler toute la page,
cartes comprises, dans la même surface. Cliquer une étape ne change que sa consultation.
Le bouton **Explorer cette période** est retiré : la navigation temporelle
reste accessible dans l’horloge et la frise, indépendamment de cette consultation.
Les dossiers sont préparés à l’ouverture de la vue, mis en cache puis invalidés
lors d’un nouveau calcul. L’Ordre naturel reste limité au tableau.

Les libellés Écoulée / En cours / À venir et le contour vert se réfèrent à la
date réelle du jour de l’ordinateur, jamais à la date déplacée dans l’horloge.
Une étape consultée peut donc être future ou passée. Un cycle hors de la période
actuelle n’a aucune carte marquée En cours. Les repères sont rafraîchis à la
réouverture/réaffichage et au changement de jour, sans modifier la consultation.

Le dossier conserve `current_step_index`, `steps[].timing` et `current_summary`
relatifs à `target_date` pour analyser la date demandée. Le bloc `present`
fournit séparément la date réelle de génération, les sept `step_timings` et
`current_step_index` (nullable) à cette date. Le LLM doit lire ces références
explicitement : une carte active à la date analysée n’est pas nécessairement
en cours aujourd’hui. Un dossier sauvegardé garde son instantané `present.date` ;
le régénérer pour une nouvelle lecture du présent.

La validation contrôle l’ordre, les dates, la période active, les positions,
les rôles Lune/Défi/Résultat, les références et les sorties LLM de sept étapes.
L’API lève `CycleCalendarMismatch` si les dates annoncées de la séquence ne
correspondent pas à la carte active calculée. Cas connu préexistant : selon
la naissance, le calcul d’âge 30/360 peut basculer un jour avant l’anniversaire
calendaire. La nouvelle vue signale alors ce désaccord au lieu d’inventer une
lecture ; la règle d’âge du moteur n’est pas modifiée par cette version.

## Mémoire liée à une période précise

Le contexte donne un `occurrence_id` stable par profil, cycle, tableau, carte et
bornes. Il reste stable pendant une même période, change pour une nouvelle
activation. Pour transmettre un vécu déclaré :

```python
cycle = next(c for c in context["cycles"] if c["id"] == "annual")
record = {
    "occurrence_id": cycle["occurrence_id"],
    "cycle_id": cycle["id"],
    "card_id": cycle["active_card"]["id"],
    "source_type": "user_reported",
    "polarity": "constructive",  # ou difficult / mixed
    "user_note": "Propos réellement rapportés, à conserver comme données.",
}
```

Sans occurrence exacte, la note reste de l’arrière-plan : elle ne sélectionne
pas une polarité. Des observations divergentes produisent `mixed`. Les deux
textes possibles restent toujours disponibles. Aucun vécu n’est inféré d’un
événement difficile. Les données d’entrée ne sont pas modifiées.

Toujours fournir `profile_id` pour une mémoire persistante : une date de
naissance n’identifie pas une personne. Le repli `birth_date_only` sert aux
calculs et démonstrations. La présente version ne change pas la BDD et ne met
pas en place de collecte automatique de vécu.

## Sources et fidélité

La base est une structuration/paraphrase de pages fournies et de conventions
Olney, pas une transcription exhaustive des livres. Les 52 portraits complets
de Sacred Symbols ne sont pas disponibles ici.

Corrections documentaires : le 7♥ conserve l’apprentissage de l’amour
inconditionnel ; le 7♠ ne reprend plus « mauvaise nouvelle / mort symbolique »,
absents de sa case p.164. Pour A♠ et 9♠, la reformulation symbolique est indiquée
comme adaptation du terme source « mort », jamais comme annonce d’un décès.

Les titres de Lune restent neutres, les anciennes fonctions différentes
ligne/colonne sont retirées, la nature duale des semi-fixes n’est pas oubliée.
Être à sa place ne prouve pas un retour daté : une transition doit être calculée
séparément. Les cartes fixes ne « reviennent » pas à chaque consultation.

## Vérification

Depuis la racine du programme :

```text
python tools/run_plain_tests.py
python tools/validate_interpretation.py
python tools/export_interpretation_context.py 1988-10-27 2026-08-31 --focus week
python tools/export_interpretation_context.py 1988-10-27 2026-08-31 --focus week --mode cycle
```

Les validations contrôlent les faits exposés, les références de règles et les
cas limites. Elles ne valident pas la capacité prédictive de la cartomancie.
