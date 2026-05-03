import type { Metadata } from 'next'
import {
  generateProjectDetailPageMetadata,
  projectDetailPageContent,
} from '@/lib/routes/projectDetailPageShared'

export async function generateMetadata({
  params,
}: {
  params: { slug: string }
}): Promise<Metadata> {
  return generateProjectDetailPageMetadata({ slug: params.slug })
}

export default async function ProjectDetailPage({
  params,
  searchParams,
}: {
  params: { slug: string }
  searchParams: Record<string, string | string[] | undefined>
}) {
  return projectDetailPageContent({
    slug: params.slug,
    searchParams,
    urlLocale: null,
  })
}
