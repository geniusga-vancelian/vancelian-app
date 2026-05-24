import { prisma } from '@/lib/prisma'
import { listPublishedPortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import { normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import { parseHumanAmountToRaw } from '@/lib/portal/morphoVaultFormat'
import {
  getMorphoUsdcBetaLimits,
  isMorphoUsdcBetaEnabled,
} from '@/lib/portal/morphoUsdcBetaConfig'
import { MorphoVaultBetaError } from '@/lib/portal/morphoUsdcBetaAccess'
import { logMorphoSupportEvent } from '@/lib/portal/morphoBetaSupportLog'

async function publishedVaultAddresses(): Promise<string[]> {
  const configs = await listPublishedPortalMorphoVaultConfigs()
  return configs.map((row) => normalizeVaultAddress(row.vaultAddress))
}

export async function loadMorphoUserExposureRaw(personId: string): Promise<bigint> {
  const vaults = await publishedVaultAddresses()
  if (vaults.length === 0) return BigInt(0)

  const rows = await prisma.userVaultPosition.findMany({
    where: { personId, vaultAddress: { in: vaults } },
    select: { lastAssetsRaw: true },
  })

  return rows.reduce((sum, row) => sum + BigInt(row.lastAssetsRaw || '0'), BigInt(0))
}

export async function loadMorphoGlobalExposureRaw(): Promise<bigint> {
  const vaults = await publishedVaultAddresses()
  if (vaults.length === 0) return BigInt(0)

  const rows = await prisma.userVaultPosition.findMany({
    where: { vaultAddress: { in: vaults } },
    select: { lastAssetsRaw: true },
  })

  return rows.reduce((sum, row) => sum + BigInt(row.lastAssetsRaw || '0'), BigInt(0))
}

/** Valide les plafonds beta pour un dépôt (no-op si beta désactivée). */
export async function assertMorphoBetaDepositLimits(args: {
  personId: string
  amount: string
  assetDecimals?: number
}): Promise<bigint> {
  if (!isMorphoUsdcBetaEnabled()) {
    return parseHumanAmountToRaw(args.amount, args.assetDecimals ?? 6)
  }

  const limits = getMorphoUsdcBetaLimits()
  const decimals = args.assetDecimals ?? limits.assetDecimals
  const amountRaw = parseHumanAmountToRaw(args.amount, decimals)

  if (amountRaw < limits.minDepositRaw) {
    throw new MorphoVaultBetaError(
      'morpho.beta.deposit_below_min',
      `Dépôt minimum beta : ${Number(limits.minDepositRaw) / 1_000_000} USDC.`,
    )
  }

  if (amountRaw > limits.maxDepositRaw) {
    logMorphoSupportEvent({
      code: 'morpho.beta_limit_exceeded',
      level: 'warning',
      message: 'Tentative de dépôt au-dessus du plafond beta par transaction.',
      personId: args.personId,
      metadata: { amountRaw: amountRaw.toString(), maxDepositRaw: limits.maxDepositRaw.toString() },
    })
    throw new MorphoVaultBetaError(
      'morpho.beta.deposit_above_max',
      `Dépôt maximum par transaction : ${Number(limits.maxDepositRaw) / 1_000_000} USDC.`,
    )
  }

  const [userExposure, globalExposure] = await Promise.all([
    loadMorphoUserExposureRaw(args.personId),
    loadMorphoGlobalExposureRaw(),
  ])

  if (userExposure + amountRaw > limits.maxUserExposureRaw) {
    logMorphoSupportEvent({
      code: 'morpho.beta_limit_exceeded',
      level: 'warning',
      message: 'Exposition utilisateur beta dépassée.',
      personId: args.personId,
      metadata: {
        userExposure: userExposure.toString(),
        amountRaw: amountRaw.toString(),
        maxUserExposureRaw: limits.maxUserExposureRaw.toString(),
      },
    })
    throw new MorphoVaultBetaError(
      'morpho.beta.user_exposure_exceeded',
      `Exposition maximum beta : ${Number(limits.maxUserExposureRaw) / 1_000_000} USDC par utilisateur.`,
    )
  }

  if (globalExposure + amountRaw > limits.maxGlobalExposureRaw) {
    logMorphoSupportEvent({
      code: 'morpho.beta_limit_exceeded',
      level: 'critical',
      message: 'Cap global beta Morpho USDC atteint.',
      metadata: {
        globalExposure: globalExposure.toString(),
        amountRaw: amountRaw.toString(),
        maxGlobalExposureRaw: limits.maxGlobalExposureRaw.toString(),
      },
    })
    throw new MorphoVaultBetaError(
      'morpho.beta.global_exposure_exceeded',
      'Capacité beta globale atteinte. Réessayez plus tard ou contactez le support.',
      503,
    )
  }

  return amountRaw
}
