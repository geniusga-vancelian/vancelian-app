"use client";

/**
 * Hero homepage — Design System Figma (GradientHeading, décor, CTA).
 */
import * as React from "react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  getActiveLocaleFromPathname,
  localizePublicInternalHref,
  shouldSkipLocalizePublicHref,
} from "@/lib/i18n/publicLocalizedRouting";
import { openWhatsAppPreferApp } from "@/lib/whatsapp/openWhatsApp";
import { Container } from "@/components/ui/Container";
import {
  GradientHeading,
  CTAButton,
  WhatsAppIcon,
  DecorativeGradient,
} from "@/components/design-system/ds-hero";
import {
  HeroOfferTagChip,
  HERO_OFFER_TAG_GAP_CLASS,
} from "@/components/design-system/heroOfferTagChip";
import { MainTitle, Titlepage } from "@/components/design-system/extracted";
import { HERO_NAV_BLEND_ANCHOR_ID } from "@/hooks/useHeroSecondaryNavBlend";

/**
 * DS hero secondary : distance du **haut du module** (`<section>`) au **bord supérieur du titre**.
 * Partout où `variant="secondary"` est utilisé (CMS projet, offre exclusive, etc.), c’est la même règle.
 */
export const HERO_SECONDARY_TOP_TO_TITLE_BLOCK_PX = 128;
export const HERO_SECONDARY_TOP_TO_TITLE_GAP_PX = 30;
export const HERO_SECONDARY_TOP_TO_TITLE_TOTAL_PX =
  HERO_SECONDARY_TOP_TO_TITLE_BLOCK_PX + HERO_SECONDARY_TOP_TO_TITLE_GAP_PX;

/**
 * Espace entre la description (dernier bloc texte) et le bas du module — hero secondary avec image
 * de fond et sans bouton CTA (`hideCta`).
 */
export const HERO_SECONDARY_BOTTOM_SPACING_NO_CTA_PX = 128;

/** Aligné sur `-mt-14` / `md:-mt-[60px]` — le `pt-*` avec image = 158px + ce retrait (voir classes ci-dessous). */

export type SectionHeroVariant = "homepage" | "secondary";

export interface SectionHeroProps extends React.HTMLAttributes<HTMLElement> {
  backgroundImage?: string;
  /** 0–1, opacité du calque image uniquement */
  backgroundImageOpacity?: number;
  /** `hero` → homepage (dégradé ligne 2) ; `hero_secondary` → titre page secondaire DS */
  variant?: SectionHeroVariant;
  /**
   * Hero secondary avec photo : texte clair + dégradé sombre (offres exclusives, maquettes type villa de nuit).
   * Sans effet si pas d’image ou si variant ≠ secondary.
   */
  inverseOverlay?: boolean;
  /** Pastilles entre le titre et la description (ex. offre exclusive) — typiquement avec `inverseOverlay`. */
  tags?: string[];
  /**
   * `categoryBadges` : puces hero DS ([HeroOfferTagChip], Figma LABEL — fond dark grey opaque).
   * `pills` : pastilles uppercase bordure (défaut).
   */
  tagsPresentation?: "pills" | "categoryBadges";
  title?: string;
  subtitle?: string;
  ctaText?: string;
  ctaLink?: string;
  sidebarText?: string;
  /** Masque le bouton CTA (hero titre seul, ex. page offre exclusive). */
  hideCta?: boolean;
}

function splitHeroTitle(raw: string): { primary: string; gradient: string } {
  const lines = raw
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (lines.length >= 2) {
    return { primary: lines[0]!, gradient: lines.slice(1).join(" ") };
  }
  return { primary: raw.trim(), gradient: "" };
}

