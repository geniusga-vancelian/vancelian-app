import { normalizeCryptoBaseTicker } from '@/lib/portal/cryptoInstrumentAssets'
import { entityIdToTicker } from '@/lib/portal/marketsFormat'
import { instrumentDisplayName } from '@/lib/portal/instrumentDetailFormat'
import { consolidateSwapTransactions, parseSwapAssetsFromTitle } from '@/lib/portal/cryptoTransactionHistoryFormat'
import {
  shouldHidePrivyDepositForLombardBorrow,
} from '@/lib/portal/lombard/lombardWalletTransactions'
import { formatPortalMoney, normalizeChartSeries } from '@/lib/portal/dashboardFormat'
import { resolvePositionPortalChain } from '@/lib/portal/portalChainFilter'
import { PORTAL_CHAIN_LABELS, type PortalChain } from '@/config/portalChains'
import {
  buildLombardWalletDetailFields,
  formatLombardPositionSubtitle,
} from '@/lib/portal/lombard/lombardWalletBalanceOverlay'
import { filterCryptoPositionsSummaryByPortalScope } from '@/lib/portal/portalWalletScopeFilter'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'
import type {
  PortalCryptoPosition,
  PortalCryptoPositionsSummary,
  PortalCryptoWalletDetail,
  PortalCryptoWalletRow,
  PortalCryptoWalletTransaction,
  PortalBundlePosition,
  PortalMyBundleSummary,
} from '@/lib/portal/cryptoWalletTypes'

const STABLECOIN_USD_PRICE: Record<string, number> = {
  USDC: 1,
  USDT: 1,
  EURC: 1,
}

function tickerFromProviderSymbol(symbol: string): string {
  return entityIdToTicker(symbol)
}

function toNumber(value: unknown, fallback = 0): number {
  if (value == null) return fallback
  if (typeof value === 'number' && !Number.isNaN(value)) return value
  const parsed = Number(String(value).replace(',', '.').replace('+', ''))
  return Number.isNaN(parsed) ? fallback : parsed
}

function toOptionalNumber(value: unknown): number | undefined {
  if (value == null || value === '') return undefined
  const parsed = toNumber(value, NaN)
  return Number.isNaN(parsed) ? undefined : parsed
}

export function parseCryptoPositionsPayload(raw: unknown): PortalCryptoPositionsSummary {
  const root = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const summary =
    root.summary && typeof root.summary === 'object'
      ? (root.summary as Record<string, unknown>)
      : {}
  const list = Array.isArray(root.positions) ? root.positions : []

  const positions: PortalCryptoPosition[] = list
    .filter((item): item is Record<string, unknown> => item != null && typeof item === 'object')
    .map((item) => ({
      asset: String(item.asset ?? '').trim().toUpperCase(),
      name: String(item.name ?? item.asset ?? '').trim(),
      balance: toNumber(item.balance),
      availableBalance: toNumber(item.available_balance),
      priceEur: toOptionalNumber(item.price_eur),
      estimatedValueEur: toOptionalNumber(item.estimated_value_eur),
      priceUsd: toOptionalNumber(item.price_usd),
      estimatedValueUsd: toOptionalNumber(item.estimated_value_usd),
      performance1dPct: toOptionalNumber(item.performance_1d_pct),
      iconKey: String(item.icon_key ?? item.asset ?? '').trim().toLowerCase(),
      portfolioScope:
        typeof item.portfolio_scope === 'string' ? item.portfolio_scope : undefined,
      privyBalance: toOptionalNumber(item.privy_balance),
      platformBalance: toOptionalNumber(item.platform_balance),
      chainType: typeof item.chain_type === 'string' ? item.chain_type : undefined,
      chainId: typeof item.chain_id === 'number' ? item.chain_id : null,
      dedicatedWallet: item.dedicated_wallet === true,
      walletAddress:
        typeof item.wallet_address === 'string' ? item.wallet_address : undefined,
    }))
    .filter((p) => p.asset)

  return {
    totalValueEur: toNumber(summary.total_value_eur),
    totalValueUsd: toOptionalNumber(summary.total_value_usd),
    positionsCount: toNumber(summary.positions_count, positions.length),
    positions,
  }
}

