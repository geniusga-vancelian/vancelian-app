# PR 0 — Rapport forensic : `sign_failed:privy.rpc_failed` (signature déléguée serveur)

| Champ | Valeur |
| --- | --- |
| **Statut** | 🔬 Forensic livré + ✅ PR 0.1 observabilité implémentée (logging-only, aucun changement de comportement) |
| **Date** | 2026-06-13 |
| **Périmètre** | Audit seul. Aucun changement de flux d'exécution, lock, retry, settlement, legacy, ni activation serveur. |
| **Déclencheur** | Prérequis bloquant avant PR 2/3/4 : la signature déléguée Privy (socle de la queue autoritaire) échoue en prod. |
| **Sources** | Code (`server_execution.py`, `delegated_signer.py`, `privy_api_client.py`), CloudWatch `/ecs/arquantix-api`, DB prod (read-only ECS). |

---

## 1. Executive Summary

- **Candidat root cause (confiance élevée)** : la **signature déléguée serveur (Privy session signer)** est défaillante **bout-en-bout** pour le wallet pilote. L'API Privy `POST /v1/wallets/{id}/rpc` (eth_sendTransaction sponsorisé) répond par une **erreur HTTP** → branche `privy.rpc_failed` (`delegated_signer.py:229-239`). Ce n'est **pas** un problème de route LI.FI / chain / allowance / calldata.
- **Preuve discriminante** : sur le **même wallet** et les **mêmes contrats**, le **chemin client réussit** (swap `64c029ad` → `CONFIRMED` on-chain) alors que le **chemin serveur délégué échoue à 100 %** (0 succès / 8 tentatives). Le delta est donc strictement le **mécanisme de signature déléguée** (clé d'autorisation / key-quorum / politique de sponsorship serveur), pas la transaction elle-même.
- **Systémique ou isolé** : **structurel** (déterministe, 100 % d'échec) mais **circonscrit à un seul wallet/personne** — le seul allowlisté pour l'exécution serveur (`8b0e0044…`, wallet `0x7ae6…5a44`). On ne peut pas encore affirmer que ça casse pour *tous* les wallets délégués (n=1).
- **Localisation de l'échec** : très probablement la **1ʳᵉ transaction déléguée = l'approval ERC-20** (avant le `mark_broadcasting` du swap), car toutes les tentatives retombent en `awaiting_signature` (jamais `broadcasting`) et tous les swaps requéraient une approval.
- **Lacune bloquante** : le **body exact Privy + HTTP status ne sont PAS logués** (capturés dans `PrivyApiError.message` mais jamais émis). **Impossible de distinguer 401/403 (auth) vs 422/400 (policy/sponsorship) vs 429 (rate limit) avec les données actuelles.**
- **Verdict PR 2/3/4** : **NE PAS DÉMARRER**. Conformément à l'intuition produit : sans **HTTP status + body Privy + confirmation approval-vs-swap**, on risque de durcir le mauvais endroit. La plus petite étape sûre est d'**obtenir le body** (dashboard Privy maintenant, ou fix observabilité minimal puis reproduction).

---

## 2. Timeline

### 2.1 Incident pilote (2026-06-13, UTC) — swap A `c248ef94` / intent `474fb2d0`

| Heure | Événement | Source |
| --- | --- | --- |
| 07:25:29 | swap A créé (USDC→CBBTC, 2 USDC), quote `fly` | DB audit |
| 07:26:00.967 | `POST /api/swaps/confirm-execute` → 200 | CloudWatch |
| 07:26:06.766 | `server_swap.sign_failed` (1 ligne, **sans body/status**) | CloudWatch |
| 07:26:06.850 | `server_swap.fallback_awaiting_signature reason=sign_failed:privy.rpc_failed` | CloudWatch |
| 07:26:07.165 | `POST /api/swaps/c248ef94/server-execute` → **200** (renvoie le fallback) | CloudWatch |
| 07:26:07.371 | `POST /confirm-execute` (swap B) → **409 Conflict** (lock global) | CloudWatch |
| 07:26:10.060 | `POST /swaps/6cd6996a/failure` → 200 (B FAILED) | CloudWatch |
| 07:26:16.351 | `POST /swaps/c248ef94/approval` → 200 (approval **client**, fallback) | CloudWatch |
| 07:26:17.073 | `POST /swaps/c248ef94/failure` → 200 (A FAILED, race approval→swap) | CloudWatch |

> Aucun `Traceback` ni body Privy n'apparaît à 07:26:06 : l'exception est capturée et seul le warning une ligne est émis.

### 2.2 Récurrence (CloudWatch, 30 j) — **déterministe**

`server_swap.sign_failed` ×8 · `fallback_awaiting_signature reason=sign_failed:privy.rpc_failed` ×7 · **0 succès serveur**. Tous regroupés **2026-06-12 (×6) et 2026-06-13 (×1)** — soit juste après l'activation de l'exécution serveur.

---

## 3. Evidence

### 3.1 Code — où naît l'erreur

```233:239:services/arquantix/api/services/privy_wallet/delegated_signer.py
        raise PrivyApiError(
            "privy.rpc_failed",
            f"Appel RPC Privy échoué (HTTP {exc.code}){': ' + detail if detail else ''}.",
            http_status=exc.code,
        ) from exc
```

- `privy.rpc_failed` = **branche `urllib.error.HTTPError`** uniquement (Privy a répondu un code d'erreur). Un timeout/réseau lèverait `privy.rpc_unreachable` (`delegated_signer.py:240-243`). Donc **Privy a bien reçu la requête authentifiée et l'a rejetée**.
- Le **body** (`detail`, ≤400 c) et le **`http_status`** sont portés par l'exception **mais jamais logués** :

```457:468:services/arquantix/api/services/trade_core/server_execution.py
    except PrivyApiError as exc:
        logger.warning(
            "server_swap.sign_failed", extra={"swap_id": str(swap_id), "code": exc.code}
        )
        ...
        return _fallback(f"sign_failed:{exc.code}")
```

Seul `exc.code` (= `"privy.rpc_failed"`) est tracé ; `exc.http_status` et le message (body) sont **perdus**. Le handler de route `post_swap_server_execute` (`lifi/routes.py:343-376`) ne logue rien non plus.

### 3.2 Déduction approval-vs-swap (par le code)

L'`except PrivyApiError` (L457) enveloppe **deux** appels délégués : l'approval (`server_execution.py:408`) **avant** `mark_broadcasting`, et le swap (`:448`) **après**. Si l'échec touchait le **swap**, le statut serait déjà `BROADCASTING` → retour `"broadcasting"` (L463-467). Or l'incident **retombe en `awaiting_signature`** (`_fallback`, L468) ⇒ l'échec a eu lieu **avant `mark_broadcasting`**, donc sur **l'approval ERC-20**. Tous les swaps de l'échantillon requéraient une approval (`approval_required=true`), cohérent avec « le 1ᵉʳ appel délégué échoue ».

### 3.3 DB — 6 swaps en `sign_failed` (read-only)

| swap_id | from→to | statut final | tx_hash | personne | wallet sign. | note |
| --- | --- | --- | --- | --- | --- | --- |
| `64c029ad` | USDC→AAVE (3) | **CONFIRMED** | `0x9244…e563` | `8b0e0044` | `0x7ae6…5a44` | **server fail → fallback client OK** |
| `c248ef94` | USDC→CBBTC (2) | FAILED | — | `8b0e0044` | idem | incident (race approval→swap) |
| `3f54f1d1` | AAVE→USDC | EXPIRED | — | `8b0e0044` | idem | leg bundle |
| `9a2d8c7e` | AAVE→USDC | EXPIRED | — | `8b0e0044` | idem | leg bundle |
| `9cca8ec7` | AAVE→USDC | EXPIRED | — | `8b0e0044` | idem | leg bundle |
| `e16dc5c7` | AAVE→USDC | EXPIRED | — | `8b0e0044` | idem | leg bundle |

- **1 seule personne, 1 seul wallet signataire** → pas de signal multi-utilisateurs (seul wallet allowlisté serveur).
- **`64c029ad` prouve la dichotomie client OK / serveur KO** sur le même wallet.

### 3.4 Pré-checks de délégation (passés)

`execute_prepared_swap_server_side` bloque **avant** tout envoi si le wallet n'est pas délégué (`server_execution.py:354-375`), via `GET /v1/users/{id}` + flag Privy `delegated` (`privy_api_client.py:97-118`). Atteindre `send_delegated_sponsored_transaction` implique donc **flag `delegated=true`**. ⇒ L'hypothèse « wallet non délégué » est **écartée au niveau du flag** — mais pas l'hypothèse « clé d'autorisation enregistrée ≠ clé utilisée pour signer » ni « signer présent mais non autorisé pour eth_sendTransaction sponsorisé ».

### 3.5 Evidence Privy / on-chain manquante

- **Body Privy / HTTP status / Privy request-id : ABSENTS des logs.** À récupérer via **dashboard Privy** (logs `POST /v1/wallets/{id}/rpc` aux timestamps ci-dessus) — source non-code immédiate.
- Aucune tx déléguée n'a jamais été diffusée (aucun `tx_hash` issu du chemin serveur).

---

## 4. Findings

### F1 — Signature déléguée serveur cassée bout-en-bout (sévérité : **bloquant**)
- **Fichiers** : `services/privy_wallet/delegated_signer.py`, `services/trade_core/server_execution.py`.
- **Evidence** : 0/8 succès serveur ; client OK sur même wallet (`64c029ad`).
- **Impact** : la queue autoritaire (PR 2/3/4) ne peut pas exécuter ; tout swap serveur retombe en client ou échoue.
- **Fix recommandé** : déterminé après obtention du body (voir §5). Probable : ré-enrôlement clé d'autorisation / key-quorum, ou activation policy sponsorship pour txs serveur.

### F2 — Body Privy + HTTP status non observables (sévérité : **bloquant pour le diagnostic**)
- **Fichiers** : `server_execution.py:457-460` (logue `code` seul), `delegated_signer.py:235-239` (porte mais n'émet pas).
- **Impact** : impossible de classer 401/403 vs 400/422 vs 429 → on ne peut pas choisir le bon correctif.
- **Fix recommandé** (minimal, §5) : logguer `http_status` + body **tronqué/rédigé** + `which_tx=approval|swap` + `privy_request_id`.

### F3 — `privy.rpc_failed` agrège HTTP 4xx ET 5xx (sévérité : moyenne)
- **Evidence** : `delegated_signer.py:229-239` mappe tout `HTTPError` vers un code unique.
- **Impact** : un 429 (transient/rate-limit, retry pertinent) est indistinguable d'un 401/403 (structurel, retry inutile) → risque de mauvaise politique de retry en PR 0/2.
- **Fix recommandé** : classification d'erreur par `http_status` (transient vs terminal) — **après** §5, pas maintenant.

### F4 — Orphelins au-delà de l'incident (sévérité : moyenne, déjà couvert par PR 1)
- **Evidence** : `1dbd4410` (SETTLED_NOOP/created), `5fe8ab6a` (QUEUED/created) du 12/06, intents non terminaux liés à swaps terminaux.
- **Impact** : confirme que le problème d'orphelins est antérieur ; le balayage PR 1 (`reconcile_orphaned_lifi_intents`) les répare. **Hors scope du backfill autorisé (2 intents)** — non modifiés.

---

## 5. Required fixes before PR 2/3/4 (minimaux, sûrs)

1. ✅ **PR 0.1 — observabilité minimale (IMPLÉMENTÉE, logging-only)** : log structuré **inline** (visible CloudWatch) de l'échec de signature déléguée, **rédigé, sans secret**. Aucun changement de flux/retry/lock/settlement/activation serveur. Champs : `which_tx` (approval|swap), `swap_id`, `intent_id`, `wallet_id`, `wallet_address`, `chain_id`, `privy_idempotency_key`, `http_status`, `privy_request_id`, `error_code`, `error_message` (rédigé), `body` (rédigé). Fichiers : `privy_api_client.py` (champs `PrivyApiError.request_id/.body` + `redact_privy_text`), `delegated_signer.py` (capture body + `x-privy-request-id`), `server_execution.py` (suivi `which_tx` + log inline dans les deux `except`). Tests : `test_privy_delegated_signer.py`, `test_server_execution_swap.py` (40 verts).
2. **Reproduire 1 tentative contrôlée** (staging ou prod allowlistée) après déploiement, puis trancher via `http_status` :
   - **401/403** → key-quorum / authorization / setup delegated signing.
   - **400/422** → payload ou policy sponsorship.
   - **429** → rate limit (transient).
   - **5xx** → Privy externe.
3. **Ne pas toucher** quote/prepare/sign/broadcast/lock/legacy tant que le `http_status`+body ne sont pas observés.

### 5.1 Requête CloudWatch de validation (après déploiement PR 0.1)

```
fields @timestamp, @message
| filter @message like /server_swap.sign_failed/
| parse @message "which_tx=* swap_id=* intent_id=* wallet_id=* wallet_address=* chain_id=* privy_idempotency_key=* http_status=* privy_request_id=* error_code=* error_message=* body=*" as which_tx, swap_id, intent_id, wallet_id, wallet_address, chain_id, idem, http_status, privy_request_id, error_code, error_message, body
| sort @timestamp desc
| limit 50
```

---

## 6. Observability gaps

| Manque | Où | Quoi logguer (sans secret) |
| --- | --- | --- |
| HTTP status Privy | `server_execution.py:457` | `exc.http_status` |
| Body d'erreur Privy | idem | `str(exc)[:400]` rédigé (pas de PII/clé) |
| approval vs swap | bloc `except` unique | `which_tx=approval\|swap` |
| Privy request-id | `delegated_signer._http_post_json` | en-tête réponse `x-privy-request-id` si présent |
| swap_id sur `sign_failed` | formatter ne sort pas `extra` | inclure `swap_id` inline (comme la ligne fallback) |
| Distinction 4xx/5xx | `delegated_signer:229` | code dérivé (`privy.rpc_http_4xx` / `5xx`) |

---

## 6bis. Reproduction contrôlée (2026-06-13 15:12 UTC) — ROOT CAUSE CONFIRMÉ

Tentative serveur contrôlée sur le wallet pilote (swap `19a00b7f-abb4-4be6-aeca-85ce166479bd`, USDC→CBBTC). Le swap a réussi **via fallback client** ; le chemin serveur a de nouveau échoué, et **PR 0.1 a capturé le body exact** :

```
server_swap.sign_failed which_tx=swap swap_id=19a00b7f… intent_id=c6f081b2…
wallet_id=znnaqrk6hkfsi0f90srxtjyq wallet_address=0x7ae6…5a44 chain_id=8453
privy_idempotency_key=vance-swap:19a00b7f… http_status=401 privy_request_id=None
error_code=privy.rpc_failed
body={"error":"No valid authorization signatures were provided. Your payload may be
malformed or your signing keys may be incorrect or expired.
Docs: https://docs.privy.io/api-reference/authorization-signatures"}
```

- **HTTP 401** = code Privy `zero_correct_authorization_signatures`.
- `which_tx=swap` (allowance déjà posée → pas d'approval) : le 401 frappe la **signature déléguée elle-même**, indépendamment de la transaction.
- Le pré-check `GET /v1/users` (Basic auth) passe → app_id/app_secret valides ; seule la **signature d'autorisation P-256** est rejetée.

### Root cause (confiance élevée) — clé d'idempotence non signée

Spec Privy (RFC 8785, P-256) — champ `headers` du payload signé : **doit inclure `privy-idempotency-key` si la requête contient ce header** (« If the request does not contain an idempotency key, leave this field out of the payload » ⇒ s'il EST présent, il doit y être).

Notre `send_delegated_sponsored_transaction` **envoie** le header `privy-idempotency-key` (`delegated_signer.py:301-302`) mais **`build_authorization_signature_input` ne l'inclut pas** dans le payload signé (`delegated_signer.py:117-132`). Privy recalcule la signature attendue **en l'incluant** → mismatch systématique → 401. Chaque appel serveur portant une clé d'idempotence (`vance-approve:` / `vance-swap:`), **100 % des signatures sont invalides** → explique le **0/8**.

> Le commentaire `delegated_signer.py:282-283` (« la clé d'idempotence n'entre pas dans le payload signé ») est **faux** au regard de la spec Privy actuelle. C'est le bug.

### Fix réel (PR 0.2 — minimal, ciblé, fonctionnel)

Inclure `privy-idempotency-key` dans `headers` de `build_authorization_signature_input` quand il est envoyé (parité header signé ↔ header transmis). `url` sans trailing slash : déjà OK (`…/rpc`). `privy-request-expiry` : optionnel, non envoyé → hors cause.

- Si après PR 0.2 le 401 disparaît → root cause entièrement résolue.
- Si le 401 persiste → sous-cause résiduelle = **clé d'autorisation non enregistrée dans le key-quorum/owner du wallet** (vérification dashboard Privy).

### 6ter. Vérification post-fix (2026-06-13 15:31 UTC) — RÉSOLU ✅

Swap contrôlé `c5f0f17e-b844-4b61-b46e-b05a468e3c75` (2.2 USDC → AAVE, Base), confirmé on-chain (`tx 0x69cc0967…2673f`).

| Marqueur | Avant PR 0.2 (`19a00b7f`) | Après PR 0.2 (`c5f0f17e`) |
|---|---|---|
| `POST /server-execute` | 200 OK | 200 OK |
| `server_swap.sign_failed` (401) | présent | **absent** |
| Fallback client (`client-trace`/`submit`) | présent | **absent** |
| Exécution on-chain | via client | **via serveur** |

→ La signature serveur déléguée Privy **réussit pour la première fois** (0/8 → 1/1). Root cause (`privy-idempotency-key` absent du payload signé → HTTP 401 `zero_correct_authorization_signatures`) **confirmé et résolu**. La clé d'autorisation est donc bien enrôlée (sous-cause résiduelle écartée).

---

## 7. Final verdict

- **Peut-on passer à PR 2/3/4 ?** → **Oui.** PR 0.2 déployée + reproduction verte (signature serveur réussie 1/1, sans fallback client). Le prérequis Privy est levé : la queue autoritaire peut désormais s'appuyer sur une signature serveur fiable.
- **`sign_failed:privy.rpc_failed` transitoire ou structurel ?** → **Structurel** (déterministe, 0/8, client OK sur même wallet) — **HTTP 401 `zero_correct_authorization_signatures`**. Cause précise : `privy-idempotency-key` envoyé mais **absent du payload signé**.
- **Plus petit fix sûr ?** → **PR 0.2** : inclure `privy-idempotency-key` dans le payload signé (`build_authorization_signature_input`), parité header signé ↔ transmis. ~5 lignes + test de parité. Redéployer, reproduire 1 tentative. Si 401 persiste → vérifier l'enrôlement clé/key-quorum côté dashboard Privy.

---

### Annexe — artefacts forensic (read-only)
- `scripts/_gaelitier-privy-signfail-forensic-inline.py` — corrélation DB des 6 swaps.
- `scripts/arquantix-ecs-run-inline.sh` — runner ECS générique read-only.
- Requêtes CloudWatch Insights (log group `/ecs/arquantix-api`) :
  - Fréquence : `filter @message like /reason=sign_failed:privy.rpc_failed/`
  - Distribution : `filter @message like /server_swap/ | stats count() as c by @message`
