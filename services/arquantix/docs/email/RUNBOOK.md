# Email Builder - Runbook & Extension Guide

## 1. Local Setup

### 1.1. Backend (FastAPI)

**Prérequis** :
- Python 3.9+
- pip
- PostgreSQL (optionnel pour MVP, utilise SQLite ou in-memory)

**Installation** :
```bash
cd api
pip install -r requirements.txt
```

**Variables d'environnement** (`.env` ou `.env.local`) :
```bash
OPENAI_API_KEY=sk-...          # Required
OPENAI_MODEL=gpt-4o-mini       # Optional, default: gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
DATABASE_URL=postgresql://...  # Optional (si DB utilisée)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001  # Optional
```

**Démarrer** :
```bash
cd api
uvicorn main:app --reload --port 8000
```

**Vérifier** :
- `http://localhost:8000/health` → `{"status": "ok"}`
- `http://localhost:8000/api/ai/email/templates` → liste des templates (avec auth)

**Source** : `api/README.md`

### 1.2. Frontend (Next.js)

**Prérequis** :
- Node.js 18+
- npm ou yarn
- MJML (via `npx`, installé automatiquement)

**Installation** :
```bash
cd web
npm install
```

**Variables d'environnement** (`.env.local`) :
```bash
OPENAI_API_KEY=sk-...          # Required (server-side only)
OPENAI_MODEL=gpt-4o-mini       # Optional, default: gpt-4o-mini
DATABASE_URL=postgresql://...  # Required (Prisma)
BACKEND_URL=http://localhost:8000  # Optional (pour proxy FastAPI)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000  # Optional
```

**Base de données (Prisma)** :
```bash
cd web
npx prisma generate  # Générer Prisma Client
npx prisma db push   # Appliquer schéma (dev)
# ou
npx prisma migrate dev  # Créer migration (production)
```

**Seed des données par défaut (Email Modules & Templates)** :
```bash
cd web
npm run seed:email   # Crée header_default, content_default, footer_default modules + base_v1_db template
```

**Note** : Le seed est idempotent (peut être exécuté plusieurs fois sans problème). Il crée :
- **Modules** :
  - `header_default` (HEADER) : En-tête avec titre et texte
  - `content_default` (CUSTOM) : Module de contenu de base (utilisé comme body starter)
  - `footer_default` (FOOTER) : Pied de page avec SOCIAL_ICONS, texte légal, FOOTER avec `{{unsubscribe_url}}`
- **Template** :
  - `base_v1_db` : Template utilisant `header_default` et `footer_default`, avec `content_default` comme body starter

Ces modules et templates sont créés avec status `VALIDATED` et peuvent être utilisés immédiatement dans l'Email Builder.

**Démarrer** :
```bash
cd web
npm run dev
```

**Vérifier** :
- `http://localhost:3000/admin/ai/email` → Email Builder
- `http://localhost:3000/admin/emails` → Liste emails

**Source** : `web/`

### 1.3. MJML Requirements

**Installation** :
- MJML est installé automatiquement via `npx --yes mjml`
- Nécessite Node.js (déjà requis pour Next.js)

**Vérifier** :
```bash
npx --yes mjml --version
```

**Alternative** : Installer globalement (optionnel)
```bash
npm install -g mjml
```

**Source** : `web/src/lib/ai-email/compileMjml.ts`, `api/services/ai_email/render.py`

## 2. Common Issues & Fixes

### 2.1. MJML Not Installed / npx Fails

**Symptôme** : Erreur "Node.js/npx not found" ou "MJML compilation failed"

**Solutions** :
1. Vérifier que Node.js est installé : `node --version`
2. Vérifier que `npx` est disponible : `npx --version`
3. Installer MJML globalement : `npm install -g mjml`
4. Vérifier les logs stderr pour détails MJML

**Source** : `web/src/lib/ai-email/compileMjml.ts` lignes 124-127

### 2.2. OpenAI JSON Invalid

**Symptôme** : Erreur "No valid JSON found in response" ou "Registry validation failed"

