import { flushSync } from 'react-dom';
import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  TitleSlide,
  TwoColumnSlide,
  InfrastructureSlide,
  RoadmapSlide,
  TeamSlide,
  MetricsSlide,
  FeatureGridSlide,
  TimelineSlide,
  ComparisonSlide,
  CenteredContentSlide,
  TeamSpotlightSlide,
  ThreeKeyElementsSlide,
  WhyNowQuadSlide,
  ChecklistPanelSlide,
  CompanyOrgChartSlide,
  StaffOrgChartSlide,
  AdvancedStaffOrgChartSlide,
  OfferingSplitSlide,
} from '../components/slide-templates';
import { advancedStaffOrgChartDemo } from '../components/slide-templates/advancedStaffOrgChartDemo';
import { Heading1, BodyLarge } from '../components/design-system/Typography';
import {
  exportSlideElementToPdf,
  renderSlideElementToCanvas,
  SLIDE_PDF_HEIGHT,
  SLIDE_PDF_WIDTH,
} from './exportSlideToPdf';
type SlideType =
  | 'title'
  | 'two-column'
  | 'infrastructure'
  | 'roadmap'
  | 'team'
  | 'metrics'
  | 'feature-grid'
  | 'timeline'
  | 'comparison'
  | 'centered'
  | 'team-spotlight'
  | 'three-key-elements'
  | 'why-now-quad'
  | 'checklist-panel'
  | 'org-company'
  | 'org-staff'
  | 'org-staff-advanced'
  | 'offering-split';

interface SlideTemplate {
  id: SlideType;
  name: string;
  description: string;
  useCase: string;
}

const slideTemplates: SlideTemplate[] = [
  {
    id: 'title',
    name: 'Title Slide',
    description: 'Slide de couverture avec grand titre et arrière-plan',
    useCase: 'Idéal pour : couverture de présentation, ruptures de section',
  },
  {
    id: 'two-column',
    name: 'Two Column Slide',
    description: 'Texte à gauche, contenu visuel à droite',
    useCase: 'Idéal pour : contexte, vision, problématique',
  },
  {
    id: 'infrastructure',
    name: 'Infrastructure / Stack',
    description: 'Stack technologique avec cartes empilées',
    useCase: 'Idéal pour : architecture, stack, solutions',
  },
  {
    id: 'roadmap',
    name: 'Roadmap Slide',
    description: 'Timeline verticale avec phases et jalons',
    useCase: 'Idéal pour : planning, roadmap produit, milestones',
  },
  {
    id: 'team',
    name: 'Team Slide',
    description: "Grille de membres d'équipe avec bios",
    useCase: 'Idéal pour : équipe, advisors, partenaires',
  },
  {
    id: 'metrics',
    name: 'Metrics / KPIs',
    description: 'Grille de métriques et KPIs',
    useCase: 'Idéal pour : traction, KPIs, résultats',
  },
  {
    id: 'feature-grid',
    name: 'Feature Grid',
    description: 'Grille de fonctionnalités avec icônes',
    useCase: 'Idéal pour : features produit, avantages, services',
  },
  {
    id: 'timeline',
    name: 'Timeline horizontale',
    description: "Timeline horizontale avec événements clés",
    useCase: 'Idéal pour : histoire, évolution, milestones historiques',
  },
  {
    id: 'comparison',
    name: 'Comparison Slide',
    description: 'Comparaison en colonnes (avant/après, offres…)',
    useCase: 'Idéal pour : pricing, comparaisons, différenciateurs',
  },
  {
    id: 'centered',
    name: 'Centered Content',
    description: 'Contenu centré avec split gauche / droite',
    useCase: 'Idéal pour : vision & mission, déclaration principale',
  },
  {
    id: 'team-spotlight',
    name: 'Team Spotlight (portrait)',
    description:
      'Portrait pleine hauteur à gauche, titre et bio sur toute la largeur restante, séparateur sable',
    useCase: 'Idéal pour : présenter une personne clé sans comprimer le texte',
  },
  {
    id: 'three-key-elements',
    name: '3 Key-elements',
    description:
      'N piliers sur grille type Team (disque 160px, titres, ligne indigo optionnelle, BodyLarge), bande conclusion',
    useCase: 'Idéal pour : synthèse en N points, messages clés, closing',
  },
  {
    id: 'why-now-quad',
    name: 'Pourquoi maintenant — quad 2×2',
    description:
      'Même typo / disques 160px / picto que 3 Key-elements, grille 2×2, bande conclusion — sans Confidential',
    useCase: 'Idéal pour : narrative timing, quatre arguments symétriques, closing produit / app',
  },
  {
    id: 'checklist-panel',
    name: 'Liste encadrée (checks)',
    description:
      'SlideHeader + flèche + sous-titre, panneau gris arrondi, par ligne : check + titre + corps (typo 3 Key-elements), espacement vertical large',
    useCase: 'Idéal pour : prerequis, critères d’éligibilité, étapes validées, conformité',
  },
  {
    id: 'org-company',
    name: 'Organigramme société',
    description: 'Arbre d’entités juridiques (holding, filiales, SPV) avec connecteurs indigo',
    useCase: 'Idéal pour : groupe, gouvernance des sociétés, périmètre légal',
  },
  {
    id: 'org-staff',
    name: 'Organigramme équipe',
    description: 'Hiérarchie collaborateurs : photo / initiales, rôle indigo, sous-équipes',
    useCase: 'Idéal pour : direction, organigramme RH, reporting lines',
  },
  {
    id: 'org-staff-advanced',
    name: 'Organigramme équipe (avancé)',
    description:
      'Board / direction / comité opérationnel + départements en colonnes colorées (palette Flutter)',
    useCase: 'Idéal pour : organigramme complet, gouvernance + effectifs par dept',
  },
  {
    id: 'offering-split',
    name: 'Offering — split + iPhone',
    description:
      'Split 60/40, iPhone centré sur la jonction, capture app Vancelian (public/offering-iphone-app-screenshot.png), stats à droite',
    useCase: 'Idéal pour : offre RWA / produit, mockup app, métadonnées sur fond image',
  },
];

