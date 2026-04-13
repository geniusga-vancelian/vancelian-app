/**
 * One-shot: run the same Prisma calls as GET /api/blog to surface the real error.
 * Usage: cd web && npx tsx scripts/diagnose-blog-prisma.ts
 */
import { readFileSync, existsSync } from 'fs'
import { resolve } from 'path'
import { PrismaClient } from '@prisma/client'

function loadDatabaseUrlFromEnvFile() {
  for (const name of ['.env.local', '.env']) {
    const p = resolve(__dirname, '..', name)
    if (!existsSync(p)) continue
    const text = readFileSync(p, 'utf8')
    for (const line of text.split('\n')) {
      const t = line.trim()
      if (!t || t.startsWith('#')) continue
      const m = t.match(/^DATABASE_URL=(.*)$/)
      if (m) {
        let v = m[1].trim()
        if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
          v = v.slice(1, -1)
        }
        process.env.DATABASE_URL = v
        return
      }
    }
  }
}

loadDatabaseUrlFromEnvFile()

function dbFingerprint(url: string | undefined): string {
  if (!url) return '(no DATABASE_URL)'
  try {
    const u = new URL(url.replace(/^postgresql:/, 'http:'))
    return `host=${u.hostname} port=${u.port || '5432'} db=${u.pathname.replace(/^\//, '') || '?'}`
  } catch {
    return '(unparseable DATABASE_URL)'
  }
}

async function main() {
  const url = process.env.DATABASE_URL
  console.log('[Next Prisma DB]', dbFingerprint(url))

  const prisma = new PrismaClient({ log: ['error', 'warn'] })

  try {
    console.log('[diagnose] investmentCategory.findMany …')
    const cats = await prisma.investmentCategory.findMany({
      orderBy: [{ sortOrder: 'asc' }, { label: 'asc' }],
      take: 3,
    })
    console.log('[diagnose] categories ok, count sample:', cats.length)

    console.log('[diagnose] article.findFirst (published, with includes) …')
    const a = await prisma.article.findFirst({
      where: { status: 'PUBLISHED' },
      include: {
        coverMedia: true,
        blocks: { orderBy: { order: 'asc' }, take: 5 },
        i18n: { where: { locale: 'fr' }, take: 1 },
      },
    })
    console.log('[diagnose] article sample:', a ? `id=${a.id} slug=${a.slug}` : '(none)')

    console.log('[diagnose] article.count PUBLISHED:', await prisma.article.count({ where: { status: 'PUBLISHED' } }))

    console.log('[diagnose] article.findFirst with blocks.i18n (getArticleBySlug shape) …')
    await prisma.article.findFirst({
      include: {
        coverMedia: true,
        i18n: { where: { locale: 'fr' }, take: 1 },
        blocks: {
          orderBy: { order: 'asc' },
          include: { i18n: { where: { locale: 'fr' }, take: 1 } },
        },
      },
    })
    console.log('[diagnose] blocks.i18n include ok')
  } catch (e) {
    console.error('[diagnose] FAILED')
    console.error(e)
    if (e instanceof Error) {
      console.error('stack:', e.stack)
    }
    process.exitCode = 1
  } finally {
    await prisma.$disconnect()
  }
}

main()
