import * as React from "react";
import { cn } from "@/lib/utils";

export interface StatCardProps {
  value: string;
  label: string;
  className?: string;
  showBorder?: boolean;
}

const StatCard = React.forwardRef<HTMLDivElement, StatCardProps>(
  ({ value, label, className, showBorder = false }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "relative min-h-px min-w-0 flex-1",
          showBorder && "border-l border-[#f3f3f3]",
          className,
        )}
      >
        <div className="flex h-full flex-row items-center">
          <div className="flex w-full items-center px-4 py-6 sm:px-5 sm:py-7">
            <div className="flex w-full flex-col items-start gap-2.5 text-[#62656e]">
              <p className="font-ui font-semibold text-[24px] leading-[1.1] tracking-[-0.24px]">
                {value}
              </p>
              <p className="font-ui font-normal text-[14px] leading-[1.6]">
                {label}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  },
);
StatCard.displayName = "StatCard";

export { StatCard };
