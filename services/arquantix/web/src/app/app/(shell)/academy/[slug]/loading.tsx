import { PortalArticleSkeleton } from '@/components/portal/PortalRouteSkeleton'

/** Skeleton streamé pendant le chargement SSR de l'article (DB + médias). */
export default function PortalAcademyArticleLoading() {
  return <PortalArticleSkeleton />
}
