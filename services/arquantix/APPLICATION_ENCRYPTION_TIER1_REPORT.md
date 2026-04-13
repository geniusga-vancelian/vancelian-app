# Rapport — chiffrement applicatif Tier 1 (niveau institutionnel, itération 1)

## Objectif

Protéger les données sensibles au repos **même en cas de fuite DB** grâce au chiffrement **AES-256-GCM** (IV aléatoire par valeur), à une **gestion de clés** séparée (KMS ou clé locale), et à un **contrôle d’accès au déchiffrement** avec audit.

## Classification (documentation)

| Niveau | Exemples de champs |
|--------|--------------------|
| **HIGH_SENSITIVE** | email, téléphone, KYC, adresse |
| **MEDIUM** | métadonnées, fragments de profil |

Implémentation : `api/services/security/data_classification.py` (constantes pour extensions futures ; même DEK Tier 1).

## Composants

| Fichier | Rôle |
|---------|------|
| `api/services/security/crypto_service.py` | `encrypt` / `decrypt`, format `v1:`, cache de clé, masquage (`mask_email`, …) |
| `api/services/security/crypto_access.py` | Autorisations par `purpose` + `operation_id`, audit `crypto.decrypt_ok`, `decryption_context` |
| `api/services/security/encrypted_sqlalchemy.py` | TypeDecorator `EncryptedField` (écriture auto ; lecture strict avec contexte) |
| `api/services/security/contact_submissions_crypto.py` | Pilote **contact_submissions** (double écriture) |

## Format ciphertext

- Préfixe `v1:` + base64(**12 octets IV** || **ciphertext + tag GCM**).
- Chaîne vide → pas de blob ; `None` reste `None`.

## Gestion des clés

| Mode | Variables |
|------|-----------|
| **Local (dev / tests)** | `CRYPTO_LOCAL_MASTER_KEY_B64` — 32 octets (base64 / base64url) |
| **AWS KMS** | `CRYPTO_KMS_ENABLED=true`, `CRYPTO_MASTER_KEY_ID` (ARN ou id), `CRYPTO_WRAPPED_KEY_B64` (blob chiffré par KMS contenant la clé AES 32 octets) |
| **Rotation** | `CRYPTO_LEGACY_MASTER_KEY_B64` — tentative de déchiffrement avec la clé courante puis les legacy |

Le cache mémoire (`get_data_key_chain`) évite des appels KMS répétés ; `invalidate_key_cache()` pour tests / rotation.

## Pilote base de données : `contact_submissions`

Migration **113** : colonnes `name_encrypted`, `email_encrypted`, `message_encrypted` (TEXT, nullable).

- **Feature flag** : `APPLICATION_ENCRYPT_CONTACT_SUBMISSIONS=true` → chiffrement à la création (`POST /public/contact`).
- **Double écriture** : par défaut, plaintext **conservé** en plus des colonnes chiffrées (rollout).
- **Strip** : `APPLICATION_ENCRYPTION_STRIP_CONTACT_PLAINTEXT=true` → champs clairs vidés après chiffrement ; réponse publique masquée.
- **Misconfiguration** : si le flag contact est actif sans clé → **503** `CRYPTO_MISCONFIGURED`.
- **Admin** : `GET /admin/contact-submissions` déchiffre via `contact_row_to_admin_dict` (operation_id `admin_list_contact_submissions`), avec repli sur plaintext si pas encore de ciphertext.

### Backfill

Script : `api/scripts/backfill_contact_submissions_encryption.py`  
Remplit `*_encrypted` pour les lignes existantes (operation_id `migration_backfill_contact`).

## Contrôle d’accès au déchiffrement

- `APPLICATION_CRYPTO_STRICT_DECRYPT` (défaut `true`) : tout `decrypt_value` doit avoir un `operation_id` autorisé pour le `purpose`.
- Purposes enregistrés : `contact_submission_read`, `contact_submission_write` (voir `crypto_access.py`).
- Extension : `register_decrypt_purpose(...)`.

## Journalisation

- Déchiffrement réussi : log **sans valeur en clair** (`ciphertext_len`, `purpose`, `op`).
- Masquage : `mask_email`, `mask_phone`, `mask_freeform` pour les réponses publiques ou logs métier.

## Performance

- **Cache clé** : une seule résolution KMS / lecture env par processus (verrouillage thread-safe).
- **Pas de déchiffrement inutile** : listes admin déchiffrent uniquement lorsque `*_encrypted` est présent et valide `v1:`.

## ORM `EncryptedField`

Pour de **nouveaux** modèles : colonne `TypeDecorator` qui chiffre à l’insert/update. En lecture **stricte**, utiliser :

```python
with decryption_context("admin_list_contact_submissions"):
    rows = session.query(MyModel).all()
```

Sans contexte : retour `None` pour éviter fuite accidentelle (logs d’avertissement).

## Stratégie de rollout

1. Déployer migration **113** + code.
2. Configurer `CRYPTO_*` (ou KMS).
3. Activer `APPLICATION_ENCRYPT_CONTACT_SUBMISSIONS` sur un environnement de test.
4. Exécuter le **backfill** sur les données existantes.
5. Valider l’admin (déchiffrement OK).
6. Optionnel : activer `APPLICATION_ENCRYPTION_STRIP_CONTACT_PLAINTEXT` après période de double lecture.

Étapes suivantes (hors Tier 1) : `pe_clients.email`, `persons.profile_json` (index de recherche **blind** / hash dédié), champs téléphone / adresse dans le moteur d’inscription.

## Tests

```bash
cd api && alembic upgrade head
pytest tests/test_application_encryption_tier1.py -v
```

Couverture : roundtrip, **rotation** (clé legacy), **corruption**, création contact avec flag + colonnes `v1:`.

## Limites connues

- **Recherche / unicité** : un email chiffré seul ne permet pas d’index unique efficace — prévoir `email_lookup_hash` (HMAC ou hash normalisé) avant de chiffrer `pe_clients.email`.
- **KMS** : le script de backfill et l’API doivent avoir les permissions `kms:Decrypt` sur la clé et le bon `KeyId`.
- Tier 1 ne chiffre pas encore l’ensemble du référentiel identité ; le pilote **contact** valide le pipeline.
