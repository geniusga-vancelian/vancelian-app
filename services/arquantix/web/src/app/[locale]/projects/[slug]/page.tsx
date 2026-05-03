import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { isValidLocale } from '@/config/locales'
import {
  generateProjectDetailPageMetadata,
  projectDetailPageContent,
} from '@/lib/routes/projectDetailPageShared'

type Props = {
  params: { locale: string; slug: string }
  searchParams: Record<string, string | string[] | undefined>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  if (!isValidLocale(params.locale)) {
    return {}
  }
  return generateProjectDetailPageMetadata({ slug: params.slug })
}

export default async function LocalizedExclusiveOfferDetailPage({
  params,
  searchParams,
}: Props) {
  if (!isValidLocale(params.locale)) {
    notFound()
  }

  return projectDetailPageContent({
    slug: params.slug,
    searchParams,
    urlLocale: params.locale,
  })
}
