"use client";

/**
 * Grille de témoignages — Vancelian Design System.
 *
 * Délègue chaque carte à {@link VTcard} (pattern DS `tcard`) et compose
 * le header standard (eyebrow + titre éditorial + chapô).
 */
import { VTcard } from "@/components/design-system/vancelian/VTcard";
import { VSectionHeader } from "@/components/design-system/vancelian/VSectionHeader";
import { Container } from "@/components/ui/Container";

export interface TestimonialItem {
  name: string;
  text: string;
  rating: number;
  /** Rôle affiché sous le nom (ex. « Family office · Paris »). */
  title?: string;
  avatarMediaId?: string;
  /** Injecté par `getPageSections` depuis `avatarMediaId`. */
  avatarMediaUrl?: string;
  /** @deprecated URL directe — préférer la médiathèque. */
  avatar?: string;
}

export interface SectionTestimonialsProps {
  eyebrow?: string;
  title?: string;
  description?: string;
  items?: TestimonialItem[];
}

export function SectionTestimonials({
  eyebrow,
  title,
  description,
  items = [],
}: SectionTestimonialsProps) {
  if (items.length === 0) {
    // Section vide : ne pas rendre (respect doctrine « pas de fallback hardcodé »)
    if (!eyebrow?.trim() && !title?.trim() && !description?.trim()) {
      return null;
    }
  }

  // Détermine combien de colonnes selon le nombre d'items (1, 2 ou 3+ → 2 col).
  // DS officiel : 2 colonnes desktop pour la grille tcard.
  const gridClasses =
    items.length === 1
      ? "grid grid-cols-1 max-w-[640px] mx-auto"
      : "grid grid-cols-1 md:grid-cols-2 items-stretch";

  return (
    <section className="w-full bg-v-bg py-24 lg:py-32">
      <Container className="flex flex-col items-center gap-16">
        <div data-v-scroll-fade className="w-full">
          <VSectionHeader
            eyebrow={eyebrow}
            title={title}
            description={description}
            titleAs="h2"
            titleSize="page"
          />
        </div>

        {items.length > 0 ? (
          <div data-v-scroll-fade className={`${gridClasses} w-full gap-6`}>
            {items.map((item, index) => {
              const fromMedia =
                typeof item.avatarMediaUrl === "string" && item.avatarMediaUrl.trim()
                  ? item.avatarMediaUrl.trim()
                  : undefined;
              const fromLegacy =
                typeof item.avatar === "string" && item.avatar.trim()
                  ? item.avatar.trim()
                  : undefined;
              const avatarUrl = fromMedia ?? fromLegacy ?? undefined;
              return (
                <VTcard
                  key={`${item.name}-${index}`}
                  quote={item.text}
                  authorName={item.name}
                  authorRole={item.title}
                  avatarUrl={avatarUrl}
                  rating={item.rating}
                />
              );
            })}
          </div>
        ) : null}
      </Container>
    </section>
  );
}
