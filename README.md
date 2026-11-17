# Olney Engine — V1.8.5

Olney Engine est une application Windows consacrée à l’exploration du système
des 52 cartes : profils, cycles temporels, frise chronologique, événements,
relations et lectures structurées assistées par Emmett.

## Installer l’application

Téléchargez l’installateur depuis la section **Releases** du dépôt GitHub, puis
lancez `Olney_Engine_Setup_1.8.5.exe`. Python n’est pas nécessaire pour utiliser
la version installée.

Les profils, événements, relations et conversations sont conservés uniquement
dans la base locale de l’utilisateur. Ils ne sont ni inclus dans le dépôt ni
envoyés automatiquement vers un service externe. La clé OpenAI reste en mémoire
pendant la session et n’est pas enregistrée par Olney Engine.

## V1.8.5 — identité visuelle et distribution GitHub

- Nouveau logo pique intégré à l’application, à l’exécutable et aux raccourcis.
- Installateur habillé avec l’étoile historique et une palette parchemin.
- Mode clair entièrement réaccordé à cette identité chaude.
- Distribution GitHub préparée sans données personnelles ni secrets.
- Version du moteur, interface, documentation et installateur synchronisées.

## V1.8.4 — Terra et listes conversationnelles lisibles

- Emmett utilise désormais `gpt-5.6-terra` par défaut, avec un effort de
  raisonnement moyen et une verbosité moyenne ; le modèle reste modifiable dans
  Connexion.
- La liste des conversations conserve l’ordre de création, indépendamment des
  discussions rouvertes ou consultées.
- Les conversations affichent leur sujet sous leur titre et les libellés longs
  reviennent proprement à la ligne dans un panneau latéral élargi.
- La liste des relations bénéficie du même affichage enveloppé, d’une largeur
  accrue et de séparateurs continus en thème clair comme en thème sombre.

## V1.8.3 — continuité relationnelle d’Emmett

- Depuis le sujet d’un profil, Emmett reconnaît désormais une relation nommée
  par son titre ou par l’autre personne, dans les deux sens.
- Le dossier relationnel devient le focus ponctuel du message sans modifier le
  profil ni l’horloge visibles. Les questions suivantes conservent ce focus ;
  une demande explicite permet de revenir au profil de départ.
- Plusieurs relations portant le même prénom déclenchent une demande de
  précision au lieu d’un choix arbitraire.
- Le routage d’un événement reste prioritaire lorsque la question porte sur une
  rencontre ou un autre événement nommé, même si une relation porte un titre
  similaire.
- La compression conserve maintenant les règles relationnelles complètes et
  masque les positions internes inutiles du chemin de vie de la relation.
- Le contexte précise que toutes les cartes de ce chemin appartiennent au lien :
  une répétition personnelle est une résonance, pas la propriété d’une étape.
- Les consignes d’Emmett imposent des correspondances directionnelles précises,
  interdisent les déductions psychologiques tirées de notes opaques et limitent
  les conseils pratiques aux demandes qui en ont réellement besoin.

## V1.8.2 — Emmett et routage conversationnel

- Le chatbot s’appelle désormais **Emmett**, interlocuteur de l’Olney Engine ;
  le moteur et la méthode conservent le nom Olney Engine.
- `Entrée` envoie le message et `Maj + Entrée` insère un retour à la ligne.
- Une date explicite, « hier », « demain » et les événements nommés sont résolus
  localement avant l’appel au modèle. Un événement lié à un profil devient le
  focus ponctuel du message sans remplacer le sujet principal de la conversation.
- Le focus calculé est affiché sous les sélecteurs. Les demandes suivantes
  conservent le focus événementiel jusqu’à ce que l’utilisateur revienne
  explicitement au présent ou choisisse un autre sujet.
- Un contrat de conversation interdit à Emmett de prétendre modifier la base,
  déplacer l’interface ou lancer après coup un calcul qui n’a pas été préparé.
- Les réponses privilégient la lecture demandée, masquent les références
  techniques et évitent les conseils génériques ou les validations rétrospectives.
- L’API dispose de 3 000 jetons de génération, d’un effort de raisonnement faible
  et d’une verbosité moyenne avec `gpt-5-mini`. Une sortie vide causée par la
  limite est retentée une fois et les autres erreurs exposent leur statut réel.

## V1.8.1 — saisie du tchat toujours accessible

- La zone de messages adopte une hauteur minimale compacte afin de ne plus
  repousser le champ de saisie sous le bord d’une fenêtre de faible hauteur.
- Le compositeur est clairement identifié par `ÉCRIS TON MESSAGE`, avec un
  contour renforcé, trois lignes de saisie et le bouton Envoyer toujours visible.

## V1.8.0 — laboratoire de conversation Olney

- Nouveau bouton `✦ OLNEY` dans le menu principal et nouvelle page de tchat.
- Le sujet peut être un profil, une relation, un événement ou une discussion
  générale ; l’angle de lecture reste sélectionnable avant chaque conversation.
- Le moteur prépare un contexte calculé compact : règles communes, cartes et
  cycles utiles, données personnelles attribuées et mémoire pertinente.
- Les conversations sont enregistrées dans la base SQLite locale ; la clé API
  reste uniquement en mémoire pendant la session et n’est jamais stockée.
- Les appels utilisent l’API Responses d’OpenAI avec `store: false`, un historique
  récent borné et une file séparée afin de ne jamais ralentir l’horloge.
- Le panneau Contexte permet de voir exactement les données transmises au modèle,
  tandis que le statut affiche le modèle et les jetons réellement consommés.
- Modèle initial : `gpt-5-mini`, modifiable dans Connexion sans dépendance Python
  supplémentaire.

## V1.7.6 — lecture relationnelle approfondie

- Les fonctions relationnelles de Morera exposent maintenant leur essence,
  leur ressource constructive et leur tension possible au lieu d’une seule phrase.
- L’ordre manifesté demeure la structure principale entre les deux cartes de
  naissance ; un bloc séparé compare désormais, dans l’ordre naturel, les deux
  cartes de naissance puis chacune avec la carte de relation.
- Le moteur recherche dans les deux sens la présence des cartes natales de l’un
  dans le chemin annuel de l’autre et précise la fonction occupée cette année.
- Les horloges synchronisées restent le climat actuel selon la convention
  fractale Olney, sans être confondues avec les liens permanents.
- La carte de relation ne déclenche plus d’horloge artificielle : la date commune
  demeure une date de l’histoire du lien et non une naissance symbolique inventée.

## V1.7.5 — hiérarchie et recherche des relations

- La carte de relation est présentée avant son chemin de vie, avec une couleur
  verte plus accueillante et distincte des autres sections.
