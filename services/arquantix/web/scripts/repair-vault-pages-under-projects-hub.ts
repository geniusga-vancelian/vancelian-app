/**
 * Rattache les pages `vault_builder` orphelines (ou mal parentées) sous le hub « projects ».
 * Corrige l’avertissement « offre vault à la racine » (ex. bali-melasti).
 *
 * Usage: npx tsx scripts/repair-vault-pages-under-projects-hub.ts
 *
 * Utilise le même .env que `npm run dev` (DATABASE_URL).
 */

import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { PrismaClient } from '@prisma/client'
import { repairVaultPagesUnderProjectsHub } from '../src/lib/admin/projectsHubAttachment'

function loadWebEnvFromCwd() {
  const root = process.cwd()
  for (const file of ['.env', '.env.local'] as const) {
    const p = join(root, file)
    if (!existsSync(p)) continue
    const text = readFileSync(p, 'utf8')
    for (const line of text.split('\n')) {
      let t = line.trim()
      if (!t || t.startsWith('#')) continue
      if (t.startsWith('export ')) t = t.slice(7).trim()
      const eq = t.indexOf('=')
      if (eq === -1) continue
      const key = t.slice(0, eq).trim()
      if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue
      let v = t.slice(eq + 1).trim()
      if (
        (v.startsWith('"') && v.endsWith('"')) ||
        (v.startsWith("'") && v.endsWith("'"))
      ) {
        v = v.slice(1, -1)
      }
      process.env[key] = v
    }
  }
}
loadWebEnvFromCwd()

const prisma = new PrismaClient()

async function main() {
  console.log('🔧 Rattachement des vaults sous le hub « projects »…')
  const result = await repairVaultPagesUnderProjectsHub(prisma)
  if ('error' in result) {
    console.error('❌', result.error)
    process.exit(1)
  }
  console.log(`✅ Hub id: ${result.hubId}`)
  console.log(`✅ Pages mises à jour: ${result.updatedCount}`)
  if (result.updatedCount === 0) {
    console.log('   (Aucun changement — tout était déjà cohérent.)')
  }
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
