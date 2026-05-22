'use client'

/**
 * Hooks internes Privy — même build CJS que @privy-io/react-auth côté client
 * (alias webpack dans next.config.js) pour partager le contexte React captcha.
 */
export { useCaptcha } from '@privy-auth-internal/provider'
export { usePrivyInternal } from '@privy-auth-internal/context'

export type { PrivyCaptchaHookState as PrivyCaptchaState } from '@privy-auth-internal/provider'
