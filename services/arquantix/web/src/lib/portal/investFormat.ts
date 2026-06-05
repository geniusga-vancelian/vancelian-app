import type {
  PortalExclusiveOffer,
  PortalInvestPayload,
  PortalVaultProduct,
} from '@/lib/portal/investTypes'
import { normalizeInvestCategorySlug } from '@/lib/portal/investCategoryFilter'
import { formatVaultNominalAmount } from '@/lib/portal/morphoVaultFormat'

type CatalogEngineSnapshot = {
  supply_apr?: number | string | null
  user_apy_bps?: number | string | null
  current_raised?: number | string | null
  target_size?: number | string | null
  progress_pct?: number | string | null
  liquidity_pct?: number | string | null
  tvl_usd?: number | string | null
  investors_count?: number | string | null
  status?: string | null
  duration_months?: number | string | null
  vault_address?: string | null
  integration_mode?: string | null
  portal_config_id?: string | null
  lock_active?: boolean | null
  lock_status_label?: string | null
  operation_end_at?: string | null
  withdraw_mode?: string | null
  asset_symbol?: string | null
}

type CatalogProductRow = {
  id: string
  slug: string
  title?: string | null
  subtitle?: string | null
  coverUrl?: string | null
  category?: string | null
  productType?: string | null
  engine?: {
    type?: string | null
    referenceId?: string | null
    snapshot?: CatalogEngineSnapshot | null
  } | null
}

function toNumber(value: unknown, fallback = 0): number {
  if (value == null) return fallback
  if (typeof value === 'number' && !Number.isNaN(value)) return value
  const parsed = Number(String(value).replace(',', '.'))
  return Number.isNaN(parsed) ? fallback : parsed
}

function formatMoney(amount: number, currency = 'EUR'): string {
  try {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(amount)
  } catch {
    return `${Math.round(amount)} ${currency}`
  }
}

function displayCategory(slug: string | null | undefined): string {
  const raw = (slug ?? '').trim()
  if (!raw) return 'Exclusive offer'
  return raw
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function resolveCatalogApy(snap: CatalogEngineSnapshot): number {
  const supplyApr = toNumber(snap.supply_apr)
  if (supplyApr > 0) return supplyApr
  const bps = toNumber(snap.user_apy_bps)
  return bps > 0 ? bps / 100 : 0
}

function resolveCatalogAssetSymbol(snap: CatalogEngineSnapshot): string | null {
  const raw = snap.asset_symbol
  if (typeof raw !== 'string') return null
  const sym = raw.trim().toUpperCase()
  return sym.length > 0 ? sym : null
}

function formatCatalogAmountLabel(amount: number, assetSymbol: string | null): string {
  if (assetSymbol) return formatVaultNominalAmount(amount, assetSymbol, 'en')
  return formatMoney(amount)
}

function mapOffer(row: CatalogProductRow): PortalExclusiveOffer {
  const snap = row.engine?.snapshot ?? {}
  const assetSymbol = resolveCatalogAssetSymbol(snap)
  const raised = toNumber(snap.current_raised, toNumber(snap.tvl_usd))
  const target = toNumber(snap.target_size, raised)
  const progressPct = Math.min(
    100,
    Math.max(
      0,
      toNumber(
        snap.progress_pct,
        toNumber(snap.liquidity_pct, target > 0 ? (raised / target) * 100 : 0),
      ),
    ),
  )
  const apy = resolveCatalogApy(snap)
  const status = (snap.status ?? '').toString().toLowerCase()
  const isFunded = progressPct >= 100 || status.includes('funded') || status.includes('closed')
  const slug = row.slug.trim()
  const categorySlug = normalizeInvestCategorySlug(row.category)

  return {
    id: row.id,
    slug,
    title: row.title?.trim() || 'Exclusive offer',
    subtitle: row.subtitle?.trim() || '',
    coverUrl: row.coverUrl?.trim() || '',
    category: displayCategory(row.category),
    categorySlug,
    description: row.subtitle?.trim() || '',
    progressPct,
    raisedLabel: formatCatalogAmountLabel(raised, assetSymbol),
    targetLabel: target > 0 ? formatCatalogAmountLabel(target, assetSymbol) : '—',
    assetSymbol,
    investorsCount: Math.max(0, Math.floor(toNumber(snap.investors_count))),
    apyLabel: apy > 0 ? `${apy.toFixed(2)}% APR` : '—',
    durationMonths: snap.duration_months != null ? Math.floor(toNumber(snap.duration_months)) : null,
    isFunded,
    href: slug ? `/app/invest/${encodeURIComponent(slug)}` : '/app/invest',
    lockActive: snap.lock_active === true,
    lockStatusLabel:
      typeof snap.lock_status_label === 'string' ? snap.lock_status_label : null,
    operationEndAt:
      typeof snap.operation_end_at === 'string' ? snap.operation_end_at : null,
    withdrawMode:
      snap.withdraw_mode === 'instant' ||
      snap.withdraw_mode === 'async_request' ||
      snap.withdraw_mode === 'blocked'
        ? snap.withdraw_mode
        : null,
  }
}

function mapVaultProduct(row: CatalogProductRow): PortalVaultProduct {
  const base = mapOffer(row)
  const snap = row.engine?.snapshot ?? {}
  const engineType = row.engine?.type ?? null
  return {
    ...base,
    productType: 'vault_simple',
    title: base.title === 'Exclusive offer' ? row.title?.trim() || 'Vault' : base.title,
    category: displayCategory(row.category) || 'Vault',
    vaultEngineConfigId:
      engineType === 'vault_engine'
        ? (row.engine?.referenceId?.trim() || snap.portal_config_id?.toString().trim() || null)
        : null,
    vaultAddress: snap.vault_address?.toString().trim() || null,
    integrationMode: snap.integration_mode?.toString().trim() || null,
    href: row.slug?.trim() ? `/app/invest/${encodeURIComponent(row.slug.trim())}` : '/app/invest',
  }
}

export function buildPortalInvestPayload(
  exclusiveOffers: CatalogProductRow[],
  vaultProducts: CatalogProductRow[] = [],
): PortalInvestPayload {
  return {
    offers: exclusiveOffers.map(mapOffer),
    vaults: vaultProducts.map(mapVaultProduct),
  }
}
