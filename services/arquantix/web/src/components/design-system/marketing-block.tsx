"use client";

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { SectionTitle } from '@/components/design-system/extracted';
import { cn } from '@/lib/utils';
import svgPaths from './imports/Footer/svg-ydimge091p';

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const h = hex.replace(/^#/, '').trim();
  if (h.length === 3) {
    return {
      r: parseInt(h[0] + h[0], 16),
      g: parseInt(h[1] + h[1], 16),
      b: parseInt(h[2] + h[2], 16),
    };
  }
  if (h.length === 6) {
    return {
      r: parseInt(h.slice(0, 2), 16),
      g: parseInt(h.slice(2, 4), 16),
      b: parseInt(h.slice(4, 6), 16),
    };
  }
  return null;
}

export function hexWithOpacity(hex: string | undefined, opacity: number): string {
  const rgb = hexToRgb(hex || '#000000');
  const a = Math.min(1, Math.max(0, opacity));
  if (!rgb) return `rgba(0,0,0,${a})`;
  return `rgba(${rgb.r},${rgb.g},${rgb.b},${a})`;
}

export interface MarketingBlockProps {
  /** Surtitre au-dessus du titre (petites caps ; filets gauche/droite gérés par le composant) */
  eyebrow?: string;
  /** Titre principal du bloc */
  title: string;
  /** Sous-titre optionnel (uniquement pour variante 'image') */
  subtitle?: string;
  /** Texte du bouton CTA */
  buttonText: string;
  /** Variante du bloc */
  variant: 'gradient' | 'image';
  /** Image de fond (pour variante 'image') */
  backgroundImage?: string;
  /** Opacité de l'overlay au-dessus de l'image (0–1) */
  overlayOpacity?: number;
  /** Couleur de l'overlay / teinte (hex, ex. #000000) */
  overlayColor?: string;
  /** Fond plein si pas d'image (hex) */
  fallbackBackgroundColor?: string;
  /** Opacité de l’image sur le fond (variante image avec fond interne) */
  backgroundImageOpacity?: number;
  /** Callback au clic du bouton */
  onButtonClick?: () => void;
  /** Second bouton (variante image, style contour blanc) */
  secondaryButtonText?: string;
  onSecondaryButtonClick?: () => void;
  /** Masque le bouton principal (variantes gradient + image). */
  showPrimaryButton?: boolean;
  /** Masque le bouton secondaire (variante image). */
  showSecondaryButton?: boolean;
  /** Sous-titre au format Markdown (par défaut : oui pour le CTA CMS). */
  subtitleAsMarkdown?: boolean;
  /** Centré ou justifié pour le corps (sous-titre / description). */
  contentTextAlign?: 'center' | 'justify';
  /**
   * Si true : surtitre + titre restent centrés ; seul le corps suit `contentTextAlign`.
   * (Module CTA CMS : « Alignement du titre et du texte » ne concerne que le texte.)
   */
  titleAlwaysCenter?: boolean;
  /** Hauteur personnalisée (défaut: 506px pour gradient, min-height pour image) */
  height?: string;
  /**
   * Variante image uniquement : n’affiche que titre / texte / boutons (pas de fond).
   * À utiliser quand le fond plein écran est rendu par le parent (ex. SectionCTA).
   */
  contentOnly?: boolean;
  /** Classes sur le bloc description (sous-titre), ex. alignement largeur éditoriale CMS. */
  subtitleClassName?: string;
}

/**
 * Surtitre aligné ProjetGallery / homepage : filets verticaux gauche-droite, 14px Heavy uppercase.
 * `onDark` : CTA image / fond sombre (filets et texte clairs).
 * `onLightWarm` : bandeau gradient rose-orange (filets et texte #62656e, comme la grille d’offres).
 */
function CtaEyebrow({
  text,
  alignCenter,
  surface,
}: {
  text: string
  alignCenter: boolean
  surface: 'onDark' | 'onLightWarm'
}) {
  const t = text.trim()
  if (!t) return null
  const dark = surface === 'onDark'
  return (
    <div
      className={cn(
        'relative flex shrink-0 content-stretch items-center justify-center rounded-[2px] px-[4px] py-[2px]',
        alignCenter ? 'mx-auto' : '',
      )}
    >
      <div
        aria-hidden="true"
        className={cn(
          'pointer-events-none absolute inset-0 rounded-[2px] border-solid border-l border-r',
          dark ? 'border-white/50' : 'border-[#62656e]',
        )}
      />
      <p
        className={cn(
          "relative whitespace-nowrap font-['Avenir:Heavy',sans-serif] text-[14px] uppercase leading-none not-italic",
          dark ? 'text-white' : 'text-[#62656e]',
        )}
      >
        {t}
      </p>
    </div>
  )
}

