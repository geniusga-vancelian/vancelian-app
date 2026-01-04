'use client'

import { Navigation } from "@/components/sections/Navigation";
import { SectionHero } from "@/components/sections/SectionHero";
import { SectionAbout } from "@/components/sections/SectionAbout";
import { SectionHowItWorks } from "@/components/sections/SectionHowItWorks";
import { SectionProjects } from "@/components/sections/SectionProjects";
import { SectionAlternate } from "@/components/sections/SectionAlternate";
import { SectionTestimonial } from "@/components/sections/SectionTestimonial";
import { SectionCTA } from "@/components/sections/SectionCTA";
import { Footer } from "@/components/sections/Footer";

export default function FigmaPage() {
  return (
    <div className="min-h-screen bg-black text-white">
      <Navigation />
      <main>
        <SectionHero />
        <SectionAbout />
        <SectionHowItWorks />
        <SectionProjects />
        <SectionAlternate />
        <SectionTestimonial />
        <SectionCTA />
      </main>
      <Footer />
    </div>
  );
}
