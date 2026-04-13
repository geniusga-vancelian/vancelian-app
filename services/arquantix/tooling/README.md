# Vancelian Dev Toolkit (local)

Scripts et notice pour le flux quotidien : sync Flutter vers `~/dev`, clean iOS, API, Web/BFF, Xcode, lancement iPhone en profile/release.

## Fichiers

| Fichier | Description |
|---------|-------------|
| `vancelian_dev_toolkit.sh` | Menu interactif + commandes `fast`, `clean`, `release`, etc. |
| `FLUTTER_DEVICE_SELECTION.md` | Détection iPhone USB / wireless / simulateur — stratégie et limites |
| `migrate_vancelian_to_local_dev.sh` | Copie **sûre** OneDrive → `~/dev/vancelian-app` (rsync, vérif, xattr) |
| `vancelian_dev_toolkit_README.html` | Notice détaillée (ouvrir dans le navigateur) |
| `cursor_prompt_dev_tooling.txt` | Prompt de spec pour Cursor / IA |

## Migration OneDrive → disque local (`~/dev`)

Objectif : travailler hors OneDrive sans rien perdre ni casser Git.

1. **Ne jamais** `mv` le dossier depuis OneDrive : uniquement **copie** puis validation.
2. Lancer depuis ce dossier (chemins par défaut : source OneDrive, cible `~/dev/vancelian-app`) :

```bash
cd services/arquantix/tooling
./migrate_vancelian_to_local_dev.sh all
```

Le flux `all` fait : copie rsync → vérification itemize → `du -sh` (réassurance) → xattrs hors `.git/*` → **`git status`** dans la destination (échec rapide si le repo n’est pas utilisable).

3. Contrôle manuel si besoin : `cd ~/dev/vancelian-app && git status`
4. Ouvrir **Cursor** sur `~/dev/vancelian-app` ; les alias `vapp` / `vmobile` et `fast` pointent automatiquement vers `~/dev` dès qu’un dépôt `.git` y est présent (voir ton `~/.zshrc`).
5. Garder OneDrive comme **backup** jusqu’à ce que tout soit validé ; ne pas supprimer la copie cloud tout de suite.

## Démarrage rapide

```bash
cd services/arquantix/tooling
./vancelian_dev_toolkit.sh
```

Les chemins `mobile/`, `api/`, `web/` sont résolus depuis le dossier parent `services/arquantix/` (pas de chemin absolu OneDrive dans le script).

### `fast` / `clean` / `release` vs page web admin

Ces commandes lancent **Flutter** sur un device (iPhone / simulateur). Elles **ne démarrent pas** Next.js. La page **`/admin/login0`** (vidéo de fond, etc.) est servie par le **site web** : il faut que le stack Docker `arquantix-web` (ou `npm run dev` dans `web/`) tourne, et que la variable **`ADMIN_LOGIN0_BG_VIDEO`** soit définie dans le `.env` à la racine du repo (injectée dans le conteneur par `docker-compose.arquantix.yml`).

## API FastAPI (`api` / option menu)

- Le toolkit lance **`python -m uvicorn`** (pas besoin du binaire `uvicorn` installé globalement dans le `PATH`).
- **Priorité Python** : `api/.venv/bin/python` (ou `python3`), puis `api/venv/bin/python`, sinon `python3` système.
- Si le module `uvicorn` est absent, le script affiche une erreur explicite ; installe les dépendances depuis `api/` (ex. `pip install -r requirements.txt` dans le venv).

## Variables d’environnement (optionnel)

- `DEVICE_ID` — si **exporté**, UDID forcé : le script l’utilise **seulement** s’il apparaît dans `flutter devices` ; sinon menu interactif (sauf `SKIP_AUTO_DEVICE=1`). Pour la **sélection automatique** (USB / wireless / simulateur), **ne pas** exporter `DEVICE_ID` (ou `unset DEVICE_ID`).
- `DEVICE_ID_DEFAULT` — UDID de **tie-break** si plusieurs appareils sont disponibles (défaut dans le script : à adapter à ton iPhone). Ce n’est pas un forçage si l’appareil n’est pas branché.
- `PREFER_WIRELESS=1` / `PREFER_USB=1` — en cas d’ambiguïté entre plusieurs iPhones physiques, privilégier un seau wireless ou USB.
- `SKIP_GIT_PULL=1` — ne pas exécuter `git pull` au lancement du menu ni avant `fast` / `clean` / `release`.
- `SKIP_AUTO_DEVICE=1` — utiliser uniquement `DEVICE_ID` (sans vérifier la liste Flutter) ; `DEVICE_ID` doit être défini.
- `SOURCE_MOBILE`, `SOURCE_API`, `SOURCE_WEB` — surcharger les chemins sources.
- `LOCAL_DEV_ROOT`, `LOCAL_MOBILE` — dossier de copie locale (défaut `~/dev/vancelian-mobile`).

## Cibles Flutter (iPhone / simulateur)

- Détection : `flutter devices --machine` + `flutter devices` (texte) pour les lignes **wireless** + optionnellement `xcrun xcdevice list` pour USB/Wi‑Fi.
- **USB**, **wireless** et **simulateurs iOS** sont classés séparément ; macOS / Chrome / web sont exclus.
- Si aucun device n’est prêt : proposition d’**ouvrir Xcode** (`Runner.xcworkspace`) et rappels (câble, confiance, mode développeur).
- Détail : **`FLUTTER_DEVICE_SELECTION.md`**.

## Git et lancement rapide

- Au **premier affichage du menu**, le script fait un `git pull --ff-only` depuis la racine du dépôt (détection via `git rev-parse`, en général le monorepo `vancelian-app`).
- En ligne de commande : `./vancelian_dev_toolkit.sh pull` (pull seul), `./vancelian_dev_toolkit.sh fast` (pull puis lancement Flutter).
- **Devices** : `DEVICE_ID` exporté et présent → lancement direct sur cet UDID. Sinon → **smart** (auto si un seul iPhone réel, menu si plusieurs, simulateur si aucun physique, aide Xcode si rien).

## Alias zsh (exemple)

Voir la section correspondante dans `vancelian_dev_toolkit_README.html`.
