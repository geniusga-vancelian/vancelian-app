import * as React from "react";
import { mainTitleTypographyClassName } from "@/components/design-system/extracted";
import { cn } from "@/lib/utils";

export interface GradientHeadingProps {
  primaryText: string;
  gradientText: string;
  className?: string;
  primaryClassName?: string;
  gradientClassName?: string;
}

const GradientHeading = React.forwardRef<HTMLDivElement, GradientHeadingProps>(
  (
    {
      primaryText,
      gradientText,
      className,
      primaryClassName,
      gradientClassName,
    },
    ref,
  ) => {
    return (
      <div
        ref={ref}
        data-name="Main title"
        className={cn(
          "flex w-full flex-col items-center text-center text-black",
          mainTitleTypographyClassName,
          className,
        )}
      >
        <div
          className={cn(
            "w-full text-black",
            primaryClassName,
          )}
        >
          <span className="block leading-none">{primaryText}</span>
        </div>
        <div
          className={cn(
            "w-full bg-clip-text text-transparent",
            "bg-gradient-to-r from-[#E885D0] to-[#FFCD4E]",
            gradientClassName,
          )}
        >
          <span className="block leading-none">{gradientText}</span>
        </div>
      </div>
    );
  },
);
GradientHeading.displayName = "GradientHeading";

export { GradientHeading };
