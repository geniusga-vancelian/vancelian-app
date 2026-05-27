export type MarketQuoteUpdate = {
  symbol: string
  price: number
  priceEur?: number | null
}

export type PortalCryptoAsset = {
  id: string
  name: string
  ticker: string
  symbol: string
  /** Prix affiché (USD pour l’instant). */
  priceLabel: string
  /** Valeur numérique USD/USDT — source WS + REST. */
  priceUsd: number
  changePct: number
  logoUrl: string | null
}

export type PortalCryptoBundle = {
  id: string
  code: string
  title: string
  description: string
  imageUrl: string | null
  performance1d: number | null
  riskLabel: string | null
  /** Portfolio PE provisionné pour ce client (catalog `/api/app/bundle/catalog`). */
  portfolioId: string | null
  productId: string | null
  entryAssetDefault: string | null
  entryAssetsAllowed: string[]
  /** Actifs du panier (poids décroissant) — stack hero carte DS. */
  allocationTickers: string[]
  /** Ordre d’affichage CMS (`portfolio_product_configs.sort_order`). */
  sortOrder: number
}

export type PortalMarketsNewsItem = {
  id: string
  slug: string
  title: string
  coverUrl: string
  authorName: string
  publishedAt: string | null
  readingTime: number
  href: string
  tags: string[]
}

export type PortalResearchItem = {
  id: string
  title: string
  coverUrl: string
  readingTime: number
  tag?: string
  href: string
}

export type PortalMarketsPayload = {
  popular: PortalCryptoAsset[]
  topGainers: PortalCryptoAsset[]
  topLosers: PortalCryptoAsset[]
  favorites: PortalCryptoAsset[]
  allCrypto: PortalCryptoAsset[]
  bundles: PortalCryptoBundle[]
  news: PortalMarketsNewsItem[]
  research: PortalResearchItem[]
  /** Base publique FastAPI (logos + WS) — même hôte que Flutter `marketDataBaseUrl`. */
  marketDataPublicBaseUrl: string
  currency: 'USD'
  partial?: boolean
}
