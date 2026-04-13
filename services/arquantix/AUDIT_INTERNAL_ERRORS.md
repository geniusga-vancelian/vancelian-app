# Audit: Internal Server Errors après Prompt 1 (Section Library)

**Date:** 2026-01-05  
**Contexte:** Erreurs 500 Internal Server Error depuis l'implémentation de la Section Library (Prompt 1)

---

## PHASE A - Collecte de Preuves

### 1. État des Migrations Prisma

```
✅ 6 migrations trouvées
✅ Database schema is up to date!
```

**Migrations appliquées:**
- `20260104135006_init_admin_cms`
- `20260104135016_init_admin_cms`
- `20260104142459_phase2_cms_content_engine`
- `20260104150416_add_media_model`
- `20260104192811_add_page_fields`
- `20260104192831_add_page_fields`

**Dernière migration:** `20260104192831_add_page_fields` ajoute:
- `url_path`, `title`, `template`, `description`, `updated_at` à la table `pages`

### 2. État de la Base de Données

**Compteurs:**
```json
{
  "pages": 1,
  "sections": 5,
  "sectionContents": 10,
  "media": 1,
  "users": 1,
  "sessions": 0
}
```

**Page "home":**
- ✅ Existe (slug: "home")
- ✅ 5 sections associées

**Colonnes vérifiées:**
- `pages`: url_path, title, template, description présents ✅
- `sections`: colonnes attendues présentes ✅
- `section_contents`: colonnes attendues présentes ✅

### 3. Code Section Library (Prompt 1)

**Fichiers identifiés:**
- `src/lib/sections/library.ts` - Définition des types de sections
- `src/lib/sections/registry.tsx` - Registre de rendu des sections

**Points d'attention:**
- ✅ `library.ts` existe et exporte des fonctions
- ✅ `registry.tsx` existe (extension .tsx pour JSX)
- ⚠️ Pas d'endpoint `/api/admin/section-types` trouvé dans le code

### 4. Endpoints Testés

**Tests effectués:**
- `/api/admin/pages` - À tester avec authentification
- `/admin/pages` - Page admin
- Build Next.js - À vérifier

### 5. Observations Clés

**Problèmes potentiels identifiés:**
1. **Section Library API manquante:** Aucun endpoint `/api/admin/section-types` trouvé, mais le code frontend peut le référencer
2. **Registry TSX:** Le fichier `registry.tsx` peut avoir des problèmes de compilation si mal formaté
3. **Dépendances:** Les imports entre `library.ts` et `registry.tsx` doivent être vérifiés

---

## PHASE B - Diagnostic

### Causes Racines Probables

#### 🔴 Cause #1: Erreur de Compilation TypeScript (PROBABILITÉ ÉLEVÉE)

**Symptôme:** Erreur de build TypeScript dans `src/app/api/admin/pages/route.ts` ligne 137: `Property 'message' does not exist on type 'object & Record<"code", unknown>'`

**Preuve:**
- Build échoue avec erreur TypeScript
- Code essaie d'accéder à `error.message` sans cast approprié
- L'endpoint `/api/admin/section-types` EXISTE déjà ✅

**Impact:**
- Build échoue, application ne démarre pas correctement
- Erreurs 500 en runtime si le code est exécuté malgré l'erreur

**Risque:** ÉLEVÉ - Bloque le build et le fonctionnement de l'app

---

#### 🟡 Cause #2: Endpoints API Potentiellement Manquants (PROBABILITÉ FAIBLE)

**Symptôme:** Vérification des endpoints référencés par le frontend.

**Preuve:**
- ✅ `/api/admin/section-types` EXISTE (`src/app/api/admin/section-types/route.ts`)
- ✅ Tous les endpoints nécessaires semblent présents

**Impact:**
- Aucun impact si tous les endpoints existent

**Risque:** FAIBLE - Endpoints présents

---

#### 🟢 Cause #3: Données Manquantes ou Incohérentes (PROBABILITÉ FAIBLE)

**Symptôme:** Les données existent mais peuvent être incomplètes.

**Preuve:**
- Page "home" existe ✅
- Sections existent ✅
- Contenus existent ✅

**Impact:**
- Erreurs de rendu si les données ne correspondent pas aux schémas attendus
- Erreurs de validation Zod

**Risque:** FAIBLE - Données semblent cohérentes

---

### Différences Schema vs DB

**Comparaison:**
- ✅ Toutes les migrations sont appliquées
- ✅ Colonnes attendues présentes dans la DB
- ✅ Pas de drift détecté par `prisma migrate status`

**Conclusion:** Le schéma Prisma et la DB sont synchronisés.

---

### État des Données

