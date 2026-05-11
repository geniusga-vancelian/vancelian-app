# Scénario E2E n°1 — Assistance multi-agents (audit qualité + raisonnement)

**Objectif** : premier tour de test « client réaliste » pour observer à la fois les **réponses** et le **chemin de décision** (router, orchestration, outils, policy soft, cognitive).

**Important — où envoyer les messages vs où observer**

| Rôle | Outil |
|------|--------|
| **Envoyer** les messages en tant que client | **Application mobile Flutter** connectée au compte client de test (même backend que ton build réel). Il n’y a pas, dans `arquantix-web`, de page publique dédiée à la saisie du chat assistance multi-agents. |
| **Suivre** les Q/R + raisonnement | **Admin web** : `Clients` → choisir la personne → **Conversations assistance** → ouvrir la conversation → tu vois la timeline, le chat, la **synthèse cognitive** (dont orchestration + `conversation_state`), les **gaps policy**, la **workflow trace**. |

---

## Prérequis

1. API + stack habituelle **déjà démarrées** (comme pour un run local normal).
2. Un **client / person** de test connu (celui que tu utilises déjà pour les essais) avec accès **Flutter** connecté à ce backend.
3. Dans l’admin, repère à l’avance l’UUID **person_id** pour arriver vite sur la liste des conversations.

---

## Persona — « Claire »

- Déjà cliente, épargne long terme ; ton **factuel**, pas jargon excessif attendu.
- Elle veut **trouver ses mouvements** et **être rassurée** sur une opération récente (sans inventer des montants : le bot doit s’appuyer sur les tools / dire ce qu’il ne sait pas).

---

## Déroulé (messages utilisateur à envoyer **dans l’ordre**, depuis Flutter)

Tu peux copier-coller tel quel après avoir **ouvert une nouvelle conversation** (ou poursuivre dans une conv dédiée aux tests pour ne pas mélanger avec du vrai historique).

### Tour 1 — Besoin données compte / parcours produit

**Message utilisateur**

> Bonjour, je cherche où voir mes derniers mouvements et paiements dans l’app. Tu peux m’indiquer le chemin, et me dire si je peux filtrer par mois ?

**Ce que tu testes**

- Routage vers un agent pertinent (ex. advisor / product selon ton produit).
- **`orchestration.data_need`** : souvent `account_data` ou `transaction_data` si le routeur est bien calibré.
- Appels d’outils de **lecture** (`list_transactions`, `read_transactions`, doc produit / wiki selon implémentation).
- Réponse **actionnable** (étapes UI) + **honnêteté** si les données ne sont pas disponibles.

### Tour 2 — Vérification factuelle (ancrage données)

**Message utilisateur**

> Merci. La semaine dernière j’ai fait un paiement ou un débit d’environ 500 € — tu peux me confirmer si tu le vois sur mon compte ?

**Ce que tu testes**

- Utilisation d’un **outil de lecture** plutôt qu’une invention de solde.
- Comportement si **aucune transaction** ne matche (refus de confirmer un faux positif).
- **Policy soft** : si `data_need` impose une lecture et qu’aucun tool adapté n’a été appelé avant la réponse → ligne `policy_data_need_reads` + bloc ambre dans l’admin.

### Tour 3 — Message laconique (continuité)

**Message utilisateur**

> Les offres

**Ce que tu testes**

- **Continuité** : la réponse doit réutiliser le contexte du tour précédent (épargne / compte / offres), pas répondre « dans le vide ».
- Bloc contexte / `recent_turns` côté synthèse admin.

### Tour 4 — Dimension émotionnelle + objectif bot

**Message utilisateur**

> Honnêtement je suis un peu inquiète avec tout ce qu’on entend sur les marchés. Tu peux m’expliquer calmement ce que ça change pour mon épargne sur 5–10 ans, sans me pousser à acheter un truc ?

**Ce que tu testes**

- **Cognitive** : `emotional_intent`, `conversation_stage`, `trust_level`, objectif (`primary_goal`, `next_best_action`, `stop_pushing`).
- **Ton** : apaisement, pas de vente agressive si `stop_pushing` ou style adapté.

---

## Pendant que tu envoies les messages : checklist sur la page admin conversation

Après **chaque** réponse assistant, rafraîchis si besoin (`Refresh`) et vérifie pour le **tour** concerné :

1. **Synthèse cognitive**  
   - Input user, contexte (summary / laconique), analyse cognitive, objectif.  
   - **Orchestration (router)** : `business_intent`, `data_need`, `urgency`, etc.  
   - **`conversation_state`** (snapshot JSON).  
   - Décision router (agent, confidence).

2. **Policy data need (audit soft)**  
   - Présence ou absence d’avertissement **gap** ; si oui : `data_need`, outils appelés, `expected_read_tools`.

3. **Workflow trace**  
   - Séquence d’outils, durées, erreurs éventuelles ; lignes `policy_data_need_reads` en surbrillance.

4. **Wiki** (si applicable)  
   - Précharge pipeline vs `read_wiki_page` / `select_wiki_pages`.

---

## Collecte pour « gros audit » ensuite

| Artefact | Comment |
|----------|---------|
| **Export JSON** (conversation + décisions) | Bouton **Export JSON** sur la page détail conversation admin. |
| **Golden trace JSONL** (ligne / tour user, replay) | CLI PR 4A : `services/arquantix/api/scripts/export_assistance_golden_traces.py` avec `--conversation-id <UUID>` ou `--since …` (voir script). |
| **Agrégats** | Page admin **Observabilité (KPI)** : taux de gaps, usage outils, etc. |

---

## Améliorations possibles à noter pendant le test (grille rapide)

À remplir pendant ou juste après la session :

- [ ] Réponse **sans** lecture métier alors que la question l’exigeait.
- [ ] **Hallucination** chiffrée ou confirmation d’une opération **non** visible via tools.
- [ ] **Mauvaise continuité** après message laconique.
- [ ] **Ton** inadapté au stress (trop promotionnel ou trop technique).
- [ ] **Orchestration** incohérente (`data_need` « none » alors que besoin évident).

---

## Suite

Scénarios suivants suggérés (à documenter ensuite) :

- **S02** : KYC / documents / conformité (`kyc_data`, `read_documents`).
- **S03** : Multi-tours « projet maison » + changement de sujet puis retour proactively.
- **S04** : Utilisateur hostile / tentative d’instructions système (safety).
