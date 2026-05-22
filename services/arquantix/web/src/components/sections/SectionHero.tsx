"use client";

/**
 * Hero homepage / page secondaire — Vancelian Design System.
 *
 * Délègue à {@link VHero} (pattern DS officiel `components/hero/hero.css`).
 * Conserve l'API CMS historique : `variant`, `inverseOverlay`, `tags`,
 * `tagsPresentation`, `hideCta`, `backgroundImageOpacity`.
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
import { VHero } from "@/components/design-system/vancelian/VHero";
import { VHeroTypewriter } from "@/components/design-system/vancelian/VHeroTypewriter";
import { parseEditorialTitle } from "@/lib/cms/parseEditorialTitle";
import { HeroOfferTagChip } from "@/components/design-system/heroOfferTagChip";
import { HERO_NAV_BLEND_ANCHOR_ID } from "@/hooks/useHeroSecondaryNavBlend";

/**
 * Constantes legacy conservées pour compatibilité avec
 * `useHeroSecondaryNavBlend` et autres consommateurs internes.
 * Le hero Vancelian aligne naturellement le titre sous la nav fixe
 * (`pt-14 md:pt-[60px]`) — ces offsets restent valides comme repères.
 */
export const HERO_SECONDARY_TOP_TO_TITLE_BLOCK_PX = 128;
export const HERO_SECONDARY_TOP_TO_TITLE_GAP_PX = 30;
export const HERO_SECONDARY_TOP_TO_TITLE_TOTAL_PX =
  HERO_SECONDARY_TOP_TO_TITLE_BLOCK_PX + HERO_SECONDARY_TOP_TO_TITLE_GAP_PX;
export const HERO_SECONDARY_BOTTOM_SPACING_NO_CTA_PX = 128;

export type SectionHeroVariant = "homepage" | "secondary";

export interface SectionHeroProps extends React.HTMLAttributes<HTMLElement> {
  backgroundImage?: string;
  backgroundVideoUrl?: string;
  /** 0–1, opacité du calque image uniquement */
  backgroundImageOpacity?: number;
  /** Surtitre DS (caption uppercase). */
  eyebrow?: string;
  /** Stats inline séparées par un point. */
  inlineStats?: string[];
  /** Note légale sous les CTA. */
  note?: string;
  secondaryCtaText?: string;
  secondaryCtaHref?: string;
  /** Mots animés sur la dernière ligne du titre (homepage). */
  typewriterWords?: string[];
  /** `homepage` → hero principal DS ; `secondary` → page de contenu / offre */
  variant?: SectionHeroVariant;
  /**
   * Hero secondary avec photo : texte clair + dégradé sombre.
   * Le DS Vancelian gère ça nativement via le variant `dark` de VHero.
   */
  inverseOverlay?: boolean;
  /** Pastilles (offres exclusives). */
  tags?: string[];
  /**
   * `categoryBadges` : `HeroOfferTagChip` (LABEL fond dark grey).
   * `pills` : pastilles uppercase bordure (défaut).
   */
  tagsPresentation?: "pills" | "categoryBadges";
  title?: string;
  subtitle?: string;
  ctaText?: string;
  ctaLink?: string;
  sidebarText?: string;
  /** Masque le bouton CTA. */
  hideCta?: boolean;
  /** Diffère la vidéo de fond (portail auth). */
  deferBackgroundVideo?: boolean;
}

/**
 * Coupe un titre passé en multi-ligne en `primary` / `secondary`. Le DS
 * Vancelian intègre les accents éditoriaux directement via `<em>` dans le
 * titre — pour préserver l'usage historique CMS (titre sur 2 lignes), on
 * conserve cette signature ici et on rejoint en `<br />`.
 */
