# Product Wiki — base de connaissance markdown de l'agent `product`

> **Statut :** Phase 1 livrée 2026-05-04 — **stockage seul**, pas encore branché au runtime.
> **Phase 2 :** branchement runtime via tools `select_wiki_pages` + `read_wiki_page` (PR séparée).
> **Spécification de l'agent :** [`PRODUCT_AGENT.md`](../PRODUCT_AGENT.md)

---

## 1. Provenance

Le contenu de ce wiki et les artefacts associés (audit + feedback) viennent du vault Obsidian `Vancelian Support (Chat WIKI LLM)/` maintenu par Jean Guillou (OneDrive Vancelian, snapshot du **2026-05-04**).

Le projet d'origine inclut aussi un bot Slack standalone (`vancelian-bot/bot.js`, runtime 2-pass Claude Haiku 4.5) qui n'est **pas importé** dans ce repo : nous ne reprenons que la base de connaissance (markdown) pour alimenter notre agent `product` in-app, qui possède déjà son propre runtime (cf. `MULTI_AGENTS_RUNTIME.md`).

Architecture d'origine du copain : `Vancelian-Agent-v4-Architecture.pdf` (avril 2026).

---

## 2. Layout dans le repo

```
services/arquantix/api/services/assistance/data/wiki/    ⭐ runtime (chargé par l'agent en Phase 2)
├── index.md                                             (master catalog Karpathy, ≈1 500 phrasings)
├── chatbot-spec.md                                      (réf — spec fonctionnelle v2 du copain)
├── system-prompt-v2.md                                  (réf — prompt PASS 2 Slack, à intégrer en Phase 2)
├── log.md                                               (journal d'ingest)
├── faq/                                                 (222 fiches client en 13 catégories)
│   ├── savings/ (16)
│   ├── exclusive-offers/ (34)
│   ├── crypto/ (29)
│   ├── aktio/ (12)
│   ├── memberships/ (7)
│   ├── account/ (36)
│   ├── transfers-cards/ (35)
│   ├── legal-compliance/ (29)
│   ├── company/ (15)
│   ├── business/ (5)
│   ├── affiliate-partner/ (3)
│   ├── b2b-agent/ (1)
│   └── other/ (vide — placeholder)
├── concepts/ (7)                                        (custody architecture, glossary, rate smoothing…)
├── entities/ (8)                                        (Automata Group, Bitmart, Hearst, Solaria…)
└── policies/ (2)                                        (vault-allocation-mechanics, crypto-transfer-policy)

docs/arquantix/product-wiki/                              (artefacts opérationnels — humains uniquement)
├── README.md                                            (ce fichier)
├── audit/                                               (cohérence avec l'Annexe 36 régulatoire)
│   ├── README.md                                        (référence OneDrive vers l'Annexe 36)
│   ├── cartographie-schema-flux-2026-04-18.md
│   ├── audit-coherence-schema-flux-2026-04-18.md
│   └── scripts/                                         (4 scripts Python d'audit maintenance)
└── feedback/                                            (retours clients du bot Slack source)
    ├── index.md                                         (dashboard 58 open / 14 traités)
    ├── entries/                                         (feedbacks ouverts)
    └── history/                                         (feedbacks traités, avec « → fix appliqué »)
```

> **Pourquoi cette séparation runtime / docs ?**
> - `assistance/data/wiki/` est lu par le LLM à chaque tour de chat → vit dans le package Python.
> - `docs/arquantix/product-wiki/` est lu par les humains lors des sessions de maintenance → vit dans `docs/`.

---

## 3. Format des fiches (Karpathy retriever pattern)

Chaque fiche `wiki/faq/<category>/<slug>.md` suit la convention `CLAUDE.md` du vault source :

```markdown
---
title: "<Plain-English question>"
slug: <kebab-case-id>
category: <savings | exclusive-offers | crypto | aktio | memberships | account | transfers-cards | legal-compliance | company | business | affiliate-partner | b2b-agent | other>
audience: client
status: <draft | verified | stale>
last_reviewed: YYYY-MM-DD
sources: [raw/<filename>]
related: [<other-page>.md]
tags: [tag1, tag2]
questions:                          # ⭐ utilisé par PASS 1 Retrieval
  - <Natural client question phrasing #1>
  - <... 5–8 total>
---

# <Question as headline>

## Short answer
<2–4 sentences self-contained — ce que le bot peut citer seul>

## Details
## Sources
```