- La recherche d’une relation examine désormais son titre, son type, ses notes
  et les prénoms/noms complets des deux personnes.
- Lorsqu’un nom est masqué par un titre personnalisé, le résultat filtré montre
  les deux identités et reçoit une surbrillance afin de rendre la correspondance
  immédiatement visible.

## V1.7.4 — chemin de vie et horloge de la relation

- La page Relations se réorganise automatiquement lorsque la fenêtre est plus
  étroite : le texte et les activations reviennent à la ligne, et les deux gros
  panneaux s’empilent avant de dépasser du cadre.
- La carte de relation expose désormais son propre chemin de vie manifesté,
  centré de Mercure jusqu’au Résultat, sans réintroduire les Défis/Résultats
  personnels dans la comparaison des deux sujets.
- Un clic sur la carte de relation ouvre une horloge temporaire à partir de la
  date commune affichée. La carte calculée pilote alors les cycles ; aucun profil
  enregistré n’est modifié et aucun ascendant ou secondaire n’est inventé.

## V1.7.3 — participants et lecture relationnelle épurée

- Les profils choisis dans un événement sont enregistrés comme participants réels en BDD.
- Les noms libres restent du texte et ne sont jamais convertis automatiquement en identité.
- La page Relation conserve seulement naissance et secondaires dans les encadrés natals.
- Les correspondances comparent uniquement les deux cartes de naissance et fusionnent les définitions répétées.
- La carte de relation reçoit une fiche développée pour le lien lui-même.
- Les encadrés de chemin de vie n’affichent plus Défi et Résultat.

## V1.7.2 — relations recentrées

- Le menu Relations se place après Événements.
- La carte de relation et les deux horloges synchronisées sont réunies et centrées.
- Le tableau centré conserve uniquement les correspondances de l’ordre manifesté.
- Les cartes associées sont limitées à celles de chaque carte de naissance.
- Les activations concernent uniquement naissance, secondaires et chemin de vie manifesté.

## V1.7.1 — correction des horloges relationnelles

- affiche réellement les deux horloges synchronisées dans la fiche Relation ;
- corrige l'interruption du rendu sous le bandeau des horloges.

## V1.7.0 — relations

- Nouveau menu et page Relations entre deux profils enregistrés.
- Carte de relation, cartes natales, secondaires et associées.
- Première version des correspondances permanentes, ensuite recentrée sur l’ordre manifesté en V1.7.2.
- Comparaison des deux chemins de vie et des deux horloges à date commune.
- Dossier structuré `ReadingService.relationship_context()` pour le futur LLM,
  sans score de compatibilité.

## V1.6.0 — préparation du compagnon Olney

- Annotation dans le titre de l’encadré : `ANALYSE (Aujourd’hui / Passé / Futur)`.
  Le champ `DATE ANALYSÉE` reste fixe, sans changement de largeur selon la date.
- Backend de lecture enrichi : intention, pédagogie, sujet, événements,
  souvenirs attribués et hypothèses révisables.
- Règles 0.7.0, contexte JSON 0.5.0 et réponse LLM 0.4.0.
- Les notes, événements pertinents et mémoires du profil actif alimentent le
  contexte commun aux lectures ; aucun texte libre n’est traité comme une consigne.
- Stockage SQLite complémentaire auto-initialisé, sans remplacement des profils
  ou événements existants. Aucun modèle/API ni entraînement automatique ajouté.

Voir [BACKEND_LECTURE.md](BACKEND_LECTURE.md) pour les API, exemples et limites.

## What this is

A calculation engine extracted from `tableaux suivi des cartes.xlsx`.

The calculation core is deliberately separated from the AI:
- calculation module = deterministic calculations
- Olney/LLM = interpretation and conversation

## Files

- `olney_engine.py` — engine
- `data.json` — 90 canonical 52-card series + card dictionary
- `places.json` — index mondial hors ligne des villes, coordonnées et fuseaux
- `astro_engine.py` — résolution du lieu et calcul astronomique de l'ascendant
- `hour_card.py` — calcul hors ligne de l'heure solaire vraie et de la carte de l'heure
- `profile_store.py` — profils locaux SQLite, dernier profil actif et import/export JSON
- `reading_store.py` — métadonnées, participants, préférences et mémoire révisable
- `reading_service.py` — lectures de profils, comparaisons et deux lectures d’événement
- `chat_store.py` — conversations et messages conservés dans la base locale
- `olney_chat.py` — préparation compacte du contexte et client OpenAI Responses
- `chat_ui.py` — page de conversation Olney, historique et connexion de session
- `personal_context.py` — intention, mémoire ciblée et rapprochements factuels bornés
- `interpretation/` — connaissances, polarités, règles, schémas et consignes LLM versionnés
- `interpretation_runtime.py` — enrichissement des faits calculés en dossier d’interprétation
- `cycle_reading.py` — dossier ordonné des sept étapes d’un cycle pour l’interface et le LLM
- `cycle_reading_ui.py` — vue Lecture du cycle et parcours consultable
- `natal_card_ui.py` — fiches permanentes de la carte de naissance et des cartes secondaires
- `analysis_work.py` — calculs hors interface et cache limité de l’ascendant natal
- `ui_jobs.py` — travaux en arrière-plan, priorité à la dernière demande et vues différées
- `navigation.py` — historique de navigation temporaire, limité à 100 positions
- `Lancer_Olney.bat` — lancement direct de l’interface sous Windows
- `tests/test_engine.py` — sanity tests
- `tests/test_astro_engine.py` — tests des lieux, fuseaux historiques et ascendant
- `tests/test_hour_card.py` — tests de la grille HOUR CARDS et des cas solaires validés
- `tests/test_interpretation.py` — tests de la base et du contrat d’interprétation
- `tests/test_profiles.py` — tests de création, modification, duplication et import/export
- `requirements.txt` — no third-party Python dependency

## Usage

```python
from olney_engine import OlneyEngine

engine = OlneyEngine()

state = engine.full_state(
    birth_date="1965-05-18",
    target_date="2025-02-20",
    target_time="12:00",
    target_place="Longjumeau, FR",
)

print(state["birth"])
print(state["year"]["year_card"])
print(state["week"]["day_card"])
print(state["day"]["card"])
print(state["hour_card"]["card"])
```

## Dossier d’interprétation

```python
context = engine.tool_get_interpretation_context(
    birth_date="1988-10-27",
    target_date="2026-08-26",
    target_time="17:51",
    target_place="Longjumeau, FR",
)

print(context["profile"]["birth_card"])
print(context["cycles"])
print(context["global_direction"])
```