const COMPONENT_IMPORT_NAME: Record<SlideType, string> = {
  title: 'TitleSlide',
  'two-column': 'TwoColumnSlide',
  infrastructure: 'InfrastructureSlide',
  roadmap: 'RoadmapSlide',
  team: 'TeamSlide',
  metrics: 'MetricsSlide',
  'feature-grid': 'FeatureGridSlide',
  timeline: 'TimelineSlide',
  comparison: 'ComparisonSlide',
  centered: 'CenteredContentSlide',
  'team-spotlight': 'TeamSpotlightSlide',
  'three-key-elements': 'ThreeKeyElementsSlide',
  'why-now-quad': 'WhyNowQuadSlide',
  'checklist-panel': 'ChecklistPanelSlide',
  'org-company': 'CompanyOrgChartSlide',
  'org-staff': 'StaffOrgChartSlide',
  'org-staff-advanced': 'AdvancedStaffOrgChartSlide',
  'offering-split': 'OfferingSplitSlide',
};

export function SlideTemplatesGallery() {
  const [selectedSlide, setSelectedSlide] = useState<SlideType>('title');
  const [pdfExporting, setPdfExporting] = useState(false);
  /** Slide 1920×1080 hors `transform: scale` — html2canvas se trompe sinon (décalage / crop). Voir RegistrationDeck. */
  const pdfCaptureRef = useRef<HTMLDivElement>(null);

  const waitPaint = () =>
    new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));

  const handleExportCurrentSlidePdf = async () => {
    flushSync(() => {
      setPdfExporting(true);
    });
    try {
      await waitPaint();
      await new Promise((r) => setTimeout(r, 220));
      const wrapper = pdfCaptureRef.current;
      const root = wrapper?.firstElementChild as HTMLElement | null;
      if (!root) return;
      await exportSlideElementToPdf(root, `vancelian-slide-${selectedSlide}.pdf`);
    } catch (err) {
      console.error(err);
      alert(
        "L'export PDF a échoué (images externes, police ou mémoire). Ouvrez la console pour le détail.",
      );
    } finally {
      setPdfExporting(false);
    }
  };

  const handleExportCatalogPdf = async () => {
    const previous = selectedSlide;
    flushSync(() => {
      setPdfExporting(true);
    });
    try {
      const { jsPDF } = await import('jspdf');
      if (typeof document !== 'undefined' && document.fonts?.ready) {
        await document.fonts.ready;
      }
      await waitPaint();
      await new Promise((r) => setTimeout(r, 200));
      const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'px',
        format: [SLIDE_PDF_WIDTH, SLIDE_PDF_HEIGHT],
        compress: true,
      });
      for (let i = 0; i < slideTemplates.length; i++) {
        flushSync(() => {
          setSelectedSlide(slideTemplates[i].id);
        });
        await new Promise((r) => setTimeout(r, 280));
        const root = pdfCaptureRef.current?.firstElementChild as HTMLElement | null;
        if (!root) continue;
        const canvas = await renderSlideElementToCanvas(root, { settleMs: 120 });
        const imgData = canvas.toDataURL('image/jpeg', 0.92);
        if (i > 0) {
          pdf.addPage([SLIDE_PDF_WIDTH, SLIDE_PDF_HEIGHT], 'landscape');
        }
        pdf.addImage(imgData, 'JPEG', 0, 0, SLIDE_PDF_WIDTH, SLIDE_PDF_HEIGHT);
      }
      pdf.save('vancelian-catalogue-templates.pdf');
    } catch (err) {
      console.error(err);
      alert(
        "L'export du catalogue PDF a échoué. Vérifiez la console (images CORS, mémoire).",
      );
    } finally {
      flushSync(() => {
        setSelectedSlide(previous);
      });
      setPdfExporting(false);
    }
  };

  const renderSlide = () => {
    switch (selectedSlide) {
      case 'title':
        return (
          <TitleSlide
            label="Pitch Deck"
            title={`Redefining\nWealth Management for next-gen investors.`}
            subtitle="Un nouveau cycle structurel dans la finance"
          />
        );

      case 'two-column':
        return (
          <TwoColumnSlide
            label="Vancelian"
            title="Context"
            sections={[
              {
                title: 'AI is the new norm',
                content: (
                  <>
                    Fintech democratized access to markets and crypto → mission accomplished.
                    <br />
                    As AI reshapes how people search, decide, interact and live, financial advisory
                    must shift to AI-driven guidance.
                  </>
                ),
              },
              {
                title: 'Performance is Under Pressure',
                content: (
                  <>
                    Purchasing power is eroding. Markets are ultra-efficient. Alpha is compressed.
                    <br />
                    Investors are searching for new options of return, private markets and
                    alternative yield.
                  </>
                ),
              },
            ]}
            quote={{
              text: 'We are entering a new structural cycle in finance as technology accelerates and user expectations evolve.',
              attribution: 'Gael Itier',
              role: 'Founder & CEO, Vancelian Group',
            }}
            rightContent={
              <div className="p-[60px] text-center">
                <Heading1>Visual Content</Heading1>
                <BodyLarge className="mt-4">Image ou graphique ici</BodyLarge>
              </div>
            }
          />
        );

      case 'infrastructure':
        return (
          <InfrastructureSlide
            label="Vancelian APP"
            title="Infrastructure"
            subtitle="De la tokenisation d'actif du monde réel à une expérience IA générative"
            features={[
              {
                type: 'single',
                title: 'La nouvelle norme AI incontournable',
                description: 'AI',
                variant: 'white',
              },
              {
                type: 'stacked',
                title: 'Infrastructure Neobanking et Fintechs',
                description: ['Payment - Core banking', 'Investment engine'],
                variant: 'light',
              },
              {
                type: 'single',
                title: 'Our Unique Selling Proposal',
                description: 'RWA',
                variant: 'medium',
              },
            ]}
          />
        );

      case 'roadmap':
        return (
          <RoadmapSlide
            label="Product"
            title="Roadmap"
            subtitle="Notre feuille de route pour les 18 prochains mois"
            roadmapItems={[
              {
                phase: 'Phase 1',
                quarter: 'Q1 2024',
                title: 'Foundation & MVP',
                status: 'completed',
                items: [
                  'Infrastructure de base',
                  'Onboarding utilisateurs',
                  'Intégration API bancaires',
                  'Dashboard analytics',
                ],
              },
              {
                phase: 'Phase 2',
                quarter: 'Q2 2024',
                title: 'AI Integration',
                status: 'in-progress',
                items: [
                  'Assistant IA conversationnel',
                  'Recommandations personnalisées',
                  'Portfolio optimization',
                  'Risk assessment AI',
                ],
              },
              {
                phase: 'Phase 3',
                quarter: 'Q3 2024',
                title: 'RWA Platform',
                status: 'planned',
                items: [
                  'Tokenization framework',
                  'Real estate tokens',
                  'Commodities integration',
                  'Secondary market',
                ],
              },
              {
                phase: 'Phase 4',
                quarter: 'Q4 2024',
                title: 'Scale & Expand',
                status: 'planned',
                items: [
                  'European expansion',
                  'Mobile app launch',
                  'API pour partenaires',
                  'Institutional features',
                ],
              },
            ]}
          />
        );

      case 'team':
        return (
          <TeamSlide
            label="About Us"
            title="Team"
            subtitle="Les experts derrière Vancelian"
            layout="3-column"
            teamMembers={[
              {
                name: 'Gael Itier',
                role: 'CEO & Founder',
                bio: "15 ans d'expérience dans la fintech et les marchés financiers. Ex-Goldman Sachs.",
                linkedin: '#',
              },
              {
                name: 'Sophie Martin',
                role: 'CTO',
                bio: 'Ancienne Lead Engineer chez Stripe. Expert en infrastructure blockchain et IA.',
                linkedin: '#',
              },
              {
                name: 'Thomas Bernard',
                role: 'CPO',
                bio: '10 ans dans le product management fintech. Ex-Revolut et N26.',
                linkedin: '#',
              },
              {
                name: 'Marie Dubois',
                role: 'Head of Compliance',
                bio: 'Expert en régulation financière EU. Ex-ACPR et AMF.',
                linkedin: '#',
              },
              {
                name: 'Alexandre Chen',
                role: 'Head of AI',
                bio: 'PhD en Machine Learning. Recherche chez DeepMind pendant 5 ans.',
                linkedin: '#',
              },
              {
                name: 'Julie Rousseau',
                role: 'Head of Growth',
                bio: 'Scale-up specialist. A fait croître 3 startups de 0 à 100M€ ARR.',
                linkedin: '#',
              },
            ]}
          />
        );

      case 'metrics':
        return (
          <MetricsSlide
            label="Traction"
            title="Key Metrics"
            subtitle="Nos résultats après 12 mois"
            layout="4-column"
            metrics={[
              {
                value: '50K+',
                label: 'Utilisateurs',
                description: 'Clients actifs',
                trend: 'up',
                trendValue: '+120% MoM',
              },
              {
                value: '€250M',
                label: 'AUM',
                description: 'Assets under management',
                trend: 'up',
                trendValue: '+85% MoM',
              },
              {
                value: '4.8',
                label: 'Rating',
                description: 'App Store & Play Store',
                trend: 'neutral',
              },
              {
                value: '€15M',
                label: 'ARR',
                description: 'Annual Recurring Revenue',
                trend: 'up',
                trendValue: '+200% YoY',
              },
              {
                value: '2.5%',
                label: 'Churn',
                description: 'Monthly churn rate',
                trend: 'down',
                trendValue: '-1.2% MoM',
              },
              {
                value: '€180',
                label: 'ARPU',
                description: 'Average revenue per user',
                trend: 'up',
                trendValue: '+15% MoM',
              },
              {
                value: '65%',
                label: 'NPS',
                description: 'Net Promoter Score',
                trend: 'up',
                trendValue: '+5pts',
              },
              {
                value: '3.2x',
                label: 'LTV/CAC',
                description: 'Unit economics',
                trend: 'up',
                trendValue: '+0.5x',
              },
            ]}
          />
        );

      case 'feature-grid':
        return (
          <FeatureGridSlide
            label="Product"
            title="Key Features"
            subtitle="Ce qui rend notre plateforme unique"
            columns={3}
            features={[
              {
                icon: <div className="text-[40px]">🤖</div>,
                title: 'AI Financial Advisor',
                description:
                  "Assistant IA conversationnel qui analyse votre profil et recommande des stratégies d'investissement personnalisées.",
              },
              {
                icon: <div className="text-[40px]">🏠</div>,
                title: 'RWA Tokenization',
                description:
                  "Accès à l'immobilier, commodités et private equity via des tokens fractionnés régulés.",
              },
              {
                icon: <div className="text-[40px]">📊</div>,
                title: 'Portfolio Analytics',
                description:
                  'Dashboard temps réel avec analytics avancés, tracking de performance et insights prédictifs.',
              },
              {
                icon: <div className="text-[40px]">🔒</div>,
                title: 'Bank-Grade Security',
                description:
                  'Infrastructure sécurisée avec chiffrement end-to-end et conformité complète EU.',
              },
              {
                icon: <div className="text-[40px]">💱</div>,
                title: 'Multi-Asset Support',
                description:
                  'Actions, crypto, RWA tokens, commodités — tout dans une seule plateforme unifiée.',
              },
              {
                icon: <div className="text-[40px]">⚡</div>,
                title: 'Instant Execution',
                description:
                  'Exécution ultra-rapide des ordres avec les meilleurs prix du marché via smart routing.',
              },
            ]}
          />
        );

      case 'timeline':
        return (
          <TimelineSlide
            label="Journey"
            title="Company Timeline"
            subtitle="Notre évolution depuis la création"
            events={[
              {
                date: 'Q1 2023',
                title: 'Founding',
                description: "Création de l'entreprise et levée de fonds seed de €2M",
                highlight: false,
              },
              {
                date: 'Q3 2023',
                title: 'MVP Launch',
                description: 'Lancement beta privée avec 1000 premiers utilisateurs',
                highlight: false,
              },
              {
                date: 'Q1 2024',
                title: 'Series A',
                description: 'Levée de €15M menée par Sequoia — expansion européenne',
                highlight: true,
              },
              {
                date: 'Q4 2024',
                title: 'Scale',
                description: '100K utilisateurs — Lancement RWA platform',
                highlight: false,
              },
            ]}
          />
        );

      case 'comparison':
        return (
          <ComparisonSlide
            label="Pricing"
            title="Plans & Pricing"
            subtitle="Choisissez le plan adapté à vos besoins"
            columns={[
              {
                title: 'Starter',
                variant: 'default',
                items: [
                  { label: 'Prix', value: '€0/mois', highlight: true },
                  { label: 'Assets', value: 'Stocks & Crypto' },
                  { label: 'AI Advisor', value: 'Basic' },
                  { label: 'RWA Access', value: '❌' },
                  { label: 'Support', value: 'Email' },
                  { label: 'Analytics', value: 'Basic' },
                ],
              },
              {
                title: 'Premium',
                variant: 'highlight',
                items: [
                  { label: 'Prix', value: '€29/mois', highlight: true },
                  { label: 'Assets', value: 'All Assets' },
                  { label: 'AI Advisor', value: 'Advanced' },
                  { label: 'RWA Access', value: '✓' },
                  { label: 'Support', value: 'Priority' },
                  { label: 'Analytics', value: 'Advanced' },
                ],
              },
              {
                title: 'Institution',
                variant: 'default',
                items: [
                  { label: 'Prix', value: 'Custom', highlight: true },
                  { label: 'Assets', value: 'Unlimited' },
                  { label: 'AI Advisor', value: 'Enterprise' },
                  { label: 'RWA Access', value: '✓✓✓' },
                  { label: 'Support', value: 'Dedicated' },
                  { label: 'Analytics', value: 'Custom' },
                ],
              },
            ]}
          />
        );

      case 'centered':
        return (
          <CenteredContentSlide
            label="Vancelian"
            title="Vision & Mission"
            leftContent={
              <Heading1>
                Redefining Wealth Management for a new generation of investors.
                <br />
                <br />
                <span className="font-['Geist:ExtraLight',sans-serif] font-extralight">
                  Orienté performance et expérience utilisateur
                </span>
              </Heading1>
            }
            rightContent={
              <Heading1>
                <span className="font-['Geist:Medium',sans-serif] font-medium">
                  Building a regulated, technology-native platform that leverage Digital assets and AI.
                </span>
                <br />
                <br />
                <span className="font-['Geist:ExtraLight',sans-serif] font-extralight">
                  RWA
                </span>
              </Heading1>
            }
          />
        );

      case 'team-spotlight':
        return (
          <TeamSpotlightSlide
            label="TEAM"
            title="Sales & Business Developers"
            member={{
              name: 'Christophe Couteau',
              role: 'Group Chief Business Development Officer',
              paragraphs: [
                "Après plusieurs années passées dans la banque privée, Christophe a rejoint Vancelian pour structurer l'offre commerciale et les partenariats institutionnels.",
                "Il pilote les négociations complexes, l'onboarding des grands comptes et l'alignement entre produit, conformité et équipes terrain.",
                "Son approche combine rigueur réglementaire et sens du réseau, ce qui permet d'accélérer les cycles de décision tout en maîtrisant les risques opérationnels.",
              ],
              closingBold:
                "Aujourd'hui, il coordonne l'expansion européenne des activités de distribution et le déploiement des offres RWA auprès des réseaux sélectionnés.",
            }}
          />
        );

      case 'three-key-elements': {
        const pillarBody =
          'Erat autem diritatis eius hoc quoque indicium nec obscurum nec latens, quod ludicris cruentis delectabatur et in circo sex vel septem aliquotiens vetitis certaminibus.';
        return (
          <ThreeKeyElementsSlide
            label="Vancelian APP"
            title="Lorem"
            subtitle="Sous titre ou phrase d'intro"
            layout="4-column"
            elements={[
              {
                title: 'Verum ad istam omnem orationem brevis est',
                tagline: 'Pilier un',
                body: pillarBody,
              },
              {
                title: 'Verum ad istam omnem orationem brevis est',
                tagline: 'Pilier deux',
                body: pillarBody,
              },
              {
                title: 'Verum ad istam omnem orationem brevis est',
                tagline: 'Pilier trois',
                body: pillarBody,
              },
              {
                title: 'Verum ad istam omnem orationem brevis est',
                tagline: 'Pilier quatre',
                body: pillarBody,
              },
            ]}
            conclusion="Conclusion: …"
          />
        );
      }

      case 'why-now-quad': {
        const quadBody =
          'Confingit intervallata debetur et longa se distributio convivia.';
        return (
          <WhyNowQuadSlide
            label="VANCELIAN APP"
            title="Pourquoi maintenant"
            subtitle="Sous titre ou phrase d'intro"
            items={[
              {
                title: 'Verum ad istam omnem orationem brevis est',
                description: quadBody,
              },
              {
                title: 'Verum ad istam omnem orationem brevis est',
                description: quadBody,
              },
              {
                title: 'Verum ad istam omnem orationem brevis est',
                description: quadBody,
              },
              {
                title: 'Verum ad istam omnem orationem brevis est',
                description: quadBody,
              },
            ]}
            conclusion="Conclusion: …"
          />
        );
      }

      case 'checklist-panel': {
        const longItem =
          'Angustus levibus insontium angustus suae corpus ad et ad solet angustus victoriam solet animus increpuisset victoriam quicquid tener quassari.';
        return (
          <ChecklistPanelSlide
            label="VANCELIAN APP"
            title="Lorem ipsum"
            subtitle="Sous titre ou phrase d'intro"
            items={[
              {
                title: 'Premier critère',
                text:
                  'Venerat auspiciis fulgorem primis atque foedere quo Roma quarum perfectam in quo primis plerumque atque.',
              },
              { title: 'Deuxième critère', text: longItem },
              { title: 'Troisième critère', text: longItem },
              { title: 'Quatrième critère', text: longItem },
            ]}
          />
        );
      }

      case 'org-company':
        return (
          <CompanyOrgChartSlide
            label="Vancelian APP"
            title="Organigramme groupe"
            subtitle="Structure des entités juridiques (schéma simplifié)"
            root={{
              title: 'Vancelian Group SA',
              subtitle: 'Holding — Luxembourg',
              children: [
                {
                  title: 'Vancelian EU SAS',
                  subtitle: 'France · Distribution',
                  children: [
                    { title: 'Vancelian Asset Mgt', subtitle: 'Gestion' },
                    { title: 'Vancelian Custody SPV', subtitle: 'Nantissement' },
                  ],
                },
                {
                  title: 'Vancelian Digital Ltd',
                  subtitle: 'UK · Tech & produit',
                },
                {
                  title: 'Vancelian Services S.à r.l.',
                  subtitle: 'Luxembourg · Support',
                  children: [{ title: 'Branch IT', subtitle: 'Nearshore' }],
                },
              ],
            }}
          />
        );

      case 'org-staff':
        return (
          <StaffOrgChartSlide
            label="Vancelian APP"
            title="Organigramme équipe"
            subtitle="Direction et lignes de reporting (exemple)"
            root={{
              name: 'Alexandre Martin',
              role: 'Chief Executive Officer',
              children: [
                {
                  name: 'Claire Dubois',
                  role: 'Chief Operating Officer',
                  children: [
                    { name: 'Julien Petit', role: 'Head of Ops' },
                    { name: 'Nadia El Amrani', role: 'Head of CX' },
                  ],
                },
                {
                  name: 'Marc Lefèvre',
                  role: 'Chief Financial Officer',
                },
                {
                  name: 'Sofia Nguyen',
                  role: 'Chief Technology Officer',
                  children: [
                    { name: 'Tom Weber', role: 'Engineering Lead' },
                    { name: 'Inès Kaya', role: 'Security Lead' },
                  ],
                },
              ],
            }}
          />
        );

      case 'org-staff-advanced':
        return <AdvancedStaffOrgChartSlide {...advancedStaffOrgChartDemo} />;

      case 'offering-split':
        return (
          <OfferingSplitSlide
            label="Vancelian Offering"
            title="Tokenisation RWA"
            subtitle="Thematic Investment – 18 to 48-Month Horizons"
            intro="Un cadre d’investissement thématique pour accéder à des actifs réels tokenisés, avec des horizons de maturité maîtrisés."
            paragraphs={[
              'Les opportunités sont structurées pour une exposition progressive au marché des RWA, avec une transparence sur les paramètres clés du produit.',
              'Une expérience unifiée : souscription, suivi et information sur une même plateforme.',
            ]}
            features={[
              {
                title: 'Diversification',
                description: 'Accès à des paniers thématiques et des actifs réels sélectionnés.',
              },
              {
                title: 'Strictly Selected Opportunities',
                description: 'Processus de revue et critères d’éligibilité documentés.',
              },
              {
                title: 'Daily Distributed Interest',
                description: 'Mécanisme d’intérêts aligné sur la documentation de l’offre.',
              },
              {
                title: 'Liquidity',
                description: 'Fenêtres de sortie et jalons communiqués aux investisseurs.',
              },
            ]}
            rightBackgroundSrc="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&q=80"
            rightBackgroundAlt="Architecture moderne"
            rightHighlights={[
              {
                label: 'Investment Type',
                value: 'Digital Asset Co-Financing',
              },
              {
                label: 'Subscription Amount',
                value: 'No minimum entry ticket',
              },
              {
                label: 'Commitment Period',
                value: '18 to 48 months*',
              },
              {
                label: 'Exit Windows',
                value: 'Biannual',
              },
              {
                label: 'Average Client Returns',
                value: '11%*',
              },
            ]}
            rightFootnote="*Fixed rate: the interest rate remains unchanged for the duration of the commitment. Past performance is not indicative of future results."
            centerScreenSrc="/offering-iphone-app-screenshot.png"
            centerScreenAlt="Application Vancelian — offres exclusives, actualités et navigation"
          />
        );

      default:
        return null;
    }
  };

  const active = slideTemplates.find((t) => t.id === selectedSlide);

  return (
    <div className="min-h-screen bg-[#1a1a1a]">
      <div className="sticky top-0 z-50 border-b border-gray-200 bg-white">
        <div className="flex flex-wrap items-start justify-between gap-4 px-6 py-6 md:px-[60px]">
          <div>
            <h1 className="font-['Geist:Bold',sans-serif] text-[24px] font-bold text-[#1e1c1b]">
              Bibliothèque de templates de slides
            </h1>
            <p className="mt-1 font-['Geist:Regular',sans-serif] text-[14px] text-[#8a8a8a]">
              Choisissez un thème, prévisualisez l’exemple, puis adaptez le contenu dans le code.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/"
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-[#1e1c1b] hover:bg-gray-50"
            >
              ← Registration deck
            </Link>
            <Link
              to="/design-system"
              className="rounded-md bg-[#4F46E5] px-4 py-2 text-sm font-medium text-white hover:bg-[#4338ca]"
            >
              Design system
            </Link>
          </div>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row">
        <div className="sticky top-[73px] z-40 h-auto max-h-[40vh] w-full overflow-y-auto border-b border-gray-200 bg-white lg:top-[97px] lg:h-[calc(100vh-97px)] lg:max-h-none lg:w-[min(400px,100%)] lg:border-r lg:border-b-0">
          <div className="p-6">
            <h2 className="mb-4 font-['Geist:SemiBold',sans-serif] text-[18px] font-semibold text-[#1e1c1b]">
              Templates ({slideTemplates.length})
            </h2>
            <div className="space-y-2">
              {slideTemplates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => setSelectedSlide(template.id)}
                  className={`w-full rounded-lg p-4 text-left transition-all ${
                    selectedSlide === template.id
                      ? 'bg-[#4F46E5] text-white'
                      : 'bg-gray-50 text-[#1e1c1b] hover:bg-gray-100'
                  }`}
                >
                  <div className="mb-1 font-['Geist:SemiBold',sans-serif] text-[16px] font-semibold">
                    {template.name}
                  </div>
                  <div
                    className={`mb-2 font-['Geist:Regular',sans-serif] text-[13px] leading-[1.4] ${
                      selectedSlide === template.id ? 'text-white/80' : 'text-[#8a8a8a]'
                    }`}
                  >
                    {template.description}
                  </div>
                  <div
                    className={`font-['Geist:Regular',sans-serif] text-[12px] italic ${
                      selectedSlide === template.id ? 'text-white/60' : 'text-[#4F46E5]'
                    }`}
                  >
                    {template.useCase}
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-8 rounded-lg bg-[#f2f2f2] p-5">
              <h3 className="mb-3 font-['Geist:SemiBold',sans-serif] text-[14px] font-semibold text-[#1e1c1b]">
                Comment utiliser
              </h3>
              <ol className="space-y-2 text-[13px] leading-[1.5] text-[#8a8a8a]">
                <li className="flex gap-2">
                  <span className="font-semibold text-[#4F46E5]">1.</span>
                  <span>Choisir un template dans la liste</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold text-[#4F46E5]">2.</span>
                  <span>Vérifier l’aperçu (échelle 0,7)</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold text-[#4F46E5]">3.</span>
                  <span>Importer le composant et passer vos props</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold text-[#4F46E5]">4.</span>
                  <span>
                    Exporter la slide affichée ou tout le catalogue en PDF (html2canvas + jsPDF, 1920×1080)
                  </span>
                </li>
              </ol>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 md:p-10 lg:h-[calc(100vh-97px)]">
          <div className="mx-auto flex max-w-[1400px] flex-col items-center">
            <div className="relative mb-8 flex w-full flex-col items-center gap-4">
              <div className="flex flex-wrap items-center justify-center gap-3">
                <button
                  type="button"
                  disabled={pdfExporting}
                  onClick={handleExportCurrentSlidePdf}
                  className="rounded-md bg-[#4F46E5] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#4338ca] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {pdfExporting ? 'Export PDF…' : 'Exporter en PDF'}
                </button>
                <button
                  type="button"
                  disabled={pdfExporting}
                  onClick={handleExportCatalogPdf}
                  className="rounded-md border border-[#4F46E5] bg-white px-5 py-2.5 text-sm font-semibold text-[#4F46E5] shadow-sm transition-colors hover:bg-[#4F46E5]/5 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Tout exporter (PDF)
                </button>
                {active ? (
                  <span className="font-['Geist:Regular',sans-serif] text-[13px] text-[#8a8a8a]">
                    {active.name}
                  </span>
                ) : null}
              </div>
              {!pdfExporting ? (
                <div className="origin-top scale-[0.7] overflow-hidden rounded-lg shadow-2xl">
                  <div className="inline-block">{renderSlide()}</div>
                </div>
              ) : null}
            </div>

            <div className="w-full max-w-[1200px] rounded-xl bg-white p-8 shadow-lg">
              <div className="mb-6">
                <h3 className="mb-2 font-['Geist:Bold',sans-serif] text-[24px] font-bold text-[#1e1c1b]">
                  {active?.name}
                </h3>
                <p className="font-['Geist:Regular',sans-serif] text-[16px] text-[#8a8a8a]">
                  {active?.description}
                </p>
              </div>

              <div className="rounded-lg bg-[#f2f2f2] p-5">
                <p className="mb-2 font-['Geist:SemiBold',sans-serif] text-[14px] font-semibold text-[#1e1c1b]">
                  Import
                </p>
                <pre className="overflow-x-auto rounded border border-gray-200 bg-white p-4 text-[12px]">
                  <code>{`import { ${COMPONENT_IMPORT_NAME[selectedSlide]} } from '@/app/components/slide-templates';`}</code>
                </pre>
              </div>

              <div className="mt-5 rounded-lg border border-[#4F46E5]/20 bg-[#4F46E5]/5 p-5">
                <p className="mb-2 font-['Geist:SemiBold',sans-serif] text-[14px] font-semibold text-[#1e1c1b]">
                  Cas d’usage
                </p>
                <p className="font-['Geist:Regular',sans-serif] text-[14px] text-[#8a8a8a]">
                  {active?.useCase}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {pdfExporting ? (
        <>
          <div className="fixed inset-0 z-[99998] bg-black/50" aria-hidden />
          <p className="fixed left-1/2 top-6 z-[100000] -translate-x-1/2 rounded-md bg-white/95 px-4 py-2 text-sm font-medium text-[#1e1c1b] shadow-md">
            Export PDF…
          </p>
          <div
            ref={pdfCaptureRef}
            className="fixed left-0 top-0 z-[99999] overflow-hidden bg-white shadow-2xl"
            style={{ width: SLIDE_PDF_WIDTH, height: SLIDE_PDF_HEIGHT }}
          >
            {renderSlide()}
          </div>
        </>
      ) : null}
    </div>
  );
}