**Solutions** :
1. Vérifier que `OPENAI_API_KEY` est configurée et valide
2. Vérifier les logs OpenAI pour détails (rate limit, quota, etc.)
3. Vérifier que le model supporte `response_format: { type: "json_object" }`
4. Vérifier que le system prompt est correct (registry rigide)
5. Vérifier que le retry logic fonctionne (fallback vers base spec)

**Source** : `api/services/ai_email/agent.py` lignes 72-146

### 2.3. LockStructure Warnings

**Symptôme** : Warnings "Ignored extra IMAGE block (max=1)" ou "Cannot remove core block CTA"

**Explication** :
- C'est **normal** : le système verrouille la structure du template
- Les warnings indiquent que certaines modifications ont été ignorées
- La structure finale correspond au template de base

**Actions** :
- Si le warning est incorrect, vérifier le template (`templates_presets/arquantix_v1.py`)
- Si le warning est correct, utiliser "Manual Edit" pour ajouter/supprimer des blocs optionnels

**Source** : `api/services/ai_email/lock.py` lignes 24-162

### 2.4. CORS/Proxy Issues

**Symptôme** : Erreur "Backend unavailable, using local fallback" ou CORS errors

**Solutions** :
1. **Vérifier que le backend FastAPI est démarré** :
   ```bash
   curl http://localhost:8000/health
   ```

2. **Vérifier `CORS_ORIGINS` dans le backend** :
   ```bash
   CORS_ORIGINS=http://localhost:3000,http://localhost:3001
   ```

3. **Vérifier `BACKEND_URL` dans le frontend** :
   ```bash
   BACKEND_URL=http://localhost:8000
   ```

4. **Note** : Le fallback local fonctionne même si le backend n'est pas accessible (templates désactivés)

**Source** : `web/src/app/api/ai/email/compose/route.ts` lignes 25-134

### 2.5. Iframe Preview Blank

**Symptôme** : Prévisualisation Desktop/Mobile vide (iframe blanche)

**Solutions** :
1. Vérifier que `html` n'est pas vide (logs console)
2. Vérifier que `compileMjml()` n'a pas retourné d'erreur
3. Vérifier la console navigateur pour erreurs iframe (sandbox restrictions)
4. Vérifier que `srcDoc` est utilisé (pas `src` externe)

**Source** : `web/src/components/ai-email/EmailOutput.tsx`

### 2.6. Prisma Client Not Available

**Symptôme** : Erreur "Cannot read properties of undefined (reading 'create')" ou "prisma.email is undefined"

**Solutions** :
1. **Régénérer Prisma Client** :
   ```bash
   cd web
   npx prisma generate
   ```

2. **Redémarrer le serveur Next.js** :
   ```bash
   # Arrêter le serveur (Ctrl+C)
   npm run dev
   ```

3. **Vérifier que le modèle Email existe dans `schema.prisma`** :
   ```prisma
   model Email {
     ...
   }
   ```

4. **Appliquer le schéma** :
   ```bash
   npx prisma db push
   ```

5. **Vider le cache Next.js** :
   ```bash
   rm -rf .next
   ```

**Source** : `web/src/lib/prisma.ts`, `web/prisma/schema.prisma`

## 3. How to Debug

### 3.1. Where Logs Are

**Backend FastAPI** :
- Console FastAPI (terminal où `uvicorn` tourne)
- Format : `print(f"[AI Email] ...")` ou `console.error(...)`
- Logs : erreurs OpenAI, MJML compilation, registry validation

**Frontend Next.js** :
- Console Next.js (terminal où `npm run dev` tourne)
- Format : `console.error('[AI Email] ...')` ou `console.log(...)`
- Logs : erreurs API, validation Zod, database errors

**Frontend Browser** :
- Console navigateur (F12 → Console)
- Logs : erreurs réseau, erreurs React, erreurs iframe

**Source** : Voir fichiers avec `console.error` ou `print`

### 3.2. How to Reproduce Typical Failures

