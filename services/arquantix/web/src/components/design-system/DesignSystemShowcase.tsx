import { Fragment, type ReactNode } from "react";
import { FigmaNavSubmenu } from "@/components/mega-menu/figma/FigmaNavSubmenu";
import type { MegaMenuColumnPayload } from "@/lib/menu/buildMegaMenuColumns";
import { NAV_PRIMARY_LINK_TYPO } from "@/components/design-system/nav-primary-link";
import { cn } from "@/lib/utils";
import FAQ from "./FAQ";
import ProjetGalleryPage from "./ProjetGalleryPage";
import { MarketingBlock } from "./marketing-block";
import HowItWorks from "./HowItWorks";
import { Testimonial } from "./Testimonial";
import { BlockLeftAndRightSection } from "./BlockLeftAndRightSection";
import { ProjetGalleryDemo } from "./ProjetGalleryDemo";
import { ExtractedDesignDemo } from "./extracted";
import { ArticleBodyQuoteBlock } from "./ArticleBodyQuoteBlock";
import { ArticleStepsModule } from "./ArticleStepsModule";
import {
  CategoryPill,
  InThisArticleNav,
  Links,
  Paragraph,
  categoryPillDotPalette,
} from "./extracted";
import {
  figmaDsColors,
  figmaDsFeaturedPostSidebarTitleClassName,
  figmaDsHeavyOblique24ClassName,
  figmaDsTypography,
} from "./extracted/tokens";
import marketingBg from "./imports/ExclusiveOffers/b775f6f8ce6fc689a865af4fdc980d94feb91d0c.png";

/** Demo alignée maquette Figma (module Vault / article CMS). */
const STEPS_MODULE_DEMO: Record<string, unknown> = {
  title: "Phases clés de votre investissement",
  subtitle: "Projet en cours",
  description:
    "Le calendrier typique, de l’ouverture à la sortie, pour vous repérer à chaque étape.",
  rightLabel: "",
  items: [
    {
      title: "Période de souscription",
      date: "Over",
      description: "",
      isCompleted: true,
    },
    {
      title: "Clôture de la période de souscription",
      date: "Over",
      description: "",
      isCompleted: true,
    },
    {
      title: "Versement des intérêts*",
      date: "",
      description:
        "Tous les mois après la date de clôture de la période de souscription.",
      isCompleted: false,
    },
    {
      title: "À partir de 6 mois",
      date: "",
      description:
        "Les frais de sortie anticipée seront de 5 %, que vous choisissiez de quitter partiellement ou totalement le programme.",
      isCompleted: false,
    },
    {
      title: "À partir de 18 mois",
      date: "",
      description:
        "Les frais de sortie anticipée seront sans frais, que vous choisissiez de quitter partiellement ou totalement le programme.",
      isCompleted: false,
    },
  ],
};

const FAQ_SAMPLE = [
  {
    question: "What is fractional real estate?",
    answer:
      "Fractional ownership allows investors to hold a proportional stake in a professionally managed asset, with reporting and governance aligned to institutional standards.",
  },
  {
    question: "How do I start?",
    answer:
      "Create an account, complete verification, and browse active opportunities with full documentation before you invest.",
  },
];

/** Démo page design : même structure que le méga-menu CMS (colonnes + catégories Figma). */
const MEGA_MENU_PRIMARY_DEMO: MegaMenuColumnPayload[] = [
  {
    id: "dm-primary-a",
    category: "Produits d’investissement",
    items: [
      {
        id: "dm-p1",
        title: "Offres exclusives",
        description: "Accédez à des opportunités sélectionnées et documentées.",
        href: "#design-mega-primary",
      },
      {
        id: "dm-p2",
        title: "Vaults",
        description: "Contenus produits et parcours dédiés.",
        href: "#design-mega-primary",
      },
      {
        id: "dm-p3",
        title: "Projets",
        description: "Découvrez les programmes en cours et à venir.",
        href: "#design-mega-primary",
      },
    ],
  },
  {
    id: "dm-primary-b",
    category: "Ressources",
    items: [
      {
        id: "dm-p4",
        title: "Blog",
        description: "Analyses, actualités et guides.",
        href: "#design-mega-primary",
      },
      {
        id: "dm-p5",
        title: "Centre d’aide",
        description: "Questions fréquentes et documentation.",
        href: "#design-mega-primary",
      },
    ],
  },
];

