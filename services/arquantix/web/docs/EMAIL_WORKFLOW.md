# Email Builder Workflow

## Overview

The Email Builder V5 introduces a complete workflow for creating, validating, and translating emails with multi-language support.

## Workflow Steps

### 1. Build Email

Use the Email Builder (`/admin/ai/email`) to create an email:

- **AI Copilot Mode**: Use OpenAI to generate email content from prompts
- **Manual Edit Mode**: Edit email blocks directly (content-only editing)
- **Templates**: Start from pre-built templates (welcome_v1, newsletter_v1, etc.)
- **Slots**: Add optional blocks (IMAGE, DIVIDER, SPACER) while keeping core structure locked

### 2. Save Draft

Click "Save Draft" in the Email Builder to persist the email:

- Email is saved with status `DRAFT`
- Structure can still be modified
- Redirects to email detail page

**API**: `POST /api/admin/emails`

### 3. Validate Email

Once the email is ready, validate it:

- Click "Validate Email" on the email detail page
- Status changes from `DRAFT` to `VALIDATED`
- **Structure is now permanently locked** (cannot be modified)
- Only content can be translated, structure cannot change

**API**: `POST /api/admin/emails/[id]/validate`

### 4. Translate Email

After validation, translate the email to other locales:

- Navigate to "Translations" tab
- Click "Auto-translate"
- Select target locales (EN, IT, etc.)
- Choose mode:
  - **Missing only**: Only translate if translation doesn't exist
  - **Force**: Re-translate even if translation exists
- Translations are created with status `MACHINE` (needs approval)

**API**: `POST /api/admin/translate/email`

**Translation Rules**:
- Only translates **content** (subject, preheader, text props of blocks)
- **Never modifies structure** (blocks, order, types)
- Preserves URLs, placeholders, and structural elements
- Uses existing translation infrastructure (glossary, retry logic, logs)

### 5. Approve Translation

Review and approve machine translations:

- Translations start with status `MACHINE`
- Review the translated email in the Preview tab
- Click "Approve" to mark translation as `APPROVED`
- Approved translations are ready for export/sending

**API**: `POST /api/admin/translate/approve`

### 6. Export / Send (Future)

Once translations are approved, emails can be:

- Exported to email providers (SendGrid, Mailchimp, etc.)
- Sent directly via SMTP
- Scheduled for sending
- Versioned for A/B testing

## Data Model

### Email

```prisma
model Email {
  id         String      @id @default(uuid())
  name       String
  templateId String
  theme      String
  locale     String
  spec       Json        // EmailSpec (structure locked after validation)
  status     EmailStatus // DRAFT | VALIDATED
  translations EmailI18n[]
}
```

### EmailI18n

```prisma
model EmailI18n {
  id               String           @id @default(uuid())
  emailId          String
  locale           String
  spec             Json             // Translated EmailSpec (content only)
  translationStatus TranslationStatus // MACHINE | APPROVED
}
```

## Status Flow

```
DRAFT → VALIDATED → (translation) → MACHINE → APPROVED
```

- **DRAFT**: Email can be modified (structure + content)
- **VALIDATED**: Structure locked, only content can be translated
- **MACHINE**: Translation exists but needs human approval
- **APPROVED**: Translation approved and ready for use

## Guardrails

### Email VALIDATED

- ❌ Cannot modify structure (blocks, order, types)
- ❌ Cannot save draft
- ✅ Can translate content
- ✅ Can preview in any locale

### Translation MACHINE

- ⚠️ Visual warning in UI
- ⚠️ Publishing requires APPROVED status
- ✅ Can approve to change status to APPROVED

## API Endpoints

### Email Management

- `GET /api/admin/emails` - List all emails
- `POST /api/admin/emails` - Create email (DRAFT)
- `GET /api/admin/emails/[id]` - Get email details
- `PUT /api/admin/emails/[id]` - Update email (DRAFT only)
- `DELETE /api/admin/emails/[id]` - Delete email
- `POST /api/admin/emails/[id]/validate` - Validate email (locks structure)

### Translation

- `POST /api/admin/translate/email` - Auto-translate email
- `POST /api/admin/translate/approve` - Approve translation (entityType: "EMAIL")

## UI Pages

- `/admin/emails` - List all emails
- `/admin/emails/[id]` - Email detail with:
  - **Preview tab**: View email in any locale (Desktop/Mobile/Code)
  - **Translations tab**: Manage translations, auto-translate, approve
  - **Meta tab**: Email metadata (readonly)

## Translation Infrastructure

The email translation system reuses the existing translation infrastructure:

- `translateText()` - Translates individual text fields
- `getGlossary()` - Applies brand terms and preferred translations
- `TranslationLog` - Logs all translation operations
- `requestWithRetry()` - Handles OpenAI API retries
- `TranslationStatus` - Tracks MACHINE → APPROVED workflow

## Best Practices

1. **Build & Iterate**: Use AI Copilot or Manual Edit to create email
2. **Save Drafts**: Save frequently during editing
3. **Validate Early**: Validate once structure is final
4. **Translate After Validation**: Only translate validated emails
5. **Review & Approve**: Always review MACHINE translations before approving
6. **Use Glossary**: Configure brand terms in Settings → Translation

## Future Enhancements

- Export to email providers (SendGrid, Mailchimp, etc.)
- Direct SMTP sending
- Scheduled sending
- A/B testing with variants
- Email analytics (open rates, clicks)
- Versioning system
- Template library expansion