const BUNDLE_PORTFOLIO_SCOPES = new Set(['bundle', 'bundle_portfolio', 'bundle_cash'])

/** Solde affiché en self-trading : atomes direct_portfolio PE, pas le total custody Privy. */
export function resolveSelfTradingPositionBalance(position: PortalCryptoPosition): number {
  const platform = position.platformBalance
  if (platform != null && platform > 0) return platform
  return position.balance
}

function scaleSelfTradingEstimatedValues(
  position: PortalCryptoPosition,
  selfTradingBalance: number,
): Pick<PortalCryptoPosition, 'estimatedValueEur' | 'estimatedValueUsd' | 'priceEur' | 'priceUsd'> {
  if (selfTradingBalance === position.balance || position.balance <= 0) {
    return {}
  }
  if (position.priceEur != null || position.priceUsd != null) {
    return {
      priceEur: position.priceEur,
      priceUsd: position.priceUsd,
      estimatedValueEur:
        position.priceEur != null ? position.priceEur * selfTradingBalance : undefined,
      estimatedValueUsd:
        position.priceUsd != null ? position.priceUsd * selfTradingBalance : undefined,
    }
  }
  const ratio = selfTradingBalance / position.balance
  return {
    estimatedValueEur:
      position.estimatedValueEur != null ? position.estimatedValueEur * ratio : undefined,
    estimatedValueUsd:
      position.estimatedValueUsd != null ? position.estimatedValueUsd * ratio : undefined,
  }
}

/** Parse `/api/app/crypto-positions/direct` — vue « Mon Trading » (direct_portfolio uniquement). */
export function parseSelfTradingCryptoPositionsPayload(
  raw: unknown,
): PortalCryptoPositionsSummary {
  const parsed = parseCryptoPositionsPayload(raw)
  const positions = parsed.positions
    .filter((position) => {
      const scope = position.portfolioScope?.trim().toLowerCase()
      return !scope || !BUNDLE_PORTFOLIO_SCOPES.has(scope)
    })
    .map((position) => {
      const balance = resolveSelfTradingPositionBalance(position)
      const scaled = scaleSelfTradingEstimatedValues(position, balance)
      return {
        ...position,
        ...scaled,
        balance,
        availableBalance: balance,
        portfolioScope: 'direct',
      }
    })
    .filter((position) => position.balance > 0 || position.dedicatedWallet)

  const totalValueEur = positions.reduce((sum, position) => sum + (position.estimatedValueEur ?? 0), 0)
  const totalValueUsd = positions.reduce((sum, position) => sum + (position.estimatedValueUsd ?? 0), 0)

  return {
    totalValueEur,
    totalValueUsd: totalValueUsd > 0 ? totalValueUsd : undefined,
    positionsCount: positions.length,
    positions,
  }
}

function parseBundlePosition(item: Record<string, unknown>): PortalBundlePosition {
  return {
    asset: String(item.asset ?? '').trim().toUpperCase(),
    quantity: toNumber(item.quantity),
    costBasis: toNumber(item.cost_basis),
    costBasisUsd: toOptionalNumber(item.cost_basis_usd),
    positionType: String(item.position_type ?? ''),
    marketValue: toOptionalNumber(item.market_value),
    marketValueUsd: toOptionalNumber(item.market_value_usd),
    priceEur: toOptionalNumber(item.price_eur),
    priceUsd: toOptionalNumber(item.price_usd),
    targetWeight: toOptionalNumber(item.target_weight),
  }
}

export function parseMyBundles(raw: unknown): PortalMyBundleSummary[] {
  let list: unknown[] = []
  if (Array.isArray(raw)) {
    list = raw
  } else if (raw && typeof raw === 'object') {
    const bundles = (raw as Record<string, unknown>).bundles
    if (Array.isArray(bundles)) list = bundles
  }
  return list
    .filter((item): item is Record<string, unknown> => item != null && typeof item === 'object')
    .map((item) => {
      const rawPositions = Array.isArray(item.positions) ? item.positions : []
      const positions = rawPositions
        .filter((p): p is Record<string, unknown> => p != null && typeof p === 'object')
        .map(parseBundlePosition)
        .filter((p) => p.asset)

      return {
        portfolioId: String(item.portfolio_id ?? ''),
        portfolioName: String(item.portfolio_name ?? 'Portfolio'),
        status: String(item.status ?? ''),
        assetsCount: toNumber(item.assets_count),
        totalCostBasis: toNumber(item.total_cost_basis),
        totalCostBasisUsd: toOptionalNumber(item.total_cost_basis_usd),
        totalMarketValue: toOptionalNumber(item.total_market_value),
        totalMarketValueUsd: toOptionalNumber(item.total_market_value_usd),
        performancePct: toOptionalNumber(item.performance_pct),
        hasHoldings: item.has_holdings === true,
        positions: positions.length > 0 ? positions : undefined,
      }
    })
    .filter((b) => b.portfolioId)
}

