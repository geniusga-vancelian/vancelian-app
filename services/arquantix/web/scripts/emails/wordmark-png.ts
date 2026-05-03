/**
 * Génère les PNG du wordmark Arquantix utilisés par les templates MJML.
 *
 * Pourquoi : les clients email (notamment Outlook + dark mode iOS) ont un support
 * SVG inégal. Les composants `HeaderL1/L2/L3/Footer.mjml` référencent donc des PNG :
 *
 *   - public/email-ds/logo-wordmark-black.png  (sur fond clair)
 *   - public/email-ds/logo-wordmark-white.png  (sur fond sombre)
 *
 * Source : `public/email-ds/logo-wordmark-black.svg` (fill="currentColor").
 * On substitue la couleur puis on rasterise via `sharp` à 3× la largeur cible
 * (≈ 600 px) pour rester net en HiDPI dans les clients mail.
 *
 * Idempotent : à relancer si le SVG source change.
 *
 * Lancement :
 *   npm run emails:wordmark-png
 */
import { promises as fs } from 'node:fs'
import path from 'node:path'
import sharp from 'sharp'

const ROOT = path.resolve(__dirname, '..', '..')
const SRC_SVG = path.join(ROOT, 'public', 'email-ds', 'logo-wordmark-black.svg')
const OUT_DIR = path.join(ROOT, 'public', 'email-ds')

const TARGETS: { file: string; color: string }[] = [
  { file: 'logo-wordmark-black.png', color: '#0E0E10' },
  { file: 'logo-wordmark-white.png', color: '#FFFFFF' },
]

const PIXEL_WIDTH = 600

async function main() {
  const svg = await fs.readFile(SRC_SVG, 'utf8')
  if (!/fill\s*=\s*"currentColor"/i.test(svg)) {
    console.warn(
      `[wordmark-png] WARNING: ${path.basename(SRC_SVG)} ne contient pas fill="currentColor" ; ` +
        `la substitution de couleur sera ignorée.`,
    )
  }

  for (const t of TARGETS) {
    const colored = svg.replace(/fill\s*=\s*"currentColor"/gi, `fill="${t.color}"`)
    const buf = Buffer.from(colored)
    const out = path.join(OUT_DIR, t.file)
    await sharp(buf, { density: 384 })
      .resize({ width: PIXEL_WIDTH })
      .png({ compressionLevel: 9, adaptiveFiltering: true })
      .toFile(out)
    const stat = await fs.stat(out)
    console.log(`[wordmark-png] wrote ${path.relative(ROOT, out)} (${stat.size} B)`)
  }
}

main().catch((err) => {
  console.error('[wordmark-png] failed:', err)
  process.exit(1)
})
