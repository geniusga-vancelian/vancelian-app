import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Tag } from "@/components/ui/Tag";
import svgPaths from "@/imports/svg-uawwnp5dcp";

export interface ProjectShrink {
  id: string;
  slug: string;
  title: string;
  location: string | null;
  shortDescription: string | null;
  coverUrl: string | null;
  coverAlt: string | null;
}

export interface SectionProjectsProps extends React.HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  // Legacy: hardcoded items
  items?: Array<{
    title: string;
    location?: string;
    tags?: string[];
    description?: string;
    mediaId?: string;
    mediaUrl?: string;
    backgroundImage?: string;
  }>;
  // New: resolved projects from DB
  resolvedProjects?: ProjectShrink[];
}

export interface ProjectCardProps {
  title: string;
  location?: string;
  tags?: string[];
  description?: string;
  backgroundImage?: string;
  className?: string;
  slug?: string; // For linking to project detail page
}

export function ProjectCard({
  title,
  location,
  tags,
  description,
  backgroundImage,
  className,
  slug,
}: ProjectCardProps) {
  const cardContent = (
    <div
      className={cn(
        "relative w-full h-[700px] overflow-hidden bg-[#363636]",
        "flex flex-col justify-between p-7 md:p-8",
        "group transition-transform hover:scale-[1.02]",
        slug ? "cursor-pointer" : "",
        className
      )}
    >
      {/* Cover Image with Overlay */}
      {backgroundImage && (
        <div className="absolute inset-0 z-0">
          <img 
            src={backgroundImage} 
            alt={title} 
            className="w-full h-full object-cover"
          />
          {/* Overlay for text readability */}
          <div 
            className="absolute inset-0"
            style={{ 
              backgroundColor: 'rgba(0, 0, 0, 0.25)',
            }}
          />
        </div>
      )}

      {/* Decorative Pattern */}
      <div className="absolute inset-0 z-[2] pointer-events-none opacity-40">
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

      {/* Content - Top */}
      <div className="relative z-10 flex flex-col gap-2.5">
        {tags && tags.length > 0 && (
          <div className="flex gap-1 opacity-50">
            {tags.map((tag, idx) => (
              <Tag key={idx}>{tag}</Tag>
            ))}
          </div>
        )}

        <h3 className="text-white text-2xl md:text-[26px] uppercase leading-tight">
          {title}
        </h3>
      </div>

      {/* Location Label (Vertical) - Vertically centered, horizontally aligned with description padding */}
      {location && (
        <div className="absolute left-7 md:left-8 top-1/2 -translate-y-1/2 z-10 flex flex-col items-start gap-2.5">
          <div className="flex items-center justify-center h-5 w-2">
            <p className="text-white text-[11px] uppercase whitespace-nowrap origin-center -rotate-90">
              {location}
            </p>
          </div>
          <div className="w-px h-20 bg-white" />
        </div>
      )}

      {/* Description + Arrow - Bottom */}
      {description && (
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
      )}
    </div>
  );

  // Wrap in Link if slug is provided
  if (slug) {
    return (
      <Link href={`/projects/${slug}`} className="block" style={{ position: 'relative' }}>
        {cardContent}
      </Link>
    );
  }

  return cardContent;
}

export function SectionProjects({ 
  title, 
  description, 
  items = [],
  resolvedProjects,
  className, 
  ...props 
}: SectionProjectsProps) {
  // Priority: resolvedProjects (from DB) > items (legacy)
  let projectsToRender: Array<{
    title: string;
    location?: string;
    tags?: string[];
    description?: string;
    backgroundImage?: string;
    slug?: string;
  }> = [];

  if (resolvedProjects && resolvedProjects.length > 0) {
    // Convert resolvedProjects to ProjectCard format
    projectsToRender = resolvedProjects.map((p) => ({
      title: p.title,
      location: p.location || undefined,
      tags: [],
      description: p.shortDescription || '',
      backgroundImage: p.coverUrl || undefined,
      slug: p.slug,
    }));
  } else if (items.length > 0) {
    projectsToRender = items;
  }

  return (
    <section
      className={cn("w-full bg-black py-16 md:py-20", className)}
      {...props}
    >
      <Container>
        <div className="flex flex-col items-center gap-12">
          {/* Section Header */}
          {title && (
            <SectionHeader
              tag={title}
              title={title}
              description={description}
            />
          )}

          {/* Projects Grid */}
          {projectsToRender.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
              {projectsToRender.map((project, idx) => (
                <ProjectCard 
                  key={project.slug || idx} 
                  title={project.title}
                  location={project.location}
                  tags={project.tags}
                  description={project.description}
                  backgroundImage={project.backgroundImage}
                  slug={project.slug}
                />
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-center">No projects available.</p>
          )}
        </div>
      </Container>
    </section>
  );
}