export function findMyBundleByPortfolioId(
  bundles: PortalMyBundleSummary[],
  portfolioId: string,
): PortalMyBundleSummary | undefined {
  const id = portfolioId.trim()
  if (!id) return undefined
  return bundles.find((b) => b.portfolioId === id)
}

export function parseWalletHistoryPoints(raw: unknown): number[] {
  const root = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const points = Array.isArray(root.points) ? root.points : []
  return normalizeChartSeries(
    points
      .filter((p): p is Record<string, unknown> => p != null && typeof p === 'object')
      .map((p) => ({
        performance_value: toNumber(
          p.wallet_value ?? p.performance_value ?? p.total_value ?? p.value,
        ),
      })),
  )
}

export function extractUpstreamDetailPayload(raw: unknown): unknown {
  if (!raw || typeof raw !== 'object') return null
  const root = raw as Record<string, unknown>
  return root.detail ?? null
}

export function marketSummaryRows(raw: unknown): Record<string, unknown>[] {
  if (!raw || typeof raw !== 'object') return []
  const root = raw as Record<string, unknown>
  const summaries =
    root.summaries ?? (Array.isArray(raw) ? raw : null)
  return Array.isArray(summaries)
    ? summaries.filter((row): row is Record<string, unknown> => row != null && typeof row === 'object')
    : []
}

export function marketSummaryByTicker(raw: unknown): Map<string, Record<string, unknown>> {
  const map = new Map<string, Record<string, unknown>>()
  for (const row of marketSummaryRows(raw)) {
    const symbol = String(row.symbol ?? '').trim().toUpperCase()
    if (!symbol) continue
    map.set(tickerFromProviderSymbol(symbol), row)
  }
  return map
}

function estimateStablecoinValues(
  asset: string,
  balance: number,
  currency: string,
): { priceEur?: number; priceUsd?: number; valueEur?: number; valueUsd?: number } {
  const usd = STABLECOIN_USD_PRICE[asset.toUpperCase()]
  if (usd == null) return {}
  const valueUsd = balance * usd
  const valueEur = balance * usd * 0.92
  return {
    priceUsd: usd,
    priceEur: 0.92,
    valueUsd,
    valueEur,
  }
}

