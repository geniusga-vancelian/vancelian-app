import * as React from "react";
import svgPaths from "@/imports/svg-uawwnp5dcp";

export interface StarIconProps extends React.SVGAttributes<SVGSVGElement> {}

export function StarIcon({ className, ...props }: StarIconProps) {
  return (
    <svg
      className={className}
      fill="none"
      preserveAspectRatio="none"
      viewBox="0 0 18 13.2344"
      {...props}
    >
      <g>
        <path d={svgPaths.pfcafc80} fill="#C6A47C" />
        <path d={svgPaths.p134f5600} fill="#C6A47C" />
        <path d={svgPaths.p7af600} fill="#C6A47C" />
        <path d={svgPaths.p96a6000} fill="#C6A47C" />
        <path d={svgPaths.p336eb1c0} fill="#C6A47C" />
        <path d={svgPaths.p11802f00} fill="#C6A47C" />
      </g>
    </svg>
  );
}
