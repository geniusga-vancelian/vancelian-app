# Compliance Topics — Spec Phases 2b → 2c.7

> **Statut :** ✅ **Phases 2b + 2c + 2c.5 + 2c.6 + 2c.7 livrées** — orchestration multi-agents + statistiques transactionnelles & portefeuille + pattern de clarification sub-agents + widgets chat (instrument card, articles, top movers) + continuité de clarification (Patches A/C/D) en production locale.
>
> **Dernière mise à jour :** 2026-05-03 (v1.3)
>
> **Objectif :** matérialiser l'arbre de décision du domaine *Compliance*
> en 3 sub-agents (`compliance.registration`, `compliance.remediation`,
> `compliance.transactional`) + un fallback (`compliance.general`),
> chacun avec son prompt, ses tools L0/L1 et ses Action CTAs vers les
> écrans Flutter via deep-links. Phase 2c ajoute l'**orchestration
> inter-agents** : `handoff_to_agent` (transfert) et
> `consult_specialist` (consultation synchrone du `product` agent).
> Phase 2c.5 élargit `compliance.transactional` aux **statistiques**
> (counts, amounts, performance, allocation — Lots 1+2+3, cf. §13)
> et formalise un **pattern de clarification QCM amont** (cf. §14)
> partagé avec `compliance.general`.
>
> **Tests Phase 2b :** `test_assistance_action_cta_catalog_unit.py` (30),
> `test_assistance_diagnose_topic_unit.py` (22),
> `test_assistance_phase2b_extras_unit.py` (22),
> `test_assistance_compliance_dispatcher_unit.py` (7),
> `test_assistance_tools_registry_unit.py` (24) — 140 tests verts.
>
> **Tests Phase 2c :** `test_assistance_consult_purposes_unit.py` (24),
> `test_assistance_consult_specialist_unit.py` (≈8),
> `test_assistance_handoff_tool_unit.py` (≈8),
> `test_assistance_tour_shared_context_unit.py` (≈8),
> `test_assistance_product_agent_unit.py` (≈11),
> `test_assistance_orchestration_chain_unit.py` (5) — **530 tests
> assistance verts au total, zéro régression Phase 2a/2b.**
>
> **Tests Phase 2c.5 :**
> `test_assistance_list_transactions_unit.py` (≈18),
> `test_assistance_stats_transaction_counts_unit.py` (22),
> `test_assistance_stats_transaction_amounts_unit.py` (17),
> `test_assistance_stats_portfolio_performance_unit.py` (15),
> `test_assistance_stats_portfolio_allocation_unit.py` (13)
> — **+67 tests** assistance verts, zéro régression Phase 2a/2b/2c.
>
> **Documents liés :**
>
> - `MULTI_AGENTS.md` — architecture cible des 5 agents
> - `PRODUCT_AGENT.md` — vrai agent `product` (Phase 2c) **NEW**
> - `MULTI_AGENTS_RUNTIME.md` — runtime, autonomy, audit (Phase 2a)
> - `MULTI_AGENTS_DATA_SOURCES.md` — cartographie data introspective
> - `AUDIT_AUTH_IDENTITIES.md` — règles d'identité (clos)

---

## 0. TL;DR

Phase 2a a livré l'agent `compliance` mono-prompt + 5 tools L0
read-only. Phase 2b enrichit cet agent en **3 sub-agents** spécialisés
selon la situation réelle du client, plus un fallback. Le **router
top-level ne change pas** (il continue à classifier en `compliance`
générique). C'est `compliance` lui-même qui se dispatche en interne au
1er tour de runtime via le tool obligatoire
`diagnose_compliance_topic`.

L'agent peut conclure ses réponses avec des **Action CTAs** (extension
du `message_type=choices` existant — pas de nouveau type) qui pointent
vers des deep-links résolus côté mobile par
`AssistanceDeepLinkResolver`.

---

## 1. Pattern à 2 niveaux

```
USER MESSAGE
   │
   ▼
ROUTER (top-level, gpt-4o-mini)
   │   classifie en {compliance | advisor | product | market | default}
   │
   ▼
RUNTIME compliance — itération 0 (forcée)
   │   tool obligatoire = diagnose_compliance_topic()
   │   ├── lit registration_progress + compliance_state + transactions
   │   └── retourne dominant_topic ∈ {registration | remediation | transactional | general}
   │
   ▼
RUNTIME bascule l'`agent_id` vers `compliance.<topic>`
   │   - charge le sous-prompt correspondant
   │   - restreint le set de tools au sous-set du topic
   │   - poursuit le loop normalement (max_iter, autonomy gating, audit)
   │
   ▼
RÉPONSE FINALE (text + optionnellement choices avec deep-links)
```

**Pourquoi pas exposer les sub-agents au router top-level ?**

1. Le router n'a pas accès à l'état DB du client → classifierait à
  l'aveugle.
2. La détermination du topic doit dépendre de la situation réelle
  (registration en cours ? remediation due ? transaction récente ?)
   pas seulement de la formulation. C'est le métier de l'agent
   Compliance, pas du routeur.
3. Évite les boucles "router demande clarification → user reformule →
  router re-classifie".

**Audit (`assistance_agent_decisions.agent_id`)** : la valeur stockée
est `compliance.registration` (granulaire). Tu peux filtrer chaque
sub-agent indépendamment dans la table.

---

## 2. Le tool clé : `diagnose_compliance_topic` (L0)

### 2.1 Contrat

```json
{
  "name": "diagnose_compliance_topic",
  "description": "Détermine le sous-univers Compliance pertinent pour ce client à ce moment, en agrégeant les signaux DB (registration, KYC, transactions). Retourne le topic dominant + l'action recommandée + le contexte LLM-friendly.",
  "parameters": {
    "type": "object",
    "properties": {
      "user_message_hint": {
        "type": "string",
        "description": "La question utilisateur (ou résumé) pour aider à départager registration vs transactional quand l'état client le permet."
      }
    },
    "required": [],
    "additionalProperties": false
  },
  "autonomy_level": "L0",
  "agent_id": "compliance"
}
```

### 2.2 Schéma de retour

```json
{
  "dominant_topic": "registration",
  "confidence": 0.85,
  "secondary_topics": ["transactional"],
  "next_recommended_action": {
    "kind": "deposit_funds",
    "label": "Effectuer mon premier dépôt",
    "deep_link": "vancelian://app/deposit",
    "urgency": "important"
  },
  "context_for_llm": {
    "kyc_complete": true,
    "registration_steps_remaining": 0,
    "first_deposit_done": false,
    "open_remediation_requests": [],
    "recent_failed_transactions": []
  },
  "triggers_used": ["pe_clients.kyc_status=approved", "pe_orders.count=0"]
}
```

### 2.3 Règles de classification

Évaluation en cascade (premier matché gagne) :


