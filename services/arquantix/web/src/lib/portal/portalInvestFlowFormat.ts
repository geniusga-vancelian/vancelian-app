import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import type { PortalLedgityVaultDetails } from '@/lib/portal/ledgity/ledgityVaultTypes'
import type { PortalMorphoVaultDetails } from '@/lib/portal/morphoVaultTypes'

const USDC_RATE_TO_EUR = 0.924
const BASE_CHAIN_ID = 8453

const VAULT_COVER_GRAD =
  'linear-gradient(160deg, #1a2840 0%, #38597d 40%, #c7d4e3 100%)'

export type PortalInvestSource = {
  key: string
  name: string
  short: string
  unit: string
  desc: string
  glyph: string
  bg: string
  color: string
  balance: number
  rateToEur: number
  balanceLabel: string
  techSource: string
}

export type PortalInvestTarget = {
  key: string
  group: string
  name: string
  short: string
  unit: string
  desc: string
  glyph: string
  bg: string
  color: string
  yieldPct: number
  pricePerPart: number
  held: string
  heldLabel: string
  tech: string
}

export function invParseAmount(raw: string | number): number {
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : 0
  let s = raw.replace(/[\s\u00A0\u202F]/g, '').trim()
  if (!s) return 0

  // en-US thousands: 10,000 or 10,000.50
  if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(s)) {
    s = s.replace(/,/g, '')
  } else {
    s = s.replace(/,/g, '.')
  }

  s = s.replace(/[^\d.]/g, '')
  const n = Number.parseFloat(s)
  return Number.isNaN(n) ? 0 : n
}

