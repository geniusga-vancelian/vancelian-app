# Agent `product` — Spec Phase 2c

> **Statut :** ✅ **livré** — Phase 2c en production locale, tests verts.
>
> **Dernière mise à jour :** 2026-05-03 (v1.0)
>
> **Objectif :** introduire un véritable agent `product` (par
> opposition au stub Phase 1) en charge des informations factuelles
> sur les produits Vancelian (délais SEPA / dépôt carte / retrait /
> KYC / swap, définitions Vault / Livret / SCPI), invoqué
> exclusivement via `consult_specialist` par les sub-agents
> `compliance.transactional` et `compliance.general`.
>
> **Tests :** `test_assistance_product_agent_unit.py` (≈11),
> `test_assistance_consult_purposes_unit.py` (24),
> `test_assistance_orchestration_chain_unit.py` (5).
>
> **Documents liés :**
> - `MULTI_AGENTS.md` §2.4 — placeholder de l'agent
> - `COMPLIANCE_TOPICS.md` §12 — orchestration multi-agents
> - `MULTI_AGENTS_RUNTIME.md` — runtime, autonomy, audit

---

## 0. TL;DR

L'agent `product` n'est **jamais routé** par le router top-level en
Phase 2c. Il est consulté **synchroniquement** par un sub-agent
compliance via le tool `consult_specialist` quand celui-ci a besoin
d'une information produit factuelle (un délai, une définition) à
intégrer dans sa propre réponse à l'utilisateur.

Le contenu est **lu en SQL** depuis la table `product_knowledge`
(seedée avec 10 fiches via la migration Alembic 149). Pas de RAG,
pas d'inférence : l'agent cite ou paraphrase une fiche figée
validée par l'équipe produit.

---

## 1. Pourquoi un vrai agent et pas juste un tool ?

Lors du design de Phase 2c, deux options ont été comparées :

| Option | Coût | Bénéfice | Verdict |
|---|---|---|---|
| **A** — Tool `read_product_knowledge` directement appelable par compliance | Très simple, pas d'agent | Compliance se mélange avec le ton produit, fuite de données client possible si on étend le tool | ❌ |
| **B** — Vrai agent `product` consulté via `consult_specialist` | +1 prompt, +1 sandbox runtime | Sandbox stricte (pas de PII), ton produit cohérent, RAG futur transparent côté caller | ✅ retenu |

L'option B garantit que **le sandbox produit restera étanche** quand
on ajoutera la Phase 5 (RAG vectoriel), parce que les sub-agents
compliance n'appelleront jamais directement les tools produit : ils
passent toujours par un `consult_specialist` qui isole le contexte.

---

## 2. Architecture

```
compliance.transactional / compliance.general
        │
        │ consult_specialist(target="product", purpose="product.delay.*", params={...})
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Sub-loop runtime (max_iter own, isolated history)              │
│                                                                 │
│  product agent                                                  │
│   ├── prompt: prompts/product_system.md                         │
│   ├── tools:                                                    │
│   │   ├── read_product_knowledge(slug)            (L0)          │
│   │   ├── list_product_knowledge_topics(topic?)   (L0)          │
│   │   └── ask_user_question                       (L0)          │
│   └── interdits:                                                │
│       ├── consult_specialist (anti-récursion)                   │
│       ├── handoff_to_agent                                      │
│       └── accès à toute donnée client (pas de tools compliance) │
└─────────────────────────────────────────────────────────────────┘
        │
        │ texte final (string)
        ▼
réinjecté comme tool_result dans la boucle compliance appelante
```

---

## 3. Données — table `product_knowledge`

### 3.1 Migration Alembic 149

```sql
CREATE TABLE public.product_knowledge (
  slug          VARCHAR(80)  PRIMARY KEY,
  topic         VARCHAR(40)  NOT NULL,
  title         VARCHAR(200) NOT NULL,
  body          TEXT         NOT NULL,
  metadata_json JSONB        NOT NULL DEFAULT '{}'::jsonb,
  is_active     BOOLEAN      NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_product_knowledge_topic ON public.product_knowledge(topic);
```

- `slug` : identifiant canonique stable (snake_case),
  ex. `deposit_delay_sepa_in`.
- `topic` : famille (`delay` | `definition` | `procedure`).
- `body` : contenu pédagogique court (200-500 mots), client-facing,
  validé éditorialement.
