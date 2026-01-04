import * as React from "react";
import { cn } from "@/lib/utils";

export interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "default" | "narrow" | "wide";
}

export function Container({ 
  size = "default", 
  className, 
  children,
  ...props 
}: ContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-4 sm:px-8 md:px-16",
        size === "default" && "max-w-[1280px]",
        size === "narrow" && "max-w-[960px]",
        size === "wide" && "max-w-[1440px]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
