'use client'

import type { LombardBetaCapSnapshot } from '@/lib/portal/lombard/lombardQaContext'
import type { LombardExecutionFailureView } from '@/lib/portal/lombard/lombardExecutionError'
import type { LombardExecutionPhase, LombardQuoteResult } from '@/lib/portal/lombard/lombardTypes'

type Props = {
  marketId: string | null
  walletAddress: string | null
  quote: LombardQuoteResult | null
  maxUserLtvPercent: number | null
  betaCaps: LombardBetaCapSnapshot | null
  executionPhase: LombardExecutionPhase
  ledgerGroupId: string | null
  executionFailure?: LombardExecutionFailureView | null
  mockMode?: boolean
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-2 text-[11px]">
      <span className="text-v-muted">{label}</span>
      <span className="break-all font-mono text-v-fg">{value}</span>
    </div>
  )
}

export function PortalLombardQaDebugPanel({
  marketId,
  walletAddress,
  quote,
  maxUserLtvPercent,
  betaCaps,
  executionPhase,
  ledgerGroupId,
  executionFailure,
  mockMode,
}: Props) {
  const warnings = quote?.warnings?.length
    ? quote.warnings.map((row) => `${row.code} (${row.projectedLtvPercent}%)`).join('; ')
    : null

  return (
    <aside
      className="rounded-xl border border-dashed border-amber-500/40 bg-amber-500/5 p-4 font-ui"
      aria-label="Lombard QA debug"
    >
      <p className="m-0 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
        Lombard QA debug (staff / non-prod)
      </p>
      <div className="mt-3 flex flex-col gap-1.5">
        <Row label="marketId" value={marketId ?? quote?.marketId ?? null} />
        <Row label="wallet" value={walletAddress} />
        <Row
          label="projected LTV"
          value={quote ? `${quote.projectedLtvPercent}%` : null}
        />
        <Row
          label="maxUserLtv"
          value={
            maxUserLtvPercent != null
              ? `${maxUserLtvPercent}%`
              : quote
                ? '70%'
                : null
          }
        />
        <Row
          label="Morpho LLTV"
          value={
            quote?.liquidationLltvPercent != null
              ? `${quote.liquidationLltvPercent}%`
              : null
          }
        />
        <Row label="quote warnings" value={warnings ?? 'none'} />
        <Row
          label="beta wallet cap"
          value={
            betaCaps
              ? `${betaCaps.walletRemainingUsdc} USDC remaining (${betaCaps.walletExposureUsdc} used / ${betaCaps.maxBorrowUsdcPerWallet} max)`
              : 'beta limits off'
          }
        />
        <Row
          label="beta global cap"
          value={
            betaCaps
              ? `${betaCaps.globalRemainingUsdc} USDC remaining (${betaCaps.globalExposureUsdc} used / ${betaCaps.maxTotalBorrowUsdcGlobal} max)`
              : null
          }
        />
        <Row label="mock mode" value={mockMode ? 'on (no Privy signature)' : 'off (live on-chain)'} />
        <Row label="prepare status" value={executionPhase} />
        <Row label="failed step" value={executionFailure?.stepLabel ?? null} />
        <Row label="failed tx" value={executionFailure?.txHash ?? null} />
        <Row label="ledger group" value={ledgerGroupId} />
      </div>
    </aside>
  )
}