- `metadata_json` : extensible (région, prérequis…).
- `is_active=false` : soft-delete silencieux (le LLM ne voit plus la
  fiche).

### 3.2 Seed initial (10 entrées Phase 2c)

| Slug | Topic | Sujet |
|---|---|---|
| `deposit_delay_sepa_in` | delay | Délai d'un dépôt par virement SEPA |
| `deposit_delay_card` | delay | Délai d'un dépôt par carte bancaire |
| `deposit_delay_crypto_in` | delay | Délai d'un dépôt en crypto-actifs |
| `withdrawal_delay_sepa_out` | delay | Délai d'un retrait SEPA sortant |
| `withdrawal_delay_crypto_out` | delay | Délai d'un retrait en crypto-actifs |
| `kyc_review_typical_delay` | delay | Délai de validation d'un dossier KYC ou d'un justificatif |
| `swap_settlement_immediate` | delay | Délai de settlement d'un swap |
| `product_basics_vault` | definition | Définition d'un Vault Vancelian |
| `product_basics_livret_vancelian` | definition | Le compte d'épargne rémunéré Vancelian |
| `product_basics_scpi` | definition | Définition d'une SCPI |

> Les entrées sont **rééditables sans redeploy** : un PR sur la
> migration suivante ajoute / met à jour les rows. À terme, prévoir
> un mini-écran admin BO (Phase 4+).

### 3.3 Modèle SQLAlchemy

