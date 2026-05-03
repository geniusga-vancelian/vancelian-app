/**
 * Compile tous les templates MJML déclarés dans `EMAIL_TEMPLATES`,
 * pour toutes les locales supportées et chaque fixture présente,
 * et écrit le HTML dans `emails/rendered/<id>.<locale>.html`.
 *
 * Usage :  npm run emails:build
 */
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { renderTemplate } from '@/lib/email'
import {
  EMAIL_TEMPLATE_IDS,
  SUPPORTED_EMAIL_LOCALES,
  type EmailTemplateId,
  type EmailLocale,
} from '@/lib/email/types'
import { MJML_PATHS } from '@/lib/email/mjmlRender'

interface FixtureFile {
  /** Variables utilisées pour rendre le template. */
  vars: Record<string, unknown>
  /** Locale par défaut de la fixture (peut être surchargée). */
  locale?: EmailLocale
}

async function loadFixture(templateId: EmailTemplateId): Promise<FixtureFile | null> {
  const file = path.join(MJML_PATHS.fixtures, `${templateId}.json`)
  try {
    const raw = await fs.readFile(file, 'utf8')
    return JSON.parse(raw) as FixtureFile
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === 'ENOENT') return null
    throw e
  }
}

async function ensureRenderedDir() {
  await fs.mkdir(MJML_PATHS.rendered, { recursive: true })
}

async function buildAll() {
  await ensureRenderedDir()

  let okCount = 0
  let failCount = 0
  const failures: string[] = []

  for (const templateId of EMAIL_TEMPLATE_IDS) {
    const fixture = await loadFixture(templateId)
    if (!fixture) {
      console.warn(`⚠️  Pas de fixture pour ${templateId} — skip.`)
      continue
    }
    for (const locale of SUPPORTED_EMAIL_LOCALES) {
      const vars = { ...fixture.vars, locale }
      try {
        const rendered = await renderTemplate({ templateId, locale, vars, beautify: true })
        const outFile = path.join(
          MJML_PATHS.rendered,
          `${templateId}.${locale}.html`,
        )
        await fs.writeFile(outFile, rendered.html, 'utf8')
        const txtFile = path.join(
          MJML_PATHS.rendered,
          `${templateId}.${locale}.txt`,
        )
        await fs.writeFile(txtFile, rendered.text, 'utf8')
        okCount += 1
        console.log(`✅ ${templateId} (${locale}) → ${path.relative(process.cwd(), outFile)}`)
      } catch (err) {
        failCount += 1
        const message = err instanceof Error ? err.message : String(err)
        failures.push(`${templateId} (${locale}): ${message}`)
        console.error(`❌ ${templateId} (${locale}):`, message)
      }
    }
  }

  console.log(`\n=== Build emails: ${okCount} OK, ${failCount} KO ===`)
  if (failCount > 0) {
    console.error('\nÉchecs:')
    for (const f of failures) console.error(`  - ${f}`)
    process.exit(1)
  }
}

buildAll().catch((err) => {
  console.error('Build emails fatal error:', err)
  process.exit(1)
})
