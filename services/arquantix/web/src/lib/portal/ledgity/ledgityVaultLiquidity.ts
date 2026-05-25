import type { Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { LEDGITY_CHAIN_ID } from '@/lib/portal/ledgity/ledgityConstants'
import { isLedgityLocalSandboxEnabled } from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import { getLedgityLocalSandboxPricePerShare } from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import { LEDGITY_ERC4626_ABI } from '@/lib/portal/ledgity/ledgityVaultAbi'

export class LedgityVaultLiquidityError extends Error {
  readonly code = 'ledgity.withdraw_liquidity_insufficient'
  readonly status = 422

  constructor(
    message = 'La liquidité disponible du vault ne permet pas un retrait instantané complet. Veuillez réessayer plus tard.',
  ) {
    super(message)
    this.name = 'LedgityVaultLiquidityError'
  }
}

export type LedgityWithdrawLiquiditySnapshot = {
  maxWithdrawRaw: bigint
  maxRedeemRaw: bigint
  totalAssetsRaw: bigint
  sharesRaw: bigint
  assetsFromSharesRaw: bigint
  previewRedeemRaw: bigint | null
  pricePerShare: number | null
}

function getBasePublicClient() {
  return createBasePublicClient({ side: 'server' })
}

/** Lit maxWithdraw / maxRedeem / previewRedeem pour un wallet sur un vault Ledgity. */
export async function readLedgityWithdrawLiquidity(args: {
  vaultAddress: string
  walletAddress: string
  chainId?: number
}): Promise<LedgityWithdrawLiquiditySnapshot | null> {
  const chainId = args.chainId ?? LEDGITY_CHAIN_ID
  if (chainId !== LEDGITY_CHAIN_ID) return null

  if (isLedgityLocalSandboxEnabled()) {
    const sharesRaw = BigInt(0)
    return {
      maxWithdrawRaw: BigInt(10_000_000_000),
      maxRedeemRaw: BigInt(10_000_000_000),
      totalAssetsRaw: BigInt(10_000_000_000),
      sharesRaw,
      assetsFromSharesRaw: BigInt(0),
      previewRedeemRaw: BigInt(0),
      pricePerShare: getLedgityLocalSandboxPricePerShare(),
    }
  }

  const vaultAddress = args.vaultAddress as Address
  const walletAddress = args.walletAddress as Address
  const client = getBasePublicClient()

  try {
    const sharesRaw = (await client.readContract({
      address: vaultAddress,
      abi: LEDGITY_ERC4626_ABI,
      functionName: 'balanceOf',
      args: [walletAddress],
    })) as bigint

    const [maxWithdrawRaw, maxRedeemRaw, totalAssetsRaw, assetsFromSharesRaw] = await Promise.all([
      client.readContract({
        address: vaultAddress,
        abi: LEDGITY_ERC4626_ABI,
        functionName: 'maxWithdraw',
        args: [walletAddress],
      }) as Promise<bigint>,
      client.readContract({
        address: vaultAddress,
        abi: LEDGITY_ERC4626_ABI,
        functionName: 'maxRedeem',
        args: [walletAddress],
      }) as Promise<bigint>,
      client.readContract({
        address: vaultAddress,
        abi: LEDGITY_ERC4626_ABI,
        functionName: 'totalAssets',
      }) as Promise<bigint>,
      sharesRaw > BigInt(0)
        ? (client.readContract({
            address: vaultAddress,
            abi: LEDGITY_ERC4626_ABI,
            functionName: 'convertToAssets',
            args: [sharesRaw],
          }) as Promise<bigint>)
        : Promise.resolve(BigInt(0)),
    ])

    let previewRedeemRaw: bigint | null = null
    if (sharesRaw > BigInt(0)) {
      previewRedeemRaw = (await client.readContract({
        address: vaultAddress,
        abi: LEDGITY_ERC4626_ABI,
        functionName: 'previewRedeem',
        args: [sharesRaw],
      })) as bigint
    }

    const oneShare = BigInt(10) ** BigInt(18)
    let pricePerShare: number | null = null
    if (oneShare > BigInt(0)) {
      const assetsForOneShare = (await client.readContract({
        address: vaultAddress,
        abi: LEDGITY_ERC4626_ABI,
        functionName: 'convertToAssets',
        args: [oneShare],
      })) as bigint
      const pps = Number(assetsForOneShare) / Number(oneShare) / 1e6
      pricePerShare = Number.isFinite(pps) && pps > 0 ? pps : null
    }

    return {
      maxWithdrawRaw,
      maxRedeemRaw,
      totalAssetsRaw,
      sharesRaw,
      assetsFromSharesRaw,
      previewRedeemRaw,
      pricePerShare,
    }
  } catch (error) {
    console.error('[ledgityVaultLiquidity] readLedgityWithdrawLiquidity failed', {
      vaultAddress: args.vaultAddress,
      walletAddress: args.walletAddress,
      error,
    })
    return null
  }
}

/** Bloque un retrait live si maxWithdraw < montant demandé. */
export async function assertLedgityWithdrawLiquidity(args: {
  vaultAddress: string
  walletAddress: string
  requestedAmountRaw: bigint
  chainId?: number
}): Promise<void> {
  if (args.requestedAmountRaw <= BigInt(0)) return

  const snapshot = await readLedgityWithdrawLiquidity(args)
  if (!snapshot) {
    throw new LedgityVaultLiquidityError(
      'Impossible de vérifier la liquidité du vault. Veuillez réessayer plus tard.',
    )
  }

  if (snapshot.maxWithdrawRaw < args.requestedAmountRaw) {
    throw new LedgityVaultLiquidityError()
  }
}

export type LedgityVaultLiquidityMetrics = {
  totalAssetsRaw: bigint
  pricePerShare: number | null
  paused: boolean | null
  withdrawalsPaused: boolean | null
}

/** Métriques vault-level pour monitoring admin (sans filtre LEDGITY_VAULTS_ENABLED). */
export async function readLedgityVaultLiquidityMetrics(args: {
  vaultAddress: string
  chainId?: number
}): Promise<LedgityVaultLiquidityMetrics | null> {
  const chainId = args.chainId ?? LEDGITY_CHAIN_ID
  if (chainId !== LEDGITY_CHAIN_ID) return null

  if (isLedgityLocalSandboxEnabled()) {
    return {
      totalAssetsRaw: BigInt(12_400_000_000_000),
      pricePerShare: getLedgityLocalSandboxPricePerShare(),
      paused: false,
      withdrawalsPaused: false,
    }
  }

  const vaultAddress = args.vaultAddress as Address
  const client = getBasePublicClient()

  try {
    const totalAssetsRaw = (await client.readContract({
      address: vaultAddress,
      abi: LEDGITY_ERC4626_ABI,
      functionName: 'totalAssets',
    })) as bigint

    const oneShare = BigInt(10) ** BigInt(18)
    const assetsForOneShare = (await client.readContract({
      address: vaultAddress,
      abi: LEDGITY_ERC4626_ABI,
      functionName: 'convertToAssets',
      args: [oneShare],
    })) as bigint
    const pps = Number(assetsForOneShare) / Number(oneShare) / 1e6
    const pricePerShare = Number.isFinite(pps) && pps > 0 ? pps : null

    let paused: boolean | null = null
    try {
      paused = (await client.readContract({
        address: vaultAddress,
        abi: LEDGITY_ERC4626_ABI,
        functionName: 'paused',
      })) as boolean
    } catch {
      paused = null
    }

    return {
      totalAssetsRaw,
      pricePerShare,
      paused,
      withdrawalsPaused: paused,
    }
  } catch (error) {
    console.error('[ledgityVaultLiquidity] readLedgityVaultLiquidityMetrics failed', {
      vaultAddress: args.vaultAddress,
      error,
    })
    return null
  }
}
