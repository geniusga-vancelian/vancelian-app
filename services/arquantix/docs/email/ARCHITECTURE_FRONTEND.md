# Email Builder - Frontend Architecture

## 1. Next.js Admin Routes

Le frontend Email Builder utilise Next.js App Router sous `/web/src/app/`.

```
web/src/app/
├── admin/
│   ├── ai/email/
│   │   └── page.tsx                # Email Builder (composer)
│   ├── emails/
│   │   ├── page.tsx                 # Emails list
│   │   └── [id]/
│   │       └── page.tsx             # Email detail (preview/translations/meta)
│   ├── email-modules/
│   │   ├── page.tsx                 # Email Modules list
│   │   └── [id]/
│   │       └── page.tsx             # Email Module detail (preview/translations/meta)
│   └── email-templates/
│       ├── page.tsx                 # Email Templates list
│       └── [id]/
│           └── page.tsx             # Email Template detail (info/meta)
└── api/
    ├── ai/email/
    │   ├── compose-ugg/route.ts      # Compose email UGG (proxy to FastAPI)
    │   ├── compose/route.ts         # Ancien compose (archivé)
    │   ├── templates/route.ts       # List templates (retourne uniquement arquantix_ugg_v1)
    │   ├── compile/route.ts         # Compile MJML → HTML
    │   └── voice/transcribe/route.ts # Audio transcription (OpenAI Whisper)
    └── admin/
        ├── emails/
        │   ├── route.ts             # POST (create), GET (list)
        │   └── [id]/
        │       ├── route.ts         # GET, PUT (update), DELETE
        │       └── validate/route.ts # POST (validate → VALIDATED)
        ├── email-modules/
        │   ├── route.ts             # POST (create), GET (list)
        │   ├── [id]/
        │   │   ├── route.ts         # GET, PUT (update DRAFT only), DELETE
        │   │   └── validate/route.ts # POST (validate → VALIDATED)
        │   └── validate.ts          # Validation helpers (allowed block types per module type)
        ├── email-templates/
        │   ├── route.ts             # POST (create), GET (list)
        │   └── [id]/
        │       ├── route.ts         # GET, PUT (update DRAFT only), DELETE
        │       └── validate/route.ts # POST (validate → VALIDATED)
        └── translate/
            ├── email/route.ts       # POST (auto-translate EmailSpec)
            ├── email-module/route.ts # POST (auto-translate EmailModule)
            └── approve/route.ts     # POST (approve translation, extended for EMAIL_MODULE)
```

**Source** : `web/src/app/`

### 1.1. Email Builder (`/admin/ai/email`)

**Route** : `web/src/app/admin/ai/email/page.tsx`

**Fonctionnalités** :
- Chat interface (AI Copilot) pour générer emails via prompts
- Sélecteur de template (uniquement `arquantix_ugg_v1`)
- Bouton "Save Draft" (sauvegarde en base, redirige vers `/admin/emails/[id]`)
- Prévisualisation Desktop/Mobile/Code

**État local** :
- `previousSpec: EmailSpecUGG | null` - Spec précédente pour itération
- `selectedTemplateId: string` - Toujours `"arquantix_ugg_v1"`
- `mjml: string` - MJML généré (template rempli)
- `html: string` - HTML compilé

**Source** : `web/src/app/admin/ai/email/page.tsx`

### 1.2. Emails List (`/admin/emails`)

**Route** : `web/src/app/admin/emails/page.tsx`

**Fonctionnalités** :
- Table listant tous les emails (name, template, status, locale, updated)
- Bouton "New Email" → redirige vers `/admin/ai/email`
- Actions : "Open" → redirige vers `/admin/emails/[id]`

**Source** : `web/src/app/admin/emails/page.tsx`

### 1.3. Email Detail (`/admin/emails/[id]`)

**Route** : `web/src/app/admin/emails/[id]/page.tsx`

**Fonctionnalités** :
- **Header** :
  - Name, Status badge (DRAFT/VALIDATED)
  - Bouton "Validate" (si DRAFT) → change status à VALIDATED