/** Positions hub — soldes réels wallet Privy enrichis marché. */
export function buildPrivyWalletPositionsSummary(
  privyRaw: unknown,
  marketRaw: unknown,
  currency: string,
): PortalCryptoPositionsSummary {
  const root = privyRaw && typeof privyRaw === 'object' ? (privyRaw as Record<string, unknown>) : {}
  const summary =
    root.summary && typeof root.summary === 'object'
      ? (root.summary as Record<string, unknown>)
      : {}
  const balances = Array.isArray(root.balances) ? root.balances : []
  const market = marketSummaryByTicker(marketRaw)

  const positions: PortalCryptoPosition[] = balances
    .filter((item): item is Record<string, unknown> => item != null && typeof item === 'object')
    .map((item) => {
      const asset = String(item.asset ?? '').trim().toUpperCase()
      const balance = toNumber(item.balance)
      const availableBalance = toNumber(item.available_balance, balance)
      const onChainBalance = toOptionalNumber(item.on_chain_balance)
      const quoteTicker = normalizeCryptoBaseTicker(asset)
      const marketRow = market.get(asset) ?? market.get(quoteTicker)
      let priceEur = marketRow ? toOptionalNumber(marketRow.price_eur ?? marketRow.priceEur) : undefined
      let priceUsd = marketRow ? toOptionalNumber(marketRow.price) : undefined
      let estimatedValueEur = priceEur != null ? balance * priceEur : undefined
      let estimatedValueUsd = priceUsd != null ? balance * priceUsd : undefined
      const perfRaw = marketRow?.change_24h_pct ?? marketRow?.change24h_pct ?? marketRow?.change24hPct
      let performance1dPct = perfRaw != null ? toOptionalNumber(perfRaw) : undefined
      const providerSymbol = marketRow
        ? String(marketRow.symbol ?? '').trim().toUpperCase() || undefined
        : undefined
      const logoUrlRaw = marketRow?.logo_url ?? marketRow?.logoUrl
      const logoUrl =
        logoUrlRaw != null && String(logoUrlRaw).trim() ? String(logoUrlRaw).trim() : null

      if (estimatedValueEur == null && estimatedValueUsd == null) {
        const stable = estimateStablecoinValues(asset, balance, currency)
        priceEur = priceEur ?? stable.priceEur
        priceUsd = priceUsd ?? stable.priceUsd
        estimatedValueEur = stable.valueEur
        estimatedValueUsd = stable.valueUsd
      }

      return {
        asset,
        name: instrumentDisplayName(asset) || String(item.name ?? asset).trim() || asset,
        balance,
        availableBalance,
        priceEur,
        estimatedValueEur,
        priceUsd,
        estimatedValueUsd,
        performance1dPct,
        iconKey: String(item.icon_key ?? asset).trim().toLowerCase(),
        providerSymbol,
        logoUrl,
        portfolioScope: 'privy',
        privyBalance: balance,
        platformBalance: 0,
        chainType: typeof item.chain_type === 'string' ? item.chain_type : undefined,
        chainId: typeof item.chain_id === 'number' ? item.chain_id : null,
        dedicatedWallet: item.dedicated_wallet === true,
        walletAddress:
          typeof item.wallet_address === 'string' ? item.wallet_address : undefined,
        onChainBalance,
      }
    })
    .filter((p) => p.asset && (p.balance > 0 || p.dedicatedWallet))

  positions.sort(
    (a, b) =>
      (selectMoneyValue(currency, b.estimatedValueEur, b.estimatedValueUsd) ?? 0) -
      (selectMoneyValue(currency, a.estimatedValueEur, a.estimatedValueUsd) ?? 0),
  )

  const totalValueEur = positions.reduce((sum, p) => sum + (p.estimatedValueEur ?? 0), 0)
  const totalValueUsd = positions.reduce((sum, p) => sum + (p.estimatedValueUsd ?? 0), 0)

  return {
    totalValueEur,
    totalValueUsd: totalValueUsd > 0 ? totalValueUsd : undefined,
    positionsCount: toNumber(summary.positions_count, positions.length),
    positions,
  }
}

export function parsePrivyWalletDeposits(raw: unknown): PortalCryptoWalletTransaction[] {
  const root = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const list = Array.isArray(root.deposits) ? root.deposits : []
  return list
    .filter((item): item is Record<string, unknown> => item != null && typeof item === 'object')
    .map((item) => {
      const asset = String(item.asset ?? '').trim().toUpperCase()
      const amountCrypto = String(item.amount ?? '')
      const direction = String(item.direction ?? 'credit')
      const isCredit = direction === 'credit' || direction === 'in'
      const title = String(item.title ?? 'Dépôt')
      const transactionKind =
        typeof item.transaction_kind === 'string' ? item.transaction_kind : 'deposit'
      const parsedSwap =
        parseSwapAssetsFromTitle(title) ??
        (typeof item.from_asset === 'string' && typeof item.to_asset === 'string'
          ? {
              fromAsset: String(item.from_asset).trim().toUpperCase(),
              toAsset: String(item.to_asset).trim().toUpperCase(),
            }
          : null)
      const isSwap =
        transactionKind === 'crypto_swap' ||
        (parsedSwap != null && parsedSwap.fromAsset !== parsedSwap.toAsset)

      return {
        id: String(item.id ?? ''),
        side: isSwap ? 'swap' : isCredit ? 'deposit' : 'withdraw',
        asset,
        amountCrypto,
        amountFiat: '',
        price: '',
        currency: 'EUR',
        status: String(item.status ?? ''),
        createdAt: String(item.created_at ?? ''),
        title,
        subtitle: String(item.subtitle ?? item.tx_hash ?? ''),
        direction,
        transactionKind,
        sourceSystem: 'privy',
        txHash: typeof item.tx_hash === 'string' ? item.tx_hash : undefined,
        fromAsset:
          typeof item.from_asset === 'string'
            ? item.from_asset
            : parsedSwap?.fromAsset,
        toAsset:
          typeof item.to_asset === 'string' ? item.to_asset : parsedSwap?.toAsset,
        swapAmountFrom:
          typeof item.swap_amount_from === 'string' ? item.swap_amount_from : undefined,
        swapAmountTo: typeof item.swap_amount_to === 'string' ? item.swap_amount_to : undefined,
      }
    })
    .filter((tx) => tx.id)
}

