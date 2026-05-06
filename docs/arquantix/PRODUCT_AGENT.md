# Agent `product` — Spec Phase 2c

> **Statut :** **livré** — Phase 2c + wiki Phase 2 + guard-rail v1.3 +
> slider Crypto Bundles v1.4 + dedup + slot topic + hot-path
> + cleanup SQL + fiche catalogue + garde-fou cross-repo +
> Karpathy LLM-as-retriever (v1.4 patch 3) en production locale,
> 1067 tests verts.
>
> **Dernière mise à jour :** 2026-05-04 (v1.4 patch 3 — cleanup
> `product_basics_scpi`/`livret`/`mandate`, fiche
> `vancelian_product_catalog`, garde-fou `read_wiki_page` sur
> slugs SQL, retriever LLM-as-retriever sur le wiki MD)
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

### 9.2bis Wiki en tool partagé — Lot 1 (2026-05-06)

**Constat brainstorming 2026-05-06** (cf. discussion Wiki commun) :
historiquement les tools `select_wiki_pages` + `read_wiki_page`
n'étaient exposés qu'aux agents `product` et `trust`. Conséquences
observées :

- L'agent `compliance.transactional` doit improviser face à
  « pourquoi mon virement n'est pas arrivé ? » alors que la fiche
  wiki `transfers-cards/sepa-deposit-delays.md` répond précisément
  (J+0 à J+2 ouvrés). Risque de paraphrase approximative ou
  d'hallucination.
- L'`advisor` doit déléguer chaque question produit au specialist
  via `consult_specialist(target=product, …)` — overhead latence et
  tokens.
- Le `market` ne peut pas cadrer ses commentaires sur les concepts
  (TVL, swap, custody) sans recourir à sa connaissance LLM brute.

**Décision** : exposer les 2 tools wiki à **tous les sub-agents
métier** :

| Agent | Avant | Après Lot 1 |
|---|---|---|
| `product` | ✅ | ✅ (inchangé, voit `audience: internal`) |
| `trust` | ✅ | ✅ (inchangé) |
| `compliance.registration` | ❌ | ✅ (audience filtré → `client`) |
| `compliance.remediation` | ❌ | ✅ (audience filtré → `client`) |
| `compliance.transactional` | ❌ | ✅ (audience filtré → `client`) |
| `compliance.general` | ❌ | ✅ (audience filtré → `client`) |
| `advisor` | ❌ | ✅ (audience filtré → `client`) |
| `market` | ❌ | ✅ (audience filtré → `client`) |
| `compliance` (top-level dispatcher) | ❌ | ❌ (reste minimal au tour 0) |
| `default` | ❌ | ❌ (fallback minimal) |

**Garde-fous** :

1. **Filtre `audience`** dans `select_wiki_pages.execute` et
   `read_wiki_page.execute` (cf.
   `_AUDIENCE_PRIVILEGED_AGENT = "product"`). Les fiches
   `audience: internal` (notes éditoriales, cas opérationnels,
   contenu non-publiable) sont **invisibles** pour tout agent ≠
   `product`. Côté `select`, elles sont retirées du `matches` (avec
   compteur `audience_filtered_out` pour observabilité). Côté `read`,
   on retourne `{"error": "audience_restricted", "hint": …}` — le
   LLM peut requêter une fiche client équivalente ou consulter
   `product` via `consult_specialist`.

2. **Quota par tour** dans `runtime/agent_loop.py` —
   `MAX_WIKI_CALLS_PER_TOUR = 6` (cumulant `select_wiki_pages` +
   `read_wiki_page`). Au-delà, le runtime court-circuite avec un
   tool_result `wiki_quota_exceeded` (mêmes mécaniques que
   `consult_limit_reached`). Évite qu'un LLM mal calibré épuise le
   budget tokens en explorant 12 fiches tangentielles. Le
   `DEDUPABLE_TOOLS` complémente déjà la dédup d'args identiques.

3. **Borne globale `MAX_ITER`** + **timeout** runtime existants
   (inchangés) restent les filets de dernière instance.

**Pas de déplacement de fichiers** : les modules restent dans
`agents/tools/product/select_wiki_pages.py` et `…/read_wiki_page.py`,
mais sont importés explicitement par `agents/tools/registry.py`
dans les listes d'autres agents (cf. `_COMPLIANCE_BASE_TOOLS`).
Cette décision design (pas de move physique) garantit zéro casse
des imports/tests externes pendant la migration.

**Tests** : `tests/test_assistance_wiki_tools_unit.py`
(`TestRegistrySharedWikiLot1`, `TestSelectWikiPagesAudienceGuard`,
`TestReadWikiPageAudienceGuard`) +
`tests/test_assistance_runtime_wiki_quota_unit.py` (5 tests).
**1502 tests assistance verts** au total après livraison.

### 9.2ter Widgets commerciaux & garde-fou stop_pushing — Lot 3 (2026-05-06)

**Constat brainstorming Wiki commun (suite Lot 2)** : les 3 widgets
commerciaux exposés au LLM côté product (`show_instrument_card`,
`show_crypto_bundles`, `show_bundle_detail`) restaient invocables
même quand le client était en FEAR/ANGER. Bug qualité pur : un
client paniqué qui demande « comment va Bitcoin ? » se voyait
pousser un CTA Acheter au lieu d'une rassurance verbale.

**Décision** : brancher `should_stop_pushing(ctx)` (helper Lot 2)
sur les 3 widgets commerciaux uniquement. Court-circuit **avant**
toute requête DB / marché (gain latence + tokens log) avec un
payload typé exploitable par le LLM.

| Tool | Garde-fou stop_pushing ? | Raison |
|---|---|---|
| `show_instrument_card` | ✅ | CTAs Acheter / Vendre = push commercial |
| `show_crypto_bundles` | ✅ | Slider catalogue + CTAs Investir |
| `show_bundle_detail` | ✅ | Fiche bundle + CTAs Voir / Investir |
| `show_top_movers` (market) | ❌ | Informationnel : pas de CTA d'achat |
| `show_featured_articles` (market) | ❌ | Informationnel : articles à la une |

