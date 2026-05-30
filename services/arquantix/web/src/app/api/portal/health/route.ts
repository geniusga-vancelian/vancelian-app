import { NextResponse } from 'next/server'
import {
  getPrivyAppId,
  getPrivyAppIdServer,
  getPrivyWebClientId,
  isPrivyConfigured,
} from '@/lib/portal/privyConfig'
import { getBackendBaseUrl } from '@/lib/backend'
import {
  getPortalPrivyOtpDevFixedCode,
  isPortalPrivyOtpDevMockEnabled,
} from '@/lib/portal/privyOtpDevMockConfig'
import { isMorphoLocalSandboxEnabled } from '@/lib/portal/morphoLocalSandboxConfig'

export const dynamic = 'force-dynamic'

/** Diagnostic portail — vérifie env + reachability API (sans exposer de secrets). */
export async function GET() {
  const privyAppId = getPrivyAppIdServer() || getPrivyAppId()
  const privyWebClientId = getPrivyWebClientId()

  let apiHealth: number | null = null
  try {
    const res = await fetch(`${getBackendBaseUrl()}/health`, { cache: 'no-store' })
    apiHealth = res.status
  } catch {
    apiHealth = null
  }

  return NextResponse.json({
    privyConfigured: isPrivyConfigured(privyAppId),
    privyAppIdPrefix: privyAppId ? privyAppId.slice(0, 8) : null,
    privyWebClientIdConfigured: Boolean(privyWebClientId),
    privyWebClientIdPrefix: privyWebClientId ? privyWebClientId.slice(0, 12) : null,
    note:
      'Do not use PRIVY_APP_CLIENT_ID from Flutter on web — it is a mobile app client and triggers Invalid nativeAppID.',
    backendUrl: getBackendBaseUrl(),
    apiHealth,
    privyOtpDevMockEnabled: isPortalPrivyOtpDevMockEnabled(),
    privyOtpDevMockCode: getPortalPrivyOtpDevFixedCode(),
    morphoLocalSandboxEnabled: (() => {
      try {
        return isMorphoLocalSandboxEnabled()
      } catch {
        return false
      }
    })(),
  })
}
