# Backend de lecture — V1.8.9 (développement)

## Conversation Emmett

`OlneyChatService` transforme les dossiers de `ReadingService` en contexte
compact pour une conversation. Le sujet est soit `general`, soit un profil, une
relation ou un événement enregistré. Les règles statiques communes ne sont
jointes qu’une fois et les références documentaires répétées sont retirées de la
requête ; les faits calculés et les fiches de cartes déjà intégrées aux dossiers
restent présents.

Le sujet sélectionné reste le cadre de la conversation. Avant chaque appel, le
service résout localement les dates simples, les titres d’événements et les
relations accessibles depuis ce sujet. Une relation peut être reconnue par son
titre ou par le nom de l’autre participant, dans les deux sens. En cas
d’homonymie, les candidats sont transmis pour clarification plutôt que devinés.
`chat_request.base_subject` conserve le cadre tandis que
`chat_request.effective_subject` expose le focus du message. Une lecture
d’événement passe ainsi par `ReadingService.event_context()` et reçoit réellement
les horloges des participants à la date enregistrée. Une lecture relationnelle
passe par `ReadingService.relationship_context()` et demeure le focus des
questions suivantes sans muter l’interface.

La compression accepte les deux formes historiques de `knowledge_bundle`, afin
que `rule:relationships` et `rule:pedagogy` restent présentes dans le dossier
relationnel. Les numéros de positions du chemin relationnel sont retirés du
contexte conversationnel : les cartes et leurs fonctions suffisent à la lecture.
Une politique de preuve accompagne chaque requête et distingue les notes libres
des faits interprétatifs.

Les tables additives `chat_threads` et `chat_messages` conservent localement le
fil, son sujet, l’angle demandé, le contexte associé à chaque question et les
compteurs de jetons retournés. Elles sont auto-initialisées dans la même base que
les profils. Une suppression de conversation supprime ses messages, sans toucher
aux profils, relations ou événements.

`OpenAIResponsesClient` utilise `POST /v1/responses`, avec un historique récent
borné et `store: false`. La clé est lue depuis la fenêtre Connexion ou depuis
`OPENAI_API_KEY` et ne possède volontairement aucun champ de persistance. Le
modèle par défaut est `gpt-5.6-terra`; `OLNEY_OPENAI_MODEL` peut le remplacer au
démarrage. Pour `gpt-5`, le client demande un effort moyen, une verbosité moyenne
et 3 000 jetons de sortie. Il inspecte `status` et `incomplete_details`, puis
retente une seule fois une réponse vide interrompue par la limite. La requête
réseau s’exécute sur une file indépendante des calculs du moteur.

## Relations entre deux profils

Une relation enregistrée conserve les identifiants de deux profils, son type,
son titre, ses notes, son statut favori et son historique de consultation. La
suppression d’un profil supprime automatiquement les relations qui en dépendent.

```python
relation = store.create_relationship({
    "profile_a_id": alice_id,
    "profile_b_id": bob_id,
    "relationship_type": "Amitié",
    "title": "Alice et Bob",
    "notes": "",
})
context = reader.relationship_context(
    relation["id"], "2026-09-01",
    target_time="12:00", target_place="Paris, FR",
)
```

Le dossier JSON 1.2.0 suit
`interpretation/schemas/relationship_context.schema.json`. Il fournit :

- deux sujets et deux contextes personnels séparés ;
- la carte de relation calculée par les valeurs solaires ;
- les cartes de naissance et les cartes secondaires de chaque personne ;
- les correspondances de l’ordre manifesté entre les deux seules cartes de naissance ;
- les deux palettes personnelles manifestées, sans comparer leurs Défis/Résultats ;
- le chemin de vie propre à la carte de relation, de Mercure au Résultat ;
- les deux horloges à la même date, avec les métadonnées des cycles actifs ;
- un ensemble dédupliqué de fiches utiles et les règles relationnelles.

