import { describe, it, before } from 'node:test'
import assert from 'node:assert/strict'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { renderTemplate, EMAIL_TEMPLATE_IDS_LIST } from '@/lib/email'
import {
  SUPPORTED_EMAIL_LOCALES,
  type EmailTemplateId,
} from '@/lib/email/types'
import { MJML_PATHS } from '@/lib/email/mjmlRender'
import { EmailTemplateVarsError } from '@/lib/email/interpolate'
import { resetEmailPartialsCache } from '@/lib/email/loadPartials'

async function loadFixtureVars(id: EmailTemplateId): Promise<Record<string, unknown>> {
  const raw = await fs.readFile(
    path.join(MJML_PATHS.fixtures, `${id}.json`),
    'utf8',
  )
  const fx = JSON.parse(raw) as { vars: Record<string, unknown> }
  return fx.vars
}

describe('renderTemplate (E2E par template)', () => {
  before(() => {
    resetEmailPartialsCache()
  })

  for (const templateId of EMAIL_TEMPLATE_IDS_LIST) {
    for (const locale of SUPPORTED_EMAIL_LOCALES) {
      it(`rend ${templateId} (${locale}) avec sa fixture sans erreur`, async () => {
        const vars = await loadFixtureVars(templateId as EmailTemplateId)
        const r = await renderTemplate({
          templateId: templateId as EmailTemplateId,
          locale,
          vars: { ...vars, locale },
        })
        assert.ok(r.html.length > 1000, `HTML ${templateId}/${locale} doit être substantiel`)
        assert.ok(r.subject.length > 0, `Subject ${templateId}/${locale} doit être défini`)
        assert.ok(r.text.length > 0, `Text fallback ${templateId}/${locale} doit être défini`)
        assert.equal(r.locale, locale)
        assert.equal(r.templateId, templateId)
        // Aucun placeholder Mustache restant
        assert.ok(!r.html.includes('{{'), `HTML ${templateId}/${locale} ne doit plus contenir {{ }}`)
      })
    }
  }

  it('rejette les variables invalides via Zod (EmailTemplateVarsError)', async () => {
    await assert.rejects(
      () =>
        renderTemplate({
          templateId: 'otp-login',
          locale: 'fr',
          vars: { otp: { code: 'abc' } } as unknown,
        }),
      (err) => err instanceof EmailTemplateVarsError,
    )
  })
})
