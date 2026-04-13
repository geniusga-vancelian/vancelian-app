# AI Email Builder - Arquantix Brand Pack v1

## Vue d'ensemble

Le module "AI Studio > Email Builder" utilise un système rigide de blocs et un Brand Pack Arquantix v1 pour garantir la cohérence visuelle et la qualité des emails générés.

## Architecture

### 1. Brand Pack (Theme)

**Fichier**: `api/services/ai_email/theme/arquantix_v1.py`

Définit les tokens de design (couleurs, espacements, typographie) pour le brand Arquantix.

**Tokens principaux**:
- **Couleurs**: `background`, `surface`, `text`, `textSecondary`, `textMuted`, `border`, `bronze` (brand), `bronzeDark`
- **Spacing**: `xs` (8px), `sm` (16px), `md` (24px), `lg` (40px), `xl` (60px)
- **Typography**: `FONT_FAMILY` (system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif)
- **Radius**: 12px (bordures arrondies)
- **Button**: padding, radius, fontWeight, fontSize

**Utilisation**:
```python
from ai_email.theme.arquantix_v1 import get_theme

theme = get_theme("arquantix_v1")
colors = theme["colors"]
spacing = theme["spacing"]
```

### 2. Template Base

**Fichier**: `api/services/ai_email/templates/arquantix_base.py`

Template MJML de base avec header et footer brandés Arquantix.

**Fonction**: `render_base_mjml(subject, preheader, body_sections_mjml, theme)`

- Ajoute un header avec logo (ou texte "ARQUANTIX")
- Injecte les sections de body (blocs)
- Ajoute un footer brandé (legal/company info)
- Applique les styles globaux (font-family, button defaults, classes utilitaires)

**Note**: Le footer du template est séparé du bloc FOOTER du spec. Le bloc FOOTER sert au contenu (unsubscribe), le template footer sert au style global.

### 3. Registry Rigide

**Fichier**: `api/services/ai_email/registry.py`

Définit les types de blocs autorisés, leurs variants, et les contraintes.

**Types de blocs autorisés (10)**:

1. **HERO** (variants: `image_top`, `text_only`)
   - Max: 1 par email
   - Props: title, subtitle, image_url, cta_label, cta_url

2. **SECTION_TITLE** (variant: `centered`)
   - Max: 3 par email
   - Props: title, subtitle

3. **TEXT** (variant: `body`)
   - Max: 5 par email
   - Props: heading, body

4. **BULLETS** (variant: `default`)
   - Max: 2 par email
   - Props: heading, items (array)

5. **FEATURE_CARDS** (variant: `3up`)
   - Max: 2 par email
   - Props: heading, items (max 3)

6. **IMAGE** (variant: `contained`)
   - Max: 3 par email
   - Props: image_url, alt_text, caption

7. **CTA** (variant: `primary`)
   - Max: 3 par email
   - Props: label, url, hint

8. **DIVIDER** (variant: `default`)
   - Max: 2 par email
   - Props: none

9. **SPACER** (variants: `md`, `lg`)
   - Max: 3 par email
   - Props: none

10. **FOOTER** (variant: `default`)
    - Max: 1 par email (obligatoire, dernier)
    - Props: company_name, address, unsubscribe_url_placeholder

**Contraintes globales**:
- Maximum 10 blocs total
- Minimum 2 blocs (contenu + footer)
- Footer obligatoire et dernier
- Footer doit contenir `{{unsubscribe_url}}`

**Validation**:
```python
from ai_email.registry import validate_spec_with_registry

try:
    validate_spec_with_registry(spec)
except ValueError as e:
    # Erreur de validation
    print(e)
```

### 4. Schemas Pydantic

**Fichier**: `api/services/ai_email/schemas.py`

Définit les modèles Pydantic stricts pour `EmailSpec` et chaque type de bloc.

**Caractéristiques**:
- Validation stricte (max lengths, patterns)
- `extra="forbid"` sur tous les blocs (pas de champs inconnus)
- Validation des URLs (https uniquement ou placeholders `{{...}}`)
- Trim automatique des strings
- Theme: `Literal["arquantix_v1"]` (rigide)

