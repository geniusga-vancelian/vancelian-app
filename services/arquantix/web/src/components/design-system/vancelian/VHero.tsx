'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/button'
import { VEditorialTitle } from './VEditorialTitle'
import { useHeroVideoParallax } from '@/hooks/useHeroVideoParallax'

export interface VHeroCta {
  label: React.ReactNode
  onClick?: () => void
  href?: string
  /** `primary` = blanc / anthracite. `secondary` = outline blanc. */
  variant?: 'primary' | 'secondary'
  /** Icône optionnelle à gauche du label (ex. <WhatsAppIcon />). */
  icon?: React.ReactNode
  /** Petite flèche `→` à droite, conventionnelle DS pour le secondaire. */
  trailingArrow?: boolean
}

export interface VHeroProps extends Omit<React.HTMLAttributes<HTMLElement>, 'title'> {
  /** Eyebrow blanc en haut du hero (caption uppercase). */
  eyebrow?: string
  /**
   * Titre du hero — accepte `<em>` pour les accents Newsreader italic.
   * Inter SemiBold clamp(48–96px).
   */
  title?: React.ReactNode
  /** Chapô sous le titre (body 16px). */
  subtitle?: React.ReactNode
  /** Liste de stats inline séparées par un dot (ex. « 500K téléchargements · 100 M€ »). */
  inlineStats?: React.ReactNode[]
  /** 1–2 CTAs. */
  ctas?: VHeroCta[]
  /** Note légale sous les CTA (ex. « Note moyenne 4,6 ★ basée sur 1 600+ avis »). */
  note?: React.ReactNode
  /** URL de l'image de fond (full-bleed). */
  backgroundImage?: string
  /** URL vidéo de fond (prioritaire sur l'image si les deux sont fournis). */
  backgroundVideoUrl?: string
  /** Diffère le chargement vidéo (portail auth) — first paint plus rapide. */
  deferBackgroundVideo?: boolean
  /** Opacité de l'image (0–1) — passé par le CMS. */
  backgroundImageOpacity?: number
  /**
   * `dark` : photo + filtre sombre → texte blanc (le pattern DS officiel).
   * `light` : pas de photo (ou photo claire) → texte anthracite.
   * `secondary` : variant page secondaire — fond clair, plus compact, pas de plein écran.
   */
  variant?: 'dark' | 'light' | 'secondary'
  /** Hauteur minimale du hero — par défaut `100vh` en `dark`, `auto` en `secondary`. */
  minHeight?: 'screen' | 'auto'
  /** Tags (chips) entre le titre et le chapô — usage offres exclusives. */
  tags?: React.ReactNode
  /** ID HTML pour l'anchor (ex. blend nav). */
  id?: string
  /** Animations + parallax vidéo homepage (spec Home.html). */
  homepageMotion?: boolean
  className?: string
}

/**
 * Vancelian — hero éditorial (`hero`).
 *
 * Spec DS officielle : voir `components/hero/hero.css` + `.html` du pack handoff.
 *
 * Trois variantes :
 *
 * 1. **dark** (par défaut quand image) : full-bleed photo + filtre sombre
 *    dégradé gauche→droite, texte blanc. C'est le pattern hero homepage du DS.
 *    Padding bas 64px, padding top 72px (sous nav fixe).
 *
 * 2. **light** : pas d'image (ou image claire), texte anthracite sur fond
 *    `--v-bg`. Idéal pour les pages éditoriales sans photo.
 *
 * 3. **secondary** : page secondaire (offre exclusive, page CMS) — hauteur
 *    auto, padding compact, image optionnelle, conserve la doctrine
 *    typographique mais sans full-screen.
 *
 * Note : la version originale `SectionHero.tsx` gérait beaucoup de cas
 * (opacity CMS, scrim blanc, alignement précis avec la nav transparente).
 * `VHero` reproduit ces comportements en restant fidèle à la spec DS.
 */