/** Menu secondaire : même module blanc, jeu de contenus plus compact (2 colonnes sans en-têtes de catégorie). */
const MEGA_MENU_SECONDARY_DEMO: MegaMenuColumnPayload[] = [
  {
    id: "dm-sec-a",
    items: [
      {
        id: "dm-s1",
        title: "À propos",
        description: "Mission, équipe et gouvernance.",
        href: "#design-mega-secondary",
      },
      {
        id: "dm-s2",
        title: "Carrières",
        description: "Rejoindre Arquantix.",
        href: "#design-mega-secondary",
      },
    ],
  },
  {
    id: "dm-sec-b",
    items: [
      {
        id: "dm-s3",
        title: "Contact",
        description: "Écrire au service client.",
        href: "#design-mega-secondary",
      },
      {
        id: "dm-s4",
        title: "Mentions légales",
        description: "CGU, confidentialité et réglementation.",
        href: "#design-mega-secondary",
      },
    ],
  },
];

/** Panneau specs Figma (capture « Typography / Paragraph »). */
function FigmaTypographyParagraphSpecPanel() {
  const rows: [string, string][] = [
    ["Category", "Typography"],
    ["Name", "Paragraph"],
    ["Font", "Avenir"],
    ["Weight", "350"],
    ["Style", "Book"],
    ["Size", "14px"],
    ["Vertical trim", "Cap height"],
    ["Line height", "160%"],
    ["Paragraph spacing", "16px"],
    ["Letter spacing", "0%"],
  ];
  return (
    <dl className="mt-4 grid max-w-md grid-cols-[minmax(0,auto)_1fr] gap-x-6 gap-y-2 border-t border-neutral-100 pt-4 text-xs sm:text-sm">
      {rows.map(([k, v]) => (
        <Fragment key={k}>
          <dt className="text-neutral-500">{k}</dt>
          <dd className="font-medium text-neutral-900">{v}</dd>
        </Fragment>
      ))}
    </dl>
  );
}

/** Panneau specs Figma (capture « Typography / Links »). */
function FigmaTypographyLinksSpecPanel() {
  const rows: [string, string][] = [
    ["Category", "Typography"],
    ["Name", "Links"],
    ["Font", "Avenir"],
    ["Weight", "800"],
    ["Style", "Heavy"],
    ["Size", "16px"],
    ["Line height", "100%"],
    ["Letter spacing", "0%"],
  ];
  return (
    <dl className="mt-4 grid max-w-md grid-cols-[minmax(0,auto)_1fr] gap-x-6 gap-y-2 border-t border-neutral-100 pt-4 text-xs sm:text-sm">
      {rows.map(([k, v]) => (
        <Fragment key={k}>
          <dt className="text-neutral-500">{k}</dt>
          <dd className="font-medium text-neutral-900">{v}</dd>
        </Fragment>
      ))}
    </dl>
  );
}

function DesignPrimaryNavMock() {
  return (
    <div
      className="flex min-h-[44px] flex-wrap items-center justify-center gap-[10px] rounded-2xl border border-neutral-200 bg-white px-4 py-2 shadow-sm"
      aria-hidden
    >
      <span
        className={cn(
          "rounded-full bg-black px-3 py-1.5 text-white",
          NAV_PRIMARY_LINK_TYPO,
        )}
      >
        Home
      </span>
      <span
        className={cn(
          "rounded-full px-3 py-1.5 text-[#62656e]",
          NAV_PRIMARY_LINK_TYPO,
        )}
      >
        Projects
      </span>
      <span
        className={cn(
          "rounded-full px-3 py-1.5 text-[#62656e]",
          NAV_PRIMARY_LINK_TYPO,
        )}
      >
        Vaults
      </span>
      <span
        className={cn(
          "rounded-full px-3 py-1.5 text-[#62656e]",
          NAV_PRIMARY_LINK_TYPO,
        )}
      >
        About
      </span>
    </div>
  );
}

function DesignSecondaryNavMock() {
  return (
    <div
      className="flex min-h-[40px] flex-wrap items-center justify-center gap-6 border-b border-neutral-200 bg-white/90 px-4 py-2"
      aria-hidden
    >
      <span className="font-['Avenir:Heavy',sans-serif] text-[13px] text-neutral-900">
        Espace investisseur
      </span>
      <span className="font-['Avenir:Book',sans-serif] text-[13px] text-[#62656e]">
        Documentation
      </span>
      <span className="font-['Avenir:Book',sans-serif] text-[13px] text-[#62656e]">
        API &amp; intégrations
      </span>
      <span className="font-['Avenir:Book',sans-serif] text-[13px] text-[#62656e]">
        Statut des services
      </span>
    </div>
  );
}

