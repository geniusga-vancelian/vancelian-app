# Email Builder - Backend Architecture

## 1. FastAPI Module Structure

Le backend FastAPI du système Email Builder est organisé dans `api/services/ai_email/`.

```
api/services/ai_email/
├── __init__.py                     # Module exports
├── schemas.py                      # Pydantic EmailSpec models
├── registry.py                     # Rigid block registry + slot metadata
├── lock.py                         # Structure locking logic
├── agent.py                        # OpenAI composition logic
├── render.py                       # MJML build + compile
├── routes.py                       # FastAPI endpoints
├── system_prompt.py                # OpenAI system prompt
├── theme/
│   ├── __init__.py
│   └── arquantix_v1.py             # Brand tokens (colors, spacing, typography)
├── templates/
│   ├── __init__.py
│   └── arquantix_base.py           # Base MJML template (header + footer)
├── templates_presets/
│   ├── __init__.py
│   ├── types.py                    # EmailTemplate dataclass
│   └── arquantix_v1.py             # 4 rigid templates (welcome_v1, newsletter_v1, etc.)
└── blocks/
    ├── __init__.py
    ├── hero.py                     # HERO block renderer
    ├── text.py                     # TEXT block renderer
    ├── section_title.py            # SECTION_TITLE block renderer
    ├── bullets.py                  # BULLETS block renderer
    ├── feature_cards.py            # FEATURE_CARDS block renderer
    ├── image.py                    # IMAGE block renderer
    ├── cta.py                      # CTA block renderer
    ├── divider.py                  # DIVIDER block renderer
    ├── spacer.py                   # SPACER block renderer
    ├── social_icons.py             # SOCIAL_ICONS block renderer
    └── footer.py                   # FOOTER block renderer
```

**Source** : `api/services/ai_email/`

### 1.1. Integration dans FastAPI

Le router FastAPI est intégré dans `api/main.py` :

```python
from services.ai_email.routes import router as ai_email_router
app.include_router(ai_email_router)
```

Le router utilise le préfixe `/api/ai` et le tag `ai-email`.

**Source** : `api/main.py` lignes 630-631

## 2. Endpoints FastAPI

### 2.1. GET `/api/ai/email/templates`

**Description** : Liste les templates disponibles (retourne uniquement `arquantix_ugg_v1` par défaut)

**Auth** : Requiert authentification (`Depends(get_current_user)`)

**Query Parameters** :
- `show_legacy` (boolean, optional) : Afficher les anciens templates (nécessite `SHOW_LEGACY_TEMPLATES=true` env var)

**Response** :
```json
[
  {
    "id": "arquantix_ugg_v1",
    "name": "Arquantix UGG v1",
    "description": "Single golden template based on UGG-style MJML. AI generates JSON only.",
    "locked": false
  }
]
```

**Source** : `api/services/ai_email/routes.py` lignes 32-49

### 2.2. POST `/api/ai/email/compose-ugg`

**Description** : Compose un email avec le template `arquantix_ugg_v1` (template unique "golden")