function swapTransactionPriority(tx: PortalCryptoWalletTransaction): number {
  if (tx.sourceSystem === 'lifi_swap' || tx.side === 'swap') return 3
  if (tx.swapAmountFrom && tx.swapAmountTo) return 2
  if (tx.transactionKind === 'crypto_swap') return 1
  return 0
}

/** Fusionne transactions crypto-positions + dépôts Privy (dédupliqués par id). */
export function mergeCryptoWalletTransactions(
  platformRaw: unknown,
  privyRaw: unknown,
): PortalCryptoWalletTransaction[] {
  const platform = parseCryptoWalletTransactions(platformRaw)
  const privy = parsePrivyWalletDeposits(privyRaw)

  const bestByHash = new Map<string, PortalCryptoWalletTransaction>()
  for (const tx of [...platform, ...privy]) {
    const hash = tx.txHash?.trim().toLowerCase()
    if (!hash) continue
    const existing = bestByHash.get(hash)
    if (!existing || swapTransactionPriority(tx) > swapTransactionPriority(existing)) {
      bestByHash.set(hash, tx)
    }
  }

  const byId = new Map<string, PortalCryptoWalletTransaction>()
  for (const tx of platform) {
    byId.set(tx.id, tx)
  }
  for (const tx of privy) {
    if (byId.has(tx.id)) continue
    const hash = tx.txHash?.trim().toLowerCase()
    if (hash) {
      const preferred = bestByHash.get(hash)
      if (preferred && preferred.id !== tx.id) continue
    }
    byId.set(tx.id, tx)
  }

  return consolidateSwapTransactions([...byId.values()]).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  )
}

/** Ajoute les emprunts Lombard USDC et masque les dépôts Privy génériques redondants. */
export function mergeLombardBorrowWalletTransactions(
  merged: PortalCryptoWalletTransaction[],
  lombardBorrow: PortalCryptoWalletTransaction[],
  hiddenPrivyKeys: Set<string>,
): PortalCryptoWalletTransaction[] {
  const filtered = merged.filter(
    (tx) => !shouldHidePrivyDepositForLombardBorrow(tx, hiddenPrivyKeys),
  )

  const byId = new Map<string, PortalCryptoWalletTransaction>()
  for (const tx of filtered) {
    byId.set(tx.id, tx)
  }
  for (const tx of lombardBorrow) {
    byId.set(tx.id, tx)
  }

  return [...byId.values()].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  )
}

export function formatCryptoTransactionAmount(tx: PortalCryptoWalletTransaction): string {
  const fiat = tx.amountFiat?.trim()
  if (fiat && fiat !== '0' && fiat !== '0.00') return fiat
  const crypto = tx.amountCrypto?.trim()
  if (!crypto) return '—'
  const asset = tx.asset?.trim().toUpperCase()
  return asset ? `${crypto} ${asset}` : crypto
}

export function isIncomingCryptoTransaction(tx: PortalCryptoWalletTransaction): boolean {
  const direction = tx.direction?.trim().toLowerCase()
  if (direction === 'credit' || direction === 'in') return true
  if (direction === 'debit' || direction === 'out') return false
  const side = tx.side?.trim().toLowerCase()
  return side === 'buy' || side === 'deposit'
}

