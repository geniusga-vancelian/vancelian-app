// i18n-allow-file: showcase /figma uniquement (jamais rendu en prod publique).
// Ce composant est conservé pour le maquettage interne (cf. /figma/page.tsx) ;
// son contenu marketing en EN est inline volontairement et n'est pas pris en
// compte par le garde-fou i18n du site public (siteHardcodedStringsScanner).
// @deprecated Pour un rendu en prod, utiliser SectionHowItWorksCms (CMS).
import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Tag } from "@/components/ui/Tag";

export interface SectionHowItWorksProps extends React.HTMLAttributes<HTMLElement> {}

const steps = [
  {
    step: "Step 1",
    title: "Access the platform",
    description: "Create a secure investor account and complete the required compliance checks.",
    image: "/images/step-1.png",
  },
  {
    step: "Step 2",
    title: "Select an investment",
    description: "Review active and delivered real estate projects, including location, structure and performance data.",
    image: "/images/step-2.png",
  },
  {
    step: "Step 3",
    title: "Subscribe and track",
    description: "Submit your subscription, finalize the transaction and monitor your holdings through a dedicated dashboard.",
    image: "/images/step-3.png",
  },
];

export function SectionHowItWorks({ className, ...props }: SectionHowItWorksProps) {
  return (
    <section
      className={cn("w-full bg-[#272727] py-16 md:py-20", className)}
      {...props}
    >
      <Container>
        <div className="flex flex-col items-center gap-12">
          {/* Section Header */}
          <SectionHeader
            tag="How it works"
            title={
              <>
                A <span className="text-[#C6A47C]">clear</span> and structured investment process.
              </>
            }
          />

          {/* Steps Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0 w-full">
            {steps.map((stepData, idx) => (
              <div key={idx} className="flex flex-col">
                {/* Image */}
                <div className="relative h-[187px] overflow-hidden">
                  <img
                    src={stepData.image}
                    alt={stepData.title}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-b from-transparent from-[57%] to-[#272727]" />
                </div>

                {/* Content */}
                <div className={cn(
                  "flex flex-col gap-5 p-5 md:p-7 flex-1",
                  idx < steps.length - 1 && "border-r border-[#5F5F5F]"
                )}>
                  <div className="opacity-50">
                    <Tag>{stepData.step}</Tag>
                  </div>

                  <h3 className="text-white text-lg uppercase leading-tight">
                    {stepData.title}
                  </h3>

                  <p className="text-[#E6E6E6] text-sm leading-relaxed">
                    {stepData.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}