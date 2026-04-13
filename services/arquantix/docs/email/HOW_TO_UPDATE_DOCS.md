# Comment Mettre à Jour la Documentation Email Builder

Ce document explique comment maintenir la documentation du système Email Builder à jour lorsque des changements sont apportés au code.

## 📋 Vue d'ensemble

La documentation Email Builder est organisée en 5 fichiers principaux :

1. **`README.md`** - Index et navigation
2. **`OVERVIEW.md`** - Vue d'ensemble, principes, workflow
3. **`ARCHITECTURE_BACKEND.md`** - Architecture backend (FastAPI)
4. **`ARCHITECTURE_FRONTEND.md`** - Architecture frontend (Next.js)
5. **`RUNBOOK.md`** - Setup, troubleshooting, extension guide

## 🔍 Quand Mettre à Jour la Documentation

Mettez à jour la documentation dans ces cas :

- ✅ Ajout d'un nouvel endpoint API (backend ou frontend)
- ✅ Modification d'un schéma de données (EmailSpec, Block types, etc.)
- ✅ Ajout d'un nouveau type de bloc
- ✅ Ajout d'un nouveau template
- ✅ Modification des règles de validation (registry, lock)
- ✅ Changement de variables d'environnement
- ✅ Modification du workflow (Save Draft, Validate, Translate)
- ✅ Ajout d'un nouveau composant frontend
- ✅ Correction d'un bug documenté dans RUNBOOK.md
- ✅ Ajout d'une nouvelle fonctionnalité

## 📝 Processus de Mise à Jour

### Étape 1 : Identifier les Changements

Avant de mettre à jour la doc, identifiez précisément :

1. **Quels fichiers de code ont changé ?**
   - Backend : `api/services/ai_email/**/*.py`
   - Frontend : `web/src/app/**/*.tsx`, `web/src/components/ai-email/**/*.tsx`
   - Schéma DB : `web/prisma/schema.prisma`

2. **Quel type de changement ?**
   - Nouveau endpoint
   - Modification schéma
   - Nouveau composant
   - Correction bug
   - Amélioration workflow

3. **Quel document est affecté ?**
   - Backend → `ARCHITECTURE_BACKEND.md`
   - Frontend → `ARCHITECTURE_FRONTEND.md`
   - Workflow → `OVERVIEW.md`
   - Bug fix → `RUNBOOK.md`
   - Nouveau template/bloc → `RUNVIEW.md` + `ARCHITECTURE_BACKEND.md`

### Étape 2 : Mettre à Jour les Documents Concernés

Suivez cette checklist pour chaque document modifié :

#### ✅ Checklist Générale

- [ ] Les chemins de fichiers référencés sont exacts (vérifier avec `glob_file_search` ou `read_file`)
- [ ] Les numéros de lignes sont à jour (si référencés)
- [ ] Les exemples de code JSON/TypeScript/Python correspondent au code réel
- [ ] Les schémas ASCII reflètent la nouvelle architecture (si changée)
- [ ] Les variables d'environnement listées sont complètes
- [ ] Les workflows utilisateur sont à jour
- [ ] Les sections "Next Steps" pointent vers les bons documents

#### ✅ Checklist OVERVIEW.md

- [ ] Les fonctionnalités principales sont à jour
- [ ] Les contraintes critiques reflètent les règles actuelles
- [ ] Le schéma d'architecture ASCII est correct
- [ ] Le workflow utilisateur (Builder → Draft → Validated → Translated) est exact
- [ ] Le modèle de données Prisma correspond au schéma réel
- [ ] Les invariants du système sont corrects
- [ ] La structure de fichiers référencée est à jour

#### ✅ Checklist ARCHITECTURE_BACKEND.md

- [ ] La structure de module FastAPI est exacte
- [ ] Tous les endpoints sont listés avec request/response corrects
- [ ] Les schémas Pydantic (EmailSpec, Block types) correspondent au code
- [ ] Le registry rigide (types, variants, slots) est à jour
- [ ] Les règles de structure locking sont exactes
- [ ] Le pipeline MJML (build → compile) est correct
- [ ] Les templates disponibles sont tous listés
- [ ] Les variables d'environnement backend sont complètes
- [ ] Les sections sécurité/sanitization sont à jour

#### ✅ Checklist ARCHITECTURE_FRONTEND.md

- [ ] Les routes Next.js admin sont toutes listées
- [ ] Les composants React sont tous documentés avec leurs props
- [ ] Les API routes Next.js (endpoints, request/response) sont exacts
- [ ] Le modèle d'état (state) de chaque page/composant est correct
- [ ] La stratégie de fallback backend/frontend est documentée
- [ ] Les workflows Save Draft / Validate sont exacts
- [ ] La sécurité iframe (sandbox) est documentée
- [ ] Les variables d'environnement frontend sont complètes

#### ✅ Checklist RUNBOOK.md

- [ ] Les étapes de setup local sont à jour (prérequis, installation)
- [ ] Les variables d'environnement listées sont complètes
- [ ] Les problèmes communs incluent les nouveaux bugs connus
- [ ] Les solutions de dépannage sont testées et fonctionnelles
- [ ] Les guides d'extension (add template, add block) sont à jour
- [ ] La checklist de test avant déploiement inclut les nouvelles fonctionnalités