export function parseCryptoWalletDetail(raw: unknown): PortalCryptoWalletDetail | null {
  if (!raw || typeof raw !== 'object') return null
  const item = raw as Record<string, unknown>
  const asset = String(item.asset ?? '').trim().toUpperCase()
  if (!asset) return null

  return {
    asset,
    name: String(item.name ?? asset),
    iconKey: String(item.icon_key ?? asset).trim().toLowerCase(),
    volume: String(item.volume ?? '0'),
    currentPriceEur: toOptionalNumber(item.current_price_eur),
    currentPriceUsd: toOptionalNumber(item.current_price_usd),
    totalValueEur: toNumber(item.total_value_eur),
    totalValueUsd: toOptionalNumber(item.total_value_usd),
    avgBuyPriceEur: toOptionalNumber(item.avg_buy_price_eur),
    avgBuyPriceUsd: toOptionalNumber(item.avg_buy_price_usd),
    averagePurchasePrice: toOptionalNumber(item.average_purchase_price),
    costBasis: toOptionalNumber(item.cost_basis),
    unrealizedGainEur: toOptionalNumber(item.unrealized_gain_eur),
    unrealizedGainUsd: toOptionalNumber(item.unrealized_gain_usd),
    unrealizedGains: toOptionalNumber(item.unrealized_gains),
    unrealizedGainsPct: toOptionalNumber(item.unrealized_gains_pct),
    realizedGainEur: toNumber(item.realized_gain_eur),
    realizedGainUsd: toOptionalNumber(item.realized_gain_usd),
    realizedGains: toNumber(item.realized_gains),
    totalGainEur: toOptionalNumber(item.total_gain_eur),
    totalGainUsd: toOptionalNumber(item.total_gain_usd),
    totalGains: toOptionalNumber(item.total_gains),
    totalGainsPct: toOptionalNumber(item.total_gains_pct),
    portfolioScope:
      typeof item.portfolio_scope === 'string' ? item.portfolio_scope : undefined,
    privyBalance: toOptionalNumber(item.privy_balance),
    platformBalance: toOptionalNumber(item.platform_balance),
  }
}

export function parseCryptoWalletTransactions(raw: unknown): PortalCryptoWalletTransaction[] {
  const root = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const list = Array.isArray(root.transactions) ? root.transactions : []
  return list
    .filter((item): item is Record<string, unknown> => item != null && typeof item === 'object')
    .map((item) => ({
      id: String(item.id ?? ''),
      side: String(item.side ?? ''),
      asset: String(item.asset ?? ''),
      amountCrypto: String(item.amount_crypto ?? ''),
      amountFiat: String(item.amount_fiat ?? ''),
      price: String(item.price ?? ''),
      currency: String(item.currency ?? 'EUR'),
      status: String(item.status ?? ''),
      createdAt: String(item.created_at ?? ''),
      title: String(item.title ?? ''),
      subtitle: String(item.subtitle ?? ''),
      direction: String(item.direction ?? ''),
      transactionKind:
        typeof item.transaction_kind === 'string' ? item.transaction_kind : undefined,
      sourceSystem: typeof item.source_system === 'string' ? item.source_system : undefined,
      fromAsset: typeof item.from_asset === 'string' ? item.from_asset : undefined,
      toAsset: typeof item.to_asset === 'string' ? item.to_asset : undefined,
      swapAmountFrom:
        typeof item.swap_amount_from === 'string' ? item.swap_amount_from : undefined,
      swapAmountTo: typeof item.swap_amount_to === 'string' ? item.swap_amount_to : undefined,
      txHash: typeof item.tx_hash === 'string' ? item.tx_hash : undefined,
    }))
    .filter((tx) => tx.id)
}

export function selectMoneyValue(
  currency: string,
  eur?: number,
  usd?: number,
): number | undefined {
  if (currency === 'USD') return usd ?? eur
  return eur ?? usd
}

/** Valorisation bundle dans la devise de référence client (API renvoie EUR + USD). */
export function bundleMoneyValue(
  currency: string,
  eur?: number,
  usd?: number,
): number | undefined {
  return selectMoneyValue(currency, eur, usd)
}

