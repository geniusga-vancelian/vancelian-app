'use client'

import { SectionHero } from "@/components/sections/SectionHero";
import { SectionAbout } from "@/components/sections/SectionAbout";
import { SectionHowItWorks } from "@/components/sections/SectionHowItWorks";
import { SectionProjects } from "@/components/sections/SectionProjects";
import { SectionAlternate } from "@/components/sections/SectionAlternate";
import { SectionTestimonial } from "@/components/sections/SectionTestimonial";
import { SectionCTA } from "@/components/sections/SectionCTA";
export default function FigmaPage() {
  const buildSha = process.env.NEXT_PUBLIC_GIT_SHA
  const buildShaShort = buildSha ? buildSha.substring(0, 7) : 'unknown'

  return (
    <div className="min-h-screen bg-black text-white">
      <main>
        <SectionHero />
        <SectionAbout />
        <SectionHowItWorks />
        <SectionProjects />
        <SectionAlternate />
        <SectionTestimonial />
        <SectionCTA />
      </main>
      {buildSha && (
        <div className="fixed bottom-4 right-4 bg-black/60 backdrop-blur-sm border border-white/10 rounded px-2 py-1 text-xs text-white/60 font-mono">
          build: {buildShaShort}
        </div>
      )}
    </div>
  );
}
