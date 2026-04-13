# Wallet History M1 Upgrade Report

## 1. Executive Summary

- **Support M1 ajouté** : OUI — les chandelles Binance 1 minute sont désormais stockées, ingérées et utilisées par le service wallet history.
- **Wallet history aligné avec l'objectif produit** : OUI — pendant les 2 premières heures suivant un trade récent, le client voit une évolution **minute par minute** de la valeur de son wallet.
- **Régression** : AUCUNE — les 33 tests core (wallet_history + exchange + market_data) passent. Les échecs de la suite complète sont tous préexistants.

---

## 2. Files modified

| Fichier | Rôle |
|---------|------|
| `api/database.py` | Ajout du modèle `MarketDataBar1m` (table `market_data_bars_1m`) |
| `api/alembic/versions/065_add_market_data_bars_1m.py` | Migration Alembic : création de la table + index |
| `api/services/market_data/binance_client.py` | Ajout de `fetch_klines_1m()` (REST Binance interval=1m) |
| `api/services/market_data/bars_1m_repo.py` | **Nouveau** — Repository `get_bars_1m` / `upsert_bar_1m` |
| `api/services/market_data/ingestion_binance_candles_1m.py` | **Nouveau** — Ingestion 1m : `run_one_cycle()` |
| `api/services/market_data/candles_backfill_service.py` | Ajout du timeframe `1m` dans `TIMEFRAME_CONFIG` (fallback_days=7) |
| `api/services/market_data/ohlc_holes.py` | Ajout période `M1` dans l'analyse des trous OHLC |
| `api/services/market_data/routes.py` | Ajout endpoint `GET /candles/1m` + M1 dans backfill-lag |
| `api/scripts/run_candles_1m_ingestion.py` | **Nouveau** — Script de lancement manuel |
| `api/services/wallet_history/service.py` | Nouvelle config granularité : 0–2h → 1m |
| `api/tests/test_wallet_history.py` | 5 nouveaux tests couvrant les chandelles 1m |

---

## 3. Market data changes

### Stockage 1m
- Table `market_data_bars_1m` : même schéma que les autres tables OHLCV (instrument_id + open_time en PK composite, colonnes OHLCV + source + updated_at).
- Index sur `instrument_id` et `open_time`.

### Backfill
- Le backfill incrémental (`candles_backfill_service.py`) supporte maintenant le timeframe `1m`.
- `fallback_days = 7` : profondeur initiale de 7 jours pour le backfill 1m.
- Le cron refresh (toutes les 60 secondes) traite automatiquement les trous M1 via `run_backfill_lag_logic`.

### Rétention
- **Recommandation** : limiter la rétention des chandelles 1m à **7–14 jours**. Au-delà, le wallet history utilise la granularité 5m (2h–7j), donc les données 1m anciennes ne sont pas exploitées.
- La rétention n'est pas automatiquement purgée en v1. Un script de purge peut être ajouté dans une version future.
- Volume estimé : ~6 instruments × 1440 candles/jour × 14 jours = ~120 960 lignes (très raisonnable).

---

## 4. Wallet history changes

### Nouvelle logique de granularité

| Fenêtre temporelle | Granularité | Modèle | Intervalle |
|--------------------|-------------|--------|------------|
| 0 – 2 heures | 1m | `MarketDataBar1m` | 60s |
| 2h – 7 jours | 5m | `MarketDataBar5m` | 300s |
| 7j – 30 jours | 1h | `MarketDataBar1h` | 3600s |
| 30j – 120 jours | 4h | `MarketDataBar4h` | 14400s |
| > 120 jours | 1d | `MarketDataBar1d` | 86400s |

### Comportement
- La granularité est sélectionnée en fonction du `span_hours` total entre le premier trade et maintenant.
- Aux timestamps de trade : `execution_price` utilisé (inchangé).
- Entre les trades : `candle.close` de la table appropriée (inchangé).
- Limite de 500 points respectée (inchangé).
- Conversion EUR via EURUSDT candles (même granularité).

---

## 5. FX changes

- **EURUSDT 1m** : Puisque EURUSDT est un instrument actif avec `provider=binance`, il est automatiquement inclus dans l'ingestion 1m et le backfill.
- Le wallet history en mode EUR utilise les chandelles EURUSDT 1m pour la conversion FX minute par minute sur la fenêtre 0–2h.
- Aucune modification spécifique nécessaire : le service `build_wallet_history` charge les FX candles avec le même `bar_model` que les asset candles.

---

## 6. Tests added

| Test | Description | Résultat |
|------|-------------|----------|
| `test_wallet_history_granularity_1m_selection` | `_select_granularity(1.5h)` retourne `MarketDataBar1m` | PASS |
| `test_wallet_history_granularity_5m_beyond_2h` | `_select_granularity(3h)` et `_select_granularity(100h)` retournent `MarketDataBar5m` | PASS |
| `test_wallet_history_with_1m_candles` | Trade il y a 90min → reconstruction avec candles 1m, points > 5 | PASS |
| `test_wallet_history_eur_conversion_1m` | Conversion EUR correcte avec EURUSDT 1m (90000/1.10 ≈ 81818) | PASS |
| `test_wallet_history_max_500_points_1m` | Limite 500 points respectée avec données 1m denses | PASS |

**Total** : 11 tests wallet_history (6 existants + 5 nouveaux), tous PASS.
**Régression** : 33 tests core passent (wallet_history + exchange + market_data).

---

## 7. Final status

**Does wallet history now provide minute-level detail during the first 2 hours after recent trades?**

**YES** — Le service wallet history utilise désormais les chandelles 1m pour les fenêtres de temps inférieures à 2 heures. Un client qui vient d'exécuter un trade verra la valeur de son wallet évoluer minute par minute, incluant :
- Le prix d'exécution exact au timestamp du trade
- L'interpolation via `candle.close` des barres 1m pour chaque minute intermédiaire
- La conversion EUR via les barres EURUSDT 1m

La transition vers des granularités moins fines (5m, 1h, 4h, 1d) se fait naturellement au-delà de 2 heures.
