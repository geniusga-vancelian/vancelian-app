# Mémoire long-terme de l'assistance Vancelian

> **Palier 2 — D.2** : continuité conversationnelle (rolling summary + faits structurés) avec mémoire **cross-conversations** au niveau du client.

**Date :** 2026-05-02
**Status :** ✅ En production (image API rebuild + migration 146 appliquée)
**Couverture tests :** 81 tests (`tests/test_assistance_memory_unit.py` + `tests/test_assistance_memory_integration.py`)

---

## TL;DR

Quand une conversation d'assistance dépasse un seuil de tokens (par défaut **6000**, plancher applicatif **1000**), un agent LLM dédié (`gpt-4o-mini`, JSON mode, T=0.2) :

1. **Compresse** les anciens tours en un `conversation_summary` (rolling, 2-6 lignes)
2. **Extrait** des `conversation_facts` typés (objectifs, montants, horizon, profil de risque…)
3. **Agrège** ces facts dans `pe_clients.assistance_long_memory` (mémoire **cross-conv** au niveau client)

Le tour utilisateur suivant (et toute conversation ultérieure du même client) reçoit ces éléments dans le system prompt, ce qui permet à l'IA de connaître spontanément le profil et les préférences du client sans qu'il ait à se répéter.

**0 latence perçue côté client** : la consolidation tourne dans une `asyncio.create_task` lancée **après** l'émission du SSE `done`.

---

## 1. Objectifs (D.2)

| ID | Objectif | Implémenté |
|---|---|---|
| D.2.1 | Rolling summary déclenché au-delà d'un seuil tokens | ✅ |
| D.2.2 | Persistence : `conversation_summary` + `conversation_facts` + `summarized_until_turn` + `summary_updated_at` | ✅ migration 146 |
| D.2.3 | Mémoire cross-conv au niveau client : `pe_clients.assistance_long_memory` (JSONB, append-mostly) | ✅ migration 146 |
| D.2.4 | Async post-réponse SSE (0 latence) | ✅ `_schedule_consolidation` dans `service.py` |
| D.2.5 | Fail-open : LLM down → fallback heuristique, pas de blocage tour | ✅ `_heuristic_summary_fallback` |
| D.2.6 | Idempotence : pas de double-compression d'un tour absorbé | ✅ `summarized_until_turn` |
| D.2.7 | Sérialisation des consolidations concurrentes par conv | ✅ `_consolidation_locks` |

---

## 2. Architecture

### 2.1. Composants