function buildTitleNode(
  raw: string,
  typewriterWords?: string[],
): React.ReactNode {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  const words = Array.isArray(typewriterWords)
    ? typewriterWords.map((w) => w.trim()).filter(Boolean)
    : [];

  if (words.length > 0) {
    const lines = trimmed
      .split(/\n+/)
      .map((s) => s.trim())
      .filter(Boolean);
    return (
      <>
        {lines.map((line, i) => (
          <span key={i} className="hero-home-line">
            <span>{parseEditorialTitle(line)}</span>
          </span>
        ))}
        <span className="hero-home-line hero-home-line-typewriter">
          <span>
            <VHeroTypewriter words={words} />
          </span>
        </span>
      </>
    );
  }

  if (/<em>|<br/i.test(trimmed)) return parseEditorialTitle(trimmed);
  const lines = trimmed
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (lines.length === 0) return null;
  if (lines.length === 1) return lines[0];
  return (
    <>
      {lines.map((line, i) => (
        <React.Fragment key={i}>
          {i > 0 ? <br /> : null}
          {line}
        </React.Fragment>
      ))}
    </>
  );
}

/** Icône smartphone pour le CTA « Télécharger l'app » (spec Home.html). */
function DownloadAppIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="h-4 w-4"
    >
      <rect x="6" y="2" width="12" height="20" rx="2" />
      <path d="M11 18h2" />
    </svg>
  );
}

/** Icône WhatsApp inline (l'ancien `WhatsAppIcon` du design-system Figma reste compatible mais on évite la dépendance). */
function WhatsAppGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className="h-4 w-4"
    >
      <path d="M19.05 4.91A10 10 0 0 0 12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.74.46 3.44 1.32 4.93L2 22l5.31-1.39a9.9 9.9 0 0 0 4.73 1.2h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.91-7Zm-7.01 15.24a8.2 8.2 0 0 1-4.18-1.14l-.3-.18-3.15.83.84-3.07-.2-.32a8.22 8.22 0 0 1-1.26-4.36c0-4.55 3.7-8.25 8.25-8.25 2.2 0 4.27.86 5.83 2.42a8.2 8.2 0 0 1 2.41 5.84c0 4.55-3.7 8.25-8.24 8.25Zm4.53-6.18c-.25-.13-1.47-.73-1.7-.81-.23-.08-.4-.13-.56.13-.17.25-.65.81-.79.97-.15.17-.29.19-.54.06-.25-.12-1.05-.39-2-1.23-.74-.66-1.24-1.47-1.38-1.72-.15-.25-.02-.39.11-.51.11-.11.25-.29.37-.43.12-.15.16-.25.25-.42.08-.17.04-.31-.02-.43-.06-.13-.56-1.34-.77-1.84-.2-.48-.41-.42-.56-.42-.15 0-.31-.02-.48-.02-.17 0-.43.06-.65.31-.23.25-.85.83-.85 2.03 0 1.2.87 2.36 1 2.52.12.17 1.71 2.62 4.14 3.67.58.25 1.03.4 1.38.51.58.18 1.11.16 1.53.1.47-.07 1.47-.6 1.68-1.18.21-.58.21-1.07.15-1.18-.06-.11-.23-.17-.48-.29Z" />
    </svg>
  );
}