**Payload retourné** quand `should_stop_pushing(ctx) == True` :

```json
{
  "error": "stop_pushing_active",
  "emotional_intent": "fear",
  "hint": "Le client est en état émotionnel négatif (FEAR/ANGER)…
           Réponds en texte avec rassurance + preuves
           (régulation, custody, sécurité)…"
}
```

**Pas de filtrage CTAs** (vs blocage complet) : un client en FEAR
n'a pas besoin de moins de boutons, il a besoin que le bot **ne
pousse pas du tout** un produit ce tour-ci. Filtrer la moitié des
CTAs n'aurait pas adressé le vrai besoin.

**Pas d'extension du registry agents** dans Lot 3. Étendre par ex.
`show_instrument_card` à `compliance.transactional` créerait un
risque de push commercial dans un contexte transactionnel —
l'esprit Lot 3 est le renforcement de la pertinence (anti-push) et
non l'élargissement du push.

**Tests** : `tests/test_assistance_widgets_stop_pushing_unit.py`
(20 tests : court-circuit FEAR/ANGER + objective explicite,
ordre du garde-fou, payload shape, non-blocage curiosity, garde
sur les widgets informatifs préservé).

### 9.2quater Topic mémoire cross-tour exposé aux tools — Lot 4 (2026-05-06)

Lot 4 expose `current_topic` (déjà persisté côté DB et lu par le
router depuis Phase 2 wiki v1.4) aux tools des sub-agents via
`ToolContext.current_topic`. Cf. `MULTI_AGENTS_RUNTIME.md`
§ 2.3ter pour le détail. Côté product, un futur lot pourra
brancher `topic_matches_product_code(ctx, code)` sur
`show_bundle_detail` pour détecter une dérive de sujet (« on parle
de TOP5, le LLM vient d'invoquer ALT5 »).

### 9.2quinquies Observabilité runtime_metrics — Lot 5 (2026-05-06)

Lot 5 expose dans le done event SSE un champ `runtime_metrics`
agrégeant les blocages silencieux du tour
(`wiki_quota_blocked_count`, `audience_filtered_out_total`,
`stop_pushing_blocked_count`, etc.). Cf. `MULTI_AGENTS_RUNTIME.md`
§ 2.3quater pour le schéma exact et l'usage admin UI.

### 9.3 Guard-rail anti-hallucination — v1.3 (2026-05-04)

**Constat post-prod (analyse de la conv `aef5923a` — 42 turns,
24 h)** : le LLM `gpt-4o-mini` ne respecte pas systématiquement
l'instruction « tu DOIS appeler un tool de lecture avant de
répondre » du `product_system.md` v2. Sur les 8 turns Phase 2 de
cette conv, **3 zappent les tools** :

| Turn | Question | Tools appelés | Résultat |
|---|---|---|---|
| 30 | « Découvrir un produit Vancelian » | aucun | 1 332 chars depuis la connaissance LLM |
| 32 | « Vancelian ne propose pas l'invest crypto ? » | aucun | **Hallucination** : « pas d'invest direct en crypto » (faux, contredit en turn 34) |
| 42 | « quels sont les meilleurs dispo sur l'app ? » | `select_wiki_pages × 2`, **0** read | Réponse composée depuis les **titres** seuls |

**Solution livrée** — guard-rail dans `agent_loop.py` :

Au moment où l'agent `product` produit une réponse finale (sans
nouveau tool_call), le runtime vérifie :

1. Si **aucun** tool de lecture (`read_product_knowledge`,
   `read_wiki_page`, `show_instrument_card`) n'a été appelé
   pendant ce tour → injection de
   `PRODUCT_GUARDRAIL_HINT_NO_READ`.
2. Sinon, si `select_wiki_pages` a été appelé sans `read_wiki_page`
   ni `read_product_knowledge` derrière → injection de
   `PRODUCT_GUARDRAIL_HINT_SELECT_WITHOUT_READ`.

Dans les deux cas, le brouillon assistant + le hint system sont
appendés à `messages` et la boucle relance le LLM. **Borné à 1
seul retry** par tour pour éviter les boucles infinies si le LLM
ignore le hint (cas rare). Si le 2e essai produit toujours une
réponse non-sourcée, on l'accepte (mieux qu'un fallback vide).

**Périmètre** :

- ✅ Activé pour l'agent `product` (top-level **et** sub-agent)
- ❌ Pas appliqué en sous-loop `consult_in_progress=True` (un
  spécialiste consulté peut légitimement répondre depuis son
  seul prompt sur des questions définitionnelles)
- ❌ Pas appliqué aux autres agents (compliance, advisor, market,
  router) — ils ont leur propre logique de tools.

**Configuration** :

