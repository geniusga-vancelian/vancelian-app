import { NextResponse } from 'next/server'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { z } from 'zod'
import { getSessionFromCookie } from '@/lib/auth'
import { EMAIL_TEMPLATES } from '@/lib/email'
import { EMAIL_TEMPLATE_IDS } from '@/lib/email/types'
import { MJML_PATHS } from '@/lib/email/mjmlRender'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

/**
 * Liste tous les **templates MJML** disponibles avec leurs métadonnées :
 * - id, description, mjmlPath
 * - schéma JSON dérivé du schéma Zod (utile pour l’IA et la doc)
 * - fixture canonique (exemple de variables)
 */
export async function GET() {
  const session = await getSessionFromCookie()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const items = await Promise.all(
    EMAIL_TEMPLATE_IDS.map(async (id) => {
      const t = EMAIL_TEMPLATES[id]
      const fixture = await loadFixture(id)
      const jsonSchema = safeToJsonSchema(t.varsSchema)
      return {
        id: t.id,
        mjmlPath: t.mjmlPath,
        description: t.description,
        subjectExamples: {
          fr: safeSubject(t, fixture?.vars, 'fr'),
          en: safeSubject(t, fixture?.vars, 'en'),
        },
        jsonSchema,
        fixture: fixture?.vars ?? null,
      }
    }),
  )

  return NextResponse.json({ items })
}

async function loadFixture(
  id: string,
): Promise<{ vars: Record<string, unknown> } | null> {
  try {
    const raw = await fs.readFile(
      path.join(MJML_PATHS.fixtures, `${id}.json`),
      'utf8',
    )
    return JSON.parse(raw)
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === 'ENOENT') return null
    return null
  }
}

function safeToJsonSchema(schema: z.ZodType<unknown>) {
  try {
    return z.toJSONSchema(schema)
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'toJSONSchema failed' }
  }
}

function safeSubject(
  t: (typeof EMAIL_TEMPLATES)[keyof typeof EMAIL_TEMPLATES],
  vars: unknown,
  locale: 'fr' | 'en',
): string {
  if (!vars) return ''
  try {
    const parsed = t.varsSchema.safeParse(vars)
    if (!parsed.success) return ''
    const subjectFn = t.subject as (vars: unknown, locale: 'fr' | 'en') => string
    return subjectFn(parsed.data, locale)
  } catch {
    return ''
  }
}
