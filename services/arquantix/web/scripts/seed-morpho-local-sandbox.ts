/**
 * Seed local Morpho sandbox : vaults publiés, registry, wallet mock, position initiale.
 *
 * Prérequis : DATABASE_URL, MORPHO_LOCAL_SANDBOX_ENABLED=true (pour tester l’UI ensuite).
 *
 * Usage :
 *   npm run morpho:seed-local
 *   MORPHO_LOCAL_SANDBOX_PERSON_ID=<uuid> npm run morpho:seed-local
 *   MORPHO_LOCAL_SANDBOX_PERSON_EMAIL=you@example.com npm run morpho:seed-local
 *
 * Alternative UI : http://localhost:3000/dev/morpho-sandbox → « Seed my current user »
 */
import { PrismaClient } from '@prisma/client'

import { MORPHO_LOCAL_SANDBOX_PERSON_EMAIL } from '../src/lib/portal/morphoLocalSandboxConfig'
import {
  seedMorphoSandboxForPerson,
  upsertMorphoSandboxRegistry,
  upsertMorphoSandboxVaultConfigs,
} from '../src/lib/portal/morphoLocalSandboxDev'

const prisma = new PrismaClient()

async function resolveTargetPersonId(): Promise<string | null> {
  const fromEnv = process.env.MORPHO_LOCAL_SANDBOX_PERSON_ID?.trim()
  if (fromEnv) {
    const person = await prisma.persons.findUnique({ where: { id: fromEnv }, select: { id: true } })
    if (person) return person.id
    console.warn(`[morpho:seed-local] person introuvable pour MORPHO_LOCAL_SANDBOX_PERSON_ID=${fromEnv}`)
  }

  const email = (process.env.MORPHO_LOCAL_SANDBOX_PERSON_EMAIL || MORPHO_LOCAL_SANDBOX_PERSON_EMAIL)
    .trim()
    .toLowerCase()
  const client = await prisma.peClients.findFirst({
    where: { email },
    select: { personId: true },
  })
  if (client) return client.personId

  return null
}

async function main() {
  const configIds = await upsertMorphoSandboxVaultConfigs()
  const registryEntries = await upsertMorphoSandboxRegistry(configIds)
  console.log(`[morpho:seed-local] vault configs=${configIds.size} registry=${registryEntries}`)

  const personId = await resolveTargetPersonId()
  if (personId) {
    const result = await seedMorphoSandboxForPerson({ personId, withInitialPosition: true })
    console.log(`[morpho:seed-local] demo user=${result.personId} wallet=${result.walletAddress}`)
    console.log(
      `[morpho:seed-local] position initiale ~90 USDC + ${result.historicalTransactions} tx historiques`,
    )
  } else {
    console.log(
      '[morpho:seed-local] aucune personne cible — vaults/registry OK. ' +
        'Utilisez /dev/morpho-sandbox après login, ou MORPHO_LOCAL_SANDBOX_PERSON_ID.',
    )
  }

  console.log('[morpho:seed-local] done')
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
