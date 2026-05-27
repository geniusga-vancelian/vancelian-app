import {
  getLombardBetaLimits,
  isLombardV1BetaLimitsEnabled,
} from '@/lib/portal/lombard/lombardBetaConfig'
import {
  loadLombardGlobalBorrowExposureRaw,
  loadLombardWalletBorrowExposureRaw,
} from '@/lib/portal/lombard/lombardBetaLimits'
import { formatLombardTokenAmount } from '@/lib/portal/lombard/lombardFormat'

export type LombardBetaCapSnapshot = {
  walletExposureUsdc: string
  walletRemainingUsdc: string
  globalExposureUsdc: string
  globalRemainingUsdc: string
  maxBorrowUsdcPerWallet: string
  maxTotalBorrowUsdcGlobal: string
}

function formatUsdcFromRaw(raw: bigint): string {
  return formatLombardTokenAmount(raw, 6)
}

export async function buildLombardBetaCapSnapshot(
  walletAddress: string,
): Promise<LombardBetaCapSnapshot | null> {
  if (!isLombardV1BetaLimitsEnabled()) return null

  const limits = getLombardBetaLimits()
  const [walletExposure, globalExposure] = await Promise.all([
    loadLombardWalletBorrowExposureRaw(walletAddress),
    loadLombardGlobalBorrowExposureRaw(),
  ])

  const walletRemaining =
    walletExposure >= limits.maxBorrowUsdcPerWalletRaw
      ? BigInt(0)
      : limits.maxBorrowUsdcPerWalletRaw - walletExposure
  const globalRemaining =
    globalExposure >= limits.maxTotalBorrowUsdcGlobalRaw
      ? BigInt(0)
      : limits.maxTotalBorrowUsdcGlobalRaw - globalExposure

  return {
    walletExposureUsdc: formatUsdcFromRaw(walletExposure),
    walletRemainingUsdc: formatUsdcFromRaw(walletRemaining),
    globalExposureUsdc: formatUsdcFromRaw(globalExposure),
    globalRemainingUsdc: formatUsdcFromRaw(globalRemaining),
    maxBorrowUsdcPerWallet: formatUsdcFromRaw(limits.maxBorrowUsdcPerWalletRaw),
    maxTotalBorrowUsdcGlobal: formatUsdcFromRaw(limits.maxTotalBorrowUsdcGlobalRaw),
  }
}
