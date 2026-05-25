/** Helpers cookie wagmi sans dépendance wagmi/rainbowkit (safe Server Components). */

/** Reconstruit un en-tête Cookie wagmi à partir de valeurs déjà décodées (Next.js cookies().get). */
export function buildWagmiCookieHeader(storeValue: string | undefined): string | undefined {
  if (!storeValue) return undefined
  return `wagmi.store=${storeValue}`
}

/** Décode les valeurs d'un en-tête Cookie (`%7B…` → `{…}`) pour wagmi. */
export function decodeWagmiCookieHeader(cookieHeader: string): string {
  return cookieHeader
    .split('; ')
    .map((part) => {
      const separator = part.indexOf('=')
      if (separator === -1) return part
      const name = part.slice(0, separator)
      const value = part.slice(separator + 1)
      if (!value.includes('%')) return part
      try {
        return `${name}=${decodeURIComponent(value)}`
      } catch {
        return part
      }
    })
    .join('; ')
}