Le moteur sépare deux couches : `permanent_links` porte la structure principale
entre les deux cartes de naissance dans l’ordre manifesté ;
`natural_order_links` compare, dans l’ordre naturel, les deux cartes de naissance
entre elles puis chacune avec la carte de relation. Le dossier LLM conserve les
liens manifestés utiles, bornés à 32 éléments ;
`permanent_link_index` indique le nombre calculé et le nombre transmis. Les
activations temporelles sont limitées aux cartes de naissance, secondaires et
à la palette de chemin de vie manifestée de l’autre sujet. Les routes produisant
la même fonction relationnelle sont fusionnées.
`annual_relationship_roles` expose en outre la règle annuelle de Morera dans les
deux sens : présence des cartes natales de l’un dans le chemin annuel de l’autre,
fonction occupée, ressource et tension possibles. Les autres fiches sont
récupérables à la demande. Aucun score de compatibilité, verdict ou vécu supposé
n’est calculé. La carte de relation ne reçoit aucune horloge artificielle : la
date commune reste un événement du lien, pas une date de naissance inventée.

## Ce qui est intégré

Le moteur calcule. Le corpus décrit les énergies et les règles. Le service
rassemble les faits et les informations attribuées au sujet. Le futur LLM
pourra les interpréter sans recalculer les cartes ni inventer un vécu.

Les quatre angles `temporal`, `behavioral`, `developmental`, `existential`
sont indépendants de l’échelle temporelle. Une question sur une journée peut
rester concrète ou approfondir un apprentissage, tout en gardant les grands
cycles comme contexte. Il n’y a pas de parcours obligatoire en quatre étapes.

Le cadre ressources → contribution / Défi / Résultat est un ensemble de
points de lecture, pas un ordre de progression ni une nouvelle carte « Don ».
Plusieurs fils conducteurs sont possibles ; aucune maturité n’est notée.
Une même énergie peut se manifester différemment selon le contexte et les choix.

## Stockage et compatibilité

La base reste à son emplacement habituel :
`%LOCALAPPDATA%/Olney Engine/olney_profiles.db` (ou `OLNEY_PROFILE_DB`).
`ProfileStore()` crée les tables manquantes au démarrage, de manière additive.
Les tables des profils et événements ne sont ni reconstruites ni remplacées.
Les nouvelles tables suivent les suppressions explicites du profil/événement
par leurs clés étrangères ; ce n’est pas une archive indépendante.

Tables complémentaires : `reading_subjects`, `event_readings`,
`event_participants`, `reading_preferences`, `reading_memory`,
`reading_memory_revisions`.

`reader_key` est une séparation de perspectives locale, **pas un mécanisme
d’authentification**. Un futur serveur devra le fournir depuis sa session
authentifiée et vérifier les droits sur les sujets. Ne jamais le confier au LLM.
La base locale n’est pas chiffrée par ce changement.

L’interface conserve ses vues. Le contexte de la carte et de la lecture du
cycle reçoit le matériau du profil actif, lu avant le travail en arrière-plan.
Le formulaire Événement permet désormais de sélectionner explicitement des
profils participants ; ces liens sont enregistrés dans `event_participants`.
Les personnes saisies librement restent du texte et ne sont **jamais** converties
automatiquement en identifiants (homonymes possibles). Les écrans de mémoire et
de préférences restent à ajouter ultérieurement.

## Lecture d’un profil

Exemple avec les identifiants réels renvoyés par votre stockage :

```python
from profile_store import ProfileStore
from reading_service import ReadingService
from interpretation_validation import validate_context, validate_llm_output

store = ProfileStore()
reader = ReadingService(store)

context = reader.profile_context(
    profile_id, "2026-08-31",
    reading_focus="day",            # focus temporel existant
    options={"angle": "developmental", "question": "Que travailler en ce moment ?"},
)
validate_context(context)
# Après génération seulement : validate_llm_output(model_output, context)
```

