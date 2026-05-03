import { cache } from 'react'
import { prisma } from '@/lib/prisma'
import { resolveHomePageCmsSlug } from '@/lib/cms/resolveHomePageCmsSlug'

/** Page CMS qui alimente la home (`/` → redirection ; `/{locale}` pilote phase 2A). */
export const getHomeCmsPage = cache(async () => {
  const homeCmsSlug = await resolveHomePageCmsSlug()
  return prisma.page.findUnique({
    where: { slug: homeCmsSlug },
  })
})