- **Tabs** :
  - **Preview** :
    - Dropdown locale (source + traductions existantes)
    - Prévisualisation Desktop/Mobile/Code (reuse `EmailOutput`)
    - Badge TranslationStatus (MACHINE/APPROVED) si traduit
    - Bouton "Approve translation" (si MACHINE)
  - **Translations** :
    - Liste des traductions existantes (locale, status, updated)
    - Bouton "Auto-translate" → ouvre `TranslateModal`
  - **Meta** :
    - Informations read-only (id, template, theme, created, updated)

**Source** : `web/src/app/admin/emails/[id]/page.tsx`

### 1.4. Email Modules List (`/admin/email-modules`)

**Route** : `web/src/app/admin/email-modules/page.tsx`

**Fonctionnalités** :
- Table listant tous les modules (name, type, status, translations count, updated)
- Filtres : par type (HEADER, FOOTER, etc.), par status (DRAFT, VALIDATED)
- Bouton "New Module" → redirige vers création
- Actions : "Open" → redirige vers `/admin/email-modules/[id]`
- Empty state avec hint pour exécuter seed

**Source** : `web/src/app/admin/email-modules/page.tsx`

### 1.5. Email Module Detail (`/admin/email-modules/[id]`)

**Route** : `web/src/app/admin/email-modules/[id]/page.tsx`

**Fonctionnalités** :
- **Header** :
  - Name, slug, Status badge (DRAFT/VALIDATED)
  - Bouton "Validate Module" (si DRAFT) → change status à VALIDATED
- **Tabs** :
  - **Preview** :
    - Dropdown locale (source + traductions existantes)
    - Prévisualisation Desktop/Mobile/Code (reuse `EmailOutput`)
    - Badge TranslationStatus (MACHINE/APPROVED) si traduit
    - Bouton "Approve translation" (si MACHINE)
  - **Translations** :
    - Liste des traductions existantes (locale, status, updated)
    - Bouton "Auto-translate" → ouvre `TranslateModal` (uniquement si VALIDATED)
  - **Meta** :
    - Informations read-only (id, slug, type, theme, description, dates)

**Source** : `web/src/app/admin/email-modules/[id]/page.tsx`

### 1.6. Email Templates List (`/admin/email-templates`)

**Route** : `web/src/app/admin/email-templates/page.tsx`

**Fonctionnalités** :
- Table listant tous les templates (name, header module, footer module, status, updated)
- Filtre : par status (DRAFT, VALIDATED)
- Bouton "New Template" → redirige vers création
- Actions : "Open" → redirige vers `/admin/email-templates/[id]`
- Empty state avec hint pour exécuter seed

**Source** : `web/src/app/admin/email-templates/page.tsx`

### 1.7. Email Template Detail (`/admin/email-templates/[id]`)

**Route** : `web/src/app/admin/email-templates/[id]/page.tsx`

**Fonctionnalités** :
- **Header** :
  - Name, slug, Status badge (DRAFT/VALIDATED)
  - Bouton "Validate Template" (si DRAFT) → change status à VALIDATED
- **Sections** :
  - **Template Information** : ID, slug, theme, heroPolicy, description
  - **Modules** : Links vers header/footer modules, bodyStarterModuleId, fixedModuleIds
  - **Body Template Structure** : Core blocks + optional slots définis
  - **Lock Policy** : JSON formaté de la politique de verrouillage
  - **Metadata** : Created/updated dates

**Source** : `web/src/app/admin/email-templates/[id]/page.tsx`

## 2. Components

Les composants React sont dans `web/src/components/ai-email/`.

```
web/src/components/ai-email/
├── ChatStudio.tsx                   # AI chat interface (prompts + messages)
├── VoiceRecorder.tsx                # Audio recording → transcription
├── EmailOutput.tsx                  # Preview (Desktop/Mobile/Code)
├── HtmlViewer.tsx                   # Code viewer (HTML/MJML)
├── BlockEditor/
│   ├── BlockEditor.tsx              # Main manual editor (list of blocks)
│   ├── BlockCard.tsx                # Individual block card (type, variant, slot badge)
│   └── editors/
│       ├── HeroEditor.tsx           # Hero block editor (title, subtitle, image_url, cta)
│       ├── TextEditor.tsx           # Text block editor (heading, body)
│       ├── ImageEditor.tsx          # Image block editor (image_url, alt_text, caption)
│       └── CtaEditor.tsx            # CTA block editor (label, url, hint)
├── types.ts                         # TypeScript types (EmailSpec, Block, etc.)
├── schema.ts                        # Zod schemas (EmailSpecSchema, etc.)
├── api.ts                           # API client functions (composeEmail, listEmailTemplates, etc.)
└── registry-helpers.ts              # Frontend registry utils (getBlockDefinition)
```

