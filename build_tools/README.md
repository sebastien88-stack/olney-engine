# Distribution Windows d’Olney Engine

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