Ce dossier contient les significations et polarités, mais aussi les faits de
position déjà calculés : carte active, planète de séquence, territoire occupé,
carte de soutien, couple planétaire, Couronne, Défi, Résultat et hiérarchie.
L’interface locale et le backend LLM doivent consommer ce même format.

Pour exporter un exemple JSON sans modifier l’application :

```text
python tools/export_interpretation_context.py 1988-10-27 2026-08-26 --time 17:51 --place "Longjumeau, FR"
```

Pour valider la base sans aucune dépendance externe :

```text
python tools/validate_interpretation.py
python tools/run_plain_tests.py
```

## Important validation step

This is a first implementation of the formulas inspected in the workbook.
Before production, validate it against the workbook on a large test matrix.

Do NOT let the LLM perform these calculations itself.

## Interface V1.5.9 — navigation temporelle et bandeau fixe

- **Une seule date et heure analysées** pour l’horloge, les tableaux, la frise
  et les lectures. Cliquer sur l’une des sept cartes de période dans Résultat
  déplace la date au début de sa période, conserve l’heure analysée et ouvre
  **Lecture du cycle → Étape consultée** après recalcul de toute l’horloge.
- Dans Lecture du cycle, les sept grandes cartes du haut sont remplacées par
  un **bandeau compact fixé au-dessus de la zone de défilement** : cycle,
  carte/planète analysée, étape sur sept, période et date analysée. Le texte
  peut défiler jusqu’en bas sans faire disparaître ces repères. Les titres
  du parcours détaillé restent cliquables pour explorer les autres périodes.
- Le repère **En cours aujourd’hui** reste lié au calendrier réel, distinct
  de l’étape explorée. Les fiches Lune, Soleil, Défi, Résultat et les portraits
  natals restent consultables sans déplacement temporel.
- Boutons **Retour / Suivant** en haut, également accessibles par Alt+← / Alt+→.
  Ils restaurent la date, l’heure, le lieu, le profil et la vue précédents.
  Historique en mémoire uniquement, limité à 100 positions ; aucune table
  SQLite ni sauvegarde d’une copie du dossier interprétatif. Une nouvelle
  exploration après Retour remplace la branche suivante. Seuls les calculs
  terminés et encore pertinents sont enregistrés. Les profils modifiés ou
  supprimés ne sont jamais réécrits par l’historique : leurs anciennes données
  se rouvrent sans profil associé.
- Repère discret **Passé / Aujourd’hui / Futur** près de la date analysée.
  Reset conserve son fonctionnement : retour à la date **et** à l’heure réelles.
- 118 tests automatisés, validation interprétative, contrôles Tk des 44 liens,
  du bandeau fixe et des deux thèmes, de l’historique, des changements de
  profils/événements, des requêtes rapides et des erreurs. Formules, données
  canoniques, fiches interprétatives et stockage utilisateurs inchangés.

Les sections ci-dessous décrivent les versions précédentes. En particulier,
la consultation sans déplacement temporel des sept cartes de période,
décrite en V1.5.8, est remplacée par la navigation synchronisée en V1.5.9.

## Interface V1.5.8 — fiches natales et navigation des cartes

- Repère permanent « Aujourd’hui » près du Reset. Celui-ci revient toujours
  à la date et à l’heure actuelles, sans réintroduire de date mémorisée.
- Ordre naturel conserve son Tableau et propose **Carte principale** et
  **Carte secondaire**. Pour le Scorpion, deux fiches secondaires distinctes
  sont accessibles ; la troisième fiche disparaît pour les autres signes.
- Fiches fondées sur les 52 profils d’énergie existants : rôle natal,
  énergie, élément, manifestations, vécu constructif et difficile. Les
  secondaires gardent leur maître astrologique et complètent la carte de
  naissance. Aucun nouveau calcul, ni assimilation à une activation temporaire.
- La carte de naissance du Profil essentiel et celle de l’horloge en Lecture
  globale ouvrent directement sa fiche, avec retour à la Lecture globale.
- Dans les quatre vues Résultat, les onze cartes sont cliquables, au clic
  ou au clavier, vers **Lecture du cycle → Étape consultée**. La fonction de
  la carte sélectionne le bon détail : sept étapes planétaires, Lune, Soleil,
  Défi ou Résultat. La page défile jusqu’au détail sans déplacer la date ou
  l’heure de l’horloge ; le repère « En cours » reste lié à aujourd’hui.
- Navigation compatible avec le chargement différé : la carte demandée est
  consultée dès que le dossier du cycle est prêt. Une nouvelle analyse annule
  cette demande pour ne pas ouvrir une occurrence dépassée.
- 114 tests automatisés ; contrôles Tk des 44 liens, portraits clair/sombre,
  défilement et changements Scorpion/autre signe/Joker. Données canoniques,
  fiches sources, profils et événements conservés.

## Interface V1.5.7 — retour au présent et mises à jour

- **Reset revient toujours à maintenant : date et heure locales actuelles.**
  La date mémorisée et son affichage sont retirés, même après une saisie manuelle.
  Le profil, les données de naissance et le lieu d’analyse ne changent pas.
  Infobulle : « Revenir à maintenant ». Les événements restent le moyen de
  conserver puis rouvrir une analyse datée.
- Calcul de l’horloge, dossiers complets des cycles et périodes de la frise en
  arrière-plan, sans accès à Tk ni à SQLite depuis le travailleur. Les demandes
  intermédiaires en attente sont ignorées ; un ancien résultat ou une ancienne
  erreur ne remplace jamais la dernière demande. Les flèches cumulent les
  déplacements depuis la date/heure demandée, même pendant un calcul.
- Indicateur animé « Mise à jour… » après 150 ms, dans le titre de l’horloge
  ou dans l’onglet concerné. Le dernier affichage reste présent pendant le calcul.
- Les onglets masqués gardent leur dernier rendu et reçoivent uniquement les
  dernières données à afficher à leur ouverture. Les données identiques ne
  provoquent pas une nouvelle reconstruction. L’ascendant est réutilisé tant
  que ses données natales sont identiques (cache mémoire limité à 32 entrées).
- Le thème n’est plus réappliqué à toute l’application à chaque calcul.
  Les résultats sont mis en couleur avant de rendre la main à l’affichage ;
  les vues d’interprétation gèrent directement leur palette.
- 111 tests automatisés, contrôle Tk des vues clair/sombre et scénario dédié
  aux clics rapides, à l’animation, à la frise, au Reset et aux erreurs.
  Calculs canoniques, base interprétative et stockage utilisateurs conservés.

Les sections suivantes décrivent l’historique des versions : les anciennes
mentions d’une date d’ancrage de Reset ne s’appliquent plus depuis la V1.5.7.

## Interface et interprétation V1.5.6

