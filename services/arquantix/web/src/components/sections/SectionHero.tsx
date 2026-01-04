import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { StarIcon } from "@/components/ui/StarIcon";
import svgPaths from "@/imports/svg-uawwnp5dcp";

export interface SectionHeroProps extends React.HTMLAttributes<HTMLElement> {
  backgroundImage?: string;
}

const features = [
  { label: "15 Villas delivered" },
  { label: "Institutionally managed" },
  { label: "Global real estate" },
];

export function SectionHero({ 
  backgroundImage,
  className, 
  ...props 
}: SectionHeroProps) {
  return (
    <section
      className={cn("relative w-full min-h-[660px] overflow-hidden", className)}
      {...props}
    >
      {/* Background Image + Overlay */}
      <div className="absolute inset-0 z-0">
        <img
          src={backgroundImage || "/images/hero-background.png"}
          alt=""
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-black/50" />
      </div>

      {/* Decorative SVG Pattern */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-20">
        <svg
          className="absolute top-0 right-0 w-full h-full"
          fill="none"
          preserveAspectRatio="none"
          viewBox="0 0 1888.07 2502.17"
          style={{ transform: "rotate(341.861deg) translate(20%, -40%)" }}
        >
          <path d={svgPaths.p34635f80} stroke="#C6A47C" strokeMiterlimit="10" />
        </svg>
      </div>

      {/* Content Container */}
      <div className="relative z-10 mx-auto max-w-[1280px] w-full px-8 md:px-16 min-h-[660px] flex flex-col md:flex-row">
        {/* Left Sidebar - Features */}
        <aside className="hidden md:flex flex-col justify-between w-[178px] py-16 px-7 bg-gradient-to-b from-transparent to-black/50 border-r border-[#272727]">
          <div className="flex flex-col items-center justify-center gap-2.5 flex-1">
            {/* Vertical Text */}
            <div className="flex items-center justify-center h-[100px] w-2">
              <p className="text-[#5F5F5F] text-[11px] uppercase whitespace-nowrap origin-center -rotate-90">
                Lorem ipsum dolor it
              </p>
            </div>
            {/* Vertical Line */}
            <div className="w-px flex-1 bg-[#5F5F5F]" />
          </div>

          {/* Features List */}
          <div className="flex flex-col gap-7">
            {features.map((feature, idx) => (
              <div key={idx} className="flex flex-col gap-2.5">
                <StarIcon className="w-[18px] h-[13px]" />
                <p className="text-[#E6E6E6] text-sm uppercase leading-tight">
                  {feature.label}
                </p>
              </div>
            ))}
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col items-end justify-center gap-7 py-16 md:py-24 px-4 md:px-16">
          <h1 className="text-white text-right text-3xl md:text-4xl lg:text-[36px] uppercase tracking-wide leading-tight max-w-2xl">
            Fractional real estate,
            <br />
            institutional rigor.
          </h1>

          <p className="text-[#E6E6E6] text-sm text-right leading-relaxed max-w-md">
            Arquantix provides access to fractional ownership of premium real estate assets. 
            Every investment is structured with the same discipline, transparency and governance 
            standards expected from an institutional financial operator.
          </p>

          <Button variant="arquantix" size="arquantix" asChild>
            <a href="https://wa.me/6281353009603?text=Hello,%20I'm%20interested%20in%20The%20Heights%20Munduk">
              Call to action
            </a>
          </Button>
        </div>
      </div>
    </section>
  );
}