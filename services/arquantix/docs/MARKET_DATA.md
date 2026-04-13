# Market Data Ingestion — Documentation Critique

**⚠️ LIRE CE DOCUMENT AVANT TOUTE MODIFICATION DU SYSTÈME D'INGESTION**

Ce document explique précisément comment fonctionne l'ingestion de Market Data dans Arquantix pour éviter toute corruption de données.

---

## Vue d'Ensemble

### Provider Supporté

**Yahoo Finance UNIQUEMENT**

- Pas d'Alpha Vantage (déprécié)
- Pas d'autres providers
- Yahoo Finance est le seul provider actif

### Méthode d'Ingestion

**Ingestion manuelle via HTML table (copier-coller)**

Cette méthode est **intentionnelle**, pas un hack :
- Évite les rate limits Yahoo
- Contrôle total sur les données importées
- Reproductibilité garantie
- Pas de dépendance à des APIs instables

---

## Processus d'Ingestion

### Étape 1 : Préparation des Données

1. Aller sur Yahoo Finance : `https://finance.yahoo.com/quote/{TICKER}/history`
2. Sélectionner la période désirée
3. **Copier le tableau HTML** (sélectionner tout le tableau, pas juste les données)
4. Coller dans l'admin UI : `/admin/market-data` → Section "Import via HTML Table"

### Étape 2 : Parsing HTML

Le parser (`yahoo_html_parser.py`) :

1. **Trouve le premier `<table>`** dans le HTML
2. **Itère les lignes `<tr>`** dans `<tbody>`
3. **Détecte les types de lignes** :
   - **Ligne OHLCV** : 7 colonnes (Date, Open, High, Low, Close, Adj Close, Volume)
   - **Ligne événement** : Colonne avec `colspan` (dividende, split) → **SKIP**
4. **Parse les valeurs** :
   - Date : "Jan 8, 2026" → `2026-01-08`
   - Prix : "189.11" → `Decimal("189.11")`
   - Volume : "172,073,400" → `172073400` (int)
5. **Valide** : Skip les lignes avec dates invalides ou prix manquants

### Étape 3 : Upsert en Base de Données

**Tables impliquées** :

#### `market_data_instruments`

```sql
CREATE TABLE market_data_instruments (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,        -- Code interne (ex: "BTCUSD")
    name VARCHAR(200),
    asset_class VARCHAR(20) NOT NULL,           -- "crypto", "etf", "equity"
    weekend_tradable VARCHAR(10) NOT NULL,      -- "true" ou "false" (STRING!)
    provider VARCHAR(50) NOT NULL,              -- "yahoo"
    provider_symbol VARCHAR(50),                 -- Symbole Yahoo (ex: "BTC-USD")
    is_active VARCHAR(10) NOT NULL,              -- "true" ou "false"
    archived_at TIMESTAMP NULL,                  -- Date d'archivage
    created_at TIMESTAMP NOT NULL
);
```

**Upsert logic** :
- Si instrument existe (par `symbol`) → Update `provider`, `provider_symbol`, `asset_class`, `weekend_tradable`
- Si instrument n'existe pas → Create new

#### `market_data_bars_d1`

```sql
CREATE TABLE market_data_bars_d1 (
    instrument_id INTEGER NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume BIGINT NOT NULL,
    source VARCHAR(50) NOT NULL,                 -- "yahoo"
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (instrument_id, date),
    UNIQUE (instrument_id, date)
);
```

**⚠️ CRITIQUE** : Pas de colonne `adj_close` dans la table. `adj_close` est parsé depuis Yahoo mais **non stocké**.

**Upsert logic** :
- Si bar existe (par `instrument_id + date`) → **UPDATE** (remplace les valeurs)
- Si bar n'existe pas → **INSERT**
- **Pas de doublons** : La contrainte unique `(instrument_id, date)` garantit l'unicité

---

## Règles de Parsing

### Format de Date Accepté

- **Yahoo format** : "Jan 8, 2026", "January 8, 2026"
- **ISO format** : "2026-01-08" (si utilisateur paste autre source)

### Colonnes Requises

