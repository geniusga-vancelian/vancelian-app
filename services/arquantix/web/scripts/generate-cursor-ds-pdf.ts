#!/usr/bin/env tsx
/**
 * Génère un PDF du design system Cursor (couleurs) pour partage designer.
 *
 * Usage :
 *   PDF_BASE_URL=http://localhost:3001 npx tsx scripts/generate-cursor-ds-pdf.ts
 *
 * Sortie :
 *   public/cursor-design-system-couleurs.pdf
 *
 * Pré-requis : un dev server Next.js doit tourner sur PDF_BASE_URL
 * (par défaut http://localhost:3000).
 */
import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const BASE_URL = process.env.PDF_BASE_URL || 'http://localhost:3000'
const TARGET = `${BASE_URL}/design/cursor/print`
const OUT_DIR = path.resolve(__dirname, '..', 'public')
const OUT_FILE = path.join(OUT_DIR, 'cursor-design-system-couleurs.pdf')

async function main() {
  await mkdir(OUT_DIR, { recursive: true })

  console.log(`[pdf] base url     : ${BASE_URL}`)
  console.log(`[pdf] target page  : ${TARGET}`)
  console.log(`[pdf] output       : ${OUT_FILE}`)

  const browser = await chromium.launch()
  try {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 1800 },
      deviceScaleFactor: 2,
    })
    const page = await context.newPage()

    const response = await page.goto(TARGET, {
      waitUntil: 'networkidle',
      timeout: 60_000,
    })
    if (!response || !response.ok()) {
      throw new Error(
        `Le serveur n'a pas répondu en 200 (status=${
          response?.status() ?? 'n/a'
        }). Vérifier que \`npm run dev\` tourne sur ${BASE_URL}.`,
      )
    }

    // Laisser un court délai pour les fonts / layout final.
    await page.waitForTimeout(500)

    await page.emulateMedia({ media: 'screen' })

    await page.pdf({
      path: OUT_FILE,
      format: 'A3',
      landscape: false,
      printBackground: true,
      margin: { top: '12mm', right: '10mm', bottom: '12mm', left: '10mm' },
      displayHeaderFooter: true,
      headerTemplate:
        '<div style="font-family:ui-monospace,Menlo,monospace;font-size:8px;color:#26251e99;width:100%;padding:0 12mm;">Cursor — Design system / couleurs</div>',
      footerTemplate:
        '<div style="font-family:ui-monospace,Menlo,monospace;font-size:8px;color:#26251e99;width:100%;padding:0 12mm;display:flex;justify-content:space-between;"><span>Source : cursor.com/get-started — extraction CSS</span><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    })

    console.log('[pdf] ok ✓')
  } finally {
    await browser.close()
  }
}

main().catch((err) => {
  console.error('[pdf] échec :', err)
  process.exit(1)
})
