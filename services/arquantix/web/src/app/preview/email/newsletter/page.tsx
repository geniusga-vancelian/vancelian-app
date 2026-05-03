import type { Metadata } from 'next'
import { headers } from 'next/headers'
import { NewsletterExample } from '@/email-ds'

export const metadata: Metadata = {
  title: 'Newsletter — preview',
  description: 'Aperçu chrome-free de la newsletter Arquantix (DS e-mail).',
  robots: { index: false, follow: false },
}

export const dynamic = 'force-dynamic'

/**
 * Preview isolée de la newsletter — rendue à la taille canonique 600 px,
 * sans coquille site ni sidebar admin, pour coller au rendu client mail.
 */
export default async function NewsletterPreviewPage() {
  const h = await headers()
  const host = h.get('host')
  const proto = h.get('x-forwarded-proto') ?? 'http'
  const assetOrigin = host ? `${proto}://${host}` : undefined
  return <NewsletterExample assetOrigin={assetOrigin} />
}
