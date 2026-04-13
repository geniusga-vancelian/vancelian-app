# Flutter Profile — Test Registration Entry Point

## Executive Summary

Un point d'entrée de test pour le Registration Flow Engine a été ajouté depuis la page Profile dans Flutter. Le système repose sur une table backend `registration_runtime_settings` qui stocke la juridiction courante, permettant à Flutter de résoudre dynamiquement le flow actif sans hardcode.

### Résultats clés
- **2 endpoints backend** créés (GET runtime + PATCH admin)
- **1 migration Alembic** avec seed EU
- **1 modèle SQLAlchemy** ajouté
- **1 écran Flutter** créé (`RegistrationTestLauncherScreen`)
- **1 méthode API** ajoutée au client Flutter
- **8 tests backend** + **5 tests Flutter** — tous verts
- **Non-régression** : 44 tests Flutter registration + 35 tests backend registration passent

---

## Profile Entry Added

### Fichier modifié : `mobile/lib/features/profile/presentation/screens/profile_screen.dart`

Une nouvelle section **"Développement"** a été ajoutée entre "Support" et "Informations" :

```
┌─────────────────────────────────────────┐
│ 🔬  Test Registration                   │
│     Tester le flow d'inscription        │
│     dynamique                      ›    │
└─────────────────────────────────────────┘
```

- Icône : `Icons.science_outlined` en indigo
- Style identique aux autres `SettingsListItem`
- Navigation vers `RegistrationTestLauncherScreen` au tap

---

## Registration Test Launcher

### Fichier créé : `mobile/lib/features/registration/screens/registration_test_launcher_screen.dart`

Écran dédié au lancement d'un flow de test :

### Structure
1. **Header** : "Registration Lab" avec icône science et description
2. **Panneau info** :
   - Juridiction courante (nom + code)
   - Flow actif (nom + version)
3. **Boutons** :
   - "Lancer le flow" — ouvre `RegistrationFlowScreen` avec la juridiction
   - "Rafraîchir" — recharge la configuration

### États gérés

| État | Comportement |
|------|-------------|
| OK (juridiction + flow) | Info affichées, bouton "Lancer" actif |
| Aucune juridiction | Warning panel, bouton désactivé |
| Juridiction sans flow | Warning panel, bouton désactivé |
| Erreur réseau | Banner rouge, bouton désactivé |
| Loading | Spinner central |

### Flow de lancement
```
Profile → tap "Test Registration"
→ RegistrationTestLauncherScreen
→ GET /api/registration/runtime/current-jurisdiction
→ Affiche EU / EU Individual Onboarding v1
→ tap "Lancer le flow"
→ RegistrationFlowScreen(jurisdiction: "EU")
→ POST /sessions/start → flow runtime complet
```

---

## Current Jurisdiction Runtime Setting

### Modèle SQLAlchemy

```python
class RegistrationRuntimeSetting(Base):
    __tablename__ = "registration_runtime_settings"
    id = Column(UUID, primary_key=True)
    current_jurisdiction_code = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
```

### Migration : `089_registration_runtime_settings.py`

- Crée la table `registration_runtime_settings`
- Insère une ligne initiale avec `current_jurisdiction_code = "EU"`

---

## Backend Endpoints

### GET /api/registration/runtime/current-jurisdiction

Retourne la juridiction courante avec son flow actif résolu :

```json
{
  "jurisdiction_code": "EU",
  "jurisdiction_name": "European Union",
  "active_flow_id": "0d823bed-...",
  "active_flow_name": "EU Individual Onboarding v1",
  "active_flow_version": 1
}
```

**Logique de résolution** :
1. Lit `current_jurisdiction_code` depuis `registration_runtime_settings`
2. Résout la `RegistrationJurisdiction` correspondante
3. Cherche le `RegistrationFlow` actif avec `entrypoint_type = "individual"`, version la plus récente

### PATCH /api/admin/registration/runtime/current-jurisdiction

Permet à l'admin de changer la juridiction courante :

```json
// Request
{ "jurisdiction_code": "UAE" }

// Response
{ "current_jurisdiction_code": "UAE", "jurisdiction_name": "United Arab Emirates" }
```

**Validations** :
- La juridiction doit exister dans `registration_jurisdictions`
- Elle doit être active (`is_active = true`)
- Sinon → 404

### GET /api/admin/registration/runtime/current-jurisdiction

Endpoint admin de lecture simple :
```json
{ "current_jurisdiction_code": "EU" }
```

---

## Data Seed

La migration `089` initialise automatiquement :
- `current_jurisdiction_code = "EU"`

Au démarrage, le système pointe vers :
- **EU** → **EU Individual Onboarding v1** (v1, actif)

---

## Tests Added

### Backend : `tests/test_registration_runtime_settings.py`

| Test | Description |
|------|-------------|
| `test_returns_eu_by_default` | GET retourne EU après seed |
| `test_resolves_active_flow` | Flow Individual résolu correctement |
| `test_returns_404_when_no_setting` | 404 si table vide |
| `test_patch_valid_jurisdiction` | PATCH EU → 200 |
| `test_patch_unknown_jurisdiction_rejected` | PATCH MARS → 404 |
| `test_patch_empty_code_rejected` | PATCH "" → 422 |
| `test_patch_persists` | PATCH UAE → GET retourne UAE |
| `test_admin_get` | Admin GET retourne la valeur |

**Résultat** : 8/8 verts

### Flutter : `test/registration/registration_launcher_test.dart`

| Test | Description |
|------|-------------|
| `shows loading then content` | CircularProgressIndicator au démarrage |
| `shows Registration Lab header` | Titre "Test Registration" présent |
| `shows Lancer le flow button` | Boutons CTA rendus |
| `shows science icon` | Icône science visible |
| `can be constructed with jurisdiction` | RegistrationFlowScreen se construit |

**Résultat** : 5/5 verts

### Non-régression totale : 44 tests Flutter + 35 tests backend — tous verts

---

## Files Created/Modified

### Created
| Fichier | Rôle |
|---------|------|
| `api/alembic/versions/089_registration_runtime_settings.py` | Migration + seed |
| `api/tests/test_registration_runtime_settings.py` | Tests backend |
| `mobile/lib/features/registration/screens/registration_test_launcher_screen.dart` | Écran launcher |
| `mobile/test/registration/registration_launcher_test.dart` | Tests Flutter |

### Modified
| Fichier | Changement |
|---------|-----------|
| `api/database.py` | Ajout `RegistrationRuntimeSetting` |
| `api/services/registration/runtime_router.py` | Ajout `GET /runtime/current-jurisdiction` |
| `api/services/registration/admin_router.py` | Ajout `PATCH` + `GET` admin current jurisdiction |
| `mobile/lib/features/registration/data/registration_api.dart` | Ajout `getCurrentJurisdiction()` |
| `mobile/lib/features/profile/presentation/screens/profile_screen.dart` | Section "Développement" avec Test Registration |

---

## Remaining Next Steps

| Item | Priorité | Description |
|------|----------|-------------|
| Admin UI selector | P2 | Ajouter un dropdown dans l'admin web pour changer la juridiction |
| Multi-entrypoint | P3 | Support "corporate" en plus de "individual" |
| Auth on admin endpoint | P1 | Protéger le PATCH admin avec auth |
| Flow history | P3 | Historique des sessions de test depuis le launcher |
| Production guard | P1 | Conditionner l'affichage de la section "Développement" à un flag `kDebugMode` ou feature flag |
