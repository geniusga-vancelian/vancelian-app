# Audit du wiki produit — référence régulatoire

> **Statut :** import initial 2026-05-04 (Phase 1 — stockage seul).
> **Provenance :** `Vancelian Support (Chat WIKI LLM)/audit-wiki/` du vault Obsidian de Jean Guillou (OneDrive Vancelian).

---

## 1. Source absolue de vérité régulatoire

Le wiki produit est régi par **l'Annexe 36 — Schéma des Flux** (Notice Vancelian, septembre 2025, v1).

> *« Le schéma de flux est la source absolue de vérité pour chaque produit qui génère une transaction. Le régulateur doit pouvoir vérifier la mécanique d'un produit via le schéma de flux. »*
>
> — `CLAUDE.md` §0 du vault Obsidian source

### Localisation du document

L'Annexe 36 **n'est volontairement pas copiée dans ce repo** (le repo de code n'est pas un coffre-fort régulatoire). Référence canonique :

```
OneDrive Vancelian
└── Vancelian Support (Chat WIKI LLM)/
    └── raw/
        └── Fiche MD Reglementation/
            └── Notice Vancelian/
                └── Annexe 36_Schéma des flux.docx
```

Hôte : `~/Library/CloudStorage/OneDrive-Vancelian/` (Mac de Gael) — ou via OneDrive web pour les autres devs.

### Périmètre couvert (7 services transactionnels)

| # | Service | Plage § | Type |
|---|---------|---------|------|
| A | Méthode de R/L hybride (base transversale) | §92-188 | Infrastructure règlement-livraison |
| B | Service de coffre « Flexible » / « Avenir » (Vaults) | §189-297 | Produit d'épargne |
| C | Service d'offre exclusive (BTC Lending) | §299-351 | Produit de prêt |
| D | Service de programme de minage (Cloud Mining) | §352-409 | Produit de vente de puissance de calcul |
| E | Service de crypto-actifs multiples (Crypto Baskets) | §410-513 | Produit de portefeuille diversifié |
| F | Service de dépôt et retrait crypto | §514-543 | Transaction on-chain |
| G | Service de paiement sur réserve crypto (Card Payment) | §544-606 | Paiement carte |

---

## 2. Documents présents dans ce dossier

| Fichier | Rôle |
|---|---|
| `cartographie-schema-flux-2026-04-18.md` | Matrice de correspondance Annexe 36 ↔ fiches du wiki produit (`assistance/data/wiki/faq/...`). Identifie les fiches alignées, à vérifier, à réécrire. |
| `audit-coherence-schema-flux-2026-04-18.md` | Rapport de cohérence détaillé : contradictions, gaps, propositions d'évolution. |
| `scripts/audit_pass1.py` | Audit structurel (présence frontmatter, `questions:`, `sources:`). |
| `scripts/audit_pass2.py` | Audit lexical / terminologique (vocabulary mapping, ambiguïtés). |
| `scripts/audit_pass3.py` | Audit sémantique (alignement avec Annexe 36). |
| `scripts/build_final_report.py` | Agrégation des passes 1/2/3 en rapport final. |

> Les scripts Python sont **outillage de maintenance** — pas de runtime, pas de dépendance pour l'app. Ils tournent à la demande sur le wiki MD lors d'une session de revue.

---

## 3. Règle de gouvernance

Quand une fiche du wiki décrit comment un produit déplace de la valeur (cash, crypto, allocation), la mécanique **doit** être alignée sur l'Annexe 36. En cas de contradiction :

1. **L'Annexe 36 gagne.**
2. Surfaicer la contradiction dans `assistance/data/wiki/log.md`.
3. Mettre à jour la fiche wiki en conséquence.
4. Ne **jamais** réécrire silencieusement.

Cette règle se place **au-dessus** de la hiérarchie de sources définie dans `CLAUDE.md` §1 (Brochures > Fiches produit > Fiches Reglementation > Site > FAQ Zendesk > Articles).

---

## 4. Mise à jour de l'audit

L'audit ci-joint est daté du **2026-04-18**. À refresh :

- Quand l'Annexe 36 publie une nouvelle version (`v2`, `v3`).
- Tous les **6 mois** au minimum (rotation `last_reviewed:` des fiches wiki).
- Après tout ajout de **catégorie produit** dans `assistance/data/wiki/faq/`.

Le run d'audit complet se fait depuis ce dossier :

```bash
cd docs/arquantix/product-wiki/audit/scripts
python audit_pass1.py
python audit_pass2.py
python audit_pass3.py
python build_final_report.py
```

(Les scripts attendent que `assistance/data/wiki/` soit présent au bon path relatif — à ajuster si on les exécute depuis ailleurs.)
