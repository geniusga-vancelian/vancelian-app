/* eslint-disable no-console */
import { execFileSync } from 'node:child_process'
import { promises as fs } from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { PrismaClient } from '@prisma/client'

import {
  lokaliseDownloadBundle,
  readLokaliseConfig,
} from '../src/lib/i18n/uiStrings/lokaliseClient'
import { readArbDirectory } from '../src/lib/i18n/uiStrings/arbReader'
import { extractArbToDb } from '../src/lib/i18n/uiStrings/extractor'

/**
 * CLI : `npm run i18n:lokalise:pull`
 *
 * Demande à Lokalise un bundle ARB (toutes locales), le télécharge, le
 * décompresse, puis applique `extractArbToDb` avec `source='lokalise_pull'`.
 *
 * Idempotence : la fonction d'extraction préserve les overrides admin
 * (cf. `extractor.ts`) — ici, le pull amène les nouvelles traductions venant
 * de Lokalise comme nouveau **sourceText** ou nouveau **value DRAFT** selon
 * que l'admin a déjà customisé ou non.
 *
 * **Décompression** : on utilise la commande `unzip` du système (présente
 * sur macOS / Linux par défaut). Sur Windows, installer `unzip.exe`.
 *
 * Mode opt-in : si Lokalise n'est pas configuré → exit 0 silencieux.
 */
async function main() {
  const cfg = readLokaliseConfig()
  if (!cfg) {
    console.warn(
      '[i18n:lokalise:pull] LOKALISE_API_TOKEN / LOKALISE_PROJECT_ID not set — skipping.',
    )
    process.exit(0)
  }

  console.log('[i18n:lokalise:pull] requesting bundle…')
  const { bundleUrl } = await lokaliseDownloadBundle(cfg)
  console.log(`[i18n:lokalise:pull] bundle URL = ${bundleUrl}`)

  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arquantix-lokalise-'))
  const zipPath = path.join(tmpDir, 'bundle.zip')
  const extractDir = path.join(tmpDir, 'extracted')
  await fs.mkdir(extractDir, { recursive: true })

  try {
    /// Téléchargement du ZIP via fetch global (Node 20+).
    const res = await fetch(bundleUrl)
    if (!res.ok) {
      throw new Error(`Download failed: HTTP ${res.status}`)
    }
    const buf = Buffer.from(await res.arrayBuffer())
    await fs.writeFile(zipPath, buf)
    console.log(`[i18n:lokalise:pull] downloaded ${buf.byteLength} bytes`)

    /// Décompression. `unzip -o` overwrite, pas de prompt.
    try {
      execFileSync('unzip', ['-o', '-q', zipPath, '-d', extractDir], {
        stdio: 'inherit',
      })
    } catch (err) {
      throw new Error(
        `unzip failed (${(err as Error).message}). On Windows, install 'unzip.exe' or use WSL.`,
      )
    }

    /// On lit le dossier extrait. Lokalise crée des fichiers `app_<lang>.arb`
    /// (pattern défini par `bundle_structure` dans `lokaliseDownloadBundle`).
    /// Si Lokalise a généré des sous-dossiers (rare avec `original_filenames=false`),
    /// on cherche récursivement les .arb.
    const arbs = await readArbDirectory(extractDir).catch(async () => {
      const allFiles = await listFilesRecursive(extractDir)
      const arbCandidates = allFiles.filter((f) => f.endsWith('.arb'))
      if (arbCandidates.length === 0) {
        throw new Error(`No .arb files found in extracted bundle ${extractDir}.`)
      }
      const cleanDir = path.join(tmpDir, 'flat')
      await fs.mkdir(cleanDir, { recursive: true })
      for (const f of arbCandidates) {
        await fs.copyFile(f, path.join(cleanDir, path.basename(f)))
      }
      return readArbDirectory(cleanDir)
    })

    if (arbs.length === 0) {
      throw new Error('Lokalise bundle is empty.')
    }

    const prisma = new PrismaClient()
    try {
      const settings = await prisma.appSettings.findUnique({ where: { id: 'default' } })
      const defaultLocale = (settings?.defaultLocale ?? 'en').trim()
      const stats = await extractArbToDb(prisma, arbs, {
        defaultLocale,
        source: 'lokalise_pull',
        strictKeys: false,
      })
      console.log('[i18n:lokalise:pull] done:')
      console.log(`  totalKeys      : ${stats.totalKeys}`)
      console.log(`  created (DRAFT): ${stats.created}`)
      console.log(`  updatedFull    : ${stats.updatedFull}`)
      console.log(`  updatedMetaOnly: ${stats.updatedMetaOnly}`)
    } finally {
      await prisma.$disconnect()
    }
  } finally {
    await fs.rm(tmpDir, { recursive: true, force: true })
  }
}

async function listFilesRecursive(dir: string): Promise<string[]> {
  const out: string[] = []
  const entries = await fs.readdir(dir, { withFileTypes: true })
  for (const e of entries) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) {
      out.push(...(await listFilesRecursive(p)))
    } else if (e.isFile()) {
      out.push(p)
    }
  }
  return out
}

main().catch((err) => {
  console.error('[i18n:lokalise:pull] fatal:', err)
  process.exit(1)
})