```
┌──────────────────────────────────────────────────────────────────────┐
│                           Tour assistance                             │
│                                                                        │
│  Mobile (Flutter)                                                      │
│      │                                                                 │
│      │  POST /api/mobile/flutter/assistance/chat/turn/stream           │
│      ▼                                                                 │
│  Next.js BFF (proxy SSE)                                               │
│      │                                                                 │
│      │  POST /api/app/assistance/chat/turn/stream                      │
│      ▼                                                                 │
│  FastAPI : services.assistance.routes.chat_turn_stream                 │
│      │                                                                 │
│      ├─▶ start_chat_turn() ────▶ _build_context()                     │
│      │     persist user msg          │                                 │
│      │                               ├─ load_memory_state(db, conv)    │
│      │                               ├─ _load_history(K=8)             │
│      │                               └─ memory.build_context(          │
│      │                                    summary, long_memory, recent)│
│      ▼                                                                 │
│  stream_assistant_turn() ──── chat_markdown_stream() ────▶ OpenAI      │
│      │  yield delta events (SSE)                                       │
│      │  …                                                              │
│      │  persist assistant msg                                          │
│      │  yield {"type":"done", message_id}                              │
│      │                                                                 │
│      └─▶ _schedule_consolidation(session_factory, conv_id)             │
│              │                                                         │
│              │  asyncio.create_task (lock par conv_id)                 │
│              ▼                                                         │
│         memory.consolidate_conversation()                              │
│              │                                                         │
│              ├─▶ asyncio.to_thread(_consolidate_sync)                  │
│              │       │                                                 │
│              │       ├─ should_consolidate(messages, threshold)        │
│              │       ├─ _summarize_llm() ───▶ OpenAI gpt-4o-mini       │
│              │       │     (fallback heuristique si erreur)            │
│              │       ├─ _merge_conv_facts()                            │
│              │       ├─ _merge_client_long_memory()                    │
│              │       └─ db.commit()                                    │
│              │                                                         │
│              └─▶ logger.warning("assistance.memory.consolidated …")    │
│                                                                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2. Module `services.assistance.memory` (~700 lignes)

Module **autonome**, sans dépendance à `services.chatbot_epargne`. Seules dépendances :
`httpx`, `tiktoken`, `sqlalchemy`, modèles `AssistanceConversation` / `AssistanceMessage` (depuis `database.py`) et `Client as PeClients` (depuis `services.portfolio_engine.clients.models`).

**Surface publique :**
- `count_tokens(messages, model=None)` — comptage via tiktoken (`cl100k_base` pour gpt-4o), fallback heuristique `chars/4` si tiktoken absent.
- `should_consolidate(messages, threshold=None)` — `True` si total tokens ≥ seuil.
- `build_context(*, summary, client_long_memory, recent_turns)` — assemble le payload OpenAI : `[system memory block?] + recent_turns`.
- `consolidate_conversation(*, session_factory, conversation_id)` — coroutine async, lockée par conv, exécute `_consolidate_sync` dans un thread.
- `load_memory_state(db, conversation_id) -> MemoryState | None` — snapshot lecture pour `_build_context`.
- 4 helpers env vars : `assistance_summarizer_model()`, `assistance_summary_threshold_tokens()`, `assistance_recent_turns_kept()`, `assistance_summarizer_temperature()`.

**Fonctions privées clés :**
- `_consolidate_sync(session_factory, conversation_id)` — implémentation synchrone du flow complet.
- `_summarize_llm(*, previous_summary, client_long_memory, new_turns)` — appel HTTP OpenAI JSON mode strict.
- `_heuristic_summary_fallback(*, previous_summary, new_turns)` — fallback ultra-conservateur.
- `_sanitize_facts(raw)` — validation/normalisation : type énuméré, confidence ∈ [0,1], evidence ≤ 200 chars.
- `_merge_conv_facts(*, existing, new)` — fusion intra-conv : 1 fact par type, replace si valeur change.
- `_merge_client_long_memory(*, existing, new_facts, source_conversation_id, now)` — fusion cross-conv : append-mostly avec `first_seen_at` / `last_seen_at` / `source_conversation_id`, dédup par `(type, value normalisée)`.

### 2.3. Prompt summarizer

Fichier : `services/arquantix/api/services/assistance/prompts/summarizer_system.md`.

Prompt en français, JSON mode strict, énumération précise des types de faits (`investment_target`, `investment_horizon`, `risk_appetite`, `goal`, `liquidity_need`, `monthly_savings`, `net_worth_bucket`, `tax_optimization`, `product_interest`, `constraint`, `preference`, `other`), garde-fous PII (anonymise IBAN, n° téléphone, etc.), garde-fous éthiques (ignore santé/religion/opinion politique).

---

## 3. Schéma de données (migration 146)

### 3.1. `assistance_conversations` — 4 nouvelles colonnes

```sql
ALTER TABLE assistance_conversations
  ADD COLUMN conversation_summary    TEXT,
  ADD COLUMN conversation_facts      JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN summarized_until_turn   INTEGER,
  ADD COLUMN summary_updated_at      TIMESTAMPTZ;
```

| Colonne | Rôle | Format |
|---|---|---|
| `conversation_summary` | Rolling summary FR (2-6 lignes) | TEXT nullable |
| `conversation_facts` | Faits structurés extraits des tours | JSONB array |
| `summarized_until_turn` | `turn_index` du dernier tour absorbé | INTEGER nullable |
| `summary_updated_at` | Timestamp dernière consolidation | TIMESTAMPTZ nullable |

**Format `conversation_facts` :**

```json
[
  {
    "type": "investment_target",
    "value": 50000,
    "confidence": 0.95,
    "evidence": "investir 50 000 €",
    "source_turn": 18
  }
]
```

### 3.2. `pe_clients` — 1 nouvelle colonne

```sql
ALTER TABLE pe_clients
  ADD COLUMN assistance_long_memory JSONB NOT NULL DEFAULT '{}'::jsonb;