function CtaRichText({
  markdown,
  align,
  className,
}: {
  markdown: string
  align: 'center' | 'justify'
  className?: string
}) {
  const center = align === 'center'
  return (
    <div
      className={cn(
        'prose prose-invert max-w-none font-[\'Avenir:Roman\',sans-serif] text-[18px] leading-[1.6] text-white/95',
        'prose-p:mt-0 prose-p:mb-4 last:prose-p:mb-0 prose-headings:text-white prose-strong:text-white',
        'prose-a:text-white prose-a:underline prose-li:text-white/95',
        center
          ? 'mx-auto max-w-[640px] text-center prose-headings:text-center prose-p:text-center'
          : 'w-full text-justify prose-p:text-justify prose-headings:text-justify',
        className,
      )}
    >
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </div>
  )
}

/**
 * MarketingBlock - Composant de bloc marketing/CTA pour Arquantix
 * 
 * Deux variantes disponibles:
 * - 'gradient': Fond dégradé rose/orange avec décoration SVG
 * - 'image': Fond image avec overlay sombre et sous-titre optionnel
 * 
 * @example
 * ```tsx
 * <MarketingBlock
 *   variant="gradient"
 *   title="Access fractional real estate with institutional confidence."
 *   buttonText="Enter the investment platform"
 *   onButtonClick={() => console.log('CTA clicked')}
 * />
 * ```
 */
