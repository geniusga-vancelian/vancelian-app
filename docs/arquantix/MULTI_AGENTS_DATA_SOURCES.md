# Multi-agents — Cartographie des sources de données

> **Statut :** doc vivant. Mise à jour à **chaque** livraison d'une phase
> V2 d'agent (Phases 2 → 6 de `MULTI_AGENTS.md`).
>
> **Source unique de vérité** pour répondre à *« où chaque agent va lire
> ses données ? »*.
>
> **Dernière mise à jour :** 2026-05-02 — **v2.1 : Phase 2a livrée** (runtime + Compliance L0). Cf. § 10. Avant: v2.0 — pivot post-AUDIT vers
> runtime agentique introspectif** (cf. § 0bis ci-dessous).
>
> **Documents liés :**
> - `MULTI_AGENTS.md` — architecture cible des agents
> - `MULTI_AGENTS_RUNTIME.md` — **spec du runtime** (function calling
>   itératif, autonomy levels, tools, sécurité tipping-off)
> - `AUDIT_AUTH_IDENTITIES.md` — règles `client_id` / `user_id` /
>   `classify_actor()`
> - `MEMORY.md` — mémoire long-terme cross-conversations (substrat partagé)
> - `ARCHITECTURE.md` — vue d'ensemble système

---

## 0bis. Mise à jour v2.0 — pivot post-AUDIT (2026-05-02)

> **Important** : les tableaux du § 3 ci-dessous décrivent toujours
> fidèlement **les données disponibles** dans la DB Vancelian. Mais le
> **pattern d'accès** par les agents a changé.

### Ce qui a changé

| Avant (v1.0) | Maintenant (v2.0) |
|---|---|
| Tool figé par cas d'usage : `get_kyc_summary`, `get_recent_orders`, etc. | Tool **introspectif** : `read_compliance_state`, `read_registration_progress`, `read_documents`, `read_transactions` — **schema-driven** |
| Single-shot LLM : 1 prompt → 1 réponse | **Function-calling itératif** : le LLM appelle 0..N tools en parallèle/séquence sur 1..6 tours |
| Hardcoding implicite des `field_slug` / types de transactions | **Aucun hardcoding** : les tools découvrent la structure DB à l'exécution |
| Mode advisory uniquement | **Autonomy levels L0 → L3** configurables par agent |
| Disclaimers réglementaires côté prompt seulement | **Sécurité matérielle tipping-off** : signaux gated côté tool, jamais en mémoire LLM |

### Comment lire ce doc maintenant

Les tableaux du § 3 deviennent une **référence des données accessibles**
au LLM via les tools introspectifs, plutôt qu'un dictionnaire 1:1 de
fonctions Python. Concrètement :

- Pour **Compliance** : tout est exposé via `read_compliance_state`
  (snapshot complet) + 4 tools spécialisés (`read_registration_progress`,
  `read_documents`, `read_transactions`, `read_external_aml_signals`).
  Le LLM choisit lesquels appeler.
- Pour **Advisor / Product / Market** : même pattern, à instancier
  Phases 3 / 5 / 6 selon `MULTI_AGENTS_RUNTIME.md` § 13.

### Mapping tools v1.0 → tools v2.0

| Tool v1.0 (cartographie figée) | Tool v2.0 (introspectif) | Champ exposé via |
|---|---|---|
| `get_kyc_summary(client_id)` | `read_compliance_state` | `.documents.summary` + `.compliance_signals` |
| `get_recent_orders(client_id, limit)` | `read_transactions` | `.by_type.orders` (top N) |
| `get_recent_ledger_entries(...)` | `read_transactions` | `.by_type.ledger` |
| `get_active_subscriptions(...)` | `read_compliance_state` | `.documents.subscriptions` (à arbitrer) |
| `get_portfolios_overview(...)` (advisor) | `read_advisor_state` (Phase 3) | `.portfolios` |
| `get_quote(symbol)` (market) | `read_market_state` (Phase 6) | `.quotes[symbol]` |

### Mode read-only intégral

**Phase 2a livre uniquement des tools L0 (read-only).** Les tools
mutatifs (`request_document_upload`, `create_compliance_ticket`, etc.)
arrivent en Phase 2c. L'agent compliance ne mute **rien** dans la DB en
sortie de Phase 2a. Voir `MULTI_AGENTS_RUNTIME.md` § 3 pour la matrice
complète des autonomy levels.

### Le `client_id` reste pivot

Toutes les signatures de repos restent sur `client_id: str` (UUID
stringifié), conformément à la **règle 1** d'`AUDIT_AUTH_IDENTITIES.md`
§ 6. Les tools introspectifs traversent les FK depuis `client_id` —
jamais depuis `user_id` directement.