```

**Format complet `pe_clients.assistance_long_memory` :**

```json
{
  "facts": [
    {
      "type": "investment_target",
      "value": 100000,
      "confidence": 0.95,
      "evidence": "investissement initial de 100 000 €",
      "source_turn": 18,
      "source_conversation_id": "e03d843d-6b3d-469c-8e20-60f0e4b077bf",
      "first_seen_at": "2026-05-01T22:42:11.902181+00:00",
      "last_seen_at": "2026-05-01T22:43:27.404177+00:00"
    }
  ],
  "updated_at": "2026-05-01T22:43:27.404177+00:00"
}
```

**Stratégie append-mostly :** un changement de valeur (ex. `investment_horizon` de 60 → 84 mois) **ne supprime pas** l'ancienne entrée — les deux coexistent avec leurs `last_seen_at` respectifs. Permet à l'orchestrateur futur de désambiguïser temporellement.

### 3.3. Mirroirs

- **Prisma** : `services/arquantix/web/prisma/schema.prisma` — modèles `AssistanceConversation` et `PeClients` à jour (nécessite `npx prisma generate` après pull).
- **SQLAlchemy** : `database.py::AssistanceConversation` + `services/portfolio_engine/clients/models.py::Client` à jour.
- **Alembic** : `alembic/versions/146_assistance_long_term_memory.py`.

---

## 4. Cycle de vie d'une consolidation

### 4.1. Timeline d'un tour streaming

```
t0   POST /chat/turn/stream  reçu
t0+0 start_chat_turn() : persist user msg, _build_context() lit memory_state
t0+1 yield {"type":"started", conversation_id, user_message_id}  ◀── SSE
t0+2 chat_markdown_stream() → for each delta: yield {"type":"delta", content}
t1   stream OpenAI terminé, persist assistant msg
t1+1 yield {"type":"done", message_id}  ◀── SSE (CLIENT REPRIS LA MAIN)
t1+2 _schedule_consolidation(session_factory, conv_id)
     │
     │  asyncio.create_task — lance memory.consolidate_conversation()
     │  task ajoutée à _running_consolidations (anti-GC)
     │
     ▼
t1+3 memory.consolidate_conversation() :
     - acquire lock pour conv_id
     - asyncio.to_thread(_consolidate_sync, ...)
        │
        ▼
        _consolidate_sync :
        - charge AssistanceMessage de la conv (chronologique)
        - count_tokens(messages) ; si < threshold → return (no-op)
        - new_turns = msgs avec turn_index > summarized_until_turn
        - si pas de new_turns → return (déjà absorbé)
        - charge PeClients pour `client_long_memory` (contexte summarizer)
        - _summarize_llm() → JSON {summary, facts, open_points}
            ↓ (si erreur réseau/JSON/HTTP)
            _heuristic_summary_fallback() → marqueur dégradé, pas de facts
        - _sanitize_facts() : valide types, clamp confidence, tronque evidence
        - _merge_conv_facts() : fusion intra-conv
        - _merge_client_long_memory() : fusion cross-conv (append-mostly)
        - UPDATE assistance_conversations : summary + facts + summarized_until_turn + summary_updated_at
        - UPDATE pe_clients : assistance_long_memory
        - db.commit()
        - logger.warning("assistance.memory.consolidated conv=… up_to_turn=… facts=+N client_facts_total=N")
```

**Coût LLM par consolidation** : ~1500 tokens input (prompt + new_turns) + ~500 tokens output, soit ≈ **0.0002 USD** avec gpt-4o-mini.

### 4.2. Tour suivant : exploitation de la mémoire

`_build_context()` (dans `service.py`) :

```python
def _build_context(db, conv) -> list[dict]:
    state = memory.load_memory_state(db, conv.id)
    recent = _load_history(db, conv.id, limit=K)  # K=8 par défaut
    return memory.build_context(
        summary=state.conversation_summary,
        client_long_memory=state.client_long_memory,
        recent_turns=recent,
    )
```

**Backward-compatible** : si ni summary ni long_memory ne contiennent de données utiles, le payload est strictement équivalent à `_load_history(K)` (= comportement Palier 1 préservé).

Quand de la mémoire est disponible, un message `system` supplémentaire est préfixé :

```markdown
## Contexte client (mémoire long-terme cross-conversations)
- **investment_target** : 100000
- **investment_horizon** : 240
- **goal** : 10-15%
- **goal** : 40%
- **investment_horizon** : 36

