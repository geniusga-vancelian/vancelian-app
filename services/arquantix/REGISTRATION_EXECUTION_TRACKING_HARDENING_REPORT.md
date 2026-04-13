# Registration execution tracking — rapport de durcissement (production-grade)

## Executive Summary

La couche **Execution Tracking + Audit Trail + Replay** a été consolidée autour d’un **point d’écriture unique** (`safe_log_registration_event`) avec **SAVEPOINT**, de **payloads normalisés** et **masquage centralisé** des valeurs sensibles dans les événements. Le **replay** est reconstruit **lecture seule** à partir des événements et de l’état ORM (`registration_session_data`, `registration_session_steps`). L’**admin** expose listes, détail, timeline et replay JSON ; l’**UI Next.js** ajoute les pages sessions et détail. Aucun changement au **contrat runtime Flutter** ni au **publish flow** du builder.

## Event Coverage Audit

### Types définis (`RegistrationEventType`)

| Type | Émis aujourd’hui | Remarque |
|------|------------------|----------|
| `registration.flow.version_locked` | Oui | Après `flush` de la session au démarrage |
| `registration.session.started` | Oui | Juste après verrouillage version |
| `registration.session.resumed` | Non | Réservé (pas d’API resume) |
| `registration.session.completed` | Oui | Après projection + `flush` |
| `registration.session.abandoned` | Non | Réservé |
| `registration.screen.entered` | Oui | Premier écran + navigation next/prev |
| `registration.screen.submitted` | Oui | Après persistance des réponses |
| `registration.fields.submitted` | Oui | `field_slugs`, `masked_values`, `screen_key` |
| `registration.validation.failed` | Oui | Champs requis manquants + validateurs écran |
| `registration.navigation.next` / `prev` | Oui | Clés / ids enrichis |
| `registration.step.completed` | Oui | Lors de `_mark_step_completed` |
| `registration.step.skipped` | Non | Réservé |
| `registration.step.blocked` | Oui | Remplace l’ancien `registration.navigation.blocked` |
| `registration.navigation.blocked` | Lecture seule | **Legacy** — encore parsé dans le replay |
| `registration.projection.completed` | Oui | Liste des slugs projetés + `person_id` |
| `registration.rule.evaluated` | Conditionnel | Lot JSON ; si aucune règle de visibilité (step/component), **aucun événement** |
| `registration.runtime.error` | Non | Réservé (pas d’instrumentation router dans cette livraison) |

### Emplacements d’émission

- `services/registration/service.py` — cycle de vie session, submit, navigation, blocage, complétion.
- `services/registration/execution_events.py` — écriture sécurisée + taxonomie + labels UI.

## Event Payload Standards

Contrat documenté en en-tête de `execution_events.py`. Exemples :

- **session.started** : `jurisdiction`, `flow_name`, `flow_version`, `entrypoint_type`
- **screen.entered** : `step_key`, `step_title`, `screen_key`, `screen_title`
- **fields.submitted** : `field_slugs`, `masked_values`, `screen_key`
- **validation.failed** : `screen_key`, `reason`, `errors` (liste `{slug, message}`)
- **projection.completed** / **session.completed** : `person_id`, `projected_fields` (**liste de slugs**), `status` (completed)

## Best-Effort Safety Model

1. **`safe_log_registration_event`** : `try` / `db.begin_nested()` / `flush` ; toute exception → log warning, pas de propagation.
2. **`_emit_rule_evaluation_batch`** : `try/except` global pour garantir qu’aucune erreur de règle ne casse le runtime.
3. Alias public : `emit_registration_execution_event` → délègue à `safe_log_registration_event`.

## Admin API

| Méthode | Chemin | Rôle |
|---------|--------|------|
| GET | `/api/admin/registration/sessions` | Liste paginée + filtres |
| GET | `/api/admin/registration/sessions/summary-stats` | Agrégats légers |
| GET | `/api/admin/registration/sessions/{id}` | Détail + sections dérivées (sans timeline complète dans le corps pour perf) |
| GET | `/api/admin/registration/sessions/{id}/execution-events` | Timeline brute + `label_fr` / `badge_variant` |
| GET | `/api/admin/registration/sessions/{id}/replay` | Replay complet + timeline |

## Admin UI

- `/admin/registration/sessions` — liste, filtres, lien détail.
- `/admin/registration/sessions/[id]` — résumé, étapes, timeline, échecs, règles, snapshot collecté, replay JSON.
- Sidebar : entrée « Reg. sessions ».

## Replay Model

Implémenté dans `services/registration/replay.py` :

- `build_session_replay(session_id, include_timeline=...)`
- Agrégats : `screens_viewed`, compteurs, `duration_seconds`, `validation_failures`, `blocked_events`, `rule_evaluation_batches`, `projection`, `collected_data_snapshot`
- Tolérant aux événements manquants (sessions anciennes ou tracking partiel).

## Masking Policy

Module `services/registration/masking.py` :

- Heuristiques par **slug** (email, téléphone, date de naissance, etc.)
- **`mask_answers_for_audit`** utilisé pour `masked_values` dans `fields.submitted`
- **`mask_context_subset`** pour `resolved_values` dans les lots de règles

Documenté en code ; ne pas dupliquer la logique dans les handlers.

## Deployment Runbook

Voir `REGISTRATION_EXECUTION_TRACKING_RUNBOOK.md`.

## Tests Added

- `tests/test_registration_api.py` : timeline enrichie, replay, liste admin, règle optionnelle, `summary-stats`
- `tests/test_registration_masking.py` : masquage email / slug / answers

## Backward Compatibility Notes

- Runtime `/api/registration/*` : **inchangé** pour le client Flutter.
- Builder admin & publish : **non modifiés** dans cette livraison (seulement nouvelles routes **read-only** sessions).
- Anciennes lignes `registration.navigation.blocked` : toujours interprétées dans le replay.

## Remaining Gaps / Recommended Next Steps

1. **`registration.session.resumed` / `abandoned`** : émettre quand les APIs existent.
2. **`registration.runtime.error`** : optionnellement, corrélation HTTP 500 avec `session_id` si disponible.
3. **Agrégats avancés** (`top validation failures`, `top blocked steps`) : requêtes SQL / matérialisation sur `payload_json` — préparer hors ligne de transaction runtime.
4. **Tests UI** : Playwright ou smoke manuel sur `/admin/registration/sessions`.
5. **Réduction des warnings SQLAlchemy** « nested transaction deassociated » dans les tests (fixture + savepoints multiples) — cosmétique.

## Exemple de replay reconstruit (structure)

```json
{
  "session_id": "...",
  "summary": {
    "screens_viewed_count": 2,
    "submits_count": 1,
    "validation_failures_count": 0,
    "blocked_steps_count": 0,
    "duration_seconds": 12.4,
    "events_total": 15
  },
  "screens_viewed": ["screen1", "screen2"],
  "timeline": [ { "event_type": "registration.session.started", "payload_json": { } } ]
}
```

## Points de vigilance déploiement

- Appliquer la migration **094** avant de s’appuyer sur les KPIs basés sur `registration_execution_events`.
- Environnements sans table : runtime protégé par SAVEPOINT ; admin timeline vide ou erreurs loguées.
