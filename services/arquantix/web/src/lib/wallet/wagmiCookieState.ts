import type { Config, State } from 'wagmi'
import { cookieToInitialState } from 'wagmi'

import { decodeWagmiCookieHeader } from '@/lib/wallet/wagmiCookieHeader'

/** Hydratation wagmi côté client — tolère cookies URL-encodés ou corrompus. */
export function resolveWagmiInitialState(
  config: Config,
  args?: { cookieHeader?: string; initialState?: State },
): State | undefined {
  if (args?.initialState) return args.initialState
  if (!args?.cookieHeader) return undefined

  try {
    return cookieToInitialState(config, args.cookieHeader)
  } catch {
    try {
      return cookieToInitialState(config, decodeWagmiCookieHeader(args.cookieHeader))
    } catch {
      return undefined
    }
  }
}
