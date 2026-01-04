import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { Button } from "@/components/ui/button";

export interface SectionCTAProps extends React.HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  primaryButtonText?: string;
  primaryButtonHref?: string;
  secondaryButtonText?: string;
  secondaryButtonHref?: string;
}

export function SectionCTA({ 
  title = "Ready to invest in fractional real estate?",
  description = "Join institutional investors accessing premium real estate opportunities through our regulated platform.",
  primaryButtonText = "Get Started",
  primaryButtonHref = "https://wa.me/6281353009603?text=Hello,%20I'm%20interested%20in%20Arquantix",
  secondaryButtonText = "Learn More",
  secondaryButtonHref = "#about",
  className,
  ...props 
}: SectionCTAProps) {
  return (
    <section
      className={cn("w-full bg-gradient-to-b from-[#1A1A1A] to-black py-20 md:py-28", className)}
      {...props}
    >
      <Container>
        <div className="flex flex-col items-center gap-8 text-center max-w-3xl mx-auto">
          <h2 className="text-white text-3xl md:text-4xl uppercase tracking-wide leading-tight">
            {title}
          </h2>

          <p className="text-[#E6E6E6] text-base md:text-lg leading-relaxed">
            {description}
          </p>

          <div className="flex flex-col sm:flex-row gap-4 mt-4">
            {primaryButtonText && (
              <Button variant="arquantix" size="arquantix" asChild>
                <a href={primaryButtonHref}>
                  {primaryButtonText}
                </a>
              </Button>
            )}
            
            {secondaryButtonText && (
              <Button variant="arquantixOutline" size="arquantix" asChild>
                <a href={secondaryButtonHref}>
                  {secondaryButtonText}
                </a>
              </Button>
            )}
          </div>
        </div>
      </Container>
    </section>
  );
}
