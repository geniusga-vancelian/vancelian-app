# Markets – Checklist de validation E2E (live WS)

Validation rapide : FastAPI + worker Binance + Flutter Markets.

---

## 1. Lancer FastAPI

```bash
cd services/arquantix/api
uvicorn main:app --reload --port 8000
```

- Vérifier : `http://127.0.0.1:8000/docs` répond.

---

## 2. Lancer le worker Binance (WS ingestion)

Dans un **second terminal** :

```bash
cd services/arquantix/api
python3 scripts/run_binance_ws_ingestion.py
```

- Laisser tourner en continu (mise à jour de `market_data_latest_quotes`).
- Sans ce worker, les prix ne changeront pas dans l’app.

---

## 3. Ouvrir Markets dans l’app Flutter

- Lancer l’app (simulateur ou device).
- Aller sur l’onglet **Markets** (bottom nav).
- La section **Top Crypto** doit afficher la liste (onglet Populaires par défaut).

---

## 4. Vérifications

### Messages WS reçus

- En **mode debug**, regarder la console Flutter :
  - `[MarketDataWS] subscribe: ws://127.0.0.1:8000/ws/market-data?symbols=...`
  - Puis régulièrement : `[MarketDataWS] message #1: N quotes`, `message #5: …`, etc.
- Si ces logs n’apparaissent pas : problème de connexion WS (URL, backend, réseau).

### Prix qui changent

- Les montants dans la liste (ex. Bitcoin, Ethereum) doivent évoluer toutes les quelques secondes.
- Si les messages WS arrivent mais les prix ne bougent pas : vérifier que `run_binance_ws_ingestion.py` tourne bien.

### Pas de double connexion au changement d’onglet

- Changer d’onglet : **Populaires** → **Top Gainers** → **Top Losers**.
- Dans les logs : une nouvelle ligne `[MarketDataWS] subscribe: ...` à chaque changement (nouvelle souscription aux symboles de l’onglet).
- Pas de multiplication de connexions (pas des dizaines de `subscribe` en boucle). Un seul `subscribe` par changement d’onglet est attendu.

---

## Résumé

| Étape | Commande / action | OK |
|-------|-------------------|-----|
| 1 | `uvicorn main:app --reload --port 8000` | ☐ |
| 2 | `python3 scripts/run_binance_ws_ingestion.py` (2e terminal) | ☐ |
| 3 | Ouvrir Markets dans l’app | ☐ |
| 4a | Logs `[MarketDataWS] message #N` visibles | ☐ |
| 4b | Prix qui changent dans la liste | ☐ |
| 4c | Un seul `subscribe` par changement d’onglet, pas de double connexion | ☐ |