Pas de vector DB, pas d'embedding : le LLM lit `index.md` (qui agrège tous les `questions:`) et sélectionne directement les 3 à 5 fiches pertinentes (pattern Karpathy LLM-as-retriever).

---

## 4. Périmètre & cohabitation avec la table SQL `product_knowledge`

Le wiki MD **ne remplace pas** la table `product_knowledge` (10 fiches canoniques courtes, seedées via Alembic 149). Conformément à `MULTI_AGENTS.md` §13.4 :

| Source | Volume | Usage |
|---|---|---|
| Table SQL `product_knowledge` | 10 fiches courtes (≈300 mots) | **Citation littérale** par les sub-agents compliance via `consult_specialist` (délais SEPA, définitions Vault/SCPI/Livret). Validées éditorial, ton figé. |
| `assistance/data/wiki/` (Phase 2) | 243 fiches markdown | **Couverture large** (Q&A développées, FAQ Zendesk, mécaniques produit complètes). Lecture LLM avec retrieval Karpathy. |

Les deux coexistent. Le SQL reste la source canonique courte ; le MD est la couverture large.

---

## 5. Phases de livraison

### Phase 1 — Stockage (livrée 2026-05-04 — cette PR)

- Copie des 243 fiches MD dans `assistance/data/wiki/`
- Copie de l'audit (cartographie + scripts) dans `docs/arquantix/product-wiki/audit/`
- Copie des 72 feedbacks dans `docs/arquantix/product-wiki/feedback/`
- **Aucune modification de code.** L'agent `product` continue à utiliser uniquement la table SQL.

### Phase 2 — Branchement runtime (PR à venir)

- Nouveau tool `services/assistance/agents/tools/product/select_wiki_pages.py` (lit `data/wiki/index.md`, retourne 3 à 5 slugs pertinents).
- Nouveau tool `services/assistance/agents/tools/product/read_wiki_page.py` (lit `data/wiki/<category>/<slug>.md`, retourne `## Short answer` + `## Details`).
- Mise à jour du prompt système `services/assistance/prompts/product_system.md` — intégration des sections clés de `system-prompt-v2.md` (vocabulary, app_ui_labels, language_and_register).
- Tests unit + integration (≥10) sur les nouveaux tools.
- Documentation : MAJ `PRODUCT_AGENT.md` v2.0 + `MULTI_AGENTS.md` v2.4.

### Phase 3+ (plus tard, hors scope immédiat)

- Pipeline d'ingest pour resynchroniser le wiki depuis le vault Obsidian source (rsync filtré, lint frontmatter).
- Mini-écran admin BO pour éditer les fiches sans PR (Phase 4 de `PRODUCT_AGENT.md`).
- I18n FR/EN du `body` (V1 = anglais source uniquement, traduit à la volée par le LLM dans la langue du client).

---

## 6. Règles de modification

| Action | Qui | Process |
|---|---|---|
| Ajouter/éditer une fiche FAQ | Équipe produit + content | PR + revue éditoriale ; respecter le frontmatter `questions:` (5–8 phrasings) |
| Modifier `index.md` | Auto-généré (Phase 3) ou manuel | Toute fiche dans `wiki/faq/` doit être listée ; les orphelins sont remontés par `audit_pass1.py` |
| Désactiver une fiche | Équipe produit | Passer `status: stale` — ne **pas** supprimer (cf. `CLAUDE.md` source §"Category evolution rule") |
| Modifier l'Annexe 36 | Conformité Automata France | Hors repo (OneDrive). Quand la version change, refresh l'audit dans `audit/`. |

---

## 7. Références

- `docs/arquantix/PRODUCT_AGENT.md` — spec de l'agent `product` Phase 2c
- `docs/arquantix/MULTI_AGENTS.md` — architecture multi-agents Vancelian
- `docs/arquantix/MULTI_AGENTS_RUNTIME.md` — runtime function calling itératif
- `assistance/data/wiki/chatbot-spec.md` — spec fonctionnelle v2 du bot Slack source (référence de design)
- `assistance/data/wiki/system-prompt-v2.md` — prompt PASS 2 Slack (à intégrer en Phase 2)