#### ✅ Checklist README.md

- [ ] Les liens vers les 4 documents principaux fonctionnent
- [ ] La navigation rapide ("Je veux comprendre...") est à jour
- [ ] La date de "Dernière mise à jour" est modifiée

### Étape 3 : Vérifier la Cohérence

Après les mises à jour :

1. **Vérifier les liens croisés** :
   - Les références entre documents (ex: "→ ARCHITECTURE_BACKEND.md") fonctionnent
   - Les numéros de sections sont cohérents

2. **Vérifier les exemples** :
   - Les exemples JSON correspondent aux schémas réels
   - Les exemples de code sont syntaxiquement corrects

3. **Vérifier la précision** :
   - Les chemins de fichiers sont exacts (utiliser `glob_file_search` ou `read_file` pour vérifier)
   - Les noms de fonctions/classes correspondent au code
   - Les valeurs par défaut (env vars, etc.) sont correctes

### Étape 4 : Mettre à Jour la Date

Mettre à jour la date de "Dernière mise à jour" dans `README.md` :

```markdown
**Dernière mise à jour** : YYYY-MM-DD
```

## 🎯 Instructions pour l'IA (Cursor/Claude)

Quand vous demandez à l'IA de mettre à jour la documentation, utilisez ce format :

### Template de Requête

```
Je veux mettre à jour la documentation Email Builder car j'ai fait les changements suivants :

**Fichiers modifiés :**
- `api/services/ai_email/routes.py` (lignes 48-109)
- `web/src/components/ai-email/EmailOutput.tsx` (nouveau composant)
- `web/prisma/schema.prisma` (ajout champ `Email.deliveredAt`)

**Changements effectués :**
1. Ajout endpoint `POST /api/ai/email/send` pour envoyer des emails
2. Ajout champ `deliveredAt` au modèle `Email` dans Prisma
3. Modification du composant `EmailOutput` pour afficher un nouveau mode "Live"

**Type de changement :**
- Nouveau endpoint API
- Modification schéma DB
- Nouveau composant frontend

**Documents à mettre à jour :**
- ARCHITECTURE_BACKEND.md (nouveau endpoint)
- ARCHITECTURE_FRONTEND.md (nouveau composant, nouveau mode)
- OVERVIEW.md (nouveau workflow "Send Email")
- RUNBOOK.md (nouvelle variable d'environnement si nécessaire)
- README.md (date mise à jour)

**Instructions spécifiques :**
- Documenter le nouvel endpoint dans la section 2 des endpoints FastAPI
- Ajouter le nouveau mode "Live" dans la section 8.2 (Preview Modes)
- Mettre à jour le workflow utilisateur dans OVERVIEW.md pour inclure "Send Email"
- Vérifier que tous les exemples JSON incluent le nouveau champ `deliveredAt` si applicable
```

### Ce que l'IA doit faire

1. **Lire les fichiers modifiés** pour comprendre les changements exacts :
   ```python
   read_file("api/services/ai_email/routes.py", offset=48, limit=62)
   read_file("web/src/components/ai-email/EmailOutput.tsx")
   ```

2. **Lire les documents existants** pour comprendre la structure :
   ```python
   read_file("docs/email/ARCHITECTURE_BACKEND.md")
   read_file("docs/email/ARCHITECTURE_FRONTEND.md")
   ```

3. **Mettre à jour les sections concernées** :
   - Maintenir le format et la structure existants
   - Ajouter les nouvelles sections si nécessaire
   - Supprimer/modifier les sections obsolètes
   - Vérifier la cohérence avec le reste du document

4. **Vérifier la précision** :
   - Utiliser `grep` ou `codebase_search` pour vérifier les chemins de fichiers
   - Vérifier que les exemples JSON correspondent aux schémas réels
   - S'assurer que les références croisées fonctionnent

5. **Mettre à jour README.md** :
   - Changer la date de "Dernière mise à jour"

## 📚 Conventions de Style

### Structure

- **Sections numérotées** : Utiliser hiérarchie logique (1, 1.1, 1.1.1, etc.)
- **Titres clairs** : Descriptifs et précis
- **Liens croisés** : Utiliser format `[ARCHITECTURE_BACKEND.md](./ARCHITECTURE_BACKEND.md)`

### Références au Code

- **Chemins de fichiers** : Utiliser chemins relatifs depuis la racine du repo
  - ✅ `api/services/ai_email/routes.py`
  - ❌ `./routes.py` ou `routes.py`

- **Numéros de lignes** : Si référencés, utiliser format `lignes X-Y`
  - ✅ `lignes 48-109`
  - ✅ `ligne 23`

- **Noms de fonctions/classes** : Utiliser format inline code
  - ✅ La fonction `compose_email_spec()` dans `agent.py`
  - ❌ La fonction compose_email_spec dans agent.py

### Exemples de Code

- **JSON** : Utiliser format markdown code block avec `json`
  ```json
  {
    "subject": "Welcome",
    "blocks": [...]
  }
  ```

