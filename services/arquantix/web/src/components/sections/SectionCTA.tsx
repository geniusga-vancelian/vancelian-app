"use client";

/**
 * CTA marketing (CMS section `cta`) — fond image + overlay pleine largeur viewport.
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
  MarketingBlock,
  hexWithOpacity,
} from "@/components/design-system/marketing-block";
import { arquantixContentTextBlockClass } from "@/lib/design/contentMaxWidth";

export interface SectionCTAProps extends React.HTMLAttributes<HTMLElement> {
  /** Surtitre au-dessus du titre (petites caps ; filets gérés par le rendu) */
  eyebrow?: string;
  title?: string;
  description?: string;
  primaryButtonText?: string;
  primaryButtonHref?: string;
  secondaryButtonText?: string;
  secondaryButtonHref?: string;
  /** Résolu par getPageSections à partir de backgroundMediaId */
  backgroundMediaUrl?: string;
  /** Couleur de fond / overlay (hex), ex. #000000 */
  backgroundColor?: string;
  /** Opacité de l’image sur la couleur de fond (0–1) */
  backgroundImageOpacity?: number;
  /** Teinte colorée par-dessus l’image (0–1), 0 = désactivé */
  overlayOpacity?: number;
  /** Afficher le bouton principal */
  showPrimaryButton?: boolean;
  /** Afficher le bouton secondaire */
  showSecondaryButton?: boolean;
  /** Centré ou justifié pour la description (le titre reste centré). */
  contentTextAlign?: "center" | "justify";
  /**
   * `gradient` = ancien bloc Figma rose/orange (CTA sans image de fond).
   * `image` = CTA sombre image + overlay + double bouton (section `cta`).
   */
  marketingVariant?: "gradient" | "image";
}

function useLocalizedNavigate() {
  const pathname = usePathname() ?? "";
  const navLocale = getActiveLocaleFromPathname(pathname);
  return (href: string | undefined) => {
    if (!href || !href.trim()) return;
    const h = href.trim();
    if (h.startsWith("#")) {
      document.querySelector(h)?.scrollIntoView({ behavior: "smooth" });
      return;
    }
    const target = shouldSkipLocalizePublicHref(h)
      ? h
      : localizePublicInternalHref(h, navLocale);
    if (openWhatsAppPreferApp(target)) {
      return;
    }
    window.location.assign(target);
  };
}

export function SectionCTA({
  eyebrow,
  title = "Ready to invest in fractional real estate?",
  description = "Join institutional investors accessing premium real estate opportunities through our regulated platform.",
  primaryButtonText = "Get Started",
  primaryButtonHref = "/signup",
  secondaryButtonText,
  secondaryButtonHref,
  backgroundMediaUrl,
  backgroundColor = "#000000",
  backgroundImageOpacity = 1,
  overlayOpacity = 0.55,
  showPrimaryButton = true,
  showSecondaryButton = true,
  contentTextAlign = "center",
  marketingVariant = "image",
  className,
  ...props
}: SectionCTAProps) {
  const navigateHref = useLocalizedNavigate();
  const hasImage = Boolean(backgroundMediaUrl?.trim());
  const useGradient = marketingVariant === "gradient" && !hasImage;

  if (useGradient) {
    return (
      <section
        className={cn("w-full bg-neutral-100 py-10 md:py-14", className)}
        {...props}
      >
        <Container className="flex justify-center">
          <div className="min-w-0 w-full">
            <MarketingBlock
              variant="gradient"
              eyebrow={eyebrow}
              title={title}
              subtitle={description}
              buttonText={primaryButtonText?.toUpperCase() ?? ""}
              onButtonClick={() => navigateHref(primaryButtonHref)}
              showPrimaryButton={showPrimaryButton}
              subtitleAsMarkdown
              contentTextAlign={contentTextAlign}
              subtitleClassName={arquantixContentTextBlockClass}
              titleAlwaysCenter
            />
          </div>
        </Container>
      </section>
    );
  }

  return (
    <section
      className={cn("relative w-full overflow-hidden py-10 md:py-14", className)}
      {...props}
    >
      {/* Fond 100 % largeur viewport (centré si le parent est plus étroit) */}
      <div
        className="pointer-events-none absolute inset-y-0 left-1/2 z-0 w-screen max-w-none -translate-x-1/2"
        aria-hidden
      >
        {/* 1. Couleur de fond pleine largeur */}
        <div
          className="absolute inset-0"
          style={{ backgroundColor }}
        />
        {/* 2. Image au-dessus, opacité réglable pour laisser apparaître la couleur */}
        {hasImage ? (
          <>
            <img
              alt=""
              src={backgroundMediaUrl}
              className="absolute inset-0 h-full w-full object-cover object-center"
              style={{
                opacity: Math.min(
                  1,
                  Math.max(0, backgroundImageOpacity ?? 1),
                ),
              }}
              sizes="100vw"
            />
            {/* 3. Teinte optionnelle par-dessus (compat + assombrissement) */}
            {(overlayOpacity ?? 0) > 0 ? (
              <div
                className="absolute inset-0"
                style={{
                  backgroundColor: hexWithOpacity(
                    backgroundColor,
                    overlayOpacity ?? 0,
                  ),
                }}
              />
            ) : null}
          </>
        ) : null}
      </div>

      <Container className="relative z-10">
        <MarketingBlock
          variant="image"
          contentOnly
          eyebrow={eyebrow}
          title={title}
          subtitle={description}
          buttonText={primaryButtonText?.toUpperCase() ?? ""}
          onButtonClick={() => navigateHref(primaryButtonHref)}
          showPrimaryButton={showPrimaryButton}
          showSecondaryButton={showSecondaryButton}
          subtitleAsMarkdown
          contentTextAlign={contentTextAlign}
          subtitleClassName={arquantixContentTextBlockClass}
          titleAlwaysCenter
          secondaryButtonText={
            secondaryButtonText?.trim()
              ? secondaryButtonText.toUpperCase()
              : undefined
          }
          onSecondaryButtonClick={
            secondaryButtonText?.trim() && secondaryButtonHref?.trim()
              ? () => navigateHref(secondaryButtonHref)
              : undefined
          }
        />
      </Container>
    </section>
  );
}