| Priorité | Condition                                                                                                              | `dominant_topic` |
| -------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------- |
| 1        | `kyc_status != approved` ∨ `account_state ∈ {PARTIAL, BLOCKED}` ∨ `registration_session.completed_steps < total_steps` | `registration`   |
| 2        | `kyc=approved` ∧ (`requires_doc_upload=true` ∨ doc rejeté récemment ∨ review annuelle due)                             | `remediation`    |
| 3        | `user_message_hint` mentionne *transaction/dépôt/virement/retrait/investissement* OU `pe_orders.recent_failed > 0`     | `transactional`  |
| 4        | Sinon                                                                                                                  | `general`        |


`secondary_topics` rempli quand 2 conditions matchent (ex: registration
incomplet ET question transactionnelle → secondary = transactional).

`next_recommended_action` : computée à partir d'une table de mapping
`(topic × état) → CTA` (cf. § 4 ci-dessous).

`context_for_llm` : strictement les signaux **déjà publics côté UI**
(client peut les voir dans son profil mobile). Anti-tipping-off
respecté : pas de risk_score, pas d'AML interne.

---

## 3. Modélisation des 4 sub-agents

### 3.1 `compliance.registration`

**Détecté quand** : KYC pas approved OU compte PARTIAL/BLOCKED OU
registration steps incomplets.

**Tools L0 actifs** :

- `read_compliance_state`
- `read_registration_progress`
- `read_documents`
- `propose_resume_registration` (nouveau Phase 2b — retourne deep-link
de la prochaine étape de registration depuis la session active)
- `ask_user_question` (transverse)

**Sous-prompt** (`compliance_registration.md`) : ton bienveillant qui
guide pas-à-pas vers la finalisation. Toujours conclure par un CTA
concret quand applicable.

**Action CTAs typiques** :

- "Reprendre l'inscription" → `vancelian://app/registration_resume`
- "Effectuer mon premier dépôt" → `vancelian://app/deposit` (quand KYC
fini mais 0 dépôt)

### 3.2 `compliance.remediation`

**Détecté quand** : `kyc=approved` ∧ `account_state=ACTIVE` ∧ (signal
remediation actif).

**Tools L0 actifs** :

- `read_compliance_state`
- `read_documents`
- `read_external_aml_signals`
- `ask_user_question`

> Note Phase 2b : `request_doc_upload` (L1, mutatif) est **reporté à
> Phase 2c**. En 2b, l'agent guide verbalement le user vers le menu
> documents quand il existera (pour l'instant : message d'attente +
> redirection support si urgent).

**Sous-prompt** (`compliance_remediation.md`) : tonalité explicative,
contexte régulatoire vulgarisé. Pas alarmant. Réassurance sur le
caractère normal des demandes de doc.

**Action CTAs typiques (Phase 2b minimal)** :

- Aucun deep-link vers upload tant que l'écran n'existe pas (cf. limite
Flutter). On utilise `ask_user_question` pour proposer "Je peux te
rappeler quand ce sera prêt" / "Contacter le support".

### 3.3 `compliance.transactional`

**Détecté quand** : la question référence une opération, une
transaction, un mouvement (dépôt / retrait / virement / carte /
crypto), un agrégat (combien / total / bilan), une mesure de
portefeuille (performance / PnL / allocation / répartition) OU
`pe_orders.recent_failed > 0`.

**Tools L0 actifs** (état Phase 2c.5 — Lots 1+2+3 livrés) :


| Tool                          | Rôle                                                                                | Sortie                                                                    |
| ----------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `read_transactions`           | Résumé agrégé (compteurs par statut + IDs récents) — **diagnostic rapide**          | dict                                                                      |
| `read_transaction_detail`     | Détail d'une transaction précise par ID (vérif ownership)                           | dict + **embed `transaction_detail*`* (récap + tableau + 2 deep-links)    |
| `list_transactions`           | Liste filtrable (catégorie / direction / statut / date / limite ≤ 50)               | `markdown_table` (Date / Type / Statut / Montant / lien Ouvrir par ligne) |
| `stats_transaction_counts`    | **Nombre** agrégé par dimension (`direction` / `status` / `kind` / `month`)         | `markdown_table` (Catégorie / Nombre + ligne Total si > 1 ligne)          |
| `stats_transaction_amounts`   | **Sommes** déposées / retirées / nettes (filtre `completed` par défaut)             | `markdown_table` (Direction / Montant + ligne Net)                        |
| `stats_portfolio_performance` | **Performance globale** (NAV, capital net déposé, PnL réalisé/latent/total, perf %) | `markdown_table` (Indicateur / Valeur, 6 lignes)                          |
| `stats_portfolio_allocation`  | **Allocation** macro (Cash / Crypto en direct / Bundles)                            | **embed `portfolio_allocation_donut`** (récap + donut + légende avec %)   |
| `read_compliance_state`       | Cohérence (compte bien actif)                                                       | dict                                                                      |
| `ask_user_question`           | Clarification ambiguïté **OU** push CTA d'action                                    | interrupt → `choices`                                                     |
| `consult_specialist`          | Consultation `product` agent (délais standards, base produit)                       | `specialist_text` à citer/paraphraser                                     |


**Sous-prompt** (`compliance_transactional_system.md`) : factuel,
chronologique. Le LLM applique systématiquement la **règle d'or de
clarification** en amont (cf. § 10) avant d'appeler un tool quand la
demande est ambiguë.

**Mode « se taire »** — 3 cas où le LLM n'écrit RIEN après l'appel
du tool, parce que l'embed/markdown est auto-suffisant :

1. Après `read_transaction_detail` → embed `transaction_detail`
  (récap textuel composé serveur + tableau + 2 actions).
2. Après `stats_portfolio_allocation` → embed
  `portfolio_allocation_donut` (récap + donut + légende).
3. Toute prose dans ces 2 cas créerait un doublon visuel avec la
  carte → côté Flutter, `_embedIsSelfContained` masque la bulle
   texte LLM si elle est triviale (< 60 chars après strip markdown).

**Pattern « coller le markdown_table tel quel »** — 4 tools où le
LLM se contente d'une intro courte (1 phrase) puis colle la sortie
du tool sans réécriture :

- `list_transactions`, `stats_transaction_counts`,
`stats_transaction_amounts`, `stats_portfolio_performance`.
- Interdit de recalculer / paraphraser les chiffres → garantit
l'absence d'hallucinations sur les agrégats.

**Action CTAs typiques** :