export function VHero({
  eyebrow,
  title,
  subtitle,
  inlineStats,
  ctas = [],
  note,
  backgroundImage,
  backgroundVideoUrl,
  backgroundImageOpacity = 1,
  deferBackgroundVideo = false,
  variant = 'dark',
  minHeight,
  tags,
  id,
  homepageMotion = false,
  className,
  ...rest
}: VHeroProps) {
  const videoRef = React.useRef<HTMLVideoElement>(null)
  const hasBgPhoto = typeof backgroundImage === 'string' && backgroundImage.trim() !== ''
  const hasBgVideo = typeof backgroundVideoUrl === 'string' && backgroundVideoUrl.trim() !== ''
  const hasBgMedia = hasBgVideo || hasBgPhoto
  const [loadBackgroundVideo, setLoadBackgroundVideo] = React.useState(
    hasBgVideo && !deferBackgroundVideo,
  )

  React.useEffect(() => {
    if (!deferBackgroundVideo || !hasBgVideo || loadBackgroundVideo) return
    const run = () => setLoadBackgroundVideo(true)
    if (typeof requestIdleCallback !== 'undefined') {
      const id = requestIdleCallback(run, { timeout: 2500 })
      return () => cancelIdleCallback(id)
    }
    const timer = window.setTimeout(run, 600)
    return () => window.clearTimeout(timer)
  }, [deferBackgroundVideo, hasBgVideo, loadBackgroundVideo])

  useHeroVideoParallax(videoRef, homepageMotion && hasBgVideo && loadBackgroundVideo)
  const opacity = Math.min(1, Math.max(0, backgroundImageOpacity ?? 1))
  const e = typeof eyebrow === 'string' ? eyebrow.trim() : eyebrow
  const hasEyebrow = Boolean(e)

  const isDark = variant === 'dark'
  const isSecondary = variant === 'secondary'

  const effectiveMinHeight =
    minHeight ?? (isSecondary || variant === 'light' ? 'auto' : 'screen')

  // Couleurs adaptatives selon le variant
  const titleTone: 'default' | 'inverse' = isDark ? 'inverse' : 'default'
  const onDarkMutedText = 'text-white/85'
  const subColor = isDark ? onDarkMutedText : 'text-v-fg-body'
  const statColor = isDark ? onDarkMutedText : 'text-v-fg-muted'
  const dotColor = isDark ? 'bg-white/60' : 'bg-v-fg-muted'
  const eyebrowColor = isDark ? 'text-white' : 'text-v-fg-muted'
  const noteColor = isDark ? 'text-white/75' : 'text-v-fg-muted'
  const motion = homepageMotion && isDark && !isSecondary

  return (
    <section
      id={id}
      {...rest}
      className={cn(
        'relative isolate w-full overflow-hidden',
        effectiveMinHeight === 'screen' ? 'min-h-screen' : '',
        // Hauteur du topnav Vancelian — strict 72px partout (cf. topnav.css).
        'pt-[72px]',
        // Background : photo full-bleed pour dark, papier off-white sinon.
        isDark ? 'bg-[#0a0a0c]' : 'bg-v-bg',
        className,
      )}
    >
      {hasBgMedia ? (
        <div className="pointer-events-none absolute inset-0 -z-10" aria-hidden>
          {hasBgVideo && loadBackgroundVideo ? (
            <video
              ref={videoRef}
              className="absolute inset-[-10%_0] h-[120%] w-full object-cover object-center max-[720px]:object-[82%_center]"
              autoPlay
              muted
              loop
              playsInline
              preload="metadata"
              src={backgroundVideoUrl}
            />
          ) : hasBgPhoto ? (
            /* eslint-disable-next-line @next/next/no-img-element -- image hero full-bleed pilotée par CSS, mode CMS */
            <img
              src={backgroundImage}
              alt=""
              sizes="100vw"
              decoding="async"
              fetchPriority="high"
              className="h-full w-full object-cover object-center"
              style={{ opacity }}
            />
          ) : null}
          {isDark ? (
            // Filtre sombre dégradé pour lisibilité (gauche→droite, plus dense à gauche)
            <div
              className="absolute inset-0 hidden lg:block"
              style={{
                background:
                  'linear-gradient(to right, rgba(10,10,12,0.62) 0%, rgba(10,10,12,0.45) 45%, rgba(10,10,12,0.28) 75%, rgba(10,10,12,0.18) 100%)',
              }}
            />
          ) : null}
          {isDark ? (
            // Sur mobile/tablette : voile uniforme pour ne pas casser la lisibilité.
            <div className="absolute inset-0 bg-[rgba(10,10,12,0.5)] lg:hidden" />
          ) : null}
        </div>
      ) : null}

      <Container
        className={cn(
          'relative flex items-center',
          effectiveMinHeight === 'screen' ? 'min-h-[calc(100vh-72px)]' : '',
        )}
      >
        <div
          className={cn(
            'w-full',
            isSecondary
              ? 'flex flex-col items-center text-center gap-8 py-20 lg:py-24'
              : isDark
                ? cn('grid grid-cols-1 items-center', motion ? 'py-16' : 'py-16 lg:py-24')
                : 'grid grid-cols-1 items-center py-20 lg:py-32',
          )}
        >
          <div
            className={cn(
              'flex flex-col',
              isSecondary
                ? 'max-w-[760px] mx-auto items-center text-center gap-6'
                : motion
                  ? 'max-w-[640px] gap-0'
                  : 'max-w-[640px] gap-8',
            )}
            {...(motion ? { 'data-v-scroll-fade': true } : {})}
          >
            {hasEyebrow ? (
              <p
                className={cn(
                  'm-0 font-ui font-medium text-[11px] uppercase tracking-[0.05em]',
                  eyebrowColor,
                  motion && 'hero-home-rise hero-home-rise-delay-1 mb-8',
                )}
              >
                {e}
              </p>
            ) : null}

            {title !== undefined && title !== null && title !== '' ? (
              <VEditorialTitle
                as="h1"
                size={isSecondary ? 'page' : 'display'}
                tone={titleTone}
                align={isSecondary ? 'center' : 'left'}
                className={cn(
                  isSecondary ? '' : 'lg:text-left',
                  motion && 'hero-home-rise hero-home-rise-delay-2 mb-8',
                )}
              >
                {title}
              </VEditorialTitle>
            ) : null}

            {tags ? (
              <div className={cn('flex flex-wrap items-center gap-2', motion && 'mb-8')}>
                {tags}
              </div>
            ) : null}

            {subtitle ? (
              <p
                className={cn(
                  'm-0 font-ui font-normal text-[16px] leading-[1.5] max-w-[480px]',
                  subColor,
                  isSecondary ? 'mx-auto' : '',
                  motion && 'hero-home-rise hero-home-rise-delay-3 mb-8',
                )}
              >
                {subtitle}
              </p>
            ) : null}

            {inlineStats && inlineStats.length > 0 ? (
              <div
                className={cn(
                  'flex flex-wrap items-center gap-x-3.5 gap-y-2 font-ui font-medium text-[11px] uppercase tracking-[0.05em]',
                  statColor,
                  motion && 'hero-home-rise hero-home-rise-delay-4 mb-10',
                )}
                aria-label="Indicateurs clés"
              >
                {inlineStats.map((stat, i) => (
                  <React.Fragment key={i}>
                    {i > 0 ? (
                      <span
                        aria-hidden="true"
                        className={cn('h-[2px] w-[2px] rounded-full', dotColor)}
                      />
                    ) : null}
                    <span>{stat}</span>
                  </React.Fragment>
                ))}
              </div>
            ) : null}

            {ctas.length > 0 ? (
              <div
                className={cn(
                  'flex flex-wrap gap-3',
                  motion && 'hero-home-rise hero-home-rise-delay-5 mb-6',
                )}
              >
                {ctas.map((cta, i) => {
                  // En mode `dark`, primary devient blanc → utilise darkPrimary,
                  // secondary devient outline blanc → utilise darkSecondary.
                  const v: 'darkPrimary' | 'darkSecondary' | 'default' | 'outline' = isDark
                    ? cta.variant === 'secondary'
                      ? 'darkSecondary'
                      : 'darkPrimary'
                    : cta.variant === 'secondary'
                      ? 'outline'
                      : 'default'
                  const content = (
                    <>
                      {cta.icon}
                      <span>{cta.label}</span>
                      {cta.trailingArrow ? (
                        <span aria-hidden="true">→</span>
                      ) : null}
                    </>
                  )
                  if (cta.href) {
                    return (
                      <Button key={i} asChild variant={v} size="default">
                        <a href={cta.href} onClick={cta.onClick}>
                          {content}
                        </a>
                      </Button>
                    )
                  }
                  return (
                    <Button key={i} variant={v} size="default" onClick={cta.onClick}>
                      {content}
                    </Button>
                  )
                })}
              </div>
            ) : null}

            {note ? (
              <p
                className={cn(
                  'm-0 font-ui font-normal text-[13px] leading-[1.5]',
                  noteColor,
                  motion && 'hero-home-rise hero-home-rise-delay-6',
                )}
              >
                {note}
              </p>
            ) : null}
          </div>
        </div>
      </Container>
    </section>
  )
}
