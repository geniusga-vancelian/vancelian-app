# Email Builder & Emails System - Overview

## 1. What is this feature?

Le système Email Builder est un module intégré au CMS Arquantix qui permet de créer, éditer, valider et traduire des emails marketing professionnels via une interface graphique combinant IA et édition manuelle.

**Fonctionnalités principales** :
- Génération d'emails via prompts en langage naturel (OpenAI)
- **Template unique "golden"** : `arquantix_ugg_v1` (basé sur MJML UGG-style)
- **Schéma strict EmailSpecUGG** : JSON dédié au template UGG (pas de blocs génériques)
- **Module Builder** (V6) : Création de modules réutilisables (Header, Footer, etc.)
- **Template Builder** (V6) : Création de templates DB utilisant des modules (archivés)
- Éditeur manuel content-only (modification de props uniquement)
- Sauvegarde de brouillons en base de données
- Validation humaine (verrouillage de structure)
- Auto-traduction multi-langue (post-validation uniquement)
- Prévisualisation Desktop/Mobile/Code avec badges module vs AI
- Export MJML/HTML

## 2. Key Principles & Constraints

### 🔒 Constraints critiques

1. **OpenAI ne génère JAMAIS de HTML/MJML**
   - OpenAI retourne uniquement du JSON EmailSpecUGG strict (pour template UGG)
   - Le backend compose le MJML via template MJML hardcodé (`arquantix_ugg_v1.mjml`)
   - Source de vérité : `api/services/ai_email/schemas_ugg.py` (EmailSpecUGG)
   - Ancien système avec EmailSpec générique : archivé (templates en DRAFT)

2. **Template unique "golden" (arquantix_ugg_v1)**
   - Un seul template actif : `arquantix_ugg_v1` basé sur MJML UGG-style
   - Structure fixe définie dans le template MJML (pas de blocs génériques)
   - Schéma JSON strict `EmailSpecUGG` avec champs dédiés (offer_line, headline_lines, carousel, etc.)
   - Anciens templates (welcome_v1, newsletter_v1, etc.) : archivés (status DRAFT)
   - Source : `api/services/ai_email/templates_mjml/arquantix_ugg_v1.mjml`

3. **Schéma EmailSpecUGG strict (template UGG uniquement)**
   - Pas de blocs génériques : structure fixe définie dans le template MJML
   - Champs dédiés : `offer_line`, `headline_lines`, `carousel`, `ctas`, `promo_block`, `rewards_block`, `footer`
   - Validation Pydantic avec `extra="forbid"`
   - URLs : `https://` uniquement ou placeholders `{{...}}`
   - Source : `api/services/ai_email/schemas_ugg.py`
   - **Note** : L'ancien système avec registry rigide (11 types de blocs) est archivé

4. **MJML compilation backend uniquement**
   - Frontend ne compile JAMAIS MJML directement
   - Utilise `npx mjml` via subprocess ou API route Next.js
   - Source : `web/src/lib/ai-email/compileMjml.ts`, `api/services/ai_email/render.py`

5. **Clé OpenAI jamais exposée au frontend**
   - Tous les appels OpenAI passent par Next.js API routes (server-side)
   - Le backend FastAPI peut aussi servir de proxy optionnel
   - Source : `web/src/app/api/ai/email/compose/route.ts`

6. **Sécurité iframe**
   - Prévisualisations Desktop/Mobile dans iframes sandboxées
   - Pas de `allow-scripts` pour éviter XSS
   - Source : `web/src/components/ai-email/EmailOutput.tsx`

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ Email Builder    │  │ Emails List      │  │ Email Detail │ │
│  │ /admin/ai/email  │  │ /admin/emails    │  │ /admin/emails│ │
│  │                  │  │                  │  │ /[id]        │ │
│  │ • ChatStudio     │  │ • Table view     │  │ • Preview    │ │
│  │ • BlockEditor    │  │ • Create button  │  │ • Translate  │ │
│  │ • EmailOutput    │  │                  │  │ • Validate   │ │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘ │
│           │                     │                     │         │
│           └─────────────────────┼─────────────────────┘         │
│                                 │                               │
│                    ┌────────────▼────────────┐                  │
│                    │  Next.js API Routes     │                  │
│                    │  /api/ai/email/compose  │                  │
│                    │  /api/admin/emails      │                  │
│                    │  /api/admin/translate/  │                  │
│                    └────────────┬────────────┘                  │
└─────────────────────────────────┼───────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ FastAPI Backend │    │   OpenAI API    │    │  PostgreSQL DB  │
│ (optionnel)     │    │                 │    │                 │
│                 │    │ • GPT-4o-mini   │    │ • Email         │
│ • Templates     │    │ • Whisper       │    │ • EmailI18n     │
│ • Lock logic    │    │                 │    │ • TranslationLog│
│ • MJML render   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 4. User-Facing Workflow

