import {
  getPortalPrivyOtpDevFixedCode,
  isPortalPrivyOtpDevMockEnabled,
} from '@/lib/portal/privyOtpDevMockConfig'

/** Code OTP attendu en mock (ex. 111111), ou null si mock désactivé. */
export function portalPrivyOtpDevMockCode(): string | null {
  return getPortalPrivyOtpDevFixedCode()
}

export function isPortalPrivyOtpDevMockCode(code: string): boolean {
  const expected = portalPrivyOtpDevMockCode()
  if (!expected || !isPortalPrivyOtpDevMockEnabled()) return false
  return code.trim() === expected
}

/** Sujet Privy stable par e-mail — `PRIVY_EXCHANGE_VERIFICATION_MODE=stub` côté API. */
export function buildPrivyDevStubExternalSubject(email: string): string {
  const normalized = email.trim().toLowerCase()
  return `local-dev:${normalized}`
}

export function buildPrivyDevStubAccessToken(email: string): string {
  return `stub:${buildPrivyDevStubExternalSubject(email)}`
}

/** Hex 40 caractères déterministe (aligné Flutter `PrivyOtpDevMock`). */
function deterministicHex40(input: string): string {
  const norm = input.trim().toLowerCase()
  let state = [...norm].reduce((acc, ch) => (acc * 65599 + ch.charCodeAt(0)) & 0x7fffffff, 0)
  let hex = ''
  while (hex.length < 40) {
    state = (state * 1103515245 + 12345) & 0x7fffffff
    hex += state.toString(16).padStart(8, '0')
  }
  return hex.slice(0, 40)
}

/** Adresse EVM mock unique par e-mail — évite fusion avec wallets Privy prod. */
export function buildPrivyDevMockWalletAddress(email: string): string {
  return `0x${deterministicHex40(email)}`
}

export function buildPrivyDevMockWalletId(email: string): string {
  return `local_mock_${deterministicHex40(email).slice(0, 16)}`
}
