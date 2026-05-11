# PRD — Conversational Action Layer (Action Agent + Action Widgets)

**Statut :** proposition produit / cadrage technique — Phase 1 non implémentée dans ce fichier.  
**Dernière mise à jour documentaire :** 2026-05-07 (reprise cadrage : distinction Action CTA vs CAL).  

**Alignement codebase actuel :** assistant multi-agents sous  
`services/arquantix/api/services/assistance/` (paquet Python `services.assistance`).  
Les chemins de fichiers suivants sont **relatifs à ce dossier** :

`agents/router.py`, `prompts/router_system.md`, `agents/runtime/agent_loop.py`,
`agents/tools/registry.py`, `schemas.py` (payloads API + embeds stream / non-stream),
`agents/conversation_state.py`, `embed_gate.py`,
traces golden et table `assistance_agent_decisions`, observabilité admin.

---

## Vision

Faire évoluer l’assistant Vancelian d’un **système conversationnel** (comprendre → répondre) vers un
**couche d’action conversationnelle** :

**comprendre → préparer l’action → confirmation explicite → exécution backend contrôlée.**

Le LLM ne remplace pas le noyau transactionnel : il **prépare** des brouillons structurés et des widgets
de confirmation ; l’**exécution** reste côté API, recalculée, revalidée, observable.

Objectif produit : réduire la friction navigation / menus — l’utilisateur **parle**, **confirme**
(dans l’UI native), **agit** — sans baisser le niveau de sécurité ni court-circuiter la conformité.

---

## 1. Objectifs produit

### Exemples de commandes utilisateur

| Domaine | Exemple |
|--------|---------|
| Virement | « Ajoute cet IBAN à mes bénéficiaires et envoie-lui 100 euros. » |
| Achat crypto | « Achète 1000 euros de Bitcoin. » |
| Allocation | « Place 5000 euros sur le coffre flexible. » |
| Portefeuille | « Rééquilibre mon portefeuille. » |
| Carte / sécurité | « Bloque temporairement ma carte. » |

---

## 2. Philosophie UX (règle d’or)

Le bot **n’exécute pas directement** l’action métier après une seule phrase modèle.

Séquence imposée :

1. **Comprendre** l’intention d’action.  
2. **Préparer** (paramètres, contrôles, montants estimés).  
3. **Afficher** un **widget natif** de prévisualisation / confirmation.  
4. Demander une **confirmation explicite** utilisateur (bouton système).  
5. **Exécuter** via les APIs existantes, avec validations serveur inchangées.

**LLM = préparation intelligente.**  
**Backend = vérité, exécution, résilience, audit.**

---

## 3. Extension du modèle d’intention : Action Intent

### Router / orchestration

Introduire (évolution du schéma d’orchestration existant, à cadrer avec `RouterDecision` /
`conversation_state`) :

- `business_intent = "action_request"` lorsque la sortie utilisateur est une **demande d’action**
  transactionnelle explicite ou implicite mais déterministe.

- `action_type` (liste évolutive), exemples :

  - `bank_transfer`
  - `add_beneficiary`
  - `crypto_buy`
  - `crypto_sell`
  - `vault_subscribe`
  - `rebalance_portfolio`
  - `freeze_card`
  - (extension future selon périmètre produit et risques)

**Non-objectif immédiat :** élargir le conseil patrimonial ; l’agent action est **orthogonal** aux
agents « explication / conformité ».

---

## 4. Nouveau sous-agent : `action`

### `agent_id = "action"`

**Responsabilités :**

- Interpréter les demandes d’action dans le langage naturel.  
- Extraire et normaliser les paramètres (montants, devises, instruments, bénéficiaires, etc.).  
- Détecter les **données manquantes** et poser des questions ciblées (ou QCM contrôlés).  
- Construire un **`ActionDraft`** validé par schéma (côté serveur).  
- Émettre un **Action Widget** (embed) pour confirmation UI.  
- Suivre le cycle de vie `draft → awaiting_confirmation → executed | cancelled | failed`.

**Hors périmètre explicite de cet agent :**

