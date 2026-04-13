# Arquantix UGG v1 Template

## Overview

The `arquantix_ugg_v1` template is the single "golden" template for email composition. It is based on a UGG-style MJML template with a strict JSON schema (`EmailSpecUGG`) that the AI must generate.

**Key Principle**: The AI generates **ONLY JSON**, never MJML or HTML. The template is a hardcoded MJML file that gets populated with JSON data.

## Architecture

```
User Prompt → AI Agent (agent_ugg.py) → EmailSpecUGG JSON
                                           ↓
                                    Renderer (render_ugg.py)
                                           ↓
                                    MJML Template
                                           ↓
                                    MJML Compiler
                                           ↓
                                    HTML Output
```

## EmailSpecUGG Schema

The AI must generate a JSON object matching this strict schema:

### Required Fields

- `subject` (string, 1-120 chars): Email subject line
- `preheader` (string, 1-100 chars): Preview text shown in email clients
- `locale` (string, 2-letter ISO code, default: "en")
- `offer_line` (string, 1-100 chars): Uppercase offer/promo line
- `headline_lines` (array, 2-4 items): Uppercase, impactful headlines
- `intro_text` (string, 1-1000 chars): Introductory paragraph
- `hero_image_url` (string): https:// URL or {{placeholder}}
- `hero_image_alt` (string, 1-200 chars): Alt text for hero image
- `carousel` (object): Product/item carousel
  - `items` (array, 1-6 items): Carousel items
    - `image_url` (string): https:// URL or {{placeholder}}
    - `thumb_url` (string, optional): Thumbnail URL
    - `alt` (string, 1-200 chars): Item description
    - `href` (string): Link URL
- `ctas` (object): Call-to-action buttons
  - `primary` (object, required): Primary CTA
    - `label` (string, 1-50 chars): Button text
    - `url` (string): https:// URL or {{placeholder}}
  - `secondary` (object, optional): Secondary CTA
    - `label` (string, 1-50 chars): Button text
    - `url` (string): https:// URL or {{placeholder}}

### Optional Fields

- `promo_block` (object): Promotional block
  - `image_url` (string): https:// URL or {{placeholder}}
  - `title_lines` (array, 1-4 items): Title lines
  - `body` (string, 1-500 chars): Promotional text
  - `button_label` (string, 1-50 chars): Button text
  - `button_url` (string): https:// URL or {{placeholder}}
- `rewards_block` (object): Rewards/loyalty block
  - `image_url` (string): https:// URL or {{placeholder}}
  - `heading` (string, 1-100 chars): Heading
  - `body` (string, 1-500 chars): Body text
  - `button_label` (string, 1-50 chars): Button text
  - `button_url` (string): https:// URL or {{placeholder}}
- `footer` (object, defaults provided): Footer information
  - `company_name` (string, default: "Arquantix")
  - `legal_lines` (array, max 5 items, optional): Legal text lines
  - `phone` (string, optional, max 50 chars)
  - `address` (string, optional, max 300 chars)
  - `privacy_policy_url_placeholder` (string, default: "{{privacy_policy_url}}")
  - `unsubscribe_url_placeholder` (string, default: "{{unsubscribe_url}}")
  - `view_in_browser_url_placeholder` (string, default: "{{view_in_browser_url}}")
  - `social_links` (object, optional): Social media links
    - `facebook` (string, optional): https:// URL or {{placeholder}}
    - `instagram` (string, optional)
    - `youtube` (string, optional)
    - `twitter` (string, optional)
    - `linkedin` (string, optional)

## URL Validation

All URLs must be:
- `https://` URLs, OR
- Placeholders like `{{logo_url}}`, `{{unsubscribe_url}}`, etc.

Placeholders are preserved in the final MJML/HTML and should be replaced by the email sending system.

## Template Structure

The MJML template includes:

1. **Preheader** (hidden): Preview text
2. **Offer Line**: Uppercase promotional line
3. **Headline**: 2-4 lines of uppercase headlines
4. **Intro Text**: Introductory paragraph
5. **Hero Image**: Large hero image
6. **Carousel**: Product/item grid (1-6 items)
7. **CTA Buttons**: Primary and optional secondary button
8. **Promo Block** (optional): Promotional section with image, title, body, button
9. **Rewards Block** (optional): Rewards/loyalty section
10. **Footer**: Company info, legal links, social links, unsubscribe

## API Endpoints

### POST `/api/ai/email/compose-ugg`

Compose an email using the UGG template.

**Request:**
```json
{
  "prompt": "Create a welcome email for new users",
  "locale": "en",
  "previous_spec": { ... } // optional, for refinement
}
```

**Response:**
```json
{
  "assistant_text": "I've created a professional email...",
  "templateId": "arquantix_ugg_v1",
  "mjml": "...",
  "html": "...",
  "spec": { ... }, // EmailSpecUGG
  "warnings": [ ... ] // optional
}
```

### GET `/api/ai/email/templates`

List available templates. Returns only `arquantix_ugg_v1` by default.

**Query Parameters:**
- `show_legacy` (boolean, default: false): Show legacy templates (requires `SHOW_LEGACY_TEMPLATES=true` env var)

## Files

- **Template MJML**: `api/services/ai_email/templates_mjml/arquantix_ugg_v1.mjml`
- **Renderer**: `api/services/ai_email/templates_mjml/render_ugg.py`
- **Schema**: `api/services/ai_email/schemas_ugg.py`
- **Agent**: `api/services/ai_email/agent_ugg.py`
- **Routes**: `api/services/ai_email/routes.py` (endpoint `/email/compose-ugg`)

## Migration from Old Templates

All old templates have been archived (status set to DRAFT). To restore them:

1. Set `SHOW_LEGACY_TEMPLATES=true` in `.env`
2. Use `show_legacy=true` query parameter in `/api/ai/email/templates`
3. Or manually update template status in database

## Development

To test the template:

```bash
# Start the API
cd api
python3 -m uvicorn main:app --reload

# Test the endpoint
curl -X POST http://localhost:8000/api/ai/email/compose-ugg \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a welcome email for new Arquantix users"
  }'
```

## Notes

- The AI agent (`agent_ugg.py`) has strict instructions to NEVER output MJML or HTML
- All placeholders (like `{{unsubscribe_url}}`) are preserved in the final output
- The template is designed for responsive email clients
- Brand colors and styling are defined in the MJML template CSS






