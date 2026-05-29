import { cookies } from 'next/headers'

import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'
import { buildWagmiCookieHeader } from '@/lib/wallet/wagmiCookieHeader'

export async function getPortalWeb3LayoutProps() {
  const cookieStore = await cookies()
  return {
    appId: getPrivyAppIdServer(),
    wagmiCookieHeader: buildWagmiCookieHeader(cookieStore.get('wagmi.store')?.value),
  }
}
