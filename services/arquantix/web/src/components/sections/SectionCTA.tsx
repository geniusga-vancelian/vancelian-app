"use client";

/**
 * CTA marketing (CMS section `cta`) — Vancelian Design System.
 *
 * Délègue à {@link VFinalCta} (pattern DS officiel `components/final-cta/`).
 *
 * Variantes :
 * - `marketingVariant="image"` (défaut) : fond image + overlay sombre par-dessus
 *   le fond dark Vancelian. Aligné sur le pattern « final-cta avec photo ».
 * - `marketingVariant="gradient"` : sans image, fond papier off-white (DS),
 *   ancien pattern Figma rose/orange déprécié.
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
import { VFinalCta } from "@/components/design-system/vancelian/VFinalCta";
import { VCmsMedia } from "@/components/design-system/vancelian/VCmsMedia";
import {
  VEditorialTitle,
  VEyebrow,
} from "@/components/design-system/vancelian";
import { Button } from "@/components/ui/button";
import {
  normalizeVancelianDarkColor,
  parseEditorialTitle,
} from "@/lib/cms/parseEditorialTitle";

/** Conversion hex (#RRGGBB) + alpha → rgba (utilitaire local conservé). */
function hexWithOpacity(hex: string, alpha: number): string {
  const v = Math.max(0, Math.min(1, alpha));
  const m = /^#([0-9a-f]{6})$/i.exec((hex || "").trim());
  if (!m) return hex;
  const r = parseInt(m[1]!.slice(0, 2), 16);
  const g = parseInt(m[1]!.slice(2, 4), 16);
  const b = parseInt(m[1]!.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${v})`;
}

export interface SectionCTAProps extends React.HTMLAttributes<HTMLElement> {
  eyebrow?: string;
  title?: string;
  description?: string;
  primaryButtonText?: string;
  primaryButtonHref?: string;
  secondaryButtonText?: string;
  secondaryButtonHref?: string;
  /** Résolu par getPageSections à partir de backgroundMediaId */
  backgroundMediaUrl?: string;
  backgroundVideoUrl?: string;
  /** Couleur de fond / overlay (hex). Défaut : `#141208` (Vancelian dark). */
  backgroundColor?: string;
  /** Opacité de l'image (0–1). */
  backgroundImageOpacity?: number;
  /** Teinte colorée par-dessus l'image (0–1). */
  overlayOpacity?: number;
  showPrimaryButton?: boolean;
  showSecondaryButton?: boolean;
  /** Centré ou justifié pour la description. Le DS centre toujours le titre. */
  contentTextAlign?: "center" | "justify";
  /**
   * `gradient` = bloc clair (sans image) — version éditoriale fond papier.
   * `image` (défaut) = CTA dark Vancelian avec image de fond.
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

/** Convertit `**gras**` markdown → JSX inline, le reste en texte plain. */
function richTextFromMd(md: string): React.ReactNode {
  const parts = md.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    const m = /^\*\*(.+)\*\*$/.exec(p);
    if (m) return <strong key={i}>{m[1]}</strong>;
    return <React.Fragment key={i}>{p}</React.Fragment>;
  });
}

export function SectionCTA({
  eyebrow,
  title = "",
  description = "",
  primaryButtonText = "",
  primaryButtonHref,
  secondaryButtonText,
  secondaryButtonHref,
  backgroundMediaUrl,
  backgroundVideoUrl,
  backgroundColor: backgroundColorProp = "#141208",
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
  const backgroundColor = normalizeVancelianDarkColor(backgroundColorProp);
  const hasImage = Boolean(backgroundMediaUrl?.trim() || backgroundVideoUrl?.trim());
  const useGradient = marketingVariant === "gradient" && !hasImage;

  const t = title?.trim();
  const titleNode = t ? parseEditorialTitle(t) : null;
  const d = description?.trim();
  const e = eyebrow?.trim();

  // === Variante gradient (sans image) — bloc clair éditorial Vancelian
  if (useGradient) {
    const buttons = showPrimaryButton && primaryButtonText?.trim()
      ? [
          <Button
            key="cta-primary"
            variant="default"
            size="default"
            onClick={() => navigateHref(primaryButtonHref)}
          >
            {primaryButtonText}
          </Button>,
        ]
      : [];
    return (
      <section
        className={cn("relative w-full bg-v-bg py-20 lg:py-24", className)}
        {...props}
      >
        <Container>
          <div className="mx-auto flex max-w-[720px] flex-col items-center text-center">
            {e ? <VEyebrow>{e}</VEyebrow> : null}
            {titleNode ? (
              <VEditorialTitle
                as="h2"
                size="page"
                tone="default"
                className={e ? "mt-6" : "mt-0"}
              >
                {titleNode}
              </VEditorialTitle>
            ) : null}
            {d ? (
              <p
                className={cn(
                  "m-0 font-ui font-normal text-[18px] leading-[1.55] text-v-fg-body",
                  contentTextAlign === "justify" ? "text-justify" : "text-center",
                  "max-w-[640px]",
                  t || e ? "mt-6" : "mt-0",
                )}
              >
                {richTextFromMd(d)}
              </p>
            ) : null}
            {buttons.length > 0 ? (
              <div className="mt-10 flex flex-wrap justify-center gap-4">
                {buttons}
              </div>
            ) : null}
          </div>
        </Container>
      </section>
    );
  }

  // === Variante image (défaut) — final-cta Vancelian dark + image
  const buttons: Array<{ label: React.ReactNode; href?: string; variant: "primary" | "secondary" }> = [];
  if (showPrimaryButton && primaryButtonText?.trim()) {
    buttons.push({
      label: primaryButtonText,
      variant: "primary",
      href: undefined,
    });
  }
  if (showSecondaryButton && secondaryButtonText?.trim()) {
    buttons.push({
      label: secondaryButtonText,
      variant: "secondary",
      href: undefined,
    });
  }

  const imgOpacity = Math.min(1, Math.max(0, backgroundImageOpacity ?? 1));
  const overlayOp = Math.min(1, Math.max(0, overlayOpacity ?? 0));

  // Cas avec image : wrap VFinalCta dans un `<section>` qui porte l'image
  // (VFinalCta gère sa propre couleur de fond, donc on lui passe `transparent`
  // pour superposer l'image).
  if (hasImage) {
    return (
      <section
        className={cn("relative w-full overflow-hidden", className)}
        {...props}
      >
        <div className="pointer-events-none absolute inset-0 z-0" aria-hidden>
          <div className="absolute inset-0" style={{ backgroundColor }} />
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
              style={{ backgroundColor: hexWithOpacity(backgroundColor, overlayOp) }}
            />
          ) : null}
        </div>
        <div className="relative z-10">
          <VFinalCta
            backgroundColor="transparent"
            eyebrow={e}
            title={titleNode ?? undefined}
            description={d ? richTextFromMd(d) : undefined}
            buttons={buttons.map((b) => ({
              ...b,
              onClick: () =>
                navigateHref(
                  b.variant === "primary" ? primaryButtonHref : secondaryButtonHref,
                ),
            }))}
          />
        </div>
      </section>
    );
  }

  // Cas sans image : VFinalCta avec son fond dark canonique
  return (
    <VFinalCta
      backgroundColor={backgroundColor}
      eyebrow={e}
      title={titleNode ?? undefined}
      description={d ? richTextFromMd(d) : undefined}
      buttons={buttons.map((b) => ({
        ...b,
        onClick: () =>
          navigateHref(
            b.variant === "primary" ? primaryButtonHref : secondaryButtonHref,
          ),
      }))}
      className={className}
    />
  );
}
