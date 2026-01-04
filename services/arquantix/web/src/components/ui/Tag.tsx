import * as React from "react";
import { cn } from "@/lib/utils";

export interface TagProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "outlined";
}

export function Tag({ 
  variant = "outlined", 
  className, 
  children,
  ...props 
}: TagProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center justify-center px-1 py-0.5 rounded-sm border border-white/40",
        "text-[11px] uppercase tracking-wide",
        "transition-colors",
        variant === "default" && "bg-white/10",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