**Source** : `web/src/components/ai-email/`

### 2.1. ChatStudio

**Fichier** : `web/src/components/ai-email/ChatStudio.tsx`

**Fonctionnalités** :
- Interface chat avec messages utilisateur/assistant
- Input texte + bouton microphone (VoiceRecorder)
- Sélecteur de template + toggle "Structure locked" + bouton "Reset"
- Appels API `composeEmail()` → met à jour `previousSpec` + génère MJML/HTML
- Affiche warnings backend (toast)

**État local** :
- `messages: Array<{role: 'user' | 'assistant', content: string}>` - Historique messages
- `input: string` - Input texte actuel
- `isLoading: boolean` - Loading state

**Props** :
- `onEmailGenerated: (spec, mjml, html, assistantText) => void` - Callback après génération
- `onTemplateChange?: (templateId: string, templateSource: 'hardcoded' | 'db') => void` - Callback quand template change
- `previousSpec?: EmailSpec` - Spec précédente pour itération
- `selectedTemplateId: string` - Template sélectionné
- `lockStructure: boolean` - Verrouillage de structure

**Template Loading** :
- Charge templates via `listEmailTemplates()` (hardcoded + DB)
- Affiche "(DB)" ou "(hardcoded)" dans le sélecteur
- Affiche warning si aucun template DB trouvé (hint pour seed)

**Source** : `web/src/components/ai-email/ChatStudio.tsx`

### 2.2. VoiceRecorder

**Fichier** : `web/src/components/ai-email/VoiceRecorder.tsx`

**Fonctionnalités** :
- Enregistrement audio via `MediaRecorder` (format: `audio/webm`)
- Upload vers `/api/ai/voice/transcribe` (OpenAI Whisper)
- Injection du transcript dans l'input du chat

**État local** :
- `isRecording: boolean` - État d'enregistrement
- `audioBlob: Blob | null` - Audio enregistré

**Props** :
- `onTranscript: (transcript: string) => void` - Callback avec transcript

**Source** : `web/src/components/ai-email/VoiceRecorder.tsx`

### 2.3. EmailOutput

**Fichier** : `web/src/components/ai-email/EmailOutput.tsx`

**Fonctionnalités** :
- Header avec title + segmented switch (Code/Desktop/Mobile) + boutons Copy HTML/MJML
- **Badges module vs AI** (uniquement pour templates DB) :
  - Affiche "Header: {name} (module)", "Body: AI", "Footer: {name} (module)"
  - Visible uniquement si `templateSource === 'db'` et modules définis
- Affichage Subject/Preheader
- **Code mode** : `HtmlViewer` pour HTML ou MJML
- **Desktop mode** : iframe avec `srcDoc={html}` et `sandbox="allow-same-origin"` (width ~640px)
- **Mobile mode** : iframe avec `srcDoc={html}` et `sandbox="allow-same-origin"` (width ~375px)

**Sécurité iframe** :
- `sandbox="allow-same-origin"` pour permettre l'affichage du contenu HTML
- Contenu injecté via `srcDoc` (pas `src` externe)
- Background gris clair + card pour preview
- HTML fallback par défaut si contenu vide

**Props** :
- `spec: EmailSpec | null` - EmailSpec à afficher
- `mjml: string` - MJML string
- `html: string` - HTML compilé
- `templateSource?: 'hardcoded' | 'db'` - Source du template (pour badges)
- `templateId?: string` - ID du template (pour référence)
- `headerModuleName?: string` - Nom du module header (pour badge)
- `footerModuleName?: string` - Nom du module footer (pour badge)

**Source** : `web/src/components/ai-email/EmailOutput.tsx`

### 2.4. BlockEditor

