import * as React from 'react'
import { cn } from '@/lib/utils'
import { Container } from '@/components/ui/Container'
import { VCmsMedia } from '@/components/design-system/vancelian/VCmsMedia'

export interface VProofStat {
  /**
   * Valeur principale — affichée en Newsreader Display Light 56px.
   * Ex. `"500K"`, `"100 M€"`, `"7 M€"`.
   */
  value: React.ReactNode
  /** Caption sous le chiffre — Inter Regular 13px muted. */
  caption: React.ReactNode
}

export interface VProofStatsProps {
  /** Eyebrow centré au-dessus de la grille (optionnel). */
  eyebrow?: string
  /** Liste de stats — 2 à 6 entrées recommandées (la grille s'adapte). */
  stats: VProofStat[]
  /**
   * Mode `dark` : fond `--v-dark-bg` et texte clair. Utile pour la variante
   * « KeyFigures dark » historique d'Arquantix (en attendant la suppression
   * progressive du fond noir au profit du papier off-white DS).
   */
  tone?: 'light' | 'dark'
  /**
   * Couleur de fond personnalisée — si fournie, prime sur `tone`.
   * (Utilisé par la couche CMS qui passe `backgroundColor`.)
   */
  backgroundColor?: string
  /** Image ou vidéo de fond optionnelle (CMS). */
  backgroundMediaUrl?: string
  backgroundVideoUrl?: string
  /** Opacité de l'image (0–1). */
  backgroundImageOpacity?: number
  /** Teinte d'overlay sur l'image (0–1). */
  overlayOpacity?: number
  className?: string
}

function hexWithOpacity(hex: string, alpha: number): string {
  const v = Math.max(0, Math.min(1, alpha))
  const m = /^#([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return hex
  const r = parseInt(m[1]!.slice(0, 2), 16)
  const g = parseInt(m[1]!.slice(2, 4), 16)
  const b = parseInt(m[1]!.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${v})`
}

/**
 * Vancelian — bandeau de chiffres clés (variante `proof__stats`).
 *
 * Spec DS officielle : voir `components/proof-bar/proof-bar.css`
 * (sélecteurs `.proof__stats`, `.proof__stat`, `.proof__num`, `.proof__caption`).
 *
 * Structure :
 * - Padding vertical 40px (`.proof`) ; en pratique 80–96px pour une vraie
 *   section bandeau (DS : « les chiffres respirent »).
 * - Eyebrow centré au-dessus (color `--v-fg-muted` ou inverse).
 * - Stats : grille flex centrée, gap 96px desktop / 48px mobile.
 * - Chaque stat : `proof__num` Newsreader Light 56px / `proof__caption` 13px muted.
 *
 * Variante `tone="dark"` ou `backgroundColor` : utilisé pour les cas legacy
 * Arquantix où le fond reste sombre (le DS officiel utilise le fond `--v-bg`
 * papier off-white par défaut).
 */
export function VProofStats({
  eyebrow,
  stats,
  tone = 'light',
  backgroundColor,
  backgroundMediaUrl,
  backgroundVideoUrl,
  backgroundImageOpacity = 1,
  overlayOpacity = 0,
  className,
}: VProofStatsProps) {
  const e = typeof eyebrow === 'string' ? eyebrow.trim() : eyebrow
  const list = (stats ?? []).filter((s) => s != null)
  if (list.length === 0) return null

  const isDark = tone === 'dark' || (backgroundColor !== undefined && backgroundColor !== '#F7F7F4')
  const numColor = isDark ? 'text-white' : 'text-v-fg'
  const captionColor = isDark ? 'text-white/65' : 'text-v-fg-muted'
  const eyebrowColor = isDark ? 'text-white/75' : 'text-v-fg-muted'

  const imgOpacity = Math.min(1, Math.max(0, backgroundImageOpacity ?? 1))
  const overlayOp = Math.min(1, Math.max(0, overlayOpacity ?? 0))
  const hasImage = Boolean(backgroundMediaUrl?.trim() || backgroundVideoUrl?.trim())
  const bgFill = backgroundColor ?? (tone === 'dark' ? 'var(--v-dark-bg)' : 'var(--v-bg)')

  return (
    <section
      className={cn('relative w-full overflow-hidden py-20 lg:py-24', className)}
      style={{ backgroundColor: bgFill }}
    >
      {hasImage ? (
        <div className="pointer-events-none absolute inset-0 z-0" aria-hidden>
          <VCmsMedia
            imageUrl={backgroundMediaUrl}
            videoUrl={backgroundVideoUrl}
            autoPlay
            loop
            muted
            playsInline
            preload="auto"
            className="absolute inset-0 h-full w-full object-cover object-center"
            style={{ opacity: imgOpacity }}
          />
          {overlayOp > 0 ? (
            <div
              className="absolute inset-0"
              style={{ backgroundColor: hexWithOpacity(typeof backgroundColor === 'string' ? backgroundColor : '#000000', overlayOp) }}
            />
          ) : null}
        </div>
      ) : null}

      <Container className="relative z-10">
        <div className="flex w-full flex-col items-center gap-12">
          {e ? (
            <p
              className={cn(
                'm-0 text-center font-ui font-medium text-[11px] uppercase tracking-[0.05em]',
                eyebrowColor,
              )}
            >
              {e}
            </p>
          ) : null}

          <ul
            className={cn(
              'm-0 flex w-full list-none flex-wrap items-start justify-center p-0',
              'gap-12 sm:gap-16 lg:gap-24',
            )}
          >
            {list.map((s, i) => (
              <li
                key={i}
                className="flex min-w-[120px] flex-col items-center gap-3 text-center"
              >
                <span
                  className={cn(
                    'font-display font-light leading-[1.05] tracking-[0]',
                    'text-[44px] sm:text-[52px] lg:text-[56px]',
                    numColor,
                  )}
                >
                  {s.value}
                </span>
                <span
                  className={cn(
                    'font-ui font-normal text-[13px] leading-[1.45]',
                    captionColor,
                  )}
                >
                  {s.caption}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </Container>
    </section>
  )
}
