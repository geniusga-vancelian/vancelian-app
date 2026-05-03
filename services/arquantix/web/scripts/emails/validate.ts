/**
 * Valide tous les **templates** MJML déclarés dans le registry,
 * pour toutes les locales supportées et leurs fixtures, en mode strict.
 *
 * Cette validation reflète exactement le rendu de production :
 *   1. Lecture du fichier `emails/mjml/templates/<id>.mjml`
 *   2. Inlining des partials Mustache (`{{> head}}`, `{{> Button}}`, …)
 *   3. Substitution des variables avec la fixture
 *   4. Compilation MJML strict (errors → exit 1)
 *
 * Les composants/partials seuls ne sont **pas** validés en isolation
 * (ce sont des fragments incomplets — leur validation est transitive).
 *
 * Usage :  npm run emails:validate
 */
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { renderTemplate } from '@/lib/email'
import {
  EMAIL_TEMPLATE_IDS,
  SUPPORTED_EMAIL_LOCALES,
  type EmailLocale,
  type EmailTemplateId,
} from '@/lib/email/types'
import { MJML_PATHS } from '@/lib/email/mjmlRender'

interface FixtureFile {
  vars: Record<string, unknown>
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

async function main() {
  let okCount = 0
  let failCount = 0
  const failures: string[] = []

  for (const templateId of EMAIL_TEMPLATE_IDS) {
    const fixture = await loadFixture(templateId)
    if (!fixture) {
      failCount += 1
      failures.push(`${templateId}: fixture manquante (${path.relative(process.cwd(), path.join(MJML_PATHS.fixtures, `${templateId}.json`))})`)
      console.error(`❌ ${templateId}: fixture manquante`)
      continue
    }
    for (const locale of SUPPORTED_EMAIL_LOCALES) {
      try {
        const vars = { ...fixture.vars, locale }
        const r = await renderTemplate({ templateId, locale, vars })
        if (!r.html || r.html.length < 200) {
          throw new Error(`HTML produit suspectement court (${r.html?.length ?? 0} bytes)`)
        }
        okCount += 1
        console.log(`✅ ${templateId} (${locale}) — ${r.html.length} bytes`)
      } catch (err) {
        failCount += 1
        const msg = err instanceof Error ? err.message : String(err)
        failures.push(`${templateId} (${locale}): ${msg}`)
        console.error(`❌ ${templateId} (${locale}):`, msg)
      }
    }
  }

  console.log(`\n=== Validate emails: ${okCount} OK, ${failCount} KO ===`)
  if (failCount > 0) {
    console.error('\nÉchecs:')
    for (const f of failures) console.error(`  - ${f}`)
    process.exit(1)
  }
}

main().catch((err) => {
  console.error('Validate emails fatal error:', err)
  process.exit(1)
})
