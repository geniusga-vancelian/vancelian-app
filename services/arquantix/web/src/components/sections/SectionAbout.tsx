/**
 * SectionAbout — Vancelian Design System.
 *
 * Bloc « About » 2 colonnes (texte gauche, image droite) avec checklist
 * optionnelle. Pattern DS : voir `journey` (split éditorial) du pack handoff.
 *
 * Typographie :
 * - Titre : Inter SemiBold module-size (page si très long), tone default.
 * - Body : Inter Regular 16px, lh 1.6, text-v-fg-body.
 * - Checklist : KalaiIcon `check` 16px + texte 14px muted.
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import {
  VEditorialTitle,
} from "@/components/design-system/vancelian";
import { KalaiIcon } from "@/components/ui/KalaiIcon";

export interface SectionAboutProps extends React.HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  items?: Array<{
    title: string;
    description: string;
  }>;
  imageUrl?: string;
  content?: string;
  ctaText?: string;
  ctaLink?: string;
}

export function SectionAbout({
  title = "",
  description,
  items = [],
  imageUrl,
  content,
  className,
  ...props
}: SectionAboutProps) {
  const bodyText = [description, content]
    .map((s) => (typeof s === "string" ? s.trim() : ""))
    .filter(Boolean)
    .join("\n\n");
  const t = title?.trim();

  if (!t && !bodyText && items.length === 0 && !imageUrl) return null;

  const textBlock = (
    <div className="flex flex-col gap-6">
      {t ? (
        <VEditorialTitle as="h2" size="module" align="left" tone="default">
          {t}
        </VEditorialTitle>
      ) : null}
      {bodyText ? (
        <p className="m-0 font-ui font-normal text-[16px] leading-[1.6] text-v-fg-body whitespace-pre-line">
          {bodyText}
        </p>
      ) : null}
      {items.length > 0 ? (
        <ul className="m-0 flex flex-col gap-3 list-none p-0">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-start gap-3 font-ui font-normal text-[14px] leading-[1.55] text-v-fg-body"
            >
              <KalaiIcon name="check" size={16} className="text-v-fg mt-1 flex-none" />
              <span className="min-w-0 flex-1">
                {item.title ? <strong className="font-semibold text-v-fg">{item.title}</strong> : null}
                {item.title && item.description ? " — " : null}
                {item.description}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );

  return (
    <section
      className={cn("w-full bg-v-bg py-20 lg:py-28", className)}
      {...props}
    >
      <Container>
        {imageUrl ? (
          <div className="grid gap-10 lg:grid-cols-2 lg:gap-16 items-center">
            <div className="lg:order-1">{textBlock}</div>
            <div className="lg:order-2 overflow-hidden rounded-v-card">
              {/* eslint-disable-next-line @next/next/no-img-element -- image éditoriale CMS */}
              <img
                src={imageUrl}
                alt={t || ""}
                className="block aspect-[4/3] w-full object-cover"
              />
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-[720px]">{textBlock}</div>
        )}
      </Container>
    </section>
  );
}