---

## 0. TL;DR

Chaque agent multi-agents respecte **3 couches strictes** : `agent → tool →
repository`. Ce doc fige :

1. Le **pattern** d'architecture data (§ 1).
2. Les **conventions** de signatures, d'erreurs et de cache (§ 2).
3. La **cartographie des sources réelles** par agent (§ 3) — quelles
   tables / services / APIs alimentent quelles questions utilisateur.
4. La **stratégie de tests** (§ 4).
5. Les **anti-patterns** à proscrire (§ 5).
6. La **roadmap V2 par agent** avec critères de done (§ 6).
7. Le **modèle de PR** quand on substitue un stub par du réel (§ 7).

---

## 1. Pattern d'architecture (3 couches)

```
┌──────────────────────────────────────────────────────┐
│  L'AGENT                                             │
│  services/assistance/agents/<id>.py                  │
│  ─────────────────────────────────────────────────── │
│  Compose le prompt LLM, consomme 1+ tools, formate   │
│  la sortie Markdown. Ne sait pas d'où vient la data. │
└────────────────────────┬─────────────────────────────┘
                         │ appelle (signature stable)
                         ▼
┌──────────────────────────────────────────────────────┐
│  LE TOOL                                             │
│  services/assistance/agents/tools/<id>_tools.py      │
│  ─────────────────────────────────────────────────── │
│  Frontière contractuelle. Convertit DB row → dict    │
│  Python plat (JSON-serializable). Cache si pertinent.│
└────────────────────────┬─────────────────────────────┘
                         │ appelle
                         ▼
┌──────────────────────────────────────────────────────┐
│  LE REPOSITORY                                       │
│  services/assistance/agents/repositories/<id>_repo.py│
│  ─────────────────────────────────────────────────── │
│  SQL/SQLAlchemy/HTTP/RAG. Réutilisable hors          │
│  multi-agents (admin web, jobs, API publique).       │
└──────────────────────────────────────────────────────┘
```

### 1.1 Pourquoi cette séparation est non-négociable

- **Testabilité** : on mocke `compliance_tools.get_kyc_summary()` au niveau
  agent ; on mocke la `Session` SQLAlchemy au niveau repo.
- **Réutilisabilité** : un repo peut servir à un job batch, à l'admin web,
  et à un agent — sans dupliquer le SQL.
- **Substitution stable** : passer du stub V1 au réel V2 = remplacer
  **uniquement le corps du repo**. Tools et agent inchangés.
- **Audit / sécurité** : tout SQL passe par les repos → *grep -r "select"*
  facile pour audit ; injection SQL = nulle (tout est paramétré).

### 1.2 Règle d'or : **read-only**

**Aucun agent V2 ne mute la DB.** Pas d'`INSERT`, pas d'`UPDATE`, pas de
`DELETE` dans aucun repo appelé par un agent. Si une action user nécessite
une mutation (ex. *« déclenche un retrait »*), l'agent **renvoie un
disclaimer** et redirige vers l'écran adéquat de l'app — il ne fait pas
le retrait lui-même.

Exception unique acceptée : `assistance_memory.consolidate_conversation`
(qui écrit dans `assistance_conversations` et `pe_clients.assistance_long_memory`)
— mais ce n'est **pas** un agent, c'est un job post-tour.

---

## 2. Conventions

### 2.1 Signatures de tools

Toutes les fonctions tool respectent ces 5 règles :

1. **Préfixe `get_`** pour la lecture, `search_` pour la recherche
   textuelle, `count_` pour des stats. **Jamais** `set_`, `update_`,
   `create_` (cf. § 1.2).
2. **1ʳᵉ position : identifiant principal** (`client_id`, `portfolio_id`,
   `instrument_code`, …). Toujours `str` (UUID stringifié) pour rester
   JSON-serializable côté LLM si on passe à du function calling natif
   plus tard.
