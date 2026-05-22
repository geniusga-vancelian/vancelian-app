import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Lockup Vancelian — assets officiels du DS (`public/brand/vancelian/`).
 *
 * Six combinaisons disponibles : `horizontal | vertical | icon` × `black | white`.
 *
 * Règle DS : le lockup horizontal anthracite reste la version par défaut.
 * Inverser en blanc uniquement sur fond sombre (footer, final-cta, hero).
 */
export type LogoLockup = "horizontal" | "vertical" | "icon"
export type LogoColor = "black" | "white"

export interface LogoProps extends React.HTMLAttributes<HTMLImageElement> {
  /** Lockup à afficher (défaut : `horizontal`). */
  lockup?: LogoLockup
  /** Couleur du logo (défaut : `black` sur fond clair). */
  color?: LogoColor
  /** Texte alternatif (défaut : `Vancelian`). */
  alt?: string
  /**
   * Alias legacy compatible avec l'ancien composant (`variant` + `color`).
   * `variant="icon"` → `lockup="icon"`. `variant="default"` → `lockup="horizontal"`.
   */
  variant?: "default" | "icon"
}

const FILE_BY_VARIANT: Record<LogoLockup, Record<LogoColor, string>> = {
  horizontal: {
    black: "/brand/vancelian/logo-black-h.svg",
    white: "/brand/vancelian/logo-white-h.svg",
  },
  vertical: {
    black: "/brand/vancelian/logo-black-v.svg",
    white: "/brand/vancelian/logo-white-v.svg",
  },
  icon: {
    black: "/brand/vancelian/logo-black-icon.svg",
    white: "/brand/vancelian/logo-white-icon.svg",
  },
}

export function Logo({
  lockup,
  variant,
  className,
  color = "black",
  alt = "Vancelian",
  ...props
}: LogoProps) {
  const resolved: LogoLockup = lockup ?? (variant === "icon" ? "icon" : "horizontal")
  const src = FILE_BY_VARIANT[resolved][color]

  return (
    // eslint-disable-next-line @next/next/no-img-element -- asset SVG statique du DS, pas optimisable par next/image
    <img
      src={src}
      alt={alt}
      className={cn("block max-h-full w-auto", className)}
      {...props}
    />
  )
}

/**
 * Wordmark texte VANCELIAN — Newsreader UPPERCASE 0.4em letter-spacing.
 *
 * Règle DS inviolable n°4 : le wordmark texte ne s'écrit qu'avec Newsreader
 * (jamais Inter) et la lettre-spacing `0.4em`. À utiliser dans les contextes
 * où on veut le mot « Vancelian » plutôt que le glyphe (ex. méga-menu, signature
 * éditoriale, e-mails).
 */
export function VancelianWordmark({
  className,
  children = "Vancelian",
}: {
  className?: string
  children?: React.ReactNode
}) {
  return <span className={cn("v-wordmark", className)}>{children}</span>
}