export function invFmtAmount(n: number, decimals = 0): string {
  return n.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function invFmtMoney(n: number, sym = '$'): string {
  return `${invFmtAmount(n, sym === '€' ? 2 : 0)} ${sym}`
}

export function invInEur(amount: number, source: PortalInvestSource): number {
  return amount * (source.rateToEur || 1)
}

function parseTicketAmount(label: string | null | undefined): number {
  if (!label?.trim()) return 1_000
  const cleaned = label.replace(/[^\d.,]/g, '').replace(',', '.')
  const n = Number.parseFloat(cleaned)
  return Number.isFinite(n) && n > 0 ? n : 1_000
}

function looksLikeInternalSlug(slug: string): boolean {
  return /^eo-/i.test(slug) || /^\d/.test(slug) || slug.includes('-177')
}

function vaultShortName(payload: ExclusiveOfferVaultPayload): string {
  const title = payload.heroTitle.trim()
  if (title) {
    const parts = title.split(/\s+/).filter(Boolean)
    const last = parts[parts.length - 1]
    if (last && last.length <= 24) return last
  }
  const slug = payload.pageSlug.trim()
  if (slug && !looksLikeInternalSlug(slug)) {
    return slug.charAt(0).toUpperCase() + slug.slice(1)
  }
  return 'Offer'
}

function resolveVaultYieldPct(payload: ExclusiveOfferVaultPayload): number {
  if (payload.lending?.supplyAprPct != null) {
    return payload.lending.supplyAprPct / 100
  }
  for (const row of payload.lending?.keyInformationRows ?? []) {
    if (/yield|apr|rendement/i.test(row.label)) {
      const n = Number.parseFloat(row.value.replace(/[^\d.,]/g, '').replace(',', '.'))
      if (Number.isFinite(n) && n > 0) return n / 100
    }
  }
  for (const mod of payload.contentModules) {
    if (mod.type !== 'KeyInformationModule') continue
    const rows = Array.isArray(mod.content.rows) ? mod.content.rows : []
    for (const raw of rows) {
      if (!raw || typeof raw !== 'object') continue
      const row = raw as Record<string, unknown>
      const label = typeof row.label === 'string' ? row.label : ''
      const value = typeof row.value === 'string' ? row.value : ''
      if (/yield|apr|rendement/i.test(label) && value) {
        const n = Number.parseFloat(value.replace(/[^\d.,]/g, '').replace(',', '.'))
        if (Number.isFinite(n) && n > 0) return n / 100
      }
    }
  }
  return 0
}

function vaultChipBg(payload: ExclusiveOfferVaultPayload): string {
  if (payload.headerImageUrl) {
    return `url('${payload.headerImageUrl}') center/cover no-repeat`
  }
  return VAULT_COVER_GRAD
}

function vaultTechToken(slug: string): string {
  const token = slug.replace(/[^a-z0-9]/gi, '').slice(0, 3).toUpperCase() || 'VLT'
  return `VAN-${token} (ERC-3643)`
}

/** Build invest target chip from exclusive offer vault payload. */
export function buildVaultInvestTarget(payload: ExclusiveOfferVaultPayload): PortalInvestTarget {
  const short = vaultShortName(payload)
  const yieldPct = resolveVaultYieldPct(payload)
  const aprPct = yieldPct * 100
  const pricePerPart = parseTicketAmount(payload.lending?.minTicket)
  const aprLabel =
    aprPct > 0
      ? `${aprPct.toLocaleString('en-US', {
          minimumFractionDigits: 1,
          maximumFractionDigits: 1,
        })}%/yr`
      : '—'

  return {
    key: payload.pageSlug,
    group: 'Exclusive offers',
    name: payload.heroTitle,
    short,
    unit: '0 SHARES',
    desc: [payload.heroSubtitle, aprLabel].filter(Boolean).join(' · ') || payload.pageTitle,
    glyph: short.charAt(0).toUpperCase(),
    bg: vaultChipBg(payload),
    color: '#F4F1E8',
    yieldPct,
    pricePerPart,
    held: '0 shares',
    heldLabel: 'to initiate',
    tech: vaultTechToken(payload.pageSlug),
  }
}

export function defaultInvestSources(): PortalInvestSource[] {
  return [
    {
      key: 'usdc',
      name: 'USDC',
      short: 'USDC',
      unit: 'Stablecoin · USD',
      desc: 'Circle USD stablecoin, 1 USDC = 1 $',
      glyph: '$',
      bg: '#2775CA',
      color: '#FFFFFF',
      balance: 0,
      rateToEur: USDC_RATE_TO_EUR,
      balanceLabel: 'Balance 0 USDC',
      techSource: 'USDC (Circle)',
    },
    {
      key: 'eur',
      name: 'Euros',
      short: 'Euros',
      unit: 'EUR',
      desc: 'Primary account currency',
      glyph: '€',
      bg: 'var(--v-fg)',
      color: '#FFFFFF',
      balance: 0,
      rateToEur: 1,
      balanceLabel: 'Balance €0',
      techSource: 'EURC (Circle)',
    },
  ]
}

export function mergeSourceBalance(
  sources: PortalInvestSource[],
  assetKey: string,
  balance: number,
): PortalInvestSource[] {
  return sources.map((source) => {
    if (source.key !== assetKey) return source
    if (assetKey === 'usdc') {
      return {
        ...source,
        balance,
        balanceLabel: `Balance ${invFmtAmount(balance, 2)} USDC`,
      }
    }
    return {
      ...source,
      balance,
      balanceLabel: `Balance €${invFmtAmount(balance, 2)}`,
    }
  })
}

export function computeReceivedParts(
  amountEur: number,
  target: PortalInvestTarget,
): number {
  if (target.unit === 'BASKET' || target.pricePerPart <= 1) return amountEur
  return amountEur / target.pricePerPart
}

function defiVaultShortName(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean)
  if (parts.length === 0) return 'Vault'
  const last = parts[parts.length - 1]!
  if (/^ly?[A-Z]{2,5}$/i.test(last) || last.length <= 8) return last
  return parts.slice(0, 2).join(' ')
}

function formatApyFromBps(bps: number | null): string {
  if (bps == null || bps <= 0) return 'Variable APY'
  const pct = bps / 100
  return `${pct.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}% APY`
}

/** Parse on-chain vault balance (raw integer string) to a JS number. */
export function parseVaultPositionAmount(raw: string, decimals: number): number {
  if (!raw || raw === '0') return 0
  try {
    const value = BigInt(raw)
    const base = BigInt(10) ** BigInt(decimals)
    const whole = value / base
    const fraction = value % base
    if (fraction === BigInt(0)) return Number(whole)
    const fracStr = fraction.toString().padStart(decimals, '0').replace(/0+$/, '')
    return Number.parseFloat(`${whole}.${fracStr}`)
  } catch {
    return 0
  }
}

