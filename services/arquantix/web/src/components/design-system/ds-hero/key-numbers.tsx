import * as React from "react";
import { cn } from "@/lib/utils";
import { StatCard } from "./stat-card";

export interface KeyNumberData {
  value: string;
  label: string;
}

export interface KeyNumbersProps {
  stats: KeyNumberData[];
  className?: string;
}

const KeyNumbers = React.forwardRef<HTMLDivElement, KeyNumbersProps>(
  ({ stats, className }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex w-full max-w-[1004px] flex-wrap items-stretch justify-center gap-y-2 sm:flex-nowrap sm:gap-y-0",
          "min-h-0 border-t border-[#f3f3f3] pt-2",
          className,
        )}
      >
        {stats.map((stat, index) => (
          <StatCard
            key={`${stat.label}-${index}`}
            value={stat.value}
            label={stat.label}
            showBorder={index > 0}
            className="min-w-[140px] flex-[1_1_40%] sm:flex-1"
          />
        ))}
      </div>
    );
  },
);
KeyNumbers.displayName = "KeyNumbers";

export { KeyNumbers };
