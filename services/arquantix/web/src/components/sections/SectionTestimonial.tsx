"use client";

/**
 * Citation isolée fullbleed — Vancelian Design System.
 *
 * Pattern : une seule citation éditoriale, centrée, sur fond image avec
 * overlay sombre. Composé en interne par {@link VTcard} ? Non : ici le DS
 * privilégie un rendu « éditorial pleine page » sans encadré — texte en
 * Newsreader Display italic sur fond photo, attribution en bas.
 *
 * Voir doctrine pack handoff §«hero éditorial» pour les principes de
 * composition (full-bleed, dark overlay, balance typographique).
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { VEyebrow } from "@/components/design-system/vancelian";

export interface SectionTestimonialProps extends React.HTMLAttributes<HTMLElement> {
  /** Surtitre éditorial (caption uppercase). */
  tag?: string;
  /** Citation — affichée en Newsreader Display Light Italic. */
  quote?: string;
  /** Nom de l'auteur. */
  author?: string;
  /** Rôle / titre sous l'auteur. */
  role?: string;
  /** URL d'image de fond. */
  backgroundImage?: string;
}

export function SectionTestimonial({
  tag,
  quote,
  author,
  role,
  backgroundImage,
  className,
  ...props
}: SectionTestimonialProps) {
  const q = quote?.trim();
  const a = author?.trim();
  if (!q && !a) return null;

  return (
    <section
      data-nav-surface="dark"
      className={cn(
        "relative w-full overflow-hidden bg-v-dark-bg",
        "py-32 lg:py-40",
        className,
      )}
      {...props}
    >
      {backgroundImage ? (
        <div className="absolute inset-0 z-0" aria-hidden>
          {/* eslint-disable-next-line @next/next/no-img-element -- image fond éditorial CMS */}
          <img
            src={backgroundImage}
            alt=""
            className="absolute inset-0 h-full w-full object-cover object-center"
            sizes="100vw"
          />
          <div className="absolute inset-0 bg-[rgba(20,18,8,0.78)]" />
        </div>
      ) : null}

      <Container className="relative z-10">
        <figure className="mx-auto flex max-w-[820px] flex-col items-center text-center">
          {tag?.trim() ? <VEyebrow tone="inverse">{tag}</VEyebrow> : null}

          {q ? (
            <blockquote
              className={cn(
                "m-0 font-display font-light italic text-balance",
                "text-[clamp(28px,3.8vw,44px)] leading-[1.3] tracking-[0]",
                "text-white",
                tag ? "mt-8" : "mt-0",
              )}
            >
              <span aria-hidden="true">« </span>
              {q.replace(/^["«»]+|["«»]+$/g, "").trim()}
              <span aria-hidden="true"> »</span>
            </blockquote>
          ) : null}

          {(a || role?.trim()) ? (
            <figcaption className="mt-12 flex flex-col items-center gap-1">
              {a ? (
                <cite className="font-ui font-semibold text-[15px] leading-tight text-white not-italic">
                  {a}
                </cite>
              ) : null}
              {role?.trim() ? (
                <span className="font-ui font-normal text-[13px] leading-tight text-white/70">
                  {role}
                </span>
              ) : null}
            </figcaption>
          ) : null}
        </figure>
      </Container>
    </section>
  );
}