- Bouton « Explorer cette période » retiré de l’étape consultée. Un clic sur
  une carte reste une consultation, sans déplacement de la date d’analyse.
- Reset retrouve la date sauvegardée et remet désormais l’analyse à l’heure
  locale actuelle de l’ordinateur. L’heure de naissance et le lieu ne changent
  pas ; l’horloge est recalculée avec cette nouvelle heure.
- Le repère « En cours » reste lié à aujourd’hui, indépendamment de la date
  consultée. Formules, tableaux, profils et événements inchangés.
- 104 tests et validation des dossiers réussis ; interface vérifiée en clair
  et sombre, avec Reset testé à différentes heures et sans modifier la naissance.

## Interface et interprétation V1.5.5

- Lecture du cycle : toute la page défile, cartes et texte ensemble. Aucun
  bandeau de cartes fixe ni mode de lecture agrandie supplémentaire.
- Le contour vert et « En cours » suivent la date réelle d’aujourd’hui,
  indépendamment de la date explorée. Un cycle entièrement passé ou futur
  ne force plus de carte en cours. La carte consultée reste repérée séparément.
- Les repères du présent sont rafraîchis au changement de jour sans déplacer
  la date d’analyse, l’étape consultée ni l’ancrage de Reset.
- Ordre des onglets : Frise chronologique, puis Lecture globale.
- Base V0.5.1 / contexte V0.4.1 : instantané `cycle_reading.present` distinct
  des faits relatifs à la date analysée, également documenté pour le futur LLM.
- Formules, tables, profils et événements conservés.
- 104 tests réussis, validation des dossiers et contrôle Tk clair/sombre :
  défilement intégral, statuts réel/exploré, cycles passés/futurs, changement
  de jour, exploration et Reset.

## Interface et interprétation V1.5.4

- Nouvelle vue **Lecture du cycle**, à côté d’Interprétation : chemin de vie,
  cycle de 7 ans, cycle annuel et semaine. L’Ordre naturel reste inchangé.
- Bande fixe des sept cartes, dates et repérage de la période active ; synthèse
  du mouvement, transitions, détail consultable, éléments, particularités,
  Lune, Défi et Résultat propres au cycle.
- Cliquer une carte consulte son étape sans déplacer la date. Le bouton
  **Explorer cette période** synchronise explicitement l’horloge avec son début.
  La date sauvegardée de Reset, l’heure et le lieu sont conservés.
- Dossier commun au futur LLM avec `reading_mode="cycle"`, préparé à la demande,
  sans appel réseau. Base V0.5.0, contexte V0.4.0, schéma de réponse V0.3.0.
  Les sept étapes sont validées dans l’ordre calculé et gardent leurs sources.
- 101 tests et contrôle d’interface clair/sombre. Tables, profils, événements
  et formules de calcul préservés.
- Limite préexistante repérée : certains anniversaires basculent un jour plus
  tôt avec le calcul d’âge 30/360. Si carte active et calendrier se contredisent,
  la nouvelle lecture du cycle signale ce cas ; corriger la règle d’âge reste
  une modification séparée du moteur.

```text
python tools/export_interpretation_context.py 1988-10-27 2026-08-31 --focus fifty_two_days --mode cycle
```

## Interface et interprétation V1.5.3

- Les 52 fiches d’énergies sont actives : cinq modèles validés, complétés par
  47 rédactions individualisées. Noyau, deux vécus, manifestations ouvertes,
  lecture selon les cycles et particularités fixes/semi-fixes.
- Les vues Interprétation affichent ces textes dans L’essentiel, les deux vécus,
  Dans la vie et Au fil des cycles. La Lecture globale utilise leurs résumés.
- Cœur–Feu, Trèfle–Air, Carreau–Eau, Pique–Terre : descriptions individuelles
  et rubrique Éléments en présence dans la lecture globale, reliée aux cartes
  actives de l’horloge, y compris l’heure lorsqu’elle est calculée.
- Base V0.4.0, contexte V0.3.0 : chaque carte référence sa fiche complète et
  son enseigne ; `knowledge_bundle.card_profiles` déduplique les fiches utiles.
  Consignes LLM actualisées, sources et statuts de relecture conservés.
- Toutes les fiches sont lisibles dans `interpretation/FICHES_CARTES.md` ; la
  source active est `interpretation/card_profiles.json`.
- 90 tests et contrôle Tk clair/sombre réussis. Tables, calculs, profils et
  événements conservés ; aucun LLM connecté par cette mise à jour.

## Interface et interprétation V1.5.2

- Textes d’interprétation et de synthèse allégés : suppression des mises en garde
  répétitives, maintien des ressources et tensions comme expressions de l’énergie.
- Style LLM centré sur les énergies incarnées et leurs manifestations ouvertes.
  Les consignes internes de prudence restent conservées.
- Fiches pilotes allégées, toujours séparées et non activées ; noyau du 5♠ repris
  selon la formulation validée avec Sébastien.
- Base d’interprétation V0.3.1, sans changement de schéma ni de calcul.

## Interface et interprétation V1.5.1

- Référence interprétative V0.3 : figures incarnées, dualité semi-fixe, palette
  permanente en arrière-plan, lecture fractale et Lune propre à chaque séquence.
- Fil rouge synthétique partagé par l’interface et le contexte LLM : répétitions,
  contrastes, activations et contextes, avec données justificatives identifiables.
- Textes des figures recentrés sur les facultés de la personne ; rubrique Lune
  du cycle et expression planétaire clarifiée dans les vues Interprétation.
- Contexte JSON V0.2 : séquence/période explicites, zoom de lecture optionnel,
  palette, Lunes, règles, sources et mémoire rattachée à une occurrence précise.
- Contrats d’entrée/sortie et validation hors ligne des données et références.
- Cinq fiches pilotes séparées dans `interpretation/drafts/`, non activées.
- Corrections documentaires du 7♥ et du 7♠ ; anciennes hypothèses archivées.
- Aucune modification des tables, formules, profils enregistrés ou événements.
  Pas de LLM connecté ni d’apprentissage automatique dans cette version.

## Interface V1.5.0

- Menu Profil : ajout d’un séparateur entre l’historique récent et « Voir tous
  les profils… », et suppression du signe « + » devant cette entrée.

## Interface V1.4.9

- Le bouton Événements devient un menu déroulant : cinq derniers événements
  consultés, accès à la grille complète, ajout libre et enregistrement rapide de
  l’analyse actuellement affichée.
- Les profils possèdent désormais un type : Humain, Ville, Pays, Organisation,
  Projet ou Animal. Les profils existants sont automatiquement classés Humain.
- La catégorie Amour rejoint les catégories d’événements.
- Toutes les colonnes des pages Profils et Événements affichent un indicateur de
  tri. Un clic choisit la colonne, un second inverse l’ordre.