**Vérifications:**
- ✅ Page "home" existe (1 page)
- ✅ 5 sections associées à "home"
- ✅ 10 contenus de section (DRAFT + PUBLISHED pour chaque section)
- ✅ 1 utilisateur admin
- ✅ 1 média synchronisé depuis R2

**Conclusion:** Les données sont présentes et cohérentes. Aucun reset récent de la DB détecté.

---

## PHASE C - Plan de Remédiation

### Priorité 1: Corriger l'Erreur TypeScript (CRITIQUE)

**Action:**
Corriger l'erreur TypeScript dans `src/app/api/admin/pages/route.ts` ligne 137 en castant `error` correctement.

**Risque:** TRÈS FAIBLE - Correction de type uniquement

**Impact:** Permet au build de passer et résout les erreurs 500

---

### Priorité 2: Vérifier et Corriger le Code Section Library

**Actions:**
1. Vérifier les imports dans `library.ts` et `registry.tsx`
2. S'assurer que les exports sont corrects
3. Vérifier la compilation TypeScript
4. Ajouter des garde-fous (fallbacks) pour les sections inconnues

**Risque:** FAIBLE - Corrections de code uniquement

**Impact:** Améliore la robustesse et évite les erreurs runtime

---

### Priorité 3: Script de Repair Seed (Optionnel)

**Action:**
Créer un script `scripts/repair-seed.ts` idempotent qui:
- Vérifie si "home" existe, sinon le crée
- Vérifie si les sections existent, sinon les crée
- Ne modifie pas les données existantes

**Risque:** TRÈS FAIBLE - Script idempotent

**Impact:** Permet de réparer facilement en cas de perte de données

---

### Ordre d'Exécution Recommandé

1. ✅ Vérifier l'état actuel (Phase A complétée)
2. ✅ Corriger l'erreur TypeScript dans `pages/route.ts`
3. 🔲 Vérifier le build (`npm run build`)
4. 🔲 Tester les endpoints critiques
5. 🔲 Vérifier et améliorer `library.ts` et `registry.tsx` (garde-fous)
6. 🔲 Créer le script de repair seed (optionnel)
7. 🔲 Validation finale (Phase D)

---

## PHASE D - Validation (À Effectuer Après Corrections)

### Tests à Effectuer

- [ ] `/admin/login` - Connexion admin
- [ ] `/admin/pages` - Liste des pages
- [ ] `/admin/pages/home` - Détails de la page home
- [ ] `/admin/pages/home` - Bouton "Add Section" fonctionne
- [ ] `/api/admin/section-types` - Retourne la liste des types
- [ ] `/admin/media` - Liste des médias
- [ ] `/preview/home?locale=fr` - Prévisualisation
- [ ] Création d'une nouvelle section depuis la bibliothèque

---

## Recommandations

### Immédiat (Avant de continuer)

1. **Créer l'endpoint API manquant** - Bloque probablement l'usage de "Add Section"
2. **Vérifier les logs serveur** - Pour identifier les erreurs exactes

### Court Terme

1. **Ajouter des logs détaillés** - Pour faciliter le debugging
2. **Ajouter des fallbacks** - Pour éviter les 500 sur erreurs de validation
3. **Tests automatisés** - Pour éviter les régressions

### Long Terme

1. **Script de repair seed** - Pour faciliter la récupération
2. **Documentation** - Pour expliquer l'architecture Section Library
3. **Monitoring** - Pour détecter les erreurs en production

---

## Fichiers à Modifier/Créer

### À Créer
- `src/app/api/admin/section-types/route.ts` (PRIORITÉ 1)
- `scripts/repair-seed.ts` (Optionnel)

### À Vérifier/Corriger
- `src/lib/sections/library.ts` (Vérifier exports)
- `src/lib/sections/registry.tsx` (Vérifier imports/exports)

### Commandes à Exécuter

```bash
# 1. Vérifier la compilation
npm run build

# 2. Lancer les tests manuels (après corrections)
npm run dev
# Puis tester les endpoints listés dans Phase D

# 3. Optionnel: Réparer les données si nécessaire
npm run repair:seed  # (si script créé)
```

---

## Conclusion

**Cause racine identifiée:** Erreur de compilation TypeScript dans `src/app/api/admin/pages/route.ts` (ligne 137) - accès à `error.message` sans cast approprié.

**État des endpoints:**
- ✅ `/api/admin/section-types` EXISTE
- ✅ Tous les endpoints nécessaires sont présents

**Risque de perte de données:** AUCUN - Les données existent et sont cohérentes. Aucune migration destructive nécessaire.

**Plan recommandé:** Corriger l'erreur TypeScript, vérifier le build, tester les endpoints, ajouter des garde-fous, puis valider.

