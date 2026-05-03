# Alignement base locale — API (Alembic) vs Web (Prisma)

**Fichiers d’env (vue d’ensemble)** : **[LOCAL_SETUP.md](./LOCAL_SETUP.md)**.

**Objectif** : éviter la confusion « l’API répond mais le CMS / Next plante » quand **la même machine** utilise **plusieurs `DATABASE_URL`** ou une base **déjà remplie par Alembic** sans historique Prisma.

**Ce document ne remplace pas** une revue métier des migrations. Il décrit la **visibilité** et une **procédure prudente**.

---

## Qui lit quoi ?

| Composant | Variable | Où c’est défini en pratique |
|-----------|----------|-----------------------------|
| **API FastAPI** | `DATABASE_URL` ou `DB_*` | `services/arquantix/api/database.py` — env processus ; fichiers `api/.env.local` puis `api/.env` au chargement. Sous Docker : `DATABASE_URL` injectée par Compose (souvent `…@arquantix-db:5432/…`). |
| **Alembic** | Même `DATABASE_URL` que le processus API | Exécuté au démarrage du conteneur API (`alembic upgrade head` avant `uvicorn`). Pas d’URL séparée. |
| **Next / Prisma** | `DATABASE_URL` | `services/arquantix/web/prisma/schema.prisma` ; fichiers typiques : `web/.env.local`, `web/.env`, **`.env` à la racine du dépôt** (chargé par `next.config.js`). Sous Docker : même pattern que l’API via Compose. |

**Pourquoi « API OK » n’implique pas « Web OK »**

- Alembic applique le **schéma Python / SQLAlchemy** (tables métier API).
- Prisma attend le **schéma généré par les migrations Prisma** (dont CMS : `pages`, `page_i18n`, `sections`, etc.).
- Une base peut être **joignable** et **correcte pour l’API** tout en **manquant de tables Prisma** si les migrations SQL Prisma n’ont jamais été appliquées sur **cette** base, ou si le web pointe vers **une autre** base que celle vue par l’API.

---

## Commandes de diagnostic (lecture seule)

Depuis la **racine du dépôt** :

```bash
make -f Makefile.arquantix local-db-doctor
```

Équivalent :

```bash
bash scripts/arquantix_db_visibility_doctor.sh
```

Le script affiche :

- URL **masquée** et **host / port / nom de base** pour l’API (conteneur + fichiers locaux) et pour le web (conteneur + fichiers).
- Une **synthèse de cohérence** (même `DB_NAME` ou non entre API et web).
- La **présence** de tables CMS Prisma dans PostgreSQL (conteneur `arquantix-db`, base `DB_NAME` de `.env.arquantix`).

**Limite** : la vérification des tables interroge la base nommée dans **`.env.arquantix`**. Si votre `DATABASE_URL` du web pointe vers **une autre** base que `DB_NAME`, le doctor l’indique quand les conteneurs exposent des URLs comparables ; sinon, comparer manuellement les URLs affichées.

---

## Procédure honnête : base déjà existante, Alembic déjà passé, Prisma à aligner

### Contexte fréquent

- La base existe (données, tables Alembic).
- `prisma migrate deploy` **échoue** avec une erreur du type **P3005** (« database schema is not empty ») ou équivalent : Prisma refuse de rejouer l’historique sur une base non vide sans baseline explicite.

### Ce qu’il ne faut pas faire à l’aveugle

- **`prisma migrate dev`** sur une base partagée / prod-like sans accord (peut proposer des changements destructifs ou diverger de l’équipe).
- **`prisma db push`** sur une base riche sans comprendre les écarts (peut écraser des contraintes ou masquer un décalage d’historique).
- **`migrate deploy`** répété sans résoudre l’état « non vide + pas d’historique Prisma » : l’échec est **informatif**, pas un bug aléatoire.

### Piste documentée (à valider selon votre politique migrations)

1. **Vérifier** la base réellement utilisée par le web : `local-db-doctor` + `echo` / `printenv` dans le conteneur web si besoin.
2. **Lister** ce qui manque : tables CMS (`page_i18n`, `pages`, …) — le doctor les marque **WARNING** si absentes.
3. **Décider** avec l’équipe :
   - soit **introduire un baseline** Prisma (`prisma migrate resolve` + stratégie d’équipe pour l’historique) ;
   - soit **appliquer les fichiers SQL** des migrations Prisma **dans l’ordre** via `prisma db execute` ou `psql`, puis marquer les migrations comme résolues ;
   - soit utiliser une **base dédiée** au dev front avec `migrate deploy` depuis vide (hors périmètre « une seule base logique » — à documenter explicitement si c’est volontaire).

4. **Ne pas** automatiser ces choix dans un script opaque : les risques dépendent des données présentes.

Les détails exacts (`migrate resolve`, noms de migrations) évoluent avec Prisma ; se référer à la doc Prisma « baselining » et aux fichiers dans `services/arquantix/web/prisma/migrations/`.

---

## Cas cohérent vs incohérent (résumé)

| Situation | Attendu dans `local-db-doctor` |
|-----------|--------------------------------|
| **Cohérent** | Même nom de base API et web (conteneurs ou fichiers). Tables CMS en **OK**. |
| **Incohérent** | Noms de base différents, ou tables CMS en **WARNING** alors que l’API est healthy : risque élevé de « API OK, web KO ». |

---

## Voir aussi

- `docs/arquantix/LOCAL_ENV_RUNBOOK.md` — ports, `DB_NAME`, redémarrage compose après changement d’URL.
