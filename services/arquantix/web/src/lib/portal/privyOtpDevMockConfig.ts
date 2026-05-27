/** Mock OTP Privy local (dev uniquement) — aligné sur TWO_FACTOR_DEV_FIXED_CODE / sandboxes Morpho. */

const DEV_OTP_RE = /^\d{6}$/

function readMockEnabledRaw(): boolean {
  return (
    process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED?.trim().toLowerCase() === 'true'
  )
}

/** Stack locale : dev Next ou Docker recovery (`ARQUANTIX_ALLOW_UNAUTHENTICATED_APP_ROUTES=1`). */
function isLocalArquantixRuntime(): boolean {
  if (process.env.NODE_ENV !== 'production') return true
  return process.env.ARQUANTIX_ALLOW_UNAUTHENTICATED_APP_ROUTES?.trim() === '1'
}

export function assertPortalPrivyOtpDevMockProductionGuard(): void {
  if (!isLocalArquantixRuntime() && readMockEnabledRaw()) {
    throw new Error('PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED cannot be true in production')
  }
}

/** OTP Privy simulé en local (pas d’e-mail Privy, code fixe). */
export function isPortalPrivyOtpDevMockEnabled(): boolean {
  assertPortalPrivyOtpDevMockProductionGuard()
  return readMockEnabledRaw() && isLocalArquantixRuntime()
}

export function getPortalPrivyOtpDevFixedCode(): string | null {
  if (!isPortalPrivyOtpDevMockEnabled()) return null
  const raw =
    process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE?.trim() ||
    process.env.NEXT_PUBLIC_TWO_FACTOR_DEV_FIXED_CODE?.trim() ||
    '111111'
  return DEV_OTP_RE.test(raw) ? raw : null
}
