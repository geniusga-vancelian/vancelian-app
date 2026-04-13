import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Button } from "@/components/ui/button";

export interface SectionAboutProps extends React.HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  items?: Array<{
    title: string;
    description: string;
  }>;
  imageUrl?: string;
  content?: string;
  ctaText?: string;
  ctaLink?: string;
}

export function SectionAbout({ 
  title, 
  description,
  items = [],
  imageUrl,
  content,
  ctaText,
  ctaLink,
  className, 
  ...props 
}: SectionAboutProps) {
  return (
    <section
      className={cn("w-full bg-[#1A1A1A] py-16 md:py-20", className)}
      {...props}
    >
      <Container>
        <div className="flex flex-col items-center gap-10">
          {/* Section Header */}
          {title && (
            <SectionHeader
              tag={title}
              title={title}
              description={description}
            />
          )}

          {/* Content Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0 w-full">
            {/* Left - Image */}
            {imageUrl && (
              <div className="relative h-[311px] overflow-hidden">
                <img
                  src={imageUrl}
                  alt={title || "About"}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/30" />
              </div>
            )}

            {/* Middle - Description */}
            {content && (
              <div className="border-x border-[#5F5F5F] p-7 md:p-8 flex flex-col justify-center bg-[#0D0D0D]">
                <div className="space-y-4 text-[#E6E6E6] text-sm leading-relaxed whitespace-pre-line">
                  {content}
                </div>
              </div>
            )}

            {/* Right - Features */}
            {items.length > 0 && (
              <div className="p-7 md:p-8 flex flex-col justify-center gap-14 bg-[#0D0D0D]">
                {items.map((item, idx) => (
                  <div key={idx} className="flex flex-col gap-5">
                    <h3 className="text-white text-lg uppercase">
                      {item.title}
                    </h3>
                    <p className="text-[#E6E6E6] text-sm leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* CTA Button */}
          {ctaText && (
            <Button variant="arquantixOutline" size="arquantix" asChild={!!ctaLink}>
              {ctaLink ? <a href={ctaLink}>{ctaText}</a> : ctaText}
            </Button>
          )}
        </div>
      </Container>
    </section>
  );
}