export function SectionHero({
  backgroundImage,
  backgroundVideoUrl,
  backgroundImageOpacity = 1,
  eyebrow,
  inlineStats,
  note,
  secondaryCtaText,
  secondaryCtaHref,
  typewriterWords,
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
  deferBackgroundVideo = false,
  className,
  style,
  ...props
}: SectionHeroProps) {
  const pathname = usePathname() ?? "";
  const navLocale = getActiveLocaleFromPathname(pathname);
  const hasBgVideo =
    typeof backgroundVideoUrl === "string" && backgroundVideoUrl.trim() !== "";
  const hasBgPhoto =
    typeof backgroundImage === "string" && backgroundImage.trim() !== "";
  const hasBgMedia = hasBgVideo || hasBgPhoto;
  const isSecondary = variant === "secondary";

  /**
   * Mapping des variants legacy → variants VHero :
   * - homepage SANS image  → `light` (fond papier off-white, texte anthracite)
   * - homepage AVEC image  → `dark`  (full-bleed photo + filtre sombre)
   * - secondary SANS image → `secondary` (compact, fond clair, texte anthracite)
   * - secondary AVEC image + inverseOverlay → `dark` (filtre sombre)
   * - secondary AVEC image SANS inverseOverlay → `secondary` (photo subtile)
   */
  const heroVariant: "dark" | "light" | "secondary" = isSecondary
    ? inverseOverlay && hasBgPhoto
      ? "dark"
      : "secondary"
    : hasBgMedia
      ? "dark"
      : "light";

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

  const isDownloadAppCta =
    /download-app/i.test(ctaLink || "") ||
    /télécharger|telecharger|download/i.test(ctaText || "");

  const bodyCopy = [subtitle, sidebarText]
    .map((s) => (typeof s === "string" ? s.trim() : ""))
    .filter(Boolean)
    .join("\n\n");

  // Tags
  const tagNodes =
    Array.isArray(tags) && tags.length > 0
      ? tagsPresentation === "categoryBadges"
        ? tags.slice(0, 10).map((t, i) => (
            <HeroOfferTagChip
              key={`${t}-${i}`}
              variant={heroVariant === "dark" ? "onMedia" : "onLight"}
            >
              {t}
            </HeroOfferTagChip>
          ))
        : tags.slice(0, 10).map((t, i) => (
            <span
              key={`${t}-${i}`}
              className={cn(
                "rounded-v-pill border px-3 py-1.5 font-ui font-semibold text-[11px] uppercase tracking-wide",
                heroVariant === "dark"
                  ? "border-white/35 bg-white/10 text-white"
                  : "border-v-fg-20 bg-v-fg-05 text-v-fg-body",
              )}
            >
              {t}
            </span>
          ))
      : undefined;

  const navigateSecondary = () => {
    if (!secondaryCtaHref) return;
    if (secondaryCtaHref.startsWith("#")) {
      document.querySelector(secondaryCtaHref)?.scrollIntoView({ behavior: "smooth" });
      return;
    }
    const target = shouldSkipLocalizePublicHref(secondaryCtaHref)
      ? secondaryCtaHref
      : localizePublicInternalHref(secondaryCtaHref, navLocale);
    window.location.assign(target);
  };

  const statNodes =
    Array.isArray(inlineStats) && inlineStats.length > 0
      ? inlineStats.map((s) => s.trim()).filter(Boolean)
      : undefined;

  return (
    <VHero
      id={
        isSecondary
          ? "hero-secondary"
          : variant === "homepage" && hasBgMedia
            ? "hero-home"
            : HERO_NAV_BLEND_ANCHOR_ID
      }
      eyebrow={eyebrow}
      title={buildTitleNode(title, typewriterWords)}
      subtitle={bodyCopy || undefined}
      backgroundImage={hasBgVideo ? undefined : backgroundImage}
      backgroundVideoUrl={backgroundVideoUrl}
      deferBackgroundVideo={deferBackgroundVideo}
      backgroundImageOpacity={backgroundImageOpacity}
      variant={heroVariant}
      minHeight={isSecondary ? "auto" : hasBgMedia ? "screen" : "auto"}
      inlineStats={statNodes}
      note={note}
      tags={tagNodes}
      ctas={
        hideCta
          ? []
          : [
              {
                label: ctaText,
                onClick: navigate,
                variant: "primary",
                icon: isWhatsAppCta
                  ? <WhatsAppGlyph />
                  : isDownloadAppCta
                    ? <DownloadAppIcon />
                    : undefined,
              },
              ...(secondaryCtaText?.trim()
                ? [
                    {
                      label: secondaryCtaText,
                      onClick: navigateSecondary,
                      variant: "secondary" as const,
                      trailingArrow: true,
                    },
                  ]
                : []),
            ]
      }
      homepageMotion={variant === "homepage" && hasBgMedia}
      className={className}
      style={style}
      {...props}
    />
  );
}