- **TypeScript/Python** : Utiliser format markdown code block avec langage
  ```typescript
  export interface EmailSpec {
    subject: string
    blocks: Block[]
  }
  ```

- **Schémas ASCII** : Utiliser format préformaté (``` sans langage)

### Variables d'Environnement

- **Format** : `NOM_VAR=value` (avec description)
- **Grouper** : Par contexte (Backend vs Frontend)
- **Indiquer** : Required vs Optional avec `# Required` ou `# Optional`

### Workflows Utilisateurs

- **Format** : Liste numérotée avec étapes claires
- **Inclure** : Fichiers clés référencés pour chaque étape
- **Source** : Toujours indiquer la source (`**Source** : fichier.ts`)

## 🔄 Checklist Rapide pour Mise à Jour

Avant de demander à l'IA de mettre à jour :

- [ ] J'ai identifié tous les fichiers de code modifiés
- [ ] J'ai listé tous les changements effectués
- [ ] J'ai identifié quels documents sont affectés
- [ ] J'ai préparé un résumé clair des changements
- [ ] J'ai vérifié que je peux expliquer le "pourquoi" de chaque changement

## 📖 Exemple Complet

### Scénario : Ajout d'un nouveau bloc "VIDEO"

**Changements effectués :**
1. Ajout `VideoBlock` dans `api/services/ai_email/schemas.py`
2. Ajout `VIDEO` au registry dans `api/services/ai_email/registry.py`
3. Création `api/services/ai_email/blocks/video.py`
4. Ajout `VideoBlock` dans `web/src/components/ai-email/types.ts`
5. Ajout `VideoEditor` dans `web/src/components/ai-email/BlockEditor/editors/`

**Requête à l'IA :**

```
Je veux mettre à jour la documentation Email Builder car j'ai ajouté un nouveau type de bloc "VIDEO".

**Fichiers modifiés :**
- `api/services/ai_email/schemas.py` (ajout VideoBlock)
- `api/services/ai_email/registry.py` (ajout VIDEO au registry)
- `api/services/ai_email/blocks/video.py` (nouveau fichier renderer)
- `api/services/ai_email/render.py` (ajout case video dans _render_block)
- `api/services/ai_email/system_prompt.py` (ajout description VIDEO)
- `web/src/components/ai-email/types.ts` (ajout VideoBlock interface)
- `web/src/components/ai-email/schema.ts` (ajout VideoBlockSchema)
- `web/src/components/ai-email/BlockEditor/editors/VideoEditor.tsx` (nouveau composant)

**Changements effectués :**
1. Nouveau bloc VIDEO avec variant "youtube" uniquement
2. Props: video_url (https://youtube.com/...), thumbnail_url, title, description
3. Slot: "optional" (max 2 occurrences)
4. Renderer MJML pour iframe YouTube responsive
5. Éditeur manuel VideoEditor dans BlockEditor

**Type de changement :**
- Nouveau type de bloc (backend + frontend)

**Documents à mettre à jour :**
- ARCHITECTURE_BACKEND.md (section 3.2 Block Types, section 4.2 Slot Metadata, section 7.3 Block Renderers)
- ARCHITECTURE_FRONTEND.md (section 2.6 Block Editors)
- RUNBOOK.md (section 4.2 Add a New Block Type - exemple avec VIDEO)
- OVERVIEW.md (section 6.2 Types autorisés)

**Instructions spécifiques :**
- Ajouter VIDEO dans la liste des 10 types de blocs (deviendra 11)
- Documenter variant "youtube", props, slot optional, max 2
- Ajouter VideoEditor dans la liste des éditeurs
- Mettre à jour l'exemple dans RUNBOOK.md pour inclure VIDEO
- Vérifier que tous les exemples JSON sont à jour
```

## ✅ Validation Finale

Après mise à jour par l'IA, vérifier :

- [ ] Tous les documents mentionnés ont été mis à jour
- [ ] Les exemples de code correspondent au code réel
- [ ] Les chemins de fichiers sont corrects
- [ ] La cohérence entre documents est maintenue
- [ ] La date dans README.md est à jour
- [ ] Les liens croisés fonctionnent
- [ ] Les conventions de style sont respectées

## 🆘 En Cas de Problème

Si la mise à jour n'est pas complète ou incorrecte :

1. **Identifier les sections manquantes** : Lister précisément ce qui manque
2. **Fournir plus de contexte** : Partager les fichiers de code concernés
3. **Demander une relecture** : Demander à l'IA de relire les documents mis à jour
4. **Vérifier manuellement** : Comparer avec le code source réel

## 📝 Notes Importantes

- **Précision avant tout** : Mieux vaut ne documenter que ce qui est sûr plutôt que d'inventer
- **Références exactes** : Toujours vérifier les chemins de fichiers avec `glob_file_search` ou `read_file`
- **Exemples réels** : Les exemples JSON/Code doivent être extraits du code réel, pas inventés
- **Cohérence** : S'assurer que les changements sont cohérents dans tous les documents affectés

---

**Dernière mise à jour de ce guide** : 2026-01-07









