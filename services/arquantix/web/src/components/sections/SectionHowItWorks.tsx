// i18n-allow-file: showcase /figma uniquement (jamais rendu en prod publique).
// Ce composant est conservé pour le maquettage interne (cf. /figma/page.tsx) ;
// son contenu marketing en EN est inline volontairement et n'est pas pris en
// compte par le garde-fou i18n du site public (siteHardcodedStringsScanner).
// @deprecated Pour un rendu en prod, utiliser SectionHowItWorksCms (CMS).
import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import HowItWorks from "@/components/design-system/HowItWorks";

export interface SectionHowItWorksProps extends React.HTMLAttributes<HTMLElement> {}

export function SectionHowItWorks({ className, ...props }: SectionHowItWorksProps) {
  return (
    <section className={cn("w-full bg-v-bg", className)} {...props}>
      <Container>
        <HowItWorks
          label="How it works"
          title={"A clear and structured\ninvestment process."}
          subtitle="Three steps, full transparency, institutional governance."
          steps={[
            {
              number: "01",
              title: "Access the platform",
              description:
                "Create a secure investor account and complete the required compliance checks.",
              imageMediaUrl: "/images/step-1.png",
            },
            {
              number: "02",
              title: "Select an investment",
              description:
                "Review active and delivered real estate projects, including location, structure and performance data.",
              imageMediaUrl: "/images/step-2.png",
            },
            {
              number: "03",
              title: "Subscribe and track",
              description:
                "Submit your subscription, finalize the transaction and monitor your holdings through a dedicated dashboard.",
              imageMediaUrl: "/images/step-3.png",
            },
          ]}
          surface="light"
        />
      </Container>
    </section>
  );
}