**1. Test OpenAI JSON Invalid** :
- Désactiver `response_format: { type: "json_object" }` dans `agent.py`
- Envoyer prompt : "Create a welcome email"
- Observer erreur "No valid JSON found"

**2. Test Registry Validation Failed** :
- Modifier `EMAIL` bloc dans `schemas.py` pour avoir un type non autorisé
- Envoyer prompt : "Create a welcome email"
- Observer erreur "Registry validation failed"

**3. Test LockStructure Warnings** :
- Créer email avec template `welcome_v1`
- Envoyer prompt : "Add 2 images and remove the CTA"
- Observer warnings "Ignored extra IMAGE block (max=1)" et "Cannot remove core block CTA"

**4. Test MJML Compilation Failed** :
- Désinstaller Node.js ou `npx`
- Générer un email
- Observer erreur "Node.js/npx not found"

**5. Test Backend Unavailable** :
- Arrêter le backend FastAPI
- Générer un email
- Observer warning "Backend unavailable, using local fallback"

**Source** : Fichiers correspondants pour chaque test

## 4. How to Add/Extend

### 4.1. Add a New Template

**Fichiers à modifier** :
- `api/services/ai_email/templates_presets/arquantix_v1.py`
- `web/src/app/api/ai/email/templates/route.ts` (si hardcodé)

**Structure** :
1. **Créer fonction builder** :
   ```python
   def _create_my_template_v1(locale: str = "en") -> EmailSpec:
       """Template: My Template"""
       return EmailSpec(
           subject="My Subject",
           preheader="My Preheader",
           locale=locale,
           theme="arquantix_v1",
           blocks=[
               HeroBlock(...),
               TextBlock(...),
               FooterBlock(...),
           ],
       )
   ```

2. **Enregistrer template** :
   ```python
   register_template(EmailTemplate(
       id="my_template_v1",
       name="My Template",
       description="Description of my template",
       initial_spec_builder=_create_my_template_v1,
       locked=True,
   ))
   ```

3. **Mettre à jour frontend** (si hardcodé) :
   ```typescript
   const TEMPLATES = [
     ...existingTemplates,
     {
       id: 'my_template_v1',
       name: 'My Template',
       description: 'Description of my template',
       locked: true,
     },
   ]
   ```

**Source** : `api/services/ai_email/templates_presets/arquantix_v1.py`

### 4.2. Add a New Block Type

**Fichiers à modifier** :
1. `api/services/ai_email/schemas.py` - Ajouter Pydantic model
2. `api/services/ai_email/registry.py` - Ajouter au registry + BLOCK_DEFINITIONS
3. `api/services/ai_email/blocks/my_block.py` - Créer renderer
4. `api/services/ai_email/render.py` - Ajouter case dans `_render_block()`
5. `api/services/ai_email/system_prompt.py` - Ajouter au system prompt
6. `web/src/components/ai-email/types.ts` - Ajouter TypeScript type
7. `web/src/components/ai-email/schema.ts` - Ajouter Zod schema
8. `web/src/lib/ai-email/buildMjml.ts` - Ajouter case (si fallback local)

**Structure** :

**1. Schema (Pydantic)** :
```python
class MyBlock(BaseModel):
    type: Literal["my_block"] = "my_block"
    variant: Literal["default"] = "default"
    title: str = Field(..., min_length=1, max_length=120)
    # ... autres props
    
    model_config = {"extra": "forbid"}
```

**2. Registry** :
```python
BLOCK_REGISTRY: Dict[str, List[str]] = {
    ...
    "MY_BLOCK": ["default"],
}

MAX_BLOCKS_PER_TYPE: Dict[str, int] = {
    ...
    "MY_BLOCK": 3,
}

BLOCK_DEFINITIONS: Dict[Tuple[str, str], BlockDefinition] = {
    ...
    ("MY_BLOCK", "default"): BlockDefinition(
        type="MY_BLOCK",
        variant="default",
        slot="core",  # or "optional"
        max_occurrences=3,
        editable_props=["title", ...],
    ),
}
```

