# Phase 5B — Règles de friction adaptatives (pré–moteur de risque)

## Objectif

Réduire le step-up inutile via des règles **déterministes** (pas de score probabiliste), évaluées **après** la politique stricte et **avant** tout moteur de risque avancé.

## Feature flag et configuration

| Variable | Rôle | Défaut |
|----------|------|--------|
| `ADAPTIVE_FRICTION_ENABLED` | Active la couche adaptive | `false` (comportement historique inchangé si non activé) |
| `LOW_RISK_TRANSFER_AMOUNT` | Plafond (EUR) pour un transfert « bas risque » | `100` |
| `LOW_RISK_RECENT_AUTH_SECONDS` | Fenêtre de fraîcheur du dernier step-up pour l’éligibilité adaptive | `900` |

## Règles implémentées

### `wallet_transfer` (niveau policy HIGH)

Après calcul strict, si `require_step_up` est encore requis **et** `require_reauth` est faux :

- **Downgrade** (pas de step-up / pas de biométrie recommandée dans la décision) si **toutes** les conditions suivantes sont vraies :
  - en-tête `X-Transfer-Amount-Eur` présent et montant **strictement inférieur** à `LOW_RISK_TRANSFER_AMOUNT` ;
  - appareil considéré comme fiable (`device_trust_level` ∈ `HIGH`, `TRUSTED`) ;
  - dernier step-up dans `LOW_RISK_RECENT_AUTH_SECONDS` ;
  - `should_require_step_up` (SI / risque session) est **faux** — on ne contourne pas un step-up imposé par l’intelligence de session (ex. score élevé sur action HIGH).

Si le montant n’est pas fourni (pas d’en-tête), la règle « petit montant » ne s’applique pas : comportement strict.

### `view_sensitive_data` (MEDIUM)

Même principe : uniquement si la politique stricte impose encore un step-up **et** pas de réauth complète.

- Downgrade si **toutes** les conditions suivantes sont vraies :
  - `required_auth_level == MEDIUM` ;
  - device fiable ;
  - récence du step-up dans `LOW_RISK_RECENT_AUTH_SECONDS` ;
  - pas de `should_require_step_up` côté SI.

**Note :** avec une fenêtre adaptive (ex. 900 s) plus large que la fenêtre policy (600 s pour `view_sensitive_data`), un accès peut être autorisé sans step-up alors que la seule policy stricte l’aurait refusé — c’est voulu pour la basse friction, sous contrôle opérateur via `LOW_RISK_RECENT_AUTH_SECONDS`.

## Sécurité

- **`require_reauth`** : jamais contourné ; si une réauth complète est requise, l’adaptive ne s’exécute pas.
- **Niveau MEDIUM (policy)** : `view_sensitive_data` est le seul cas générique adaptive ici (downgrade MEDIUM).
- **`wallet_transfer` (HIGH)** : exception produit Phase 5B — downgrade explicite pour petit montant + contexte sûr, **sans** lever le step-up SI quand `should_require_step_up` est vrai.

## UX / intégration client

- Les routes protégées par `require_continuous_auth_for_action("wallet_transfer")` peuvent envoyer **`X-Transfer-Amount-Eur`** (nombre décimal, virgule ou point acceptés) pour activer la règle de montant.
- Codes de raison ajoutés en cas de succès adaptatif : `adaptive_low_friction_transfer`, `adaptive_low_friction_view_sensitive`.

## Cas limites

- Montant absent : pas d’adaptive « petit montant » pour les transferts.
- `SESSION_STEP_UP_ENABLED` + risque session élevé : step-up conservé (pas de downgrade).
- `ADAPTIVE_FRICTION_ENABLED=false` : alignement strict sur l’existant.

## Tests

Fichier : `api/tests/test_phase5b_adaptive_friction.py` (petit montant, gros montant, device non fiable, session périmée, risque SI, vue sensible avec fenêtre adaptive).
