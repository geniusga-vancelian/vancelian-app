'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'

import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { SectionHero } from '@/components/sections/SectionHero'
import { Container } from '@/components/ui/Container'
import { VaultModuleWeb } from '@/components/exclusive-offer/VaultModuleWeb'
import { vaultCommonCta } from '@/lib/i18n/vaultCommonCta'
import { getActiveLocaleFromPathname } from '@/lib/i18n/publicLocalizedRouting'

type Props = {
  payload: ExclusiveOfferVaultPayload
}

/**
 * Hero = `SectionHero` secondary DS + image média header + titre/sous-titre du **premier** module `TitlePage`
 * + pastilles du **premier** `TagsModule` (retirés du corps). Corps : autres modules Vault, ordre préservé.
 */
export function ExclusiveOfferVaultDetail({ payload }: Props) {
  const { contentModules, headerImageUrl, heroTitle, heroSubtitle, heroTags } = payload
  const [visibleCount, setVisibleCount] = useState(0)
  const pathname = usePathname() ?? ''
  const loc = getActiveLocaleFromPathname(pathname)

  useEffect(() => {
    if (visibleCount >= contentModules.length) {
      return
    }
    const delayMs = visibleCount === 0 ? 0 : 90
    const t = window.setTimeout(() => {
      setVisibleCount((n) => n + 1)
    }, delayMs)
    return () => window.clearTimeout(t)
  }, [visibleCount, contentModules.length])

  const hasHeroImage =
    typeof headerImageUrl === 'string' && headerImageUrl.trim().length > 0

  const heroTagList =
    Array.isArray(heroTags) && heroTags.length > 0 ? heroTags.slice(0, 10) : undefined

  return (
    <>
      <SectionHero
        variant="secondary"
        backgroundImage={hasHeroImage ? headerImageUrl! : undefined}
        backgroundImageOpacity={1}
        inverseOverlay={hasHeroImage}
        title={heroTitle}
        subtitle={heroSubtitle || undefined}
        tags={heroTagList}
        tagsPresentation="categoryBadges"
        hideCta
      />

      {/* Une seule bande blanche pleine largeur (évite gris sur les côtés entre blocs) */}
      <div className="w-full min-w-0 bg-white pb-16">
        <Container className="pt-6 pb-8 md:pt-8">
          <div className="flex flex-col gap-10">
            {contentModules.slice(0, visibleCount).map((mod) => (
              <article key={mod.id} className="transition-opacity duration-300">
                <VaultModuleWeb mod={mod} />
              </article>
            ))}
          </div>

          {contentModules.length === 0 ? (
            <p className="py-8 text-center text-neutral-500 text-sm">
              {vaultCommonCta(loc, 'vault_no_content')}
            </p>
          ) : null}
        </Container>
      </div>
    </>
  )
}
