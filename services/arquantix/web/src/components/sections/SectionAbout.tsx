import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Button } from "@/components/ui/button";

export interface SectionAboutProps extends React.HTMLAttributes<HTMLElement> {}

const features = [
  {
    title: "15 assets delivered",
    description: "Proven execution track record",
  },
  {
    title: "Institutionally managed",
    description: "Regulated financial structure",
  },
  {
    title: "Global real estate",
    description: "Bali • Dubai • Japan",
  },
];

export function SectionAbout({ className, ...props }: SectionAboutProps) {
  return (
    <section
      className={cn("w-full bg-[#1A1A1A] py-16 md:py-20", className)}
      {...props}
    >
      <Container>
        <div className="flex flex-col items-center gap-10">
          {/* Section Header */}
          <SectionHeader
            tag="About us"
            title={
              <>
                Built on real assets.{" "}
                <span className="text-[#C6A47C]">Delivered.</span>
              </>
            }
          />

          {/* Content Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0 w-full">
            {/* Left - Image */}
            <div className="relative h-[311px] overflow-hidden">
              <img
                src="/images/about-asset.png"
                alt="Real estate asset"
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-black/30" />
            </div>

            {/* Middle - Description */}
            <div className="border-x border-[#5F5F5F] p-7 md:p-8 flex flex-col justify-center bg-[#0D0D0D]">
              <div className="space-y-4 text-[#E6E6E6] text-sm leading-relaxed">
                <p>
                  Arquantix provides access to fractional ownership of premium real 
                  estate assets through a regulated financial structure.
                </p>
                <p>
                  Unlike traditional real estate marketplaces, we originate, develop 
                  and manage each project end-to-end, from land acquisition to delivery 
                  and ongoing operations.
                </p>
                <p>
                  This integrated approach ensures full control over execution, asset 
                  quality and long-term performance.
                </p>
                <p className="text-[#C6A47C]">
                  Our model combines institutional governance with real, tangible assets 
                  already delivered across international markets.
                </p>
              </div>
            </div>

            {/* Right - Features */}
            <div className="p-7 md:p-8 flex flex-col justify-center gap-14 bg-[#0D0D0D]">
              {features.map((feature, idx) => (
                <div key={idx} className="flex flex-col gap-5">
                  <h3 className="text-white text-lg uppercase">
                    {feature.title}
                  </h3>
                  <p className="text-[#E6E6E6] text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* CTA Button */}
          <Button variant="arquantixOutline" size="arquantix">
            En Savoir Plus
          </Button>
        </div>
      </Container>
    </section>
  );
}