**3. Renderer** :
```python
def render_my_block(block: MyBlock, theme_name: str = "arquantix_v1") -> str:
    """Render MY_BLOCK block to MJML using theme"""
    theme = get_theme(theme_name)
    # ... MJML generation ...
    return mjml_string
```

**4. System Prompt** :
Ajouter description du bloc dans `SYSTEM_PROMPT` (lignes 25-65)

**5. Frontend Types** :
```typescript
export interface MyBlock {
  type: 'my_block'
  variant?: 'default'
  title: string
  // ... autres props
}

export type Block = ... | MyBlock
```

**Source** : Voir fichiers correspondants pour exemples

### 4.3. Add Optional Slots for a Template

**Fichiers à modifier** :
- `api/services/ai_email/templates_presets/arquantix_v1.py`

**Structure** :
1. **Identifier les blocs optionnels** dans le template :
   - Ex: `IMAGE`, `DIVIDER`, `SPACER` sont des blocs optionnels
   - Documenter `max_occurrences` dans les commentaires

2. **Vérifier le registry** :
   - Les blocs doivent être marqués `slot="optional"` dans `BLOCK_DEFINITIONS`
   - Vérifier `max_occurrences` correspond

**Exemple** :
```python
def _create_newsletter_v1(locale: str = "en") -> EmailSpec:
    """Template: Newsletter
    
    Core blocks: HERO, SECTION_TITLE, TEXT, FEATURE_CARDS, CTA, FOOTER
    Optional slots:
    - IMAGE (max 1, after SECTION_TITLE)
    - DIVIDER (max 2)
    - SPACER (md/lg)
    """
    return EmailSpec(
        ...
    )
```

**Source** : `api/services/ai_email/templates_presets/arquantix_v1.py`

### 4.4. Add a New Email Module (DB)

**Workflow** :
1. Naviguer vers `/admin/email-modules`
2. Cliquer "New Module"
3. Remplir formulaire :
   - Slug : `my_module`
   - Name : `My Module`
   - Type : `HEADER` | `FOOTER` | `CUSTOM` | etc.
   - Description : (optionnel)
   - Spec : JSON EmailSpec avec blocs autorisés pour le type
4. Sauvegarder (créé en DRAFT)
5. Prévisualiser et éditer si nécessaire
6. Cliquer "Validate Module" → status devient VALIDATED
7. Une fois VALIDATED, peut être utilisé dans les templates

**Contraintes par type de module** :
- **HEADER** : Blocs autorisés : `section_title`, `text`, `divider`, `spacer`
- **FOOTER** : Blocs autorisés : `social_icons`, `text`, `bullets`, `divider`, `footer` (doit contenir `{{unsubscribe_url}}`)
- **CUSTOM** : Tous types de blocs autorisés (sauf header/footer si dans un autre contexte)

**Source** : `web/src/app/admin/email-modules/[id]/page.tsx`, `web/src/app/api/admin/email-modules/validate.ts`

### 4.5. Add a New Email Template (DB)

**Workflow** :
1. Naviguer vers `/admin/email-templates`
2. Cliquer "New Template"
3. Remplir formulaire :
   - Slug : `my_template`
   - Name : `My Template`
   - Header Module : Sélectionner un module HEADER (doit être VALIDATED)
   - Footer Module : Sélectionner un module FOOTER (doit être VALIDATED)
   - Body Starter Module : (optionnel) Module pour initialiser le body spec
   - Hero Policy : `REQUIRED` | `OPTIONAL`
   - Body Template : JSON définissant la structure BODY autorisée (core blocks + optional slots)
   - Lock Policy : JSON définissant les règles de verrouillage
4. Sauvegarder (créé en DRAFT)
5. Prévisualiser la structure
6. Cliquer "Validate Template" → status devient VALIDATED
7. Une fois VALIDATED, apparaît dans AI Studio template selector

