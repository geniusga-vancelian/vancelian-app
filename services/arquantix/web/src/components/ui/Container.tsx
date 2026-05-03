import * as React from "react";
import { cn } from "@/lib/utils";

export interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "default" | "narrow" | "wide";
}

/**
 * Largeur de contenu alignée site-wide (~1280px), centrée, padding horizontal responsive.
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
        "mx-auto w-full max-w-[1280px] px-6 lg:px-8",
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
