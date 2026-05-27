export type PortalBundleVaultModule = {
  id?: string
  type: string
  enabled?: boolean
  content: Record<string, unknown>
}

export type PortalBundleAllocationRow = {
  assetSymbol: string
  name: string
  targetWeight: number
}

export type PortalBundleProductDetailPayload = {
  productCode: string
  title: string
  subtitle: string
  headerMediaUrl: string | null
  detailMediaUrl: string | null
  portfolioId: string | null
  productId: string | null
  entryAssetDefault: string | null
  entryAssetsAllowed: string[]
  riskLabel: string | null
  modules: PortalBundleVaultModule[]
  allocations: PortalBundleAllocationRow[]
}

export type PortalBundleChartPayload = {
  period: string
  performancePct: number | null
  historyPoints: number[]
}
