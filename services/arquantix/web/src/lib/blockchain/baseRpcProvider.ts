import { createPublicClient, fallback, http } from 'viem'
import { base } from 'viem/chains'

/** RPC public Base — dernier recours uniquement, jamais provider principal. */
export const PUBLIC_BASE_RPC_LAST_RESORT = 'https://mainnet.base.org'

const RPC_HTTP_TIMEOUT_MS = 12_000
const RPC_RETRY_COUNT = 2
const RPC_RETRY_DELAY_MS = 350

export type BaseRpcSide = 'server' | 'client'

function readEnv(name: string): string | undefined {
  const value = process.env[name]?.trim()
  return value || undefined
}

function isPublicBaseRpc(url: string): boolean {
  try {
    return new URL(url).hostname.includes('base.org')
  } catch {
    return url.includes('mainnet.base.org')
  }
}

function pushUnique(urls: string[], url: string | undefined): void {
  if (!url) return
  if (!urls.includes(url)) urls.push(url)
}

/** URLs RPC Base ordonnées (primary → fallback). */
export function resolveBaseRpcUrls(options?: { side?: BaseRpcSide }): string[] {
  const side = options?.side ?? 'server'
  const urls: string[] = []

  if (side === 'client') {
    pushUnique(urls, readEnv('NEXT_PUBLIC_BASE_RPC_URL'))
    pushUnique(urls, readEnv('NEXT_PUBLIC_BASE_RPC_URL_FALLBACK'))
    if (urls.length === 0) {
      urls.push(PUBLIC_BASE_RPC_LAST_RESORT)
    }
    return urls
  }

  const primary = readEnv('BASE_RPC_URL_PRIMARY') ?? readEnv('BASE_RPC_URL')
  const fallbackUrl = readEnv('BASE_RPC_URL_FALLBACK')
  const nextPublic = readEnv('NEXT_PUBLIC_BASE_RPC_URL')

  pushUnique(urls, primary)
  if (nextPublic && nextPublic !== primary) pushUnique(urls, nextPublic)
  pushUnique(urls, fallbackUrl)

  if (urls.length === 0) {
    urls.push(PUBLIC_BASE_RPC_LAST_RESORT)
    return urls
  }

  if (!urls.some((url) => isPublicBaseRpc(url))) {
    pushUnique(urls, PUBLIC_BASE_RPC_LAST_RESORT)
  }

  return urls
}

export function isPublicBaseRpcPrimary(): boolean {
  const urls = resolveBaseRpcUrls({ side: 'server' })
  return urls.length > 0 && isPublicBaseRpc(urls[0]!)
}

/** Label court pour monitoring (sans exposer la clé API). */
export function labelBaseRpcUrl(url: string): string {
  try {
    const hostname = new URL(url).hostname.toLowerCase()
    if (hostname.includes('alchemy')) return 'alchemy'
    if (hostname.includes('quicknode')) return 'quicknode'
    if (hostname.includes('infura')) return 'infura'
    if (hostname.includes('base.org')) return 'public-base'
    return hostname
  } catch {
    return 'unknown'
  }
}

function createFallbackTransport(urls: string[]) {
  const transports = urls.map((url) =>
    http(url, {
      timeout: RPC_HTTP_TIMEOUT_MS,
      retryCount: RPC_RETRY_COUNT,
      retryDelay: RPC_RETRY_DELAY_MS,
    }),
  )
  return fallback(transports, { rank: false })
}

/** Client viem Base avec fallback multi-provider + retry. */
export function createBasePublicClient(options?: { side?: BaseRpcSide }) {
  const urls = resolveBaseRpcUrls(options)
  return createPublicClient({
    chain: base,
    transport: createFallbackTransport(urls),
  })
}

export type BasePublicClient = ReturnType<typeof createBasePublicClient>

export type BaseRpcProviderProbe = {
  label: string
  ok: boolean
  latencyMs?: number
  error?: string
  isPublic: boolean
}

export type BaseRpcHealthSnapshot = {
  ok: boolean
  latencyMs?: number
  error?: string
  activeProvider?: string
  usedFallback: boolean
  publicRpcAsPrimary: boolean
  providers: BaseRpcProviderProbe[]
}

/** Ping individuel + client fallback pour monitoring admin. */
export async function checkBaseRpcHealth(options?: { side?: BaseRpcSide }): Promise<BaseRpcHealthSnapshot> {
  const side = options?.side ?? 'server'
  const urls = resolveBaseRpcUrls({ side })
  const publicRpcAsPrimary = urls.length > 0 && isPublicBaseRpc(urls[0]!)

  const providers: BaseRpcProviderProbe[] = []
  for (const url of urls) {
    const label = labelBaseRpcUrl(url)
    const started = Date.now()
    try {
      const client = createPublicClient({
        chain: base,
        transport: http(url, { timeout: RPC_HTTP_TIMEOUT_MS, retryCount: 0 }),
      })
      await client.getBlockNumber()
      providers.push({
        label,
        ok: true,
        latencyMs: Date.now() - started,
        isPublic: isPublicBaseRpc(url),
      })
    } catch (error) {
      providers.push({
        label,
        ok: false,
        latencyMs: Date.now() - started,
        error: error instanceof Error ? error.message : 'RPC error',
        isPublic: isPublicBaseRpc(url),
      })
    }
  }

  const startedFallback = Date.now()
  try {
    const client = createBasePublicClient({ side })
    await client.getBlockNumber()
    const latencyMs = Date.now() - startedFallback
    const firstOk = providers.find((row) => row.ok)
    const activeProvider = firstOk?.label ?? providers[0]?.label
    const usedFallback = Boolean(firstOk && providers.indexOf(firstOk) > 0)

    return {
      ok: true,
      latencyMs,
      activeProvider,
      usedFallback,
      publicRpcAsPrimary,
      providers,
    }
  } catch (error) {
    return {
      ok: false,
      latencyMs: Date.now() - startedFallback,
      error: error instanceof Error ? error.message : 'RPC Base indisponible',
      activeProvider: providers.find((row) => row.ok)?.label,
      usedFallback: false,
      publicRpcAsPrimary,
      providers,
    }
  }
}