const IN_THIS_ARTICLE_DEMO_ITEMS = [
  {
    id: "a1",
    label: "Eu ridiculus fringilla aenean",
    isActive: true,
  },
  {
    id: "a2",
    label: "Faucibus nullam luctus felis pretium donec",
    isActive: false,
  },
  {
    id: "a3",
    label: "Tincidunt veni tellus orci aenean consectetuer",
    isActive: false,
  },
  {
    id: "a4",
    label: "Eu ridiculus fringilla",
    isActive: false,
  },
];

function Section({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      className="border-b border-neutral-200 bg-white py-12"
    >
      <div className="mx-auto max-w-[1320px] px-4">
        <div className="mb-8 max-w-2xl">
          <h2 className="text-lg font-semibold tracking-tight text-neutral-900">
            {title}
          </h2>
          {description ? (
            <p className="mt-1 text-sm text-neutral-600">{description}</p>
          ) : null}
        </div>
        <div className="flex w-full justify-center overflow-x-auto">
          {children}
        </div>
      </div>
    </section>
  );
}

const figmaColorAtoms = Object.entries(figmaDsColors).flatMap(
  ([family, palette]) =>
    Object.entries(palette).map(([name, value]) => ({
      token: `${family}.${name}`,
      value,
    })),
);

export function DesignSystemShowcase() {
  return (
    <div className="min-h-screen bg-neutral-50">
      <Section
        id="nav-mega-primary"
        title="Navigation primaire — méga-menu (module blanc Figma)"
        description="Panneau blanc arrondi, colonnes et items (icône + titre + description). Titres d’entrées : **Links** (`MEGA_MENU_ITEM_TITLE_TYPO`). Libellés de colonne + descriptions d’items : atome **Paragraph** (`Paragraph` / `figmaDsParagraphClassName`, couleur `text.secondary`). Démo statique."
      >
        <div
          id="design-mega-primary"
          className="w-full max-w-[980px] shrink-0 space-y-5 rounded-2xl border border-neutral-200 bg-[#e8eaee] p-8 shadow-inner"
        >
          <DesignPrimaryNavMock />
          <p className="text-center text-xs text-neutral-600">
            En production : ouverture au survol du lien primaire ; ici le panneau est
            affiché en permanence pour la maquette.
          </p>
          <FigmaNavSubmenu columns={MEGA_MENU_PRIMARY_DEMO} />
        </div>
      </Section>

      <Section
        id="nav-mega-secondary"
        title="Navigation secondaire — même module blanc"
        description="Bande de liens secondaires + panneau FigmaNavSubmenu. Titres d’entrées : **Links** ; colonnes + descriptions : **Paragraph** (même règle que la nav primaire)."
      >
        <div
          id="design-mega-secondary"
          className="w-full max-w-[980px] shrink-0 space-y-4 overflow-hidden rounded-2xl border border-neutral-200 bg-neutral-100 shadow-sm"
        >
          <DesignSecondaryNavMock />
          <div className="px-6 pb-8 pt-2">
            <FigmaNavSubmenu columns={MEGA_MENU_SECONDARY_DEMO} />
          </div>
        </div>
      </Section>

      <Section
        id="figma-extracted"
        title="Couche Figma (extracted)"
        description="Atomes, molécules et organismes du zip Design System — distincts des modules marketing existants."
      >
        <div className="w-full max-w-[1200px] shrink-0 overflow-x-auto rounded-lg border border-neutral-200 bg-white shadow-sm">
          <ExtractedDesignDemo />
        </div>
      </Section>

      <Section
        id="color-atoms"
        title="Color atoms"
        description="Nuancier des tokens couleur du DS (nom + valeur hex)."
      >
        <div className="grid w-full max-w-[1200px] shrink-0 grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {figmaColorAtoms.map((item) => (
            <div
              key={item.token}
              className="overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-sm"
            >
              <div
                className="h-20 w-full border-b border-neutral-200"
                style={{ backgroundColor: item.value }}
              />
              <div className="space-y-1 p-4">
                <p className="text-sm font-semibold text-neutral-900">
                  {item.token}
                </p>
                <p className="font-mono text-xs uppercase text-neutral-600">
                  {item.value}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section
        id="typography-atoms"
        title="Typography atoms"
        description="Référence des styles de texte (blog Figma, navigation, méga-menu)."
      >
        <div className="flex w-full max-w-[1200px] shrink-0 flex-col gap-8">
          <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
            <p className="mb-1 text-xs uppercase tracking-[0.08em] text-neutral-500">
              Atome Links (Figma)
            </p>
            <p className="text-xs text-neutral-500">
              Composant <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">Links</code>{" "}
              (
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">
                extracted/atoms/links.tsx
              </code>
              ) — jeton{" "}
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">
                figmaDsLinksClassName
              </code>{" "}
              / objet{" "}
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">
                figmaDsTypography.links
              </code>{" "}
              (
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">
                {JSON.stringify(figmaDsTypography.links)}
              </code>
              ). Nav :{" "}
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">
                NAV_PRIMARY_LINK_TYPO
              </code>{" "}
              · méga-menu :{" "}
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">
                MEGA_MENU_ITEM_TITLE_TYPO
              </code>
              .
            </p>
            <FigmaTypographyLinksSpecPanel />
            <p className="mt-6 max-w-2xl text-xs text-neutral-500">
              Rendu avec le composant <strong>Links</strong> (couleur via prop{" "}
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">color</code> ou classes
              Tailwind) :
            </p>
            <p className="mt-3 max-w-2xl">
              <Links color="#000000">Lien menu top (noir)</Links>
            </p>
            <p className="mt-3 max-w-2xl">
              <Links color="#272727">Titre d’entrée méga-menu (gris foncé panneau)</Links>
            </p>
            <p className="mt-3 max-w-2xl">
              <Links href="#typography-atoms" color="#2563eb" className="underline decoration-2 underline-offset-4">
                Exemple de lien &lt;a&gt; (href + souligné)
              </Links>
            </p>
          </div>

          <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
            <p className="mb-1 text-xs uppercase tracking-[0.08em] text-neutral-500">
              Paragraph (Figma)
            </p>
            <p className="text-xs text-neutral-500">
              Composant <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">Paragraph</code> (
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">
                extracted/atoms/paragraph.tsx
              </code>
              ) — <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">figmaDsParagraphClassName</code>{" "}
              /{" "}
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">
                figmaDsTypography.paragraph
              </code>{" "}
              (
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">
                {JSON.stringify(figmaDsTypography.paragraph)}
              </code>
              ). Méga-menu : libellés de colonne + descriptions sous les titres d’entrées (
              <code className="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">FigmaNavSubmenu</code>
              ).
            </p>
            <FigmaTypographyParagraphSpecPanel />
            <div className="mt-6 max-w-2xl space-y-4">
              <Paragraph color={figmaDsColors.text.primary}>
                Paragraphe corps — texte primaire (ex. article, bloc CMS).
              </Paragraph>
              <Paragraph color={figmaDsColors.text.secondary}>
                Paragraphe secondaire — même atome, couleur <code className="text-[11px]">text.secondary</code> (méga-menu, métadonnées).
              </Paragraph>
            </div>
          </div>

          <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
            <p className="mb-1 text-xs uppercase tracking-[0.08em] text-neutral-500">
              Featured post sidebar title
            </p>
            <p className="text-xs text-neutral-500">
              Avenir Heavy 18px — lh 110 % — tracking −1 %
            </p>
            <p className="mt-4 max-w-2xl text-black">
              <span className={figmaDsFeaturedPostSidebarTitleClassName}>
                Eodem tempore Serenianus ex duce, cuius ignavia populatam...
              </span>
            </p>
          </div>

          <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
            <p className="mb-1 text-xs uppercase tracking-[0.08em] text-neutral-500">
              Citation (bold + italic)
            </p>
            <p className="text-xs text-neutral-500">
              Avenir Heavy — 24px — weight 800 — bold + italic — lh 110 % — tracking −1 %
            </p>
            <p className="mt-4 max-w-2xl text-black">
              <span className={figmaDsHeavyOblique24ClassName}>
                Citation d’exemple : l’atome sert le corps de texte du module Quote.
              </span>
            </p>
          </div>

          <div className="w-full max-w-[720px] shrink-0 rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
            <p className="mb-1 text-xs uppercase tracking-[0.08em] text-neutral-500">
              Module Quote (citation)
            </p>
            <p className="text-xs text-neutral-500">
              Corps = Heavy 800 + italique (24px) ; auteur = Book 14px (gris, italique)
            </p>
            <div className="mt-6 text-left">
              <ArticleBodyQuoteBlock
                quote="L’infrastructure de conformité est le socle d’une confiance durable entre investisseurs et émetteurs."
                author="Conseil de lecture, 2024"
              />
            </div>
          </div>
        </div>
      </Section>

      <Section
        id="category-pill"
        title="Pill catégorie (tag article)"
        description="Point coloré 7px + atome Label (Avenir Black 900, 10px, lh 100 %, uppercase, noir). Conteneur : padding 10px, radius 8px, fond blanc, sans bordure, gap 6px. Entre pills : gap 8px (parent). Tokens : figmaDsCategoryPillContainerClassName, figmaDsLabelClassName."
      >
        <div className="w-full max-w-[720px] shrink-0 space-y-6">
          <div className="rounded-lg border border-neutral-200 bg-[#f3f3f3] p-8 shadow-sm">
            <p className="mb-4 text-xs text-neutral-600">
              Fond gris type hero article — même contexte que la page blog.
            </p>
            <div className="flex flex-wrap gap-2">
              <CategoryPill label="Category" dotClassName="bg-[#c4a574]" />
              <CategoryPill label="Crypto" dotClassName={categoryPillDotPalette[0]} />
              <CategoryPill label="Analysis" dotClassName={categoryPillDotPalette[2]} />
              <CategoryPill label="Segment éditorial" />
            </div>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
            <p className="mb-4 text-xs text-neutral-600">Fond blanc (contrôle).</p>
            <div className="flex flex-wrap gap-2">
              <CategoryPill label="Market news" dotClassName={categoryPillDotPalette[1]} />
              <CategoryPill label="Company news" dotClassName={categoryPillDotPalette[3]} />
            </div>
          </div>
        </div>
      </Section>

      <Section
        id="article-left-nav"
        title="Module gauche article (In this article)"
        description="Specs Figma: border radius 10, fond neutral.gray100, padding interne 40."
      >
        <div className="w-full max-w-[720px] shrink-0 rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
          <InThisArticleNav title="In this article" items={IN_THIS_ARTICLE_DEMO_ITEMS} />
        </div>
      </Section>

      <Section
        id="steps-module"
        title="Steps module (timeline)"
        description="Titre de module, surtitre et description centrés au-dessus ; encart gris = timeline seule (fond #f0f0f0, 32px entre étapes, ligne pointillée, titres Paragraph Large Bold, tag EN COURS)."
      >
        <div className="w-full max-w-[560px] shrink-0">
          <ArticleStepsModule content={STEPS_MODULE_DEMO} />
        </div>
      </Section>

      <Section
        id="marketing-block"
        title="Marketing block"
        description="Variantes gradient et image (extraits Figma)."
      >
        <div className="flex w-[1152px] max-w-full shrink-0 flex-col gap-10">
          <MarketingBlock
            variant="gradient"
            title={
              "Access fractional real estate with\ninstitutional confidence."
            }
            buttonText="Enter the investment platform"
          />
          <MarketingBlock
            variant="image"
            title="Build a portfolio aligned with your objectives."
            subtitle="Curated opportunities, transparent structures, disciplined execution."
            buttonText="Explore opportunities"
            backgroundImage={marketingBg.src}
          />
        </div>
      </Section>

      <Section
        id="how-it-works"
        title="How it works"
        description="Parcours investisseur en trois étapes."
      >
        <div className="w-full shrink-0">
          {/* Showcase design-system (/design) : on passe explicitement le surtitre
              de démo. En prod, ce composant est piloté par le CMS via
              `SectionHowItWorksCms` (module `how_it_works`) et n'a AUCUN
              fallback hardcodé sur `label` — voir HowItWorks.tsx. */}
          <HowItWorks label="How it works" />
        </div>
      </Section>

      <Section
        id="block-left-right"
        title="Bloc gauche / droite"
        description="Texte, image et checklist."
      >
        <div className="w-[1152px] max-w-full shrink-0">
          <BlockLeftAndRightSection />
        </div>
      </Section>

      <Section
        id="projet-gallery"
        title="Projet gallery"
        description="Onglets et cartes projet (module)."
      >
        <div className="w-full shrink-0">
          <ProjetGalleryDemo />
        </div>
      </Section>

      <Section
        id="testimonial"
        title="Testimonial"
        description="Carte témoignage avec notation."
      >
        <div className="w-[378px] max-w-full shrink-0">
          <Testimonial
            authorName="Alexandre Martin"
            authorTitle="Family office, Paris"
            authorImage="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=96&h=96&fit=crop"
            rating={5}
            testimonialText="The level of documentation and clarity on each opportunity matches what we expect from institutional partners."
          />
        </div>
      </Section>

      <Section
        id="faq"
        title="FAQ"
        description="Accordéon questions / réponses."
      >
        <div className="w-full shrink-0">
          <FAQ items={FAQ_SAMPLE} headline="Questions Fréquentes." />
        </div>
      </Section>

      <Section
        id="page-projets"
        title="Page « Tous les projets »"
        description="Composition pleine page extraite de Figma."
      >
        <div className="w-full shrink-0 overflow-hidden rounded-lg border border-neutral-200 shadow-sm">
          <ProjetGalleryPage />
        </div>
      </Section>
    </div>
  );
}
