import * as React from "react";
import svgPaths from "@/imports/svg-uawwnp5dcp";

export interface LogoProps extends React.SVGAttributes<SVGSVGElement> {
  variant?: "default" | "icon";
  color?: "white" | "black";
}

export function Logo({ variant = "default", className, color = "white", ...props }: LogoProps) {
  const fillColor = color === "black" ? "black" : "white";
  
  if (variant === "icon") {
    return (
      <svg
        className={className}
        fill="none"
        preserveAspectRatio="none"
        viewBox="0 0 178 85.7715"
        {...props}
      >
        <path d={svgPaths.p25268400} fill={fillColor} />
      </svg>
    );
  }

  return (
    <svg
      className={className}
      fill="none"
      preserveAspectRatio="xMidYMid meet"
      viewBox="0 0 178 85.7715"
      {...props}
    >
      <path d={svgPaths.p25268400} fill={fillColor} />
    </svg>
  );
}
