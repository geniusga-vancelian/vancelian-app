declare module '@privy-auth-internal/provider' {
  export type PrivyCaptchaHookState = {
    enabled: boolean
    status: 'disabled' | 'ready' | 'loading' | 'success' | 'error'
    error?: string
    reset: () => void
    execute: () => void
    waitForResult: () => Promise<string>
  }

  export function useCaptcha(): PrivyCaptchaHookState
}

declare module '@privy-auth-internal/context' {
  type AuthFlow = {
    meta?: {
      email?: string
      captchaToken?: string
    }
    sendCodeEmail?: (args: {
      email?: string
      captchaToken?: string
      withPrivyUi?: boolean
    }) => Promise<unknown>
  }

  export function usePrivyInternal(): {
    getAuthFlow: () => AuthFlow | null | undefined
    resendEmailCode: () => Promise<void>
    initLoginWithEmail: (args: {
      email: string
      captchaToken?: string
      disableSignup?: boolean
      withPrivyUi?: boolean
    }) => Promise<void>
  }
}