**Auth** : Requiert authentification

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
  "assistant_text": "I've created a professional email with the requested content.",
  "templateId": "arquantix_ugg_v1",
  "spec": { ... },  // EmailSpecUGG JSON
  "mjml": "<mjml>...</mjml>",  // MJML string (template rempli)
  "html": "<!DOCTYPE html>...",  // Compiled HTML
  "warnings": [  // optional
    "MJML compilation warning: ..."
  ]
}
```

**Comportement** :
1. L'IA génère un `EmailSpecUGG` JSON strict (via `agent_ugg.py`)
2. Le renderer (`render_ugg.py`) remplace les placeholders dans `arquantix_ugg_v1.mjml`
3. Le MJML est compilé en HTML via `compile_mjml()`
4. Retourne le spec, MJML et HTML

**Source** : `api/services/ai_email/routes.py` lignes 364-410

### 2.3. POST `/api/ai/email/compose` (ARCHIVÉ)

**Description** : Ancien endpoint pour composer des emails avec templates génériques

**Status** : Archivé (templates en DRAFT). Utiliser `/compose-ugg` à la place.

**Source** : `api/services/ai_email/routes.py` lignes 52-363

### 2.4. POST `/api/ai/voice/transcribe`

**Description** : Transcription audio vers texte (OpenAI Whisper)

**Auth** : Requiert authentification

**Request** : FormData avec fichier audio (`file`)

**Formats acceptés** : `audio/webm`, `audio/wav`, `audio/mpeg`, `audio/mp3`, `audio/x-m4a`

**Taille max** : 15 MB

**Response** :
```json
{
  "transcript": "Create a welcome email for new users..."
}
```

**Source** : `api/services/ai_email/routes.py` lignes 112-183

**Note** : Ce endpoint est conservé pour compatibilité. Le frontend utilise maintenant principalement les Next.js API routes qui appellent OpenAI directement.

## 3. EmailSpec Schema (Pydantic)

### 3.1. Structure générale

```python
class EmailSpec(BaseModel):
    subject: str = Field(..., min_length=1, max_length=120)
    preheader: Optional[str] = Field(None, max_length=100)
    locale: str = Field(default="en", pattern=r"^[a-z]{2}$")
    theme: Literal["arquantix_v1"] = "arquantix_v1"
    blocks: List[Block] = Field(..., min_length=2, max_length=10)
```

**Validation** :
- `subject` : 1-120 chars, trimmed
- `preheader` : max 100 chars, trimmed, optional
- `locale` : 2 lettres (ex: `fr`, `en`, `it`)
- `theme` : toujours `"arquantix_v1"` (rigide)
- `blocks` : 2-10 blocs, dernier DOIT être `footer`

**Source** : `api/services/ai_email/schemas.py` lignes 153-178

### 3.2. Block Types

11 types de blocs autorisés avec variants stricts :

1. **HERO** (`hero`)
   - Variants : `image_top`, `text_only`
   - Props : `title` (max 120), `subtitle` (max 200), `image_url` (https), `cta_label` (max 50), `cta_url` (https)
   - Max occurrences : 1

2. **SECTION_TITLE** (`section_title`)
   - Variant : `centered`
   - Props : `title` (max 120), `subtitle` (max 200)
   - Max occurrences : 3

3. **TEXT** (`text`)
   - Variant : `body`
   - Props : `heading` (max 120), `body` (max 1500)
   - Max occurrences : 5

4. **BULLETS** (`bullets`)
   - Variant : `default`
   - Props : `heading` (max 120), `items` (array, max 8 items)
   - Max occurrences : 2

5. **FEATURE_CARDS** (`feature_cards`)
   - Variant : `3up`
   - Props : `heading` (max 120), `items` (array, max 3 items)
   - Max occurrences : 2

6. **IMAGE** (`image`) - **optional slot**
   - Variant : `contained`
   - Props : `image_url` (https), `alt_text` (max 200), `caption` (max 200)
   - Max occurrences : 3

7. **CTA** (`cta`)
   - Variant : `primary`
   - Props : `label` (max 50), `url` (https), `hint` (max 150)
   - Max occurrences : 3

8. **DIVIDER** (`divider`) - **optional slot**
   - Variant : `default`
   - Props : none
   - Max occurrences : 2

9. **SPACER** (`spacer`) - **optional slot**
   - Variants : `md`, `lg`
   - Props : none
   - Max occurrences : 3

10. **FOOTER** (`footer`) - **required last**
    - Variant : `default`
    - Props : `company_name` (max 100), `address` (max 300), `unsubscribe_url_placeholder` (doit être `{{unsubscribe_url}}`)
    - Max occurrences : 1

**Validation URLs** :
- Toutes les URLs doivent être `https://` ou placeholders `{{...}}`
- Validation via Pydantic validators

**Source** : `api/services/ai_email/schemas.py` (ARCHIVÉ)

### 4.2. Rigid Registry - ARCHIVÉ

Le registry rigide définit les types/variants autorisés et les métadonnées de slots.

### 4.1. Block Registry