```python
class ProductKnowledge(Base):
    __tablename__ = "product_knowledge"
    __table_args__ = (
        Index("ix_product_knowledge_topic", "topic"),
        {"schema": "public"},
    )
    slug          = Column(String(80), primary_key=True)
    topic         = Column(String(40), nullable=False)
    title         = Column(String(200), nullable=False)
    body          = Column(Text, nullable=False)
    metadata_json = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    is_active     = Column(Boolean, nullable=False, server_default=text("true"))
    created_at    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

---

## 4. Tools

### 4.1 `read_product_knowledge(slug: str) -> dict | error`

- **Path :** `services/assistance/agents/tools/product/read_product_knowledge.py`
- **Autonomy :** L0 (read-only, pas d'effet de bord).
- **Comportement :**
  - `slug` vide → `{"error": "missing_slug"}`.
  - `slug` inexistant ou `is_active=false` →
    `{"error": "not_found", "slug": ...}`.
  - Sinon → `{"slug", "topic", "title", "body", "metadata", "updated_at"}`.

### 4.2 `list_product_knowledge_topics(topic?: str, limit?: int) -> list`

- **Path :** `services/assistance/agents/tools/product/list_product_knowledge_topics.py`
- **Autonomy :** L0.
- **Comportement :** retourne `[{slug, topic, title}, ...]` — minimal
  pour ne pas dump tout le contenu d'un coup, le LLM doit ensuite
  cibler avec `read_product_knowledge`.

### 4.3 `ask_user_question`

Hérité du shared toolset, autorisé pour clarifier un slug ambigu
quand l'utilisateur a écrit "mes délais" sans préciser entrant vs
sortant. Cas marginal — `consult_specialist` arrive normalement
déjà avec un purpose précis.

### 4.4 Tools interdits

- `consult_specialist` — anti-récursion stricte.
- `handoff_to_agent` — `product` est une feuille consultable, pas
  un nœud pivot.
- Aucun tool compliance ou portfolio (pas d'accès à `client_id`).

---

## 5. Prompt système

`services/assistance/prompts/product_system.md` — points clés :

- **Mission** : être l'unique source factuelle des informations
  produit. Pas de conseil d'investissement, pas d'opinion, pas
  d'extrapolation.
- **Procédure attendue** :
  1. Si appelé via `consult_specialist`, le purpose et les params
     déterminent le slug à lire (mapping suggéré dans le prompt).
  2. Lire la fiche via `read_product_knowledge`.
  3. Citer ou paraphraser fidèlement (≤ 3 phrases si caller =
     `compliance.transactional`).
  4. Ne **jamais** inventer un délai ou une caractéristique non
     présente dans la fiche → répondre "donnée non disponible".
- **Limites strictes** :
  - Pas de PII / pas de données client.
  - Pas de recommandation produit.
  - Pas d'URL externe, pas de deep-link (le caller compose les CTAs).

---

## 6. Catalog `consult_purposes` (V1)

Cf. `COMPLIANCE_TOPICS.md` §12.3 pour la liste exhaustive (5 entrées).
Chaque purpose mappe vers un slug ou une famille de slugs ; le
prompt produit donne au LLM la table de correspondance pour
résoudre déterministiquement.

---

## 7. Repository

`services/assistance/agents/repositories/product_repo.py` :

- `fetch_knowledge_by_slug(db, *, slug) -> dict | None` — best-effort,
  retourne None sur erreur DB.
- `list_known_slugs(db, *, topic=None, limit=100) -> list[dict]` —
  minimal `{slug, topic, title}`, hard-cap `limit ∈ [1, 200]`.

Aucune écriture exposée. Pas de cache en V1 (10 fiches, traffic
faible) — TTL Redis envisageable Phase 5.

---

## 8. Garde-fous & sécurité

| Risque | Mitigation |
|---|---|
| Fuite de PII via le sub-loop | Sandbox sans tools compliance, prompt qui interdit toute mention client |
| Hallucination de délai | Prompt impose la citation littérale du `body` ; tests unitaires sur fallback `not_found` |
| Récursion infinie produit→produit | `consult_specialist` absent du registry de `product` |
| Cascade hors-tour | `MAX_CHAIN_DEPTH=1`, `MAX_CONSULTATIONS_PER_TOUR=3` côté runtime |
| Désactivation silencieuse | Soft-delete `is_active=false` ; le LLM voit `not_found` et passe en fallback |

---

## 9. Hors scope Phase 2c

Reportés Phase 5+ :

- RAG vectoriel sur fiches PDF/MD (pgvector ou Qdrant). **Source MD
  amont déjà importée en Phase 1 stockage** (cf. §9.1) **et branchée
  au runtime en Phase 2 wiki** (cf. §9.2) via les tools
  `select_wiki_pages` + `read_wiki_page`. Le RAG vectoriel reste
  pertinent quand le volume dépassera ~1 000 fiches.
- Mini-écran admin BO pour éditer les fiches sans migration.
- I18n multi-locale du `body` (V1 = FR uniquement).
- Routing top-level vers `product` quand l'utilisateur pose
  directement une question produit (V1 : couvert par `default`
  agent + futur RAG).
- Agent `market` consultable de la même façon (V1 : `product` seul
  est éligible à `consult_specialist`).

### 9.1 Wiki MD importé en Phase 1 (2026-05-04)

Une base de **243 fiches markdown** a été importée depuis le vault
Obsidian `Vancelian Support (Chat WIKI LLM)` (snapshot du
2026-05-04, source : Jean Guillou).

| Élément | Emplacement | Statut |
|---|---|---|
| Wiki runtime | `services/arquantix/api/services/assistance/data/wiki/` | ⏳ stocké, pas branché |
| Audit cohérence Annexe 36 | `docs/arquantix/product-wiki/audit/` | ✅ référence |
| Feedback historiques (72) | `docs/arquantix/product-wiki/feedback/` | ✅ référence |
| Doc provenance & phasing | `docs/arquantix/product-wiki/README.md` | ✅ |

Phase 1 = **stockage seul**, aucun changement de code. La table SQL
`product_knowledge` (10 fiches canoniques courtes) **reste la
source utilisée par l'agent en Phase 2c**.

Phase 2 (cf. §9.2) ajoutera deux tools L0 — **livrée en
2026-05-04**.

### 9.2 Wiki MD branché au runtime — Phase 2 (2026-05-04)

Cohabitation des 2 sources de vérité :

| Source | Volume | Tool(s) | Use case |
|---|---|---|---|
| SQL `product_knowledge` | 10 fiches | `read_product_knowledge` + `list_product_knowledge_topics` | Délais courts (SEPA/KYC) + définitions canoniques (Vault/SCPI/Livret) — citation littérale par sub-agents compliance |
| Wiki MD | 243 fiches | `select_wiki_pages` + `read_wiki_page` | FAQ longues, mécaniques produit, exclusive offers, crypto, account, transfers, legal-compliance, … |

**Pattern de retrieval** : option C (cf. plan Phase 2) — pré-filtre
Python BM25-light sur le frontmatter `questions:` des 243 fiches.
Pas de vector DB. Pas d'appel LLM dans le retrieval. Le LLM
principal de l'agent `product` choisit lui-même la fiche à lire
parmi les 5 candidats retournés par `select_wiki_pages`.

**Tools L0 livrés** :

| Tool | Fichier | Comportement |
|---|---|---|
| `select_wiki_pages(question, top_k?, category?)` | `agents/tools/product/select_wiki_pages.py` | Score les 243 fiches contre les tokens de la question (matching sur `questions:` + `title` + `tags` du frontmatter). Retourne top_k ≤ 10 fiches avec `score` + `matched_questions_preview`. Pas de body. |
| `read_wiki_page(category, slug)` | `agents/tools/product/read_wiki_page.py` | Lit la fiche complète (frontmatter + sections `Short answer` + `Details`). Validation anti-path-traversal via whitelist `wiki_repo.ALL_CATEGORIES`. |

**Repository** : `agents/repositories/wiki_repo.py` — parseur
frontmatter maison (pas de PyYAML), cache RAM thread-safe TTL 5 min,
scoring keyword déterministe (testable). Premier hit après reload
≈ 150 ms (243 fiches), hits suivants O(1) ou O(N) sans I/O.

**Prompt système** : `prompts/product_system.md` v2 — intégration
complète des sections de `system-prompt-v2.md` (Jean Guillou) :
identity, language_and_register, app_ui_labels, vocabulary
(7 termes critiques + types de frais), grounding_rule,
account_limitation, response_rules, mandatory_disclaimers,
escalation_triggers, forbidden_patterns, self_check + 4 examples.
La section `## Sources de vérité — 2 couches` cadre la décision SQL
vs MD pour le LLM (option α : SQL d'abord pour les fiches courtes
canoniques, MD pour la couverture large).

