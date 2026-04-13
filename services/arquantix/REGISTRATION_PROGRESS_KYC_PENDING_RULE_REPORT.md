# Registration progress — règle `kyc_pending`

## État initial

`kyc_pending` était partiellement heuristique (inférences floues sur `persons.kyc_status` sans lien clair avec la fin d’inscription moteur).

## Table de mapping des statuts KYC (référence code)

| `person.kyc_status` (normalisé) | Signification produit | Effet lifecycle |
|-------------------------------|------------------------|-----------------|
| `approved`, `verified` | KYC validé | `kyc_completed = true`, `kyc_pending = false` |
| `rejected`, `failed` | Rejet terminal | `kyc_pending = false` (macro peut rester `kyc_pending` pour affichage « action requise » — voir ci-dessous) |
| Autres (`not_started`, `in_progress`, `pending`, etc.) | Pas encore validé | `kyc_pending` **uniquement si** inscription moteur **terminée** |

Constantes : `_KYC_DONE`, `_KYC_REJECTED` dans `registration_progress.py`.

## Règle canonique retenue

```text
kyc_pending =
  registration_completed   (session registration status == "completed")
  AND NOT kyc_completed    (statut ∉ {approved, verified})
  AND NOT kyc_rejected     (statut ∉ {rejected, failed})
```

- **`registration.registration_completed`** reste le booléen métier (session complétée).
- Le **stade macro** `KYC_PENDING` s’affiche lorsque `lifecycle.kyc_pending` est vrai, ou lorsque la session est complétée et le KYC est **rejeté** (branche dédiée dans `_macro_from_signals` pour garder un seul bucket « KYC » côté admin).

## Stades macro (transition)

Ordre de priorité dans `_macro_from_signals` : `active_client` → `pe_client_linked` → `kyc_completed` → rejet post-inscription → `kyc_pending` (lifecycle) → `registration_in_progress` → `account_secured` → `phone_started`.

- Il n’y a **plus** de valeur macro séparée `registration_completed` : après inscription terminée sans KYC validé, le macro attendu est **`kyc_pending`**.

## Fichiers touchés

- `api/services/customers_admin/registration_progress.py` — `_lifecycle_flags`, `_macro_from_signals`
- `api/services/customers_admin/schemas.py` — enum `RegistrationMacroStage` sans `REGISTRATION_COMPLETED`
- `api/tests/test_customers_admin_registration_progress.py`
- Admin web : retrait du style réservé à l’ancien stage `registration_completed`

## Cas limites

- **KYC approuvé en base sans session `completed`** : macro peut déjà monter à `KYC_COMPLETED` (priorité lifecycle), ce qui reflète une réalité data possible (import / correction admin).

## Recommandations (futur provider KYC)

- Garder `person.kyc_status` comme colonne pivot ; enrichir avec `kyc_provider_ref` / timestamps si besoin, sans changer la règle booléenne `kyc_pending` ci-dessus.
