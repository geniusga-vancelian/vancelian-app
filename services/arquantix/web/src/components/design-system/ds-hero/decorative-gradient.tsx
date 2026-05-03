import * as React from "react";
import { cn } from "@/lib/utils";

export interface DecorativeGradientProps {
  className?: string;
}

/** Décor SVG Figma (traits dégradés rose/orange), opacité faible. */
const DecorativeGradient = React.forwardRef<HTMLDivElement, DecorativeGradientProps>(
  ({ className }, ref) => {
    return (
      <div ref={ref} className={cn("relative size-full", className)}>
        <div className="absolute inset-[0_-0.2%_-0.49%_0]">
          <svg
            className="block size-full"
            fill="none"
            preserveAspectRatio="none"
            viewBox="0 0 3573.05 692.524"
          >
            <g opacity="0.1">
              <path
                d="M1094.46 64.3458L1066.32 542.984"
                stroke="url(#paint0_linear_ds_hero)"
                strokeMiterlimit="10"
                strokeWidth="6"
              />
              <path
                d="M2648.81 154.915L2620.67 633.553"
                stroke="url(#paint1_linear_ds_hero)"
                strokeMiterlimit="10"
                strokeWidth="6"
              />
            </g>
            <defs>
              <linearGradient
                gradientUnits="userSpaceOnUse"
                id="paint0_linear_ds_hero"
                x1="1094.46"
                x2="1066.32"
                y1="64.3458"
                y2="542.984"
              >
                <stop stopColor="#E885D0" />
                <stop offset="1" stopColor="#FFB84D" />
              </linearGradient>
              <linearGradient
                gradientUnits="userSpaceOnUse"
                id="paint1_linear_ds_hero"
                x1="2648.81"
                x2="2620.67"
                y1="154.915"
                y2="633.553"
              >
                <stop stopColor="#E885D0" />
                <stop offset="1" stopColor="#FFB84D" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      </div>
    );
  },
);
DecorativeGradient.displayName = "DecorativeGradient";

export { DecorativeGradient };
