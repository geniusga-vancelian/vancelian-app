# Page de Comparaison de Backtests

## Vue d'ensemble

La page `/admin/backtests/compare` permet de comparer visuellement jusqu'à 10 backtests en superposant leurs courbes NAV (base100) et en affichant un tableau comparatif de statistiques.

---

## Endpoints Backend (FastAPI)

### GET /api/backtests

**Description**: Liste paginée et filtrable des backtests

**Query Parameters**:
- `status` (optional): Filter par statut ("SUCCESS", "FAILED", "PENDING")
- `strategy_type` (optional): Filter par type de stratégie
- `q` (optional): Recherche par nom ou ID
- `date_from` (optional): Date de début (YYYY-MM-DD)
- `date_to` (optional): Date de fin (YYYY-MM-DD)
- `limit` (optional, default 50): Nombre de résultats par page
- `offset` (optional, default 0): Offset pour pagination

**Response**:
```json
{
  "runs": [
    {
      "id": 90,
      "name": "Run #90",
      "status": "SUCCESS",
      "strategy_type": "CPPI",
      "created_at": "2024-12-XX...",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "effective_start_date": "2024-01-01",
      "effective_end_date": "2024-12-31",
      "rebalance": "weekly",
      "universe_label": "Bundle Crypto" or "2 instruments",
      "instrument_count": 2
    },
    ...
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

**Tri**: Par `created_at` DESC (plus récents en premier)

---

### POST /api/backtests/compare

**Description**: Compare plusieurs backtests (min 1, max 10)

**Request Body**:
```json
{
  "run_ids": [90, 91, 92],
  "align_mode": "intersection"  // ou "union"
}
```

**Validation**:
- `run_ids`: Array d'entiers, min 1, max 10
- `align_mode`: "intersection" ou "union" (default: "intersection")

**Response**:
```json
{
  "runs": {
    "90": {
      "id": 90,
      "name": "Run #90",
      "strategy_type": "CPPI",
      "strategy_params_json": {...},
      "universe_label": "Bundle Crypto",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "effective_start_date": "2024-01-01",
      "effective_end_date": "2024-12-31",
      "rebalance": "weekly",
      "instrument_ids_json": [1, 2],
      "bundle_id": null
    },
    ...
  },
  "series": [
    {
      "date": "2024-01-01",
      "values": {
        "90": 100.0,
        "91": 100.0,
        "92": null  // si align_mode="union" et date manquante
      }
    },
    ...
  ],
  "stats": {
    "90": {
      "annualized_performance": 0.15,
      "max_drawdown": -0.10,
      "sharpe_ratio": 1.2,
      "calmar_ratio": 1.5
    },
    ...
  }
}
```

**Codes de statut**:
- `200`: Succès
- `400`: Validation failed (run_ids vides ou align_mode invalide)
- `404`: Un ou plusieurs run_ids non trouvés
- `422`: Plus de 10 run_ids

---

## Règles d'alignement des dates

### Mode "intersection" (par défaut)

- **Logique**: Retourne uniquement les dates présentes dans **TOUS** les runs
- **Usage**: Pour comparer des backtests sur des périodes identiques
- **Exemple**: Si run 90 a [2024-01-01, 2024-01-02, 2024-01-03] et run 91 a [2024-01-02, 2024-01-03, 2024-01-04], alors l'intersection = [2024-01-02, 2024-01-03]

### Mode "union"

- **Logique**: Retourne **TOUTES** les dates présentes dans au moins un run
- **Valeurs manquantes**: Si un run n'a pas de données pour une date, la valeur est `null`
- **Usage**: Pour comparer des backtests sur des périodes différentes (avec trous)
- **Exemple**: Si run 90 a [2024-01-01, 2024-01-02] et run 91 a [2024-01-02, 2024-01-03], alors l'union = [2024-01-01, 2024-01-02, 2024-01-03], et run 91 aura `null` pour 2024-01-01, run 90 aura `null` pour 2024-01-03

---

## Statistiques comparatives

### Annualized Performance

**Définition**: Return annualisé (en décimal, ex: 0.15 = 15%)

**Source**:
1. Si disponible en DB (`BacktestMetrics`, scope="portfolio", key="annualized_return"): utilise cette valeur
2. Sinon, calculé depuis `nav_base100`:
   - `total_return = (last_nav / first_nav) - 1.0`
   - `annualized_return = ((1 + total_return) ^ (365.0 / days)) - 1.0`

### Max Drawdown

**Définition**: Drawdown maximum (en décimal, négatif, ex: -0.10 = -10%)

**Source**:
1. Si disponible en DB (`BacktestMetrics`, scope="portfolio", key="max_drawdown"): utilise cette valeur
2. Sinon, calculé depuis `nav_base100`:
   - Parcours de la série, maintient un "peak" (maximum jusqu'à présent)
   - Pour chaque point: `drawdown = (nav - peak) / peak`
   - `max_drawdown` = minimum de tous les drawdowns

### Sharpe Ratio

**Définition**: Ratio de Sharpe (annualisé, sans facteur de risque)

**Source**:
1. Si disponible en DB (`BacktestMetrics`, scope="portfolio", key="sharpe_ratio"): utilise cette valeur
2. Sinon, calculé depuis `nav_base100`:
   - Calcul des returns quotidiens: `ret_i = (nav_i / nav_{i-1}) - 1.0`
   - `mean_return = mean(returns)`
   - `std_return = std(returns, ddof=1)`
   - `sharpe_ratio = (mean_return * sqrt(252)) / (std_return * sqrt(252))` (simplifié)

### Calmar Ratio

**Définition**: Ratio de Calmar = `annualized_return / abs(max_drawdown)`

**Formule**:
```
calmar_ratio = annualized_performance / abs(max_drawdown)
```

**Gestion des cas spéciaux**:
- Si `max_drawdown == 0`: `calmar_ratio = null` (division par zéro impossible)
- Si `max_drawdown < 0` (normal): calcul direct

**Source**:
1. Si disponible en DB (`BacktestMetrics`, scope="portfolio", key="calmar_ratio"): utilise cette valeur
2. Sinon, calculé depuis `annualized_performance` et `max_drawdown`:
   - `calmar_ratio = annualized_performance / abs(max_drawdown)` si `max_drawdown != 0`
   - `calmar_ratio = null` sinon

---

## Limites

- **Maximum de runs comparables**: 10 (validation au niveau API)
- **Minimum de runs comparables**: 1 (permis, mais trivial)

---

## Frontend

### Page: `/admin/backtests/compare`

**Layout**: 2 colonnes (grid lg:grid-cols-2)
- **Colonne gauche**: Bibliothèque de backtests (filtres, liste, sélection)
- **Colonne droite**: Résultats de comparaison (chart + tableau stats)

### Composants

- **MultiBacktestChart**: Graphique principal superposé (Recharts LineChart)
  - Une ligne par run sélectionné
  - Legend cliquable (afficher/masquer)
  - Format NAV base100

- **Tableau de stats**: Affiche pour chaque run:
  - Nom
  - Stratégie
  - Univers (bundle ou instruments)
  - Annualized Performance (%)
  - Max DD (%)
  - Sharpe Ratio
  - Calmar Ratio
  - Bouton "Open run" (lien vers `/admin/backtests?run_id=XX`)

### API Routes (Next.js)

- `GET /api/backtests`: Proxy vers FastAPI GET /api/backtests
- `POST /api/backtests/compare`: Proxy vers FastAPI POST /api/backtests/compare

---

## Exemples d'utilisation

### Comparer 2 runs CPPI

1. Sélectionner 2 runs dans la liste (max 10)
2. Cliquer "Comparer"
3. Chart montre 2 courbes NAV superposées
4. Tableau compare les stats (Sharpe, Calmar, etc.)

### Comparer runs avec périodes différentes

1. Sélectionner des runs avec dates différentes
2. Choisir `align_mode="union"` (toggle)
3. Chart montre toutes les dates (avec `null` où manquant)
4. Recharts gère automatiquement les trous (`connectNulls={false}`)

---

**Dernière mise à jour**: 2024-12-XX