- L’historique des événements est stocké localement et actualisé lors de leur
  ouverture, indépendamment de leur date chronologique.

## Interface V1.4.8

- Les cartes de l’Horloge des cycles ouvrent maintenant directement la vue
  Résultat de leur cycle. Les raccourcis de Lecture globale conservent leur
  navigation vers les interprétations détaillées.
- La page Événements adopte une grille visuelle proche de celle des profils et
  affiche, pour chaque ligne, les cartes Chemin de vie, Année, 52 jours, Jour et
  Heure réellement actives à la date enregistrée.
- La grille réunit les événements de tous les profils et précise leur
  propriétaire. L’ouverture d’un événement charge automatiquement le bon profil.
- Un événement peut être attribué à n’importe quel profil, avec le profil actif
  présélectionné. Le champ Personnes propose les profils enregistrés tout en
  restant libre pour saisir une personne extérieure.

## Interface V1.4.7

- Ajout d’un espace Événements directement dans l’application, accessible entre
  le menu Profil et le bouton de thème.
- Chaque événement est lié à un profil et conserve son titre, sa catégorie, sa
  date ou période, son heure, son lieu, son importance, ses personnes, ses
  mots-clés et ses notes.
- L’ouverture d’un événement déplace la date actuellement explorée et recalcule
  l’horloge sans écraser la date d’ancrage utilisée par Réinitialiser.
- Les événements du profil actif apparaissent aussi comme marqueurs sur la frise
  chronologique. Les tables SQLite sont créées automatiquement et supprimées en
  cascade avec leur profil.

## Interface V1.4.6

- Le petit menu des profils redevient un historique pur des cinq dernières
  consultations : les favoris n’y sont ni épinglés ni signalés.
- Lorsqu’un profil est choisi depuis ce menu pendant que la page Profils est
  ouverte, l’application revient automatiquement à l’horloge et charge le
  profil sélectionné.

## Interface V1.4.5

- Les zones figée et défilante de la page Profils utilisent désormais les
  mêmes hauteurs exactes pour leurs bandeaux, en-têtes et lignes.
- Le déplacement vertical est neutralisé lorsque tous les profils tiennent
  dans la fenêtre, ce qui supprime l’espace vide accessible au-dessus du
  tableau.
- Les favoris sont épinglés en tête de la page immédiatement après leur ajout,
  même lorsqu’un tri de colonne est actif.

## Interface V1.4.4

- Tous les en-têtes de la page Profils deviennent triables, dans les deux sens,
  avec un indicateur visuel sur la colonne active.
- Un profil peut être ajouté aux favoris ou retiré des favoris depuis la barre
  d’actions. Les favoris sont marqués d’une étoile et remontent en priorité dans
  le menu rapide.
- Les colonnes Prénom et Nom restent figées à gauche pendant le défilement
  horizontal des données natales, de l’horloge et du chemin de vie.
- La molette déplace verticalement la liste ; Maj + molette permet d’explorer
  horizontalement toutes les colonnes jusqu’à Défi et Résultat.

## Interface V1.4.3

- Les cartes Défi et Résultat retrouvent leurs cases entièrement colorées dans
  la page Profils ; seules les sept cartes planétaires restent présentées avec
  un contour coloré.
- Le bouton « Nouveau » est ajouté juste après « Modifier » dans la barre
  d’actions de la page Profils.

## Interface V1.4.2

- Dans la page Profils, les cartes Mercure à Neptune, Défi et Résultat du
  chemin de vie reprennent les couleurs canoniques des vues Résultat sous forme
  de contours uniquement. Le fond reste neutre pour une lecture plus élégante.

## Interface V1.4.1

- La page Profils affiche le signe et l’ascendant immédiatement après la date
  de naissance.
- Le bandeau du groupe permanent est simplifié en « Cartes du chemin de vie ».
- Les cartes Défi et Résultat du chemin de vie sont ajoutées après Neptune avec
  leurs couleurs respectives.
- Le menu n’affiche plus une seconde commande « Gérer les profils » : « Voir
  tous les profils… » devient l’unique accès à la page complète.

## Interface V1.4.0

- La gestion des profils est maintenant une véritable page intégrée à
  l’application, avec retour direct vers l’horloge.
- Les cartes de l’horloge sont regroupées sous un bandeau « Aujourd’hui » et
  mises en valeur avec les couleurs propres à chaque cycle.
- La colonne « Carte primaire » reprend son appellation canonique « Carte de
  naissance ».
- Les sept cartes planétaires du chemin de vie sont affichées à la suite dans
  une zone colorée distincte et identifiée comme palette permanente.
- Les colonnes prénom et nom sont plus compactes et la page reste navigable
  horizontalement.
- Le menu rapide montre les cinq profils consultés le plus récemment, et non
  les cinq premiers par ordre alphabétique.
- Dans les formulaires, un clic ou une tabulation sélectionne désormais tout le
  contenu du champ ; le passage du nom de famille à la date sélectionne bien la
  date complète.

## Interface V1.3.9

- Le menu rapide affiche au maximum cinq profils. Au-delà, une commande
  « + Voir tous les profils… » ouvre la gestion complète.
- La gestion des profils devient une grande page dédiée, redimensionnable et
  centrée, avec recherche instantanée.
- Chaque profil est présenté sur une ligne avec prénom, nom, naissance, carte
  primaire, cartes secondaires et horloge actuelle : chemin de vie, année,
  52 jours, jour et heure.
- Les actions Ouvrir, Modifier et Supprimer restent directement accessibles.

## Interface V1.3.8

- Les profils disposent maintenant de deux champs distincts : prénom et nom de
  famille. Deux personnes ayant le même prénom peuvent ainsi être enregistrées
  lorsque leur nom de famille diffère.
- Les profils déjà existants sont migrés automatiquement et restent intacts.
- Le menu des profils est simplifié : les commandes Dupliquer, Importer et
  Exporter sont masquées en attendant leur futur emplacement.

## Interface V1.3.7

- Toute modification des données de naissance depuis l'écran principal quitte
  le profil actif sans altérer le profil enregistré.
- « Enregistrer… » demande alors un nom et crée un nouveau profil.
- La modification volontaire d'un profil passe par « Gérer les profils » et
  rouvre sa fiche complète au lieu d'un simple renommage.
- Le Verseau utilise uniquement Uranus et les Poissons uniquement Neptune :
  le Scorpion reste le seul signe possédant deux cartes secondaires.

## Interface V1.3.6

- La création d'un profil rassemble désormais directement le nom, la date,
  l'heure et la ville de naissance dans une fiche dédiée.