**Sécurité** :

- Toutes les fiches MD sont par construction client-facing (validé
  éditorial Jean Guillou, cf. `CLAUDE.md` du vault source).
  **Aucun risque tipping-off.**
- Pas de PII dans le wiki.
- Tools L0 read-only, idempotents, jamais d'exception remontée
  (toujours `{"error": "..."}` en cas d'échec).

**Tests** : `tests/test_assistance_wiki_tools_unit.py` — 46 tests
verts (parsing frontmatter, sections markdown, scoring, tool spec,
registry wiring, sanity filesystem). **679 tests assistance** verts
au total après l'intégration → zéro régression.

**Garanties charte** :

- Aucune modif `.env*`, Docker, DB, Alembic, Prisma.
- Aucune nouvelle dépendance Python (parseur frontmatter maison
  ~80 lignes).
- Path legacy `ProductAgent._collect_tool_context` (heuristique
  V1) **non modifié** — kill-switch via `ASSISTANCE_RUNTIME_LOOP_AGENTS`.

---

## 10. Versioning

| Date | Version | Phase | Changements |
|---|---|---|---|
| **2026-05-03** | **1.0** | **Phase 2c livrée** | **Création de l'agent `product` (prompt + tools), table SQL `product_knowledge` (migration 149, 10 seeds), invocation via `consult_specialist`. Garde-fous structurels (pas de `consult_specialist`/`handoff_to_agent` côté product). 530 tests assistance verts.** |
| **2026-05-04** | **1.1** | **Phase 1 wiki MD livrée** | **Import de 243 fiches markdown depuis le vault Obsidian source dans `assistance/data/wiki/` (stockage seul, aucun branchement runtime). Audit cohérence Annexe 36 + 72 feedbacks copiés dans `docs/arquantix/product-wiki/`. Phase 2 (branchement runtime via `select_wiki_pages` + `read_wiki_page`) en PR séparée.** |
| **2026-05-04** | **1.2** | **Phase 2 wiki branchée au runtime** | **Repo `wiki_repo.py` (parsing frontmatter maison + cache TTL 5 min + scoring keyword Karpathy-style). 2 tools L0 livrés : `select_wiki_pages(question, top_k?, category?)` (pré-filtre top 5 sur les 243 fiches) + `read_wiki_page(category, slug)` (lecture complète). Prompt système v2 enrichi de `system-prompt-v2.md` (vocabulary, grounding_rule, account_limitation, response_rules, mandatory_disclaimers, escalation_triggers, forbidden_patterns, self_check, 4 examples). Cohabitation SQL/MD : SQL d'abord pour les fiches courtes canoniques, MD pour la couverture large. 46 tests wiki + 679 tests assistance globaux verts → zéro régression. Aucune modif env/DB/Docker, aucune nouvelle dépendance Python.** |

> **Règle :** toute évolution du catalog `consult_purposes`, du
> schéma `product_knowledge`, ou des garde-fous structurels **doit**
> incrémenter cette version.