3. **kwargs only pour le reste** (`limit`, `since`, `include_drafts`).
4. **Return = `dict | list[dict] | None`** — toujours JSON-serializable.
   `None` = ressource introuvable (pas exception). Liste vide = pas de
   donnée (légitime, n'est pas une erreur).
5. **Aucune exception non-attrapée**. Erreurs réseau/DB → log warning + retour
   `None` ou liste vide. Le tour LLM ne doit **jamais** crasher à cause
   d'une donnée manquante.

```python
# ✓ BON
def get_kyc_summary(client_id: str) -> Optional[dict[str, Any]]:
    """Retourne {kyc_status, status, updated_at} ou None si client introuvable."""

# ✗ MAUVAIS — exception non gérée + return objet ORM
def get_kyc(client_uuid: UUID) -> PeClients:
    return db.query(PeClients).filter_by(id=client_uuid).one()
```

### 2.2 Format de retour standardisé

Tous les tools retournent des **dicts plats** avec des clés `snake_case`
en minuscules. Les valeurs Decimal sont converties en `float` (lossy
acceptable pour de l'affichage) **OU** en `str` (sans perte) selon le
contexte. Les `datetime` sont sérialisés en ISO-8601 UTC.

```python
{
    "id": "8f3c…",
    "kyc_status": "validated",
    "status": "active",
    "updated_at": "2026-04-15T08:32:11+00:00",
}
```

### 2.3 Cache (à activer agent par agent)

Certains tools sont appelés sur **chaque tour** d'une même conversation
courte (ex. `get_kyc_summary` du même client). Pour éviter du SQL
inutile, on peut activer un cache **côté tool** (pas côté repo) avec
une TTL courte :

| Tool | TTL recommandée | Justification |
|---|---|---|
| `get_kyc_summary` | 60 s | KYC bouge très peu, le client ne resoumet pas tous les 30 s |
| `get_recent_orders` | 10 s | Veut voir « son dépôt vient d'arriver » → pas trop long |
| `get_portfolio_overview` | 30 s | NAV bouge mais pas seconde par seconde |
| `get_quote(symbol)` | 5 s | Cours marché → frais |

Implémentation V2 : `functools.lru_cache` pour du in-memory simple ; si
besoin cross-process, Redis avec clé `assistance:{tool}:{key}`. **Cache
explicitement opt-in** par tool, pas global.

### 2.4 Erreurs et observabilité

Chaque tool log un événement structuré sur erreur :

```python
logger.warning(
    "assistance.tool.%s.failed client=%s exc=%s",
    tool_name, client_id, exc,
)
return None  # jamais propager
```

Les compteurs de calls / latences peuvent être ajoutés en V2 via Prometheus
(à brancher dans une phase ultérieure si nécessaire).

---

## 3. Cartographie par agent

Pour chaque agent : **(a) catalogue des questions** que l'agent doit
savoir traiter, **(b) source réelle** dans la DB Vancelian (table +
champs), **(c) tool exposé**, **(d) statut V1 / V2**.

### 3.1 Agent `compliance` — Assistance compte

> **Ton :** factuel, court, pas de pédagogie. Cf. `prompts/compliance_system.md`.
>
> **Repo cible :** `services/assistance/agents/repositories/compliance_repo.py`
> (à créer en Phase 2).

| Question utilisateur type | Source DB | Champs clés | Tool exposé | V1 | V2 |
|---|---|---|---|---|---|
| « Mon KYC est-il validé ? » | `pe_clients` | `kyc_status` (`not_started`/`pending`/`validated`/`rejected`), `status`, `updated_at` | `get_kyc_summary(client_id)` | stub neutre | ✅ planifié |
| « Mon compte est actif ? » | `pe_clients` | `status` (`pending`/`active`/etc.) | (idem ci-dessus) | stub | ✅ |
| « Où en est mon dépôt / virement ? » | `pe_orders` | `order_type`, `side`, `quantity`, `amount`, `currency`, `status` (`pending`/`filled`/`rejected`/etc.), `rejection_reason`, `created_at` | `get_recent_orders(client_id, limit=10)` | stub | ✅ |
| « Mes mouvements récents (grand livre) ? » | `pe_ledger_entries` | `entry_type` (debit/credit), `amount`, `currency`, `reference_type`, `description`, `effective_at` | `get_recent_ledger_entries(client_id, limit=20)` | — | ✅ |
| « Mes souscriptions produit ? » | `pe_product_subscriptions` × `pe_product_definitions` | `subscription_amount`, `subscription_currency`, `status`, `metadata`, `name`, `product_code` | `get_active_subscriptions(client_id)` | — | ✅ |
| « Mes wallets / custody ? » | `pe_wallet_containers` | `wallet_type`, `custody_provider`, `blockchain_address`, `ledger_account_ref` | `get_wallets_overview(client_id)` | — | optionnel |
| « Mes trades exécutés ? » | `pe_trades` × `pe_orders` | `quantity`, `price`, `gross_amount`, `fee_amount`, `instrument_id`, jointure pour récupérer le `client_id` via order | `get_recent_trades(client_id, limit=10)` | — | optionnel |

**Cas d'escalade détectés par l'agent (cf. `compliance_system.md` § « Cas d'escalade »)** :
- `kyc_status='rejected'` → encart de redirection support.
- `pe_orders.status='on_hold'` ou `pe_orders.status='rejected'` depuis > 48 h → idem.
- Mots-clés du message user (« urgent », « bloqué », « fraude ») → idem.

→ La détection se fait **côté agent** (logique métier dans le prompt et/ou
dans `compliance.py` après lecture du tool), pas dans le tool lui-même
(qui doit rester neutre / réutilisable).

### 3.2 Agent `advisor` — Conseil placement

> **Ton :** pédagogue, structuré, avec disclaimers. Cf. `prompts/advisor_system.md`.
>
> **Repo cible :** `services/assistance/agents/repositories/advisor_repo.py`
> (à créer en Phase 3).

| Question | Source | Champs | Tool | V1 | V2 |
|---|---|---|---|---|---|
| Profil / objectifs / horizon | `pe_clients.assistance_long_memory` | `facts` (déjà structurés) | `get_long_memory(client_id)` | déjà branché via `prompt_builder` | déjà ✅ |
| Profil de risque officiel | `pe_portfolios` | `risk_profile`, `name`, `base_currency`, `status` | `get_portfolios_overview(client_id)` | stub `None` | ✅ |
| Valeur portefeuille (NAV) | `pe_portfolio_valuations` | `nav`, `total_realized_pnl`, `total_unrealized_pnl`, `total_pnl`, `valuation_timestamp` | (idem ci-dessus, dernière valuation par portefeuille) | stub | ✅ |
| Positions détenues | `pe_position_atoms` × `pe_instruments` | `instrument_id`, `position_type`, infos instrument | `get_positions(portfolio_id, limit=50)` | — | ✅ phase 3 |
| Allocation cible vs réelle | `pe_target_allocations` × `pe_position_atoms` | `target_weight`, `min_weight`, `max_weight`, poids réel calculé | `get_target_vs_actual(portfolio_id)` | — | ✅ phase 3 |
| Conseiller humain assigné | `pe_advisor_client_assignments` | (recherche du conseiller assigné) | `get_assigned_advisor(client_id)` | — | optionnel |
| « Que se passerait-il si … ? » (simulation) | `backtest_runs`, `backtest_metrics`, `backtest_portfolio_series` | dépend du scenario | `get_recent_backtest(strategy_instance_id)` | — | phase 3+ |
| Stratégies actives | `pe_strategy_instances`, `pe_strategy_evaluations` | nom, état, dernière évaluation | `get_active_strategies(client_id)` | — | optionnel |

**Règles d'allocation** : **pas en DB**. Module Python dédié
`services/assistance/agents/allocation_rules.py` (à créer en Phase 3) qui
prend `(objectif, horizon, profil_risque, contraintes)` et retourne des
fourchettes recommandées (ex. *« 60-80 % actions, 15-30 % obligations »*).

**Disclaimers** : déjà gérés dans le prompt système (`advisor_system.md` §
« Disclaimers réglementaires »). Aucune logique data ici.

### 3.3 Agent `product` — Produits Vancelian

> **Ton :** informatif, factuel, citations chiffrées exactes uniquement.
> Cf. `prompts/product_system.md`.
>
> **Repo cible :** `services/assistance/agents/repositories/product_repo.py`
> (à créer en Phase 2 lite ou Phase 5).

| Question | Source | Champs | Tool | V1 | V2 lite | V2 full (RAG) |
|---|---|---|---|---|---|---|
| Liste des produits Vancelian | `pe_product_definitions` (`is_public=true`, `status='published'` ou similaire) | `product_code`, `name`, `description`, `product_type`, `risk_label`, `base_currency` | `list_public_products()` | — | ✅ | ✅ |
| Détail d'un produit | `pe_product_definitions` (par `product_code`) | (idem) + `metadata` | `get_product_summary(product_code)` | stub `None` | ✅ | ✅ |
| Page CMS d'un produit | `pages` × `page_i18n` × `sections` | `slug`, `urlPath`, `title`, `description`, contenu sections | `get_product_page(slug, locale='fr')` | — | optionnel | ✅ |
| Articles d'aide produit | `help_articles` × `help_article_blocks` × `help_article_i18n` | `slug`, `title`, blocs Markdown | `search_help_articles(query, locale='fr', limit=5)` | — | optionnel | ✅ |
| Fiche DICI / KIID / plaquette PDF | RAG vectoriel sur PDFs ingérés depuis le CMS / R2 | embeddings + chunks | `rag_query(query, product_code=None, top_k=5)` | — | — | ✅ Phase 5 |

**Phase V2 lite vs V2 full** :
- **lite** = on lit `pe_product_definitions` + éventuellement `pages` ; on
  reste sur la connaissance LLM générale Vancelian.
- **full (RAG Phase 5)** = on indexe les vrais documents officiels
  (DICI/KIID/plaquettes commerciales) et on les retrouve par embedding
  similarity. Permet à l'agent de **citer textuellement** des passages
  réglementaires.

### 3.4 Agent `market` — Veille marché

> **Ton :** analytique, daté, mesuré. Cf. `prompts/market_system.md`.
>
> **Repo cible :** `services/assistance/agents/repositories/market_repo.py`
> (à créer en Phase 4 / Phase 6).

| Question | Source | Champs | Tool | V1 | V2 lite | V2 full |
|---|---|---|---|---|---|---|
| Cours d'un instrument | `marketdata_latest_quotes` × `marketdata_instruments` | `last_price`, `bid_price`, `ask_price`, `quote_time`, `symbol`, `name` | `get_quote(symbol)` | stub vide | ✅ | ✅ |
| Évolution sur N jours / semaines | `marketdata_bars_1d` / `marketdata_bars_1w` | `open`, `high`, `low`, `close`, `volume`, `timestamp` | `get_history(symbol, period='1m')` | — | ✅ | ✅ |
| Bundles d'instruments thématiques | `marketdata_bundles` | (à inspecter quand pertinent) | `list_bundles(theme=None)` | — | ✅ | ✅ |
| Actualités macro / news live | **table à créer** (`vancelian_news`) ou flux RSS curaté | `title`, `published_at`, `source`, `excerpt`, `topics[]`, `body` | `get_recent_news(topic, limit=5)` | stub vide | — | ✅ Phase 6 |
| Analyses internes équipe | **table à créer** (`vancelian_analyses`) ou MD versionnés en R2 | `title`, `author`, `topic`, `body_markdown`, `published_at` | `get_internal_analyses(topic, limit=3)` | — | — | ✅ Phase 6 |

**Tables à créer Phase 6** : `vancelian_news` + `vancelian_analyses` avec
admin BO côté Next pour saisie/import RSS. Pas de schéma figé ici, on le
décidera au démarrage Phase 6.

---

## 4. Stratégie de tests

Chaque couche a sa **suite dédiée**, pour ne tester qu'une chose à la fois :

| Couche | Suite | Mocks |
|---|---|---|
| **Agent** | `tests/test_assistance_agents_*.py` | mocke les tools (pas la DB) |
| **Tool** | `tests/test_assistance_tools_*.py` (à créer Phase 2+) | mocke le repo |
| **Repo** | `tests/test_assistance_repos_*.py` (à créer Phase 2+) | utilise une **vraie session DB transactionnelle** (pattern déjà en place pour `test_assistance_memory_integration.py`) |

### 4.1 Tests d'intégration end-to-end

À créer Phase 2+ : `tests/test_assistance_e2e_<agent>.py` qui :
- monte un client `pe_clients` + transactions fixtures via fixture pytest,
- déclenche un `start_chat_turn` + `stream_assistant_turn` mocké côté LLM,
- vérifie que le message persisté contient le bon `agent_used` et que les
  données injectées dans le prompt système contiennent bien le snapshot
  des fixtures (via mock du `chat_completion_stream` qui inspecte les
  `messages`).

---

## 5. Anti-patterns à proscrire

| ❌ Anti-pattern | ✅ À faire à la place |
|---|---|
| `db.query(PeClients).filter_by(...).first()` directement dans `compliance.py` | Passer par `compliance_tools.get_kyc_summary(client_id)` qui appelle `compliance_repo.fetch_kyc(client_id)` |
| Retourner un objet ORM `PeClients` depuis un tool | Retourner un `dict` plat (les ORMs ne sont pas JSON-serializable et pas thread-safe au-delà de la session) |
| `raise HTTPException` dans un tool | Logger + retourner `None`. L'agent décide quoi dire au LLM. |
| Cache global `@lru_cache` sans TTL | Cache opt-in **par tool**, TTL explicite (cf. § 2.3) |
| Importer un agent depuis un repo (cycle) | Repos ne dépendent **jamais** des agents. Sens = `agent → tool → repo`, jamais l'inverse. |
| Passer une `Session` SQLAlchemy à un agent | L'agent reçoit `client_id`, c'est tout. Le repo gère la session via `SessionLocal()` ou via DI explicite. |
| Mêmes tools partagés entre 2 agents | Chaque agent a son **propre fichier de tools** (`compliance_tools.py`, `advisor_tools.py`). Si vraiment du code commun → factoriser dans `repositories/` (la couche en-dessous). |
| Agent qui sait quel modèle LLM il utilise | L'agent lit son modèle via `assistance_agent_model(self.agent_id)` (config centralisée). Aucun hardcode. |
| Mutation DB depuis un agent | **Interdit** (cf. § 1.2). Toute action mutative passe par une route HTTP dédiée + une UI utilisateur explicite. |

---

## 6. Roadmap V2 par agent

> **Note v2.0** : la roadmap est désormais alignée sur le runtime
> agentique de `MULTI_AGENTS_RUNTIME.md`. Phase 2 est scindée en
> **2a / 2b / 2c** selon les autonomy levels.

### 6.1 Phase 2a — Runtime + Compliance L0 (priorité #1)

**Pré-requis :** `AUDIT_AUTH_IDENTITIES.md` clôturé (✅ fait), spec
runtime validée (✅ `MULTI_AGENTS_RUNTIME.md`), schéma DB inchangé
(juste migration 148 = table `agent_decisions`).

**Critères de done :**
- [ ] **Migration 148** — table `agent_decisions` créée (cf. RUNTIME § 4.1).
- [ ] **Runtime loop** `runtime/agent_loop.py` (function calling itératif, MAX_ITER, timeouts) + tests unit ≥ 12.
- [ ] **Tools L0 introspectifs** Compliance livrés (5 tools) :
  - `read_compliance_state` (snapshot global)
  - `read_registration_progress` (axe 1)
  - `read_documents` (axe 1 + 2)
  - `read_transactions` (axe 3)
  - `read_external_aml_signals` (axe 2, **gated** : signaux pré-cuits safe)
- [ ] **Tool transverse** `ask_user_question` (clarifications QCM/freeform) + tests.
- [ ] **Primitive** `classify_actor()` (4 valeurs : CUSTOMER/ONBOARDING/ADMIN_BO/SUSPENDED) + tests ≥ 5.
- [ ] **Repos schema-driven** : `compliance_repo.py`, `registration_repo.py` — les tools découvrent dynamiquement les `RegistrationFlowSteps`, types de transactions, types de docs **sans hardcoding**.
- [ ] **Tests repo** intégration DB transactionnel ≥ 12 (fixture `pe_clients` + transactions + registration_session minimale).
- [ ] **Tests tools** (mock repo) ≥ 25.
- [ ] **Adapter pattern external** : `external/adapters/mock.py` actif par défaut, contrat `KycProvider` Protocol défini.
- [ ] **Tests anti-tipping-off** ≥ 8 scenarios (cf. RUNTIME § 5.3 et § 10.2). **Bloquants merge.**
- [ ] **Court-circuit `ADMIN_BO` → 403** dans `service.start_chat_turn`.
- [ ] **Court-circuit `SUSPENDED` → réponse standardisée** (pas de LLM call).
- [ ] **Promotion globale du fix `_require_client`** (`get_current_user_or_admin` avec opt-in) — clôture audit identité.
- [ ] **0 régression** sur les 47 tests Phase 1.
- [ ] **Smoke test live** : un client réel pose une question, l'agent appelle 2-3 tools, répond, message persisté avec `decision_ids` non vide.
- [ ] **MAJ § 3.1 du présent doc** avec statut « ✅ livré L0 v2.0 » sur les 5 tools.
- [ ] **Bump version** dans le tableau § 10 du présent doc → 2.1.

**Tables touchées en lecture** : `pe_clients`, `pe_orders`,
`pe_ledger_entries`, `pe_product_subscriptions`, `persons`, `documents`,
`registration_sessions`, `registration_session_steps`,
`registration_session_data`, `auth_global_risk_score` (gated, sortie
filtrée), `auth_security_decisions` (gated). Si l'une est vide en
local pour le client de test, générer un dataset minimal via
`services/arquantix/api/scripts/seed_assistance_e2e.py` (à créer).

**Aucune écriture en DB** sauf la nouvelle table `agent_decisions`
(audit trail). Toutes les actions L1/L2/L3 sont **désactivées** par
config (`ASSISTANCE_COMPLIANCE_AUTONOMY_MAX=L0`).

### 6.1bis Phase 2b — Conversation enquête + provider mock dynamique

**Critères de done :**
- [ ] Tool `ask_user_question` exploitable en multi-tour (la boucle redémarre proprement après réponse client).
- [ ] `external/adapters/mock_dynamic.py` qui retourne des résultats variés selon l'input.
- [ ] 5 scenarios e2e complexes (héritage, dépôt anormal, doc rejeté, etc.).
- [ ] Tests anti-tipping-off renforcés (≥ 12 scenarios).
- [ ] **MAJ § 3.1 du présent doc** + bump version 2.2.

### 6.1ter Phase 2c — Mutations L2 + UI BO admin

**Critères de done :**
- [ ] Tools `request_document_upload` (L2), `create_compliance_ticket` (L2), `propose_account_action` (L1) actifs.
- [ ] Config `ASSISTANCE_COMPLIANCE_AUTONOMY_MAX=L2`.
- [ ] UI BO admin Next.js pour reviewer les `agent_decisions` en `review_status='pending'` (L1) + audit log L2.
- [ ] Tests E2E mutations (création ticket déclenche notification, demande doc crée notification).
- [ ] **MAJ § 3.1 du présent doc** + bump version 2.3.

### 6.2 Phase 3 — Advisor V2

**Critères de done :**
- [ ] `advisor_repo.py` + `advisor_tools.py` mis à jour.
- [ ] Fonctions repo : `fetch_portfolios(client_id)`, `fetch_latest_valuations(portfolio_ids)`, `fetch_positions(portfolio_id)`, `fetch_target_vs_actual(portfolio_id)`.
- [ ] Module `allocation_rules.py` créé avec au moins 4 règles d'allocation (objectif × horizon).
- [ ] Disclaimers MiFID II testés (présents dans la sortie LLM via mock).
- [ ] Tests repo ≥ 6, tests tools ≥ 5, e2e ≥ 1.
- [ ] **MAJ § 3.2** du présent doc.

### 6.3 Phase 5 — Product V2 (lite puis full)

**Phase 5a (lite) — Critères de done :**
- [ ] `product_repo.py` lit `pe_product_definitions` + `pages`.
- [ ] `list_public_products()`, `get_product_summary(code)`, `get_product_page(slug, locale)`.
- [ ] Tests intégration sur dataset CMS minimal.
- [ ] **MAJ § 3.3** du présent doc.

**Phase 5b (full RAG) — Critères de done (projet à part) :**
- [ ] Décision indexation : pgvector (DB existante, plus simple) **ou** Qdrant (séparé, plus performant à grande échelle).
- [ ] Pipeline d'ingestion fiches (admin BO upload → chunk → embed → store).
- [ ] `rag_query(query, product_code=None, top_k=5)` opérationnel.
- [ ] Évaluation qualité : 20 questions de test → top-5 doit contenir le bon chunk dans ≥ 80 % des cas.
- [ ] **MAJ § 3.3** du présent doc.

### 6.4 Phase 6 — Market V2

**Phase 6a (cours / historique) — Critères de done :**
- [ ] `market_repo.py` lit `marketdata_latest_quotes` + `marketdata_bars_*`.
- [ ] `get_quote(symbol)`, `get_history(symbol, period)`, `list_bundles(theme)`.
- [ ] Tests sur dataset marketdata existant.
- [ ] **MAJ § 3.4** du présent doc.

**Phase 6b (news + analyses) — Critères de done (projet à part) :**
- [ ] Migration Alembic : tables `vancelian_news` + `vancelian_analyses`.
- [ ] Admin BO Next.js pour saisie analyses + import RSS curaté.
- [ ] `get_recent_news(topic, limit)`, `get_internal_analyses(topic, limit)`.
- [ ] **MAJ § 3.4** du présent doc.

---

## 7. Modèle de PR pour substituer un stub par du réel

À chaque livraison de phase V2, la PR doit suivre cette **checklist** :

1. **Repo créé / étendu** dans `services/assistance/agents/repositories/`.
2. **Tools substitués** : seul le **corps** change, **signatures
   inchangées** (sinon = breaking change pour l'agent → revue d'archi).
3. **Tests** : repo + tools + 1 e2e par tool (au minimum).
4. **Doc mise à jour** : § 3.x du présent doc avec colonnes V1/V2 actualisées.
5. **Pas de migration Alembic** sauf si nouvelle table (Phase 6b par ex.).
   Si migration : numéro `148+`, doc dans `MULTI_AGENTS.md` § 4.
6. **Smoke test live** sur la stack locale avant merge :
   - Un client de test connu en local
   - Une vraie question utilisateur déclenchée depuis Flutter
   - Vérification logs `assistance.agent.tour_done` + persistance correcte du
     message avec `agent_used` rempli.
7. **Pas de hot path bloqué** : tout call DB synchrone dans un tool doit
   répondre en < 200 ms p99 (sinon = ajouter cache § 2.3 ou index DB).

---

## 8. Glossaire

| Terme | Définition |
|---|---|
| **Agent** | Sous-classe Python implémentant `AgentBase`, qui produit la réponse Markdown finale au client. 5 agents : `default`, `compliance`, `advisor`, `product`, `market`. Cf. `MULTI_AGENTS.md` § 2. |
| **Tool** | Fonction Python pure exposée à un agent. Lit la donnée via le repo, retourne un dict plat. **Pas de SQL ici.** |
| **Repository** | Couche d'accès aux données — SQL/SQLAlchemy/HTTP/RAG. Réutilisable hors agents. |
| **V1 (Phase 1)** | Squelette livré : tools = stubs (retours neutres ou vides). Permet de prouver le pipeline end-to-end sans dépendre d'intégrations DB. |
| **V2** | Tools branchés sur les vraies sources DB / API. Phase par phase (Compliance Phase 2, Advisor Phase 3, etc.). |
| **Stub** | Implémentation neutre / vide d'un tool — retourne `None`, `[]` ou un dict avec `"stub": true`. Volontairement non-bavard pour ne pas brouiller les tests humains. |
| **RAG** | *Retrieval-Augmented Generation*. Indexer du texte (fiches PDF) en embeddings, retrouver les passages pertinents par similarité, les injecter dans le prompt LLM. Phase 5. |

---

## 9. Annexe — Contre-exemple : ce qu'on ne fait PAS

Ce snippet est volontairement **mauvais** pour qu'on s'en éloigne :

```python
# ❌ services/assistance/agents/compliance.py — VERSION INTERDITE
class ComplianceAgent:
    async def stream(self, agent_input):
        # Anti-pattern 1 : SQL direct dans l'agent
        from database import SessionLocal, PeClients
        db = SessionLocal()
        client = db.query(PeClients).filter_by(id=self._client_id).first()

        # Anti-pattern 2 : exception non gérée
        if not client:
            raise ValueError("client not found")

        # Anti-pattern 3 : objet ORM passé au prompt
        prompt = f"Status: {client.status}, KYC: {client.kyc_status}"

        # Anti-pattern 4 : mutation
        client.last_seen = datetime.now()
        db.commit()

        # Anti-pattern 5 : pas de log structuré, pas de close
        ...
```

À la place :

```python
# ✅ services/assistance/agents/compliance.py — VERSION CIBLE V2
class ComplianceAgent(LLMAgentBase):
    agent_id = "compliance"
    # …
    def _collect_tool_context(self, agent_input):
        kyc = compliance_tools.get_kyc_summary(self._client_id)
        orders = compliance_tools.get_recent_orders(self._client_id, limit=10)
        return _format_compliance_block(kyc, orders)


# ✅ services/assistance/agents/tools/compliance_tools.py
def get_kyc_summary(client_id: str) -> Optional[dict]:
    try:
        return compliance_repo.fetch_kyc(client_id)
    except Exception as exc:
        logger.warning("assistance.tool.kyc_failed client=%s exc=%s", client_id, exc)
        return None


# ✅ services/assistance/agents/repositories/compliance_repo.py
def fetch_kyc(client_id: str) -> Optional[dict]:
    with SessionLocal() as db:
        row = db.query(PeClients).filter_by(id=client_id).one_or_none()
        if row is None:
            return None
        return {
            "id": str(row.id),
            "kyc_status": row.kyc_status,
            "status": row.status,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
```

---

## 10. Versioning de ce doc

| Date | Version | Phase | Changements |
|---|---|---|---|
| 2026-05-02 | 1.0 | Phase 1 livrée | Création. Cartographie initiale (V1 stubs partout). |
| 2026-05-02 | **2.0** | Pré-Phase 2a | **Pivot post-AUDIT vers runtime agentique introspectif** : tools `read_compliance_state` etc. (schema-driven), function calling itératif, autonomy levels L0-L3, sécurité matérielle tipping-off. Cf. `MULTI_AGENTS_RUNTIME.md`. § 0bis ajouté. § 6 réorganisé en 2a/2b/2c. |
| 2026-05-02 | **2.1** | **Phase 2a livrée** | Runtime + Compliance L0 livrés. 5 tools L0 actifs (`read_compliance_state`, `read_registration_progress`, `read_documents`, `read_transactions`, `read_external_aml_signals`) + tool transverse `ask_user_question`. `classify_actor()` + court-circuits ADMIN_BO/ONBOARDING/SUSPENDED. Audit identité clôturé via `patch_auth_client_id_from_person`. 286 tests unit verts. Cf. `MULTI_AGENTS_RUNTIME.md` §13.1. |
| (à venir) | 2.2 | Phase 2b | Compliance enquête + provider mock dynamique — § 3.1 actualisé |
| (à venir) | 2.3 | Phase 2c | Compliance mutations L2 + UI BO review — § 3.1 actualisé |
| (à venir) | 3.x | Phase 3 | Advisor — § 3.2 actualisé |
| (à venir) | 4.x | Phase 4 | (réservé) |
| (à venir) | 5.x | Phase 5 | Product — § 3.3 actualisé |
| (à venir) | 6.x | Phase 6 | Market — § 3.4 actualisé |

> **Règle :** chaque PR de Phase V2 **doit** incrémenter la version ici
> et ajouter une ligne dans ce tableau, sinon la PR est incomplète.