- La ville bénéficie des suggestions de la base locale dès la création.
- La fenêtre de gestion des profils s'ouvre centrée sur Olney Engine.

## Interface V1.3.5

- Ajout des profils locaux dans une base SQLite séparée des fichiers de l'application.
- Menu de profil en haut à droite avec sélection, création, sauvegarde et duplication.
- Fenêtre de gestion avec ouverture, renommage et suppression confirmée.
- Import et export individuel au format `.olney.json`.
- Le dernier profil utilisé est automatiquement chargé au prochain lancement.

## Interface V1.3.4

- La date d'ancrage reste visible à côté du reset sans libellé supplémentaire.

## Interface V1.3.3

- La date saisie manuellement devient une cible persistante distincte de la date explorée.
- La frise et toutes les flèches de l'horloge mettent désormais à jour le champ de date visible.
- Le reset revient à la cible mémorisée, affichée directement à côté de son bouton.

## Interface V1.3.2

- Les cartes annuelles et de 52 jours restent détaillées plus longtemps lors du recul.
- Ajout de la bande Heure et des zooms rapprochés « 2 jours » et « 12 heures ».
- Ajout de repères intégrés pour la Couronne, les convergences et les cases doubles.
- Les changements d’enseigne sont signalés directement aux frontières des périodes.
- Le bouton de thème montre désormais le Soleil en mode sombre et la Lune en mode clair.

## Interface V1.3.1

- Les quatre bandes chronologiques conservent désormais leur couleur d'origine à tous les niveaux de zoom.

## Interface V1.3.0

- Les échelles non détaillées restent affichées sous forme de bandes chronologiques pleines grisées.
- Suppression du rappel supérieur des cartes actives et de la date sélectionnée.
- L'axe de dates et le curseur central restent disponibles directement dans la frise.

## Interface V1.2.9

- Le déplacement par molette et par flèches s'adapte maintenant au niveau de zoom, de 7 ans à 1 jour.
- Les quatre bandes restent visibles à tous les zooms ; les échelles inactives sont représentées par des repères gris.
- La légende des symboles a été retirée du résumé supérieur.

## Interface V1.2.8

- L'onglet porte désormais le nom complet Frise chronologique.
- Suppression de la bande Tableau 7 ans : ses frontières apparaissent directement tous les sept segments annuels.
- Ajout des frontières annuelles dans la bande 52 jours et des frontières hebdomadaires dans la bande Jour.
- Apparition progressive des échelles selon le zoom : Chemin de vie seul au recul maximal, puis année, 52 jours et enfin cartes quotidiennes.
- Ajout des vues 28 ans, 14 ans, 7 ans, 3 ans, 1 an, 4 mois, 1 mois et 1 semaine.

## Interface V1.2.7

- Ajout de la couche Chemin de vie, avec une carte active par période de 13 ans.
- La molette déplace maintenant la frise par pas mensuels au lieu de modifier le zoom.
- Les flèches temporelles déplacent précisément la date analysée d'une année.

## Interface V1.2.6

- Ajout de l'onglet interactif Frise chrono après Lecture globale.
- Superposition des périodes Tableau 7 ans, carte annuelle et carte 52 jours.
- Clic ou glissement sur la frise pour recalculer la date analysée et synchroniser l'horloge.
- Zoom temporel, déplacement rapide, retours de la carte de naissance et convergences année/52 jours.
- Ajout des requêtes temporelles déterministes `get_periods`, `get_transitions`, `find_card_occurrences` et `find_convergences`.

## Interface V1.2.5

- La hauteur initiale de la fenêtre a été légèrement augmentée afin que les légendes des échanges restent entièrement visibles en vue Tableau.

## Interface V1.2.4

- L'Ordre naturel conserve uniquement sa vue Tableau.
- L'onglet de cycle sélectionné met en évidence sa carte correspondante dans l'horloge.
- Le changement de thème utilise désormais un bouton carré Soleil/Lune.

## Interface V1.2.3

- Le pied de page est désormais ancré en bas de la fenêtre : l'état du calcul et la signature restent toujours visibles.
- La signature affiche explicitement la version courante de l'application.

## Interface V1.2.2

- Les échanges sont formulés dans leur ordre réel : la carte active déplace la carte propriétaire, puis la carte de soutien occupe sa place d'origine.
- Les interprétations décrivent désormais la carte comme une expression incarnée à l'instant étudié, et non comme un « niveau » abstrait.
- Le Fil rouge devient une synthèse globale de l'horloge, sans répétition des mots-clés planétaires déjà détaillés dans la Cascade.

## Interface V1.2.1

- En mode clair, les cartes de l'horloge interprétative ont un contour plus net.
- Les vues Lecture globale et Interprétation utilisent des nuances légères pour mieux séparer les blocs de lecture.
- Le mode sombre conserve sa palette existante.

## Interface V1.2.0

- le fond coloré des cadres **Naissance** et **Analyse** est supprimé en mode sombre ; seuls leurs contours structurent désormais les champs ;
- l’espace de l’horloge est placé précisément entre le bandeau coloré et le cadre de chaque carte ;
- le tableau reste au centre exact, tandis que chaque légende est centrée dans l’espace compris entre le tableau et le bord correspondant de l’application.

## Interface V1.1.9

- les titres **Naissance** et **Analyse** restent visuellement contenus dans leurs cadres ;
- les cartes de l’horloge disposent d’un léger espace supplémentaire sous le bord supérieur ;
- le bouton de remise à l’heure actuelle est placé au-dessus de **Calculer** ;
- la validation d’une ville avec Entrée conduit bien à la date analysée sans sauter vers l’heure ;
- le tableau, la légende d’échange et la légende des couleurs forment désormais un groupe centré, en fenêtre comme en plein écran.

## Interface V1.1.8

- les cartes de l’horloge ouvrent désormais directement la vue **Interprétation** du cycle concerné ;
- la lecture globale enrichit les cartes secondaires, le fil rouge, la cascade, le Défi et la direction du chemin de vie avec leurs mots-clés ;
- les interprétations distinguent clairement la carte active, sa planète de séquence et son emplacement dans le tableau ;
- les échanges sont formulés ensemble : la carte active occupe et déplace une carte, tandis qu’une autre occupe sa place d’origine ;
- la légende d’échange de chaque tableau suit maintenant la carte réellement active de son cycle et non systématiquement la carte de naissance.

## Interface V1.1.7

- les vues **Interprétation** disposent maintenant d’une synthèse immédiate, d’un mode d’expression détaillé et d’un contexte planétaire explicite ;
- les cartes propriétaire et de soutien sont affichées visuellement dans le territoire occupé ;
- l’onglet **Lecture globale** développe le fil rouge, la cascade des cycles et les résonances remarquables ;
- un clic sur une carte de la lecture globale ouvre son cycle avec un bouton de retour ;
- les panneaux d’interprétation se parcourent à la roulette et proposent un détail repliable **Pourquoi cette lecture ?**.

