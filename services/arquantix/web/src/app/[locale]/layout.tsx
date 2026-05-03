import { notFound } from 'next/navigation'
import { isValidLocale } from '@/config/locales'

/**
 * Segment `/{locale}` — rejette les locales invalides (évite capturer `/de/...` comme locale).
 */
export default function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { locale: string }
}) {
  if (!isValidLocale(params.locale)) {
    notFound()
  }
  return <>{children}</>
}