1. **Date** : Obligatoire, format ci-dessus
2. **Open** : Obligatoire, numeric
3. **High** : Optionnel (fallback = close si manquant)
4. **Low** : Optionnel (fallback = close si manquant)
5. **Close** : Obligatoire, numeric
6. **Adj Close** : Optionnel (parsé mais non stocké)
7. **Volume** : Obligatoire, integer (peut être 0)

### Lignes Ignorées

- **Lignes vides** : Skip
- **Lignes dividendes** : Format `<td>Dec 4, 2025</td><td colspan="6">0.01 Dividend</td>` → Skip
- **Lignes splits** : Format `<td>Dec 4, 2025</td><td colspan="6">2:1 Split</td>` → Skip
- **Lignes invalides** : Dates non parsables, prix manquants → Skip (avec raison dans `skipped`)

---

## Sécurité de l'Ingestion

### Pas de Preflight Check Actuellement

**⚠️ ATTENTION** : L'ingestion actuelle **remplace directement** les bars existants sans prévenir l'utilisateur.

**Comportement actuel** :
- Si une date existe déjà → **UPDATE** (écrase les valeurs)
- Si une date n'existe pas → **INSERT**

**Risque** : Si l'utilisateur paste une table avec des dates qui existent déjà, les données seront écrasées sans confirmation.

### Recommandations Futures

Pour rendre l'ingestion plus sûre, ajouter :

1. **Preflight check** : Détecter les overlaps avant import
2. **User choice** :
   - **Abort** : Annuler l'import
   - **Delta-only** : Importer uniquement les nouvelles dates
   - **Overwrite** : Remplacer les dates existantes (avec confirmation)

**Exemple de preflight** :
```python
# Détecter overlaps
existing_dates = set(
    db.query(MarketDataBarD1.date)
    .filter(MarketDataBarD1.instrument_id == instrument.id)
    .all()
)
new_dates = {bar.date for bar in parsed_bars}
overlaps = existing_dates & new_dates

if overlaps:
    # Demander confirmation à l'utilisateur
    return {
        "overlaps": list(overlaps),
        "action_required": "confirm_overwrite_or_delta"
    }
```

---

## Exemples d'Usage

### Exemple 1 : Import Initial (5 ans d'historique)

**Scénario** : Import initial de BTC-USD avec 5 ans de données

1. Aller sur `https://finance.yahoo.com/quote/BTC-USD/history`
2. Sélectionner période : 5 ans
3. Copier le tableau HTML
4. Coller dans admin UI
5. Remplir :
   - Instrument Code : `BTCUSD`
   - Asset Class : `CRYPTO`
   - Provider Symbol : `BTC-USD` (optionnel)
6. Cliquer "Validate & Import"