export function bundleSummaryMarketValue(
  bundle: PortalMyBundleSummary | undefined | null,
  currency: string,
): number {
  if (!bundle) return 0
  return (
    bundleMoneyValue(currency, bundle.totalMarketValue, bundle.totalMarketValueUsd) ??
    bundleMoneyValue(currency, bundle.totalCostBasis, bundle.totalCostBasisUsd) ??
    0
  )
}

export function bundlePositionDisplayValue(
  position: PortalBundlePosition,
  currency: string,
): number {
  const asset = position.asset.toUpperCase()
  if ((asset === 'USDC' || asset === 'USDT') && currency === 'USD' && position.quantity > 0) {
    return position.quantity
  }
  if ((asset === 'EUR' || asset === 'EURC') && currency === 'EUR' && position.quantity > 0) {
    return position.quantity
  }

  const fromMarket = bundleMoneyValue(
    currency,
    position.marketValue,
    position.marketValueUsd,
  )
  if (fromMarket != null && fromMarket > 0) return fromMarket
  const fromCost = bundleMoneyValue(currency, position.costBasis, position.costBasisUsd)
  if (fromCost != null && fromCost > 0) return fromCost
  if (asset === 'USDC' || asset === 'USDT') {
    return position.quantity
  }
  return 0
}

export function formatCryptoMoney(amount: number | undefined, currency: string): string {
  if (amount == null || Number.isNaN(amount)) return '—'
  return formatPortalMoney(amount, currency)
}

