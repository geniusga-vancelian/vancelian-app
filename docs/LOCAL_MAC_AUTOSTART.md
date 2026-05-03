# macOS — démarrage automatique de la stack Arquantix (recovery)

Objectif : au **login utilisateur**, lancer uniquement la stack Docker officielle locale :

- **Projet Compose** : `arquantixrecovery`
- **Fichier** : `docker-compose.arquantix-recovery.yml`
- **Fichier d’environnement** : `.env.arquantix` à la racine du dépôt

Le script utilisé ne fait **pas** de `down`, **aucun** `prune` de volumes, et **n’utilise jamais** le projet historique `arquantix`.

## Fichiers concernés

| Fichier | Rôle |
|--------|------|
| `scripts/start_arquantix_recovery_boot.sh` | Attente Docker → `compose up -d --remove-orphans` → contrôle `http://127.0.0.1:8000/health` (port lu via `API_PORT` dans `.env.arquantix`) |
| `ops/macos/com.arquantix.autostart.plist` | Modèle **LaunchAgent** (à copier dans `~/Library/LaunchAgents/` après remplacement du chemin du dépôt) |

## Prérequis

- Docker Desktop installé et autorisé à démarrer avec la session (comportement habituel sur Mac).
- `.env.arquantix` avec `COMPOSE_PROJECT_NAME=arquantixrecovery` (le script **refuse** `COMPOSE_PROJECT_NAME=arquantix` ou une autre valeur).
- Le dépôt reste au **même chemin** que celui indiqué dans le plist (sinon mettre à jour le plist).

## Installation du Launch Agent

1. Remplacer `__REPO_ROOT__` par le chemin absolu du dépôt, par exemple :

   ```bash
   REPO="$HOME/dev/vancelian-app"
   sed "s|__REPO_ROOT__|$REPO|g" ops/macos/com.arquantix.autostart.plist > /tmp/com.arquantix.autostart.plist
   ```

2. Copier le plist dans votre répertoire LaunchAgents :

   ```bash
   cp /tmp/com.arquantix.autostart.plist ~/Library/LaunchAgents/com.arquantix.autostart.plist
   chmod 644 ~/Library/LaunchAgents/com.arquantix.autostart.plist
   ```

3. Charger l’agent :

   ```bash
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.arquantix.autostart.plist
   ```

   (Sur certaines versions de macOS, si l’agent était déjà chargé : `launchctl bootout` puis `bootstrap` — voir section Désactivation.)

4. Rendre le script exécutable (une fois) :

   ```bash
   chmod +x scripts/start_arquantix_recovery_boot.sh
   ```

## Désactiver l’autostart

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.arquantix.autostart.plist
mv ~/Library/LaunchAgents/com.arquantix.autostart.plist ~/Library/LaunchAgents/com.arquantix.autostart.plist.disabled
```

## Logs

- Sorties **launchd** : `/tmp/com.arquantix.autostart.stdout.log` et `/tmp/com.arquantix.autostart.stderr.log`
- Logs **Docker** (après démarrage) :  
  `docker compose --project-name arquantixrecovery --env-file .env.arquantix -f docker-compose.arquantix-recovery.yml logs -f`

## Relance manuelle (sans attendre le prochain login)

```bash
cd /chemin/vers/vancelian-app
bash scripts/start_arquantix_recovery_boot.sh
```

Équivalent via Makefile :

```bash
make -f Makefile.arquantix arquantix-recovery-up
```

(le Makefile utilise le même projet / fichier que `.env.arquantix`)

## Vérifier que tout est OK

```bash
docker ps --filter "label=com.docker.compose.project=arquantixrecovery"
curl -sf http://127.0.0.1:8000/health && echo OK
```

Diagnostic repo : `make -f Makefile.arquantix arquantix-doctor`

## Dépannage

- **Docker démarre après le script** : augmenter `ARQUANTIX_BOOT_DOCKER_WAIT_SEC` (défaut 300) ou lancer le script à la main une fois Docker prêt.
- **Health timeout** : `docker compose ... logs arquantix-api --tail 100` ; build initial des images peut être long.
- **Sauter temporairement le health check** (sortie 0 après `up`) :  
  `ARQUANTIX_BOOT_SKIP_HEALTH=1 bash scripts/start_arquantix_recovery_boot.sh`

## Écart avec les autres scripts

- `services/arquantix/scripts/arquantix-boot.sh` : flux **développement** (DB Docker + API/Web sur l’hôte), pas adapté comme équivalent « prod Docker locale ».
- `scripts/start-arquantix.sh` : reprise de session avec nettoyages sur l’hôte et worker — plus large que ce boot Docker-only.
