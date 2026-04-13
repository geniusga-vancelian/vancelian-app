# Flux canonique — création compte euro / custody / IBAN (admin & support)

## Modèle

| Concept | Rôle |
|--------|------|
| **`persons`** | Customer métier canonique (`profile_json.collected`, KYC, etc.). |
| **`pe_clients`** | Pivot produit / portefeuille ; FK des `custody_accounts` (`client_id`). |
| **`custody_accounts`** | Compte fiat (IBAN) rattaché au **pe_client**. |
| **`pe_clients.email`** | Optionnel ; l’e-mail métier affiché côté admin provient surtout de `collected.email` lorsqu’il est renseigné. |

## Règle

Toute **nouvelle** création custody côté admin / support doit passer par :

1. **Résolution stricte** `Person` → un seul `pe_client` (`services.custody.identity_resolution`).
2. **`POST /api/admin/custody/accounts/client/canonical`** (recommandé)  
   ou équivalent utilisant le même resolver.

L’ancienne route **`POST /api/admin/custody/accounts/client`** (saisie directe du UUID `pe_client`) reste valide pour compatibilité / scripts avancés.

## API

| Endpoint | Usage |
|----------|--------|
| `POST /api/admin/custody/identity/resolve` | Prévisualiser `person_id`, `pe_client_id`, e-mails, téléphone, sans créer de compte. |
| `POST /api/admin/custody/accounts/client/canonical` | Création avec **exactement un** des champs : `person_id`, `phone_e164`, `pe_client_id`. |

## Résolution téléphone

- `admin_users.mobile_e164` (indexé, identifiant OTP).
- `profile_json.collected.phone_e164` / `phone`.

**Refus** si 0 personne ou **plus d’une** personne pour le même numéro.

## Scripts

| Script | Comportement |
|--------|----------------|
| `scripts/ensure_modulr_eur_client_by_phone.py` | Par défaut : **résolution stricte** uniquement. `--create-missing` : création synthétique (sandbox). |
| `scripts/ensure_modulr_eur_geant_vert.py` | Sans `--create-missing` : **échec** si client introuvable. |

## Diagnostic e-mail

- **Business email** : `profile_json.collected` lorsque présent.
- **PE / technical login** : `pe_clients.email` si renseigné (souvent absent pour les comptes mobile sans e-mail produit).

## Logs

La création canonique émet un log `custody_canonical_client_account` avec `person_id`, `pe_client_id`, `resolution_source`, `pe_client_email`, etc.