**Fichier** : `web/src/components/ai-email/BlockEditor/BlockEditor.tsx`

**Fonctionnalités** :
- Liste verticale de `BlockCard` pour chaque bloc
- Bouton "Add Optional Block" (menu filtré par slots autorisés)
- Gestion de l'édition manuelle (ouvre éditeur spécifique)
- Bouton "Remove" (visible uniquement pour slots optionnels)

**État local** :
- `editingBlockIndex: number | null` - Index du bloc en édition

**Props** :
- `spec: EmailSpec` - EmailSpec actuel
- `onUpdate: (spec: EmailSpec) => void` - Callback après mise à jour

**Source** : `web/src/components/ai-email/BlockEditor/BlockEditor.tsx`

### 2.5. BlockCard

**Fichier** : `web/src/components/ai-email/BlockEditor/BlockCard.tsx`

**Fonctionnalités** :
- Affiche type/variant du bloc
- Badge "🔒 Core block" ou "✨ Optional block"
- Bouton "Edit" → ouvre éditeur spécifique
- Bouton "Remove" (conditionnel pour slots optionnels)

**Props** :
- `block: Block` - Bloc à afficher
- `index: number` - Index dans `spec.blocks`
- `isCore: boolean` - Si bloc core (non supprimable)

**Source** : `web/src/components/ai-email/BlockEditor/BlockCard.tsx`

### 2.6. Block Editors (editors/*.tsx)

**Fichiers** : `web/src/components/ai-email/BlockEditor/editors/*.tsx`

**Fonctionnalités** :
- Éditeurs spécifiques pour chaque type de bloc (Hero, Text, Image, CTA)
- Affiche uniquement les props autorisées (`editableProps` depuis registry)
- Validation côté client (length, required)
- Aucun champ libre arbitraire

**Exemples** :
- `HeroEditor` : title, subtitle, image_url, cta_label, cta_url
- `TextEditor` : heading, body
- `ImageEditor` : image_url, alt_text, caption
- `CtaEditor` : label, url, hint

**Source** : `web/src/components/ai-email/BlockEditor/editors/*.tsx`

## 3. API Routes (Next.js)

### 3.1. POST `/api/ai/email/compose-ugg`

**Fichier** : `web/src/app/api/ai/email/compose-ugg/route.ts`

**Description** : Compose email avec template `arquantix_ugg_v1` (template unique "golden")

**Auth** : Requiert session (`getSessionFromCookie()`)

**Request** :
```json
{
  "prompt": "Create a welcome email for new users",
  "locale": "en",
  "previous_spec": { ... }  // optional EmailSpecUGG JSON
}
```

**Response** :
```json
{
  "assistant_text": "I've created a professional email...",
  "templateId": "arquantix_ugg_v1",
  "spec": { ... },  // EmailSpecUGG JSON
  "mjml": "<mjml>...</mjml>",
  "html": "<!DOCTYPE html>...",
  "warnings": [ ... ]  // optional
}
```

**Comportement** :
1. Proxy vers FastAPI `/api/ai/email/compose-ugg`
2. Création JWT token pour authentification FastAPI
3. Retourne la réponse FastAPI directement

**Source** : `web/src/app/api/ai/email/compose-ugg/route.ts`

### 3.2. POST `/api/ai/email/compose` (ARCHIVÉ)

**Fichier** : `web/src/app/api/ai/email/compose/route.ts`

**Description** : Ancien endpoint pour composer des emails avec templates génériques

**Status** : Archivé. Utiliser `/compose-ugg` à la place.

**Request** :
```json
{
  "prompt": "Create a welcome email for new users",
  "locale": "en",
  "previous_spec": { ... },  // optional EmailSpec
  "templateId": "arquantix_ugg_v1",  // optional
  "lockStructure": true  // optional, default: true
}
```

**Response** :
```json
{
  "assistant_text": "I've created a professional email...",
  "spec": { ... },  // EmailSpec JSON
  "mjml": "<mjml>...</mjml>",
  "html": "<!DOCTYPE html>...",
  "warnings": [  // optional
    "Backend unavailable, using local fallback..."
  ],
  "templateId": "arquantix_ugg_v1",
  "locked": true
}
```

