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
  `release\Olney_Engine_Setup_1.8.6.exe` avec Inno Setup.

La clé OpenAI n’est jamais intégrée à la distribution.
