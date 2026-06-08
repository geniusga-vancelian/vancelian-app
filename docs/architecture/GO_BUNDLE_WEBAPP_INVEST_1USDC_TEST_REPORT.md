# Rapport GO — WebApp Bundle Invest 1 USDC (prod)

| Champ | Valeur |
| --- | --- |
| **Date** | **EN COURS** |
| **Compte pilote** | `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **Portfolio** | Crypto Majors `ab4ae920-f3e8-481b-8f82-a41a81d5779d` |
| **Montant** | **1 USDC** · Base |
| **Plan** | [GO_BUNDLE_WEBAPP_INVEST_1USDC_TEST_PLAN.md](GO_BUNDLE_WEBAPP_INVEST_1USDC_TEST_PLAN.md) |
| **Décision** | **⏸ En attente invest WebApp + audit post-trade** |

---

## 1. Baseline (pré-test)

| Check | Valeur |
| --- | --- |
| `test_start_iso` | `2026-06-08T16:15:06.973194+00:00` |
| `all_checks_pass` | **true** |
| PE / CB / legs | **19 / 67 / 131** |
| Flags Bundle OFF | ✅ |
| USDC disponible | **162.14** |
| locks / dead_letter / COMPLETED | **0 / 0 / 0** |

ECS task : `523c72eff9bd444e913a2932e9ee84c7`

---

## 2. Invest WebApp (manuel)

*(À compléter après exécution)*

| Champ | Valeur |
| --- | --- |
| Heure invest | |
| `batch_id` | |
| `parent_intent_id` | |
| `swap_id` | |
| `tx_hash` Base | |
| Chemin exécution | legacy / event-driven |

---

## 3. Audit post-trade

*(À compléter)*

---

## 4. Critères GO

| Critère | Statut |
| --- | --- |
| `tx_hash` réel (pas mock) | |
| Signature Privy réelle | |
| Swap CONFIRMED | |
| PE/CB/legs cohérents | |
| `dead_letter=0` | |
| Lock orphelin = 0 | |
| Pas de double settlement | |

---

## 5. Rollback

Si lock orphelin : documenter `parent_intent_id` · ne pas activer flags en TD.
