# Morpho USDC Volt — Runbook beta contrôlée

Ouverture progressive du vault Morpho USDC à un petit groupe d'utilisateurs, avec plafonds, kill switch et surveillance support.

**Références**
- Staging : [MORPHO_STAGING_RUNBOOK.md](./MORPHO_STAGING_RUNBOOK.md)
- Production : [MORPHO_PRODUCTION_CHECKLIST.md](./MORPHO_PRODUCTION_CHECKLIST.md)
- Cron : [MORPHO_CRON_JOBS.md](./MORPHO_CRON_JOBS.md)
- Monitoring admin : `/admin/morpho-vaults/monitoring`

---

## Variables d'environnement (beta)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `MORPHO_USDC_BETA_ENABLED` | `false` | Active la beta privée (allowlist obligatoire) |
| `MORPHO_USDC_BETA_PERSON_IDS` | — | UUIDs autorisés (CSV) |
| `MORPHO_USDC_BETA_EMAILS` | — | Emails autorisés (CSV, insensible à la casse) |
| `MORPHO_USDC_BETA_PROFILE_TAG` | — | Tag dans `profile_json.tags` / `beta_tags` |
| `MORPHO_USDC_BETA_INCLUDE_ADMINS` | `false` | Inclure les personnes liées à un compte admin CMS |
| `MORPHO_USDC_BETA_MIN_DEPOSIT_USDC` | `10` | Dépôt minimum |
| `MORPHO_USDC_BETA_MAX_DEPOSIT_USDC` | `100` | Dépôt max par transaction |
| `MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC` | `500` | Exposition max par utilisateur |
| `MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC` | `5000` | Cap global beta |
| `MORPHO_USDC_DEPOSITS_DISABLED` | `false` | Kill switch dépôts |
| `MORPHO_USDC_WITHDRAWS_DISABLED` | `false` | Kill switch retraits |

**Logs support (stdout JSON, préfixe `[morpho:support]`)**
- `morpho.tx_failed` / `morpho.tx_reverted`
- `morpho.withdraw_failed` / `morpho.deposit_failed`
- `morpho.reconciliation_mismatch` (> 1 USDC)
- `morpho.tx_pending_stale` (> 15 min, émis lors de la réconciliation cron)
- `morpho.beta_limit_exceeded`

---

## 1. Procédure d'ouverture beta

1. **Valider staging** — runbook staging OK, monitoring **Healthy** ou Warning documenté.
2. **Publier le vault** — CMS `/admin/morpho-vaults`, mode `direct_morpho` ou `privy_earn`.
3. **Sync registry** :
   ```bash
   cd services/arquantix/web
   pnpm morpho:sync-vault-registry
   ```
4. **Configurer l'allowlist** (staging puis prod) :
   ```bash
   MORPHO_USDC_BETA_ENABLED=true
   MORPHO_USDC_BETA_PERSON_IDS=<uuid1>,<uuid2>
   # et/ou
   MORPHO_USDC_BETA_EMAILS=user1@example.com,user2@example.com
   # et/ou tag profil
   MORPHO_USDC_BETA_PROFILE_TAG=morpho_usdc_beta
   ```
5. **Vérifier kill switch** : `MORPHO_USDC_DEPOSITS_DISABLED=false`, `MORPHO_USDC_WITHDRAWS_DISABLED=false`.
6. **Redéployer** le web avec les nouvelles variables (sans toucher DB/Docker sans accord).
7. **Smoke test** avec un compte allowlisté :
   - Invest → vault visible
   - Dépôt 10 USDC (min beta)
   - Retrait partiel
   - Monitoring admin → section **Beta Morpho USDC** cohérente
8. **Activer cron** réconciliation quotidienne (voir `MORPHO_CRON_JOBS.md`).

---

## 2. Procédure d'ajout utilisateur

**Option A — Par person_id (recommandé)**
1. Récupérer `person_id` (admin / support / SQL `persons`).
2. Ajouter à `MORPHO_USDC_BETA_PERSON_IDS`.
3. Redéployer ou hot-reload env selon infra.

**Option B — Par email**
1. Vérifier que l'email est dans `pe_clients.email` ou `profile_json` du portail.
2. Ajouter à `MORPHO_USDC_BETA_EMAILS`.

**Option C — Par tag profil**
1. Définir `MORPHO_USDC_BETA_PROFILE_TAG=morpho_usdc_beta`.
2. Ajouter le tag dans `profile_json.tags` (ou `beta_tags`) de la personne.

**Option D — Admins internes**
- `MORPHO_USDC_BETA_INCLUDE_ADMINS=true` pour les personnes liées à `AdminUser`.