export function MarketingBlock({
  eyebrow,
  title,
  subtitle,
  buttonText,
  variant,
  backgroundImage,
  overlayOpacity = 0.8,
  overlayColor = '#000000',
  fallbackBackgroundColor,
  backgroundImageOpacity = 1,
  onButtonClick,
  secondaryButtonText,
  onSecondaryButtonClick,
  showPrimaryButton = true,
  showSecondaryButton = true,
  subtitleAsMarkdown = true,
  contentTextAlign = 'center',
  height,
  contentOnly = false,
  subtitleClassName,
  titleAlwaysCenter = false,
}: MarketingBlockProps) {
  const defaultHeight = variant === 'gradient' ? '506px' : '454px';
  const blockHeight = height || defaultHeight;
  const bodyAlignCenter = contentTextAlign !== 'justify';
  const titleAlignCenter = titleAlwaysCenter ? true : bodyAlignCenter;
  const primaryVisible =
    showPrimaryButton && Boolean(buttonText?.trim());
  const secondaryVisible =
    showSecondaryButton &&
    Boolean(secondaryButtonText?.trim()) &&
    Boolean(onSecondaryButtonClick);
  const showButtonRow = primaryVisible || secondaryVisible;

  if (variant === 'gradient') {
    return (
      <div
        className="relative shrink-0 w-full"
        style={{ height: blockHeight }}
        data-name="Marketing Block - Gradient"
      >
        <div className="flex size-full flex-col items-center justify-center overflow-clip rounded-[inherit]">
          <div className="flex w-full flex-col items-center justify-center px-0 pb-24 pt-10 md:pb-32 md:pt-14">
            <div className="relative min-h-px min-w-0 w-full flex-1 rounded-[10px] bg-gradient-to-r from-[#e885d0] to-[#ffb84d]">
              <div className="flex size-full flex-col items-center justify-center overflow-clip rounded-[inherit]">
                <div className="relative flex size-full flex-col items-center justify-center px-4 py-10 sm:px-6 md:px-8 md:py-12">
                  <div
                    className={cn(
                      'relative z-[1] flex w-full min-w-0 max-w-[900px] flex-col justify-center gap-[30px]',
                      bodyAlignCenter ? 'items-center' : 'items-stretch',
                    )}
                  >
                  {/* Surtitre + titre */}
                  <div
                    className={cn(
                      'content-stretch flex flex-col relative shrink-0 w-full gap-[10px]',
                      titleAlignCenter ? 'items-center' : 'items-stretch',
                    )}
                  >
                    {eyebrow ? (
                      <CtaEyebrow
                        text={eyebrow}
                        alignCenter={titleAlignCenter}
                        surface="onLightWarm"
                      />
                    ) : null}
                    <SectionTitle
                      as="h1"
                      size="module"
                      align={titleAlignCenter ? 'center' : 'left'}
                      color="#ffffff"
                      className={cn('whitespace-pre-wrap', !titleAlignCenter && 'text-justify')}
                    >
                      {title}
                    </SectionTitle>
                  </div>

                  {subtitle ? (
                    subtitleAsMarkdown ? (
                      <CtaRichText
                        markdown={subtitle}
                        align={contentTextAlign}
                        className={subtitleClassName}
                      />
                    ) : (
                      <p
                        className={cn(
                          'max-w-[640px] font-[\'Avenir:Roman\',sans-serif] text-[18px] leading-[1.6] text-white/95',
                          bodyAlignCenter ? 'text-center' : 'w-full max-w-none text-justify',
                          subtitleClassName,
                        )}
                      >
                        {subtitle}
                      </p>
                    )
                  ) : null}

                  {/* CTA Button */}
                  {primaryVisible ? (
                    <button
                      onClick={onButtonClick}
                      className="bg-white content-stretch flex h-[36px] items-center justify-center px-[16px] py-[10px] relative rounded-[999px] shrink-0 hover:bg-gray-100 transition-colors cursor-pointer"
                    >
                      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black tracking-[0.06px] uppercase whitespace-nowrap">
                        {buttonText}
                      </p>
                    </button>
                  ) : null}
                  </div>

                  {/* SVG Decoration */}
                  <div
                    className="pointer-events-none absolute flex inset-[-70.65%_-52.45%_-158.91%_-52.41%] items-center justify-center"
                    style={{ containerType: 'size' }}
                  >
                    <div className="-rotate-15 flex-none h-[hypot(4.92326cqw,41.902cqh)] w-[hypot(95.0767cqw,-58.098cqh)]">
                      <div className="relative size-full">
                        <div className="absolute inset-[0_-1.54%_-3.78%_-0.44%]">
                          <svg
                            className="block size-full"
                            fill="none"
                            preserveAspectRatio="none"
                            viewBox="0 0 2368.92 465.91"
                          >
                            <g opacity="0.2">
                              <path
                                d={svgPaths.p35b225f0}
                                stroke="white"
                                strokeMiterlimit="10"
                                strokeWidth="30"
                              />
                              <path
                                d={svgPaths.p366dcff0}
                                stroke="white"
                                strokeMiterlimit="10"
                                strokeWidth="30"
                              />
                            </g>
                          </svg>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Variant: image — contenu seul (fond géré par le parent, plein écran)
  if (variant === "image" && contentOnly) {
    return (
      <div
        className="relative w-full"
        data-name="Marketing Block - Image Content"
      >
        <div className="relative flex w-full flex-col items-center justify-center">
          <div
            className={cn(
              'relative mx-auto flex w-full min-w-0 max-w-[900px] flex-col gap-[30px] px-4 py-12 sm:px-6 md:px-8 md:py-16',
              bodyAlignCenter ? 'items-center justify-center' : 'items-stretch justify-center',
            )}
          >
            <div
              className={cn(
                'content-stretch flex w-full flex-col gap-[24px] not-italic',
                bodyAlignCenter ? 'items-center' : 'items-stretch',
              )}
            >
              <div
                className={cn(
                  'flex w-full flex-col gap-[10px]',
                  titleAlignCenter ? 'items-center' : 'items-stretch',
                )}
              >
                {eyebrow ? (
                  <CtaEyebrow
                    text={eyebrow}
                    alignCenter={titleAlignCenter}
                    surface="onDark"
                  />
                ) : null}
                <SectionTitle
                  as="h2"
                  size="module"
                  align={titleAlignCenter ? 'center' : 'left'}
                  color="#ffffff"
                  className={cn('whitespace-pre-wrap', !titleAlignCenter && 'text-justify')}
                >
                  {title}
                </SectionTitle>
              </div>
              {subtitle ? (
                subtitleAsMarkdown ? (
                  <CtaRichText
                    markdown={subtitle}
                    align={contentTextAlign}
                    className={subtitleClassName}
                  />
                ) : (
                  <p
                    className={cn(
                      'font-[\'Avenir:Roman\',sans-serif] text-[18px] leading-[1.6] text-white/95',
                      bodyAlignCenter ? 'max-w-[640px] text-center' : 'w-full text-justify',
                      subtitleClassName,
                    )}
                  >
                    {subtitle}
                  </p>
                )
              ) : null}
            </div>

            {showButtonRow ? (
              <div className="flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center sm:justify-center sm:gap-4">
                {primaryVisible ? (
                  <button
                    type="button"
                    onClick={onButtonClick}
                    className="flex h-11 min-h-[44px] flex-none cursor-pointer items-center justify-center rounded-[999px] bg-white px-5 transition-colors hover:bg-gray-100"
                  >
                    <span className="font-['Avenir:Heavy',sans-serif] text-[12px] uppercase tracking-[0.06px] text-black">
                      {buttonText}
                    </span>
                  </button>
                ) : null}
                {secondaryVisible ? (
                  <button
                    type="button"
                    onClick={onSecondaryButtonClick}
                    className="flex h-11 min-h-[44px] flex-none cursor-pointer items-center justify-center rounded-[999px] border border-white bg-transparent px-5 transition-colors hover:bg-white/10"
                  >
                    <span className="font-['Avenir:Heavy',sans-serif] text-[12px] uppercase tracking-[0.06px] text-white">
                      {secondaryButtonText}
                    </span>
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  // Variant: image (carte avec fond interne — ex. aperçus DS)
  const imageVariantHeight = height
    ? { height: blockHeight }
    : { minHeight: defaultHeight };
  const solidFallback =
    !backgroundImage && fallbackBackgroundColor
      ? fallbackBackgroundColor
      : !backgroundImage
        ? hexWithOpacity(overlayColor, 1)
        : undefined;

  return (
    <div
      className="relative shrink-0 w-full overflow-hidden rounded-[10px]"
      style={{ ...imageVariantHeight, backgroundColor: solidFallback }}
      data-name="Marketing Block - Image"
    >
      {backgroundImage && (
        <div aria-hidden="true" className="pointer-events-none absolute inset-0">
          <div
            className="absolute inset-0"
            style={{
              backgroundColor:
                fallbackBackgroundColor ||
                (overlayColor ? hexWithOpacity(overlayColor, 1) : '#000000'),
            }}
          />
          <img
            alt=""
            className="absolute inset-0 size-full max-w-none object-cover object-center"
            src={backgroundImage}
            sizes="(max-width: 1280px) 100vw, 1280px"
            style={{
              opacity: Math.min(1, Math.max(0, backgroundImageOpacity ?? 1)),
            }}
          />
          {(overlayOpacity ?? 0) > 0 ? (
            <div
              className="absolute inset-0"
              style={{
                backgroundColor: hexWithOpacity(
                  overlayColor,
                  overlayOpacity ?? 0.55,
                ),
              }}
            />
          ) : null}
        </div>
      )}

      <div className="relative flex min-h-[inherit] w-full flex-col items-center justify-center">
        <div
          className={cn(
            'relative mx-auto flex w-full min-w-0 max-w-[900px] flex-col gap-[30px] px-4 py-12 sm:px-6 md:px-8 md:py-16',
            bodyAlignCenter ? 'items-center justify-center' : 'items-stretch justify-center',
          )}
        >
          <div
            className={cn(
              'content-stretch flex w-full flex-col gap-[24px] not-italic',
              bodyAlignCenter ? 'items-center' : 'items-stretch',
            )}
          >
            <div
              className={cn(
                'flex w-full flex-col gap-[10px]',
                titleAlignCenter ? 'items-center' : 'items-stretch',
              )}
            >
              {eyebrow ? (
                <CtaEyebrow
                  text={eyebrow}
                  alignCenter={titleAlignCenter}
                  surface="onDark"
                />
              ) : null}
              <SectionTitle
                as="h2"
                size="module"
                align={titleAlignCenter ? 'center' : 'left'}
                color="#ffffff"
                className={cn('whitespace-pre-wrap', !titleAlignCenter && 'text-justify')}
              >
                {title}
              </SectionTitle>
            </div>
            {subtitle ? (
              subtitleAsMarkdown ? (
                <CtaRichText
                  markdown={subtitle}
                  align={contentTextAlign}
                  className={subtitleClassName}
                />
              ) : (
                <p
                  className={cn(
                    'font-[\'Avenir:Roman\',sans-serif] text-[18px] leading-[1.6] text-white/95',
                    bodyAlignCenter ? 'max-w-[640px] text-center' : 'w-full text-justify',
                    subtitleClassName,
                  )}
                >
                  {subtitle}
                </p>
              )
            ) : null}
          </div>

          {showButtonRow ? (
            <div className="flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center sm:justify-center sm:gap-4">
              {primaryVisible ? (
                <button
                  type="button"
                  onClick={onButtonClick}
                  className="flex h-11 min-h-[44px] flex-none cursor-pointer items-center justify-center rounded-[999px] bg-white px-5 transition-colors hover:bg-gray-100"
                >
                  <span className="font-['Avenir:Heavy',sans-serif] text-[12px] uppercase tracking-[0.06px] text-black">
                    {buttonText}
                  </span>
                </button>
              ) : null}
              {secondaryVisible ? (
                <button
                  type="button"
                  onClick={onSecondaryButtonClick}
                  className="flex h-11 min-h-[44px] flex-none cursor-pointer items-center justify-center rounded-[999px] border border-white bg-transparent px-5 transition-colors hover:bg-white/10"
                >
                  <span className="font-['Avenir:Heavy',sans-serif] text-[12px] uppercase tracking-[0.06px] text-white">
                    {secondaryButtonText}
                  </span>
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
