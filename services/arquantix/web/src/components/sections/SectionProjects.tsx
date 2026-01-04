import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Tag } from "@/components/ui/Tag";
import svgPaths from "@/imports/svg-uawwnp5dcp";

export interface SectionProjectsProps extends React.HTMLAttributes<HTMLElement> {}

export interface ProjectCardProps {
  title: string;
  location: string;
  tags: string[];
  description: string;
  backgroundImage: string;
  className?: string;
}

export function ProjectCard({
  title,
  location,
  tags,
  description,
  backgroundImage,
  className,
}: ProjectCardProps) {
  return (
    <div
      className={cn(
        "relative w-full h-[700px] overflow-hidden bg-[#363636]",
        "flex flex-col justify-between p-7 md:p-8",
        "group cursor-pointer transition-transform hover:scale-[1.02]",
        className
      )}
    >
      {/* Background Image (if needed) */}
      {backgroundImage && (
        <div className="absolute inset-0 z-0 opacity-0">
          <img src={backgroundImage} alt={title} className="w-full h-full object-cover" />
        </div>
      )}

      {/* Decorative Pattern */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-40">
        <svg
          className="absolute bottom-0 right-0 w-[200%] h-[80%]"
          fill="none"
          preserveAspectRatio="none"
          viewBox="0 0 1314.34 255.609"
          style={{ transform: "rotate(296deg)" }}
        >
          <path d={svgPaths.p3d131400} stroke="#C6A47C" strokeMiterlimit="10" />
          <path d={svgPaths.p37eb1c40} stroke="#C6A47C" strokeMiterlimit="10" />
        </svg>
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col gap-2.5">
        <div className="flex gap-1 opacity-50">
          {tags.map((tag, idx) => (
            <Tag key={idx}>{tag}</Tag>
          ))}
        </div>

        <h3 className="text-white text-2xl md:text-[26px] uppercase leading-tight">
          {title}
        </h3>
      </div>

      {/* Location Label (Vertical) */}
      <div className="relative z-10 flex flex-col items-center gap-2.5">
        <div className="flex items-center justify-center h-5 w-2">
          <p className="text-white text-[11px] uppercase whitespace-nowrap origin-center -rotate-90">
            {location}
          </p>
        </div>
        <div className="w-px h-20 bg-white" />
      </div>

      {/* Description + Arrow */}
      <div className="relative z-10 flex items-end gap-6">
        <p className="flex-1 text-[#E6E6E6] text-sm leading-relaxed">
          {description}
        </p>
        <svg 
          className="w-5 h-5 text-white flex-shrink-0 group-hover:translate-x-1 transition-transform" 
          fill="currentColor"
          viewBox="0 0 20 8"
        >
          <path d={svgPaths.p3d2fd000} />
        </svg>
      </div>
    </div>
  );
}

const projects = [
  {
    title: "The Heights Bingin",
    location: "Bali",
    tags: ["7 Villas", "Delivered"],
    description: "Hanc regionem praestitutis celebritati diebus invadere parans dux ante edictus",
    backgroundImage: "/images/project-bingin.jpg",
  },
  {
    title: "The Heights Munduk",
    location: "Bali",
    tags: ["7 Villas", "Delivered"],
    description: "Hanc regionem praestitutis celebritati diebus invadere parans dux ante edictus",
    backgroundImage: "/images/project-munduk.jpg",
  },
  {
    title: "Seminyak Villas",
    location: "Bali",
    tags: ["5 Villas", "In Progress"],
    description: "Luxurious beachfront villas with modern amenities and stunning ocean views",
    backgroundImage: "/images/project-seminyak.jpg",
  },
];

export function SectionProjects({ className, ...props }: SectionProjectsProps) {
  return (
    <section
      className={cn("w-full bg-black py-16 md:py-20", className)}
      {...props}
    >
      <Container>
        <div className="flex flex-col items-center gap-12">
          {/* Section Header */}
          <SectionHeader
            tag="Our Projects"
            title={
              <>
                <span className="text-[#C6A47C]">Delivered</span> real estate investments.
              </>
            }
            description="Explore our portfolio of premium fractional real estate assets across global markets."
          />

          {/* Projects Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
            {projects.map((project, idx) => (
              <ProjectCard key={idx} {...project} />
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}