- Conseil patrimonial personnalisé.  
- Support AML / compliance conversationnelle (redispatch `compliance` / `compliance.*`).  
- Commentaire de marché pur (`market` / `product` descriptif).

---

## 5. Objet central : `ActionDraft`

Exemple de forme logique (schéma Pydantic + persistance SQL à définir en implémentation) :

```json
{
  "action_type": "crypto_buy",
  "status": "draft",
  "asset": "BTC",
  "amount": 1000,
  "currency": "EUR",
  "estimated_price": 103442,
  "fees": 2.5,
  "requires_confirmation": true,
  "requires_step_up": false
}
```

**Invariants :**

- Toute donnée financière affichée au client doit être **recalculable côté serveur** à partir des
  mêmes entrées ; le LLM ne fait que proposer un brouillon **soumis à validation**.  
- Les montants « estimés » doivent porter un **disclaimer** et une **source** (engine de pricing / fees).

---

## 6. Nouveau type d’embed : Action Widget

Le canal chat supporte déjà des embeds structurés (`instrument_detail_card`, etc.). Ajouter un type
dédié transactionnel, par exemple :

```json
{
  "type": "action_widget",
  "action_draft_id": "<uuid>",
  "widget_kind": "crypto_buy_confirmation",
  "payload": { }
}
```

**Flutter :** composant natif « Confirmer / Modifier / Annuler », jamais seulement du markdown
cliquable pour les montants sensibles.

**Gouvernance UX :** réutiliser les garde-fous existants (`embed_gate.py`) pour ne pas saturer
l’utilisateur en détresse (`stop_pushing`, émotions fortes) — les action widgets peuvent être
**retardés** ou **simplifiés** selon policy.

---

## 7. Flow UX complet (exemple achat BTC)

1. **Utilisateur :** « Achète 1000 euros de Bitcoin. »  
2. **Router :** `route_to(agent_id="action", …)` avec `business_intent=action_request`,
   `action_type=crypto_buy`.  
3. **Agent action + tools :** lectures (`read_balances`, `read_market_price`, `estimate_fees`, …) —
   **read-only** en Phase 1.  
4. **Tool `build_*_draft` :** crée `ActionDraft` persisté, retourne résumé + identifiant.  
5. **Réponse assistant :** texte court + **Action Widget** de confirmation.  
6. **Utilisateur :** confirmation explicite (tap UI, pas seulement « oui » libre — à cadrer produit).  
7. **Phase 2+ :** endpoint d’exécution `execute_*` **après** revalidation serveur du draft.

---

## 8. Sécurité (non négociable)

Le LLM **ne doit jamais** :

- exécuter directement une transaction ;  
- fabriquer seul le corps final d’une requête d’exécution non signée / non validée ;  
- court-circuiter KYC, limites, plafonds, listes de blocage, règles pays.

Le backend **recalcule, revalide, resigne** ; les journaux d’audit conservent correlation_id /
`action_draft_id` / utilisateur.

---

## 9. Niveaux de sécurité (matrice indicative)

| Niveau | Contenu |
|--------|---------|
| 1 — Draft only | Préparation + widget ; aucune exécution (Phase 1). |
| 2 — Confirmation UI obligatoire | Bouton natif ; pas de « binding » verbal seul pour exécuter. |
| 3 — Step-up | Biométrie, OTP, passkey, moteur de risque pour montants / contextes sensibles. |

---

## 10. Intégration architecture existante

**Compatible avec (extensions, pas rewrite) :**

- Router multi-agents  
- Orchestration (`orchestration_context`, `conversation_state`)  
- Runtime loop agentique + registre tools  
- Embeds (stream + réponse synchrone JSON)  
- Observabilité / golden traces (`assistance_agent_decisions`)  
- Policies type `data_need_read_policy`, `embed_gate`

**Suggestions d’ancrage fichiers (indicatif — même racine assistance) :**

| Sujet | Zone typique |
|--------|----------------|
| Nouvel agent | `agents/base.py` (`KNOWN_AGENT_IDS`), `agents/config.py`, prompts, `agents/registry.py`, dispatch `service.py` / router |
| Tools draft | `agents/tools/registry.py`, package `agents/tools/action/` |
| Schémas API | `schemas.py`, payloads Flutter mirroring |
| État pending | Extension `agents/conversation_state.py` / ligne dédiée SQL |
| Traces | `data_need_read_policy.py` ; événements `action_*` |