## Interface V1.1.6

- Chaque cycle possède maintenant une troisième vue Interprétation, en plus
  de Tableau et Résultat.
- La carte active, ses deux vécus, sa planète de séquence, son territoire, son
  contexte planétaire, son Défi et son Résultat y sont présentés localement.
- Un nouvel onglet Lecture globale rassemble l’horloge interprétative, le fil
  rouge, la cascade des cycles et la direction du chemin de vie.
- Les cartes de cette horloge globale ouvrent directement l’interprétation du
  cycle correspondant.
- Les vues sont alimentées par le même dossier JSON versionné que le futur LLM.

## Interface V1.1.5

- L’heure analysée est initialisée avec l’heure actuelle de l’ordinateur et ne
  dépend plus jamais de l’heure de naissance.
- Une date ou une heure complètement saisie place automatiquement le focus sur
  le champ suivant. La sélection d’une ville de naissance conduit ensuite à la
  date analysée, et la dernière heure place le focus sur Calculer.

## Fonctionnalités ajoutées en V1.1.4

- Les cinq groupes du bandeau profil partagent maintenant une même structure
  verticale centrée, avec des titres et des valeurs parfaitement alignés.
- Le pied de page conserve l’état du calcul à gauche et affiche désormais
  `Olney Engine — développé par Sébastien` à droite.

## Fonctionnalités ajoutées en V1.1.3

- L’application démarre désormais directement en mode sombre ; le bouton en
  haut à droite permet toujours de revenir au mode clair.
- Un clic initial dans un champ sélectionne automatiquement tout son contenu,
  ce qui permet de remplacer immédiatement une date, une heure ou une ville.
  Les clics suivants conservent le placement normal du curseur.
- Le bouton `↺` adopte un style compact et reste séparé du champ Ville sans
  modifier l’alignement vertical des formulaires.

## Fonctionnalités ajoutées en V1.1.2

- Le bouton `↺` ne modifie plus la hauteur de la ligne des libellés : les
  champs Naissance et Analyse sont parfaitement alignés.
- Ce bouton remet désormais la date et l’heure analysées sur le moment actuel,
  sans modifier les informations de naissance ni le lieu analysé.

## Fonctionnalités ajoutées en V1.1.1

- Les champs de date et d’heure ajoutent automatiquement `/` et `:` pendant
  la saisie, y compris lors d’un remplacement ou d’un collage.
- La carte de l’heure possède maintenant ses propres flèches précédente et
  suivante. Elles déplacent l’heure analysée d’une heure et changent aussi la
  date analysée en cas de passage à minuit.
- Le bouton `↺` du bloc Naissance replace l’analyse sur la date, l’heure et la
  ville de naissance, puis rétablit la synchronisation initiale.
- Les champs Heure et Ville de naissance sont plus compacts afin de donner
  davantage de largeur au bandeau profil en mode fenêtré.

## Fonctionnalités ajoutées en V1.1.0

- Une cinquième carte, `Carte de l’heure`, complète l’horloge. Elle dépend du
  jour, de l’heure et du lieu analysés et ne renvoie à aucun des 90 tableaux.
- Le calcul reste entièrement local : fuseau historique, heure d’été/hiver,
  correction de longitude et équation du temps sont appliqués sans API ni
  dépendance au site de référence.
- La grille imprimée de 52 × 24 cases est représentée par sa séquence circulaire
  source de 52 cartes. Le moteur restitue exactement chaque ligne et chaque
  colonne sans recopier 1 248 valeurs redondantes.
- Le bloc Analyse comporte désormais un champ Heure compact et un bouton de
  localisation. Celui-ci ouvre un sélecteur de ville hors ligne sans alourdir
  l’écran principal.
- L’heure et le lieu analysés sont initialisés depuis la naissance, puis restent
  indépendants dès que l’utilisateur les modifie. Le bouton Calculer ne réécrit
  jamais les informations de naissance et ne peut donc pas altérer l’ascendant.
- Les références validées sont couvertes automatiquement : R♣ pour le
  27/10/1988 à 07:51 à Longjumeau, D♥ pour le 26/08/2026 à 17:51 et 7♥ à 18:32.

## Fonctionnalités conservées de la V1.0.9

- Cinq onglets : Ordre naturel, Chemin de vie, Cycle 7 ans, Cycle annuel
  et Cycle semaine.
- Boutons Tableau et Résultat dans chaque onglet.
- Tableau complet de 52 cartes avec couleurs et légende.
- Une légende d’échange à gauche de chaque tableau montre la carte dont la
  carte personnelle prend la place et celle qui occupe sa position d’origine.
  Le Chemin de vie est comparé à l’Ordre naturel ; tous les cycles suivants
  sont comparés au Chemin de vie.
- L’Ordre naturel, qui sert uniquement de référence initiale, n’affiche pas de
  bloc d’échange inutile.
- Deux séparateurs légers en forme de losange structurent les vues Résultat
  entre la carte Soleil/de naissance et Mercure, puis entre Neptune et Défi.
- Les losanges sont désormais alignés sur le centre visuel des cartes.
- L’ensemble du paquet adopte le nom Olney : dossier, moteur Python, classe,
  lanceur, imports et nom du ZIP.
- Un bouton en haut à droite permet de basculer instantanément entre les modes
  clair et sombre. Les cartes et leurs surbrillances restent contrastées tandis
  que les fonds, panneaux, formulaires, onglets et légendes changent de thème.
- La phrase explicative sous l’échange de place a été retirée pour alléger les
  tableaux. Les vues Résultat sont maintenant centrées dans tout l’espace
  disponible et leur barre de défilement horizontale a été supprimée.
- Le bloc d’échange de place est légèrement remonté afin de rester entièrement
  visible lorsque l’application n’est pas utilisée en plein écran.
- Les paramètres sont désormais organisés dans deux blocs visuels distincts,
  `Naissance` et `Analyse`, avec des champs plus aérés et un bouton Calculer
  mis en valeur. Les libellés sont simplifiés en `Heure` et `Ville`.
- La légende de chaque tableau rappelle désormais les cartes fixes
  (`R♠`, `V♥`, `8♣`) et semi-fixes (`A♣`, `2♥`, `7♦`, `9♥`).
- Les résultats sont présentés comme un tirage horizontal illustré : symbole,
  planète, date ou période et carte. Lune, Soleil, Défi et Résultat sont inclus,
  avec les mêmes couleurs que le tableau complet.
