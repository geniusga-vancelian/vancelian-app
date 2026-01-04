import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { Tag } from "@/components/ui/Tag";

export interface SectionAlternateProps extends React.HTMLAttributes<HTMLElement> {}

const features = [
  {
    tag: "About us",
    title: (
      <>
        Built on <span className="text-[#C6A47C]">real</span> assets. Delivered.
      </>
    ),
    description: [
      "Arquantix provides access to fractional ownership of premium real estate assets through a regulated financial structure.",
      "Unlike traditional real estate marketplaces, we originate, develop and manage each project end-to-end, from land acquisition to delivery and ongoing operations.",
      "This integrated approach ensures full control over execution, asset quality and long-term performance.",
    ],
    image: "/images/alternate-1.png",
  },
  {
    tag: "About us",
    title: (
      <>
        Institutional <span className="text-[#C6A47C]">governance</span>. Real assets.
      </>
    ),
    description: [
      "Every investment is structured with the same discipline, transparency and governance standards expected from an institutional financial operator.",
      "Our model combines institutional rigor with tangible assets already delivered across international markets.",
      "We provide full visibility on asset structure, expected returns and risk factors.",
    ],
    image: "/images/alternate-2.png",
  },
];

export function SectionAlternate({ className, ...props }: SectionAlternateProps) {
  return (
    <section
      className={cn("w-full bg-white py-20 md:py-32", className)}
      {...props}
    >
      <Container size="wide">
        <div className="flex flex-col gap-0">
          {features.map((feature, idx) => (
            <div
              key={idx}
              className={cn(
                "flex flex-col items-center h-[520px]",
                idx % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
              )}
            >
              {/* Image */}
              <div className="basis-0 grow h-full min-h-[311px] relative">
                <img
                  src={feature.image}
                  alt=""
                  className="w-full h-full object-cover"
                />
              </div>

              {/* Content */}
              <div
                className={cn(
                  "basis-0 grow h-full flex flex-col justify-center gap-8 p-8 md:p-12",
                  idx % 2 === 0 ? "border-l border-[#E6E6E6]" : "border-r border-[#E6E6E6]"
                )}
              >
                <div className="flex flex-col gap-3">
                  <div className="opacity-50">
                    <Tag variant="default">{feature.tag}</Tag>
                  </div>

                  <h2 className="text-[#272727] text-2xl md:text-3xl uppercase tracking-wide leading-tight">
                    {feature.title}
                  </h2>
                </div>

                <div className="flex flex-col gap-4">
                  {feature.description.map((paragraph, pIdx) => (
                    <p key={pIdx} className="text-[#272727] text-sm leading-relaxed">
                      {paragraph}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