export function SectionHero({
  backgroundImage,
  backgroundImageOpacity = 1,
  variant = "homepage",
  inverseOverlay = false,
  tags,
  tagsPresentation = "pills",
  title = "",
  subtitle,
  ctaText = "Explore projects",
  ctaLink = "#",
  sidebarText,
  hideCta = false,
  className,
  style: styleProp,
  ...props
}: SectionHeroProps) {
  const pathname = usePathname() ?? "";
  const navLocale = getActiveLocaleFromPathname(pathname);
  const { primary, gradient } = splitHeroTitle(title);
  const hasBgPhoto =
    typeof backgroundImage === "string" && backgroundImage.trim() !== "";

  const opacity =
    typeof backgroundImageOpacity === "number" &&
    Number.isFinite(backgroundImageOpacity)
      ? Math.min(1, Math.max(0, backgroundImageOpacity))
      : 1;
  const isSecondary = variant === "secondary";
  const useInverse =
    Boolean(inverseOverlay) && hasBgPhoto && isSecondary;
  /** À 100 %, pas de voile blanc par-dessus la photo (sinon le rendu ne correspond pas au curseur CMS). */
  const showReadableScrim =
    hasBgPhoto && opacity < 0.999 && !useInverse;

  const bodyCopy = [subtitle, sidebarText].filter(Boolean).join("\n\n");

  /** Image sous la nav fixe (homepage ou secondary) pour alignement avec la barre transparente. */
  const bleedUnderNav =
    hasBgPhoto && (isSecondary || variant === "homepage");

  /** Bas du module : 128px sous le contenu quand la description est le dernier bloc (pas de CTA), image obligatoire. */
  const secondaryBgNoCtaBottom =
    isSecondary && hasBgPhoto && hideCta;

  const navigate = () => {
    if (!ctaLink) return;
    if (ctaLink.startsWith("#")) {
      document.querySelector(ctaLink)?.scrollIntoView({ behavior: "smooth" });
      return;
    }
    const target = shouldSkipLocalizePublicHref(ctaLink)
      ? ctaLink
      : localizePublicInternalHref(ctaLink, navLocale);
    if (openWhatsAppPreferApp(target)) {
      return;
    }
    window.location.assign(target);
  };

  const isWhatsAppCta =
    /wa\.me|whatsapp|api\.whatsapp/i.test(ctaLink || "") ||
    /whatsapp/i.test(ctaText || "");

  return (
    <section
      id={
        isSecondary
          ? "hero-secondary"
          : variant === "homepage" && hasBgPhoto
            ? "hero-home"
            : undefined
      }
      className={cn(
        "relative w-full overflow-x-clip bg-white",
        /** Secondary + image : fond sous la nav ; padding compensé pour aligner le titre sur le cas sans image. */
        bleedUnderNav && isSecondary && "-mt-14 md:-mt-[60px]",
        bleedUnderNav &&
          !isSecondary &&
          "-mt-14 pt-[calc(3.5rem+6rem)] md:-mt-[60px] md:pt-[calc(60px+8rem)]",
        isSecondary &&
          (bleedUnderNav
            ? // (128+30) + retrait nav — aligné titre avec le hero secondary sans image
              "pt-[calc(128px+30px+3.5rem)] md:pt-[calc(128px+30px+60px)]"
            : "pt-[calc(128px+30px)]"),
        className,
      )}
      style={{
        ...styleProp,
      }}
      {...props}
    >
      {hasBgPhoto ? (
        <div
          className="pointer-events-none absolute inset-y-0 left-1/2 z-0 w-[100vw] max-w-[100vw] -translate-x-1/2 overflow-hidden"
          aria-hidden
        >
          <img
            alt=""
            src={backgroundImage}
            sizes="100vw"
            decoding="async"
            fetchPriority="high"
            style={{ opacity }}
            className="absolute inset-0 h-full w-full max-w-none object-cover object-center"
          />
          {/* Voile uniquement si l’opacité CMS est inférieure à 100 % — sinon photo telle qu’uploadée. */}
          {useInverse ? (
            <div
              className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/45 to-black/75"
              aria-hidden
            />
          ) : showReadableScrim ? (
            <div
              className="absolute inset-0 bg-gradient-to-b from-white/[0.88] via-white/[0.62] to-white/[0.92]"
              aria-hidden
            />
          ) : null}
        </div>
      ) : null}
      {!hasBgPhoto && variant !== "secondary" ? (
        <div
          className="pointer-events-none absolute inset-0 z-[1] overflow-hidden"
          aria-hidden
        >
          <div className="absolute left-1/2 top-1/2 h-[min(120vw,80vh)] w-[min(220vw,200vh)] -translate-x-1/2 -translate-y-1/2 rotate-[-22deg]">
            <DecorativeGradient />
          </div>
        </div>
      ) : null}

      <Container className="relative z-[2]">
        <div
          className={cn(
            "flex flex-col items-center px-4 lg:px-8",
            isSecondary
              ? secondaryBgNoCtaBottom
                ? "pb-[128px]" // = HERO_SECONDARY_BOTTOM_SPACING_NO_CTA_PX
                : "pb-16"
              : "pb-0",
            isSecondary
              ? "gap-10"
              : bleedUnderNav
                ? "gap-16 pt-0"
                : "gap-16 pt-24 md:pt-32",
          )}
        >
          <div
            className={cn(
              "flex w-full max-w-[900px] flex-col items-center text-center",
              isSecondary ? "gap-10" : "gap-16",
            )}
          >
            {variant === "secondary" ? (
              <Titlepage
                id={HERO_NAV_BLEND_ANCHOR_ID}
                color={useInverse ? "#ffffff" : "#000000"}
              >
                {primary ? <span className="block">{primary}</span> : null}
                {gradient ? (
                  <span
                    className={cn(
                      "mt-[0.35em] block",
                      useInverse ? "text-white/95" : "text-black",
                    )}
                  >
                    {gradient}
                  </span>
                ) : null}
                {!primary && !gradient && title ? (
                  <span className="block whitespace-pre-line">{title}</span>
                ) : null}
              </Titlepage>
            ) : gradient ? (
              <div id={HERO_NAV_BLEND_ANCHOR_ID} className="w-full">
                <GradientHeading
                  primaryText={primary}
                  gradientText={gradient}
                />
              </div>
            ) : (
              <MainTitle id={HERO_NAV_BLEND_ANCHOR_ID} as="h1">
                {primary || title}
              </MainTitle>
            )}

            {isSecondary && Array.isArray(tags) && tags.length > 0 ? (
              tagsPresentation === "categoryBadges" ? (
                <div
                  className={cn(
                    "flex flex-wrap items-center justify-center",
                    HERO_OFFER_TAG_GAP_CLASS,
                  )}
                >
                  {tags.slice(0, 10).map((t, i) => (
                    <HeroOfferTagChip
                      key={`${t}-${i}`}
                      variant={useInverse ? "onMedia" : "onLight"}
                    >
                      {t}
                    </HeroOfferTagChip>
                  ))}
                </div>
              ) : (
                <div className="flex flex-wrap items-center justify-center gap-2">
                  {tags.slice(0, 10).map((t, i) => (
                    <span
                      key={`${t}-${i}`}
                      className={cn(
                        "rounded-full border px-3 py-1.5 font-['Avenir:Heavy',sans-serif] text-[11px] uppercase tracking-wide",
                        useInverse
                          ? "border-white/35 bg-white/10 text-white"
                          : "border-neutral-200 bg-neutral-50 text-neutral-700",
                      )}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )
            ) : null}

            {bodyCopy ? (
              <p
                className={cn(
                  "max-w-[746px] font-['Avenir:Roman',sans-serif] text-[18px] leading-[1.6]",
                  useInverse ? "text-white/90" : "text-black",
                )}
              >
                {bodyCopy}
              </p>
            ) : null}

            {!hideCta ? (
              <CTAButton
                size="md"
                onClick={navigate}
                icon={isWhatsAppCta ? <WhatsAppIcon /> : undefined}
                className={useInverse ? "border border-white/40 bg-white text-black hover:bg-white/95" : undefined}
              >
                {ctaText}
              </CTAButton>
            ) : null}
          </div>
        </div>
      </Container>
    </section>
  );
}
