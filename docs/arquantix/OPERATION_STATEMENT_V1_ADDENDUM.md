# Addendum V1 — relevé d’opération (PDF & snapshot futurs)

Décisions figées pour éviter la dérive d’implémentation avant PR3+. Court et normatif.

## 1. Taxonomie `operation_type` (V1)

Valeurs canoniques alignées sur le domaine actuel :

| `operation_type` | Origine |
|------------------|---------|
| `deposit` | `CustodyTransaction.transaction_type` |
| `withdrawal` | idem |
| `transfer_internal` | idem |
| `exchange_buy` | `transaction_kind` / flux exchange |
| `exchange_sell` | idem |

La granularité bancaire (`bank_transfer_in`, `bank_transfer_out`, `internal_transfer`) reste portée par `transaction_kind` (custody) et alimente libellés / sous-titres, **sans** créer d’autres valeurs `operation_type` en V1.

## 2. Taxonomie `status` autorisée pour le PDF (V1)

- **Seul** `completed` autorise l’émission d’un PDF « opération » conforme en V1.
- Les autres statuts (`pending`, `processing`, `failed`, `reversed`) **ne** produisent **pas** de PDF ; l’API renvoie une erreur explicite (voir §5), pas un document partiel.

## 3. Règles `title` / `subtitle` (affichage document / écran)

- **`title`** : `TRANSACTION_KIND_TITLE_MAP[kind]` si `transaction_kind` est renseigné, sinon `TRANSACTION_TITLE_MAP[transaction_type]`, sinon libellé titre à partir de `transaction_type` (espaces, casse).
- **`subtitle`** (V1) : optionnel ; pour les flux banque, première info utile parmi `remitter_name`, `narrative` (métadonnées) ; pour exchange, ligne courte montant + devise cohérente avec le sens (achat : montant fiat, vente : quantité crypto + actif). Si rien d’utile : sous-titre absent.

## 4. Montant principal affiché (PDF ultérieur)

- **Custody** : montant absolu de l’opération dans `currency` du compte / transaction, signe porté par `direction` (crédit / débit).
- **Exchange — spot fiat↔crypto — achat** : montant fiat principal (`amount_fiat` + devise compte).
- **Exchange — spot fiat↔crypto — vente** : quantité crypto exécutée (`amount_crypto` + `asset`).
- **Exchange — swap crypto↔crypto** (détection : `from_asset` et `to_asset` renseignés, `from_asset` ≠ devise de cotation) : le montant principal documentaire est l’actif **reçu** : `amount_to` + `to_asset`. Les deux jambes figurent dans `asset_impacts`. Si `amount_to` ou `to_asset` manque : **pas de PDF** (erreur métier explicite, pas de semi-support).

## 5. Politique `pending` / `failed` / `reversed`

- **Pas de PDF** en V1 ; réponse HTTP **404** avec code machine `operation_statement_not_completed` ou `operation_statement_not_eligible` selon le cas (support / QA), message métier clair en français.
- **`reversed`** : même principe — pas de relevé de confirmation sur une opération annulée ; erreur explicite, pas de contournement par un PDF « brouillon ».

## 6. Contenu minimal obligatoire de `metadata_snapshot` (V1, PR5)

Champs requis pour une régénération déterministe ultérieure :

- `source_system` (`custody` \| `exchange`)
- `source_id` (UUID de l’entité source)
- `operation_type`, `status`
- `direction`, `amount`, `currency`
- `booking_date` (date comptable ISO ou date UTC dérivée de `created_at` selon règle custody actuelle)
- `transaction_kind` (nullable)
- `client_visible_title` (chaîne déjà résolue pour l’UI, comme `title` API)

Hash et migration Alembic : hors scope PR1–PR2.

---

## Codes erreur HTTP — `GET .../operation-statement.pdf`

Réponses **404** sauf mention contraire. L’en-tête **`X-Vancelian-Error-Code`** reprend le code machine (stable pour support / QA).

| Code | Signification |
|------|----------------|
| `operation_statement_not_found` | UUID inconnu pour ce client, ou accès interdit (même réponse qu’introuvable). |
| `operation_statement_not_completed` | Opération / ordre non `completed` (custody ou Exchange). |
| `operation_statement_balance_chain_unavailable` | Custody : impossible de reconstruire la chaîne de solde pour cette opération. |
| `operation_statement_swap_incomplete` | Exchange : ordre swap sans données suffisantes (`amount_to` / `to_asset`). |

*(L’ancien code `operation_statement_exchange_not_supported` n’est plus émis : la même route sert custody et Exchange.)*

Les clients JSON du détail transaction (`GET /transactions/{id}`) doivent **ignorer** les champs optionnels inconnus : `source_system` et `source_id` sont additive-only (PR2).

---

## Notes d’implémentation (revue PR3 / PR4)

### CSS `@import iban_statement.css` (PR3)

- Mutualisation **provisoire** de style : le gabarit HTML `operation_statement.html` reste **autonome** ; seules les règles visuelles sont partagées.
- Une future extraction vers un `statement_common.css` pourra se faire sans toucher au contrat `OperationStatementPayload`.

### Champ `custody_pdf` (PR3)

- Projection **spécifique custody** (IBAN + lignes type relevé bancaire). Ne pas y ajouter d’autres familles.
- Exchange (PR4) : pas de `exchange_pdf` ; les flux passent par `asset_impacts` et méta génériques (`person`, `execution_detail_rows`, `fees`, `references`).

### PR4 — Exchange sur le même pipeline

- PDF unitaire **custody ou Exchange** via `GET .../operation-statement.pdf` et `OperationStatementPayload`.
- Exchange : `balance_context.applicable = false`, bloc soldes bancaire masqué (`hide_balance_summary`), tableau **Détail des flux** alimenté par `asset_impacts`.
- Statut PDF : `completed` uniquement ; sinon erreur `operation_statement_not_completed`.
- **Frais** : affichage minimal cohérent en V1 ; le **raffinement** du formatage (fiat vs crypto, alignement avec les places de marché) est une **amélioration post-PR4** si besoin.

### Gabarit `operation_statement.html`

- La logique métier reste dans les adapters Python et le mapper ; le template ne fait qu’afficher des structures déjà résolues (`layout.mode`, `execution_detail_rows`, `asset_impact_rows`, …).
- Les branches `custody` / `exchange` évitent toute dépendance croisée (pas de champ IBAN requis côté Exchange).
