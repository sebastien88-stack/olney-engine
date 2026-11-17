# Olney Engine V1.8.9

[English version](README.en.md) · [Contribuer](CONTRIBUTING.md)

<a id="sommaire"></a>
## Sommaire

- [Aux origines d’Olney Engine](#aux-origines-dolney-engine)
- [Télécharger et installer](#installation)
- [Pourquoi Olney Engine ?](#pourquoi)
- [Découvrir les vues de l’application](#découvrir-lapplication)
- [Menus, profils, événements, relations et Emmett](#les-menus-et-les-dossiers-personnels)
- [Sources et références historiques](#references)
- [Biblaridion et Apocalypse de Saint Jean](#biblaridion)
- [Atlas historique](#atlas)
- [Questions fréquentes](#faq)
- [Données locales](#données-locales)
- [Développement et contribution](#développement-et-documentation)
- [Crédits et licence](#crédits-et-licence)

<p align="center">
  <img src="docs/screenshots/OlneyEngineLOGO.png" alt="Logo Olney Engine" width="220">
</p>

## Aux origines d'Olney Engine

À la fin du XIXe siècle, **Olney H. Richmond**, occultiste américain et représentant de l'Ordre des Mages, publie en 1893 *The Mystic Test Book*, un ouvrage consacré à **la cartomancie des anciens Mages**.

Richmond affirme être l'héritier d'une tradition ésotérique millénaire, issue notamment des atlantes. Au cœur de son enseignement se trouve **la Religion des Étoiles**, une conception mystique de l'univers dans laquelle les cycles célestes, les nombres et les 52 cartes à jouer participent d'un même langage symbolique.

<p align="center">
  <img src="docs/screenshots/OrdreMageEtoile.png" alt="L'Étoile des Mages" width="500">
</p>

Selon Richmond, le jeu de cartes constitue un véritable calendrier cosmique, permettant d'explorer les correspondances entre les mouvements des astres et les événements de l'existence.

**Olney Engine propose de redécouvrir ce système à l'ère numérique**, en réunissant les calculs de Richmond, les cycles temporels et l'analyse des événements dans une application interactive.

### Olney Engine

Olney Engine est une application Windows consacrée au système des 52 cartes.
Elle réunit les cartes de naissance, les cycles temporels, une frise interactive,
les événements, les relations et Emmett, un interlocuteur IA qui s’appuie sur
les calculs et les règles du moteur pour accompagner la lecture.

<a id="installation"></a>

**[Télécharger Olney Engine 1.8.9 pour Windows (.exe)](https://github.com/sebastien88-stack/olney-engine/releases/download/v1.8.9/Olney_Engine_Setup_1.8.9.exe)**

[Version portable (.zip)](https://github.com/sebastien88-stack/olney-engine/releases/download/v1.8.9/Olney_Engine_Portable_1.8.9.zip) · [Toutes les versions](https://github.com/sebastien88-stack/olney-engine/releases)

Python n’est pas nécessaire pour utiliser l’application installée. La version
portable doit être entièrement extraite avant de lancer `Olney Engine.exe`.

<a id="pourquoi"></a>
## Pourquoi Olney Engine ?

Pour réunir dans un même outil les calculs des 52 cartes, l’exploration du temps
et la mise en perspective du vécu. Olney permet de passer du tableau détaillé
à une lecture globale, puis d’approfondir une période ou une relation.
Le moteur calcule les cartes et leurs positions ; l’interprétation explore
leurs expressions possibles selon la personne, son contexte et ses choix.
Les contributions communautaires permettent de faire évoluer cet outil,
sous la validation du responsable du projet.

## Découvrir l’application

### Une horloge pour se situer

La date de naissance, l’heure et le lieu servent de point de départ à l’analyse.
L’horloge affiche les cartes actives du chemin de vie, de l’année, des 52 jours,
du jour et de l’heure. Ses flèches permettent d’explorer d’autres périodes ;
la date analysée et les vues se mettent à jour ensemble. Le bouton Aujourd’hui
ramène à la date et à l’heure présentes.

<p align="center">
  <img src="docs/screenshots/accueil-clair.png" alt="Accueil en thème clair avec l’horloge et le tableau de l’ordre naturel" width="960">
</p>

*Le thème clair reprend une palette parchemin. Le bouton soleil/lune permet
de passer au thème sombre, visible dans les captures suivantes.*

### Le chemin de vie et les séquences de cartes

La vue **Résultat** rassemble les cartes d’une séquence, leurs fonctions
planétaires et leurs périodes, avec la Lune, le Soleil, le Défi et le Résultat.
Sur le chemin de vie, les sept étapes de Mercure à Neptune couvrent chacune
treize ans. Un clic sur une carte permet d’approfondir l’étape correspondante.

<p align="center">
  <img src="docs/screenshots/chemin-de-vie.png" alt="Résultat du chemin de vie : cartes, planètes et tranches d’âge" width="960">
</p>

### Comprendre la carte active

La vue **Interprétation** développe l’énergie de la carte consultée : son
essentiel, son élément, sa fonction dans la séquence et son emplacement dans
le tableau. Elle présente des expressions constructives et difficiles ainsi
que différentes formes possibles dans la vie concrète.

<p align="center">
  <img src="docs/screenshots/interpretation.png" alt="Interprétation de la carte active en thème sombre" width="960">
</p>

*Les cartes sont lues comme des énergies que l’on traverse et incarne, dont
les manifestations dépendent de la personne, de son contexte et de ses choix.*

### Lire un cycle dans son ensemble

La **Lecture du cycle** replace chaque étape dans le mouvement de la séquence.
Elle articule les sept cartes, la Lune du cycle, le Défi et le Résultat. Un
bandeau fixe conserve les repères de l’étape consultée pendant le défilement,
en distinguant la date explorée de la période réellement en cours aujourd’hui.

<p align="center">
  <img src="docs/screenshots/lecture-du-cycle.png" alt="Lecture du cycle annuel avec les blocs Lune, Défi et Résultat" width="960">
</p>

### Explorer les tableaux et les échanges de place

Les vues **Tableau** montrent la position des 52 cartes, les axes planétaires,
la Couronne et les cartes fixes ou semi-fixes. La carte active est encadrée ;
le panneau d’échange permet de repérer la carte déplacée et celle qui occupe
sa place d’origine à l’échelle consultée.

<p align="center">
  <img src="docs/screenshots/tableau-semaine.png" alt="Tableau de la semaine et panneau des échanges de place" width="960">
</p>

### Parcourir la frise chronologique

La frise superpose les cartes du chemin de vie, de l’année, des 52 jours,
du jour et de l’heure. Le zoom révèle progressivement les périodes fines.
La navigation temporelle est synchronisée avec l’horloge ; des repères signalent
notamment les passages en Couronne, les cases doubles et les convergences.

<p align="center">
  <img src="docs/screenshots/frise-chronologique.png" alt="Frise chronologique et couches temporelles superposées" width="960">
</p>

### Relier les différentes échelles

La **Lecture globale** réunit le profil essentiel et les cartes actives pour
faire ressortir le fil rouge du moment, la cascade des cycles et leurs résonances.
Elle permet de passer d’une vue d’ensemble à l’interprétation d’une carte.

<p align="center">
  <img src="docs/screenshots/lecture-globale.png" alt="Lecture globale avec profil essentiel et horloge interprétative" width="960">
</p>

## Les menus et les dossiers personnels

Les menus en haut de l’application donnent accès aux **profils**, aux
**événements**, aux **relations** et à **Emmett**. Les listes récentes permettent
de retrouver rapidement un dossier ; les boutons Retour et Suivant facilitent
la navigation entre les consultations.

### Profils

Enregistrez un prénom, un nom, un type de sujet, une date de naissance, une heure
et un lieu. La page des profils rassemble le signe, l’ascendant, les cartes de
naissance et secondaires, l’horloge d’aujourd’hui et les cartes du chemin de vie,
jusqu’au Défi et au Résultat. Recherche, tri par colonne et favoris facilitent
la consultation. Les noms restent visibles pendant le défilement horizontal.

### Événements

Créez un événement à partir de la date analysée, attribuez-le à un profil et
associez des participants enregistrés ou des personnes mentionnées librement.
Les catégories, dates et notes permettent de retrouver les moments importants.
La grille affiche la configuration des cycles à la date de chaque événement,
pour mettre le vécu et les périodes en perspective.

### Relations

Un dossier de relation rapproche deux profils autour de leur lien : cartes de
naissance et secondaires, carte de la relation, chemin de vie du lien,
correspondances entre les cartes et horloges synchronisées à une date commune.
La lecture distingue les correspondances de fond des activations temporelles.
La date de rencontre reste un événement de l’histoire du lien.

### Emmett, l’interlocuteur d’Olney Engine

Emmett permet de discuter d’un profil, d’un événement, d’une relation ou de la
méthode. Le moteur prépare les cartes, les cycles et les règles utiles ; le
modèle les utilise pour formuler une lecture en langage naturel. Les discussions
sont enregistrées localement et peuvent être reprises. Le panneau Contexte
permet de consulter les données préparées pour le modèle.

Pour commencer : **Emmett → Connexion → OpenRouter ou OpenAI**, puis saisir
une clé API et le modèle souhaité. Sur OpenRouter, utiliser l’identifiant exact
du modèle, ou `openrouter/auto` pour le routage automatique.

La clé reste en mémoire pendant la session. Les messages et le contexte utile
sont transmis au service choisi et, avec OpenRouter, au fournisseur du modèle.
L’utilisation du modèle nécessite une connexion Internet et peut être facturée
par le service. Les calculs et les lectures intégrées restent accessibles sans IA.

<a id="references"></a>
## Sources et références historiques

Quelques repères pour consulter les écrits d’Olney H. Richmond et leur contexte :

| Ouvrage | Repère documentaire |
| --- | --- |
| *Temple Lectures of the Order of the Magi* (1892) | Conférences sur les enseignements de l’Ordre ; [exemplaire numérisé, IAPSOP (PDF)](https://iapsop.com/ssoc/1892__richmond___temple_lectures_of_the_order_of_the_magi.pdf). |
| *The Mystic Test Book; or, The Magic of the Cards* (1893) | Ouvrage central sur les cartes et leurs correspondances ; [exemplaire de 1893, Library of Congress](https://www.loc.gov/resource/gdcmassbookdig.mystictestbook01rich/?st=gallery). |
| *Mystic Test Book Supplement* (1896) | Instructions complémentaires sur les dispositions et les cartes temporelles ; [exemplaire numérisé, IAPSOP (PDF)](https://iapsop.com/ssoc/1896__richmond___mystic_test_book_supplement.pdf). |
| *Religion of the Stars* | Recueil reprenant et augmentant les conférences ; [annonce contemporaine dans *The Progressive Thinker*, 19 juin 1897 (PDF, IAPSOP)](https://iapsop.com/archive/materials/progressive_thinker/progressive_thinker_v16_n395_jun_19_1897.pdf). |

Ces documents témoignent de l’enseignement et des affirmations de Richmond.
Les récits d’origine atlante relèvent de cette tradition ésotérique.
Les éditions, ajouts éditoriaux et ressources modernes peuvent avoir des droits
distincts : ces liens de consultation ne valent pas autorisation de redistribution.
Les conventions propres à l’application et les sources de son corpus sont
identifiées dans [la provenance des interprétations](interpretation/provenance.json).

<a id="biblaridion"></a>
### Biblaridion et Apocalypse de Saint Jean

Dans l’Apocalypse, saint Jean reçoit un livre qui tient la paume de sa main : le petit livre — [*biblaridion*, « petit rouleau »](https://biblehub.com/greek/974.htm) — et les **Sept Tonnerres**, dont les paroles ne doivent pas être écrites,
apparaissent en [Ap 10, 2–10](https://www.aelf.org/bible/Ap/10).
Le rouleau aux **Sept Sceaux** figure en [Ap 5, 1](https://www.aelf.org/bible/Ap/5),
et le **Livre de Vie** notamment en [Ap 20, 12–15](https://www.aelf.org/bible/Ap/20).
Leur rapprochement avec les 52 cartes constitue une lecture ésotérique :
le texte biblique ne présente pas ce système de cartomancie.

<a id="atlas"></a>
## Atlas historique

L’**Atlas historique** est un projet indépendant, en cours de constitution :
une base destinée à rassembler des centaines de personnages et de dates
historiques pour de futures explorations. Les sources, les dates, leur degré de
précision et les droits de réutilisation doivent encore être vérifiés.
L’Atlas n’est pas inclus dans le logiciel téléchargé ni dans les données de ce
dépôt ; son intégration sera traitée séparément. Voir [la politique des données](DATA_POLICY.md).

<a id="faq"></a>
## Questions fréquentes

**Faut-il installer Python ?**

Non pour l’installateur Windows : téléchargez le fichier `.exe` ci-dessus et
suivez l’assistant. La version portable s’extrait entièrement avant lancement.
Python avec Tcl/Tk est nécessaire uniquement pour exécuter les sources.

**L’application est-elle gratuite ?**

Les téléchargements actuels sont proposés gratuitement. L’utilisation d’Emmett
peut entraîner des frais auprès d’OpenAI ou d’OpenRouter, selon le modèle et le
compte utilisés. Les conditions de licence du code et des ressources sont
détaillées dans [LICENSING.md](LICENSING.md).

**Que peut-on utiliser hors ligne ?**

Les calculs, tableaux, frise, lectures intégrées et dossiers locaux fonctionnent
sans connexion Internet. La génération de réponses d’Emmett nécessite Internet.

**Emmett est-il obligatoire ?**

Non. C’est un interlocuteur IA facultatif, connecté dans **Emmett → Connexion**.
Il s’appuie sur le contexte préparé par le moteur ; les calculs restent
accessibles sans clé API. La clé n’est pas enregistrée par l’application.

## Données locales

Les profils, événements, relations et conversations sont conservés dans une
base SQLite locale, créée automatiquement au premier lancement dans
`%LOCALAPPDATA%\Olney Engine\olney_profiles.db`. La base personnelle n’est
incluse ni dans ce dépôt ni dans les fichiers distribués.

## Développement et documentation

Les sources Python et l’installateur Windows sont en **1.8.9**.
Pour lancer les sources, utiliser Python avec Tkinter :

```bash
python app.py
```

- [Construction de l’application Windows](build_tools/README.md)
- [Architecture du backend et préparation des lectures](BACKEND_LECTURE.md)
- [Corpus et règles d’interprétation](interpretation/README.md)
- [Nouveautés de la version 1.8.6](RELEASE_NOTES_1.8.6.md)
- [Nouveautés de la version 1.8.9](RELEASE_NOTES_1.8.9.md)
- [Historique détaillé et documentation des versions précédentes](docs/HISTORY.md)
- [Confidentialité et signalement de problèmes](SECURITY.md)

## Crédits et licence

Développé par Sébastien. Olney Engine explore la cartomancie des anciens mages,
avec des règles et des lectures documentées dans son corpus d’interprétation.

Le code original du projet est proposé sous [GNU GPL v3.0](LICENSE).
Les données et ressources tierces ont des conditions distinctes ; consulter
[le périmètre des licences et les vérifications en attente](LICENSING.md).
Les composants tiers sont documentés dans [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