### 4.1. Builder → Draft

**Workflow** :
1. L'utilisateur ouvre `/admin/ai/email`
2. Le template `arquantix_ugg_v1` est sélectionné par défaut (seul template disponible)
3. Envoie un prompt : "Create a welcome email for new users"
4. L'IA génère un EmailSpecUGG JSON (via OpenAI, endpoint `/api/ai/email/compose-ugg`)
5. Le backend remplit le template MJML `arquantix_ugg_v1.mjml` avec les données JSON
6. Le backend compile MJML → HTML
7. La prévisualisation s'affiche (Desktop/Mobile/Code)
8. L'utilisateur peut :
   - Itérer via prompts ("Make the headline shorter")
   - Cliquer "Save Draft" → redirection vers `/admin/emails/[id]`

**Fichiers clés** :
- `web/src/app/admin/ai/email/page.tsx` - Page principale
- `web/src/components/ai-email/ChatStudio.tsx` - Interface chat (utilise template UGG)
- `web/src/app/api/ai/email/compose-ugg/route.ts` - API composition UGG
- `api/services/ai_email/agent_ugg.py` - Agent OpenAI pour EmailSpecUGG
- `api/services/ai_email/templates_mjml/render_ugg.py` - Renderer MJML

### 4.2. Draft → Validated

**Workflow** :
1. L'utilisateur ouvre `/admin/emails/[id]`
2. Consulte la prévisualisation (locale source)
3. Clique "Validate" → status passe de `DRAFT` à `VALIDATED`
4. La structure est définitivement verrouillée (non modifiable)

**Fichiers clés** :
- `web/src/app/admin/emails/[id]/page.tsx` - Page détail
- `web/src/app/api/admin/emails/[id]/validate/route.ts` - Endpoint validation

### 4.3. Validated → Translated

**Workflow** :
1. Une fois validé, l'onglet "Translations" s'active
2. L'utilisateur clique "Auto-translate"
3. Sélectionne les langues cibles (ex: EN, IT)
4. L'API traduit :
   - `subject`, `preheader`
   - Props textuelles de chaque bloc (contenu uniquement)
   - **PAS** la structure (blocs, ordre, types)
5. Les traductions sont créées en `EmailI18n` avec `translationStatus: MACHINE`
6. L'utilisateur peut prévisualiser chaque locale
7. Approuve manuellement (`translationStatus: APPROVED`)

**Fichiers clés** :
- `web/src/app/api/admin/translate/email/route.ts` - Endpoint traduction
- `web/src/lib/translate/translateText.ts` - Utilitaire traduction

### 4.4. Preview & Export

**Workflow** :
1. Sur `/admin/emails/[id]`, sélection de la locale dans le dropdown
2. Prévisualisation Desktop/Mobile/Code
3. Copie HTML/MJML via boutons "Copy HTML" / "Copy MJML"

**Fichiers clés** :
- `web/src/components/ai-email/EmailOutput.tsx` - Prévisualisation
- `web/src/components/ai-email/HtmlViewer.tsx` - Vue code

## 5. Data Model (Prisma)

```prisma
model Email {
  id            String      @id @default(uuid())
  name          String      // "Welcome - March 2024"
  templateId    String      // "arquantix_ugg_v1" (seul template actif)
  theme         String      @default("arquantix_v1")
  locale        String      @default("fr")
  spec          Json        // EmailSpecUGG JSON (structure fixe définie par template MJML)
  status        EmailStatus @default(DRAFT)
  createdAt     DateTime    @default(now())
  updatedAt     DateTime    @updatedAt
  translations  EmailI18n[]
}

model EmailI18n {
  id                String            @id @default(uuid())
  emailId           String
  locale            String
  spec              Json              // EmailSpec JSON (contenu traduit uniquement)
  translationStatus TranslationStatus @default(MACHINE)
  createdAt         DateTime          @default(now())
  updatedAt         DateTime          @updatedAt
  email             Email             @relation(...)
  @@unique([emailId, locale])
}

enum EmailStatus {
  DRAFT
  VALIDATED
}

model EmailModule {
  id            String          @id @default(uuid())
  slug          String          @unique
  name          String
  description   String?
  moduleType    EmailModuleType // HEADER, FOOTER, LEGAL, SIGNATURE, SOCIAL, DISCLAIMER, CUSTOM
  theme         String          @default("arquantix_v1")
  status        EmailStatus     @default(DRAFT)
  spec          Json            // EmailSpec JSON
  translations  EmailModuleI18n[]
}

model EmailModuleI18n {
  id                String            @id @default(uuid())
  moduleId          String
  locale            String
  spec              Json              // EmailSpec JSON (contenu traduit uniquement)
  translationStatus TranslationStatus @default(MACHINE)
  module            EmailModule       @relation(...)
  @@unique([moduleId, locale])
}

model EmailTemplateEntity {
  id                 String          @id @default(uuid())
  slug               String          @unique
  name               String
  description        String?
  theme              String          @default("arquantix_v1")
  status             EmailStatus     @default(DRAFT)
  heroPolicy         EmailHeroPolicy // REQUIRED, OPTIONAL
  headerModuleId     String          // FK -> EmailModule (HEADER)
  footerModuleId     String          // FK -> EmailModule (FOOTER)
  bodyStarterModuleId String?        // FK -> EmailModule (optionnel, initialise body)
  fixedModuleIds     Json?           // Array de module IDs (optionnel)
  bodyTemplate       Json            // Structure BODY autorisée
  lockPolicy         Json            // Politique de verrouillage
  headerModule       EmailModule @relation(...)
  footerModule       EmailModule @relation(...)
}
```