```python
BLOCK_REGISTRY: Dict[str, List[str]] = {
    "HERO": ["image_top", "text_only"],
    "SECTION_TITLE": ["centered"],
    "TEXT": ["body"],
    "BULLETS": ["default"],
    "FEATURE_CARDS": ["3up"],
    "IMAGE": ["contained"],
    "CTA": ["primary"],
    "DIVIDER": ["default"],
    "SPACER": ["md", "lg"],
    "SOCIAL_ICONS": ["default"],
    "FOOTER": ["default"],
}
```

**Source** : `api/services/ai_email/registry.py` lignes 12-23

### 4.2. Slot Metadata

Chaque bloc a des métadonnées de slot (`core` vs `optional`) :

```python
@dataclass
class BlockDefinition:
    type: str
    variant: str
    slot: Literal["core", "optional"] = "core"
    max_occurrences: Optional[int] = None
    editable_props: List[str] = None
```

**Blocs core** (intouchables) :
- `HERO`, `SECTION_TITLE`, `TEXT`, `BULLETS`, `FEATURE_CARDS`, `CTA`, `SOCIAL_ICONS`, `FOOTER`

**Blocs optional** (ajoutables/supprimables) :
- `IMAGE` (max 3)
- `DIVIDER` (max 2)
- `SPACER` (max 3, variants `md`/`lg`)

**Note** : `SOCIAL_ICONS` est un bloc core mais uniquement autorisé dans les modules de type `FOOTER`.

**Source** : `api/services/ai_email/registry.py` lignes 57-152

### 4.3. Registry Validation

La fonction `validate_spec_with_registry(spec: EmailSpec)` vérifie :
- Theme est `arquantix_v1`
- 2-10 blocs total
- Types/variants autorisés uniquement
- Max occurrences respectés
- Footer est dernier
- Footer contient `{{unsubscribe_url}}`

**Source** : `api/services/ai_email/registry.py` lignes 204-267 (ARCHIVÉ)

### 4.3. Structure Locking - ARCHIVÉ

La logique de verrouillage de structure est dans `api/services/ai_email/lock.py`.

### 5.1. `enforce_locked_structure`

```python
def enforce_locked_structure(
    base: EmailSpec,
    proposed: EmailSpec,
) -> Tuple[EmailSpec, List[str]]:
    """
    Enforce locked structure from base spec onto proposed spec
    
    Rules:
    - Core blocks: structure (type+variant, order, count) must match base
    - Optional blocks: can be added/removed if slot="optional" and max_occurrences respected
    - Copy compatible props from proposed to base blocks
    - If props missing, keep base props
    - Always revalidate via registry
    
    Returns:
        (final_spec, warnings)
    """
```

**Règles** :
1. Blocs core : ordre, type, variant DOIVENT correspondre à `base`
2. Blocs optionnels : peuvent être ajoutés/supprimés si `slot="optional"` et `max_occurrences` respecté
3. Props : seules les props éditable (`editable_props`) sont copiées depuis `proposed`
4. Props manquantes : conservent les valeurs de `base`
5. Validation : révalidation via registry après merge

**Warnings retournés** :
- `"Ignored extra IMAGE block (max=1)"`
- `"Cannot remove core block CTA"`
- `"Reordered blocks reverted to template order"`

**Source** : `api/services/ai_email/lock.py` lignes 24-162 (ARCHIVÉ)

### 4.4. OpenAI Composition Logic - ARCHIVÉ

La logique de composition OpenAI est dans `api/services/ai_email/agent.py`.

### 6.1. `compose_email_spec`

```python
def compose_email_spec(
    prompt: str,
    previous_spec: Optional[EmailSpec] = None,
    locale: str = "en",
    template_id: Optional[str] = None,
    lock_structure: bool = True,
) -> Tuple[str, EmailSpec, List[str]]:
    """
    Compose EmailSpec from user prompt using OpenAI
    
    Returns:
        (assistant_text, EmailSpec, warnings)
    """
```

**Flux** :
1. Détermine `base_spec` :
   - Si `previous_spec` existe → utilise `previous_spec`
   - Sinon, si `template_id` fourni → charge template
   - Sinon → utilise template par défaut (`welcome_v1`)

