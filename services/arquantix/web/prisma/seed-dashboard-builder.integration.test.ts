/**
 * Intégration DB optionnelle : définir ARQUANTIX_DS_SEED_INTEGRATION=1 et DATABASE_URL.
 * Ré-exécute les seeds idempotents puis vérifie chapitre + dashboard_layout.
 */
import assert from 'node:assert/strict'
import { after, before, describe, it } from 'node:test'

import { PrismaClient } from '@prisma/client'

import { seedDsComponents } from './seed-ds-components'
import { seedWidgetBuilderCore } from './seed-widget-builder-core'
import {
  DASHBOARD_LAYOUT_SLUG,
  FLUTTER_DS_CHAPTER_SLUG,
  getDashboardBuilderProductHealth,
} from '../src/lib/health/dashboard-builder-products'

const runIntegration = process.env.ARQUANTIX_DS_SEED_INTEGRATION === '1' && Boolean(process.env.DATABASE_URL)

;(runIntegration ? describe : describe.skip)('seed dashboard builder (integration)', () => {
  const prisma = new PrismaClient()

  before(async () => {
    await seedDsComponents(prisma)
    await seedWidgetBuilderCore(prisma)
  })

  after(async () => {
    await prisma.$disconnect()
  })

  it('chapter component_ds_flutter and dashboard_layout exist (no Chapter not found)', async () => {
    const chapter = await prisma.dsComponentChapter.findUnique({
      where: { slug: FLUTTER_DS_CHAPTER_SLUG },
      select: { id: true },
    })
    assert.ok(chapter)
    const layout = await prisma.dsComponent.findUnique({
      where: {
        chapterId_slug: { chapterId: chapter.id, slug: DASHBOARD_LAYOUT_SLUG },
      },
      select: { id: true, schemaJson: true },
    })
    assert.ok(layout)
  })

  it('health flags are true after seed', async () => {
    const h = await getDashboardBuilderProductHealth(prisma)
    assert.equal(h.dashboard_layout_ok, true)
    assert.equal(h.vault_widgets_ok, true)
    assert.equal(h.offers_widgets_ok, true)
    assert.equal(h.bundles_widgets_ok, true)
    assert.ok(h.ds_component_chapters_count >= 3)
    assert.ok(h.ds_components_count >= 10)
  })
})
