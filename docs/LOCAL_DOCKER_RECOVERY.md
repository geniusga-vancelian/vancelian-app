# Docker local Arquantix — recovery, sauvegardes, sécurité

Ce document complète `docs/arquantix/LOCAL_ENV_RUNBOOK.md` avec une procédure **recovery** et des **garde-fous** contre la perte de données.

**État du dépôt (bascule namespace)** : la stack **par défaut** est `COMPOSE_PROJECT_NAME=arquantixrecovery` avec `ARQUANTIX_COMPOSE_FILE=docker-compose.arquantix-recovery.yml` (mêmes volumes nommés `arquantix_arquantix-db-data`, etc.). Les cibles `make arquantix-up` et `make arquantix-recovery-up` sont équivalentes. Le namespace historique `arquantix` peut rester **cassé** côté Docker Desktop sans bloquer le travail local.

## Volumes de référence (compose actuel)

| Rôle   | Nom Docker                         |
|--------|-------------------------------------|
| Postgres | `arquantix_arquantix-db-data`   |
| Redis    | `arquantix_arquantix-redis-data` |

Ces noms sont **figés** dans les fichiers compose (principal et recovery). Ils ne dépendent pas du `--project-name` Compose.

## Vérifier la base sans rien modifier

Avec la stack **officielle** up :

```bash
make -f Makefile.arquantix arquantix-doctor
```

Manuellement (service Compose `arquantix-db`) :

```bash
docker compose --project-name "$(grep '^COMPOSE_PROJECT_NAME=' .env.arquantix | head -1 | cut -d= -f2)" \
  --env-file .env.arquantix -f docker-compose.arquantix.yml \
  exec arquantix-db psql -U arquantix -d postgres -c '\l'
```

Remplacer la base par celle de `.env.arquantix` (`DB_NAME`, souvent `arquantix_fresh`) pour lister les tables :

```bash
docker compose --project-name arquantix --env-file .env.arquantix -f docker-compose.arquantix.yml \
  exec arquantix-db psql -U arquantix -d arquantix_fresh -c '\dt'
```

*(Adapter `arquantix` si `COMPOSE_PROJECT_NAME` diffère.)*

## Quand utiliser le mode recovery

Symptômes : `docker compose up` échoue avec `No such container: <id>` alors que les volumes sont sains.

Fichier : `docker-compose.arquantix-recovery.yml` — **sans** `container_name`, volumes **external** pointant vers les mêmes noms nommés, projet Compose distinct (`arquantixrecovery`).

```bash
make -f Makefile.arquantix arquantix-recovery-up
```

Arrêt **sans** suppression des volumes :

```bash
make -f Makefile.arquantix arquantix-recovery-down
```

**Interdit** pour récupérer les données : `docker compose down -v`, `docker volume prune`, `system prune --volumes`.

## Dump logique (sauvegarde)

```bash
bash scripts/backup_db.sh              # auto : officiel si up, sinon recovery si seule la stack recovery tourne
bash scripts/backup_db.sh official    # force le compose principal
bash scripts/backup_db.sh recovery    # force la stack recovery (même volume DB nommé)
```

Sortie : `$HOME/backups/arquantix_<DB_NAME>_*.dump` (format custom `pg_dump -Fc`).

Équivalent Makefile : `make -f Makefile.arquantix arquantix-backup-db` (passe par le script en mode **auto**).

## Restaurer un dump (dangereux si mal ciblé — à faire hors prod critique sans backup)

1. S’assurer que la stack DB est up et que personne n’écrit la base si besoin de fenêtre de maintenance.
2. Restaurer dans une **base existante** ou recréer la base vide **volontairement** (hors scope d’un doc « non destructif » par défaut — demander une revue avant).

Exemple de restauration **vers une base déjà créée** (remplacer les variables) :

```bash
docker compose --project-name arquantix --env-file .env.arquantix -f docker-compose.arquantix.yml \
  exec -T arquantix-db pg_restore -U arquantix -d arquantix_fresh --clean --if-exists < /chemin/vers/fichier.dump
```

`--clean` modifie fortement les objets : **tester sur copie** avant.

## Outils SAFE

| Script | Rôle |
|--------|------|
| `scripts/docker_safe_cleanup.sh` | Par défaut : **liste seule** (aucune suppression). Prune réel : `bash scripts/docker_safe_cleanup.sh --force` — **pas** les volumes |
| `scripts/docker_volume_audit.sh` | Liste / inspecte les volumes `arquantix*` (lecture seule) |

## Règles de sécurité Docker (rappel)

- Ne pas utiliser `make -f Makefile.arquantix arquantix-reset` ni `arquantix-clean` : cibles **désactivées** dans le Makefile (risque `down -v`).
- Ne pas multiplier les `--project-name` ad hoc sans lire le runbook (alignement doctor).
- Après changement de `DB_NAME` / `DATABASE_URL`, recréer les conteneurs qui embarquent l’ancienne env (voir runbook).

## Références

- Runbook général : `docs/arquantix/LOCAL_ENV_RUNBOOK.md`
- Compose principal : `docker-compose.arquantix.yml`
- Compose recovery : `docker-compose.arquantix-recovery.yml`
