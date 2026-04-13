/**
 * Envoie l’image locale du welcome Flutter vers R2 (même bucket que la media lib).
 *
 * Usage : cd services/arquantix/web && npx tsx scripts/upload-welcome-hero.ts
 *
 * Prérequis : .env ou .env.local avec R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME.
 * Optionnel : WELCOME_HERO_R2_KEY (défaut mobile/welcome/hero.png)
 */
import { readFileSync, existsSync } from 'fs'
import { resolve } from 'path'

function loadEnvFiles() {
  const root = resolve(__dirname, '..')
  for (const name of ['.env', '.env.local']) {
    const p = resolve(root, name)
    if (!existsSync(p)) continue
    for (const line of readFileSync(p, 'utf8').split('\n')) {
      const t = line.trim()
      if (!t || t.startsWith('#')) continue
      const i = t.indexOf('=')
      if (i < 1) continue
      const key = t.slice(0, i).trim()
      let v = t.slice(i + 1).trim()
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

async function main() {
  loadEnvFiles()

  const { uploadFile } = await import('../src/lib/storage/storageClient')

  const mobileHero = resolve(
    __dirname,
    '../../mobile/assets/welcome/hero.png',
  )
  if (!existsSync(mobileHero)) {
    console.error('Fichier introuvable :', mobileHero)
    process.exit(1)
  }

  const key = process.env.WELCOME_HERO_R2_KEY?.trim() || 'mobile/welcome/hero.png'
  const buf = readFileSync(mobileHero)

  const result = await uploadFile(buf, key, 'image/png')
  console.log('OK — clé R2 :', result.key)
  console.log('URL publique (si bucket exposé) :', result.url)
  console.log(
    '\nAjoutez si besoin dans .env :\n  WELCOME_HERO_R2_KEY=' + result.key,
  )
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