**Exemple EmailSpec**:
```python
{
  "subject": "Welcome to Arquantix",
  "preheader": "Discover our platform",
  "locale": "en",
  "theme": "arquantix_v1",
  "blocks": [
    {
      "type": "hero",
      "variant": "text_only",
      "title": "Welcome",
      "subtitle": "Thank you for joining"
    },
    {
      "type": "text",
      "variant": "body",
      "body": "Content here..."
    },
    {
      "type": "footer",
      "variant": "default",
      "company_name": "Arquantix",
      "unsubscribe_url_placeholder": "{{unsubscribe_url}}"
    }
  ]
}
```

### 5. Blocs MJML

**Dossier**: `api/services/ai_email/blocks/`

Chaque bloc a un renderer qui génère du MJML brandé.

**Structure**:
```python
def render_block(block: BlockType, theme_name: str = "arquantix_v1") -> str:
    theme = get_theme(theme_name)
    # Génère MJML avec tokens du theme
    return mjml_string
```

**Tous les blocs**:
- Utilisent `escape_xml()` pour sécuriser le contenu
- Appliquent les tokens du theme (couleurs, spacing, radius)
- Respectent la largeur 600px
- Utilisent les classes utilitaires du template

### 6. Pipeline de Rendering

**Fichier**: `api/services/ai_email/render.py`

**Fonction `build_mjml(spec: EmailSpec)`**:
1. Valide le spec contre le registry (`validate_spec_with_registry`)
2. Récupère le theme (`get_theme`)
3. Rend chaque bloc via `_render_block()`
4. Compose le MJML complet via `render_base_mjml()` (template brandé)
5. Retourne le MJML

**Fonction `compile_mjml(mjml: str)`**:
1. Vérifie sécurité (rejette `<script` tags)
2. Compile MJML → HTML via `npx mjml`
3. Vérifie sécurité sur HTML compilé
4. Retourne (html, error_message)

### 7. Agent OpenAI

**Fichier**: `api/services/ai_email/agent.py`

**Fonction `compose_email_spec(prompt, previous_spec, locale)`**:
1. Appelle OpenAI avec `SYSTEM_PROMPT` (registry rigide)
2. Parse la réponse JSON
3. Valide contre le registry
4. Si échec validation → retry avec erreurs
5. Si échec retry → fallback spec conforme registry

**Fallback spec**:
- HERO (text_only) + TEXT + FOOTER
- Conforme au registry
- Minimal mais valide

### 8. System Prompt

**Fichier**: `api/services/ai_email/system_prompt.py`

Le `SYSTEM_PROMPT` liste explicitement:
- Les 10 types de blocs autorisés
- Les variants pour chaque type
- Les contraintes (max blocks, footer last, etc.)
- Les formats de props
- Interdiction stricte de HTML/MJML/CSS dans la réponse

## Comment ajouter un nouveau bloc

### 1. Ajouter au Registry

Dans `registry.py`:
```python
BLOCK_REGISTRY["NEW_BLOCK"] = ["variant1", "variant2"]
MAX_BLOCKS_PER_TYPE["NEW_BLOCK"] = 2
BLOCK_TYPE_NAMES["NEW_BLOCK"] = "New Block"
```

### 2. Créer le Schema Pydantic

Dans `schemas.py`:
```python
class NewBlock(BaseModel):
    type: Literal["new_block"] = "new_block"
    variant: Literal["variant1", "variant2"] = "variant1"
    # props...
    model_config = {"extra": "forbid"}
```

Ajouter à l'Union `Block`.

### 3. Créer le Renderer

Dans `blocks/new_block.py`:
```python
def render_new_block(block: NewBlock, theme_name: str = "arquantix_v1") -> str:
    theme = get_theme(theme_name)
    # Génère MJML brandé
    return mjml_string
```

### 4. Ajouter au Renderer

Dans `render.py`, fonction `_render_block()`:
```python
elif block_type == "new_block":
    return new_block.render_new_block(block, theme_name)
```

### 5. Mettre à jour System Prompt

Dans `system_prompt.py`, ajouter le nouveau bloc à la liste dans `SYSTEM_PROMPT`.

## Comment changer les tokens (couleurs, spacing, etc.)

