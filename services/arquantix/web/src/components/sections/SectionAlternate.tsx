// i18n-allow-file: showcase /figma uniquement (jamais rendu en prod publique).
// Ce composant est conservé pour le maquettage interne (cf. /figma/page.tsx) ;
// son contenu marketing en EN est inline volontairement et n'est pas pris en
// compte par le garde-fou i18n du site public (siteHardcodedStringsScanner).
// @deprecated Pour un rendu en prod, utiliser une section CMS (Page + Section).
import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import {
  VEyebrow,
  VEditorialTitle,
} from "@/components/design-system/vancelian";

export interface SectionAlternateProps extends React.HTMLAttributes<HTMLElement> {}

/**
 * Bloc « About » alternate — pattern Vancelian éditorial split image/texte.
 *
 * Spec DS : voir doctrine pack handoff §«editorial scale» et patterns
 * `journey` / `product-card` pour la balance image/texte. Image full-bleed
 * dans sa moitié (border-radius 8px côté contenu), texte aligné gauche avec
 * eyebrow + titre éditorial (italic Newsreader sur un mot-clé) + chapô.
 *
 * Alternance pair/impair pour rythmer la page (image gauche / image droite).
 */
const features = [
  {
    tag: "About us",
    title: (
      <>
        Built on <em>real</em> assets. Delivered.
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
        Institutional <em>governance</em>. Real assets.
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
      className={cn("w-full bg-v-bg py-24 lg:py-32", className)}
      {...props}
    >
      <Container size="wide">
        <div className="flex flex-col gap-20 lg:gap-28">
          {features.map((feature, idx) => (
            <div
              key={idx}
              className={cn(
                "flex flex-col items-center gap-10 lg:gap-16",
                idx % 2 === 0 ? "lg:flex-row" : "lg:flex-row-reverse",
              )}
            >
              <div className="basis-0 grow w-full overflow-hidden rounded-v-card">
                {/* eslint-disable-next-line @next/next/no-img-element -- showcase asset statique */}
                <img
                  src={feature.image}
                  alt=""
                  className="block aspect-[4/3] w-full object-cover"
                />
              </div>

              <div className="basis-0 grow w-full flex flex-col justify-center gap-6 lg:max-w-[480px]">
                <VEyebrow>{feature.tag}</VEyebrow>
                <VEditorialTitle as="h2" size="module" align="left">
                  {feature.title}
                </VEditorialTitle>

                <div className="flex flex-col gap-4">
                  {feature.description.map((paragraph, pIdx) => (
                    <p
                      key={pIdx}
                      className="m-0 font-ui font-normal text-[15px] leading-[1.6] text-v-fg-body"
                    >
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
