/**
 * Migration one-shot : remplace `#000000` / `#000` / `black` par `#141208`
 * (couleur dark officielle DS Vancelian) dans :
 * - global_settings.footer_json
 * - section_contents.data_json (sections CMS)
 *
 * Usage : npx tsx scripts/migrate-vancelian-dark-colors.ts
 * Audit only avant exécution — ne touche pas à l'infra Docker / volumes.
 */
import { PrismaClient } from '@prisma/client'

const VANCELIAN_DARK = '#141208'

const BLACK_VALUES = new Set(['#000000', '#000', '000000', 'black'])

function normalizeColor(value: unknown): unknown {
  if (typeof value !== 'string') return value
  const v = value.trim().toLowerCase()
  if (BLACK_VALUES.has(v)) return VANCELIAN_DARK
  return value
}

function deepNormalizeColors(obj: unknown): { next: unknown; changed: boolean } {
  if (obj === null || obj === undefined) return { next: obj, changed: false }
  if (typeof obj === 'string') {
    const next = normalizeColor(obj)
    return { next, changed: next !== obj }
  }
  if (Array.isArray(obj)) {
    let changed = false
    const next = obj.map((item) => {
      const r = deepNormalizeColors(item)
      if (r.changed) changed = true
      return r.next
    })
    return { next, changed }
  }
  if (typeof obj === 'object') {
    let changed = false
    const next: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      if (k === 'backgroundColor' || k === 'overlayColor') {
        const normalized = normalizeColor(v)
        next[k] = normalized
        if (normalized !== v) changed = true
      } else {
        const r = deepNormalizeColors(v)
        next[k] = r.next
        if (r.changed) changed = true
      }
    }
    return { next, changed }
  }
  return { next: obj, changed: false }
}

async function main() {
  const prisma = new PrismaClient()
  let footerUpdated = 0
  let sectionsUpdated = 0

  try {
    const settings = await prisma.globalSettings.findMany()
    for (const row of settings) {
      if (!row.footerJson || typeof row.footerJson !== 'object') continue
      const { next, changed } = deepNormalizeColors(row.footerJson)
      if (changed) {
        await prisma.globalSettings.update({
          where: { id: row.id },
          data: { footerJson: next as object },
        })
        footerUpdated++
        console.log(`✓ global_settings.footer_json mis à jour (id=${row.id})`)
      }
    }

    const contents = await prisma.sectionContent.findMany({
      select: { id: true, data: true },
    })
    for (const row of contents) {
      if (!row.data || typeof row.data !== 'object') continue
      const { next, changed } = deepNormalizeColors(row.data)
      if (changed) {
        await prisma.sectionContent.update({
          where: { id: row.id },
          data: { data: next as object },
        })
        sectionsUpdated++
      }
    }

    console.log('\nRésumé :')
    console.log(`  footer_json : ${footerUpdated} ligne(s) modifiée(s)`)
    console.log(`  section_contents : ${sectionsUpdated} ligne(s) modifiée(s)`)
    console.log(`  Couleur cible : ${VANCELIAN_DARK}`)
  } finally {
    await prisma.$disconnect()
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