Le format individuel est `context.schema.json` 0.5.0. L’ancienne API par dates
reste compatible : elle n’accède à aucune base sans `reading_material` fourni.
Sans profil, les identités `birth:DATE` restent des espaces de démonstration,
pas des identifiants uniques de personnes.

Éléments supplémentaires :

| Champ | Contenu |
|---|---|
| `subject` | identité, type, relation au lecteur, origine, précision et source |
| `reading.intent` | question, angle, profondeur et préférences |
| `learning_frame` | références aux ressources, Défi et Résultat déjà calculés |
| `personal.events` | événements enregistrés et participants explicitement reliés |
| `personal.records` | observations, actions rapportées, hypothèses et statuts |
| `personal.longitudinal` | rapprochements calculés ou étiquetés, pas une psychologie déduite |
| `personal.retrieval` | périmètre non exhaustif de la sélection |
| `personal.excluded_refs` | éléments rétractés, rejetés ou abandonnés |
| `personal.unresolved_links` | liens dont la cible n’est pas dans cette sélection |

Les préférences sont enregistrées explicitement, sans inférer un consentement :

```python
store.set_reading_preferences({
    "depth": "balanced",                 # concise / balanced / deep
    "technical_details": "on_request",  # show / minimal / on_request
    "existential": "on_request",        # never / on_request / when_relevant_or_requested
})
```

Par défaut, pas de recherche longitudinale coûteuse pour une simple lecture
temporelle. `include_patterns=True` l’active ; elle est aussi activée par défaut
pour les angles comportemental, développemental ou existentiel.

## Mémoire attribuée et révisions

```python
observation = store.add_memory(f"profile:{profile_id}", {
    "kind": "observation", "text": "J’ai changé ma façon de travailler.",
    "source_type": "user_reported", "reporter": "Utilisateur local",
    "perspective": "self", "date_start": "2026-08-30",
    "themes": ["autonomie"], "event_ids": [event_id],
})
hypothesis = store.add_memory(f"profile:{profile_id}", {
    "kind": "hypothesis", "text": "L’autonomie pourrait être un fil conducteur.",
    "evidence_ids": [observation["id"]], "counterexample_ids": [],
})
revised = store.revise_memory(
    hypothesis["id"], {}, status="partial", expected_revision=0,
    reason="L’utilisateur reconnaît ce thème au travail, pas dans ses relations.",
)
audit = store.memory_revisions(hypothesis["id"])
```

`kind` vaut `observation`, `action` ou `hypothesis`. Une action est **rapportée**,
pas déduite d’une suggestion. `source_type` distingue utilisateur, tiers,
document et modèle ; `perspective` distingue récit de soi et regard extérieur.
Les dates de l’expérience ne sont pas les dates de création/révision.
Les notes non datées restent un arrière-plan, pas une preuve de polarité.

Hypothèses : `proposed`, `partial`, `confirmed`, `revised`, `rejected`,
`abandoned`. Observations/actions : `reported`, `retracted`.
Même confirmée, une hypothèse reste une hypothèse. Nature et provenance ne
changent pas lors d’une révision. L’ancienne version reste dans l’audit et une
révision concurrente est refusée. Avec `actor="model"`, seules ses hypothèses
encore proposées/révisées sont modifiables : il ne confirme pas une hypothèse
et ne remplace pas une décision humaine. Ce paramètre doit être choisi par le
contrôleur, jamais accepté aveuglément dans la sortie d’un modèle.

Une polarité exige une observation explicite de soi, une date exacte et les
trois identifiants d’une occurrence calculée : `occurrence_id`, `cycle_id`,
`card_id`. Elle ne se propage pas à une autre période ou personne. Une
expérience douloureuse n’implique pas qu’elle a été mal vécue.

## Sujets et événements

Les profils gardent leur `profile_type`. Pour un sujet autre qu’humain, le
choix de la date est à préciser, sans lui attribuer une psychologie humaine :

