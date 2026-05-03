/**
 * Lecture seule : statistiques et anomalies sur `article_blocks` (blog).
 * Usage : `npx tsx scripts/article-blocks-dry-run.ts`
 */

import { PrismaClient, ArticleBlockType } from '@prisma/client'

const prisma = new PrismaClient()

type Issue = { blockId: string; articleId: string; kind: string; detail?: string }

function asRecord(x: unknown): Record<string, unknown> {
  if (x && typeof x === 'object' && !Array.isArray(x)) return x as Record<string, unknown>
  return {}
}

async function main() {
  const rows = await prisma.articleBlock.findMany({
    select: { id: true, articleId: true, type: true, data: true, order: true },
    orderBy: [{ articleId: 'asc' }, { order: 'asc' }],
  })

  const byType = new Map<string, number>()
  const issues: Issue[] = []

  for (const r of rows) {
    byType.set(r.type, (byType.get(r.type) ?? 0) + 1)
    const d = asRecord(r.data)

    if (r.type === ArticleBlockType.MEDIA_IMAGE_CAROUSEL) {
      const ids = d.imageMediaIds
      if (!Array.isArray(ids) || ids.length === 0) {
        issues.push({
          blockId: r.id,
          articleId: r.articleId,
          kind: 'carousel_empty_imageMediaIds',
        })
      }
    }

    if (r.type === ArticleBlockType.IMAGE) {
      if (typeof d.mediaId !== 'string' || !d.mediaId.trim()) {
        issues.push({
          blockId: r.id,
          articleId: r.articleId,
          kind: 'image_missing_mediaId',
        })
      }
    }

    if (r.type === ArticleBlockType.DOCUMENT) {
      if (typeof d.mediaId !== 'string' || !d.mediaId.trim()) {
        issues.push({
          blockId: r.id,
          articleId: r.articleId,
          kind: 'document_missing_mediaId',
        })
      }
    }

    if (r.type === ArticleBlockType.DOCUMENTS_LIST) {
      const entries = d.documentEntries
      const legacyIds = d.documentMediaIds
      const hasEntries = Array.isArray(entries) && entries.length > 0
      const hasLegacy = Array.isArray(legacyIds) && legacyIds.length > 0
      if (!hasEntries && !hasLegacy) {
        issues.push({
          blockId: r.id,
          articleId: r.articleId,
          kind: 'documents_list_no_entries',
        })
      }
    }

    if (r.type === ArticleBlockType.DOCUMENTS_LIST && Array.isArray(d.documentMediaIds) && !d.documentEntries) {
      issues.push({
        blockId: r.id,
        articleId: r.articleId,
        kind: 'documents_list_legacy_documentMediaIds_only',
      })
    }
  }

  const summary = Object.fromEntries(
    [...byType.entries()].sort((a, b) => a[0].localeCompare(b[0])),
  )

  console.log(JSON.stringify({ totalBlocks: rows.length, byType: summary, issueCount: issues.length }, null, 2))

  if (issues.length > 0) {
    const sample = issues.slice(0, 50)
    console.log('\nSample issues (max 50):')
    console.log(JSON.stringify(sample, null, 2))
    if (issues.length > 50) {
      console.log(`\n… ${issues.length - 50} more`)
    }
  }

  console.log('\narticle-blocks-dry-run : OK (read-only).')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
