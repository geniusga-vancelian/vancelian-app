# Registration execution tracking — runbook

## Prérequis

- PostgreSQL avec schéma `public` aligné sur les migrations Alembic du service API.
- Variable `DATABASE_URL` (ou équivalent) pointant vers la base cible.
- Migration **094** appliquée (`registration_execution_events`).

## Migration 094

**Révision Alembic** : `094` — fichier `api/alembic/versions/094_registration_execution_events.py` — enchaîne après **`093`**. Si un environnement est bloqué avant `093`, appliquer d’abord la chaîne manquante (`alembic upgrade head` ou migrations ciblées selon votre politique).

**Prérequis DDL** : la table `public.pe_clients` doit exister (FK `client_id` → `pe_clients`). Si une base isolée n’a pas ce schéma, corriger avant d’appliquer `094` (alignement avec le reste du monolithe API).

---

## Déploiement migration 094 partout (checklist)

Tant que **094** n’est pas appliquée sur une base, les KPIs / timelines registration sur **cette** base ne sont **pas** fiables (événements non persistés ou logs `registration_tracking_failed`). Répéter la séquence **pour chaque** environnement qui sert l’API Arquantix (dev partagé, staging, préprod, prod, replicas d’intégration si base dédiée).

### 1. Avant (par environnement)

- [ ] Identifier le **DSN** / secret utilisé par l’API (même URL que celle du déploiement réel, pas une base locale par erreur).
- [ ] Vérifier la révision actuelle : `python3 -m alembic current` (avec `DATABASE_URL` pointant sur cette base).
- [ ] S’assurer que la cible est au moins à **`093`** (sinon `upgrade head` appliquera la chaîne complète jusqu’à la tête).

### 2. Fenêtre de maintenance

- **DDL** : `CREATE TABLE` + index — généralement **court** et **peu bloquant** sur PostgreSQL récent ; en prod, préférer une fenêtre faible trafic si votre gouvernance l’exige.
- **Pas de downtime obligatoire** côté app : le runtime registration reste tolérant si la table manque encore (SAVEPOINT) ; une fois la table créée, les événements commencent à s’accumuler.

### 3. Appliquer

```bash
cd services/arquantix/api
export DATABASE_URL='postgresql://...'   # ou .env chargé par votre outil
python3 -m alembic upgrade head
```

Équivalents selon votre ops : job ECS/Kubernetes one-shot, pipeline « migrate » avant redémarrage des tâches, bastion + venv, etc. — **même commande**, même répertoire `api`, même code versionné que le déploiement.

### 4. Après (validation obligatoire)

```bash
python3 -m alembic current
# Attendu : révision en tête de branche incluant 094 (souvent affichée comme 094 ou head)
```

```sql
SELECT version_num FROM alembic_version;  -- doit refléter la tête après upgrade
SELECT to_regclass('public.registration_execution_events') IS NOT NULL AS table_ok;
\d public.registration_execution_events
```

- [ ] Table présente, index créés (cf. section suivante).
- [ ] Smoke API : `GET /api/admin/registration/sessions/summary-stats` retourne 200 (sans erreur DB).
- [ ] Optionnel : démarrer une session test, vérifier qu’une ligne apparaît dans `registration_execution_events`.

### 5. Suivi « tous environnements »

Tenir une **liste nominative** (ex. tableau interne) : `local-dev | staging | preprod | prod` avec date/heure, opérateur, et résultat `alembic current` + `table_ok`. Ne **pas** considérer la fonctionnalité « production-grade » tant qu’une ligne du tableau reste non cochée pour la prod.

### 6. Rollback (exceptionnel)

Le fichier `094_*.py` définit un `downgrade()` qui supprime la table. **À utiliser seulement** si décision produit/DBA ; les lignes d’audit seront perdues. En pratique, préférer corriger l’avant plutôt que downgrade en prod.

---

### Commande unique (référence)

```bash
cd services/arquantix/api
python3 -m alembic upgrade head
```

Vérifier que la révision courante inclut **`094`** (et que `registration_execution_events` existe).

## Vérification table / index

```sql
SELECT to_regclass('public.registration_execution_events');
SELECT indexname FROM pg_indexes WHERE tablename = 'registration_execution_events';
```

Index attendus (noms pouvant varier selon migration) : `session_id`, `flow_id`, `created_at`, `event_type`, `person_id`, `client_id`.

## Best-effort (runtime)

- Tous les inserts passent par `safe_log_registration_event` dans `execution_events.py`, à l’intérieur d’un **`db.begin_nested()`** (SAVEPOINT).
- En cas d’échec d’insert : rollback **du seul savepoint**, log `registration_tracking_failed`, **aucune exception** vers le code métier registration.
- Le lot d’audit des règles (`_emit_rule_evaluation_batch`) est enveloppé dans un `try/except` : une erreur de collecte n’interrompt pas le flux.

## Vérification API (read-only admin)

```http
GET /api/admin/registration/sessions?limit=5
GET /api/admin/registration/sessions/{uuid}
GET /api/admin/registration/sessions/{uuid}/execution-events
GET /api/admin/registration/sessions/{uuid}/replay
GET /api/admin/registration/sessions/summary-stats
```

Réponses JSON uniquement ; pas d’effet de bord sur les flows ou le publish.

## Vérification UI admin

- Liste : `/admin/registration/sessions`
- Détail : `/admin/registration/sessions/[id]`
- Depuis la page flows : bouton « Sessions (audit) »

## Logs

Rechercher :

- `registration_tracking_failed` — échec d’écriture d’un événement (table absente, contrainte, etc.).
- `registration_rule_audit_batch_failed` — échec du batch d’évaluation de règles (ne bloque pas le runtime).

## Table tracking absente ou cassée

1. Le **runtime Flutter** continue de fonctionner si les SAVEPOINTs fonctionnent : les erreurs d’insert sont avalées.
2. Restaurer la table via `alembic upgrade head` ou script DBA équivalent.
3. Vérifier les FKs : `registration_sessions`, `registration_flows`, `persons`, `pe_clients` (selon environnement).

## Confirmer que le runtime survit à un échec tracking

1. Sur un environnement de test, simuler une erreur (ex. renommer temporairement la table, exécuter `start` + `submit`).
2. Observer des `registration_tracking_failed` dans les logs.
3. Vérifier que la session est créée et que `GET /api/registration/sessions/{id}/screen` répond sans `PendingRollbackError`.

## Contrat Flutter

Aucun changement sur les endpoints `/api/registration/*` existants (schémas de réponse inchangés). Le tracking est **strictement additif** côté base et logs.