**Fichier**: `api/services/ai_email/theme/arquantix_v1.py`

Modifier les constantes:
- `COLORS`: changer les couleurs
- `SPACING`: ajuster les espacements
- `RADIUS`: changer le border-radius
- `BUTTON`: modifier les styles de boutons

**Note**: Tous les blocs utilisent ces tokens automatiquement. Pas besoin de modifier chaque bloc individuellement.

## Exemples de EmailSpec valides

### Exemple 1: Email simple

```json
{
  "subject": "Welcome to Arquantix",
  "preheader": "Start your investment journey",
  "locale": "en",
  "theme": "arquantix_v1",
  "blocks": [
    {
      "type": "hero",
      "variant": "text_only",
      "title": "Welcome to Arquantix",
      "subtitle": "Your trusted investment platform"
    },
    {
      "type": "text",
      "variant": "body",
      "body": "Thank you for joining us. We're excited to help you achieve your financial goals."
    },
    {
      "type": "cta",
      "variant": "primary",
      "label": "Get Started",
      "url": "https://arquantix.com/dashboard"
    },
    {
      "type": "footer",
      "variant": "default",
      "company_name": "Arquantix",
      "unsubscribe_url_placeholder": "{{unsubscribe_url}}"
    }
  ]
}
```

### Exemple 2: Email avec feature cards

```json
{
  "subject": "New Features Available",
  "preheader": "Discover what's new",
  "locale": "en",
  "theme": "arquantix_v1",
  "blocks": [
    {
      "type": "hero",
      "variant": "text_only",
      "title": "New Features",
      "subtitle": "We've added powerful tools to help you invest smarter"
    },
    {
      "type": "section_title",
      "variant": "centered",
      "title": "What's New"
    },
    {
      "type": "feature_cards",
      "variant": "3up",
      "items": [
        {
          "title": "Portfolio Analytics",
          "body": "Track your investments with advanced analytics"
        },
        {
          "title": "Risk Assessment",
          "body": "Understand your risk profile better"
        },
        {
          "title": "Market Insights",
          "body": "Get real-time market data and insights"
        }
      ]
    },
    {
      "type": "cta",
      "variant": "primary",
      "label": "Explore Features",
      "url": "https://arquantix.com/features"
    },
    {
      "type": "footer",
      "variant": "default",
      "company_name": "Arquantix",
      "unsubscribe_url_placeholder": "{{unsubscribe_url}}"
    }
  ]
}
```

## Checklist "Rigid Mode"

Avant de déployer un changement:

- [ ] Tous les blocs utilisent `theme_name` paramètre
- [ ] Tous les blocs utilisent `escape_xml()` pour le contenu
- [ ] Registry valide tous les types/variants
- [ ] Schemas Pydantic ont `extra="forbid"`
- [ ] System prompt liste tous les blocs autorisés
- [ ] Agent valide contre registry après parsing
- [ ] Fallback spec est conforme au registry
- [ ] Tests manuels: prompt simple → spec → html OK
- [ ] Tests manuels: prompt long → reste ≤ 10 blocs
- [ ] Tests manuels: prompt demandant HTML → refuse et reste dans blocs

## Sécurité

- **Rejet de `<script` tags**: `compile_mjml()` vérifie avant et après compilation
- **URLs**: Validation stricte (https uniquement ou placeholders)
- **XML escaping**: Tous les contenus utilisent `escape_xml()`
- **Extra fields**: `extra="forbid"` empêche les champs inconnus

## Variables d'environnement

- `OPENAI_API_KEY`: Clé API OpenAI
- `OPENAI_MODEL`: Modèle à utiliser (défaut: `gpt-4o-mini`)
- `OPENAI_BASE_URL`: URL de base OpenAI (défaut: `https://api.openai.com/v1`)
- `ARQUANTIX_EMAIL_LOGO_URL`: URL du logo pour le header (optionnel, sinon texte "ARQUANTIX")

## Endpoints API

- `POST /api/ai/email/compose`: Compose un email (Next.js route handler)
- `POST /api/ai/voice/transcribe`: Transcription audio (Next.js route handler)

Les routes Next.js appellent OpenAI directement (pas de proxy FastAPI pour MVP).









