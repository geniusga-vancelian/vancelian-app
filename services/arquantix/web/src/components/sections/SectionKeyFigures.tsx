"use client";

/**
 * Grille « Key figures » (chiffres clés) — Vancelian Design System.
 *
 * Délègue à {@link VProofStats} (pattern DS `proof-bar` variante stats) +
 * affiche optionnellement un eyebrow et un titre éditorial au-dessus.
 *
 * Le DS Vancelian utilise par défaut le fond papier off-white (`--v-bg`)
 * pour les bandeaux de stats — mais l'historique Arquantix conservait
 * souvent un fond sombre piloté par CMS, donc on conserve `backgroundColor`.
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { VProofStats } from "@/components/design-system/vancelian/VProofStats";
import { VCmsMedia } from "@/components/design-system/vancelian/VCmsMedia";
import { VEditorialTitle, VEyebrow } from "@/components/design-system/vancelian";

export interface KeyFigureStat {
  value?: string;
  label?: string;
}

export interface SectionKeyFiguresProps extends React.HTMLAttributes<HTMLElement> {
  eyebrow?: string;
  title?: string;
  stats?: KeyFigureStat[];
  backgroundMediaUrl?: string;
  backgroundVideoUrl?: string;
  /** Couleur de fond. Défaut : `#141208` (dark Vancelian — variant historique). */
  backgroundColor?: string;
  backgroundImageOpacity?: number;
  overlayOpacity?: number;
}

export function SectionKeyFigures({
  eyebrow,
  title,
  stats = [],
  backgroundMediaUrl,
  backgroundVideoUrl,
  backgroundColor = "#141208",
  backgroundImageOpacity = 1,
  overlayOpacity = 0,
  className,
  ...props
}: SectionKeyFiguresProps) {
  const list = stats
    .slice(0, 6)
    .filter((s) => String(s?.value ?? "").trim() || String(s?.label ?? "").trim())
    .map((s) => ({
      value: String(s.value ?? "").trim() || "—",
      caption: String(s.label ?? "").trim() || "",
    }));

  if (list.length === 0) return null;

  const eyebrowText = eyebrow?.trim();
  const titleText = title?.trim();
  const hasHeader = Boolean(eyebrowText || titleText);

  // Détermine le ton selon la couleur de fond : si fond clair Vancelian, ton clair.
  const isLightBg =
    backgroundColor === "#F7F7F4" ||
    backgroundColor === "#FFFFFF" ||
    backgroundColor === "transparent";
  const tone: "light" | "dark" = isLightBg ? "light" : "dark";

  // Si pas de header : on rend directement VProofStats avec son fond canonique.
  if (!hasHeader) {
    return (
      <VProofStats
        stats={list}
        tone={tone}
        backgroundColor={backgroundColor}
        backgroundMediaUrl={backgroundMediaUrl}
        backgroundVideoUrl={backgroundVideoUrl}
        backgroundImageOpacity={backgroundImageOpacity}
        overlayOpacity={overlayOpacity}
        className={className}
        {...props}
      />
    );
  }

  // Avec header : on compose un wrapper qui porte le fond + image + overlay,
  // puis VProofStats en mode transparent.
  const imgOpacity = Math.min(1, Math.max(0, backgroundImageOpacity ?? 1));
  const overlayOp = Math.min(1, Math.max(0, overlayOpacity ?? 0));
  const hasImage = Boolean(backgroundMediaUrl?.trim() || backgroundVideoUrl?.trim());

  return (
    <section
      className={cn("relative w-full overflow-hidden py-20 lg:py-24", className)}
      style={{ backgroundColor }}
      {...props}
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
              style={{ backgroundColor }}
              data-overlay-opacity={overlayOp}
            />
          ) : null}
        </div>
      ) : null}

      <Container className="relative z-10">
        <div className="mx-auto mb-12 flex max-w-[720px] flex-col items-center text-center gap-6">
          {eyebrowText ? (
            <VEyebrow tone={tone === "dark" ? "inverse" : "light"}>
              {eyebrowText}
            </VEyebrow>
          ) : null}
          {titleText ? (
            <VEditorialTitle
              as="h2"
              size="page"
              tone={tone === "dark" ? "inverse" : "default"}
            >
              {titleText}
            </VEditorialTitle>
          ) : null}
        </div>

        {/* Stats inline DS — sans wrapper supplémentaire pour éviter le double-padding */}
        <ul
          className={cn(
            "m-0 flex w-full list-none flex-wrap items-start justify-center p-0",
            "gap-12 sm:gap-16 lg:gap-24",
          )}
        >
          {list.map((s, i) => (
            <li
              key={i}
              className="flex min-w-[120px] flex-col items-center gap-3 text-center"
            >
              <span
                className={cn(
                  "font-display font-light leading-[1.05] tracking-[0]",
                  "text-[44px] sm:text-[52px] lg:text-[56px]",
                  tone === "dark" ? "text-white" : "text-v-fg",
                )}
              >
                {s.value}
              </span>
              <span
                className={cn(
                  "font-ui font-normal text-[13px] leading-[1.45]",
                  tone === "dark" ? "text-white/65" : "text-v-fg-muted",
                )}
              >
                {s.caption}
              </span>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
