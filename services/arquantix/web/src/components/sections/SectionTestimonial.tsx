import * as React from "react";
import { cn } from "@/lib/utils";
import { Tag } from "@/components/ui/Tag";

export interface SectionTestimonialProps extends React.HTMLAttributes<HTMLElement> {
  tag?: string;
  quote?: string;
  author?: string;
  role?: string;
  backgroundImage?: string;
}

export function SectionTestimonial({ 
  tag = "Citation",
  quote = "\"L'architecture est un fait d'art, un phénomène qui suscite l'émotion, au-delà des problèmes de construction. La construction sert à faire tenir, l'architecture à émouvoir.\"",
  author = "Le Corbusier",
  role = "Architecte",
  backgroundImage,
  className,
  ...props 
}: SectionTestimonialProps) {
  return (
    <section
      className={cn("relative w-full h-[680px] overflow-hidden", className)}
      {...props}
    >
      {/* Background Image + Dark Overlay */}
      <div className="absolute inset-0 z-0">
        <img
          src={backgroundImage || "/images/testimonial-background.png"}
          alt=""
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-black/80" />
      </div>

      {/* Content */}
      <div className="relative z-10 flex items-center justify-center h-full px-16 py-16">
        <figure className="max-w-4xl">
          <div className="flex flex-col gap-10 items-start w-full">
            {/* Tag */}
            <div className="opacity-50">
              <Tag>{tag}</Tag>
            </div>

            {/* Quote */}
            <blockquote className="text-white text-3xl md:text-4xl uppercase tracking-wider leading-tight">
              {quote}
            </blockquote>

            {/* Author */}
            <figcaption className="flex flex-col gap-1">
              <cite className="text-[#C6A47C] text-lg not-italic uppercase">
                {author}
              </cite>
              {role && (
                <p className="text-[#E6E6E6] text-sm">
                  {role}
                </p>
              )}
            </figcaption>
          </div>
        </figure>
      </div>
    </section>
  );
}