/** EURC spendable balance mapped to the Euros invest source. */
export function resolveEurcBalance(
  positions: Array<{
    asset: string
    balance?: number
    availableBalance?: number
  }>,
): number {
  for (const row of positions) {
    if (row.asset.trim().toUpperCase() === 'EURC') {
      return row.availableBalance ?? row.balance ?? 0
    }
  }
  return 0
}

/** USDC spendable on Base for DeFi deposit max. */
export function resolveBaseUsdcBalance(
  positions: Array<{
    asset: string
    balance?: number
    availableBalance?: number
    onChainBalance?: number
    chainId?: number | null
  }>,
): number {
  for (const row of positions) {
    if (row.asset.trim().toUpperCase() !== 'USDC') continue
    if (row.chainId != null && row.chainId !== BASE_CHAIN_ID) continue
    return row.onChainBalance ?? row.availableBalance ?? row.balance ?? 0
  }
  for (const row of positions) {
    if (row.asset.trim().toUpperCase() === 'USDC') {
      return row.onChainBalance ?? row.availableBalance ?? row.balance ?? 0
    }
  }
  return 0
}

/**
 * USDC max investissable en vault Morpho/Ledgity — trading_available PE uniquement.
 * N'utilise pas le solde Privy fusionné ni on_chain_balance.
 */
export function resolveVaultDepositUsdcBalance(
  positions: Array<{
    asset: string
    balance?: number
    availableBalance?: number
    platformBalance?: number
    tradingAvailable?: number
    chainId?: number | null
  }>,
): number {
  for (const row of positions) {
    if (row.asset.trim().toUpperCase() !== 'USDC') continue
    if (row.chainId != null && row.chainId !== BASE_CHAIN_ID) continue
    if (row.tradingAvailable != null && Number.isFinite(row.tradingAvailable)) {
      return Math.max(0, row.tradingAvailable)
    }
    if (row.platformBalance != null && row.platformBalance > 0) {
      return row.platformBalance
    }
    return 0
  }
  for (const row of positions) {
    if (row.asset.trim().toUpperCase() !== 'USDC') {
      continue
    }
    if (row.tradingAvailable != null && Number.isFinite(row.tradingAvailable)) {
      return Math.max(0, row.tradingAvailable)
    }
    if (row.platformBalance != null && row.platformBalance > 0) {
      return row.platformBalance
    }
    return 0
  }
}

export type PortalDefiVaultRef =
  | { kind: 'morpho'; vault: PortalMorphoVaultDetails }
  | { kind: 'ledgity'; vault: PortalLedgityVaultDetails }

/** Invest target chip for Morpho / Ledgity DeFi vault pages. */
export function buildDefiVaultInvestTarget(
  ref: PortalDefiVaultRef,
  position?: { display: string; heldLabel: string } | null,
): PortalInvestTarget {
  const vault = ref.vault
  const symbol = vault.asset.symbol
  const short = defiVaultShortName(vault.name)
  const apyBps = vault.userApyBps ?? 0
  const yieldPct = apyBps > 0 ? apyBps / 10_000 : 0

  return {
    key: vault.id,
    group: 'DeFi vaults',
    name: vault.name,
    short,
    unit: `${symbol} · BASE`,
    desc: `${vault.provider} · ${formatApyFromBps(vault.userApyBps)}`,
    glyph: '',
    bg: "url('/app-ds/assets/photos/coffre-flex.png') center/cover no-repeat",
    color: '#F4F1E8',
    yieldPct,
    pricePerPart: 1,
    held: position?.display ?? `0 ${symbol}`,
    heldLabel: position?.heldLabel ?? 'to initiate',
    tech:
      ref.kind === 'morpho'
        ? `Morpho vault · ${vault.vaultAddress}`
        : `Ledgity ERC4626 · ${vault.vaultAddress}`,
  }
}

export { USDC_RATE_TO_EUR, BASE_CHAIN_ID }
