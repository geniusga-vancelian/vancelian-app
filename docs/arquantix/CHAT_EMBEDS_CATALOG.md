# CHAT EMBEDS CATALOG — Phase 2c.7

> Catalogue des **widgets visuels** que les agents IA peuvent attacher à
> leurs réponses texte pour enrichir une bulle assistant (au-delà du
> Markdown). Pendant longtemps, le chat était purement « texte
> Markdown » ; à partir de Phase 2c.2 (`transaction_detail`) puis
> Phase 2c.5/2c.6 (`portfolio_allocation_donut`, `instrument_detail_card`),
> chaque réponse peut transporter un ou plusieurs **embeds** : blocs
> structurés rendus par un widget dédié côté Flutter.
>
> Phase 2c.7 généralise le pattern : on documente ici le **catalogue**,
> les **conventions** et la **roadmap** de tous les widgets chat.

---

## 1. Pattern technique

### 1.1 Backend — émission d'un embed

Un tool L0 (read-only) qui veut afficher un widget appelle simplement :

```python
embed: dict[str, Any] = {
    "type": "<embed_type>",     # discriminateur côté Flutter
    "summary": "...",            # optionnel, intro composée serveur
    # … champs spécifiques au type …
    "actions": [                 # optionnel, deep-links whitelistés
        build_action("kind", params={...}),
    ],
}
ctx.embeds_to_emit.append(embed)
```

Le runtime aggrège tous les embeds émis pendant le tour et les envoie au
client via :
- `AgentEvent(type='done', embeds=[...])` (live SSE) ;
- `message_payload.embeds[]` (persistance + replay historique).

### 1.2 Frontend — rendu d'un embed

Le `search_screen` dispatche chaque embed via `_buildEmbed(emb)` qui
fait un switch sur `emb.type`. Les types inconnus du client sont
**ignorés silencieusement** (rétro-compat : on peut introduire un
nouveau type côté backend sans bumper les clients existants).

Chaque widget est enveloppé dans un `_CardShell` standard (radius,
padding, shadow alignés) pour l'homogénéité visuelle dans les bulles
assistant.

### 1.3 Self-contained vs complémentaire

| Mode | Exemples | Comportement |
|---|---|---|
| **Self-contained** | `transaction_detail`, `portfolio_allocation_donut` | La bulle texte LLM **est masquée** au profit de l'embed seul (tout est dans le widget). Le serveur peut composer un `summary` injecté en haut du widget. |
| **Complémentaire** | `instrument_detail_card`, `featured_articles_list`, `top_movers_crypto` | Le LLM rédige son texte explicatif **au-dessus** ; le widget porte les chiffres factuels et les CTAs. |

Côté Flutter, un embed est self-contained ssi listé dans
`_embedIsSelfContained()` (search_screen).

### 1.4 Whitelist deep-links

Toutes les actions (`actions[]`) embarquées dans un embed sont des
deep-links produits par `action_cta_catalog.build_action(kind, ...)`.
**Aucun URL libre n'est jamais accepté.** Le resolver Flutter
(`AssistanceDeepLinkResolver`) reconnaît un set fini d'intents
(`registration_resume`, `deposit`, `wallet`, `transactions`,
`profile`, `instrument`, `article`, …).

### 1.5 Filtres LLM — toujours whitelistés

Quand un tool accepte des paramètres (ex. `kind`, `direction`,
`limit`), il **valide chaque champ contre une whitelist**. Aucune
chaîne libre acceptée. Les valeurs invalides → tool retourne
`{"error": "invalid_filter", ...}` au LLM, qui peut soit reformuler
soit répondre en texte seul.

### 1.6 Sécurité & anti-tipping-off

- Les embeds visibles côté chat ne doivent jamais exposer de **score
  interne** (risk score, KYC tier, anti-fraude…).
- Pour les données client (transactions, positions), `read_*` filtre
  sur le `client_id` du `ToolContext` (jamais sur un argument LLM).
- Les données publiques (articles, prix marché, offres, news) n'ont
  pas de contrainte anti-tipping-off mais doivent rester **stables**
  (idempotence des tools).

---

## 2. Catalogue actuel (Phase 2c.7)

### 2.1 `transaction_detail` — Phase 2c.2

- **Tool** : `read_transaction_detail(transaction_id)`
- **Agents** : `compliance.transactional`, `compliance.general`
- **Mode** : self-contained (LLM intro masquée si trivial)
- **Contenu** : récap, tableau Markdown détaillé, CTAs « Voir la
  transaction » + « Télécharger le relevé ».
- **Deep-links** : `view_transaction_detail`,
  `download_transaction_statement`.

### 2.2 `portfolio_allocation_donut` — Phase 2c.5

- **Tool** : `stats_portfolio_allocation()`
- **Agents** : `compliance.transactional`, `compliance.general`
- **Mode** : self-contained
- **Contenu** : donut chart fiat / crypto-direct / bundles, NAV total,
  pourcentages.

### 2.3 `instrument_detail_card` — Phase 2c.6

- **Tool** : `show_instrument_card(symbol)`
- **Agents** : `product`, `advisor`
- **Mode** : complémentaire (LLM peut écrire explication contextuelle)
- **Contenu** : logo, nom, prix, perf 24h, mini-sparkline, CTAs
  Acheter / Vendre.
- **Symbols supportés** : BTC, ETH, USDT, USDC, SOL, XRP, ADA, AVAX,
  DOT, DOGE, TRX.
- **Deep-links** : `buy_instrument`, `sell_instrument`.

### 2.4 `featured_articles_list` — Phase 2c.7 ★ nouveau

