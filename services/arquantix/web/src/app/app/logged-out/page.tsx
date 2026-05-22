import type { Metadata } from 'next'
import Link from 'next/link'
import { BrandLogo } from '@/components/ui/BrandLogo'
import { defaultLocale } from '@/config/locales'
import { getSiteBrandLogo } from '@/lib/cms/site-footer'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import '@/styles/portal-auth.css'

export const metadata: Metadata = {
  title: 'Vancelian — Signed out',
  robots: { index: false, follow: false },
}

/** Page légère post-logout — sans Privy ni hero vidéo. */
export default async function PortalLoggedOutPage() {
  let brand: Awaited<ReturnType<typeof getSiteBrandLogo>> | null = null
  try {
    brand = await getSiteBrandLogo(defaultLocale)
  } catch {
    brand = null
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-v-bg px-6 py-16">
      <BrandLogo brand={brand} lockup="horizontal" color="black" className="h-8 w-auto sm:h-9" />
      <p className="mt-8 max-w-sm text-center font-ui text-[15px] leading-relaxed text-v-fg-body">
        You have been signed out of your account.
      </p>
      <Link
        href={PORTAL_ROUTES.login}
        className="portal-auth__btn portal-auth__btn--primary portal-auth__btn--lg mt-8 inline-flex min-w-[200px] items-center justify-center no-underline"
      >
        <span>Sign in again</span>
        <span className="portal-auth__btn-arrow" aria-hidden="true">
          →
        </span>
      </Link>
    </div>
  )
}
