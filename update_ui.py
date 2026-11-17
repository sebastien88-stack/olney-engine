"""User-initiated GitHub release checks; installer download via the browser."""
import json
import queue
import re
import threading
import webbrowser
from tkinter import messagebox
from urllib.request import Request, urlopen

API = 'https://api.github.com/repos/sebastien88-stack/olney-engine/releases/latest'
PREFIX = 'https://github.com/sebastien88-stack/olney-engine/releases/download/'


def version(value):
    if not isinstance(value, str):
        raise ValueError('Version publiée non reconnue.')
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise ValueError('Version publiée non reconnue.')
    return tuple(map(int, match.groups()))


def installer_for_release(data, current):
    """Only accept the exact official installer attached to a stable release."""
    if not isinstance(data, dict):
        raise ValueError('Réponse GitHub non reconnue.')
    if data.get('draft') or data.get('prerelease'):
        raise ValueError('Cette version n’est pas une publication stable.')
    tag = data.get('tag_name')
    if version(tag) <= version(current):
        return None
    expected = 'Olney_Engine_Setup_' + tag.lstrip('v') + '.exe'
    assets = data.get('assets')
    if not isinstance(assets, list):
        raise ValueError('Aucun installateur Windows officiel disponible pour cette version.')
    for asset in assets:
        if (isinstance(asset, dict) and asset.get('name') == expected
                and asset.get('browser_download_url') == PREFIX + tag + '/' + expected):
            return tag, asset['browser_download_url']
    raise ValueError('Aucun installateur Windows officiel disponible pour cette version.')


def check_update(root, current):
    if getattr(root, '_update_check_running', False):
        return
    root._update_check_running = True
    results = queue.Queue()

    def fetch():
        try:
            request = Request(API, headers={'Accept': 'application/vnd.github+json',
                                           'User-Agent': 'Olney-Engine'})
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read())
            results.put((data, None))
        except Exception as error:
            results.put((None, str(error)))

    def poll():
        try:
            data, error = results.get_nowait()
        except queue.Empty:
            root.after(150, poll)
            return
        root._update_check_running = False
        if error:
            messagebox.showerror('Mise à jour', 'Vérification impossible.\n' + error, parent=root)
            return
        try:
            installer = installer_for_release(data, current)
            if installer is None:
                messagebox.showinfo('Mise à jour', 'Aucune version plus récente n’est publiée.', parent=root)
                return
            tag, url = installer
            if messagebox.askyesno('Mise à jour disponible',
                                  f'Olney Engine {tag} est disponible.\n\nTélécharger l’installateur ? '
                                  'Après téléchargement, ferme Olney puis lance-le pour mettre à jour '
                                  'l’installation. Tes données restent dans leur dossier utilisateur.', parent=root):
                webbrowser.open(url)
        except (ValueError, KeyError, TypeError) as error:
            messagebox.showerror('Mise à jour', str(error), parent=root)

    threading.Thread(target=fetch, daemon=True).start()
    root.after(150, poll)