- La fenêtre s'ouvre dans un format intermédiaire adapté à l'écran, jusqu'à
  1360 × 900 pixels.
- Deux onglets précèdent les cycles : `Ordre naturel` (séquence 0, ligne
  interne 90) et `Chemin de vie` (séquence 0.1, ligne interne 1). Après le
  calcul, ils proposent aussi le résultat complet Lune → Résultat.
- Dans les cinq onglets, le bouton `Tableau` précède `Résultat` et constitue
  la vue par défaut. L'Ordre naturel reste donc visible avant la saisie des dates.
- Le badge de profil réunit l'âge, la carte de naissance et le signe
  astrologique. La date de naissance n'y est pas répétée.
- L'ancien résumé est remplacé par une horloge visuelle de quatre cartes :
  chemin de vie, année, 52 jours et carte du jour, avec leurs périodes sous
  chaque carte et sans flèches intermédiaires.
- Les cartes de l'horloge sont des raccourcis vers leurs tableaux : chemin de
  vie vers l'onglet Chemin de vie, année vers Cycle 7 ans, 52 jours vers Cycle annuel et
  jour vers Cycle semaine. Le raccourci sélectionne toujours la vue `Tableau`.
- Le Chemin de vie associe les sept planètes à des tranches de 13 ans :
  0–12, 13–25, 26–38, 39–51, 52–64, 65–77 et 78–90 ans. La carte de la tranche
  active apparaît dans l'horloge et est mise en évidence dans le tableau 0.1.
- La carte Chemin de vie dispose de flèches précédente/suivante. Elles placent
  la date analysée sur le début de la tranche de 13 ans choisie et recalculent
  immédiatement toutes les autres cartes.
- La carte de naissance reste la carte active de l'Ordre naturel.
- Le profil affiche les cartes secondaires lues dans le tableau 0.1 selon le
  ou les maîtres du signe natal. Le Scorpion utilise Mars et Pluton, le Verseau
  Saturne et Uranus, et les Poissons Jupiter et Neptune ; les autres signes ont
  un seul maître.
- Les cartes secondaires sont placées entre la carte de naissance et le signe
  astrologique. Elles sont affichées seules, sans symbole planétaire dessous.
- Deux champs permettent de saisir l'heure (`HH:MM`) et la ville de naissance.
  L'ascendant tropical est calculé hors ligne à partir des coordonnées du lieu,
  de son fuseau IANA historique, du jour julien et du temps sidéral local.
- La ville peut être précisée sous la forme `Ville, FR` en cas d'homonymie.
  La base GeoNames embarquée contient près de 70 000 villes mondiales et aucun
  renseignement de naissance n'est envoyé sur Internet.
- Le champ heure démarre à `00:00`. Le champ ville propose automatiquement une
  liste déroulante de correspondances après la saisie des premières lettres.
- La liste des villes est désormais un panneau flottant qui ne prend jamais le
  focus pendant la frappe : le curseur reste dans le champ jusqu'à la sélection.
- L'ascendant reste calculé au degré près dans le moteur, mais l'interface
  affiche uniquement son symbole et son signe pour conserver un profil épuré.

## Versionnement

La branche stable commence à `V1.0.1`. Les versions progressent par lots de dix :
`V1.0.1` à `V1.0.9`, puis `V1.1.0` à `V1.1.9`, puis `V1.2.0`, etc.
- L'en-tête de l'application porte désormais le nom Olney Engine et présente
  l'interface de calcul des cycles du Biblaridion.
- Les noms des colonnes planétaires sont placés sous les grilles pour laisser
  la couronne supérieure entièrement dégagée.
- Les vues Résultat n'affichent plus de texte de remplacement lorsqu'une date
  n'existe pas réellement.
- Le bloc de profil affiche le signe astrologique occidental à côté de l'âge.
- Sous chaque carte des vues Résultat, deux symboles planétaires indiquent sa
  ligne et sa colonne dans le tableau réellement utilisé. Les trois cartes
  supérieures utilisent un symbole de couronne à la place de la planète de ligne.
- Le séparateur entre les deux symboles de coordonnées a été supprimé.
- L'horloge propose une navigation précédente/suivante pour l'année, le cycle
  de 52 jours et le jour. Chaque déplacement modifie la date analysée puis
  recalcule l'ensemble afin de conserver un état chronologique cohérent.
- Les dates sont placées sous les cartes, juste au-dessus des boutons de
  navigation. La carte du jour affiche uniquement la date analysée.
- La limite des périodes de 52 jours est traitée comme une borne exclusive :
  le cycle suivant commence le jour affiché comme prochaine date, jamais la veille.
- Les derniers jours du cycle annuel sont rattachés à sa dernière période de
  52 jours jusqu'au véritable départ de l'année suivante. Cela supprime le
  faux chevauchement et la carte répétée au passage de l'anniversaire.
- La navigation annuelle place la date analysée sur l'anniversaire qui ouvre
  le cycle choisi, puis recalcule les cartes de 52 jours et du jour.
- Les ordres de base sont nommés `Tableau 0` et `Tableau 0.1` dans leur grille.
- La saisie d'une date valide déclenche automatiquement un recalcul complet ;
  le bouton Calculer et la touche Entrée restent disponibles.
- Les dates saisies restent la référence : les flèches explorent d'autres
  cycles sans modifier le champ, et Calculer revient toujours à la date saisie.
- Le cycle annuel ouvre et ferme désormais sur les anniversaires calendaires
  exacts. Le premier cycle de 52 jours s'ouvre lui aussi le jour anniversaire.
- Le 31 décembre est reconnu comme la carte Joker. Les cycles ordinaires sont
  désactivés et grisés, tandis que Tableau 0 et Tableau 0.1 restent consultables.
- Une carte située dans la Couronne affiche désormais deux symboles de couronne
  dans les résultats ; aucune planète de colonne ne lui est attribuée.
- La série annuelle boucle après 89 ans : 89 ans utilise Tableau 89,
  90 ans Tableau 0.1, 91 ans Tableau 1, 179 ans Tableau 89 et 180 ans
  Tableau 0.1. Le numéro de
  cycle réel reste disponible séparément de l'identifiant interne du tableau.
- Tableau 0 reste exclusivement l'Ordre naturel et ne fait jamais partie de
  la boucle des séquences annuelles.

## AI tool boundary

Your backend can expose only:

```python
engine.tool_get_state(birth_date, target_date)
engine.tool_compare_dates(birth_date, date_a, date_b)
engine.tool_get_interpretation_context(
    birth_date,
    target_date,
    target_time=None,
    target_place=None,
    profile_history=None,
)
```

The LLM receives the interpretation context as structured JSON. It never
recalculates or guesses cards, dates, tables, positions or planetary axes.