**Résultat** : Toutes les dates sont insérées (pas d'overlap).

### Exemple 2 : Extension d'Historique (5 ans → 10 ans)

**Scénario** : Étendre l'historique de 5 ans à 10 ans

1. Aller sur Yahoo Finance, sélectionner 10 ans
2. Copier le tableau HTML (contient les 5 ans existants + 5 ans nouveaux)
3. Coller dans admin UI

**⚠️ COMPORTEMENT ACTUEL** :
- Les 5 premières années seront **écrasées** (UPDATE)
- Les 5 nouvelles années seront **ajoutées** (INSERT)

**⚠️ RISQUE** : Si les données Yahoo ont changé (corrections), les anciennes données seront perdues.

**Recommandation** : Implémenter preflight check + delta-only mode.

### Exemple 3 : Mise à Jour Mensuelle

**Scénario** : Mettre à jour avec le dernier mois de données

1. Aller sur Yahoo Finance, sélectionner "1 Month"
2. Copier le tableau HTML
3. Coller dans admin UI

**Comportement** :
- Si dates existent déjà → UPDATE (met à jour avec dernières valeurs Yahoo)
- Si nouvelles dates → INSERT

**Cas d'usage valide** : Correction de données, mise à jour des dernières valeurs.

---

## Modèle de Données

### Instrument Model

**Champs critiques** :

- `symbol` : Code interne unique (ex: "BTCUSD")
- `provider` : **"yahoo"** (uniquement)
- `provider_symbol` : Symbole Yahoo (ex: "BTC-USD")
- `asset_class` : "crypto", "etf", "equity"
- `weekend_tradable` : **STRING "true" ou "false"** (pas boolean!)
- `is_active` : **STRING "true" ou "false"** (pas boolean!)

**⚠️ NE JAMAIS CHANGER** :
- Le type de `weekend_tradable` (doit rester STRING)
- Le type de `is_active` (doit rester STRING)

### Bar Model

**Champs stockés** :

- `instrument_id` : FK vers `market_data_instruments.id`
- `date` : Date du bar (DATE, pas TIMESTAMP)
- `open`, `high`, `low`, `close` : Prix (NUMERIC(20, 8))
- `volume` : Volume (BIGINT)
- `source` : **"yahoo"** (uniquement)

**Champs NON stockés** :

- `adj_close` : Parsé depuis Yahoo mais **non stocké** en DB

**Contrainte unique** : `(instrument_id, date)` → Garantit pas de doublons

---

## Filtrage des Instruments

### Backtests

Les backtests utilisent **uniquement** les instruments qui :

1. `provider = 'yahoo'`
2. `is_active = 'true'` (STRING)
3. Ont au moins un bar dans `market_data_bars_d1`

**Endpoint** : `GET /api/backtests/instruments?provider=yahoo&has_bars=true`

**Filtrage automatique** : Les instruments non-Yahoo ou inactifs ne sont **jamais** affichés dans le backtest builder.

---

## Gestion des Erreurs

### Erreurs de Parsing

- **Ligne invalide** : Skip avec raison dans `skipped` array
- **Date non parsable** : Skip
- **Prix manquant** : Skip
- **Table HTML introuvable** : Erreur 400 "No <table> element found"

### Erreurs de Base de Données

- **Contrainte unique violée** : Ne devrait jamais arriver (géré par upsert)
- **FK violation** : Instrument doit exister avant d'insérer des bars
- **Transaction rollback** : En cas d'erreur fatale, rollback complet

---

## Bonnes Pratiques

### Pour les Développeurs

1. **Ne jamais modifier le schéma** sans migration Alembic
2. **Ne jamais changer** le type de `weekend_tradable` ou `is_active` (STRING)
3. **Toujours utiliser upsert** (pas d'INSERT direct sans vérification)
4. **Tester avec DRY_RUN** avant modifications importantes

### Pour les Utilisateurs

1. **Vérifier la période** avant de coller (éviter overlaps non désirés)
2. **Vérifier le ticker** (s'assurer que c'est le bon instrument)
3. **Vérifier les résultats** après import (regarder le chart preview)

---

## Limitations Actuelles

1. **Pas de preflight check** : Overlaps non détectés avant import
2. **Pas de delta-only mode** : Toutes les dates sont traitées (UPDATE ou INSERT)
3. **Pas de confirmation** : Overwrite silencieux des données existantes
4. **adj_close non stocké** : Perdu après import (disponible uniquement dans `chart_series`)

---

## Évolutions Futures (si nécessaire)

### Preflight Check

```python
# Détecter overlaps
overlaps = detect_overlaps(instrument_id, parsed_bars)

if overlaps:
    return {
        "overlaps": overlaps,
        "action_required": "user_choice",
        "options": ["abort", "delta_only", "overwrite"]
    }
```

### Delta-Only Mode

```python
# Filtrer uniquement les nouvelles dates
existing_dates = get_existing_dates(instrument_id)
new_bars = [bar for bar in parsed_bars if bar.date not in existing_dates]
```

### Stockage adj_close

Si nécessaire, ajouter colonne `adj_close` via migration Alembic :
```sql
ALTER TABLE market_data_bars_d1 
ADD COLUMN adj_close NUMERIC(20, 8);
```

---

## Checklist Avant Modification

Avant de modifier le système d'ingestion, vérifier :

- [ ] J'ai lu ce document en entier
- [ ] Je comprends le comportement actuel (UPDATE sur overlap)
- [ ] J'ai testé avec DRY_RUN
- [ ] Je n'ai pas changé le type de `weekend_tradable` ou `is_active`
- [ ] J'ai créé une migration Alembic si changement de schéma
- [ ] J'ai documenté les changements

---

**Dernière mise à jour:** 2026-01-09

