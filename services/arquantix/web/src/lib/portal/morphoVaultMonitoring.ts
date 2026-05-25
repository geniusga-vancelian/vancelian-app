import type { MorphoReconciliationStatus } from '@prisma/client'

import { checkBaseRpcHealth, type BaseRpcHealthSnapshot } from '@/lib/blockchain/baseRpcProvider'
import {
  getMorphoAlertMismatchToleranceRaw,
  getMorphoReconciliationToleranceRaw,
} from '@/lib/portal/morphoReconciliationConfig'
import { MORPHO_GRAPHQL_URL } from '@/lib/portal/morphoConstants'
import { isMorphoLocalSandboxEnabled } from '@/lib/portal/morphoLocalSandboxConfig'
import { getSandboxDependencyHealth } from '@/lib/portal/mocks/morphoLocalSandbox'

function absBigInt(value: bigint): bigint {
  return value < BigInt(0) ? -value : value
}

/** Compare ledger vs on-chain avec tolérance configurable. */
export function compareMorphoReconciliationAssets(args: {
  ledgerAssetsRaw: string | null
  onchainAssetsRaw: string | null
  toleranceRaw?: bigint
}): MorphoReconciliationStatus {
  const tolerance = args.toleranceRaw ?? getMorphoReconciliationToleranceRaw()
  const ledger = BigInt(args.ledgerAssetsRaw || '0')
  const onchain = BigInt(args.onchainAssetsRaw || '0')

  if (ledger === BigInt(0) && onchain === BigInt(0)) return 'matched'
  if (ledger > BigInt(0) && onchain === BigInt(0)) return 'missing_onchain'
  if (ledger === BigInt(0) && onchain > BigInt(0)) return 'missing_ledger'
  if (absBigInt(ledger - onchain) <= tolerance) return 'matched'
  return 'mismatch'
}

export function isSignificantMismatchDelta(deltaAssetsRaw: string | null | undefined): boolean {
  if (!deltaAssetsRaw) return false
  return absBigInt(BigInt(deltaAssetsRaw)) > getMorphoAlertMismatchToleranceRaw()
}

export type MorphoDependencyHealth = {
  morphoGraphql: { ok: boolean; latencyMs?: number; error?: string }
  baseRpc: BaseRpcHealthSnapshot & { ok: boolean; latencyMs?: number; error?: string }
}

/** Ping Morpho GraphQL + RPC Base. */
export async function checkMorphoDependencyHealth(): Promise<MorphoDependencyHealth> {
  if (isMorphoLocalSandboxEnabled()) {
    return getSandboxDependencyHealth()
  }

  const startedGraphql = Date.now()
  let morphoGraphql: MorphoDependencyHealth['morphoGraphql']
  try {
    const res = await fetch(MORPHO_GRAPHQL_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ query: '{ __typename }' }),
      cache: 'no-store',
      signal: AbortSignal.timeout(8_000),
    })
    if (!res.ok) {
      morphoGraphql = { ok: false, error: `HTTP ${res.status}` }
    } else {
      morphoGraphql = { ok: true, latencyMs: Date.now() - startedGraphql }
    }
  } catch (error) {
    morphoGraphql = {
      ok: false,
      error: error instanceof Error ? error.message : 'GraphQL indisponible',
    }
  }

  const startedRpc = Date.now()
  const baseRpcSnapshot = await checkBaseRpcHealth({ side: 'server' })
  const baseRpc: MorphoDependencyHealth['baseRpc'] = {
    ...baseRpcSnapshot,
    ok: baseRpcSnapshot.ok,
    latencyMs: baseRpcSnapshot.latencyMs ?? Date.now() - startedRpc,
    error: baseRpcSnapshot.error,
  }

  return { morphoGraphql, baseRpc }
}

export type MorphoAlertLevel = 'info' | 'warning' | 'critical'

export type MorphoGlobalStatus = 'healthy' | 'warning' | 'critical'

