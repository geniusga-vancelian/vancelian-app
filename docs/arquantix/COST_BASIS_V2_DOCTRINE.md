# Cost Basis V2 — Doctrine

**Date :** 2026-05-29  
**Statut :** normatif pour toute extension PRU / P&L / charts  
**Implémentation :** [COST_BASIS_V2_IMPLEMENTATION_REPORT.md](./COST_BASIS_V2_IMPLEMENTATION_REPORT.md)  
**Audit initial :** [COST_BASIS_EXECUTION_PRICE_AUDIT.md](./COST_BASIS_EXECUTION_PRICE_AUDIT.md)

---

## 1. Principe fondateur

Le **PRU (prix de revient unitaire)** et le **WAC** ne doivent naître que d’un **événement économique d’échange** : acquisition ou cession d’un actif contre une contrepartie valorisable à l’instant T.

Un **simple dépôt**, un **retrait**, un **transfert de poche** ou un **mouvement de custodie** ne crée **pas** de nouveau PRU.

> **Règle courte :** pas d’échange économique → pas de ligne `cost_basis_executions`.

---

## 2. Périmètre de `cost_basis_executions`

### Entrent dans la table (événements éligibles)

| Type | `event_kind` typique | Exemples |
| --- | --- | --- |
| Swap / trade | `acquisition`, `disposal` | Li.FI USDC → AAVE, exchange BUY/SELL |
| Rebalancing bundle | `acquisition`, `disposal` | Leg allocation USDC → ETH dans bundle X |
| Crypto ↔ crypto | `disposal` + `acquisition` | ETH → AAVE (jambe sortie + entrée) |
| Liquidation forcée | `disposal` | Collatéral saisi / vente forcée → P&L réalisé |

**Providers actuels :** `lifi`, `bundle_lifi`, `exchange`.  
**Extensions futures éligibles :** ordres RWA, OTC, exécutions exchange traditionnelles — **même critère** (échange économique).

### N’entrent pas dans la table

| Type | Traitement attendu | Pourquoi |
| --- | --- | --- |
| Dépôt vault (Morpho, Ledgity, …) | Couche **position / mouvement** | Transfert de poche ; PRU de l’actif **inchangé** |
| Retrait vault | Couche **position / mouvement** | Transfert retour ; pas de cession économique du PRU |
| Borrow (ex. USDC contre cbBTC) | Couche **liability / dette** | Création de dette USDC, **pas** acquisition USDC avec PRU |
| Yield / rewards / intérêts vault | Couche **revenu / yield** | Performance / revenu, **pas** PRU classique |
| Dépôt fiat / virement | Ledger / cash | Pas d’actif crypto échangé |
| Transfert interne wallet ↔ wallet | `position_movements` | Même PRU, autre emplacement |

**Interdit explicitement :** brancher Morpho / Ledgity (deposit / withdraw simples) sur `cost_basis_executions` pour « inventer » un PRU vault.

---

## 3. Exemples canoniques

| Scénario | PRU actif | Cost basis V2 |
| --- | --- | --- |
| USDC déjà détenu → dépôt Morpho | PRU USDC **inchangé** | Aucune ligne |
| cbBTC détenu → dépôt Morpho collatéral | PRU cbBTC **inchangé** | Aucune ligne |
| Borrow USDC contre cbBTC | Dette USDC (liability) | Aucune acquisition USDC |
| Bundle rebalance USDC → AAVE | PRU AAVE **dans le bundle** | `bundle_lifi` + scope bundle |
| Li.FI self-trading USDC → AAVE | PRU AAVE **direct** | `lifi` + scope direct |
| Liquidation collatéral | P&L réalisé sur l’actif cédé | `disposal` (provider à définir) |

---

## 4. PRU par actif et par scope (pas de PRU « bundle unique »)

Un **bundle** est multi-actifs. Il peut exposer :

- **NAV** agrégée
- **Performance globale** du portefeuille
- **P&L global** bundle