**Body Template Structure** :
```json
{
  "core_blocks": [
    { "type": "HERO", "variant": "text_only" },
    { "type": "TEXT", "variant": "body" },
    { "type": "CTA", "variant": "primary" }
  ],
  "optional_slots": {
    "IMAGE": { "max": 1 },
    "DIVIDER": { "max": 2 }
  }
}
```

**Source** : `web/src/app/admin/email-templates/[id]/page.tsx`, `web/src/app/api/admin/email-templates/[id]/route.ts`

### 4.6. Add a Provider Export Endpoint (Future)

**Fichiers à créer/modifier** :
1. `api/services/ai_email/exporters/sendgrid.py` - Export SendGrid
2. `api/services/ai_email/exporters/mailchimp.py` - Export Mailchimp
3. `api/services/ai_email/routes.py` - Ajouter endpoint `POST /api/ai/email/[id]/export`
4. `web/src/app/api/admin/emails/[id]/export/route.ts` - Proxy Next.js

**Structure** :

**1. Exporter** :
```python
def export_to_sendgrid(email: Email, locale: str) -> dict:
    """Export EmailSpec to SendGrid format"""
    spec = email.spec if locale == email.locale else email.translations[locale].spec
    # ... conversion SendGrid ...
    return sendgrid_payload
```

**2. Endpoint** :
```python
@router.post("/email/{email_id}/export")
async def export_email(
    email_id: str,
    provider: str = "sendgrid",
    locale: str = "en",
    current_user: AdminUser = Depends(get_current_user)
):
    """Export email to provider (SendGrid, Mailchimp, etc.)"""
    # ... validation ...
    # ... export ...
    return {"status": "exported", "provider": provider}
```

**Source** : À créer (non présent actuellement)

## 5. Environment Variables Reference

### 5.1. Backend (FastAPI)

```bash
OPENAI_API_KEY=sk-...          # Required
OPENAI_MODEL=gpt-4o-mini       # Optional, default: gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
DATABASE_URL=postgresql://...  # Optional (si DB utilisée)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001  # Optional
ARQUANTIX_EMAIL_LOGO_URL=https://...  # Optional (logo URL pour header)
```

**Source** : `api/services/ai_email/agent.py`, `api/main.py`

### 5.2. Frontend (Next.js)

```bash
OPENAI_API_KEY=sk-...          # Required (server-side only)
OPENAI_MODEL=gpt-4o-mini       # Optional, default: gpt-4o-mini
OPENAI_TRANSLATION_TEMPERATURE=0  # Optional, default: 0
OPENAI_TRANSLATION_MAX_CHARS=12000  # Optional, default: 12000
DATABASE_URL=postgresql://...  # Required (Prisma)
BACKEND_URL=http://localhost:8000  # Optional (pour proxy FastAPI)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000  # Optional
```

**Source** : `web/src/lib/openai/client.ts`, `web/src/app/api/ai/email/compose/route.ts`

## 6. Testing Checklist

**Avant de déployer** :

1. ✅ Backend FastAPI démarre correctement
2. ✅ Frontend Next.js démarre correctement
3. ✅ OpenAI API key configurée et valide
4. ✅ MJML compilation fonctionne (`npx mjml`)
5. ✅ Prisma Client généré et tables créées
6. ✅ Email Builder génère un email avec prompt
7. ✅ Save Draft fonctionne (redirection vers `/admin/emails/[id]`)
8. ✅ Validate fonctionne (status DRAFT → VALIDATED)
9. ✅ Auto-translate fonctionne (post-validation)
10. ✅ Preview Desktop/Mobile/Code fonctionne
11. ✅ Manual Edit fonctionne (ajout/suppression blocs optionnels)
12. ✅ LockStructure warnings affichés correctement
13. ✅ Fallback local fonctionne si backend inaccessible

## 7. Next Steps

Pour approfondir :
- **Overview** → [OVERVIEW.md](./OVERVIEW.md)
- **Architecture Backend** → [ARCHITECTURE_BACKEND.md](./ARCHITECTURE_BACKEND.md)
- **Architecture Frontend** → [ARCHITECTURE_FRONTEND.md](./ARCHITECTURE_FRONTEND.md)