- *Voir mes virements en cours* → `vancelian://app/wallet/euro`
- *Voir le détail* → `vancelian://app/transactions/{id}`
(intégré automatiquement à l'embed `transaction_detail`)
- *Télécharger le relevé* → `vancelian://app/transactions/{id}/statement`
(intégré à l'embed `transaction_detail`, déclenche download PDF
  - `Share` natif côté mobile)

**Anti-tipping-off — garanties par tool** :

- `read_transaction_detail` : `amount` et `currency` sont lus depuis
le repo, **utilisés uniquement pour composer le `summary` de
l'embed**, puis **strippés** avant retour au LLM. Le LLM ne voit
jamais le montant brut, mais le client le voit dans la carte UI
(déjà accessible via API authentifiée).
- `stats_portfolio_allocation` : retour LLM expose les **%
uniquement** (les `value` en € sont dans l'embed UI, pas dans le
contexte LLM).
- `stats_transaction_amounts` / `stats_portfolio_performance` :
exposent des agrégats client-visibles uniquement (déjà disponibles
dans Wallet / Statement / Performance screens) — pas de leak de
scoring ou de signaux internes.

### 3.4 `compliance.general` (fallback)

**Détecté quand** : aucun des 3 ci-dessus.

**Tools L0 actifs** : tous les tools L0 (lecture seule). Permet à
l'agent de répondre à des questions générales tout en restant safe.

**Sous-prompt** : reprend le prompt Phase 2a actuel
(`compliance_system.md`).

---

## 4. Catalogue des Action CTAs (Phase 2b)

Tous résolus côté Flutter par `AssistanceDeepLinkResolver`.


| `kind`                    | Label par défaut          | Deep-link                             | Disponible Phase 2b ? |
| ------------------------- | ------------------------- | ------------------------------------- | --------------------- |
| `resume_registration`     | "Reprendre l'inscription" | `vancelian://app/registration_resume` | ✅                     |
| `deposit_funds`           | "Effectuer un dépôt"      | `vancelian://app/deposit`             | ✅                     |
| `deposit_virement`        | "Faire un virement"       | `vancelian://app/deposit/virement`    | ✅                     |
| `deposit_carte`           | "Déposer par carte"       | `vancelian://app/deposit/carte`       | ✅                     |
| `deposit_crypto`          | "Déposer en crypto"       | `vancelian://app/deposit/crypto`      | ✅                     |
| `view_wallet_euro`        | "Voir mon compte euro"    | `vancelian://app/wallet/euro`         | ✅                     |
| `view_iban`               | "Voir mon IBAN"           | `vancelian://app/wallet/iban`         | ✅                     |
| `view_transactions`       | "Voir mes transactions"   | `vancelian://app/transactions`        | ✅                     |
| `view_transaction_detail` | "Voir le détail"          | `vancelian://app/transactions/{id}`   | ✅                     |
| `view_account_info`       | "Mes informations"        | `vancelian://app/profile/account`     | ✅                     |
| `view_security`           | "Sécurité de mon compte"  | `vancelian://app/profile/security`    | ✅                     |
| `upload_document`         | "Uploader un document"    | (écran inexistant)                    | ❌ Phase 2c            |
| `contact_support`         | "Contacter le support"    | (à définir avec l'équipe)             | ❌ Phase 2c            |


---

## 5. Extension `choices` avec `deep_link` (vs nouveau type)

Décision : **pas de nouveau `message_type`**. On étend
`AssistanceChoiceOption` :

```python
@dataclass(frozen=True)
class AssistanceChoiceOption:
    id: str
    label: str
    agent_hint: Optional[str] = None
    deep_link: Optional[str] = None  # NEW Phase 2b
```

**Validation backend** : `agent_hint` et `deep_link` mutuellement
exclusifs sur une même option (validateur dans
`ask_user_question.execute` + tout endroit qui forge des choices).

**Côté Flutter** dans `_handleChoiceTapped` (extension de l'existant) :

```dart
if (option.deepLink != null) {
  await AssistanceDeepLinkResolver.resolve(context, option.deepLink!);
} else if (option.agentHint != null) {
  _sendMessageWithText(option.label, agentHint: option.agentHint);
} else {
  _sendMessageWithText(option.label);  // free text reformulation
}
```

**Visuel** : l'option avec `deep_link` peut afficher un trailing chevron
(distinct du sparkle des `agent_hint`) pour signaler "je vais te
naviguer vers un écran".

---

## 6. Resolver Flutter `AssistanceDeepLinkResolver`

Nouveau fichier : `lib/features/search/application/assistance_deep_link_resolver.dart`.

API publique : `static Future<void> resolve(BuildContext, String)`.

Implémentation : switch sur `uri.pathSegments` → push du bon
`MaterialPageRoute` avec les bons params. Gère :

- l'auth gate (si écran nécessite authentification, vérifie `JwtSession.isLoggedIn` avant push)
- les params manquants (transactionId, jurisdiction…) — fallback gracieux vers l'écran parent + snackbar d'erreur
- l'origine analytics (paramètre `?from=assistance` ajouté implicitement pour traçage)

**Hors scope Phase 2b** : Universal Links OS (Android `intent-filter` /
iOS `Associated Domains`). On reste sur deep-links **in-app** (string
résolue dans le chat), pas d'ouverture de l'app depuis un email
externe. À adresser en Phase 3+ quand le besoin externalisation se
posera.

---

## 7. Tests


| Niveau                                            | Couverture cible                                                                                                        |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Unit `diagnose_compliance_topic`                  | ≥ 8 scénarios (registration / remediation / transactional / general / multi-trigger / DB error / no auth / pas de hint) |
| Unit dispatcher runtime                           | ≥ 4 scénarios (forcing iter 0 = diagnose, switch agent_id, fallback general, error path)                                |
| Unit `AssistanceChoiceOption.deep_link` validator | ≥ 3 (valid, mutual exclusion, malformed URL)                                                                            |
| Unit `propose_resume_registration`                | ≥ 4 (session active / pas de session / session terminée / DB error)                                                     |
| Unit `read_transaction_detail`                    | ≥ 4 (id valide / id inconnu / pas client owner / DB error)                                                              |
| E2E end-to-end par topic                          | 4 (1 par sub-agent) — mock LLM + tool calls réels                                                                       |
| Anti-tipping-off                                  | que les nouveaux tools respectent la blacklist (déjà couvert par sanitizer, mais explicite)                             |


**Total cible : ~30 nouveaux tests Phase 2b**, en complément des 286
Phase 2a.

---

## 8. Roadmap d'implémentation


| Step    | Livrable                                                                                 | Estimation | Bloquant pour |
| ------- | ---------------------------------------------------------------------------------------- | ---------- | ------------- |
| **D.1** | Cette spec (validée par user)                                                            | —          | tout          |
| **D.2** | Tool `diagnose_compliance_topic` + 8 tests unit                                          | 1h         | D.5           |
| **D.3** | Étendre `KNOWN_AGENT_IDS` + `TOOLS_BY_AGENT` (4 sub-agents)                              | 30 min     | D.5           |
| **D.4** | 3 prompts `.md` (registration, remediation, transactional) — general réutilise l'actuel  | 1h         | D.5           |
| **D.5** | Runtime "compliance dispatcher" — switch `agent_id` après iter 0 + reload prompt + tools | 1h30       | D.7           |
| **D.6** | `AssistanceChoiceOption.deep_link` (backend + SSE propagation + Flutter parsing)         | 1h         | D.7           |
| **D.7** | `AssistanceDeepLinkResolver` Flutter + handler `_handleChoiceTapped` étendu              | 1h30       | D.9           |
| **D.8** | Tools nouveaux : `propose_resume_registration` + `read_transaction_detail`               | 1h         | D.9           |
| **D.9** | Tests unit + E2E (≥ 30)                                                                  | 1h30       | release       |


**Total : ~9h marathon** (un peu plus que mon estimation initiale de
7-8h, vu la complexité réelle du dispatcher runtime).

---

## 8bis. UX — stream "thinking" pendant `diagnose_compliance_topic`

L'iter 0 forcée ajoute ~1-2s de latence avant la première réponse
LLM. Pour rassurer le user, le SSE émet un événement
`thinking` dédié au début de la boucle compliance :

```json
{"event": "thinking", "data": {"phase": "diagnose", "agent": "compliance"}}
```

Côté Flutter, le bubble assistant reste sur l'animation typing dots,
mais on peut afficher un sous-titre discret (italique, gris clair)
"Analyse de votre situation…" tant que `phase=diagnose`. Le sous-titre
disparaît dès que le premier `delta` arrive.

Ce comportement est gated par `ASSISTANCE_STREAM_THINKING_ENABLED=true`
(déjà introduit en Phase 2a).

---

## 8ter. Sécurité — whitelist stricte des deep-links

Le LLM pourrait halluciner un deep-link malformé ou non implémenté
(ex: `vancelian://app/admin` ou `vancelian://wipe-account`). Pour
éviter toute fuite vers un écran non prévu :

1. **Côté backend** — toute option `choices` avec `deep_link` est
  validée à la **génération** : le `kind` doit appartenir à la
   whitelist statique du § 4 ; tout autre deep-link est **stripé** du
   SSE (l'option dégrade en simple texte) et loggé en
   `assistance.deep_link.rejected` pour analyse.
2. **Côté backend (génération)** — le tool `propose_resume_registration`
  et le builder `_build_action_cta` ne peuvent forger de deep-link
   qu'à partir d'enum `ActionKind` (Python `Literal`) → impossible de
   produire un URL libre.
3. **Côté Flutter resolver** — défense en profondeur :
  `AssistanceDeepLinkResolver.resolve` vérifie le scheme `vancelian://`
  - path matchant la whitelist locale. Tout URL non reconnu →
   snackbar "Action indisponible" + log analytics.

La whitelist canonique est la source de vérité :
`[services/arquantix/api/services/assistance/agents/tools/shared/action_cta_catalog.py](../../services/arquantix/api/services/assistance/agents/tools/shared/action_cta_catalog.py)`
(livrée D.6, validée par 30 tests unitaires dont 5 anti-tipping-off /
anti-template-injection).

---

## 9. Hors scope explicite Phase 2b

Reportés à Phase 2c ou ultérieur :

- `request_doc_upload` (L1) — nécessite l'écran d'upload côté Flutter
- `read_product_knowledge` — nécessite seed contenu produit (RAG ou
table SQL admin-éditable)
- Universal Links OS (Android/iOS deep-link externe)
- UI BO admin pour reviewer les `assistance_agent_decisions`
- Renommage `admin_users` → `auth_credentials` (dette tech identifiée
dans AUDIT_AUTH_IDENTITIES § 5.1 — Phase 3+)

---

## 10. Risques connus


| Risque                                                                 | Mitigation                                                                                                         |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Le LLM compliance ne respecte pas le sub-prompt et reste générique     | Sub-prompt en système role + 1-shot exemple dans chaque                                                            |
| `diagnose_compliance_topic` mal classifie (faux positif transactional) | `confidence` exposé ; fallback `general` en dessous de 0.5 ; tests adversariaux                                    |
| Coût OpenAI multiplié (iter 0 forcée)                                  | iter 0 réutilise les datas en cache du dispatcher pour iter 1+ ; latence mesurée                                   |
| Deep-link vers écran inexistant                                        | Resolver vérifie chaque kind contre une whitelist statique ; fallback snackbar "fonctionnalité bientôt disponible" |
| Boucle entre dispatcher et sub-agent                                   | Sub-agent ne peut PAS rappeler `diagnose_compliance_topic` (filtre dans le tools list de chaque sub-agent)         |


---

## 12. Phase 2c — Orchestration multi-agents

### 12.1 Vue d'ensemble

Phase 2b introduit déjà un dispatch interne (router → `compliance` →
`compliance.<topic>`). Phase 2c étend cette mécanique en deux
directions :

1. `**handoff_to_agent`** — un sub-agent compliance peut **transférer
  définitivement** le tour à un autre sub-agent compliance après
   investigation, lorsque le topic réel diffère du topic attendu
   (ex : `remediation` ne trouve aucun signal AML → handoff vers
   `transactional` pour répondre à la vraie question de l'utilisateur).
2. `**consult_specialist`** — un sub-agent compliance peut **consulter
  synchroniquement** un autre agent racine (en V1 : le seul agent
   éligible est `product`) pour obtenir une réponse factuelle
   (délais, définitions) qu'il intègre dans sa propre réponse. Le
   contrôle revient toujours au sub-agent appelant.

```
USER
  │
  ▼
ROUTER → compliance → diagnose_compliance_topic → compliance.remediation
                                                       │
                  ┌────────────────────────────────────┼────────────────────────────────────┐
                  ▼                                    ▼                                    ▼
       réponse directe                  handoff_to_agent (terminal)        consult_specialist (synchrone)
                                                ▼                                    ▼
                                  compliance.transactional         product (sub-loop autonome,
                                  (poursuit avec contexte           retourne du texte factuel)
                                   partagé filtré)                          ▼
                                                                  réponse compliance composite
```

### 12.2 Tool `handoff_to_agent`

- **Path** : `services/assistance/agents/tools/shared/handoff_to_agent.py`
- **Whitelist** des transitions (`_ALLOWED_HANDOFFS`) :

  | Source                     | Cibles autorisées                                    |
  | -------------------------- | ---------------------------------------------------- |
  | `compliance.remediation`   | `compliance.transactional`, `compliance.general`     |
  | `compliance.registration`  | `compliance.general` (cas rare)                      |
  | `compliance.general`       | `compliance.remediation`, `compliance.transactional` |
  | `compliance.transactional` | (aucun handoff sortant — feuille terminale)          |

- **Pré-conditions** :
  - Pour `compliance.remediation` uniquement, **au moins 2 outils
  d'investigation** parmi `{read_compliance_state, read_documents, read_external_aml_signals, fetch_transactions_summary, fetch_transaction_detail}` doivent
  avoir été appelés (`investigation_done`).
  - Au plus **un** handoff par tour (`handoff_done` filtre l'outil
  après le 1er succès).
  - Interdit pendant un sous-loop `consult_specialist`.
- **Effet runtime** : interrompt la boucle courante, charge le
prompt et les tools du sub-agent cible, injecte un bloc
*"Contexte partagé du tour précédent"* construit par
`tour_shared_context.format_for_prompt(...)` puis poursuit.
- **Anti-tipping-off** : le sub-agent cible n'a accès qu'aux clés
whitelistées (cf. §12.4).

### 12.3 Tool `consult_specialist`

- **Path** : `services/assistance/agents/tools/shared/consult_specialist.py`
- **Catalog** des purposes whitelistés
(`[tools/shared/consult_purposes.py](../../services/arquantix/api/services/assistance/agents/tools/shared/consult_purposes.py)`)
— V1 = 5 entrées :

  | Purpose                            | Target    | Paramètres requis                                                                   | Question construite (déterministe)                              |
  | ---------------------------------- | --------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------- |
  | `explain_deposit_delay`            | `product` | `payment_method ∈ {bank_transfer_in, card, crypto_in}`                              | "Quel est le délai standard pour un dépôt {payment_method} ?"   |
  | `explain_withdrawal_delay`         | `product` | `payment_method ∈ {bank_transfer_out, sepa_out, crypto_out}`                        | "Quel est le délai standard pour un retrait {payment_method} ?" |
  | `explain_kyc_review_typical_delay` | `product` | —                                                                                   | "Quel est le délai standard de revue KYC ?"                     |
  | `explain_swap_settlement_delay`    | `product` | —                                                                                   | "Quel est le délai de settlement d'un swap ?"                   |
  | `explain_product_basics`           | `product` | `product_slug ∈ {product_basics_vault, product_basics_livret, product_basics_scpi}` | "Donne une définition courte du produit {product_slug}."        |

  Chaque purpose contient un schéma de paramètres (required, enum,
  max_length). Toute entrée non whitelistée est rejetée à l'execute().
- **Effet runtime** :
  1. Le tool retourne `{"interrupt_with_consult": True, ...}`.
  2. Le runtime exécute un **sub-loop autonome** sur l'agent cible
    (`product`) avec son propre prompt, ses tools, et **son propre
     historique** (pas d'héritage du contexte compliance).
  3. Seul le **texte final** du sub-loop est ré-injecté comme
    `tool_result` dans la boucle compliance appelante.
  4. La consultation est tracée dans `consultations[]`
    (target, purpose, ok, duration_ms, text_excerpt) du `done`
     event final.
- **Garde-fous** :
  - `MAX_CONSULTATIONS_PER_TOUR=3` — au-delà, le tool est filtré et
  indisponible pour le LLM.
  - `MAX_CHAIN_DEPTH=1` — empêche `product` de re-consulter un autre
  agent (anti-récursion ; côté `product`, `consult_specialist`
  n'est pas dans ses tools de toute façon).
  - Le sub-loop a son propre `max_iterations` indépendant.

### 12.4 `tour_shared_context` (anti-tipping-off entre sub-agents)

`services/assistance/agents/runtime/tour_shared_context.py` agrège
les résultats d'outils du tour courant et n'expose que les **clés
explicitement whitelistées** par tool (`_SAFE_KEYS_PER_TOOL`) au
prompt du sub-agent cible après un handoff.


| Tool                         | Clés whitelistées                                              |
| ---------------------------- | -------------------------------------------------------------- |
| `read_compliance_state`      | `kyc_state`, `account_status`                                  |
| `read_registration_progress` | `current_step`, `completed_steps_count`                        |
| `read_documents`             | `missing_documents_count`, `pending_review_count`              |
| `read_external_aml_signals`  | `decision_summary` *(jamais le contenu brut des signaux)*      |
| `fetch_transactions_summary` | `total_count`, `last_transaction_date`, `pending_count`        |
| `fetch_transaction_detail`   | `transaction_id`, `status`, `amount`, `currency`, `created_at` |
| `diagnose_compliance_topic`  | `dominant_topic`, `confidence`                                 |


Tout autre champ (PII, message d'audit AML interne, raisons
détaillées de blocage…) est filtré silencieusement.

### 12.5 Checklist d'extension du catalog `consult_purposes`

Toute nouvelle question cross-agent **doit** :

1. Ajouter une entrée `PurposeName` + `PurposeSpec` dans
  `consult_purposes.py` avec `target`, `params_schema` (required,
   enum, max_length) et `question_template` (déterministe).
2. Couvrir le purpose par un test dans
  `test_assistance_consult_purposes_unit.py`.
3. Documenter le purpose dans cette section §12.3 et incrémenter la
  version (v1.2…).
4. Si l'agent cible est nouveau : voir §12.6.

### 12.6 Checklist d'ajout d'un nouvel agent consultable

1. Créer le prompt dans
  `services/assistance/prompts/<agent>_system.md`.
2. Créer ses tools dédiés dans
  `services/assistance/agents/tools/<agent>/` (typiquement L0
   read-only).
3. L'inscrire dans `tools/registry.py` (`TOOLS_BY_AGENT`) **sans**
  `consult_specialist` (anti-récursion) et **sans**
   `handoff_to_agent` (cf. §12.7).
4. L'inscrire dans `assistance_runtime_loop_agents` (config) si
  applicable.
5. Étendre `consult_purposes._CATALOG` avec les purposes éligibles.
6. Couvrir par un test unitaire dédié (cf. modèle
  `test_assistance_product_agent_unit.py`).

### 12.7 Garde-fous structurels (rappel)

- `product` n'a **ni** `consult_specialist` **ni** `handoff_to_agent`
→ impossible de cascader hors du sandbox.
- `compliance.transactional` n'a **pas** `handoff_to_agent`
(feuille terminale) mais a `consult_specialist`.
- Un seul handoff par tour ; au plus 3 consultations par tour ; au
plus 1 niveau de sub-loop.
- `tour_shared_context` ne propage que les clés whitelistées.
- Audit complet via `assistance_messages.message_payload.metadata`
(cf. §12.8).

### 12.8 Audit & observabilité

L'événement SSE `done` final contient désormais :

```json
{
  "type": "done",
  "message_id": "...",
  "completed": true,
  "final_agent_id": "compliance.transactional",
  "agent_chain": ["compliance.remediation", "compliance.transactional"],
  "consultations": [
    {
      "target": "product",
      "purpose": "product.delay.deposit",
      "ok": true,
      "duration_ms": 1842,
      "text_excerpt": "Un dépôt SEPA arrive en général..."
    }
  ]
}
```

Ces deux champs sont aussi persistés dans `assistance_messages. message_payload.metadata.orchestration` pour analyse offline (BO
admin V2). `agent_chain` n'est inclus que si `len > 1`.

### 12.9 Volumes Phase 2c


| Item                               | Volume                                                      |
| ---------------------------------- | ----------------------------------------------------------- |
| Lignes de code production (Python) | ~860                                                        |
| Migration Alembic (149) + seed     | 10 entrées `product_knowledge`                              |
| Prompts ajoutés / modifiés         | 1 nouveau (`product_system.md`) + 4 mis à jour (compliance) |
| Nouveaux tests unitaires           | ~64 (24 + 8 + 8 + 8 + 11 + 5)                               |
| Garde-fous runtime                 | `MAX_CHAIN_DEPTH=1`, `MAX_CONSULTATIONS_PER_TOUR=3`         |


---

## 13. Phase 2c.5 — Statistiques transactionnelles & portefeuille (Lots 1-3)

> **Statut :** ✅ **Lots 1, 2 et 3 livrés** — élargissement du scope
> de `compliance.transactional` aux **agrégats** transactions + aux
> **mesures portefeuille** (performance + allocation).

### 13.1 Objectif

Le sub-agent `compliance.transactional` couvrait Phase 2b/2c
uniquement la lecture **unitaire** d'une opération
(`read_transactions` agrégat + `read_transaction_detail`). Phase
2c.5 ajoute 4 angles **agrégés** :

1. **Counts** — combien de transactions (par direction / statut /
  kind / mois).
2. **Amounts** — total déposé / retiré / net en € (sur les
  `completed` par défaut).
3. **Performance** — NAV, capital net déposé, PnL réalisé / latent /
  total, perf %.
4. **Allocation** — répartition macro Cash / Crypto direct / Bundles
  sous forme de carte donut Flutter.

### 13.2 Découpage en 3 lots


| Lot       | Tools                                                   | Sortie                             | Statut |
| --------- | ------------------------------------------------------- | ---------------------------------- | ------ |
| **Lot 1** | `stats_transaction_counts`, `stats_transaction_amounts` | `markdown_table`                   | ✅      |
| **Lot 2** | `stats_portfolio_performance`                           | `markdown_table`                   | ✅      |
| **Lot 3** | `stats_portfolio_allocation`                            | embed `portfolio_allocation_donut` | ✅      |


### 13.3 Architecture des sources data

Les 4 nouveaux tools s'appuient sur des helpers existants
(zero duplication métier) :


| Tool                          | Source data principale                                                                                |
| ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| `stats_transaction_counts`    | `custody_transactions` (SQL `GROUP BY` agrégé via `compliance_repo._build_tx_where_clause`)           |
| `stats_transaction_amounts`   | `custody_transactions` (`SUM(amount)` ventilé par direction/devise, restreint `completed` par défaut) |
| `stats_portfolio_performance` | `portfolio_engine.valuation.{get_portfolio_breakdown, get_pnl, get_net_deposits}`                     |
| `stats_portfolio_allocation`  | `portfolio_engine.valuation.get_portfolio_breakdown` (filtre slices à 0 €)                            |


**Performance %** : calculée comme `total_pnl / net_deposits * 100`
uniquement si `net_deposits > 0` (dénominateur sain) ; sinon `null`
→ rendu `n/a` côté markdown.

### 13.4 Pattern de rendu


| Tool                          | Rendu                                                      | Texte LLM                        |
| ----------------------------- | ---------------------------------------------------------- | -------------------------------- |
| `stats_transaction_counts`    | `markdown_table` (Catégorie / Nombre + Total si > 1 ligne) | 1 phrase d'intro + colle tableau |
| `stats_transaction_amounts`   | `markdown_table` (Direction / Montant + Net)               | 1 phrase d'intro + colle tableau |
| `stats_portfolio_performance` | `markdown_table` (Indicateur / Valeur, 6 lignes)           | 1 phrase d'intro + colle tableau |
| `stats_portfolio_allocation`  | embed `portfolio_allocation_donut`                         | **vide** (la carte se suffit)    |


**Format FR strict** : `\u202f` (narrow no-break space) entre
milliers, virgule décimale, signe `+`/`-` explicite sur les PnL,
perf `+12,34 %` / `-5,00 %` / `n/a`.

### 13.5 Embed `portfolio_allocation_donut`

- **Type** : `portfolio_allocation_donut` (alongside
`transaction_detail`).
- **Payload serveur** :
  ```json
  {
    "type": "portfolio_allocation_donut",
    "currency": "EUR",
    "total_value": 20000.0,
    "summary": "Ton portefeuille s'élève à 20 000 €, avec une dominante en **Crypto en direct** (60,0 %).",
    "slices": [
      {"key": "fiat",          "label": "Cash (EUR)",       "value": 5000.0,  "percentage": 25.0},
      {"key": "crypto_direct", "label": "Crypto en direct", "value": 12000.0, "percentage": 60.0},
      {"key": "bundles",       "label": "Bundles",          "value": 3000.0,  "percentage": 15.0}
    ]
  }
  ```
- **Widget Flutter** : `PortfolioAllocationDonutEmbed` qui wrappe
`DonutsChartBig` (existant DS, pas de fetch réseau, tout vient de
l'embed).
- **Anti-tipping-off** : le retour LLM strippe `value` et ne garde
que les `percentage` (les € sont déjà dans l'embed UI).

### 13.6 Mise à jour `_embedIsSelfContained`

Côté `search_screen.dart`, la liste des embeds qui suppriment la
bulle texte LLM (si triviale) est étendue à
`portfolio_allocation_donut`. Pattern identique à
`transaction_detail` : éviter le doublon visuel quand l'embed
contient déjà tout.

### 13.7 Prompts mis à jour

- `compliance_transactional_system.md` : 5 nouvelles lignes dans le
tableau de routage + 5 cas d'exemple (Cas 6-10) + clarification
de la règle « jamais de montants bruts » (autorisée uniquement
depuis un `markdown_table` retourné par un tool).
- `compliance_general_system.md` : mention des 4 tools en filet de
sécurité (si le router envoie une demande stats vers `general`
par erreur).

### 13.8 Tests Phase 2c.5


| Tool                          | Tests                                                                          | Statut |
| ----------------------------- | ------------------------------------------------------------------------------ | ------ |
| `stats_transaction_counts`    | 22 (mapping labels, header markdown, group_by validation, filtres, total)      | ✅      |
| `stats_transaction_amounts`   | 17 (rendu markdown, signes, FR formatting, multi-devise, by_currency)          | ✅      |
| `stats_portfolio_performance` | 15 (header, signes, perf %, NAV sans signe, cas vide)                          | ✅      |
| `stats_portfolio_allocation`  | 13 (embed émis, slices sérialisées, summary, retour LLM strippé, slice unique) | ✅      |


**Total : +67 tests verts**, 0 régression sur les ~530 tests
assistance Phase 2a/2b/2c.

---

## 14. Pattern « Clarifier avant d'agir » (sub-agents compliance)

> **Statut :** ✅ **Phase 2c.5 — actif sur `compliance.transactional`
> et `compliance.general`**.

### 14.1 Pourquoi ce pattern

Avec l'élargissement du scope `compliance.transactional` (7 tools
fonctionnels couvrant 4 angles distincts : listing, counts, amounts,
performance, allocation), une demande client **vague** (« mes
transactions », « bilan », « stats », « comment ça va mon argent »)
peut conduire le LLM à choisir un tool arbitraire et produire une
réponse à côté.

Le router top-level utilise déjà ce pattern via le tool dédié
`ask_clarification` (cf. `router_system.md` règle 5.5). On
**transpose** le pattern aux sub-agents en réutilisant le tool
**transverse `ask_user_question`** déjà disponible (`agent_id: "*"`),
sans introduire de nouveau tool.

### 14.2 Tool utilisé

`ask_user_question` (transverse — toujours disponible). Le
runtime sait déjà :

1. interrompre la boucle agent (`interrupt_with_question: True`),
2. émettre un événement SSE `choices` côté client,
3. réinjecter la réponse client comme **nouveau message user** au
  prochain tour (l'agent raisonne dessus comme s'il s'agissait
   d'une nouvelle requête).

→ Aucun changement runtime / aucun nouveau tool / aucune
migration. Tout vit dans les prompts.

### 14.3 Règle d'or — heuristique du LLM

Avant tout appel à un tool de lecture / stats / détail, le LLM
applique le **test du mot-clé précis** :

> *« La demande contient-elle au moins UN mot-clé qui identifie
> sans ambiguïté le tool à appeler ? »*

- **Oui** → action directe (pas de QCM).
- **Non** → QCM via `ask_user_question` AVANT tout autre tool.

Mots-clés précis (`compliance.transactional`) : *dépôt(s)*,
*retrait(s)*, *virement(s)*, *combien de*, *total déposé / retiré*,
*performance*, *PnL*, *plus-value*, *allocation*, *répartition*, ID
transaction explicite.

Mots-clés précis (`compliance.general`) : *KYC*, *dossier*,
*étapes*, *documents*, *bloqué*, *AML*, ainsi que tous ceux du
transactional.

### 14.4 Wordings types

3 types pré-définis dans le prompt `compliance.transactional` :

- **A** — *« Mes transactions » / « historique » sans qualificatif*
→ 3 options : lister / compter / totaliser.
- **B** — *« Bilan » / « stats » / « point » global*
→ 4 options couvrant counts / amounts / performance / allocation.
- **C** — *« Mon dépôt » / « ma transaction » au singulier sans ID*
→ 3 chemins : dernier / liste / précis.

2 types pré-définis dans le prompt `compliance.general` :

- **A** — *« Parle-moi de mon compte »* → 3-4 angles couvrant
compte / transactions / performance / allocation.
- **B** — *« Mes infos »* → compte / KYC / documents.

### 14.5 Ton — chaleureux, jamais culpabilisant


| ✅ À utiliser                                                  | ❌ À éviter                  |
| ------------------------------------------------------------- | --------------------------- |
| « Pour bien te répondre, tu cherches plutôt à… ? »            | « Précise ta question »     |
| « Ça peut prendre plusieurs angles — sur lequel on creuse ? » | « Je n'ai pas compris »     |
| « Tu veux qu'on regarde quoi exactement ? »                   | « Reformule s'il te plaît » |


### 14.6 Anti-pattern

> **Le QCM est un outil de DERNIER RECOURS.** Mieux vaut une
> réponse pertinente directe qu'une clarification systématique.

**Ne PAS clarifier** quand :

- ≥ 1 mot-clé précis dans la demande,
- l'intention est déductible du contexte de conversation,
- la demande est très spécifique (un QCM serait condescendant).

### 14.7 Convention de QCM

Quand le LLM appelle `ask_user_question` pour clarifier :

- `prompt` : phrase courte (<200 chars), ton chaleureux.
- `options` : 3-4 reformulations claires sans jargon.
- **Pas d'`agent_hint`** (on reste dans le sub-agent courant — la
clarification est intra-agent, pas un dispatch).
- **Pas de `deep_link`** (la clarification pré-route le tour
suivant, elle ne navigue pas l'utilisateur).
- `allow_freeform: true` pour issue de secours.

Au tour suivant, le label cliqué devient le nouveau message user
→ contient maintenant un mot-clé précis → règle d'or matche →
action directe.

### 14.8 Évolution future (hors scope Phase 2c.5)

- Étendre le pattern à `compliance.registration` et
`compliance.remediation` (besoin moindre car plus directifs).
- Si besoin se confirme, extraire un tool dédié
`ask_clarification` (statut spécial dans le SSE,
instrumentation analytics propre) — pas avant validation
feedback terrain.
- Mesurer le ratio « QCM posé vs réponse directe » pour calibrer
l'agressivité de la règle d'or.

---

## 15. Phase 2c.6 + 2c.7 — Widgets chat & continuité de clarification

> **Statut :** ✅ livré (2026-05-03). Détail complet des widgets chat dans
> `[CHAT_EMBEDS_CATALOG.md](./CHAT_EMBEDS_CATALOG.md)`. Cette section
> documente uniquement l'intégration côté **agents Compliance** + le
> fix de continuité post-clarification (Patches A/C/D).

### 15.1 Phase 2c.6 — `instrument_detail_card`

Carte chat blanche affichant un instrument financier (logo, nom, prix
courant, perf 24h, sparkline, boutons Acheter/Vendre). Émise par les
agents `product` et `advisor` via le tool `show_instrument_card`
(symbole en argument : `BTC`, `ETH`, `SOL`, etc.). **Aucun changement**
côté `compliance.`* : ces sub-agents ne pushent pas la carte (anti-
tipping-off : un client en remediation ne doit pas être incité à
acheter du Bitcoin pendant un step-up KYC).

Le `compliance.general` peut **consulter** `product` via
`consult_specialist` avec `purpose='catalog_basics'` pour récupérer
des informations textuelles sur un instrument, mais le widget
`instrument_detail_card` reste réservé aux agents non-compliance.

### 15.2 Phase 2c.7 — Widgets `featured_articles_list` + `top_movers_crypto`

Deux nouveaux widgets pour enrichir les réponses des agents `market`
et `advisor` :

- `**featured_articles_list`** (tool `show_featured_articles`) :
liste 1-5 articles à la une filtrés par type (`NEWS`,
`ANALYSIS`, `RESEARCH`) et optionnellement par requête textuelle.
Chaque article ouvre `ArticleDetailScreen` via deep-link
`vancelian://app/article/{slug}`.
- `**top_movers_crypto`** (tool `show_top_movers`) : 1-10 cryptos
les plus mouvementées (gainers / losers / volume). Prix en EUR.
Chaque ligne ouvre `CryptoDetailScreen` via deep-link
`vancelian://app/instrument/{id}`.

Le `compliance.general` n'a **pas** ces tools (anti-tipping-off + pas
sa mission). Le `compliance.transactional` n'a pas non plus ces tools :
ses statistiques portent sur **les opérations du client**, pas sur
le marché global.

L'agent `market` est **réveillé en runtime** (cf.
`ASSISTANCE_RUNTIME_LOOP_AGENTS=compliance,product,advisor,market`).

### 15.3 Patches A/C/D — continuité de clarification

Suite à un audit de la conversation runtime `fc8a689f` (5 tours, 3
sub-agents traversés), trois patches ont été livrés pour fiabiliser
le pattern « Clarifier avant d'agir » (§14) une fois en production :

#### Patch D — keywords stats dans `diagnose_compliance_topic`

Ajout des keywords FR/EN ciblant les statistiques et le portefeuille
dans `_TRANSACTIONAL_KEYWORDS_RE` :

- `performance(s)` / `perf(s)` / `rendement(s)`
- `stats` / `statistique(s)` / `bilan(s)`
- `compter` / `combien` (intent count)
- `total(s)` / `totaux` / `totaliser` (intent amounts)
- `allocation(s)` / `portefeuille(s)` / `portfolio(s)`

Sans ces keywords, une question type *« quelle est ma performance ? »*
était routée sur `compliance.general` (filet de sécurité §13.7) au
lieu de `compliance.transactional` qui possède les tools `stats_`*.
Le filet continue de fonctionner (les mêmes tools sont aussi exposés
sur `general`), mais on gagne un tour : la réponse arrive directement
avec le bon format (table Markdown ou donut) sans bascule
intermédiaire. *(Détail : `_classify` priorise déjà transactional sur
remediation pour les keywords combinés — voir §2.3.)*

#### Patch A — continuité d'agent post-clarification

**Bug runtime observé.** Quand un sub-agent (`compliance.transactional`)
pose une clarification via `ask_user_question` avec des options
sémantiques (`id={list, count, amounts}`), le client clique → Flutter
renvoie `agent_hint='count'`. Or `count` n'est PAS un `agent_id`
valide → la branche `_decide_agent` qui vérifie
`hint in KNOWN_AGENT_IDS` rejetait le hint, loggait
`assistance.agent.invalid_hint hint='count'` et retombait sur le
router top-level qui reclassait depuis zéro → **cassure de la chaîne
agent** (le sub-agent qui avait posé la question ne voyait jamais la
réponse, et la conv sautait sur un autre agent — typiquement `advisor`
ou `compliance.general`).

**Fix.** Nouveau helper `_resolve_clarification_choice_hint(db, conversation_id, hint)` dans `service.py`. Quand `_decide_agent`
voit un hint qui n'est ni `resume_topic` ni un `agent_id` valide,
il consulte la DB :

1. Récupérer le **dernier message assistant** `message_type='choices'`.
2. Vérifier si `hint` correspond à l'`id` d'une de ses
  `message_payload.options[].id`.
3. Si oui, renvoyer `agent_used` de ce message (peut être un
  sub-agent comme `compliance.transactional`) → le tour reste sur
   le bon agent.
4. Sinon `None` → fallback router classique préservé.

`RouterDecision.reasoning='clarification_choice_continuity'`,
`confidence=1.0`. Visible dans les logs sous le format
`assistance.agent.clarification_choice_resolved conv=… hint=… → agent=…`.

#### Patch A2 — `use_runtime` reconnaît les sub-agents

Conséquence du Patch A : `decision.agent_id` peut désormais valoir
`compliance.transactional` (sub-agent direct), or
`assistance_runtime_loop_agents()` ne contient que les **top-levels**
(`compliance`, `product`, `advisor`, `market`). Le check
`decision.agent_id in assistance_runtime_loop_agents()` rejetait donc
le sub-agent et faisait fallback Phase 1 (sans tools).

Fix : on dérive le top-level (`split('.', 1)[0]`) pour le check de
runtime activé, tout en passant `decision.agent_id` (sub-agent) à
`tools_registry.tools_for(...)` et `load_agent_system_prompt(...)`
qui acceptaient déjà parfaitement les sub-agents.

#### Patch C — pas de modif Flutter

Le Patch A étant une correction **purement serveur**, le client
continue d'envoyer `agent_hint=<option.id>` comme avant (cf.
`_handleChoiceTapped` dans `search_screen.dart`). Aucun risque de
régression pour les anciennes versions de l'app.

### 15.4 Ce qui n'a PAS changé

- Les 4 sub-agents compliance (`registration`, `remediation`,
`transactional`, `general`) gardent leur scope et leurs tools.
- Le routing top-level (`router.classify(...)`) reste inchangé.
- Le pattern §14 « Clarifier avant d'agir » reste inchangé côté
prompts (Patches B.1/B.2/B.3 livrés en v1.2).
- Le contrat SSE et le format des messages persistés
(`message_type`, `message_payload`) sont strictement préservés.

---

## 11. Versioning de cette spec


| Date       | Version        | Phase                          | Changements                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ---------- | -------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 2026-05-02 | 0.1            | Pré-Phase 2b                   | Création initiale, draft avant validation user                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-05-02 | 0.9            | Post-validation                | Spec gelée après validation user (stream thinking + whitelist strict)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| 2026-05-03 | 1.0            | Phase 2b livrée                | Implémentation D.2 → D.9 complétée : `diagnose_compliance_topic`, dispatcher runtime, 4 sub-agents (`registration` / `remediation` / `transactional` / `general`), `action_cta_catalog`, SSE `thinking`, Flutter `AssistanceDeepLinkResolver`. 140 tests Phase 2b verts.                                                                                                                                                                                                                                                                                                                                                             |
| **1.1**    | **2026-05-03** | **Phase 2c livrée**            | **Orchestration multi-agents : `handoff_to_agent`, `consult_specialist`, `tour_shared_context` (whitelist explicite), vrai agent `product` consulté via `consult_specialist`, audit `agent_chain` + `consultations` dans `message_payload.metadata`. Garde-fous `MAX_CHAIN_DEPTH=1`, `MAX_CONSULTATIONS_PER_TOUR=3`. 530 tests assistance verts.**                                                                                                                                                                                                                                                                                   |
| **1.2**    | **2026-05-03** | **Phase 2c.5 livrée**          | **§13 Stats Lots 1+2+3 : 4 nouveaux tools sur `compliance.transactional` (et filet `compliance.general`) — `stats_transaction_counts`, `stats_transaction_amounts`, `stats_portfolio_performance` (markdown_table) et `stats_portfolio_allocation` (embed `portfolio_allocation_donut` + widget Flutter `PortfolioAllocationDonutEmbed` wrappant `DonutsChartBig`). §14 Pattern « Clarifier avant d'agir » : règle d'or basée sur le test du mot-clé précis, formalisé sur `compliance.transactional` et `compliance.general` via `ask_user_question` (sans nouveau tool, sans changement runtime). +67 tests verts, 0 régression.** |
| **1.3**    | **2026-05-03** | **Phases 2c.6 + 2c.7 livrées** | **§15 Widgets chat : `instrument_detail_card` (agents `product` + `advisor`), `featured_articles_list` + `top_movers_crypto` (agents `market` + `advisor`). Agent `market` réveillé. Patches A/C/D pour la continuité de clarification : helper `_resolve_clarification_choice_hint` (`service.py`), enrichissement `_TRANSACTIONAL_KEYWORDS_RE` (perf/rendement/stats/bilan/compter/allocation/portefeuille), `use_runtime` reconnaît les sub-agents par dérivation top-level. Détail catalogue : `CHAT_EMBEDS_CATALOG.md`.**                                                                                                       |


> **Règle :** toute évolution de la liste des topics, des tools, ou de
> la convention deep-link **doit** incrémenter la version.