- **Tool** : `show_featured_articles(kind, limit?, query?)`
- **Agents** : `market`, `advisor`, `product`, `compliance.general`
- **Mode** : complémentaire (LLM rédige la synthèse, widget montre
  3 articles à lire)
- **Contenu** : titre du bloc + liste de 1 à 5 articles (cover, titre,
  date, temps de lecture). Chaque ligne est cliquable et ouvre le
  lecteur d'article via deep-link.
- **Param `kind`** (whitelist stricte) :
  - `NEWS` → actu marché (`articles.article_type='NEWS'`).
  - `ANALYSIS` → analyses & opinions
    (`articles.article_type='ANALYSIS'`).
  - `RESEARCH` → notes de recherche
    (`articles.article_type='RESEARCH'`).
- **Param `query`** (optionnel) : mots-clés pour filtrage best-effort
  sur titre + standfirst (LIKE insensible à la casse). Si vide → top
  X articles publiés les plus récents avec `is_featured=true` en
  priorité, fallback sur les plus récents.
- **Param `limit`** : 1 à 5 (défaut 3).
- **Deep-link** : `open_article` (`vancelian://app/article/{slug}`).

### 2.5 `top_movers_crypto` — Phase 2c.7 ★ nouveau

- **Tool** : `show_top_movers(direction, limit?)`
- **Agents** : `market`, `advisor`
- **Mode** : complémentaire
- **Contenu** : titre du bloc + liste de 3 à 5 cryptos avec logo,
  symbol, prix, variation 24h colorée. Chaque ligne ouvre la carte
  instrument via deep-link.
- **Param `direction`** (whitelist stricte) :
  - `gainers` → top hausses 24h.
  - `losers` → top baisses 24h.
  - `volume` → top volumes 24h.
- **Param `limit`** : 1 à 10 (défaut 5).
- **Deep-link** : `view_instrument` (`vancelian://app/instrument/{id}`).

---

## 3. Roadmap — backlog d'embeds

Embeds identifiés mais non livrés en Phase 2c.7. Chacun nécessite un
audit plus poussé des endpoints existants (offers, projects,
positions client, etc.) et des prompts agents pour valider le bon
trigger d'invocation.

| Embed | Source de données | Agent cible | Effort |
|---|---|---|---|
| `crypto_bundles_pitch` | tables `bundles` + `bundle_allocations` | `advisor`, `product` | ★★ |
| `featured_offer_card` | `articles[articleType='OFFER']` ou table `offers` | `advisor`, `product` | ★ |
| `exclusive_offers_carousel` | idem (3-5 offres) | `advisor`, `market` | ★★ |
| `investment_card` | tables `pe_positions` + valuations | `advisor`, `compliance.transactional` | ★★★ |
| `property_card` | `articles[articleType='PROJECT']` ou table `projects` | `product`, `advisor` | ★★ |
| `setup_progress_card` | `read_registration_progress()` existant | `compliance.registration`, `compliance.general` | ★★ |
| `news_company_list` | variante de `featured_articles_list` filtrée `isCompanyNews=true` | `market` | ★ |

**Critère d'ajout au catalogue** : un embed n'est ajouté que s'il
apporte une valeur claire que le Markdown ne sait pas restituer
(visuel riche, CTA contextuel, fraîcheur des données serveur).

---

## 4. Conventions de design (à respecter pour tout nouvel embed)

1. **Naming** : `<noun>_<view>` (`featured_articles_list`,
   `top_movers_crypto`, `setup_progress_card`).
2. **Hauteur** : ≤ 400 px dans une bulle assistant — au-delà, scroll
   gênant côté UX. Préférer `limit` plus restrictif et CTA « voir
   tout ».
3. **Au moins un CTA cliquable** par embed. Sinon c'est de la
   décoration — préférer du Markdown texte.
4. **Pas de fetch côté Flutter** par défaut : les données affichées
   sont **embedées** dans le payload serveur (pattern « snapshot »).
   Exception : si la fraîcheur est critique (ex. prix live), le
   widget peut fetch en complément, mais doit rester rendable sans.
5. **Réutiliser le DS** : tout nouveau widget chat **wrappe** un
   composant existant du DS (`NewsCard`, `BlogALaUne`,
   `InstrumentDetailHeroCtaRow`, `DonutsChartBig`, …) plutôt que de
   ré-implémenter l'UI from scratch.
6. **Tester le rendu vide** : si l'embed n'a pas de données à
   afficher (ex. 0 article match), le tool **ne doit pas** créer
   l'embed (laisser le LLM répondre en texte seul). Côté Flutter, si
   un getter critique renvoie vide, retourner `SizedBox.shrink()`.

---

## 5. Process pour ajouter un embed

1. **Audit** : composant DS réutilisable ? Endpoint backend dispo ?
   Filtres pertinents ?
2. **Spec** : ajouter une entrée à ce document (§ 2 ou § 3) avec
   tool, agents, mode, contenu, params.
3. **Backend** :
   - Tool `services/assistance/agents/tools/<area>/<show_X>.py`.
   - `action_cta_catalog.py` : nouveau `kind` si nécessaire.
   - `registry.py` : enregistrement pour le(s) agent(s) cible(s).
   - Prompt système agent : section dédiée + exemples d'usage.
4. **Frontend** :
   - `chat_api.dart` : getters typés pour le payload de l'embed.
   - Nouveau widget `<feature>/presentation/widgets/<name>_embed.dart`.
   - `search_screen.dart` : case dans `_buildEmbed()`.
   - Si nouveau deep-link : `assistance_deep_link_resolver.dart` +
     `knownIntents`.
5. **Doc** : mettre à jour cette section + ajouter dans le prompt
   système agent.
6. **Lints** : `flutter analyze` + tests Python ne doivent pas
   régresser.