## Résumé de la conversation en cours
Le client s'interroge sur la performance de son portefeuille diversifié...
```

(les facts à confiance < 0.7 sont annotés `_(confiance 0.5)_`)

---

## 5. Configuration

### 5.1. Variables d'environnement

| Var | Défaut | Plancher | Plafond | Rôle |
|---|---|---|---|---|
| `ASSISTANCE_SUMMARIZER_MODEL` | `OPENAI_MODEL` ou `gpt-4o-mini` | — | — | Modèle pour le summarizer (séparable du chat principal) |
| `ASSISTANCE_SUMMARY_THRESHOLD_TOKENS` | `6000` | `1000` | — | Seuil de déclenchement consolidation (somme tokens conv) |
| `ASSISTANCE_RECENT_TURNS_KEPT` | `8` | `2` | — | K — derniers tours bruts toujours envoyés (post-summary) |
| `ASSISTANCE_SUMMARIZER_TEMPERATURE` | `0.2` | `0.0` | `2.0` | Temperature OpenAI summarizer (bas = factuel) |
| `OPENAI_API_KEY` | — | — | — | (déjà existante, utilisée par chat principal aussi) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | — | — | (déjà existante) |

**Application** : modifier `.env.arquantix` puis `docker compose -f docker-compose.arquantix-recovery.yml --project-name arquantixrecovery up -d arquantix-api` (recreate du conteneur).

> ⚠️ Un `docker restart` ne suffit **pas** : il préserve le filesystem mais ne re-lit pas `env_file:`. Seul `up -d` (avec recreate) recharge les variables.

### 5.2. Tuning des paramètres

#### `ASSISTANCE_SUMMARY_THRESHOLD_TOKENS`

- **6000** (défaut) : conv power-user (30+ tours longs) → consolidation tardive, faible coût LLM.
- **1500** : conv typique (4-5 tours détaillés) → consolidation rapide, mémoire cross-conv quasi-immédiate.
- **1000** (plancher) : tout est consolidé presque tout le temps. Useful pour démos / recettes.

> 💡 Si l'utilisateur attend une mémoire cross-conv « WhatsApp-like » (= dès que je clos la conv 1, la conv 2 sait), descendre à **1500-2000**. Le coût LLM marginal est trivial avec `gpt-4o-mini`.

#### `ASSISTANCE_RECENT_TURNS_KEPT`

- **8** (défaut) : équilibre entre richesse contextuelle et coût tokens.
- **4** : optimisation tokens, conv plus « courte mémoire ».
- **16** : LLM voit beaucoup d'historique brut → plus précis mais coûts × 2.

---

## 6. Observabilité

### 6.1. Logs

Le module `services.assistance.memory` émet 3 types de logs (tous au niveau **WARNING** pour visibilité par défaut dans `docker logs` :

| Niveau | Préfixe | Contenu | Quand |
|---|---|---|---|
| WARNING | `assistance.memory.consolidated` | `conv=<uuid> up_to_turn=<n> facts=+<n> client_facts_total=<n>` | Consolidation OK, après commit DB |
| WARNING | `assistance.memory.llm_failed` | `conv=<uuid> — using heuristic fallback` | LLM down → fallback heuristique |
| WARNING | `assistance.memory.consolidation_failed` | `conv=<uuid>` + stack trace | Crash inattendu (best-effort) |

**Tail en live :**

```bash
docker logs arquantixrecovery-arquantix-api-1 --tail 100 -f \
  | grep "assistance.memory"
```

### 6.2. Queries SQL diagnostic

**État global mémoire des dernières conv :**

```sql
SELECT
  substring(id::text, 1, 8) AS conv,
  client_id,
  to_char(created_at, 'HH24:MI:SS') AS created,
  (SELECT count(*) FROM assistance_messages WHERE conversation_id = ac.id) AS n_msgs,
  summarized_until_turn AS sumto,
  jsonb_array_length(conversation_facts) AS n_facts,
  to_char(summary_updated_at, 'HH24:MI:SS') AS sum_updated
FROM assistance_conversations ac
ORDER BY last_message_at DESC NULLS LAST
LIMIT 10;
```

**Mémoire long-terme par client :**

```sql
SELECT
  substring(id::text, 1, 8) AS client,
  CASE WHEN assistance_long_memory = '{}'::jsonb THEN 'EMPTY'
       ELSE 'has ' || jsonb_array_length(assistance_long_memory->'facts') || ' facts'
  END AS state,
  assistance_long_memory->>'updated_at' AS updated_at