```python
store.set_subject_details(
    profile_id, origin_label="Fondation officielle", date_precision="exact",
    source="Acte conservé", relationship_to_user="public",
)
store.set_event_participants(event_id, [
    {"profile_id": other_profile_id, "role": "Co-organisateur"},
])
participants = reader.event_context(event_id, mode="participants")
```

Le propriétaire de l’événement et ses participants reliés ont chacun leur
contexte et leur mémoire ; aucun souvenir n’est copié entre personnes. Une
personne dont l’origine est postérieure à l’événement est signalée indisponible.

Pour utiliser l’événement **lui-même** comme point de départ :

```python
store.set_event_reading(
    event_id, origin_label="Lancement public", date_precision="exact",
    source="Annonce publique", event_state="occurred",
)
project = reader.event_context(event_id, mode="origin", target_date="2027-01-15")
```

Cette lecture utilise `event:ID`, pas l’identité du propriétaire. L’événement
reste enregistré sous son profil propriétaire dans l’interface existante :
aucune migration vers des événements sans propriétaire n’est réalisée ici.
`event_state` distingue `recorded`, `occurred`, `planned`, `cancelled`.
Une date approximative reste un point de référence déclaré, pas une plage
d’incertitude calculée. Le formulaire de profils conserve ses champs requis.

L’heure d’origine n’est pas réutilisée comme heure d’une date explorée future.
Si heure/lieu analysés manquent ou sont introuvables, `ReadingService` conserve
les cycles datés et signale l’heure non calculable, sans inventer un lieu.

`compare_profiles(ids, date)` et `event_context(..., mode="participants")`
renvoient une enveloppe simple 1.0 (`mode`, `target_date`, `contexts`, politique
de comparaison et éventuelles indisponibilités). Chacun de ses `contexts` suit
le contrat individuel ; il n’y a ni carte composite ni score de compatibilité.

## Rapprochements et limites

La sélection charge au maximum 80 événements et 100 mémoires, depuis au plus
400 candidats mémoire récents ; défaut 40. Événements explicitement demandés,
liens/thèmes fournis et proximité de date guident le choix. Les exclusions et
preuves/contre-exemples directs sont conservés dans ces limites. Les extraits
de texte sont bornés à 24 000 caractères au total, avec troncature signalée ;
les originaux restent stockés. Ce budget n’est pas la taille totale du JSON,
qui comprend aussi les calculs et les fiches utiles.

La comparaison longitudinale calcule au plus 12 dates de début d’événement,
sans pré-calculer toutes les heures/jours d’une vie. Une répétition exige deux
occurrences distinctes. Les planètes de séquence et de case restent séparées.
Des thèmes explicitement étiquetés peuvent se répéter sous des cartes différentes.
Les dates approximatives et antérieures à l’origine ne reçoivent pas de faux
instantané précis. Un événement prévu ou annulé ne devient pas un vécu parce
que ses cycles sont calculables. Les événements étendus ne sont pas parcourus
sur toute leur durée dans cette première API.

L’analyse sémantique des récits appartient au futur LLM : aucune causalité,
progression psychologique ou « leçon apprise » n’est calculée ici. Le contrat
de sortie propose `learning_synthesis`, `theme_hypotheses` et
`practice_suggestions` facultatifs, sourcés. Les validations contrôlent forme,
références et séparation de provenance, pas la justesse de toute la prose.

## Suite de l’intégration

Brancher un contrôleur de conversation qui choisit le sujet/l’intention,
assemble ce contexte, transmet les consignes canoniques séparément des données,
valide les réponses et demande la confirmation utile avant une écriture.
Ne pas alimenter la mémoire en recopiant automatiquement ses propres réponses.
Il reste à ajouter le chat, son adaptateur de modèle, les écrans de correction
et les évaluations de qualité sur des cas validés. Aucun appel réseau ni
entraînement du modèle n’est exécuté par cette version.
