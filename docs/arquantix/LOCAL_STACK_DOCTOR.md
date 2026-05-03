# Doctor local — ports et mode web (Lot 1)

Contexte : **[LOCAL_SETUP.md](./LOCAL_SETUP.md)** (référence env locale). Depuis le Lot 4, ce doctor inclut aussi un scan **:3001 / :5433** dans les fichiers `.env` listés.

## Commande

Depuis la **racine du dépôt** :

```bash
make -f Makefile.arquantix local-doctor
```

Équivalent :

```bash
bash scripts/arquantix_local_stack_doctor.sh
```

Lecture seule : aucun arrêt de processus, aucune modification.

## Ce que ça vérifie

- **Ports** lus dans `.env.arquantix` (défauts : web **3000**, API **8000**, Postgres **5443**).
- **Conteneurs** `arquantix-web` et `arquantix-api` (projet Compose défini dans `.env.arquantix`).
- **Conflit de mode web** : écoute sur le port web + présence du conteneur `arquantix-web` + détection d’un `next dev` / `next-server` sur l’hôte.
- **TCP** sur le port Postgres hôte et **pg_isready** dans le conteneur `arquantix-db` si présent.
- **HTTP** : `GET /health` (API), `GET /` (web).
- **Présence** des fichiers d’env typiques (sans afficher de secrets).

## Règle métier rappelée

Un seul service doit répondre sur le port **web** (souvent **3000**) :

- soit **Next dans Docker** (`arquantix-web`),
- soit **`npm run dev`** sur l’hôte,

pas les deux en compétition sur le même port.

## Flutter / iPhone

- **Simulateur** : `API_BASE_URL` vers le BFF Next sur **3000** (souvent `http://127.0.0.1:3000` sur iOS).
- **Appareil physique** : utiliser l’**IP LAN du Mac** (`http://<IP>:3000`), pas `localhost` — voir `services/arquantix/mobile/run-ios-device.sh`.
- L’auth FastAPI est en général sur le **même hôte, port 8000** (`AUTH_API_BASE_URL` ou défaut dans `SecureApiConfig`).

## Voir aussi

- [LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md) — source de vérité `.env.arquantix`, compose recovery.
- `make -f Makefile.arquantix dev-status` — diagnostic rapide alternatif.
