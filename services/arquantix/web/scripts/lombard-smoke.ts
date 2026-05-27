/**
 * Smoke checks Lombard V1 readiness (env, Morpho markets, optional HTTP endpoints).
 *
 * Usage:
 *   pnpm lombard:smoke
 *   LOMBARD_SMOKE_BASE_URL=http://localhost:3000 \
 *   LOMBARD_SMOKE_PORTAL_COOKIE="portal_access_token=..." \
 *   LOMBARD_SMOKE_ADMIN_COOKIE="session=..." \
 *   pnpm lombard:smoke --json
 */
import { isLombardV1BetaLimitsEnabled } from '../src/lib/portal/lombard/lombardBetaConfig'
import { isLombardV1Enabled, VANCELIAN_LOMBARD_V1 } from '../src/lib/portal/lombard/lombardConfig'
import { resolveLombardMarket } from '../src/lib/portal/lombard/lombardMarket'

type SmokeCheck = {
  name: string
  ok: boolean
  detail: string
}

const json = process.argv.includes('--json')

function push(checks: SmokeCheck[], name: string, ok: boolean, detail: string) {
  checks.push({ name, ok, detail })
}

async function fetchStatus(url: string, cookie?: string): Promise<{ ok: boolean; status: number; detail: string }> {
  try {
    const res = await fetch(url, {
      headers: cookie ? { Cookie: cookie } : undefined,
      cache: 'no-store',
    })
    const body = await res.text()
    return {
      ok: res.ok,
      status: res.status,
      detail: `HTTP ${res.status} ${body.slice(0, 160)}`,
    }
  } catch (error) {
    return {
      ok: false,
      status: 0,
      detail: error instanceof Error ? error.message : String(error),
    }
  }
}

async function main() {
  const checks: SmokeCheck[] = []

  push(
    checks,
    'feature_flag.lombard_v1_enabled',
    isLombardV1Enabled(),
    isLombardV1Enabled() ? 'LOMBARD_V1_ENABLED is active' : 'LOMBARD_V1_ENABLED=false',
  )

  push(
    checks,
    'feature_flag.beta_limits',
    true,
    isLombardV1BetaLimitsEnabled()
      ? 'LOMBARD_V1_BETA limits enabled'
      : 'beta limits disabled (ok for local smoke)',
  )

  for (const market of VANCELIAN_LOMBARD_V1.markets) {
    try {
      const resolved = await resolveLombardMarket({ collateral: market.collateral })
      const liquidity = resolved.gql.state?.liquidityAssets ?? null
      push(
        checks,
        `market.resolve.${market.collateral}`,
        Boolean(resolved.marketParams.id),
        `marketId=${market.marketId} liquidity=${liquidity ?? 'unknown'}`,
      )
    } catch (error) {
      push(
        checks,
        `market.resolve.${market.collateral}`,
        false,
        error instanceof Error ? error.message : String(error),
      )
    }
  }

  const baseUrl = process.env.LOMBARD_SMOKE_BASE_URL?.trim().replace(/\/$/, '')
  const portalCookie = process.env.LOMBARD_SMOKE_PORTAL_COOKIE?.trim()
  const adminCookie = process.env.LOMBARD_SMOKE_ADMIN_COOKIE?.trim()
  const walletAddress = process.env.LOMBARD_SMOKE_WALLET_ADDRESS?.trim()

  if (baseUrl && portalCookie) {
    const markets = await fetchStatus(`${baseUrl}/api/portal/lombard/markets`, portalCookie)
    push(checks, 'http.markets', markets.ok, markets.detail)

    if (walletAddress) {
      const params = new URLSearchParams({ wallet_address: walletAddress })
      const position = await fetchStatus(
        `${baseUrl}/api/portal/lombard/position?${params.toString()}`,
        portalCookie,
      )
      push(checks, 'http.position', position.ok, position.detail)
    } else {
      push(
        checks,
        'http.position',
        true,
        'skipped — set LOMBARD_SMOKE_WALLET_ADDRESS for authenticated position check',
      )
    }
  } else {
    push(
      checks,
      'http.markets',
      true,
      'skipped — set LOMBARD_SMOKE_BASE_URL + LOMBARD_SMOKE_PORTAL_COOKIE',
    )
    push(checks, 'http.position', true, 'skipped — set portal cookie + wallet address')
  }

  if (baseUrl && adminCookie) {
    const monitoring = await fetchStatus(`${baseUrl}/api/admin/lombard/monitoring`, adminCookie)
    push(checks, 'http.monitoring', monitoring.ok, monitoring.detail)
  } else {
    push(
      checks,
      'http.monitoring',
      true,
      'skipped — set LOMBARD_SMOKE_BASE_URL + LOMBARD_SMOKE_ADMIN_COOKIE',
    )
  }

  const failed = checks.filter((row) => !row.ok)
  const summary = {
    ok: failed.length === 0,
    checks,
    failedCount: failed.length,
  }

  if (json) {
    process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`)
  } else {
    for (const row of checks) {
      console.log(`${row.ok ? 'OK' : 'FAIL'}  ${row.name} — ${row.detail}`)
    }
    console.log(
      failed.length === 0
        ? '[lombard:smoke] all checks passed'
        : `[lombard:smoke] ${failed.length} check(s) failed`,
    )
  }

  process.exit(failed.length > 0 ? 1 : 0)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
