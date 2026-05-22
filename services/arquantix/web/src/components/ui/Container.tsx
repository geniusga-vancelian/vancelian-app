import * as React from "react";
import { cn } from "@/lib/utils";

export interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "default" | "narrow" | "wide";
}

/**
 * Largeur de contenu site-wide — classe DS `.v-container`
 * (1280px max, padding 48 / 24 / 16 px selon breakpoint).
 * Même conteneur que les modules CMS (`FaqSection`, `Footer`, etc.).
 */
export function Container({
  size = "default",
  className,
  children,
  ...props
}: ContainerProps) {
  return (
    <div
      className={cn(
        "v-container",
        size === "narrow" && "max-w-[960px]",
        size === "wide" && "max-w-[1440px]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