**Non allowlisté** : section Earn vide + message « beta privée ».

---

## 3. Surveillance quotidienne (5–10 min)

| Check | Où | Seuil |
|-------|-----|-------|
| Statut global | `/admin/morpho-vaults/monitoring` | **Healthy** idéal |
| Beta users / assets / yield | Section Beta Morpho USDC | Tendance stable |
| Tx pending > 15 min | Alertes + compteur | **0** |
| Mismatches > 1 USDC | Dernière réconciliation | **0** |
| Tx failed / reverted | Section Beta | Investiguer chaque nouvelle |
| Cap global beta | `totalAssetsInVaultUsdc` vs 5000 | < 80 % avant alerte interne |
| Logs `[morpho:support]` | stdout / agrégateur | Pas de critical non traité |

**Actions quotidiennes**
```bash
pnpm morpho:reconcile   # ou cron
# Puis actualiser le dashboard admin
```

---

## 4. Procédure incident

1. **Identifier** : code alerte, person_id, vault, tx_hash dans logs `[morpho:support]`.
2. **Classer** :
   - P1 : mismatch > 1 USDC, retrait bloqué inexpliqué, perte tracking ledger
   - P2 : tx failed/reverted isolée, pending > 15 min
   - P3 : warning monitoring (GraphQL lent, mismatch mineur)
3. **P1 — immédiat** :
   - Kill switch dépôts : `MORPHO_USDC_DEPOSITS_DISABLED=true`
   - Ne pas activer `MORPHO_USDC_WITHDRAWS_DISABLED` sauf risque smart contract
   - Lancer réconciliation manuelle (admin POST ou `pnpm morpho:reconcile`)
   - Documenter dans le canal support
4. **Investigation** :
   - SQL `onchain_vault_transactions`, `user_vault_positions`
   - Receipt on-chain (Base explorer)
   - Comparer ledger vs on-chain (items réconciliation)
5. **Résolution** : corriger à la couche code/API si bug ; sinon communication utilisateur + compensation manuelle si besoin.

---

## 5. Kill switch

**Suspendre les dépôts uniquement (retraits OK)**
```bash
MORPHO_USDC_DEPOSITS_DISABLED=true
MORPHO_USDC_WITHDRAWS_DISABLED=false
```
UI : message « Les dépôts sont suspendus. Vous pouvez retirer vos fonds. »

**Suspendre tout**
```bash
MORPHO_USDC_DEPOSITS_DISABLED=true
MORPHO_USDC_WITHDRAWS_DISABLED=true
```

**Fermer la beta (aucun accès)**
```bash
MORPHO_USDC_BETA_ENABLED=true
# + vider allowlist OU retirer tous les utilisateurs
```

Redéployer après changement env.

---

## 6. Rollback

1. Kill switch dépôts (`MORPHO_USDC_DEPOSITS_DISABLED=true`).
2. Si bug code : revert du déploiement web précédent (pas de rollback DB ledger).
3. `MORPHO_USDC_BETA_ENABLED=false` → comportement pré-beta (vault visible pour tous les utilisateurs connectés, si vault publié).
4. Vérifier monitoring post-rollback.
5. Post-mortem : cause, impact utilisateurs, fix forward.

**Interdit** : recréer une DB parallèle ou `docker compose down -v` pour contourner un incident fonctionnel.

---

## 7. Critères passage rollout large

Tous les critères suivants pendant **7 à 14 jours** :

| Critère | Cible |
|---------|-------|
| Utilisateurs beta actifs | 20–50 |
| Mismatch critique (> 1 USDC) | 0 |
| Perte tracking ledger | 0 |
| Retrait bloqué non expliqué | 0 |
| Cron réconciliation | Stable |
| Monitoring | **Healthy** |
| Support | Capable d'expliquer intérêts + risques DeFi |

**Passage rollout**
1. Désactiver la beta : `MORPHO_USDC_BETA_ENABLED=false`
2. Conserver plafonds ou les relever via env (décision produit)
3. Retirer kill switch si actif
4. Continuer monitoring 2 semaines supplémentaires avant annonce large

---

## 8. Checklist go / no-go beta (résumé)

- [ ] Staging validé (runbook staging)
- [ ] Allowlist configurée et testée
- [ ] Plafonds beta en env
- [ ] Kill switch testé (dépôts off, retraits on)
- [ ] Monitoring admin + logs support vérifiés
- [ ] Cron réconciliation planifié
- [ ] Support briefé (risques Morpho, délais pending, procédure incident)