FROM pe_clients
WHERE id IN (SELECT DISTINCT client_id FROM assistance_conversations);
```

**Détail des facts d'un client :**

```sql
SELECT jsonb_pretty(assistance_long_memory)
FROM pe_clients
WHERE id = '<client_uuid>';
```

**Conv consolidées dans les dernières 24h :**

```sql
SELECT count(*)
FROM assistance_conversations
WHERE summary_updated_at > now() - interval '24 hours';
```

---

## 7. Troubleshooting

### Symptôme : *"L'IA ne se souvient pas du client dans une nouvelle conv"*

**Cause probable :** la conv précédente n'a jamais déclenché de consolidation (total tokens < seuil).

**Diagnostic :**

```sql
SELECT id, summarized_until_turn,
       jsonb_array_length(conversation_facts) AS n_facts
FROM assistance_conversations
WHERE client_id = '<client_uuid>'
ORDER BY last_message_at DESC;
```

Si toutes les lignes ont `summarized_until_turn = NULL`, aucune consolidation n'a eu lieu. Solutions :

1. Vérifier les tokens cumulés réels (cf. script `count_tokens` du module).
2. Baisser `ASSISTANCE_SUMMARY_THRESHOLD_TOKENS` (cf. §5.2) puis recreate API.
3. Forcer une consolidation manuelle ad-hoc (script Python à brancher sur SessionLocal).

### Symptôme : *"Aucun log `assistance.memory.consolidated` ne sort"*

Tous les logs critiques sont en **WARNING**. Si tu ne les vois pas avec :

```bash
docker logs arquantixrecovery-arquantix-api-1 | grep "assistance.memory"
```

Causes possibles :
- Aucune conv n'a atteint le seuil (cf. ci-dessus).
- Le hook `_schedule_consolidation` n'est pas exécuté → mode `/chat/turn` non-streaming utilisé (Phase 3 ne câble que le streaming, par design).
- Plus rare : le format string du logger a un bug. Si toi ou un dev modifie un `logger.warning(...)`, vérifier que `%s` count == args count (sinon `TypeError: not enough arguments for format string` plante silencieusement).

### Symptôme : *"`tiktoken` indisponible / fallback heuristique constant"*

Le module retombe sur une heuristique `chars/4` (suffisante pour le déclenchement, pas pour facturation OpenAI). Pour vérifier dans le conteneur :

```bash
docker exec arquantixrecovery-arquantix-api-1 python3 -c \
  "import tiktoken; e = tiktoken.encoding_for_model('gpt-4o-mini'); print(len(e.encode('hello world')))"
```

Si erreur d'import : `pip install tiktoken==0.7.0` (déjà dans `requirements.txt`).

### Symptôme : *"Consolidation tourne mais `conversation_facts` reste `[]`"*

Le LLM summarizer a renvoyé un JSON valide mais `facts: []` — souvent normal pour des tours sans information factuelle (salutations, questions très générales). Vérifier le contenu du `conversation_summary` (qui peut être substantiel même sans facts).

### Symptôme : *"Erreur `OPENAI_API_KEY missing`"*

`OPENAI_API_KEY` non chargée dans le conteneur. Vérifier `.env.arquantix` puis recreate le conteneur (cf. §5.1).

---

## 8. Tests

### 8.1. Couverture

**81 tests** (`docker exec -w /app arquantixrecovery-arquantix-api-1 python3 -m pytest tests/test_assistance_memory_*.py -v`) :

| Fichier | Tests | Couvre |
|---|---|---|
| `test_assistance_memory_unit.py` | 64 | Fonctions pures sans DB ni réseau : env vars, count_tokens, should_consolidate, _format_memory_block, build_context, _sanitize_facts, _merge_conv_facts, _merge_client_long_memory, _heuristic_summary_fallback, _load_system_prompt |
| `test_assistance_memory_integration.py` | 17 | DB Postgres réelle (rollback transactionnel) + mock httpx : load_memory_state, _consolidate_sync (cas nominal, no-op, idempotence, fallback heuristique sur LLM down/JSON invalide/HTTP 500), dédup cross-conv, append-mostly horizon evolution, lock concurrence async |

### 8.2. Lancer les tests

Les dépendances de test (pytest + pytest-asyncio) sont déclarées dans
`services/arquantix/api/requirements-dev.txt` (séparées du `requirements.txt`
de production pour garder l'image Docker minimale).

```bash
# Pré-requis (idempotent — à faire une fois après chaque rebuild d'image) :
docker exec arquantixrecovery-arquantix-api-1 \
  pip install -r /app/requirements-dev.txt

# Tous les tests mémoire :
docker exec -w /app arquantixrecovery-arquantix-api-1 \
  python3 -m pytest tests/test_assistance_memory_unit.py tests/test_assistance_memory_integration.py -v