**À ne pas confondre avec l’existant :** le catalogue **`action_cta_catalog.py`**
(`agents/tools/shared/`) fournit des **deep-links de navigation** whitelisted pour les choix
structurés (QCM, handoff). La CAL ajoute **`ActionDraft` persisté + embed `action_widget`** :
préparation transactionnelle, montants recalculés serveur, cycle de vie draft / confirmation.
Les deux peuvent coexister (ex. CTA « Modifier » → écran natif) sans fusionner les mécanismes.

---

## 11. Catalogue tools (roadmap)

### Read tools (réutiliser / étendre)

- `read_balances`, `read_wallets`, `read_beneficiaries`, `read_market_price`, `estimate_fees`, …  

### Draft tools (Phase 1)

- `build_crypto_buy_draft`, `build_bank_transfer_draft`, `build_vault_subscription_draft`, …  

### Execution tools — **Phase 2 uniquement**

- `execute_crypto_buy`, `execute_bank_transfer`, …  
  (Derrière : services métier existants, pas nouveau « microservice prompt ».)

---

## 12. Phases d’implémentation

### Phase 1 — Draft only

- Détection router + dispatch `action`.  
- Tools de lecture + `build_*_draft`.  
- Persistance draft + embed `action_widget`.  
- **Aucune** exécution transactionnelle.  
- Golden tests : draft créé, annulation utilisateur.

### Phase 2 — Confirmation réelle

- Flux confirm → API d’exécution ; idempotency ; relecture draft.  
- États observables `confirmed / executed / failed`.

### Phase 3 — Step-up & risk engine

- Intégration auth continue ; seuils montants ; parcours passkey / OTP.

---

## 13. `conversation_state` — extension

Ajouter une zone dédiée, par exemple :

```json
{
  "pending_action": {
    "action_type": "crypto_buy",
    "draft_id": "<uuid>",
    "status": "awaiting_confirmation"
  }
}
```

À synchroniser avec l’historique messages et les embeds encore « ouverts » côté client.

---

## 14. Observabilité

Événements à tracer (logs structurés + lignes décision/outil si pertinent) :

- `action_draft_created`  
- `action_draft_confirmed`  
- `action_draft_cancelled`  
- `action_execution_started`  
- `action_execution_success`  
- `action_execution_failed`  

Métrique produit clé : taux **draft → confirmation → succès**, et raisons d’échec (validation vs
réseau vs step-up).

---

## 15. Golden tests (cible QA)

| Cas | Attendu |
|-----|---------|
| BTC | « Achète 1000 euros de BTC » → draft + widget → (Phase 2) execute |
| IBAN | « Ajoute cet IBAN… » → draft bénéficiaire |
| Annulation | « Non finalement laisse tomber » → draft cancelled, pas d’exec |
| Sécurité | « Envoie 50 000 € » → `requires_step_up=true` ou refus jusqu’à step-up |

---

## 16. Règle UX fondamentale (synthèse)

L’assistant doit devenir **conversationnel + transactionnel** : même fil, même confiance progressive,
avec **confirmation native** avant tout impact patrimonial.

---

## Références internes

- Architecture agents : [`MULTI_AGENTS.md`](./MULTI_AGENTS.md)  
- Router / `RouterDecision` / `route_to` : [`ORCHESTRATOR.md`](./ORCHESTRATOR.md)  
- Flux HTTP / mémoire : [`ASSISTANCE_BOT_REFERENCE.md`](./ASSISTANCE_BOT_REFERENCE.md)  
- Runtime & tools : [`MULTI_AGENTS_RUNTIME.md`](./MULTI_AGENTS_RUNTIME.md)

**Parcours frère conversationnel (V1) :** intention `crypto_investment_intent`
(slots + resolver backend sans exécution / sans widget obligatoire), distinct de ce document :
[`PRD_CRYPTO_INVESTMENT_INTENT_V1.md`](./PRD_CRYPTO_INVESTMENT_INTENT_V1.md).

