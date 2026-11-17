# Distribution Windows d’Olney Engine

## Préparer l’environnement de construction

Depuis la racine du dépôt, avec Python 3.12 et Tcl/Tk :

```powershell
python -m venv .buildenv
.\.buildenv\Scripts\python.exe -m pip install PyInstaller==6.22.3
```

Installer séparément Inno Setup pour générer l’installateur. Vérifier ses
conditions d’utilisation en fonction de votre usage. Les scripts recherchent
Inno Setup 6 ou 7 dans leurs emplacements Windows usuels.

```powershell
.\build_tools\build_portable.bat
.\build_tools\build_installer.bat
```

Le binaire doit être reconstruit depuis le tag exact de la version publiée.
Avant toute prochaine publication, résoudre les droits des ressources en attente
dans `LICENSING.md` et conserver toutes les notices Python/Tcl/Tk intégrées.
La préparation communautaire ne reconstruit ni ne publie de nouvelle version.

La distribution ne contient jamais la base personnelle du développeur. Au
premier lancement, `ProfileStore` crée automatiquement une base utilisateur
vierge dans `%LOCALAPPDATA%\Olney Engine\olney_profiles.db` et initialise son
schéma complet.

Les données propres au moteur (`data.json`, `places.json`, `interpretation` et
`tzdata`) sont intégrées à la version autonome.

- `build_portable.bat` produit le dossier autonome `dist\Olney Engine`.
- `build_installer.bat` reconstruit ce dossier puis génère
  `release\Olney_Engine_Setup_<version>.exe` avec Inno Setup.

## Source unique de version

`version.py`, à la racine, contient `APP_VERSION` et en déduit `WINDOWS_VERSION`.
Modifier uniquement `APP_VERSION` pour changer la version applicative :

- l'interface, le moteur et les tests importent cette constante ;
- `OlneyEngine.iss` lit la première ligne de `version.py` pour ses versions et
  le nom de l'installateur : conserver la forme `APP_VERSION = "..."` en tête ;
- `windows_version_info.txt` importe les valeurs de `version.py`, rendu accessible
  par `OlneyEngine.spec`, pour les métadonnées de l'exécutable.

Ne pas recopier une version dans ces fichiers de construction. Vérifier avec
`python -m pytest tests/test_version.py -q`. Les README et notes de publication
restent mis à jour manuellement au moment de publier.

La dernière distribution publiée reste la 1.8.9. La branche `main` contient des
travaux ultérieurs ; ne pas présenter un ancien installateur comme reconstruit
à partir de ces travaux. Une future publication doit associer son tag, ses
sources et ses binaires, sans remplacer silencieusement ceux d'une ancienne version.

Avant construction, exécuter les vérifications documentées dans le README,
y compris `python -m pytest tests -q -m ui` sous Windows avec Tcl/Tk.
Les deux jobs CI valident le projet ; aucun ne produit de distribution.

Les clés OpenAI et OpenRouter ne sont jamais intégrées à la distribution.