```

Temps total : ~30 s.

Pour le développement local hors conteneur (uvicorn hôte) :

```bash
cd services/arquantix/api
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/test_assistance_memory_*.py -v
```

### 8.3. Stratégie d'isolation tests intégration

Les tests d'intégration utilisent la fixture `db` du `conftest.py` qui ouvre une transaction Postgres avec savepoint nested rollbacké en fin de test. Pour permettre aux fonctions du module (qui appellent `db.commit()`) de s'exécuter sans casser ce mécanisme, un wrapper `_NonClosingSession` :

- ignore `close()` (la fixture s'en charge)
- substitue `commit()` → `flush()` (matérialise les écritures dans le savepoint sans le consommer)

Cf. docstring de `_NonClosingSession` dans `tests/test_assistance_memory_integration.py` pour les détails.

---

## 9. Limitations connues

1. **Mode non-streaming non câblé.** La route `/chat/turn` (sans `/stream`) utilise toujours `_load_history` brut sans mémoire. C'est intentionnel (le mobile utilise exclusivement le streaming), mais à câbler si on rajoute un client non-streaming.

2. **Pas de backfill rétroactif.** Les conv créées avant la migration 146 (et qui n'ont reçu aucun nouveau tour depuis l'activation Phase 3) restent `summarized_until_turn = NULL`. À traiter via un script ad-hoc si besoin.

3. **Lock applicatif (mémoire process), pas distribué.** `_consolidation_locks: dict[UUID, asyncio.Lock]` sérialise les consolidations concurrentes sur la **même conv** dans **un seul process API**. Si on scale horizontalement (plusieurs replicas FastAPI), passer à un advisory lock Postgres (`SELECT pg_advisory_lock(hashtext('assistance_memory:' || conv_id::text))`).

4. **Cache identité PE Client.** Le bug pré-existant `client_required` (résolution `jwt_only` sans fallback DB) est patché localement dans `services/arquantix/api/services/assistance/routes.py::_require_client(auth, db)` — pas dans `auth_resolution.py`. À harmoniser globalement à terme.

5. **Pas de purge ni cap sur `assistance_long_memory.facts`.** Append-mostly avec dédup par `(type, value)`, mais une vie d'utilisation longue peut accumuler des dizaines de facts. Cap futur souhaitable (ex. top-N par recency × confidence).

---

## 10. Roadmap future

- **Orchestrateur multi-agents** (mentionné par le CTO) : router le tour utilisateur vers un agent spécialisé (épargne, marchés, KYC, juridique) **en exploitant la mémoire long-terme** pour décider du routing. À designer après stabilisation Palier 2.
- **Purge / TTL des facts** : retirer les facts à `confidence < 0.5` et `last_seen_at` ancien.
- **UI admin de la mémoire** : page CMS pour visualiser/éditer manuellement `conversation_summary` et `assistance_long_memory.facts` d'un client (transparence + correction).
- **Logs structurés JSON** : passer de `logger.warning("...")` à un logger structuré (cf. `structlog`) pour faciliter le parsing en agrégateur (Datadog, etc.).
- **Métriques Prometheus** : nombre de consolidations/min, taux de fallback heuristique, latence summarizer.
- **Tests E2E** : route `/chat/turn/stream` avec assertions DB sur summary/facts produits — actuellement testé manuellement (cf. logs DB confirmés du 02/05/2026, 5/5 facts utilisés cross-conv).

---

## 11. Référence rapide pour devs

| Action | Commande / fichier |
|---|---|
| Lire le code mémoire | `services/arquantix/api/services/assistance/memory.py` |
| Lire le prompt summarizer | `services/arquantix/api/services/assistance/prompts/summarizer_system.md` |
| Patch `service.py` (build_context + hook) | `services/arquantix/api/services/assistance/service.py` (chercher `_build_context` / `_schedule_consolidation`) |
| Migration Alembic | `services/arquantix/api/alembic/versions/146_assistance_long_term_memory.py` |
| Mirror Prisma | `services/arquantix/web/prisma/schema.prisma` (modèles `AssistanceConversation` + `PeClients`) |
| Tests unitaires | `services/arquantix/api/tests/test_assistance_memory_unit.py` |
| Tests intégration | `services/arquantix/api/tests/test_assistance_memory_integration.py` |
| Variables `.env` | `.env.arquantix`, `services/arquantix/api/.env`, `services/arquantix/web/.env`, `.env.example` |
| Doc | (ce fichier) `docs/arquantix/MEMORY.md` |