Mais le **PRU reste toujours par actif et par scope**, par exemple :

| Scope | Clé logique | Exemple |
| --- | --- | --- |
| Mon Trading | `portfolio_scope=direct` | AAVE self-trading |
| Bundle | `portfolio_scope=bundle` + `portfolio_id` | AAVE dans bundle X |
| Global (legacy) | agrégation UI seulement | Ne pas mélanger les scopes dans le WAC |

```
AAVE (direct)     → WAC depuis executions scope=direct
AAVE (bundle X)   → WAC depuis executions scope=bundle, portfolio_id=X
```

**Pas de PRU unique « bundle »** pertinent pour un actif sous-jacent.

---

## 5. Couches complémentaires (hors `cost_basis_executions`)

Pour vaults, emprunts et revenus, une **couche séparée** est recommandée — **ne pas surcharger** `cost_basis_executions` :

| Couche (cible) | Rôle | Exemples |
| --- | --- | --- |
| `position_movements` | Transferts sans changement de PRU | Wallet → vault, vault → wallet |
| `vault_positions` | Encours vault (shares, underlying) | Parts ERC-4626 Morpho |
| `liabilities` | Dettes (borrow, Lombard, …) | USDC emprunté vs cbBTC collatéral |
| `yield_events` | Revenus, rewards, intérêts | Yield Morpho, incentives |

**Charts épargne / DeFi vault :** NAV vault, performance vault, yield cumulé — **pas** la courbe PRU d’un actif déposé.

**Charts wallet crypto / bundle :** `performance_value` depuis `cost_basis_executions` (trades + rebalancing) — voir rapport §14.

---

## 6. Matrice décisionnelle (implémentation)

```
Événement reçu
    │
    ├─ Échange économique (contrepartie + quantité + prix à T) ?
    │       └─ OUI → cost_basis_executions (acquisition | disposal)
    │
    ├─ Transfert de custodie (même PRU) ?
    │       └─ OUI → position_movements / vault_positions
    │
    ├─ Création ou remboursement de dette ?
    │       └─ OUI → liabilities
    │
    ├─ Revenu passif (yield, reward) ?
    │       └─ OUI → yield_events
    │
    └─ Sinon → ledger / audit uniquement
```

---

## 7. Conséquences produit

| Surface UI | Métrique PRU | Source |
| --- | --- | --- |
| Marché / détail crypto (holding) | PRU par actif, scope direct | `cost_basis_executions` + WAC |
| Détail actif dans bundle | PRU par actif, scope bundle | Idem, filtre `portfolio_id` |
| Épargne Morpho / Ledgity | **Pas** de PRU vault inventé | NAV / APY / historique vault |
| Lombard borrow | Dette + collatéral | `liabilities` (futur), pas PRU borrow |

---

## 8. Anti-patterns (à ne pas faire)

1. **Dépôt vault = acquisition** → double comptage ou PRU faux.
2. **Borrow = BUY USDC** → PRU USDC artificiellement bas.
3. **Un seul PRU « bundle »** pour plusieurs actifs → incomparable et faux en rebalance.
4. **Extension Morpho via `provider_source=morpho` sur deposit** dans `cost_basis_executions` → viole la doctrine ; utiliser les couches §5.

---

## 9. Références code (état 2026-05-29)

| Composant | Fichier | Conforme doctrine |
| --- | --- | --- |
| Ingestion Li.FI direct | `ingest_lifi.py` | Oui (swap) |
| Ingestion bundle rebalance | `ingest_bundle_lifi.py` | Oui (échange leg) |
| Exchange | `ingest_exchange.py` | Oui |
| Morpho / Ledgity | — | **Non branché** (volontaire) |
| WAC | `wac.py` | Oui, par scope |
| Charts P&L crypto | `history_events.py` | Oui, exécutions uniquement |

---

*Doctrine validée produit / architecture — toute PR qui ajoute une source à `cost_basis_executions` doit référencer ce document et justifier l’échange économique.*
