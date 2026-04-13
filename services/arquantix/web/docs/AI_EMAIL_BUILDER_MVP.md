# AI Email Builder MVP

## Overview

AI Email Builder is an integrated module in the Arquantix CMS Admin that allows users to create professional email templates using AI (OpenAI) and MJML.

## Architecture

### Backend (FastAPI) - Optional

Located in `api/services/ai_email/`:

- **schemas.py**: Pydantic models for EmailSpec validation
- **blocks/**: MJML template functions for each block type (hero, text, feature_cards, cta, footer)
- **render.py**: Builds MJML from EmailSpec and compiles to HTML
- **system_prompt.py**: Strict OpenAI system prompt for Email Architect
- **agent.py**: OpenAI integration with JSON parsing and retry logic
- **routes.py**: FastAPI endpoints (kept for backward compatibility)

**Note:** The frontend now uses Next.js API routes that call OpenAI directly (same pattern as Auto-Translate). The FastAPI backend routes are optional and kept for backward compatibility.

### Frontend (Next.js)

Located in `web/src/`:

- **app/admin/ai/email/page.tsx**: Main page with split layout
- **app/api/ai/email/compose/route.ts**: Next.js API route (calls OpenAI directly)
- **app/api/ai/voice/transcribe/route.ts**: Next.js API route (calls OpenAI Whisper directly)
- **lib/ai-email/**: Core logic
  - `composeEmail.ts`: OpenAI email composition (uses `@/lib/openai/client`)
  - `buildMjml.ts`: Builds MJML from EmailSpec
  - `compileMjml.ts`: Compiles MJML to HTML using npx
- **components/ai-email/**: React components
  - `ChatStudio.tsx`: ChatGPT-like interface
  - `VoiceRecorder.tsx`: Audio transcription
  - `EmailOutput.tsx`: Preview with Desktop/Mobile/Code views
  - `HtmlViewer.tsx`: Code viewer with copy
  - `api.ts`: API client functions (calls Next.js routes)
  - `types.ts`: TypeScript types
  - `schema.ts`: Zod validation schemas

## Endpoints

### POST /api/ai/email/compose (Next.js API Route)

Compose email from text prompt. Calls OpenAI directly from Next.js (same pattern as Auto-Translate).

**Request:**
```json
{
  "prompt": "Create a welcome email for new users",
  "locale": "en",
  "previous_spec": { ... } // optional
}
```

**Response:**
```json
{
  "assistant_text": "I've created a professional email...",
  "spec": { ... },
  "mjml": "<mjml>...</mjml>",
  "html": "<!DOCTYPE html>..."
}
```

**Authentication:** Uses `getSessionFromCookie()` (same as other admin routes)

### POST /api/ai/voice/transcribe (Next.js API Route)

Transcribe audio to text using OpenAI Whisper. Calls OpenAI directly from Next.js.

**Request:** multipart/form-data with `file` (audio/webm, audio/wav, audio/mpeg)

**Response:**
```json
{
  "transcript": "Transcribed text..."
}
```

**Authentication:** Uses `getSessionFromCookie()` (same as other admin routes)

### Backend FastAPI Endpoints (Optional)

The FastAPI backend endpoints (`/api/ai/email/compose`, `/api/ai/voice/transcribe`) are kept for backward compatibility but are not used by the frontend. They follow the same authentication pattern as other admin endpoints (`get_current_user`).

## Setup

### Backend Dependencies

```bash
cd api
pip install -r requirements.txt
```

Required:
- `openai==1.12.0` (for OpenAI API)
- `httpx` (already in requirements)

### Node.js for MJML

MJML compilation requires Node.js and npx:

```bash
# Install Node.js (if not already installed)
# Then MJML will be installed automatically via npx on first use
```

The backend uses `npx mjml` to compile MJML to HTML. On first use, npx will download MJML automatically.

### Environment Variables

**Backend (`api/.env`):**
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini  # optional, defaults to gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1  # optional, defaults to https://api.openai.com/v1
```

**Frontend (`web/.env.local`):**
```
OPENAI_API_KEY=sk-...  # Required - same as backend
OPENAI_MODEL=gpt-4o-mini  # optional, defaults to gpt-4o-mini
OPENAI_TRANSLATION_TEMPERATURE=0  # optional, defaults to 0
OPENAI_TRANSLATION_MAX_CHARS=12000  # optional, defaults to 12000
```

**Note:** The frontend uses Next.js API routes that call OpenAI directly (same pattern as Auto-Translate). No `NEXT_PUBLIC_BACKEND_URL` is needed.

### Running

1. **Start Next.js frontend:**
```bash
cd web
npm run dev
```

2. **Access:**
- Frontend: http://localhost:3000/admin/ai/email

**Note:** The frontend calls OpenAI directly via Next.js API routes. The FastAPI backend is optional and only needed if you want to use the backend endpoints directly.

## EmailSpec Structure

EmailSpec is a strict JSON schema:

```typescript
{
  subject: string (1-200 chars)
  preheader?: string (max 150 chars)
  locale: string (2-letter code, default: "en")
  blocks: Block[] (2-6 blocks)
}
```

**Block Types:**

1. **hero**: Title, subtitle, optional image, optional CTA
2. **text**: Heading and body text
3. **feature_cards**: Heading + 1-3 feature items
4. **cta**: Call-to-action button with optional hint
5. **footer**: Company info + unsubscribe link (MUST be last)

**Constraints:**
- Maximum 6 blocks
- Maximum 1 hero block
- Footer must be last
- Footer must include `{{unsubscribe_url}}` placeholder

## Adding a New Block Type

1. **Backend:**
   - Add block class to `api/services/ai_email/schemas.py`
   - Add render function to `api/services/ai_email/blocks/`
   - Update `Block` union type
   - Update `render.py` `_render_block()` function
   - Update `system_prompt.py` with new block type

2. **Frontend:**
   - Add block interface to `web/src/components/ai-email/types.ts`
   - Update `Block` union type

## Security

- All endpoints require authentication (`getSessionFromCookie()` for Next.js routes, `get_current_user` for FastAPI routes)
- OpenAI API key is never exposed to the frontend (only used server-side)
- HTML output is sanitized (no `<script>` tags)
- Audio file size limited to 15MB
- Prompt length limited to 2000 chars
- iframe preview uses `sandbox=""` (no scripts)
- Uses same authentication pattern as Auto-Translate module

## Troubleshooting

### MJML compilation fails

- Ensure Node.js is installed
- Check that `npx` is available in PATH
- First run may take time as npx downloads MJML
- Check backend logs for error details

### OpenAI API errors

- Verify `OPENAI_API_KEY` is set
- Check API quota/rate limits
- Verify network connectivity

### Audio transcription fails

- Check file format (webm, wav, mpeg supported)
- Verify file size < 15MB
- Check OpenAI API quota

## Future Enhancements

- Save email templates to database
- Email preview in actual email clients
- Template library
- Multi-language support
- A/B testing variants
- Analytics integration