| Var | Défaut | Effet |
|---|---|---|
| `ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED` | `true` | Active le guard-rail |
| `ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED=false` | — | Comportement legacy < 2026-05-04 (rollback rapide en cas d'incident) |

**Observabilité** :

```
WARN agent_loop.product_guardrail_triggered iter=0
    tools_called=- reason=no_read conv=<uuid> corr=<corr>
WARN agent_loop.product_guardrail_triggered iter=0
    tools_called=select_wiki_pages reason=select_without_read
    conv=<uuid> corr=<corr>
```

→ surveiller la fréquence du déclenchement en prod : > 30 % du
trafic `product` indique soit un prompt v2 trop permissif, soit
un changement de modèle (ex. passage à un LLM moins rigoureux)
qui mériterait un upgrade vers `gpt-4o`.

**Tests** : `tests/test_assistance_runtime_loop_unit.py` —
**18 nouveaux tests** (`TestProductGuardrailHelper` ×7,
`TestProductGuardrailIntegration` ×7,
`TestProductGuardrailConfig` ×4). Couvre :

- Helper pur `_check_product_guardrail` (chaque combinaison de
  tools).
- Intégration `run_agent_loop` : retry triggered, retry borné à
  1, env-disable, pas-applicable-aux-autres-agents,
  pas-applicable-en-consult.
- Lecture env var `ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED`
  (truthy/falsy).

### 9.4 Slider Crypto Bundles — v1.4 (2026-05-04)

**Constat post-prod (analyse conv `e5133711`)** : quand le client
clique « Découvrir les différents bundles disponibles » dans un QCM
router, l'agent `product` répond uniquement par **un texte
markdown** (lecture wiki) — pas de moyen visuel de lister les
bundles concrets disponibles dans le catalogue Vancelian. L'attente
utilisateur explicite : retrouver le slider **Crypto Bundles** déjà
affiché côté markets/home, mais en bulle chat.

**Solution livrée** — nouveau tool L0 `show_crypto_bundles()` (sans
paramètre, idempotent) :

| Composant | Source / cible |
|---|---|
| Tool Python | `services/assistance/agents/tools/product/show_crypto_bundles.py` |
| Source DB | `services/portfolio_engine/products/catalog.py::CatalogService.get_public_catalog(product_type='crypto_bundle')` (réutilisé tel quel — **0 modif** côté `portfolio_engine`) |
| Embed type | `crypto_bundles_card` (push dans `ctx.embeds_to_emit`) |
| Cap | 8 bundles maxi par embed |
| Guard-rail | Inscrit dans `PRODUCT_KNOWLEDGE_READ_TOOLS` — équivalent fonctionnel de `show_instrument_card` |

**Deep-links whitelisted** (cf. `action_cta_catalog`) :

- `view_bundle_detail` → `vancelian://app/bundle/{id}` (tap card →
  `ProductPreviewScreen`).
- `invest_bundle` → `vancelian://app/bundle/{id}/invest` (bouton
  « Investir » → `BundleInvestFlowController.start` après
  enrichissement `getBundleCatalog` pour résoudre le
  `portfolioId`).

**Côté mobile** : nouvel embed `CryptoBundlesCardEmbed` qui délègue
le rendu à `AssetsBundlesModule` (réutilisé tel quel) — **réplique
visuelle exacte** du widget `CryptoBundlesWidget` markets, ce qui
garantit la cohérence design même quand le DS évoluera.

**Documentation prompt** : section *« Slider de Crypto Bundles —
Phase 2 wiki »* ajoutée à `product_system.md` — guide le LLM sur
quand appeler / ne pas appeler le tool, et notamment lui interdit
d'inventer un bundle si `bundles_count == 0`.

**Tests** : nouveau fichier
`tests/test_assistance_show_crypto_bundles_unit.py` — **30 tests**
couvrant la SPEC (4), le cas nominal (4), edge cases (4), helpers
(4), action catalog whitelist (12 incluant param check), guard-rail
intégration (3) + maj `test_assistance_wiki_tools_unit.py` pour
asserter `len(tools) == 7` côté `product` (+ exclusion explicite
sur les autres agents).

### 9.5 Refonte design `instrument_detail_card` — v1.4 (2026-05-04)

**Constat client (UX feedback)** : la carte instrument du chat
n'était pas alignée sur la partie haute de la page détail
([`CryptoDetailScreen` / `LayoutPageInstrumentDetail`]). Quatre
écarts visuels :

1. Mini-sparkline 96 px **avec zone area** (vs line chart pur du
   hero), sans ligne horizontale + puce de prix de départ, sans
   sonar point en bout, sans puces de période, sans disclaimer
   mid-rate.
2. Pas de tag **« Crypto »** au-dessus du titre.
3. Avatar = `Image.network` brut (pas le `CryptoAvatar` du DS qui
   gère SVG bundled → réseau → fallback icône).
4. Chart pas bord-à-bord du module.

**Solution livrée** — refonte complète du widget
`InstrumentDetailCardEmbed` en `StatefulWidget` qui **réutilise
strictement** les composants du hero détail instrument :

| Composant hero | Réutilisé dans le chat embed |
|---|---|
| `ChartAssetModule(instrumentDetailStyle: true)` | ✅ idem (line chart pur, ligne horizontale + puce, sonar, period chips, disclaimer) |
| `CategoryBadge('Crypto')` | ✅ idem |
| `CryptoAvatar(size: small)` | ✅ idem |
| `InstrumentDetailHeroPerformanceRow` | ✅ idem |
| `InstrumentDetailHeroCtaRow` + `AppPrimaryButton(arrow_up/down)` | ✅ idem |
| `MarketDataApi.getChartHistory` | ✅ idem (1j/1s/1m/1a/5a) |

**Extension rétrocompatible** : `ChartAssetModule` accepte une nouvelle
prop optionnelle `chartContainerWidth` (override de
`MediaQuery.size.width`) — null = comportement actuel page détail
(bord-à-bord écran), valeur = bord-à-bord du module parent (bulle chat).
Pas de régression sur la page détail (la prop n'est passée que par
l'embed chat).

**Différence assumée vs page détail** :

- Tout est encapsulé dans un module blanc (radius bubble assistant +
  shadow). Chart bord-à-bord du module, pas de l'écran.
- Pas de boutons header (favoris / alertes / orders).

**v1.4 patch (2026-05-04 – instrument live)** : ajout du **WebSocket
streaming** (`MarketDataWsService`) dans le widget chat, exactement
comme la page détail instrument. Le tick live (`QuoteUpdate.price`)
prime sur le dernier close des bougies pour la ligne « prix +
performance », ce qui permet à la bulle chat de rester à jour si le
client la garde ouverte. `dispose()` déconnecte proprement le WS.

**Comportement** :

- Au mount → fetch `getChartHistory(symbol, period='1j')` (default).
- Toggle des period chips → re-fetch + maj du libellé période + perf
  recalculée (premier vs dernier close).
- Toggle ligne ↔ chandeliers via le bouton du module chart.
- CTAs Acheter/Vendre dispatchent vers `AssistanceDeepLinkResolver`
  (deep-links `buy_instrument` / `sell_instrument`).

**Fallback** : tant que les bougies ne sont pas chargées, on affiche
le prix backend (EUR ou USD) + la perf 24 h fournie dans le payload
backend (`change_24h_abs/pct`). Une fois les bougies arrivées, on
bascule sur USD + perf calculée sur la période sélectionnée.

**Fichiers touchés** :

- `services/arquantix/mobile/lib/features/markets/presentation/widgets/chart_asset_module.dart`
  → +1 prop `chartContainerWidth` (rétrocompatible).
- `services/arquantix/mobile/lib/features/search/presentation/widgets/instrument_detail_card_embed.dart`
  → réécriture complète (Stateful, charge candles, délègue à
  `ChartAssetModule(instrumentDetailStyle: true)`).

`flutter analyze` clean sur les deux fichiers (0 nouveau warning).

### 9.6 Bundle detail + filtrage liste + WS instrument — v1.4 patch (2026-05-04)

**Constat client (UX feedback)** : quatre écarts résiduels après la
livraison v1.4 initiale :

1. La bulle chat instrument **n'est pas live** (vs page détail qui
   stream le ticker Binance) — incohérent quand le client laisse la
   bulle ouverte plusieurs minutes.
2. Pas d'équivalent **bulle « bundle detail »** : si le client cible
   un bundle nommé (« parle-moi du TOP5 »), on ne peut afficher que
   la liste — pas de fiche détaillée avec chart de performance.
3. Le slider liste a un **titre de module** (« Crypto Bundles ») au
   dessus des cards qui fait double-emploi avec le texte d'intro du
   LLM, et la **taille des cards** diffère de la page markets
   (densité visiblement différente). En plus, l'**image de cover ne
   s'affiche pas** dans le chat.
4. Quand le client précise *plusieurs* bundles ciblés (« les bundles
   à dominante BTC »), le slider montre **tout** le catalogue au lieu
   du sous-ensemble demandé.

**Solutions livrées** :

| Item | Solution |
|---|---|
| (1) Stream live instrument | `InstrumentDetailCardEmbed` ouvre `MarketDataWsService.subscribe([providerSymbol])` au mount → tick `QuoteUpdate.price` prime sur `_candles.last.close` pour `_currentPriceUsd`. `dispose()` déconnecte. Identique au pattern `CryptoDetailScreen`. |
| (2) Bundle detail card | Nouveau tool L0 backend `show_bundle_detail(product_code OR bundle_id)` (consomme `CatalogService.get_public_catalog`, idempotent, ajouté à `PRODUCT_KNOWLEDGE_READ_TOOLS`). Nouveau widget Flutter `BundleDetailCardEmbed` qui réplique la **partie haute** de `BundleInstrumentDetailHero` : tag « Crypto Bundle » + `BundleTickerAvatarRow` (allocations) + titre/description + `InstrumentDetailHeroPerformanceRow` (alimentée par `BundlePerformanceChartModule.onHeroMetricsChanged`) + chart bord-à-bord (`BundlePerformanceChartModule(embedInstrumentHero: true, chartContainerWidth: ...)`) + CTAs « Voir détail » + « Investir ». |
| (3a) Pas de titre dans la liste | `CryptoBundlesCardEmbed` passe `title: ''` à `AssetsBundlesModule`. |
| (3b) Taille cards = markets | `visibleCardsCount: 1.4` (strictement identique au widget markets). |
| (3c) Image cover affichée | `CryptoBundlesCardEmbed` devient `Stateful`, fetch `ProductCatalogApi.getDisplayConfigs()` au mount, applique `headerMediaUrl` + `cardTitle` + `performance1d` + tri par `sortOrder` (le payload backend Python n'a pas accès à la table Prisma `portfolioProductConfig` côté Web/BFF). |
| (4) Filtrage liste | `show_crypto_bundles` accepte un paramètre **optionnel** `product_codes: list[str]` ; si fourni, seul ce sous-ensemble est retourné. En cas de zéro match, le tool renvoie `available_product_codes` pour permettre au LLM de proposer une alternative au client. |

**Extension `BundlePerformanceChartModule`** : nouvelle prop
optionnelle `chartContainerWidth` (override de
`MediaQuery.size.width`) — null = bord-à-bord écran (page détail
bundle), valeur = bord-à-bord du module parent (bulle chat).
Rétrocompatible.

**Routing LLM** : section *« Bundles Vancelian — `show_crypto_bundles`
vs `show_bundle_detail` »* enrichie dans `product_system.md` avec une
règle de tri **CRITIQUE** sur 3 cas (1 bundle nommé →
`show_bundle_detail` ; bundles ciblés multiples →
`show_crypto_bundles(product_codes=[...])` ; tout le catalogue →
`show_crypto_bundles()` sans param).

**Tests** : 5 nouveaux tests sur le filtrage `show_crypto_bundles`
+ nouveau fichier `test_assistance_show_bundle_detail_unit.py` (24
tests : SPEC, nominal, edge cases, helper, registry, guard-rail).
**935 tests assistance globaux verts → zéro régression.**

**Fichiers touchés** :

- Backend : `services/assistance/agents/tools/product/show_crypto_bundles.py` (filtre), `services/assistance/agents/tools/product/show_bundle_detail.py` (nouveau), `services/assistance/agents/tools/product/__init__.py`, `services/assistance/agents/tools/registry.py`, `services/assistance/agents/runtime/agent_loop.py` (guard-rail), `services/assistance/prompts/product_system.md`.
- Flutter : `features/markets/presentation/widgets/bundle_performance_chart_module.dart` (+1 prop), `features/search/presentation/widgets/instrument_detail_card_embed.dart` (+WS), `features/search/presentation/widgets/crypto_bundles_card_embed.dart` (refondu Stateful), `features/search/presentation/widgets/bundle_detail_card_embed.dart` (nouveau), `features/search/data/chat_api.dart` (+helper `singleBundleItem`), `features/search/presentation/screens/search_screen.dart` (case `bundle_detail_card`).

`flutter analyze` clean sur tous les fichiers modifiés (0 nouveau warning).

### 9.7 Router QCM contextualisé + advisor pour « profil » — v1.4 (2026-05-04)

**Constat post-prod (conv `e5133711` turn 3)** : « quel bundle est
le plus adapté à mon profil ? » → router émet un QCM Niveau 2 avec
4 labels génériques (« Conseils pour mes placements », « La
situation des marchés », etc.) qui ne mentionnent pas « bundle ».
Le client a l'impression qu'on a oublié son sujet.

**Solution livrée** (prompt-only — `router_system.md`) :

1. **Sous-cas règle 2 « profil sur produit Vancelian nommé »** :
   quand un produit Vancelian propriétaire est cité (Bundle, Coffre
   Flexible, etc.) **et** que le client demande lequel **lui**
   correspond, route_to(advisor) direct (≥ 0.8) — la règle 2 prime
   sur la règle 0bis. **3 nouveaux exemples calibrés** ajoutés
   (« le plus adapté à mon profil », « me convient le mieux »,
   « lequel je devrais choisir »).
2. **Règle de contextualisation `ask_clarification`** : quand
   `recent_turns` mentionne un produit / instrument nommé, **chacun**
   des labels d'options DOIT explicitement reprendre ce sujet
   (« Adapter un bundle à mon profil » plutôt que « Conseils pour
   mes placements »). Exemple anti-pattern + pattern positif fournis.

**Tests** : nouvelle classe
`TestRouterPromptProfileAdvisorAndContextualQcm` (6 tests) qui
asserte le contenu textuel du prompt enrichi.

### 9.9 Catalogue produit canonique + Karpathy retriever (v1.4 patch 3 — 2026-05-04)

**Constat post-prod (analyse conv `534d545b`, 7 turns, 27 tool calls)** :
sur une question simple « parle moi des offres exclusives » et son
extension « quels sont les produits Vancelian ? », le bot enchaîne
4 défaillances majeures :

1. **0 match wiki** sur 4 appels `select_wiki_pages(category="exclusive-offers")`
   alors que la catégorie contient 34 fiches. Le scoring **keyword pur**
   ne traduit pas FR↔EN (66 % du wiki en anglais).
2. **MAX_ITER atteint** au turn 8 (« service indisponible ») après
   16 tool calls dans un seul tour qui boucle sur des slugs introuvables.
3. **Hallucination « Vancelian propose des SCPI »** au turn 10 : la
   fiche SQL `product_basics_scpi` a un titre affirmatif (« Investir en
   SCPI sur Vancelian ») mais un corps purement définitionnel — le LLM
   l'ajoute à la gamme. Idem `product_basics_livret_vancelian` et
   `product_basics_managed_mandate`.
4. **Confusion runtime SQL ↔ wiki** : 3 appels à
   `read_wiki_page(slug="product_basics_*")` retournent `not_found`
   alors que ces slugs vivent dans la table SQL `product_knowledge`.

Le bot du copain (Jean Guillou, cf. `wiki/chatbot-spec.md` v2.1)
n'a aucun de ces défauts car il utilise le **pattern Karpathy
LLM-as-retriever** : un LLM Haiku reçoit `index.md` entier (310
lignes, 222 fiches résumées) + la question, et retourne 3-5 slugs.

**Solutions livrées (4 lots)** :

#### Lot 1 — Cleanup SQL `product_knowledge` (migration 151)

  * **Soft-delete** (`is_active=false`) de 3 fiches non-canoniques :
    `product_basics_scpi`, `product_basics_livret_vancelian`,
    `product_basics_managed_mandate`. Aucun de ces produits n'est
    proposé par Vancelian.
  * Migration purement additive (UPDATE + INSERT, aucun DROP).

#### Lot 2 — Fiche `vancelian_product_catalog`

  * Nouvelle entrée canonique dans `product_knowledge` qui décrit
    les **5 familles** Vancelian (Coffres, Offres Exclusives, Crypto
    Baskets, Trading spot, Compte EUR + carte VISA) avec une section
    « Ce que Vancelian ne propose PAS » qui mentionne explicitement
    SCPI / livret / mandat.
  * Patch `product_system.md` : règle PRIORITÉ ABSOLUE — sur question
    catalogue (« quels produits ? », « la gamme », « découvrir
    Vancelian »), appeler EN PREMIER `read_product_knowledge('vancelian_product_catalog')`.
  * Texte calibré sur la réponse référence du chatbot Slack v3 du
    wiki source.

#### Lot 3 — Garde-fou cross-référentiel `read_wiki_page`

  * Détection préfixes SQL (`product_basics_`, `deposit_delay_`,
    `withdrawal_delay_`, `kyc_`, `swap_`, `kind_`) + whitelist
    `vancelian_product_catalog`. Si match → retourne
    `{"error": "wrong_repo", "use_tool": "read_product_knowledge",
    "hint": "..."}` au lieu de `not_found`. Le LLM voit le hint et
    sait quoi faire.
  * Patch prompt : règle explicite « les slugs `product_basics_*`,
    `deposit_delay_*`, etc. sont SQL — utilise `read_product_knowledge` ».
  * Tests : 16 dans `test_assistance_read_wiki_page_guard_unit.py`.

#### Lot 4 — Karpathy LLM-as-retriever sur le wiki MD

  * Nouveau module `services/assistance/agents/repositories/wiki_llm_retriever.py` :
    construit un catalogue compact (1 ligne / fiche, ~6 000 tokens),
    appelle un LLM avec un tool `return_selected_slugs` qui force la
    sortie structurée.
  * Wire dans `select_wiki_pages.execute` : LLM-as-retriever **par
    défaut**, fallback transparent sur le scoring keyword si l'appel
    LLM échoue / retourne 0 slug exploitable / désactivé via env var.
  * Sentinel `__use_sql_catalog__` : si la question vise la **gamme
    globale**, le retriever LLM peut renvoyer ce slug spécial → le
    tool retourne `via: llm_sql_hint` qui pousse le LLM caller à
    utiliser `read_product_knowledge('vancelian_product_catalog')`.
  * **Cohérence catégorie** : si le caller passe un `category=...`,
    on filtre les matches LLM dans cette catégorie *si* au moins
    1 match reste. Sinon on garde tout (le LLM a parfois un meilleur
    choix transverse).
  * Configuration env :
      - `ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED=true` (défaut).
      - `ASSISTANCE_WIKI_LLM_RETRIEVER_MODEL=<override>` (défaut =
        modèle agent product = `gpt-4o-mini` ou autre selon env).
      - `ASSISTANCE_WIKI_LLM_RETRIEVER_MAX_SLUGS=5`.
  * Cache catalogue partagé avec TTL `wiki_repo._cache_ttl_seconds()`
    = 300 s. Lazy-build, 1 lock pour éviter rebuild concurrent.
  * Tests : 14 dans `test_assistance_wiki_llm_retriever_unit.py`.

**Tests** :
  * `test_assistance_wiki_llm_retriever_unit.py` — 14 tests (build
    catalogue, cas nominaux, sentinel SQL, erreurs LLM, intégration).
  * `test_assistance_read_wiki_page_guard_unit.py` — 16 tests
    (détection slugs SQL, redirection, slugs wiki normaux préservés).
  * `test_assistance_product_catalog_seed_unit.py` — 9 tests (état
    DB après migration 151, sanity du body catalogue).
  * **1067 tests assistance globaux verts** (vs 1017 avant) — **zéro
    régression** après ajustement de 2 tests legacy
    (`test_assistance_wiki_tools_unit.py`) qui désactivent
    explicitement le retriever LLM pour tester le fallback keyword.

**Rétrocompatibilité** :
  * Migration 151 purement additive (UPDATE + INSERT).
  * Si `ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED=false`, le tool
    retombe sur le keyword scoring d'origine (zéro changement de
    comportement vs avant patch 3 sur le `via: keyword` path).
  * Garde-fou `wrong_repo` ne casse aucun appel légitime — uniquement
    les appels qui retournaient déjà `not_found`.

**Aucune modif env/Docker.** Lots actifs immédiatement après restart
container API.

### 9.8 Stabilité conversationnelle — dedup + topic + hot-path (v1.4 patch 2 — 2026-05-04)

**Constat post-prod** (analyse conv `5bef01e9`, 5 turns) : malgré les
patchs 9.6 et 9.7, 3 problèmes résiduels observés :

  1. **Routeur qui flippe sur mot-clé isolé** — turn 3, le user envoie
     « précisément les perf sont bonnes sur ce bundle ? » (28 chars,
     déictique fort « ce bundle »). Le LLM router classifie sur
     `market` à cause du keyword « perf », casse la conversation
     produit en cours.
  2. **Tool dupliqué dans le même turn** — turn 4, le LLM appelle
     `show_crypto_bundles()` × 2 avec exactement les mêmes args dans
     le même turn (compte le 1er résultat comme insuffisant et
     re-tente). Tokens / latence / DB gaspillés. Le 2ᵉ appel
     contribue à déclencher le guard-rail à tort.
  3. **Sujet « en cours » non matérialisé** — `recent_turns` (4
     derniers messages bruts) ne suffit pas au LLM pour comprendre
     que « ce bundle » désigne TOP_5 quand l'ancrage est ≥ 2 tours
     en arrière.

**Solutions livrées (3 mécanismes complémentaires, déterministes,
cheap, observables — voir `MULTI_AGENTS.md` § 8.5 pour les détails
de bas niveau)** :

  * **9.8.1 Dédoublonnage runtime** (`agent_loop.py` ::
    `tool_call_cache`) — cache local au turn `(tool_name, frozen_args)
    → result`. Au 2ᵉ appel identique sur un tool de
    `DEDUPABLE_TOOLS` (whitelist d'idempotents read-only),
    on renvoie le cache + un hint `_dedup_hint` au LLM. Erreurs
    non-cachées. Hits non-persistés dans `agent_decisions`.
  * **9.8.2 Slot mémoire `current_topic`** (migration 150 + service
    `conversation_topic.py`) — colonne JSONB `assistance_conversations
    .current_topic` auto-set par les tools ancrants
    (`show_bundle_detail`, `show_instrument_card`, `read_wiki_page`,
    `read_product_knowledge`). Lu par le router au tour suivant et
    injecté dans le system prompt sous forme `[CONTEXT TOPIC] Sujet
    en cours : produit Vancelian TOP_5 (agent owner: product). Si le
    user message est un follow-up déictique, reste sur l'agent_owner`.
    Listes (`show_crypto_bundles`, `select_wiki_pages`) **n'ancrent
    pas**.
  * **9.8.3 Hot-path follow-up court** (`router_hot_path.py`) — bypass
    LLM router quand `len(msg) ≤ 60` + dernier agent expert + pas de
    signal de changement de sujet (`par contre`, `sinon`, `au fait`,
    …). Économie ~150-300 ms et ~500 tokens. Kill-switch
    `ASSISTANCE_ROUTER_HOT_PATH_ENABLED=false`.

**Tests** :
  * `test_assistance_runtime_dedup_unit.py` — 8 tests (dedup whitelist,
    args différents, tool hors whitelist, erreur, scope par turn).
  * `test_assistance_conversation_topic_unit.py` — 28 tests (inférence
    par tool, périmètre whitelist, render prompt, persistance defensive).
  * `test_assistance_router_hot_path_unit.py` — 46 tests (matrice
    longueur / agent / signaux / kill-switch / wrapper input).

**1017 tests assistance globaux verts → zéro régression.** Aucune
modif env/Docker (la migration Alembic 150 est purement additive,
JSONB nullable, aucun backfill). Lot actif immédiatement après
restart API container.

---

## 10. Versioning

| Date | Version | Phase | Changements |
|---|---|---|---|
| **2026-05-03** | **1.0** | **Phase 2c livrée** | **Création de l'agent `product` (prompt + tools), table SQL `product_knowledge` (migration 149, 10 seeds), invocation via `consult_specialist`. Garde-fous structurels (pas de `consult_specialist`/`handoff_to_agent` côté product). 530 tests assistance verts.** |
| **2026-05-04** | **1.1** | **Phase 1 wiki MD livrée** | **Import de 243 fiches markdown depuis le vault Obsidian source dans `assistance/data/wiki/` (stockage seul, aucun branchement runtime). Audit cohérence Annexe 36 + 72 feedbacks copiés dans `docs/arquantix/product-wiki/`. Phase 2 (branchement runtime via `select_wiki_pages` + `read_wiki_page`) en PR séparée.** |
| **2026-05-04** | **1.2** | **Phase 2 wiki branchée au runtime** | **Repo `wiki_repo.py` (parsing frontmatter maison + cache TTL 5 min + scoring keyword Karpathy-style). 2 tools L0 livrés : `select_wiki_pages(question, top_k?, category?)` (pré-filtre top 5 sur les 243 fiches) + `read_wiki_page(category, slug)` (lecture complète). Prompt système v2 enrichi de `system-prompt-v2.md` (vocabulary, grounding_rule, account_limitation, response_rules, mandatory_disclaimers, escalation_triggers, forbidden_patterns, self_check, 4 examples). Cohabitation SQL/MD : SQL d'abord pour les fiches courtes canoniques, MD pour la couverture large. 46 tests wiki + 679 tests assistance globaux verts → zéro régression. Aucune modif env/DB/Docker, aucune nouvelle dépendance Python.** |
| **2026-05-04** | **1.3** | **Guard-rail anti-hallucination + mémoire affinée** | **Constat post-prod (analyse conv `aef5923a`) : sur 8 turns Phase 2, 3 zappent les tools (turns 30/32 répondent direct → hallucination cf. turn 32 « Vancelian ne propose pas d'invest crypto » faux ; turn 42 = `select_wiki_pages × 2` sans `read_wiki_page` → composition depuis titres seuls). **Guard-rail runtime livré** dans `agent_loop.py` : si l'agent `product` termine un turn sans `read_product_knowledge` / `read_wiki_page` / `show_instrument_card`, ou avec `select_wiki_pages` mais sans read derrière, on injecte un hint system explicite et on rejoue la boucle **une seule fois**. Désactivable via `ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED=false`. **Mémoire long-terme retunée** : seuil tokens abaissé `6000 → 2500` + nouveau déclencheur `min_turns=10` (consolidation à 20 messages indépendamment des tokens). Conséquence : la conv `aef5923a` (4 200 tokens) aurait été consolidée 3-4 fois au lieu de 0. 18 nouveaux tests guard-rail + 6 nouveaux tests memory + 6 ajustements de tests existants. **852 tests assistance globaux verts (vs 679 avant) → zéro régression.** Aucune modif env/DB/Docker.** |
| **2026-05-04** | **1.4** | **Slider Crypto Bundles + router QCM contextualisé + refonte `instrument_detail_card`** | **Constat post-prod (analyse conv `e5133711`) : (1) « Découvrir les bundles disponibles » → réponse markdown générique (pas de visuel concret du catalogue) ; (2) « quel bundle adapté à mon profil ? » → QCM router avec labels génériques ne mentionnant pas « bundle » + bascule en clarification au lieu d'advisor direct ; (3) la carte `instrument_detail_card` du chat n'était pas alignée sur la partie haute de la page détail (mini-sparkline avec area, pas de tag Crypto, mauvais avatar, chart pas bord-à-bord). **Solutions livrées (4 lots)** : **Lot 1 (router prompt-only)** : nouveau sous-cas règle 2 « profil sur produit Vancelian nommé » → `route_to(advisor)` direct + règle de contextualisation `ask_clarification` (labels DOIVENT reprendre le sujet `recent_turns`) + 3 exemples calibrés. **Lot 2 (tool backend)** : nouveau tool L0 `show_crypto_bundles()` qui consomme `CatalogService.get_public_catalog(product_type='crypto_bundle')` (réutilisé tel quel — 0 modif portfolio_engine) et émet un embed `crypto_bundles_card` avec bundles + allocations + 2 deep-links whitelistés (`view_bundle_detail` + `invest_bundle`). Ajouté à `PRODUCT_KNOWLEDGE_READ_TOOLS` (compatible guard-rail). **Lot 3 (Flutter `crypto_bundles_card`)** : nouvel embed `CryptoBundlesCardEmbed` qui délègue le rendu à `AssetsBundlesModule` (réplique exacte du widget markets). Resolver `vancelian://app/bundle/{id}[/invest]` ajouté avec enrichissement `portfolioId` via `getBundleCatalog`. **Lot 4 (Flutter `instrument_detail_card` refonte)** : `InstrumentDetailCardEmbed` réécrit en `StatefulWidget` qui charge les vraies bougies via `MarketDataApi.getChartHistory` et délègue au `ChartAssetModule(instrumentDetailStyle: true)` (réplique visuelle exacte du hero détail instrument : line chart pur + ligne horizontale + sonar + period chips + disclaimer + tag « Crypto » + `CryptoAvatar` + CTAs Acheter/Vendre sous le chart). `ChartAssetModule` étendu d'une prop optionnelle rétrocompatible `chartContainerWidth` pour fonctionner dans une bulle chat. **Tests** : 30 nouveaux (show_crypto_bundles) + 6 nouveaux (router QCM/advisor profil) + maj wiring registry. **909 tests assistance globaux verts → zéro régression**. Aucune modif env/DB/Docker, 0 nouvelle dépendance. Lots 1+2 actifs immédiatement (restart container) ; Lots 3+4 attendent un build Flutter.** |
| **2026-05-04** | **1.4 patch 2** | **Stabilité conversationnelle — dedup + topic + hot-path** | **Constat post-prod (analyse conv `5bef01e9`, 5 turns) : (1) router LLM flippe sur mot-clé isolé (« perf » → market) malgré déictique « ce bundle » ; (2) `show_crypto_bundles` appelé 2× avec mêmes args dans le même turn ; (3) sujet « en cours » non matérialisé entre tours. **Solutions livrées (3 mécanismes complémentaires)** : **(A) Dédoublonnage runtime** (`agent_loop.py` :: `tool_call_cache`) — cache local au turn `(tool_name, frozen_args)`, whitelist `DEDUPABLE_TOOLS` (idempotents read-only). 2ᵉ appel identique → cache + `_dedup_hint` au LLM. Erreurs non-cachées. Hits non-persistés. **(B) Slot mémoire `current_topic`** (migration 150 + `services/assistance/conversation_topic.py`) — colonne JSONB nullable auto-set par `show_bundle_detail` / `show_instrument_card` / `read_wiki_page` / `read_product_knowledge`. Lu par le router et injecté en system prompt `[CONTEXT TOPIC]`. Listes (`show_crypto_bundles`, `select_wiki_pages`) n'ancrent pas. **(C) Hot-path follow-up court** (`services/assistance/router_hot_path.py`) — bypass LLM router quand message ≤ 60 chars + dernier agent expert + pas de signal de changement de sujet. Économie 150-300 ms / 500 tokens. Kill-switch `ASSISTANCE_ROUTER_HOT_PATH_ENABLED=false`. **Tests** : 8 (dedup) + 28 (topic) + 46 (hot-path) = **82 nouveaux tests**. **1017 tests assistance globaux verts (vs 935 avant) → zéro régression.** Migration 150 purement additive (JSONB NULL, aucun backfill). Aucune modif env/Docker. Lot actif immédiatement après restart container.** |
| **2026-05-04** | **1.4 patch** | **WebSocket instrument live + Bundle detail card + filtrage liste bundles** | **Constat client (UX feedback v1.4)** : 4 écarts résiduels — (1) bulle chat instrument **non live** (vs page détail qui stream Binance) ; (2) pas d'équivalent **fiche détaillée** pour UN bundle ciblé (« parle-moi du TOP5 ») ; (3) slider liste avec titre de module dupliquant le texte LLM + cards de **taille différente** vs markets + **image cover absente** ; (4) demande de **plusieurs bundles ciblés** affiche tout le catalogue. **Solutions livrées (4 lots couplés)** : **Lot 1 (Flutter instrument live)** : `InstrumentDetailCardEmbed` connecte `MarketDataWsService.subscribe([providerSymbol])` au mount → tick `QuoteUpdate.price` prime sur `_candles.last.close`. `dispose()` déconnecte. **Lot 2 (Flutter `crypto_bundles_card` refonte)** : `CryptoBundlesCardEmbed` devient `Stateful`, fetch `ProductCatalogApi.getDisplayConfigs()` au mount → résout `headerMediaUrl` (image cover), `cardTitle`, `performance1d`, `sortOrder`. `title: ''` (pas de titre module) + `visibleCardsCount: 1.4` (strictement identique markets). **Lot 3 (Flutter `bundle_detail_card` nouveau)** : nouveau widget `BundleDetailCardEmbed` qui réplique la partie haute de `BundleInstrumentDetailHero` (tag Crypto Bundle + `BundleTickerAvatarRow` + titre + `InstrumentDetailHeroPerformanceRow` alimentée par `BundlePerformanceChartModule.onHeroMetricsChanged` + chart bord-à-bord + CTAs Voir/Investir). `BundlePerformanceChartModule` étendu de la prop optionnelle rétrocompatible `chartContainerWidth`. Nouveau case `bundle_detail_card` dans `search_screen.dart`. Nouveau helper `singleBundleItem` dans `chat_api.dart`. **Lot 4 (backend filtrage + show_bundle_detail)** : `show_crypto_bundles` accepte param optionnel `product_codes: list[str]` (zéro match → `available_product_codes` retourné pour aider le LLM). Nouveau tool L0 `show_bundle_detail(product_code OR bundle_id)` qui émet un embed `bundle_detail_card`, ajouté à `PRODUCT_KNOWLEDGE_READ_TOOLS`. Prompt `product_system.md` enrichi d'une règle de tri **CRITIQUE** sur 3 cas (1 bundle nommé / N bundles ciblés / tout le catalogue). **Tests** : 5 nouveaux (filtrage `show_crypto_bundles`) + 24 nouveaux (`show_bundle_detail` complet) + maj `test_product_total_tool_count` (7→8). **935 tests assistance globaux verts → zéro régression.** Aucune modif env/DB/Docker, 0 nouvelle dépendance. Lot 4 (backend) actif immédiatement après restart container ; Lots 1-3 (Flutter) attendent un build mobile.** |

> **Règle :** toute évolution du catalog `consult_purposes`, du
> schéma `product_knowledge`, ou des garde-fous structurels **doit**
> incrémenter cette version.
