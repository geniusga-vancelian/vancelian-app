import type { AppPortfolioAllocationSlice } from '@/components/design-system/app/AppPortfolioAllocationDonut'
import type { PortalBundleVaultModule } from '@/lib/portal/bundleProductTypes'

const PERF_MODULE_TYPES = new Set([
  'performancechart',
  'bundleperformancechart',
])

export function normalizeVaultModuleType(type: string): string {
  return type.trim().toLowerCase()
}

export function isVaultModuleEnabled(mod: PortalBundleVaultModule): boolean {
  return mod.enabled !== false
}

export function parseVaultModules(raw: unknown): PortalBundleVaultModule[] {
  if (!Array.isArray(raw)) return []
  return raw
    .filter((m): m is Record<string, unknown> => m != null && typeof m === 'object')
    .map((m) => ({
      id: typeof m.id === 'string' ? m.id : undefined,
      type: String(m.type ?? '').trim(),
      enabled: m.enabled !== false,
      content:
        m.content != null && typeof m.content === 'object' && !Array.isArray(m.content)
          ? (m.content as Record<string, unknown>)
          : {},
    }))
    .filter((m) => m.type.length > 0 && isVaultModuleEnabled(m))
}

/** Corps page bundle : allocation en premier, sans graphique perf (hero). */
export function orderBundleBodyModules(modules: PortalBundleVaultModule[]): PortalBundleVaultModule[] {
  const allocation: PortalBundleVaultModule[] = []
  const rest: PortalBundleVaultModule[] = []

  for (const mod of modules) {
    const norm = normalizeVaultModuleType(mod.type)
    if (norm === 'titlepage') continue
    if (PERF_MODULE_TYPES.has(norm)) continue
    if (norm === 'allocationmodule') {
      allocation.push(mod)
      continue
    }
    rest.push(mod)
  }

  return [...allocation, ...rest]
}

export function findTitlePageModule(
  modules: PortalBundleVaultModule[],
): PortalBundleVaultModule | undefined {
  return modules.find((m) => normalizeVaultModuleType(m.type) === 'titlepage')
}

export function findPerformanceChartModule(
  modules: PortalBundleVaultModule[],
): PortalBundleVaultModule | undefined {
  return modules.find((m) => PERF_MODULE_TYPES.has(normalizeVaultModuleType(m.type)))
}

export function readAllocationSlices(
  content: Record<string, unknown>,
): AppPortfolioAllocationSlice[] {
  const raw = content.slices
  if (!Array.isArray(raw)) return []
  return raw.flatMap((it) => {
    if (it == null || typeof it !== 'object' || Array.isArray(it)) return []
    const row = it as Record<string, unknown>
    const label = typeof row.label === 'string' ? row.label.trim() : ''
    const percentage = Number(row.percentage)
    const colorHex = typeof row.colorHex === 'string' ? row.colorHex.trim() : '#6366F1'
    if (!label || !Number.isFinite(percentage)) return []
    return [{ label, percentage, colorHex }]
  })
}

export function parseBundleChartPoints(raw: unknown): {
  performancePct: number | null
  historyPoints: number[]
} {
  const root = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const points = Array.isArray(root.points) ? root.points : []
  const historyPoints = points
    .map((p) => {
      if (p == null || typeof p !== 'object') return NaN
      return Number((p as Record<string, unknown>).value)
    })
    .filter((v) => Number.isFinite(v))

  const perfRaw = root.performance_pct
  const performancePct =
    typeof perfRaw === 'number' && Number.isFinite(perfRaw) ? perfRaw : null

  return { performancePct, historyPoints }
}