**Invariants** :
- `Email.status === DRAFT` → modifiable (contenu uniquement, structure fixe)
- `Email.status === VALIDATED` → traduisible uniquement
- `EmailI18n.translationStatus === MACHINE` → nécessite approbation humaine
- `EmailI18n.spec` contient uniquement le contenu traduit (pas la structure)
- `Email.templateId === "arquantix_ugg_v1"` → seul template actif
- `Email.spec` doit respecter le schéma EmailSpecUGG strict
- `EmailModule.status === VALIDATED` → utilisable dans les templates (archivé)
- `EmailTemplateEntity.status === DRAFT` → templates archivés (non utilisables)

**Source** : `web/prisma/schema.prisma`

## 6. System Invariants

### EmailSpecUGG invariants (template arquantix_ugg_v1)

1. **Champs requis** :
   - `subject` (string, 1-120 chars)
   - `preheader` (string, 1-100 chars)
   - `offer_line` (string, 1-100 chars, uppercase)
   - `headline_lines` (array, 2-4 items, uppercase)
   - `intro_text` (string, 1-1000 chars)
   - `hero_image_url` (string, https:// ou {{placeholder}})
   - `hero_image_alt` (string, 1-200 chars)
   - `carousel` (object avec 1-6 items)
   - `ctas` (object avec primary requis, secondary optionnel)
   - `footer` (object avec company_name, unsubscribe_url_placeholder, etc.)

2. **Champs optionnels** :
   - `promo_block` (object avec image_url, title_lines, body, button)
   - `rewards_block` (object avec image_url, heading, body, button)
   - `footer.social_links` (object avec facebook, instagram, youtube, twitter, linkedin)

3. **Validation** :
   - URLs : `https://` uniquement ou placeholders `{{...}}`
   - Longueurs : `subject` max 120, `preheader` max 100, `headline_lines` 2-4 items, `carousel.items` 1-6 items
   - Locale : code ISO 2 lettres (`fr`, `en`, `it`)
   - Structure fixe : définie dans le template MJML, pas modifiable

**Source** : `api/services/ai_email/schemas_ugg.py`, `api/services/ai_email/templates_mjml/arquantix_ugg_v1.mjml`

**Note** : L'ancien système avec EmailSpec générique et registry rigide (11 types de blocs) est archivé.

## 7. Security & Safety

### Sécurité

1. **Clé OpenAI** :
   - Jamais exposée au client
   - Stockée dans variables d'environnement serveur
   - Utilisée uniquement dans Next.js API routes ou FastAPI backend

2. **HTML Sanitization** :
   - Rejet des `<script>` tags dans HTML compilé
   - Validation backend avant compilation MJML
   - Source : `api/services/ai_email/render.py`

3. **Iframe Sandboxing** :
   - Prévisualisations dans iframes avec `sandbox="allow-same-origin"` (pour affichage HTML)
   - Contenu injecté via `srcDoc` (pas `src` externe)
   - Source : `web/src/components/ai-email/EmailOutput.tsx`

4. **Validation stricte** :
   - Pydantic schemas avec `extra="forbid"`
   - Zod schemas côté frontend
   - Validation registry avant rendu MJML

### Rate Limiting

- Pas de rate limiting côté frontend (implémenter si nécessaire)
- Retry logic via `requestWithRetry` pour OpenAI
- Source : `web/src/lib/openai/requestWithRetry.ts`

## 8. File Structure Reference

### Backend (FastAPI)
```
api/services/ai_email/
├── __init__.py
├── schemas.py              # Pydantic EmailSpec models
├── registry.py             # Block registry + slot metadata
├── lock.py                 # Structure locking logic
├── agent.py                # OpenAI composition logic
├── render.py               # MJML build + compile
├── routes.py               # FastAPI endpoints
├── system_prompt.py        # OpenAI system prompt
├── theme/
│   ├── __init__.py
│   └── arquantix_v1.py     # Brand tokens
├── templates/
│   ├── __init__.py
│   └── arquantix_base.py   # Base MJML template
├── templates_presets/
│   ├── __init__.py
│   ├── types.py            # EmailTemplate dataclass
│   └── arquantix_v1.py     # 4 rigid templates
├── assemble.py             # Assemble template + modules + body spec (V6)
├── modules_resolver.py     # Resolve modules from DB (V6)
└── blocks/
    ├── __init__.py
    ├── hero.py
    ├── text.py
    ├── feature_cards.py
    ├── cta.py
    ├── footer.py
    ├── section_title.py
    ├── bullets.py
    ├── image.py
    ├── divider.py
    ├── spacer.py
    └── social_icons.py     # SOCIAL_ICONS block renderer (V6)
```

### Frontend (Next.js)
```
web/src/
├── app/
│   ├── admin/
│   │   ├── ai/email/page.tsx           # Email Builder page
│   │   ├── emails/
│   │   │   ├── page.tsx                 # Emails list
│   │   │   └── [id]/page.tsx            # Email detail
│   │   ├── email-modules/               # Module Builder (V6)
│   │   │   ├── page.tsx                 # Modules list
│   │   │   └── [id]/page.tsx            # Module detail
│   │   └── email-templates/             # Template Builder (V6)
│   │       ├── page.tsx                 # Templates list
│   │       └── [id]/page.tsx            # Template detail
│   └── api/
│       ├── ai/email/
│       │   ├── compose/route.ts         # Compose email (proxy or local)
│       │   ├── templates/route.ts       # List templates
│       │   ├── compile/route.ts         # Compile MJML → HTML
│       │   └── voice/transcribe/route.ts # Audio transcription
│       └── admin/
│           ├── emails/
│           │   ├── route.ts             # POST (create), GET (list)
│           │   └── [id]/
│           │       ├── route.ts         # GET, PUT, DELETE
│           │       └── validate/route.ts # POST (validate)
│           ├── email-modules/           # Module Builder API (V6)
│           │   ├── route.ts             # POST (create), GET (list)
│           │   └── [id]/
│           │       ├── route.ts         # GET, PUT, DELETE
│           │       └── validate/route.ts # POST (validate)
│           ├── email-templates/         # Template Builder API (V6)
│           │   ├── route.ts             # POST (create), GET (list)
│           │   └── [id]/
│           │       ├── route.ts         # GET, PUT, DELETE
│           │       └── validate/route.ts # POST (validate)
│           └── translate/
│               ├── email/route.ts       # POST (auto-translate Email)
│               ├── email-module/route.ts # POST (auto-translate EmailModule)
│               └── approve/route.ts     # POST (approve translation)
├── components/ai-email/
│   ├── ChatStudio.tsx                   # AI chat interface
│   ├── VoiceRecorder.tsx                # Audio recording
│   ├── EmailOutput.tsx                  # Preview (Desktop/Mobile/Code)
│   ├── HtmlViewer.tsx                   # Code viewer
│   ├── BlockEditor/
│   │   ├── BlockEditor.tsx              # Main manual editor
│   │   ├── BlockCard.tsx                # Individual block card
│   │   └── editors/
│   │       ├── HeroEditor.tsx
│   │       ├── TextEditor.tsx
│   │       ├── ImageEditor.tsx
│   │       └── CtaEditor.tsx
│   ├── types.ts                         # TypeScript types
│   ├── schema.ts                        # Zod schemas
│   ├── api.ts                           # API client functions
│   └── registry-helpers.ts              # Frontend registry utils
└── lib/ai-email/
    ├── composeEmail.ts                  # Local OpenAI composition (fallback)
    ├── buildMjml.ts                     # MJML builder (frontend fallback)
    └── compileMjml.ts                   # MJML compiler (uses npx mjml)
```

## 9. Next Steps

Pour approfondir :
- **Architecture Backend** → [ARCHITECTURE_BACKEND.md](./ARCHITECTURE_BACKEND.md)
- **Architecture Frontend** → [ARCHITECTURE_FRONTEND.md](./ARCHITECTURE_FRONTEND.md)
- **Runbook & Extension** → [RUNBOOK.md](./RUNBOOK.md)