**Flux** :
1. Essaie de proxy vers FastAPI backend (`BACKEND_URL/api/ai/email/compose`)
2. Si backend inaccessible (404, connection error) → **fallback local** :
   - Importe `composeEmailSpec` depuis `@/lib/ai-email/composeEmail`
   - Appelle OpenAI directement (server-side)
   - Compile MJML via `buildMjml()` + `compileMjml()`
   - Retourne avec warning "Backend unavailable, using local fallback"

**Source** : `web/src/app/api/ai/email/compose/route.ts` (ARCHIVÉ)

### 3.3. GET `/api/ai/email/templates`

**Fichier** : `web/src/app/api/ai/email/templates/route.ts`

**Description** : Liste les templates disponibles (retourne uniquement `arquantix_ugg_v1` par défaut)

**Auth** : Requiert session

**Query Parameters** :
- `show_legacy` (boolean, optional) : Afficher les anciens templates (nécessite `SHOW_LEGACY_TEMPLATES=true` env var)

**Response** :
```json
[
  {
    "id": "arquantix_ugg_v1",
    "name": "Arquantix UGG v1",
    "description": "Single golden template based on UGG-style MJML. AI generates JSON only.",
    "locked": false,
    "source": "hardcoded"
  }
]
```

**Comportement** :
- Par défaut : retourne uniquement le template `arquantix_ugg_v1`
- Si `show_legacy=true` ET `SHOW_LEGACY_TEMPLATES=true` : retourne les anciens templates (archivés)

**Source** : `web/src/app/api/ai/email/templates/route.ts`
```json
[
  {
    "id": "welcome_v1",
    "name": "Welcome Email",
    "description": "Welcome new users with an introduction and key features",
    "locked": true
  },
  ...
]
```

**Comportement** :
- Charge templates hardcodés (4 templates : welcome_v1, newsletter_v1, project_update_v1, investor_update_v1)
- Charge templates DB depuis `EmailTemplateEntity` (status = VALIDATED)
- Merge les deux listes, ajoute `source: "hardcoded" | "db"` et `(DB)` dans le nom
- Retourne toujours au moins les templates hardcodés (fallback si erreur)

**Response** :
```json
[
  {
    "id": "welcome_v1",
    "name": "Welcome Email",
    "description": "Welcome new users with an introduction and key features",
    "locked": true,
    "source": "hardcoded"
  },
  {
    "id": "base_v1_db",
    "name": "Base Template (DB)",
    "description": "Template de base utilisant les modules header_default, footer_default",
    "locked": true,
    "source": "db"
  },
  ...
]
```

**Source** : `web/src/app/api/ai/email/templates/route.ts`

### 3.3. POST `/api/ai/email/compile`

**Fichier** : `web/src/app/api/ai/email/compile/route.ts`

**Description** : Compile MJML → HTML (server-side)

**Auth** : Requiert session

**Request** :
```json
{
  "mjml": "<mjml>...</mjml>"
}
```

**Response** :
```json
{
  "html": "<!DOCTYPE html>...",
  "error": null  // or error message
}
```

**Flux** : Utilise `compileMjml()` depuis `@/lib/ai-email/compileMjml` (subprocess `npx mjml`)

**Source** : `web/src/app/api/ai/email/compile/route.ts`

### 3.4. POST `/api/ai/voice/transcribe`

**Fichier** : `web/src/app/api/ai/voice/transcribe/route.ts`

**Description** : Transcription audio → texte (OpenAI Whisper)

**Auth** : Requiert session

**Request** : FormData avec `file` (audio/webm, audio/wav, etc.)

**Response** :
```json
{
  "transcript": "Create a welcome email for new users..."
}
```

**Source** : `web/src/app/api/ai/voice/transcribe/route.ts`

### 3.5. POST `/api/admin/emails`

**Fichier** : `web/src/app/api/admin/emails/route.ts`

**Description** : Créer un email DRAFT

**Auth** : Requiert session

**Request** :
```json
{
  "name": "Welcome - March 2024",
  "templateId": "arquantix_ugg_v1",
  "locale": "fr",
  "spec": { ... }  // EmailSpec JSON
}
```

