"use client";

import { SectionTitle } from "@/components/design-system/extracted";
import { Testimonial } from "@/components/design-system/Testimonial";
import { Container } from "@/components/ui/Container";
import { arquantixContentTextBlockClass } from "@/lib/design/contentMaxWidth";
import { cn } from "@/lib/utils";

export interface TestimonialItem {
  name: string;
  text: string;
  rating: number;
  /** Rôle affiché sous le nom (ex. « Family office ») */
  title?: string;
  avatarMediaId?: string;
  /** Injecté par `getPageSections` depuis `avatarMediaId` */
  avatarMediaUrl?: string;
  /** @deprecated URL directe — préférer la médiathèque */
  avatar?: string;
}

export interface SectionTestimonialsProps {
  /** Surtitre (pastille style DS, au-dessus du titre). */
  eyebrow?: string;
  title?: string;
  /** Chapô sous le titre (Avenir Roman). */
  description?: string;
  items?: TestimonialItem[];
}

/** Aligné sur `FAQLabel` dans `FAQ.tsx` (mêmes classes). */
function TestimonialsEyebrow({ text }: { text: string }) {
  const t = text.trim();
  if (!t) return null;
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0">
      <div
        aria-hidden="true"
        className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]"
      />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">
        {t}
      </p>
    </div>
  );
}

const AVATAR_PLACEHOLDERS = [
  "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=96&h=96&fit=crop",
  "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=96&h=96&fit=crop",
  "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=96&h=96&fit=crop",
];

/**
 * Grille de témoignages — compose le composant DS Testimonial (un par carte).
 */
export function SectionTestimonials({
  eyebrow,
  title,
  description,
  items = [],
}: SectionTestimonialsProps) {
  const e = eyebrow?.trim();
  const t = title?.trim();
  const d = description?.trim();
  const hasHeader = Boolean(e || t || d);

  return (
    <section className="w-full bg-white py-12 md:py-16">
      <Container className="flex flex-col items-center gap-10">
        {hasHeader ? (
          <div className="content-stretch relative flex w-full max-w-[900px] shrink-0 flex-col items-center gap-[10px] text-center">
            {e ? <TestimonialsEyebrow text={e} /> : null}
            {t ? (
              <SectionTitle align="center" color="#000000" size="module">
                {t}
              </SectionTitle>
            ) : null}
            {d ? (
              <p
                className={cn(
                  "text-center font-['Avenir:Roman',sans-serif] text-[18px] leading-[1.6] text-black/85",
                  arquantixContentTextBlockClass,
                )}
              >
                {d}
              </p>
            ) : null}
          </div>
        ) : null}
        <div className="flex w-full flex-wrap justify-center gap-6">
          {items.map((item, index) => {
            const fromMedia =
              typeof item.avatarMediaUrl === "string" && item.avatarMediaUrl.trim()
                ? item.avatarMediaUrl.trim()
                : undefined;
            const fromLegacy =
              typeof item.avatar === "string" && item.avatar.trim()
                ? item.avatar.trim()
                : undefined;
            const authorImage =
              fromMedia ||
              fromLegacy ||
              (AVATAR_PLACEHOLDERS[index % AVATAR_PLACEHOLDERS.length] ??
                AVATAR_PLACEHOLDERS[0]);
            return (
              <div
                key={`${item.name}-${index}`}
                className="w-full max-w-[378px] shrink-0"
              >
                <Testimonial
                  authorName={item.name}
                  authorTitle={item.title ?? "Investor"}
                  authorImage={authorImage}
                  rating={Math.min(5, Math.max(0, Math.round(item.rating)))}
                  testimonialText={item.text}
                />
              </div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
