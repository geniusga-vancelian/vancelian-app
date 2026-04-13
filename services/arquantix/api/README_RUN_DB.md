# Runbook DB - Database Migrations & Diagnostics

Guide rapide pour diagnostiquer et appliquer les migrations Alembic depuis Cursor.

## 🆕 Créer une DB Propre pour Market Data + Backtest

Si votre DB principale contient déjà des tables applicatives et que vous voulez une DB dédiée pour market_data et backtest :

### Workflow Complet

```bash
# 1. Créer la nouvelle DB 'arquantix_quant'
python3 api/scripts/create_db_quant.py

# 2. Switcher l'environnement vers cette DB
python3 api/scripts/switch_env_to_quant.py

# 3. Appliquer les migrations
python3 api/scripts/migrate_quant_db.py

# 4. Redémarrer le backend pour utiliser la nouvelle DB
# (Le backend chargera automatiquement .env.local s'il existe)
```

**Note :** 
- Le script `switch_env_to_quant.py` crée/modifie `api/.env.local` (qui est dans `.gitignore`)
- Le backend (`main.py` et `database.py`) charge automatiquement `.env.local` en priorité s'il existe
- La DB originale reste intacte, aucune modification n'est apportée

### Vérification

Après avoir exécuté les scripts :

```bash
# Vérifier que les tables existent
python3 api/scripts/db_doctor.py

# Devrait afficher :
# Database name: arquantix_quant
# Toutes les tables en ✅ YES
```

---

## 📋 Prérequis

- Python 3.9+ installé
- `.env` configuré avec `DATABASE_URL` dans `api/`
- Accès à la base de données PostgreSQL
- PostgreSQL démarré et accessible

## 🔍 Workflow Complet (Recommandé)

### Étape 1 : Inspecter l'état Alembic

Vérifier la révision actuelle et les révisions disponibles :

```bash
python3 api/scripts/alembic_state_inspect.py
```

**Résultat attendu :**
- Affiche la révision actuelle en DB (si existe)
- Liste toutes les révisions disponibles dans le repository
- Exit code 0 : État cohérent
- Exit code 2 : Révision en DB non trouvée dans le repo (nécessite réparation)

### Étape 2 : Réparer et Appliquer Migrations (si DB vide)

**⚠️ ATTENTION : Ce script ne fonctionne QUE si la DB est vide (pas de tables applicatives)**

```bash
python3 api/scripts/alembic_repair_and_upgrade.py
```

Ce script :
1. Vérifie si la DB contient des tables applicatives
2. Si DB vide : supprime la révision invalide dans `alembic_version` (si présente)
3. Applique toutes les migrations (`alembic upgrade head`)
4. Vérifie que toutes les tables sont créées

**Si la DB n'est pas vide :**
- Le script refuse d'exécuter (sécurité)
- Vous devez réparer manuellement (voir section Dépannage)

### Étape 3 : Vérifier les Tables

Vérifier que toutes les tables requises existent :

```bash
python3 api/scripts/db_doctor.py
```

**Résultat attendu :**
- ✅ Exit code 0 : Toutes les tables existent
- ❌ Exit code 2 : Tables manquantes

## 🔍 Diagnostic des Tables (Standalone)

Vérifier si toutes les tables requises existent :

```bash
python3 api/scripts/db_doctor.py
```

**Résultat attendu :**
- ✅ Exit code 0 : Toutes les tables existent
- ❌ Exit code 2 : Tables manquantes (migrations à appliquer)

**Tables vérifiées :**
- `market_data_instruments`
- `market_data_bars_d1`
- `backtest_runs`
- `backtest_portfolio_series`
- `backtest_instrument_series`
- `backtest_metrics`

## 🔄 Appliquer les Migrations (Sans Réparation)

Si l'état Alembic est cohérent, appliquer directement :

```bash
python3 api/scripts/alembic_upgrade_head.py
```

Ce script :
1. Exécute `alembic upgrade head`
2. Vérifie automatiquement les tables après migration
3. Affiche un rapport de succès/échec

**⚠️ Note :** Si vous obtenez l'erreur "Can't locate revision", utilisez plutôt `alembic_repair_and_upgrade.py` (si DB vide) ou réparez manuellement.

## 📝 Workflow Complet

### Premier Setup (DB Vide)

```bash
# 1. Inspecter l'état
python3 api/scripts/alembic_state_inspect.py

# 2. Réparer et appliquer (si DB vide)
python3 api/scripts/alembic_repair_and_upgrade.py

# 3. Vérification finale
python3 api/scripts/db_doctor.py
```

### Vérification Rapide (après changements)

```bash
python3 api/scripts/db_doctor.py
```

## 🐛 Dépannage

