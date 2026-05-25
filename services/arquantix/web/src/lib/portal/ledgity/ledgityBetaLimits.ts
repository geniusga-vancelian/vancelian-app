import { prisma } from '@/lib/prisma'
import { normalizeVaultAddress } from '@/lib/portal/ledgity/ledgityConstants'
import { LedgityVaultBetaError } from '@/lib/portal/ledgity/ledgityBetaAccess'
import { getLedgityBetaLimits, isLedgityBetaEnabled } from '@/lib/portal/ledgity/ledgityConfig'
import { parseHumanAmountToRaw } from '@/lib/portal/ledgity/ledgityVaultFormat'
import { listPublishedPortalLedgityVaultConfigs } from '@/lib/portal/ledgity/ledgityVaultConfigStore'

function logLedgitySupportEvent(event: {
  code: string
  level: 'warning' | 'critical'
  message: string
  personId?: string
  metadata?: Record<string, unknown>
}): void {
  const payload = {
    ts: new Date().toISOString(),
    service: 'arquantix-web',
    component: 'ledgity_vault',
    ...event,
  }
  const line = JSON.stringify(payload)
  if (event.level === 'critical') {
    console.error('[ledgity:support]', line)
    return
  }
  console.warn('[ledgity:support]', line)
}

function limitCode(suffix: string): string {
  return isLedgityBetaEnabled() ? `ledgity.beta.${suffix}` : `ledgity.${suffix}`
}

function formatStablecoinAmount(raw: bigint, decimals = 6): string {
  return `${Number(raw) / 10 ** decimals} USDC/EURC`
}

async function publishedVaultAddresses(): Promise<string[]> {
  const configs = await listPublishedPortalLedgityVaultConfigs()
  return configs.map((row) => normalizeVaultAddress(row.vaultAddress))
}

export async function loadLedgityUserExposureRaw(personId: string): Promise<bigint> {
  const vaults = await publishedVaultAddresses()
  if (vaults.length === 0) return BigInt(0)

  const rows = await prisma.userVaultPosition.findMany({
    where: { personId, vaultAddress: { in: vaults } },
    select: { lastAssetsRaw: true },
  })

  return rows.reduce((sum, row) => sum + BigInt(row.lastAssetsRaw || '0'), BigInt(0))
}

export async function loadLedgityGlobalExposureRaw(): Promise<bigint> {
  const vaults = await publishedVaultAddresses()
  if (vaults.length === 0) return BigInt(0)

  const rows = await prisma.userVaultPosition.findMany({
    where: { vaultAddress: { in: vaults } },
    select: { lastAssetsRaw: true },
  })

  return rows.reduce((sum, row) => sum + BigInt(row.lastAssetsRaw || '0'), BigInt(0))
}

/** Valide les plafonds live pour un dépôt (actifs avec ou sans mode beta). */
export async function assertLedgityDepositLimits(args: {
  personId: string
  amount: string
  assetDecimals?: number
}): Promise<bigint> {
  const limits = getLedgityBetaLimits()
  const decimals = args.assetDecimals ?? limits.assetDecimals
  const amountRaw = parseHumanAmountToRaw(args.amount, decimals)

  if (amountRaw < limits.minDepositRaw) {
    throw new LedgityVaultBetaError(
      limitCode('deposit_below_min'),
      `Dépôt minimum : ${formatStablecoinAmount(limits.minDepositRaw, decimals)}.`,
    )
  }

  if (amountRaw > limits.maxDepositRaw) {
    logLedgitySupportEvent({
      code: limitCode('deposit_above_max'),
      level: 'warning',
      message: 'Tentative de dépôt au-dessus du plafond par transaction.',
      personId: args.personId,
      metadata: { amountRaw: amountRaw.toString(), maxDepositRaw: limits.maxDepositRaw.toString() },
    })
    throw new LedgityVaultBetaError(
      limitCode('deposit_above_max'),
      `Dépôt maximum par transaction : ${formatStablecoinAmount(limits.maxDepositRaw, decimals)}.`,
    )
  }

  const [userExposure, globalExposure] = await Promise.all([
    loadLedgityUserExposureRaw(args.personId),
    loadLedgityGlobalExposureRaw(),
  ])

  if (userExposure + amountRaw > limits.maxUserExposureRaw) {
    logLedgitySupportEvent({
      code: limitCode('user_exposure_exceeded'),
      level: 'warning',
      message: 'Exposition utilisateur dépassée.',
      personId: args.personId,
      metadata: {
        userExposure: userExposure.toString(),
        amountRaw: amountRaw.toString(),
        maxUserExposureRaw: limits.maxUserExposureRaw.toString(),
      },
    })
    throw new LedgityVaultBetaError(
      limitCode('user_exposure_exceeded'),
      `Exposition maximum : ${formatStablecoinAmount(limits.maxUserExposureRaw, decimals)} par utilisateur.`,
    )
  }

  if (globalExposure + amountRaw > limits.maxGlobalExposureRaw) {
    logLedgitySupportEvent({
      code: limitCode('global_exposure_exceeded'),
      level: 'critical',
      message: 'Cap global Ledgity atteint.',
      metadata: {
        globalExposure: globalExposure.toString(),
        amountRaw: amountRaw.toString(),
        maxGlobalExposureRaw: limits.maxGlobalExposureRaw.toString(),
      },
    })
    throw new LedgityVaultBetaError(
      limitCode('global_exposure_exceeded'),
      'Capacité globale atteinte. Réessayez plus tard ou contactez le support.',
      503,
    )
  }

  return amountRaw
}

/** @deprecated Alias — préférer assertLedgityDepositLimits */
export const assertLedgityBetaDepositLimits = assertLedgityDepositLimits