**Response** : Email object (id, name, templateId, locale, status: DRAFT, etc.)

**Source** : `web/src/app/api/admin/emails/route.ts`

### 3.6. GET `/api/admin/emails`

**Fichier** : `web/src/app/api/admin/emails/route.ts`

**Description** : Liste tous les emails

**Auth** : Requiert session

**Response** :
```json
[
  {
    "id": "uuid",
    "name": "Welcome - March 2024",
    "templateId": "arquantix_ugg_v1",
    "locale": "fr",
    "status": "DRAFT",
    "updatedAt": "2024-03-01T10:00:00Z",
    "_count": { "translations": 2 }
  },
  ...
]
```

**Source** : `web/src/app/api/admin/emails/route.ts`

### 3.7. GET/PUT/DELETE `/api/admin/emails/[id]`

**Fichier** : `web/src/app/api/admin/emails/[id]/route.ts`

**Description** : Récupère/met à jour/supprime un email

**Auth** : Requiert session

**PUT Rules** :
- Seulement si `status === 'DRAFT'` (refuse si VALIDATED)

**Source** : `web/src/app/api/admin/emails/[id]/route.ts`

### 3.8. POST `/api/admin/emails/[id]/validate`

**Fichier** : `web/src/app/api/admin/emails/[id]/validate/route.ts`

**Description** : Valide un email (change status de DRAFT → VALIDATED)

**Auth** : Requiert session

**Response** : Email object avec `status: 'VALIDATED'`

**Source** : `web/src/app/api/admin/emails/[id]/validate/route.ts`

### 3.9. POST `/api/admin/translate/email`

**Fichier** : `web/src/app/api/admin/translate/email/route.ts`

**Description** : Auto-traduit un email validé en plusieurs langues

**Auth** : Requiert session

**Request** :
```json
{
  "emailId": "uuid",
  "sourceLocale": "fr",
  "targetLocales": ["en", "it"],
  "mode": "missing"  // or "force"
}
```

**Rules** :
- Seulement si `Email.status === 'VALIDATED'`
- Traduit uniquement le contenu (subject, preheader, props textuelles des blocs)
- **PAS** la structure (blocs, ordre, types)
- Crée/upsert `EmailI18n` avec `translationStatus: MACHINE`
- Log `TranslationLog` entries

**Response** :
```json
{
  "translated": ["en", "it"],
  "skipped": []
}
```

**Source** : `web/src/app/api/admin/translate/email/route.ts`

## 4. State Model

### 4.1. Email Builder State

**Page** : `/admin/ai/email`

**État local** :
- `previousSpec: EmailSpecUGG | null` - Spec précédente pour itération IA
- `selectedTemplateId: string` - Toujours `"arquantix_ugg_v1"`
- `mjml: string` - MJML généré (template rempli)
- `html: string` - HTML compilé
- `isSaving: boolean` - Loading state pour "Save Draft"

**Source** : `web/src/app/admin/ai/email/page.tsx`

### 4.2. Email Detail State

**Page** : `/admin/emails/[id]`

**État local** :
- `email: Email | null` - Email chargé depuis API
- `activeTab: 'preview' | 'translations' | 'meta'` - Onglet actif
- `selectedLocale: string` - Locale sélectionnée pour preview
- `mjml: string` - MJML généré pour preview
- `html: string` - HTML compilé pour preview
- `showTranslateModal: boolean` - Affichage modal traduction
- `isValidating: boolean` - Loading state pour "Validate"

**Source** : `web/src/app/admin/emails/[id]/page.tsx`

### 4.3. ChatStudio State

**Component** : `ChatStudio`

**État local** :
- `messages: Array<{role: 'user' | 'assistant', content: string}>` - Historique messages
- `input: string` - Input texte actuel
- `isLoading: boolean` - Loading state pour génération

**Source** : `web/src/components/ai-email/ChatStudio.tsx`

### 4.4. EmailOutput State

**Component** : `EmailOutput`

**État local** :
- `viewMode: 'desktop' | 'mobile' | 'code'` - Mode de prévisualisation
- `copied: 'html' | 'mjml' | null` - État copie (pour feedback UI)

**Source** : `web/src/components/ai-email/EmailOutput.tsx`