### Erreur : "DATABASE_URL not found"

**Solution :**
1. Vérifier que `.env` existe dans `api/`
2. Vérifier que `DATABASE_URL` est défini dans `.env`
3. Format attendu : `postgresql://user:password@host:port/dbname`

### Erreur : "relation does not exist"

**Solution :**
```bash
cd api
python3 scripts/alembic_upgrade_head.py
```

### Erreur : "Alembic directory not found"

**Solution :**
- Vérifier que `api/alembic/` existe
- Si absent, initialiser Alembic : `alembic init alembic`

### Erreur de connexion DB

**Solution :**
1. Vérifier que PostgreSQL est démarré
2. Vérifier les credentials dans `DATABASE_URL` (fichier `.env` dans `api/`)
3. Vérifier le port (par défaut 5433, peut être 5432)
4. Tester la connexion avec `db_doctor.py` qui affichera l'erreur détaillée

### Erreur : "Can't locate revision identified by 'XXXXX'"

**Cause :** La table `alembic_version` contient une révision qui n'existe plus dans le repository.

**Solution :**

1. **Si DB vide (pas de tables applicatives) :**
   ```bash
   python3 api/scripts/alembic_repair_and_upgrade.py
   ```

2. **Si DB non vide (tables applicatives présentes) :**
   
   **Option A : Script de réparation manuelle (recommandé)**
   ```bash
   # 1. Inspecter l'état
   python3 api/scripts/alembic_state_inspect.py
   
   # 2. Réparer manuellement (supprime révision invalide + applique migrations)
   python3 api/scripts/alembic_repair_manual.py
   # ⚠️  Demande confirmation avant d'exécuter
   
   # 3. Vérifier
   python3 api/scripts/db_doctor.py
   ```
   
   **Option B : Réparation SQL directe**
   ```bash
   # 1. Inspecter l'état
   python3 api/scripts/alembic_state_inspect.py
   
   # 2. Se connecter à la DB et supprimer la révision invalide
   # Via psql ou un client SQL :
   # DELETE FROM alembic_version;
   
   # 3. Appliquer migrations
   python3 api/scripts/alembic_upgrade_head.py
   ```
   
   **Option C : Forcer la révision actuelle**
   ```bash
   cd api
   # Marquer comme étant à la révision head (sans appliquer)
   python3 -m alembic stamp head
   
   # Puis vérifier
   python3 scripts/db_doctor.py
   ```

## 📚 Commandes Alembic Utiles

### Voir l'état des migrations

```bash
cd api
python3 -m alembic current
```

### Voir l'historique

```bash
cd api
python3 -m alembic history
```

### Créer une nouvelle migration

```bash
cd api
python3 -m alembic revision --autogenerate -m "description"
```

### Rollback (attention !)

```bash
cd api
python3 -m alembic downgrade -1  # Un niveau en arrière
python3 -m alembic downgrade base  # Tout en arrière
```

## 🔧 Scripts Disponibles

| Script | Description |
|--------|-------------|
| `db_doctor.py` | Diagnostic des tables (vérifie existence, affiche nom DB) |
| `create_db_quant.py` | Crée une nouvelle DB 'arquantix_quant' (sans toucher à l'existante) |
| `switch_env_to_quant.py` | Switche DATABASE_URL vers arquantix_quant (crée .env.local) |
| `migrate_quant_db.py` | Applique migrations sur arquantix_quant + vérifie tables |
| `alembic_state_inspect.py` | Inspecte l'état Alembic (révision actuelle vs disponible) |
| `alembic_repair_and_upgrade.py` | Répare et applique migrations (DB vide uniquement) |
| `alembic_repair_manual.py` | Répare manuellement (DB non vide, demande confirmation) |
| `alembic_upgrade_head.py` | Applique migrations (si état cohérent) |

**Tous les scripts :**
- Se positionnent automatiquement dans le bon répertoire
- Utilisent le même `.env` / `.env.local` que l'application
- Masquent le mot de passe dans les logs
- Affichent le nom de la base de données utilisée

## ✅ Checklist Post-Migration

Après avoir appliqué les migrations :

- [ ] `db_doctor.py` retourne exit code 0
- [ ] Backend démarre sans erreur
- [ ] Endpoints Market Data fonctionnent
- [ ] Endpoints Backtest fonctionnent
- [ ] Diagnostic UI fonctionne (`/admin/diagnostics`)

## 🔗 Références

- **Alembic Docs** : https://alembic.sqlalchemy.org/
- **SQLAlchemy Docs** : https://docs.sqlalchemy.org/
- **Migrations existantes** : `api/alembic/versions/`

---

**Dernière mise à jour** : 2026-01-09

