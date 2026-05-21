/**
 * Config Privy — portail web.
 *
 * Important : le `PRIVY_APP_CLIENT_ID` Flutter est un **app client mobile**
 * (bundle iOS / package Android). Le passer au SDK React provoque
 * « Invalid nativeAppID ». Sur le web, on utilise uniquement l'appId,
 * ou un client web dédié (`NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID`) créé dans le
 * dashboard Privy (Allowed origins : http://localhost:3100, etc.).
 */
/** Côté serveur (layout, API) — `PRIVY_APP_ID` injecté par ECS / Secrets Manager. */
export function getPrivyAppIdServer(): string {
  return (
    process.env.PRIVY_APP_ID?.trim() ||
    process.env.NEXT_PUBLIC_PRIVY_APP_ID?.trim() ||
    ''
  )
}

/** Côté client — repli sur la prop passée par le layout serveur. */
export function getPrivyAppId(): string {
  return (
    process.env.NEXT_PUBLIC_PRIVY_APP_ID?.trim() ||
    process.env.PRIVY_APP_ID?.trim() ||
    ''
  )
}

/** Client ID web optionnel — ne jamais réutiliser le client mobile Flutter. */
export function getPrivyWebClientId(): string {
  return process.env.NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID?.trim() || ''
}

/** @deprecated Utiliser getPrivyWebClientId — conservé pour compat interne. */
export function getPrivyAppClientId(): string {
  return getPrivyWebClientId()
}

export function isPrivyConfigured(appIdOverride?: string): boolean {
  return Boolean((appIdOverride || getPrivyAppId()).trim())
}

export function privyProviderProps(appIdOverride?: string): {
  appId: string
  clientId?: string
} {
  const appId = (appIdOverride || getPrivyAppId()).trim()
  const webClientId = getPrivyWebClientId()
  return webClientId ? { appId, clientId: webClientId } : { appId }
}
