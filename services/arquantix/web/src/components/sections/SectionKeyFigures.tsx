"use client";

/**
 * Grille « Key figures » (chiffres clés) — fond sombre, séparateurs verticaux, typo Avenir (design system).
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import { SectionTitle } from "@/components/design-system/extracted";
import { Container } from "@/components/ui/Container";
import { hexWithOpacity } from "@/components/design-system/marketing-block";

export interface KeyFigureStat {
  value?: string;
  label?: string;
}

export interface SectionKeyFiguresProps extends React.HTMLAttributes<HTMLElement> {
  eyebrow?: string;
  title?: string;
  stats?: KeyFigureStat[];
  backgroundMediaUrl?: string;
  backgroundColor?: string;
  backgroundImageOpacity?: number;
  /** Teinte par-dessus l’image (0 = aucune) */
  overlayOpacity?: number;
}

function KeyFigureCell({
  value,
  label,
}: {
  value: string;
  label: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-start gap-2.5 px-5 py-9 sm:px-6 sm:py-10 md:px-8 md:py-11",
      )}
    >
      <p
        className="font-['Avenir:Heavy',sans-serif] text-[1.75rem] leading-[1.1] tracking-[-0.02em] text-white sm:text-[2rem] md:text-[2.125rem] lg:text-[2.25rem]"
      >
        {value}
      </p>
      <p className="font-['Avenir:Roman',sans-serif] text-[0.9375rem] leading-[1.55] text-white/75 md:text-base">
        {label}
      </p>
    </div>
  );
}

export function SectionKeyFigures({
  eyebrow,
  title,
  stats = [],
  backgroundMediaUrl,
  backgroundColor = "#000000",
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
      label: String(s.label ?? "").trim() || "",
    }));

  if (list.length === 0) {
    return null;
  }

  const hasImage = Boolean(backgroundMediaUrl?.trim());
  const imgOpacity = Math.min(1, Math.max(0, backgroundImageOpacity ?? 1));
  const overlayOp = Math.min(1, Math.max(0, overlayOpacity ?? 0));

  const eyebrowText = eyebrow?.trim();
  const titleText = title?.trim();

  return (
    <section
      className={cn(
        "relative w-full overflow-hidden py-10 md:py-14",
        className,
      )}
      {...props}
    >
      <div
        className="pointer-events-none absolute inset-y-0 left-1/2 z-0 w-screen max-w-none -translate-x-1/2"
        aria-hidden
      >
        <div className="absolute inset-0" style={{ backgroundColor }} />
        {hasImage ? (
          <>
            <img
              alt=""
              src={backgroundMediaUrl}
              className="absolute inset-0 h-full w-full object-cover object-center"
              style={{ opacity: imgOpacity }}
              sizes="100vw"
            />
            {overlayOp > 0 ? (
              <div
                className="absolute inset-0"
                style={{
                  backgroundColor: hexWithOpacity(backgroundColor, overlayOp),
                }}
              />
            ) : null}
          </>
        ) : null}
      </div>

      <Container className="relative z-10">
        <div className="mx-auto w-full max-w-[1100px]">
          {(eyebrowText || titleText) && (
            <div className="mb-10 flex w-full flex-col gap-3 px-4 text-center sm:px-6 md:px-8">
              {eyebrowText ? (
                <p className="font-['Avenir:Heavy',sans-serif] text-[11px] uppercase tracking-[0.22em] text-white/85 md:text-xs">
                  {eyebrowText}
                </p>
              ) : null}
              {titleText ? (
                <SectionTitle align="center" color="#ffffff" size="module">
                  {titleText}
                </SectionTitle>
              ) : null}
            </div>
          )}

          {/* Mobile : pile avec séparateurs horizontaux */}
          <div className="divide-y divide-white/25 border-y border-white/25 md:hidden">
            {list.map((s, i) => (
              <KeyFigureCell key={i} value={s.value} label={s.label} />
            ))}
          </div>

          {/* Desktop : grille 3 colonnes — séparateurs verticaux et ligne entre les deux rangées */}
          <div className="hidden md:grid md:grid-cols-3 md:border md:border-white/25">
            {list.map((s, i) => (
              <div
                key={i}
                className={cn(
                  (i % 3) !== 2 && "border-r border-white/25",
                  i >= 3 && "border-t border-white/25",
                )}
              >
                <KeyFigureCell value={s.value} label={s.label} />
              </div>
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}
