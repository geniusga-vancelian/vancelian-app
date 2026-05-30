'use client'

import type { ReactNode } from 'react'
import { resolveCryptoAvatarSources } from '@/lib/portal/cryptoInstrumentAssets'
import { formatEvmNetworkLabel } from '@/lib/portal/evmNetworkLabel'

export type ChainFlowAsset = {
  id: string
  sym: string
  name: string
}

export const CHAIN_FLOW_ASSETS: ChainFlowAsset[] = [
  { id: 'usdc', sym: 'USDC', name: 'USD Coin' },
  { id: 'eurc', sym: 'EURC', name: 'Euro Coin' },
  { id: 'eth', sym: 'ETH', name: 'Ethereum' },
  { id: 'usdt', sym: 'USDT', name: 'Tether' },
]

export type ChainNetworkMeta = {
  time: string
  confirmations: number
  short: string
  feeLabel?: string
}

export const CHAIN_NETWORK_META: Record<number, ChainNetworkMeta> = {
  1: { time: '≈ 3 min', confirmations: 12, short: 'ERC-20', feeLabel: '—' },
  8453: { time: '≈ 1 min', confirmations: 1, short: 'BASE', feeLabel: '—' },
  42161: { time: '≈ 1 min', confirmations: 1, short: 'ARBITRUM', feeLabel: '—' },
  137: { time: '≈ 5 min', confirmations: 128, short: 'POLYGON', feeLabel: '—' },
  10: { time: '≈ 1 min', confirmations: 1, short: 'OPTIMISM', feeLabel: '—' },
}

export function resolveChainNetworkMeta(chainId: number): ChainNetworkMeta {
  return (
    CHAIN_NETWORK_META[chainId] ?? {
      time: 'Varies',
      confirmations: 1,
      short: 'EVM',
      feeLabel: '—',
    }
  )
}

export const EVM_ADDRESS_PATTERN = /^0x[a-fA-F0-9]{40}$/

export function formatChainFlowAmount(value: number, assetId: string): string {
  const decimals = assetId === 'eth' ? 4 : 2
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function parseChainFlowAmountInput(raw: string): number {
  const normalized = raw.replace(/\s/g, '').replace(/,/g, '.')
  const parsed = Number.parseFloat(normalized)
  return Number.isFinite(parsed) ? parsed : 0
}

export function ChainFlowAssetGlyph({ sym }: { sym: string }) {
  const src = resolveCryptoAvatarSources(sym)[0]
  if (!src) return null
  return <img src={src} alt="" width={14} height={14} className="rounded-full" />
}

export function ChainFlowPill({
  active,
  onClick,
  label,
  sub,
  glyph,
  disabled,
}: {
  active: boolean
  onClick: () => void
  label: string
  sub?: string
  glyph?: ReactNode
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      className="chain-pill"
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
    >
      {glyph ? <span className="chain-pill__glyph">{glyph}</span> : null}
      <span>{label}</span>
      {sub ? <span className="chain-pill__sub">{sub}</span> : null}
    </button>
  )
}

export function chainFlowNetworkLabel(chainId: number): string {
  return formatEvmNetworkLabel(chainId)
}

export function chainFlowAddressPlaceholder(address: string, networkLabel: string): string {
  const trimmed = address.trim()
  if (trimmed.length >= 12) {
    return `${trimmed.slice(0, 6)}…${trimmed.slice(-4)} (${networkLabel} address)`
  }
  return `0x… (${networkLabel} address)`
}
