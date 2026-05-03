#!/usr/bin/env tsx
/**
 * Génère un PDF du design system Hermès (couleurs) pour partage designer.
 *
 * Usage :
 *   PDF_BASE_URL=http://localhost:3001 npx tsx scripts/generate-hermes-ds-pdf.ts
 *   # ou via npm :
 *   npm run ds:hermes:pdf
 *
 * Sortie :
 *   public/hermes-design-system.pdf
 *
 * Pré-requis : un dev server Next.js doit tourner sur PDF_BASE_URL
 * (par défaut http://localhost:3000).
 */
import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const BASE_URL = process.env.PDF_BASE_URL || 'http://localhost:3000'
const TARGET = `${BASE_URL}/design/hermes/print`
const OUT_DIR = path.resolve(__dirname, '..', 'public')
const OUT_FILE = path.join(OUT_DIR, 'hermes-design-system.pdf')

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

    // Attendre que les Google Fonts (EB Garamond / Manrope / Overpass Mono)
    // soient appliquées avant de générer le PDF.
    await page.evaluate(async () => {
      // @ts-expect-error - document.fonts est dispo dans Chromium.
      if (document.fonts && document.fonts.ready) {
        // @ts-expect-error - idem
        await document.fonts.ready
      }
    })
    await page.waitForTimeout(800)

    await page.emulateMedia({ media: 'screen' })

    await page.pdf({
      path: OUT_FILE,
      format: 'A3',
      landscape: false,
      printBackground: true,
      margin: { top: '12mm', right: '10mm', bottom: '12mm', left: '10mm' },
      displayHeaderFooter: true,
      headerTemplate:
        '<div style="font-family:\'Overpass Mono\',ui-monospace,Menlo,monospace;font-size:8px;color:#69696999;width:100%;padding:0 12mm;">Hermès — Design system / tokens, atomes &amp; composants</div>',
      footerTemplate:
        '<div style="font-family:\'Overpass Mono\',ui-monospace,Menlo,monospace;font-size:8px;color:#69696999;width:100%;padding:0 12mm;display:flex;justify-content:space-between;"><span>Source : hermes.com — extraction CSS &amp; bundle Angular</span><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
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
