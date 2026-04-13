# Email Builder & Emails System Documentation

Documentation complète du système Email Builder et de gestion des emails dans Arquantix CMS.

## 📚 Documents

1. **[OVERVIEW.md](./OVERVIEW.md)** - Vue d'ensemble du système, principes clés, workflow utilisateur
2. **[ARCHITECTURE_BACKEND.md](./ARCHITECTURE_BACKEND.md)** - Architecture backend (FastAPI), endpoints, modèles de données, MJML
3. **[ARCHITECTURE_FRONTEND.md](./ARCHITECTURE_FRONTEND.md)** - Architecture frontend (Next.js), routes admin, composants, état
4. **[RUNBOOK.md](./RUNBOOK.md)** - Guide d'installation, dépannage, extension du système
5. **[UGG_TEMPLATE.md](./UGG_TEMPLATE.md)** - Documentation du template unique `arquantix_ugg_v1` et schéma EmailSpecUGG
6. **[HOW_TO_UPDATE_DOCS.md](./HOW_TO_UPDATE_DOCS.md)** - Guide pour maintenir cette documentation à jour

## 🎯 Vue d'ensemble rapide

Le système Email Builder permet de :
- Générer des emails avec l'IA (OpenAI) via des prompts en langage naturel
- Utiliser un template unique "golden" : `arquantix_ugg_v1` (basé sur MJML UGG-style)
- Schéma JSON strict `EmailSpecUGG` (pas de blocs génériques)
- Sauvegarder des brouillons dans la base de données
- Valider les emails (structure fixe définie par template MJML)
- Traduire automatiquement en plusieurs langues (post-validation)
- Prévisualiser en Desktop/Mobile/Code

**Contraintes critiques** :
- OpenAI ne génère JAMAIS de HTML/MJML, uniquement du JSON EmailSpecUGG strict
- Template unique : `arquantix_ugg_v1` (structure fixe dans MJML)
- Schéma strict : EmailSpecUGG avec champs dédiés (offer_line, headline_lines, carousel, etc.)
- MJML compilé backend uniquement
- Clé OpenAI jamais exposée au frontend

## 🚀 Démarrage rapide

### Backend (FastAPI)
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)
```bash
cd web
npm install
npm run dev
```

### Variables d'environnement
```bash
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
BACKEND_URL=http://localhost:8000  # optionnel (fallback local)
```

## 📖 Structure des documents

Chaque document suit une structure claire :
- **Sections numérotées** avec hiérarchie logique
- **Exemples concrets** avec code réel du repo
- **Schémas ASCII** pour visualiser les flux
- **Références précises** aux fichiers du repo
- **Points d'attention** pour le debugging

## 🔍 Navigation rapide

### Je veux comprendre...
- **Comment ça marche** → [OVERVIEW.md](./OVERVIEW.md)
- **Les APIs backend** → [ARCHITECTURE_BACKEND.md](./ARCHITECTURE_BACKEND.md#endpoints)
- **Les composants frontend** → [ARCHITECTURE_FRONTEND.md](./ARCHITECTURE_FRONTEND.md#components)
- **Installer localement** → [RUNBOOK.md](./RUNBOOK.md#local-setup)
- **Débugger un problème** → [RUNBOOK.md](./RUNBOOK.md#troubleshooting)
- **Ajouter un template** → [RUNBOOK.md](./RUNBOOK.md#add-template)
- **Ajouter un bloc** → [RUNBOOK.md](./RUNBOOK.md#add-block)
- **Mettre à jour la doc** → [HOW_TO_UPDATE_DOCS.md](./HOW_TO_UPDATE_DOCS.md)

## ⚠️ Notes importantes

1. **Backend FastAPI optionnel** : Le frontend peut fonctionner en mode "fallback local" si le backend n'est pas accessible. Les templates et le verrouillage de structure sont désactivés dans ce mode.

2. **MJML requis** : La compilation MJML nécessite Node.js et `npx mjml`. Installer via `npm install -g mjml` ou laisser `npx` l'installer automatiquement.

3. **Clé OpenAI** : Doit être configurée côté serveur (Next.js API routes) uniquement. Jamais exposée au client.

4. **Base de données** : Les emails sont persistés dans PostgreSQL via Prisma (`Email` et `EmailI18n` models).

## 📝 Mises à jour

Cette documentation est maintenue à jour avec le code. En cas de divergence, référez-vous au code source comme source de vérité.

**Dernière mise à jour** : 2026-01-09

### 🆕 Changements récents (2026-01-09)

- **Reset Template System** : Un seul template "golden" `arquantix_ugg_v1` basé sur MJML UGG-style
- **Nouveau schéma EmailSpecUGG** : Schéma JSON strict dédié au template UGG (pas de blocs génériques)
- **Nouvel endpoint `/api/ai/email/compose-ugg`** : Génération d'emails avec template UGG uniquement
- **Template MJML hardcodé** : `arquantix_ugg_v1.mjml` avec placeholders remplacés par EmailSpecUGG
- **Anciens templates archivés** : Tous les templates précédents (welcome_v1, newsletter_v1, etc.) sont en status DRAFT
- **Documentation UGG** : Nouveau document `UGG_TEMPLATE.md` expliquant le schéma et l'utilisation

### 📦 Changements précédents (2026-01-08)

- **V6 - Module Builder & Template Builder** : Ajout de la création de modules réutilisables (Header, Footer) et de templates DB (archivé)
- **Bloc SOCIAL_ICONS** : Nouveau bloc pour icônes sociales dans les modules Footer (archivé)
- **bodyStarterModuleId** : Support pour modules qui initialisent le body spec lors de la création d'emails (archivé)
- **Badges dans EmailOutput** : Affichage des badges indiquant l'origine du contenu (module vs AI) (archivé)
- **Pages de détail** : Ajout des pages de détail pour modules et templates (archivé)
- **Seed script** : `npm run seed:email` pour créer les modules et templates par défaut (archivé)
- **Corrections HTML** : Amélioration du sandbox iframe pour permettre l'affichage du contenu

