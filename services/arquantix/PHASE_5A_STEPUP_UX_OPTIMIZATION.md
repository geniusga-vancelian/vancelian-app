# Phase 5A — Optimisation UX step-up (friction maîtrisée)

## Objectif

Enrichir les réponses **401/403** de l’auth continue avec des champs **UX** lisibles (`ux_message`, `ux_tone`, `ux_action_label`, `ux_context`) **sans modifier** les décisions du moteur (`continuous_auth_engine`).

## Fichiers modifiés / ajoutés

| Fichier | Rôle |
|---------|------|
| `api/services/security/continuous_auth_ux.py` | **Nouveau** — priorisation des `reason_codes`, messages courts, tonalité, contexte métier. |
| `api/services/security/session_intelligence_dependencies.py` | Fusion des champs UX dans `_detail_payload` (réponses structurées). |
| `api/tests/test_continuous_auth_ux.py` | **Nouveau** — priorité, messages par contexte, fallback. |
| `mobile/lib/core/sensitive_action_http.dart` | Parse des champs UX ; `displayMessage` préfère `ux_message`. |
| `mobile/test/core/sensitive_action_http_test.dart` | **Nouveau** — parse + fallback. |

## Mécanisme

- **Sécurité** : inchangée (`allow`, `require_step_up`, `require_reauth`, `reason_codes` produits comme avant).
- **HTTP `detail`** : champs additionnels **rétrocompatibles** ; les anciens clients ignorent les clés inconnues.
- **Priorité d’un seul message** si plusieurs raisons :  
  1. `reauth_required`  
  2. `device_not_trusted`  
  3. `recent_auth_required`  
  puis `policy_requires_step_up`, `step_up_required`, `biometric_recommended`.

## `ux_context` (dérivé de `action_key`)

| `action_key` (exemples) | `ux_context` |
|-------------------------|----------------|
| `withdrawal`, `wallet_transfer`, `internal_transfer_low`, `beneficiary_add` | `withdrawal` |
| `security_settings_change`, `api_key_create`, `passcode_reset`, … | `security_change` |
| `view_sensitive_data`, `view_portfolio`, `data_export`, défaut | `data_access` |

## Table de correspondance (principale raison × tonalité)

| Raison prioritaire | `ux_tone` | Exemple de `ux_message` (FR) |
|--------------------|-----------|------------------------------|
| `reauth_required` | `critical` | Session expirée — reconnectez-vous. |
| `device_not_trusted` | `warning` | Nouvel appareil détecté — vérification d’identité. |
| `recent_auth_required` + `withdrawal` | `soft` | Pour votre sécurité, confirmez ce transfert. |
| `recent_auth_required` + `data_access` | `soft` | Confirmez votre identité pour accéder à ces informations. |
| `recent_auth_required` + `security_change` | `soft` | Confirmez votre identité pour modifier ce paramètre sensible. |
| `policy_requires_step_up` / `step_up_required` | `warning` | Formulations contextualisées (retrait / données / sécurité). |
| `biometric_recommended` | `soft` | Vérification code ou biométrie. |
| Raison inconnue | `warning` | Message générique non technique. |

`ux_action_label` : ex. **Se reconnecter** (reauth), **Confirmer** / **Continuer** selon le cas.

## Exemple de `detail` JSON (403 step-up)

```json
{
  "code": "session.step_up_required",
  "message": "Vérification supplémentaire requise (OTP / passkey).",
  "action_key": "view_sensitive_data",
  "reason_codes": ["recent_auth_required", "step_up_required"],
  "next_step": "otp_or_passkey",
  "policy": { ... },
  "ux_message": "Confirmez votre identité pour accéder à ces informations.",
  "ux_tone": "soft",
  "ux_action_label": "Confirmer",
  "ux_context": "data_access"
}
```

## Guidelines Flutter

- Afficher **`displayMessage`** (préfère `ux_message` si présent).
- Adapter le **conteneur** selon `ux_tone` :  
  - `soft` → bottom sheet / dialogue léger  
  - `warning` → modal centrée  
  - `critical` → plein écran ou flux reconnexion  
- Utiliser **`ux_action_label`** pour le CTA principal quand pertinent.

## Intérêt produit

- Moins de jargon (`reason_codes` en liste brute).
- Un **seul** message principal même si plusieurs codes techniques sont présents.
- **Confiance** : formulations orientées sécurité utilisateur, pas audit interne.

## Contraintes respectées

- Aucun changement de politique dans `evaluate_request_security_context`.
- Couche présentation uniquement ; `ready` / décisions inchangées côté moteur.