export type MorphoAlert = {
  code: string
  level: MorphoAlertLevel
  message: string
  count?: number
}

export function computeMorphoGlobalStatus(alerts: MorphoAlert[]): MorphoGlobalStatus {
  if (alerts.some((alert) => alert.level === 'critical')) return 'critical'
  if (alerts.some((alert) => alert.level === 'warning')) return 'warning'
  return 'healthy'
}

export function buildMorphoMonitoringAlerts(args: {
  pendingTransactionsCount: number
  pendingThresholdMinutes: number
  mismatchCount: number
  significantMismatchCount: number
  missingOnchainCount: number
  missingLedgerCount: number
  inactiveRegistryVaultsCount: number
  dependencyHealth: MorphoDependencyHealth
}): MorphoAlert[] {
  const alerts: MorphoAlert[] = []

  if (!args.dependencyHealth.morphoGraphql.ok) {
    alerts.push({
      code: 'morpho_graphql_unavailable',
      level: 'critical',
      message: `Morpho GraphQL indisponible : ${args.dependencyHealth.morphoGraphql.error ?? 'erreur inconnue'}`,
    })
  }

  if (!args.dependencyHealth.baseRpc.ok) {
    alerts.push({
      code: 'base_rpc_unavailable',
      level: 'critical',
      message: `RPC Base indisponible : ${args.dependencyHealth.baseRpc.error ?? 'erreur inconnue'}`,
    })
  } else if (args.dependencyHealth.baseRpc.publicRpcAsPrimary) {
    alerts.push({
      code: 'base_rpc_public_primary',
      level: 'critical',
      message: 'RPC public Base utilisé comme provider principal — configurer BASE_RPC_URL_PRIMARY (Alchemy/QuickNode).',
    })
  } else if (args.dependencyHealth.baseRpc.usedFallback) {
    alerts.push({
      code: 'base_rpc_failover',
      level: 'warning',
      message: `Failover RPC Base actif (provider : ${args.dependencyHealth.baseRpc.activeProvider ?? 'fallback'})`,
    })
  }

  if (args.pendingTransactionsCount > 0) {
    alerts.push({
      code: 'pending_tx_stale',
      level: args.pendingTransactionsCount >= 3 ? 'critical' : 'warning',
      message: `${args.pendingTransactionsCount} transaction(s) pending depuis plus de ${args.pendingThresholdMinutes} min`,
      count: args.pendingTransactionsCount,
    })
  }

  if (args.significantMismatchCount > 0) {
    alerts.push({
      code: 'reconciliation_mismatch_significant',
      level: 'critical',
      message: `${args.significantMismatchCount} mismatch(es) > seuil USDC`,
      count: args.significantMismatchCount,
    })
  } else if (args.mismatchCount > 0) {
    alerts.push({
      code: 'reconciliation_mismatch_minor',
      level: 'warning',
      message: `${args.mismatchCount} mismatch(es) dans la tolérance`,
      count: args.mismatchCount,
    })
  }

  if (args.missingOnchainCount > 0) {
    alerts.push({
      code: 'missing_onchain',
      level: 'warning',
      message: `${args.missingOnchainCount} position(s) ledger sans équivalent on-chain`,
      count: args.missingOnchainCount,
    })
  }

  if (args.missingLedgerCount > 0) {
    alerts.push({
      code: 'missing_ledger',
      level: 'warning',
      message: `${args.missingLedgerCount} position(s) on-chain sans ledger`,
      count: args.missingLedgerCount,
    })
  }

  if (args.inactiveRegistryVaultsCount > 0) {
    alerts.push({
      code: 'registry_vault_inactive',
      level: 'warning',
      message: `${args.inactiveRegistryVaultsCount} vault(s) publié(s) absent(s) ou inactif(s) dans le registry`,
      count: args.inactiveRegistryVaultsCount,
    })
  }

  return alerts
}
