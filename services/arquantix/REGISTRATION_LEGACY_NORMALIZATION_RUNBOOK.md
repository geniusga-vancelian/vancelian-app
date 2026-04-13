# Registration legacy normalization — exécution en 4 étapes

Toute la logique métier reste dans `services/registration/legacy_normalization.py`. Ce runbook décrit l’orchestration **sécurisée** (analyse, garde-fous, traces).

## Procédure recommandée (safe by process)

1. **Dry-run** avec export JSON.  
2. **`analyze`** puis **`validate`**.  
3. **Lire en priorité** : % ambiguous, `MULTIPLE_FIELD_MATCH`, orphelins `field_definition_id`, impact publishable (before / after / heuristique).  
4. **Apply** uniquement si c’est propre **et** que `validate` sort en **0**.  
5. **Re-dry-run** post-apply + **`delta`** pour le summary.

**Exemple de commandes (chemins libres) :**

```bash
cd services/arquantix/api

python3 scripts/run_registration_legacy_normalization.py --json-out /tmp/reg_dry.json
python3 scripts/run_registration_legacy_normalization.py analyze /tmp/reg_dry.json
python3 scripts/run_registration_legacy_normalization.py validate /tmp/reg_dry.json
```

Si `validate` est OK :

```bash
python3 scripts/run_registration_legacy_normalization.py apply \
  --pre-validate-json /tmp/reg_dry.json \
  --json-out /tmp/reg_apply.json \
  --post-verify-json-out /tmp/reg_after.json

python3 scripts/run_registration_legacy_normalization.py delta \
  --before /tmp/reg_dry.json \
  --after /tmp/reg_after.json \
  --apply-json /tmp/reg_apply.json \
  --write-summary /tmp/REGISTRATION_LEGACY_NORMALIZATION_EXECUTION_SUMMARY.md
```

Optionnel sur `apply` : `--snapshot-out`, `--log-file`, et confirmation interactive `YES` (ou `--yes` en CI après relecture du dry-run).

## Prérequis

```bash
cd services/arquantix/api
# Base accessible (même `DATABASE_URL` que l’API)
```

---

## Étape 1 — Dry-run complet + export JSON

```bash
python3 scripts/run_registration_legacy_normalization.py \
  --json-out /tmp/registration_legacy_dry_run.json
```

Contenu utile du JSON : `totals`, `ok`, `auto_fixable`, `ambiguous`, `health_before`, `health_after` (identique à `health_before` en dry-run).

**Équivalent API :**

`POST /api/admin/registration/legacy-normalization/dry-run`

---

## Étape 2 — Analyse structurée

```bash
python3 scripts/run_registration_legacy_normalization.py analyze /tmp/registration_legacy_dry_run.json
```

Sortie : volumes, ratios, top `reason_codes`, bindings ambigus, signaux dangereux, flows publishables.

**Validation automatique (exit code 2 si bloquant) :**

```bash
python3 scripts/run_registration_legacy_normalization.py validate /tmp/registration_legacy_dry_run.json
```

Seuils par défaut : `--max-ambiguous-pct 10`, `--max-multiple-match-abs 50`, etc. (`--help` sur le sous-commande validate).

---

## Étape 3 — Apply sécurisé (uniquement si l’étape 2 est OK)

**Obligatoire :** rapport dry-run JSON (`--pre-validate-json`). Pas d’apply sans ce fichier.

```bash
python3 scripts/run_registration_legacy_normalization.py apply \
  --pre-validate-json /tmp/registration_legacy_dry_run.json \
  --snapshot-out /tmp/registration_legacy_snapshot.json \
  --log-file /tmp/registration_legacy_apply.log \
  --json-out /tmp/registration_legacy_apply.json
```

Le script affiche l’analyse + la validation, puis demande : `Type YES to continue:`.

Automatisation (CI) : ajouter `--yes` (à utiliser seulement si le dry-run a été revu).

Optionnel : `--post-verify-json-out /tmp/registration_legacy_after.json` pour relancer un dry-run dans la même session et afficher le **delta** console.

**Équivalent API :** `POST /api/admin/registration/legacy-normalization/apply` avec `{"confirm": true}` (pas de snapshot fichier côté API — faire un GET report avant).

**Apply « urgence » sans pré-validation (déconseillé) :**

```bash
python3 scripts/run_registration_legacy_normalization.py --apply --i-understand-unsafe-apply --yes
```

---

## Étape 4 — Vérification post-apply + delta

```bash
python3 scripts/run_registration_legacy_normalization.py \
  --json-out /tmp/registration_legacy_after.json

python3 scripts/run_registration_legacy_normalization.py delta \
  --before /tmp/registration_legacy_dry_run.json \
  --after /tmp/registration_legacy_after.json \
  --apply-json /tmp/registration_legacy_apply.json \
  --write-summary REGISTRATION_LEGACY_NORMALIZATION_EXECUTION_SUMMARY.md
```

Le fichier `REGISTRATION_LEGACY_NORMALIZATION_EXECUTION_SUMMARY.md` est **généré** (ne pas commiter de secrets ; adapter le chemin si besoin).

---

## Traçabilité

| Artefact | Rôle |
|----------|------|
| `registration_legacy_dry_run.json` | État avant |
| `registration_legacy_snapshot.json` | Liste `auto_fixable` figée avant apply |
| `registration_legacy_apply.log` | Logs des corrections (handler fichier) |
| `registration_legacy_apply.json` | Réponse apply (`applied[]`) |
| `registration_legacy_after.json` | État après (nouveau dry-run) |
| `REGISTRATION_LEGACY_NORMALIZATION_EXECUTION_SUMMARY.md` | Synthèse markdown |

---

## Module Python (tests / notebooks)

```python
from services.registration.legacy_normalization_analysis import (
    load_report,
    analyze_legacy_normalization_report,
    format_console_analysis,
    validate_safe_to_apply,
    compute_post_apply_delta,
    format_post_apply_delta,
)
```