2. Construit le prompt utilisateur :
   - Si `lock_structure=True` → `get_locked_structure_prompt()` (met en avant la structure verrouillée)
   - Sinon → `get_user_prompt()` (prompt standard)

3. Appelle OpenAI :
   - Model : `OPENAI_MODEL` (env var, défaut `gpt-4o-mini`)
   - API Key : `OPENAI_API_KEY` (env var)
   - Format : `response_format: { type: "json_object" }`
   - Temperature : `0.3`

4. Parse la réponse JSON :
   - Parse JSON depuis `response.choices[0].message.content`
   - Nettoie markdown code blocks si présents

5. Valide via registry :
   - Appelle `validate_spec_with_registry(spec)`
   - Si erreur → retry avec feedback d'erreur
   - Si retry échoue → fallback vers `base_spec`

6. Applique structure lock si activé :
   - Appelle `enforce_locked_structure(base_spec, spec)`
   - Retourne `(final_spec, warnings)`

**Source** : `api/services/ai_email/agent.py` lignes 23-140

### 6.2. System Prompt

Le system prompt est défini dans `api/services/ai_email/system_prompt.py`.

**Règles critiques** :
- Retourne UNIQUEMENT du JSON EmailSpec (pas de markdown, pas d'explications)
- Utilise UNIQUEMENT les types/variants du registry rigide
- Maximum 10 blocs, 1 hero, footer dernier avec `{{unsubscribe_url}}`
- Pas de HTML, MJML, ou CSS dans la réponse

**Source** : `api/services/ai_email/system_prompt.py` lignes 10-154

### 6.3. Environment Variables

```bash
OPENAI_API_KEY=sk-...          # Required
OPENAI_MODEL=gpt-4o-mini       # Optional, default: gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
```

**Source** : `api/services/ai_email/agent.py` lignes 17-20

## 7. MJML Rendering Pipeline

Le pipeline de rendu MJML est dans `api/services/ai_email/render.py`.

### 7.1. `build_mjml`

```python
def build_mjml(spec: EmailSpec) -> str:
    """
    Build complete MJML document from EmailSpec
    
    Steps:
    1. Validate against rigid registry
    2. Get theme (arquantix_v1)
    3. Render all blocks → body_sections_mjml
    4. Build complete MJML with branded template
    5. Return MJML string
    """
```

**Flux** :
1. Validation : `validate_spec_with_registry(spec)`
2. Theme : `get_theme(spec.theme)` → tokens (colors, spacing, typography)
3. Rendu blocs : pour chaque bloc, appelle le renderer approprié (ex: `hero.render_hero()`, `text.render_text()`)
4. Template base : `render_base_mjml(subject, preheader, body_sections_mjml, theme)`
5. Retour : MJML complet (XML)

**Source** : `api/services/ai_email/render.py` lignes 20-46

### 7.2. `compile_mjml`

```python
def compile_mjml(mjml: str) -> Tuple[str, str]:
    """
    Compile MJML to HTML using npx mjml
    
    Returns:
        (html, error_message)
    """
```

**Flux** :
1. Sécurité : rejette MJML contenant `<script` ou `javascript:`
2. Fichier temporaire : écrit MJML dans fichier temp
3. Subprocess : exécute `npx --yes mjml -s <temp_file>` avec timeout 8s
4. Collecte sortie : `stdout` = HTML compilé, `stderr` = erreurs
5. Validation HTML : rejette HTML contenant `<script` ou `javascript:`
6. Nettoyage : supprime fichier temp
7. Retour : `(html, error)` (si erreur, HTML fallback avec message)

**Prérequis** :
- Node.js installé
- `npx` disponible
- MJML installé automatiquement via `npx --yes`

**Source** : `api/services/ai_email/render.py` lignes 77-147

### 7.3. Block Renderers

Chaque bloc a un renderer dans `api/services/ai_email/blocks/`.

**Pattern** :
```python
def render_hero(block: HeroBlock, theme_name: str = "arquantix_v1") -> str:
    """Render HERO block to MJML using theme"""
    theme = get_theme(theme_name)
    # ... MJML generation using theme tokens ...
    return mjml_string
```

**Renderers** :
- `hero.render_hero()` - HERO block
- `section_title.render_section_title()` - SECTION_TITLE
- `text.render_text()` - TEXT
- `bullets.render_bullets()` - BULLETS
- `feature_cards.render_feature_cards()` - FEATURE_CARDS
- `image.render_image()` - IMAGE
- `cta.render_cta()` - CTA
- `divider.render_divider()` - DIVIDER
- `spacer.render_spacer()` - SPACER
- `footer.render_footer()` - FOOTER

**Source** : `api/services/ai_email/blocks/*.py`

### 7.4. Base Template

Le template de base est dans `api/services/ai_email/templates/arquantix_base.py`.

**Fonction** :
```python
def render_base_mjml(
    *,
    subject: str,
    preheader: str = None,
    body_sections_mjml: str,
    theme: Dict[str, Any]
) -> str:
    """
    Render complete MJML document with Arquantix branding
    
    Includes:
    - <mj-head> with title, preview, attributes, styles
    - <mj-body> with header (branded), body sections, footer (branded)
    """
```

**Structure MJML** :
1. `<mj-head>` :
   - `<mj-title>` : subject
   - `<mj-preview>` : preheader
   - `<mj-attributes>` : font-family, button styles, spacing globaux
   - `<mj-style>` : classes CSS custom (`.card`, `.muted`, `.text-secondary`)

2. `<mj-body>` :
   - Header Arquantix (logo ou texte "ARQUANTIX")
   - Body sections (blocs rendus)
   - Footer Arquantix (copyright, legal links)

**Source** : `api/services/ai_email/templates/arquantix_base.py`

### 7.5. Theme Tokens

Les tokens de thème sont dans `api/services/ai_email/theme/arquantix_v1.py`.

**Tokens** :
```python
WIDTH = 600
FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif"
COLORS = {
    "background": "#f8f8f8",
    "surface": "#ffffff",
    "text": "#1a1a1a",
    "textSecondary": "#666666",
    "textMuted": "#999999",
    "border": "#e5e5e5",
    "bronze": "#C6A47C",  # Brand primary
    "bronzeDark": "#A6895F",
}
SPACING = {"xs": 8, "sm": 16, "md": 24, "lg": 40, "xl": 60}
RADIUS = 12
BUTTON = {"padding": "16px 40px", "radius": 12, "fontWeight": "600", "fontSize": "16px"}
```

**Source** : `api/services/ai_email/theme/arquantix_v1.py`

## 8. Email Templates

Les templates rigides sont dans `api/services/ai_email/templates_presets/arquantix_v1.py`.

### 8.1. EmailTemplate Type

```python
@dataclass
class EmailTemplate:
    id: str
    name: str
    description: str
    locale_defaults: Optional[List[str]] = None
    initial_spec: Optional[EmailSpec] = None
    initial_spec_builder: Optional[Callable[[str], EmailSpec]] = None
    locked: bool = True
```

**Source** : `api/services/ai_email/templates_presets/types.py`

### 8.2. Templates disponibles

1. **welcome_v1** - Email de bienvenue
   - Structure : HERO (text_only) + TEXT + FEATURE_CARDS + CTA + FOOTER
   - Slots optionnels : aucun

2. **newsletter_v1** - Newsletter mensuelle
   - Structure : HERO (image_top) + SECTION_TITLE + TEXT + FEATURE_CARDS + CTA + FOOTER
   - Slots optionnels : IMAGE (max 1), DIVIDER (max 2), SPACER

3. **project_update_v1** - Mise à jour projet
   - Structure : HERO (text_only) + SECTION_TITLE + TEXT + BULLETS + CTA + FOOTER
   - Slots optionnels : IMAGE (max 2), DIVIDER (max 1)

4. **investor_update_v1** - Mise à jour investisseurs
   - Structure : HERO (image_top) + SECTION_TITLE + TEXT + FEATURE_CARDS + CTA + FOOTER
   - Slots optionnels : IMAGE (max 1), SPACER

**Source** : `api/services/ai_email/templates_presets/arquantix_v1.py`

## 9. Security & Safety

### 9.1. HTML Sanitization

**Rejet `<script>` tags** :
- Dans MJML avant compilation : `if "<script" in mjml.lower()`
- Dans HTML compilé : `if "<script" in html.lower()`
- Si détecté → HTML fallback avec message d'erreur

**Source** : `api/services/ai_email/render.py` lignes 84-87, 108-110

### 9.2. URL Validation

**Validation Pydantic** :
- URLs doivent être `https://` ou placeholders `{{...}}`
- Validation dans chaque block schema (ex: `HeroBlock.validate_url()`)

**Source** : `api/services/ai_email/schemas.py` (validators)

### 9.3. OpenAI API Key

**Gestion** :
- Clé stockée dans variables d'environnement (`OPENAI_API_KEY`)
- Jamais exposée au frontend
- Utilisée uniquement dans FastAPI backend ou Next.js API routes (server-side)

**Source** : `api/services/ai_email/agent.py` lignes 17-20

## 10. Logging & Debugging

### 10.1. Logs

**Backend FastAPI** :
- Erreurs : `print(f"[AI Email] Error: {str(e)}")`
- Warnings MJML : `print(f"[AI Email] MJML compilation warning: {error}")`

**Où trouver les logs** :
- Console FastAPI (terminal où `uvicorn` tourne)
- Pas de fichier log dédié (utiliser un logger configuré dans FastAPI si nécessaire)

### 10.2. Debugging Tips

**Erreur "Template not found"** :
- Vérifier que le template est enregistré dans `templates_presets/arquantix_v1.py`
- Vérifier que `register_template()` est appelé

**Erreur "Registry validation failed"** :
- Vérifier que tous les blocs sont dans `BLOCK_REGISTRY`
- Vérifier que les variants sont autorisés
- Vérifier que le footer est dernier avec `{{unsubscribe_url}}`

**Erreur "MJML compilation failed"** :
- Vérifier que Node.js est installé
- Vérifier que `npx` est disponible
- Vérifier les logs stderr pour détails MJML

**Erreur "OpenAI API error"** :
- Vérifier que `OPENAI_API_KEY` est configurée
- Vérifier la validité de la clé (pas expirée)
- Vérifier les limites de quota/rate limit

## 11. Email Modules & Templates (V6)

Le système V6 introduit des **modules réutilisables** (Header, Footer, etc.) et des **templates basés sur la DB** qui référencent ces modules.

### 11.1. EmailModule (Module Builder)

**Schéma Prisma** :
```prisma
model EmailModule {
  id          String          @id @default(uuid())
  slug        String          @unique
  name        String
  description String?
  moduleType  EmailModuleType // HEADER, FOOTER, LEGAL, SIGNATURE, SOCIAL, DISCLAIMER, CUSTOM
  theme       String          @default("arquantix_v1")
  status      EmailStatus     @default(DRAFT) // DRAFT, VALIDATED
  spec        Json            // EmailSpec avec blocs (pas de header/footer dans le module lui-même)
  translations EmailModuleI18n[]
}
```

**Types de modules** :
- `HEADER` : En-tête avec SECTION_TITLE, TEXT, DIVIDER, SPACER (pas de CTA)
- `FOOTER` : Pied de page avec SOCIAL_ICONS, TEXT, FOOTER (doit contenir `{{unsubscribe_url}}`)
- `LEGAL`, `DISCLAIMER`, `SIGNATURE`, `SOCIAL` : Modules spécialisés
- `CUSTOM` : Module personnalisé (tous types de blocs autorisés)

**Workflow** :
1. Créer module en DRAFT → éditer spec → Valider (VALIDATED)
2. Une fois VALIDATED, peut être utilisé dans les templates
3. Auto-translate disponible après validation (crée `EmailModuleI18n`)

**Source** : `web/prisma/schema.prisma` lignes 618-637

### 11.2. EmailTemplateEntity (Template Builder)

**Schéma Prisma** :
```prisma
model EmailTemplateEntity {
  id                 String          @id @default(uuid())
  slug               String          @unique
  name               String
  description        String?
  theme              String          @default("arquantix_v1")
  status             EmailStatus     @default(DRAFT) // DRAFT, VALIDATED
  heroPolicy         EmailHeroPolicy // REQUIRED, OPTIONAL
  headerModuleId     String          // FK -> EmailModule (HEADER)
  footerModuleId     String          // FK -> EmailModule (FOOTER)
  bodyStarterModuleId String?        // FK -> EmailModule (optionnel, initialise body spec)
  fixedModuleIds     Json?           // Array de module IDs (optionnel)
  bodyTemplate       Json            // Définit structure BODY autorisée
  lockPolicy         Json            // Politique de verrouillage (core vs optional)
  headerModule       EmailModule @relation(...)
  footerModule       EmailModule @relation(...)
}
```

**Workflow** :
1. Créer template en DRAFT
2. Sélectionner headerModule et footerModule (doivent être VALIDATED)
3. Optionnellement définir `bodyStarterModuleId` (module qui initialise le body)
4. Définir `bodyTemplate` (core blocks + optional slots)
5. Valider → status devient VALIDATED, template utilisable dans AI Studio

**bodyStarterModuleId** :
- Module optionnel qui initialise le body spec lors de la création d'un email
- L'IA peut modifier/supprimer les blocs du body starter
- Différent de `fixedModuleIds` (qui sont toujours inclus, imposés)

**Source** : `web/prisma/schema.prisma` lignes 649-678

### 11.3. Module Assembly (`assemble.py`)

La fonction `assemble_email()` combine un template DB, un body spec généré par l'IA, et les modules localisés :

```python
def assemble_email(
    template_entity: Dict[str, Any],
    body_spec: EmailSpec,
    locale: str,
    modules_resolver: Callable[[str, str], Optional[EmailSpec]],
) -> Tuple[EmailSpec, List[str]]:
```

**Règles d'assemblage** :
1. **HEADER** : Blocs viennent du `headerModuleId` (localisé si disponible)
2. **HERO** : Props viennent du body_spec (IA), structure fixée par template
3. **BODY** : Blocs viennent du body_spec (IA), structure verrouillée par `bodyTemplate`/`lockPolicy`
4. **FIXED MODULES** : Blocs viennent des modules listés dans `fixedModuleIds` (localisés)
5. **FOOTER** : Blocs viennent du `footerModuleId` (localisé si disponible)

**Ordre final** : HEADER → HERO → BODY → FIXED → FOOTER

**Source** : `api/services/ai_email/assemble.py` lignes 10-167

### 11.4. Module Resolver (`modules_resolver.py`)

**Fonctions principales** :

1. **`get_module_spec(db, module_id, locale)`** :
   - Charge `EmailModule` par ID
   - Si locale != default : cherche `EmailModuleI18n` (APPROVED/MACHINE)
   - Fallback vers spec base si traduction absente ou ORIGINAL

2. **`get_template_entity(db, template_id)`** :
   - Charge `EmailTemplateEntity` par slug (template_id)
   - Vérifie que status = VALIDATED

3. **`get_template_modules(db, template_entity, locale)`** :
   - Résout header, footer, et fixed modules pour un template
   - Retourne tuple `(header_spec, footer_spec, fixed_specs[])`

**Source** : `api/services/ai_email/modules_resolver.py`

### 11.5. Compose Flow avec DB Templates

Quand `templateSource: "db"` dans la requête compose :

1. Charge `EmailTemplateEntity` (doit être VALIDATED)
2. Résout modules via `modules_resolver` :
   - Header module (localisé)
   - Footer module (localisé)
   - Fixed modules si présents
3. Génère body spec via OpenAI (HERO props + BODY blocks uniquement)
4. Si `bodyStarterModuleId` défini, utilise son spec comme base pour le body
5. Assemble final spec via `assemble_email()`
6. Valide et retourne EmailSpec complet

**Source** : `api/services/ai_email/routes.py` lignes 73-128

## 12. Next Steps

Pour approfondir :
- **Architecture Frontend** → [ARCHITECTURE_FRONTEND.md](./ARCHITECTURE_FRONTEND.md)
- **Runbook & Extension** → [RUNBOOK.md](./RUNBOOK.md)