## 5. Frontend → Backend Communication

### 5.1. API Client Functions

**Fichier** : `web/src/components/ai-email/api.ts`

**Fonction `composeEmail`** :
- Détecte automatiquement si `templateId === 'arquantix_ugg_v1'`
- Si UGG : utilise `/api/ai/email/compose-ugg`
- Sinon : utilise `/api/ai/email/compose` (archivé)

**Fonction `listEmailTemplates`** :
- Appelle `/api/ai/email/templates`
- Retourne uniquement `arquantix_ugg_v1` par défaut

**Source** : `web/src/components/ai-email/api.ts`

### 5.2. Fallback Strategy (ARCHIVÉ)

L'ancien système utilisait une stratégie de fallback. Le nouveau système utilise uniquement FastAPI backend :

1. **FastAPI backend** :
   - URL : `BACKEND_URL` ou `NEXT_PUBLIC_BACKEND_URL` ou `http://localhost:8000`
   - Endpoint : `/api/ai/email/compose-ugg`

2. **Si backend inaccessible** (404, connection error) :
   - **Fallback local** : utilise Next.js API routes qui appellent OpenAI directement
   - Templates et verrouillage de structure **désactivés** dans fallback
   - Affiche warning : "Backend unavailable, using local fallback..."

**Source** : `web/src/app/api/ai/email/compose/route.ts` lignes 27-134

### 5.2. Environment Variables (Frontend)

```bash
# Optionnel (pour proxy FastAPI)
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

**Note** : La clé OpenAI n'est **jamais** exposée au frontend. Elle est utilisée uniquement dans Next.js API routes (server-side).

**Source** : `web/src/lib/openai/client.ts` (vérifie `process.env.OPENAI_API_KEY`)

## 6. Save Draft Workflow

**Flux** :
1. L'utilisateur génère un email via AI Copilot ou Manual Edit
2. Clique "Save Draft" dans `/admin/ai/email`
3. Appelle `POST /api/admin/emails` avec :
   - `name`: généré automatiquement ou saisi
   - `templateId`: template sélectionné
   - `locale`: locale actuelle
   - `spec`: EmailSpec actuel (validé via Zod)
4. API crée `Email` avec `status: 'DRAFT'`
5. Redirige vers `/admin/emails/[id]`

**Source** : `web/src/app/admin/ai/email/page.tsx` (handleSaveDraft)

## 7. Validate Email Workflow

**Flux** :
1. L'utilisateur ouvre `/admin/emails/[id]` (email DRAFT)
2. Consulte la prévisualisation (locale source)
3. Clique "Validate" → appelle `POST /api/admin/emails/[id]/validate`
4. API change `status` de `DRAFT` → `VALIDATED`
5. Structure verrouillée définitivement (non modifiable)
6. Onglet "Translations" s'active (auto-translate disponible)

**Source** : `web/src/app/admin/emails/[id]/page.tsx` (handleValidate)

## 8. Preview & iFrame Security

### 8.1. iFrame Sandboxing

**Sécurité** :
- Prévisualisations Desktop/Mobile dans iframes avec `sandbox=""` (sans `allow-scripts`)
- Contenu injecté via `srcDoc` (pas `src` externe)
- Background gris clair + card pour preview

**Code** :
```tsx
<iframe
  srcDoc={html}
  sandbox=""  // No scripts allowed
  className="w-full border-0 rounded-lg bg-gray-100"
  style={{ width: mode === 'desktop' ? '640px' : '375px', height: '600px' }}
/>
```

**Source** : `web/src/components/ai-email/EmailOutput.tsx`

### 8.2. Preview Modes

**Modes** :
- **Code** : `HtmlViewer` pour HTML ou MJML (readonly, boutons Copy)
- **Desktop** : iframe avec width ~640px (centered)
- **Mobile** : iframe avec width ~375px (centered)

**Source** : `web/src/components/ai-email/EmailOutput.tsx`

## 9. Next Steps

Pour approfondir :
- **Architecture Backend** → [ARCHITECTURE_BACKEND.md](./ARCHITECTURE_BACKEND.md)
- **Runbook & Extension** → [RUNBOOK.md](./RUNBOOK.md)

