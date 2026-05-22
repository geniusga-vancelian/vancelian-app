import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * Bouton aligné sur le Design System Vancelian.
 *
 * Décisions DS appliquées (voir `src/styles/vancelian-tokens.css`) :
 * - **Radius pill** (`rounded-v-pill` = 999px). Tous les boutons sont pill.
 * - **CTA primaire = anthracite** (`bg-primary` = `var(--v-fg)` = #1A1815).
 *   Jamais terracotta — la terracotta est réservée aux text-links et accents
 *   éditoriaux. (Cf. règle inviolable n°2 du DS.)
 * - Hover : anthracite légèrement allégé (#3B3633). Active : noir pur.
 * - **Secondary outline** : bordure anthracite 1px, fond `var(--v-fg-05)` au hover.
 * - **Dark variants** : pour les fonds sombres (footer, final-cta, journey).
 * - **Tailles strictes DS** : `sm` (10px/16px padding, 13px text), `md` /
 *   `default` (14px/24px padding, 14px text).
 * - Font : Inter Medium (500). Aucun usage de Newsreader sur un bouton.
 *
 * Les variants historiques `arquantix` / `arquantixOutline` (couleurs Bronze
 * `#C6A47C`) sont conservés en bridge pendant la migration : ils héritent
 * désormais de la terracotta DS via `bg-brand-bronze`.
 */
const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "font-ui font-medium leading-none",
    "ring-offset-background transition-colors duration-v-fast ease-v-out",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
    "disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  ].join(" "),
  {
    variants: {
      variant: {
        /** CTA primaire — anthracite (jamais terracotta). */
        default:
          "rounded-v-pill bg-v-fg text-white hover:bg-[#3B3633] active:bg-black",
        /** Erreur — seul rouge autorisé (#B83A3A). */
        destructive:
          "rounded-v-pill bg-destructive text-destructive-foreground hover:bg-destructive/90",
        /** Outline anthracite — bordure 1px : padding réduit pour hauteur visuelle identique à `md`. */
        outline:
          "rounded-v-pill border border-v-fg bg-transparent text-v-fg hover:bg-v-fg-05 active:bg-v-fg-10",
        /** Subtle — fond `--v-fg-05` (papier off-white légèrement saturé). */
        secondary:
          "rounded-v-pill bg-secondary text-secondary-foreground hover:bg-v-card-hover",
        /** Ghost — pas de fond, fond `--v-fg-05` au hover. */
        ghost:
          "rounded-v-pill text-v-fg hover:bg-v-fg-05",
        /** Link — text-link terracotta (seul endroit DS où la terracotta apparaît dans l'UI). */
        link:
          "text-v-terracotta hover:underline underline-offset-[3px] active:text-v-terracotta-pressed",
        /** Primary sur fond sombre (final-cta, footer). */
        darkPrimary:
          "rounded-v-pill bg-v-dark-fg text-v-fg hover:bg-white",
        /** Secondary sur fond sombre — bordure 1px. */
        darkSecondary:
          "rounded-v-pill border border-v-dark-fg bg-transparent text-v-dark-fg hover:bg-white/[0.08]",
        /**
         * Legacy Arquantix — hérite désormais de la terracotta DS
         * (l'ancien Bronze #C6A47C est remappé en `bg-brand-bronze`).
         * À déprécier au profit de `default`.
         */
        arquantix:
          "rounded-v-pill bg-brand-bronze text-white hover:opacity-90 uppercase tracking-wider text-[10px]",
        arquantixOutline:
          "rounded-v-pill border border-v-dark-fg bg-transparent text-v-dark-fg hover:bg-white/[0.05] uppercase tracking-wider text-[10px]",
      },
      size: {
        /** DS Vancelian `md` — 14px / padding 14×24 (spec Home.html `.btn--md`). */
        default: "h-auto px-6 py-[14px] text-[14px] leading-none",
        /** DS Vancelian `sm` — 13px / padding 10×16. */
        sm: "h-auto px-4 py-[10px] text-[13px] leading-none",
        /** Variante `lg` — usage marketing hero. */
        lg: "h-auto px-8 py-[16px] text-[15px] leading-none",
        /** Icône seule — carré 40×40. */
        icon: "h-10 w-10",
        /** Compatibilité Arquantix legacy. */
        arquantix: "h-9 px-5 py-2.5",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
    compoundVariants: [
      {
        variant: ['outline', 'darkSecondary', 'arquantixOutline'],
        size: 'default',
        class: 'px-[23px] py-[13px]',
      },
    ],
  },
);

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot : "button";

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