export function formatPerfPct(pct: number | undefined): string | null {
  if (pct == null || Number.isNaN(pct)) return null
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)} %`
}

export function assetPrecisionDisplay(asset: string): number {
  switch (asset.toUpperCase()) {
    case 'BTC':
      return 8
    case 'ETH':
      return 6
    case 'SOL':
    case 'XRP':
    case 'ADA':
      return 4
    default:
      return 6
  }
}

export function formatCryptoVolume(balance: number, asset: string): string {
  const precision = assetPrecisionDisplay(asset)
  return `${balance.toFixed(precision)} ${asset.toUpperCase()}`
}

/** Volume affiché sur l'écran détail (sans suffixe ticker). */
export function formatDetailVolumeAmount(balance: number, asset: string): string {
  const precision = assetPrecisionDisplay(asset)
  let text = balance.toFixed(precision)
  if (text.includes('.')) {
    text = text.replace(/0+$/, '').replace(/\.$/, '')
  }
  return text || '0'
}

export function resolveScopedPrivyPositionForAsset(
  summary: PortalCryptoPositionsSummary,
  asset: string,
  chain: PortalChain,
  scope: PortalWalletScope | null,
): PortalCryptoPosition | undefined {
  const scoped = filterCryptoPositionsSummaryByPortalScope(summary, chain, scope)
  const assetU = asset.trim().toUpperCase()
  return scoped.positions.find((row) => row.asset.toUpperCase() === assetU)
}

/** Construit un détail crypto depuis le hub Privy (source de vérité portail). */
export function buildCryptoWalletDetailFromScopedPosition(
  position: PortalCryptoPosition,
): PortalCryptoWalletDetail {
  return {
    asset: position.asset,
    name: position.name,
    iconKey: position.iconKey,
    currentPriceEur: position.priceEur,
    currentPriceUsd: position.priceUsd,
    avgBuyPriceEur: undefined,
    avgBuyPriceUsd: undefined,
    unrealizedGainEur: 0,
    unrealizedGains: 0,
    realizedGainEur: 0,
    realizedGains: 0,
    portfolioScope: position.portfolioScope ?? 'privy',
    privyBalance: position.privyBalance ?? position.balance,
    platformBalance: position.platformBalance ?? 0,
    ...buildLombardWalletDetailFields(position),
  }
}

/** Aligne volume / valorisation détail crypto sur le hub wallet (Privy + scope navbar). */
export function alignCryptoWalletDetailWithScopedPosition(
  detail: PortalCryptoWalletDetail,
  position: PortalCryptoPosition | undefined,
): PortalCryptoWalletDetail {
  if (!position || position.balance <= 0) return detail

  return {
    ...detail,
    privyBalance: position.privyBalance ?? position.balance,
    platformBalance: position.platformBalance ?? 0,
    portfolioScope: position.portfolioScope ?? detail.portfolioScope ?? 'privy',
    currentPriceEur: position.priceEur ?? detail.currentPriceEur,
    currentPriceUsd: position.priceUsd ?? detail.currentPriceUsd,
    ...buildLombardWalletDetailFields(position),
  }
}

function resolvePositionChainLabel(position: PortalCryptoPosition): string {
  const portalChain = resolvePositionPortalChain(position)
  if (portalChain) return PORTAL_CHAIN_LABELS[portalChain]
  const chainType = (position.chainType ?? '').trim().toLowerCase()
  if (chainType === 'solana') return 'Solana'
  if (chainType === 'evm' || chainType === 'ethereum') return 'Ethereum'
  return position.chainType
    ? position.chainType.charAt(0).toUpperCase() + position.chainType.slice(1)
    : 'EVM'
}

export function resolvePositionSubtitle(position: PortalCryptoPosition): string {
  const lombardSubtitle = formatLombardPositionSubtitle(position)
  if (lombardSubtitle) return lombardSubtitle

  const volumeStr = formatCryptoVolume(position.balance, position.asset)
  if (position.dedicatedWallet && position.chainType) {
    const chainLabel = resolvePositionChainLabel(position)
    return `Wallet ${chainLabel} · ${volumeStr}`
  }
  if (position.portfolioScope === 'privy') return volumeStr
  if (position.portfolioScope === 'merged') return `${volumeStr} · incl. integrated wallet`
  return volumeStr
}

export function isPrivyOnlyScope(scope?: string): boolean {
  return scope === 'privy'
}

export function buildUnifiedWalletRows(
  positions: PortalCryptoPosition[],
  bundles: PortalMyBundleSummary[],
  currency: string,
): PortalCryptoWalletRow[] {
  const rows: PortalCryptoWalletRow[] = []

  for (const position of positions) {
    const value =
      selectMoneyValue(
        currency,
        position.estimatedValueEur,
        position.estimatedValueUsd,
      ) ?? 0
    rows.push({ kind: 'position', value, position })
  }

  for (const bundle of bundles.filter((b) => b.hasHoldings)) {
    const value = bundleSummaryMarketValue(bundle, currency)
    rows.push({ kind: 'bundle', value, bundle })
  }

  rows.sort((a, b) => b.value - a.value)
  return rows
}

export function resolveHubTotalValue(
  positions: PortalCryptoPositionsSummary,
  bundles: PortalMyBundleSummary[],
  currency: string,
): number {
  const direct =
    selectMoneyValue(currency, positions.totalValueEur, positions.totalValueUsd) ?? 0
  const bundleSum = bundles
    .filter((b) => b.hasHoldings)
    .reduce((sum, b) => sum + bundleSummaryMarketValue(b, currency), 0)
  return direct + bundleSum
}

export function resolveHubCountLabel(
  positions: PortalCryptoPositionsSummary,
  bundles: PortalMyBundleSummary[],
  options?: { privyOnly?: boolean; selfTradingDirect?: boolean },
): string {
  const count = positions.positionsCount || positions.positions.length
  if (options?.selfTradingDirect) {
    return count === 1 ? '1 actif · Mon Trading' : `${count} actifs · Mon Trading`
  }
  if (options?.privyOnly) {
    return count === 1 ? '1 actif · wallet Privy' : `${count} actifs · wallet Privy`
  }
  const activeBundles = bundles.filter((b) => b.hasHoldings).length
  if (activeBundles > 0) {
    return `${count} crypto${count === 1 ? '' : 's'} · ${activeBundles} bundle${activeBundles === 1 ? '' : 's'}`
  }
  return `${count} crypto-actif${count === 1 ? '' : 's'}`
}

export function resolvePrivyHubTotalValue(
  positions: PortalCryptoPositionsSummary,
  currency: string,
): number {
  return positions.positions.reduce(
    (sum, p) => sum + (selectMoneyValue(currency, p.estimatedValueEur, p.estimatedValueUsd) ?? 0),
    0,
  )
}

export function perfToneClass(pct: number | undefined): string {
  if (pct == null || Number.isNaN(pct) || Math.abs(pct) < 0.005) return 'text-v-fg-muted'
  return pct > 0 ? 'text-v-green' : 'text-v-error'
}
