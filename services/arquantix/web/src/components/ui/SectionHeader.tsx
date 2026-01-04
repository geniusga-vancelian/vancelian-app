import * as React from "react";
import { cn } from "@/lib/utils";
import { Tag } from "./Tag";

export interface SectionHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  tag?: string;
  title: React.ReactNode;
  highlightColor?: string;
  description?: string;
  align?: "left" | "center" | "right";
}

export function SectionHeader({ 
  tag,
  title, 
  highlightColor = "text-[#C6A47C]",
  description,
  align = "center",
  className,
  ...props 
}: SectionHeaderProps) {
  const alignClass = {
    left: "items-start text-left",
    center: "items-center text-center",
    right: "items-end text-right",
  }[align];

  return (
    <div
      className={cn(
        "flex flex-col gap-2.5 w-full",
        alignClass,
        className
      )}
      {...props}
    >
      {tag && (
        <div className="opacity-50">
          <Tag>{tag}</Tag>
        </div>
      )}
      
      <h2 className="text-[#E6E6E6] uppercase tracking-wider max-w-4xl">
        {typeof title === "string" ? (
          <span className={cn("inline", highlightColor)}>{title}</span>
        ) : (
          title
        )}
      </h2>

      {description && (
        <p className="text-[#E6E6E6] text-sm leading-relaxed max-w-2xl opacity-90">
          {description}
        </p>
      )}
    </div>
  );
}
