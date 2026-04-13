import { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  DisplayTitle, 
  SectionTitle, 
  Heading1, 
  Heading2, 
  BodyLarge,
  BodyMedium,
  Caption, 
  Label,
  MonoLabel,
  QuoteText,
  Logo,
  Divider,
  Quote,
  Arrow,
  LabelCard,
  FeatureCard,
  StackedFeatureCard,
  Section,
  SlideLayout,
  SlideHeader,
  TwoColumnLayout
} from './components/design-system';
import { ColorPalette } from './components/design-system/Colors';
import { OfferingIphoneDevice } from './components/slide-templates';
import { IPHONE_PRO_APP_FRAME_SRC } from './design-tokens/iphoneProAppFrame';

export function DesignSystemShowcase() {
  const [iphoneScreenUrl, setIphoneScreenUrl] = useState('/offering-iphone-app-screenshot.png');

  return (
    <>
    <nav className="sticky top-0 z-50 flex flex-wrap gap-4 border-b border-gray-200 bg-white/95 px-6 py-3 backdrop-blur">
      <Link to="/" className="text-sm font-medium text-[#4F46E5] hover:underline">
        ← Registration deck
      </Link>
      <Link to="/templates" className="text-sm font-medium text-[#4F46E5] hover:underline">
        Templates de slides
      </Link>
    </nav>
    <div className="min-h-screen bg-white">
      {/* Hero Section - Design System Overview */}
      <section className="px-[120px] py-[120px] bg-gradient-to-br from-white to-[#f2f2f2]">
        <div className="flex flex-col gap-[48px] max-w-[1200px]">
          <Label>Design System</Label>
          <DisplayTitle>
            Vancelian Presentation
            <br />
            Design System
          </DisplayTitle>
          <Divider />
          <BodyLarge>
            Un système de design complet pour créer des présentations professionnelles et cohérentes.
            Tous les composants extraits de vos slides Figma, prêts à être réutilisés.
          </BodyLarge>
        </div>
      </section>

      {/* Logo Variants */}
      <section className="px-[120px] py-[80px] border-b border-gray-200">
        <SectionTitle className="mb-[48px]">Logo</SectionTitle>
        <div className="flex flex-col gap-[40px]">
          <div className="flex items-end gap-[60px]">
            <div>
              <Caption className="mb-4">Large / Primary</Caption>
              <Logo variant="primary" size="large" />
            </div>
            <div>
              <Caption className="mb-4">Medium / Primary</Caption>
              <Logo variant="primary" size="medium" />
            </div>
            <div>
              <Caption className="mb-4">Small / Secondary</Caption>
              <Logo variant="secondary" size="small" />
            </div>
          </div>
        </div>
      </section>

      {/* Color Palette */}
      <section className="px-[120px] py-[80px] border-b border-gray-200">
        <SectionTitle className="mb-[12px]">Palette de couleurs</SectionTitle>
        <BodyMedium className="mb-[48px] max-w-[800px] text-[#636366]">
          Couleurs slides (Figma) + palette Flutter <code className="font-mono text-[15px]">AppColors</code>{' '}
          (variables <code className="font-mono text-[15px]">--flutter-*</code>, utilitaires{' '}
          <code className="font-mono text-[15px]">bg-flutter-*</code>).
        </BodyMedium>
        <ColorPalette />
      </section>

      {/* Mockup iPhone (offering / app) */}
      <section className="border-b border-gray-200 px-[120px] py-[80px]">
        <SectionTitle className="mb-[12px]">Mockup iPhone app</SectionTitle>
        <BodyMedium className="mb-[8px] max-w-[900px] text-[#636366]">
          Par défaut : cadre vectoriel fin (<code className="font-mono text-[14px]">IPHONE_PRO_DEVICE_VECTOR_SPEC</code>
          ). Avec <code className="font-mono text-[14px]">frameSrc</code>, calage PNG{' '}
          <code className="font-mono text-[14px]">{IPHONE_PRO_APP_FRAME_SRC}</code> via{' '}
          <code className="font-mono text-[14px]">IPHONE_PRO_APP_FRAME_SPEC</code> (
          <code className="font-mono text-[14px]">design-tokens/iphoneProAppFrame.ts</code>).
        </BodyMedium>
        <Caption className="mb-[24px] block">
          Props : <code className="font-mono">screenSrc</code> ou <code className="font-mono">screen</code> (React) —
          priorité à <code className="font-mono">screen</code>. Sans les deux : image aléatoire{' '}
          <code className="font-mono text-[12px]">picsum.photos</code>. Fond autour du device : transparent.
        </Caption>
        <div className="flex flex-wrap items-end gap-[40px] rounded-[12px] bg-[#f4f4f5] p-[40px]">
          <OfferingIphoneDevice
            screenSrc={iphoneScreenUrl.trim() ? iphoneScreenUrl.trim() : undefined}
            screenAlt="Aperçu app"
          />
          <div className="flex min-w-[280px] max-w-[480px] flex-1 flex-col gap-3">
            <Caption>URL de l’image (capture sans cadre)</Caption>
            <input
              type="url"
              value={iphoneScreenUrl}
              onChange={(e) => setIphoneScreenUrl(e.target.value)}
              placeholder="https://… ou /captures/mon-ecran.png"
              className="w-full rounded-lg border border-[#E5E7EB] bg-white px-4 py-3 font-mono text-[14px] text-[#1C1C1E] outline-none focus:ring-2 focus:ring-[#6B5DFF]/30"
            />
            <BodyMedium className="!text-[15px] !text-[#8E8E93]">
              Laissez vide pour une image aléatoire (picsum). Utilisez le même composant dans{' '}
              <code className="font-mono text-[13px]">OfferingSplitSlide</code> via{' '}
              <code className="font-mono text-[13px]">centerScreenSrc</code> ou{' '}
              <code className="font-mono text-[13px]">centerScreen</code>.
            </BodyMedium>
          </div>
        </div>
      </section>

      {/* Typography */}
      <section className="px-[120px] py-[80px] border-b border-gray-200">
        <SectionTitle className="mb-[48px]">Typographie</SectionTitle>
        <div className="flex flex-col gap-[60px] max-w-[1200px]">
          <div className="flex flex-col gap-4">
            <Caption>Display Title (96px)</Caption>
            <DisplayTitle>Redefining Wealth Management</DisplayTitle>
          </div>
          
          <div className="flex flex-col gap-4">
            <Caption>Section Title (60px)</Caption>
            <SectionTitle>Vision & Mission</SectionTitle>
          </div>
          
          <div className="flex flex-col gap-4">
            <Caption>Heading 1 (40px)</Caption>
            <Heading1>AI is the new norm</Heading1>
          </div>
          
          <div className="flex flex-col gap-4">
            <Caption>Heading 2 (32px)</Caption>
            <Heading2>De la tokenisation d'actif du monde réel</Heading2>
          </div>
          
          <div className="flex flex-col gap-4">
            <Caption>Body Large (24px)</Caption>
            <BodyLarge>
              Fintech democratized access to markets and crypto → mission accomplished.
              As AI reshapes how people search, decide, interact and live, financial advisory must shift to AI-driven guidance.
            </BodyLarge>
          </div>

          <div className="flex flex-col gap-4">
            <Caption>Body Medium (18px)</Caption>
            <BodyMedium>
              Standard body text for detailed descriptions and paragraphs. Perfect for longer content.
            </BodyMedium>
          </div>
          
          <div className="flex flex-col gap-4">
            <Caption>Label (24px uppercase)</Caption>
            <Label>Pitch Deck</Label>
          </div>

          <div className="flex flex-col gap-4">
            <Caption>Mono Label (24px uppercase)</Caption>
            <MonoLabel>Vancelian</MonoLabel>
          </div>
          
          <div className="flex flex-col gap-4">
            <Caption>Quote Text (40px italic)</Caption>
            <QuoteText>
              We are entering a new structural cycle in finance as technology accelerates and user expectations evolve.
            </QuoteText>
          </div>
        </div>
      </section>

      {/* Dividers */}
      <section className="px-[120px] py-[80px] border-b border-gray-200">
        <SectionTitle className="mb-[48px]">Séparateurs</SectionTitle>
        <div className="flex flex-col gap-[40px] max-w-[1200px]">
          <div>
            <Caption className="mb-4">Divider avec accent (défaut)</Caption>
            <Divider />
          </div>
          <div>
            <Caption className="mb-4">Divider accent personnalisé (100px)</Caption>
            <Divider accentWidth={100} />
          </div>
          <div>
            <Caption className="mb-4">Divider simple</Caption>
            <Divider variant="primary" />
          </div>
        </div>
      </section>

      {/* Quote Component */}
      <section className="px-[120px] py-[80px] border-b border-gray-200 bg-[#f2f2f2]">
        <SectionTitle className="mb-[48px]">Citations</SectionTitle>
        <div className="max-w-[1078px]">
          <Quote 
            attribution="Gael Itier"
            role="Founder & CEO Group, Vancelian Group"
            iconColor="#4F46E5"
          >
            We are entering a new structural cycle in finance as technology accelerates and user expectations evolve.
            If financial institutions took 10 years to become digital, how will they pivot to AI and RWA in the next 24 months?
          </Quote>
        </div>
      </section>

      {/* Arrow */}
      <section className="px-[120px] py-[80px] border-b border-gray-200">
        <SectionTitle className="mb-[48px]">Flèche</SectionTitle>
        <div className="flex items-center gap-[16px]">
          <Arrow />
          <Heading2>De la tokenisation d'actif du monde réel à une expérience IA générative</Heading2>
        </div>
      </section>

      {/* Cards */}
      <section className="px-[120px] py-[80px] border-b border-gray-200">
        <SectionTitle className="mb-[48px]">Cards</SectionTitle>
        <div className="flex flex-col gap-[40px] max-w-[1000px]">
          <div>
            <Caption className="mb-4">Label Card</Caption>
            <LabelCard label="AI" variant="white" />
          </div>
          
          <div>
            <Caption className="mb-4">Feature Card</Caption>
            <FeatureCard 
              title="La nouvelle norme AI incontournable"
              description="AI"
              variant="light"
            />
          </div>

          <div>
            <Caption className="mb-4">Stacked Feature Card</Caption>
            <StackedFeatureCard 
              title="Infrastructure Neobanking et Fintechs"
              items={["Payment - Core banking", "Investment engine"]}
              variant="light"
            />
          </div>
        </div>
      </section>

      {/* Content Sections */}
      <section className="px-[120px] py-[80px] border-b border-gray-200">
        <SectionTitle className="mb-[48px]">Sections de contenu</SectionTitle>
        <div className="flex flex-col gap-[64px] max-w-[1200px]">
          <Section 
            title="AI is the new norm"
            content={
              <>
                Fintech democratized access to markets and crypto → mission accomplished.
                <br />
                As AI reshapes how people search, decide, interact and live, financial advisory must shift to AI-driven guidance.
                <br />
                Access of financial market is the old world, forcing the interface of finance is being rebuilt.
              </>
            }
          />
          
          <Section 
            title="Performance is Under Pressure"
            content={
              <>
                Purchasing power is eroding. Markets are ultra-efficient. Alpha is compressed.
                <br />
                Investors are searching for new options of return, private markets and alternative yield
              </>
            }
          />
        </div>
      </section>

      {/* Slide Header Examples */}
      <section className="px-[120px] py-[80px] border-b border-gray-200 bg-[#f2f2f2]">
        <SectionTitle className="mb-[48px]">En-têtes de slides</SectionTitle>
        <div className="flex flex-col gap-[60px]">
          <div className="bg-white rounded-lg overflow-hidden">
            <SlideHeader 
              label="Vancelian"
              title="Context"
              showLogo={false}
            />
          </div>
          
          <div className="bg-white rounded-lg overflow-hidden">
            <SlideHeader 
              label="Vancelian APP"
              title="Infrastructure"
              subtitle={
                <>
                  <Arrow />
                  <Heading2>De la tokenisation d'actif du monde réel à une expérience IA générative</Heading2>
                </>
              }
            />
          </div>
        </div>
      </section>

      {/* Complete Slide Example */}
      <section className="py-[80px] overflow-x-auto">
        <div className="px-[120px] mb-[48px]">
          <SectionTitle>Exemple de slide complet</SectionTitle>
        </div>
        <div className="flex justify-center">
          <div className="scale-[0.5] origin-top">
            <SlideLayout background="light">
              <TwoColumnLayout
                left={
                  <div className="bg-white h-full">
                    <SlideHeader 
                      label="Vancelian"
                      title="Context"
                      showLogo={false}
                    />
                    <div className="px-[60px] py-[40px] flex flex-col gap-[64px]">
                      <Section 
                        title="AI is the new norm"
                        content={
                          <>
                            Fintech democratized access to markets and crypto → mission accomplished.
                            <br />
                            As AI reshapes how people search, decide, interact and live, financial advisory must shift to AI-driven guidance.
                          </>
                        }
                      />
                      
                      <Quote 
                        attribution="Gael Itier"
                        role="Founder & CEO Group, Vancelian Group"
                      >
                        We are entering a new structural cycle in finance as technology accelerates and user expectations evolve.
                      </Quote>
                    </div>
                  </div>
                }
                right={
                  <div className="bg-[#f2f2f2] h-full flex items-center justify-center">
                    <div className="text-center">
                      <Heading1>Image ou contenu visuel</Heading1>
                    </div>
                  </div>
                }
              />
            </SlideLayout>
          </div>
        </div>
      </section>

      {/* Usage Guide */}
      <section className="px-[120px] py-[120px] bg-gradient-to-br from-[#f2f2f2] to-white">
        <div className="max-w-[1200px]">
          <SectionTitle className="mb-[48px]">Guide d'utilisation</SectionTitle>
          <div className="flex flex-col gap-[32px]">
            <div className="bg-white p-[40px] rounded-lg border border-gray-200">
              <Heading2 className="mb-4">Import des composants</Heading2>
              <pre className="bg-gray-50 p-4 rounded text-sm overflow-x-auto">
                <code>{`import { 
  Logo, 
  Divider, 
  Quote, 
  SlideLayout,
  SlideHeader,
  Section 
} from './components/design-system';`}</code>
              </pre>
            </div>

            <div className="bg-white p-[40px] rounded-lg border border-gray-200">
              <Heading2 className="mb-4">Composants disponibles</Heading2>
              <ul className="grid grid-cols-2 gap-4">
                <li className="flex items-center gap-2">
                  <span className="text-[#4F46E5]">→</span>
                  <BodyMedium>Logo (3 tailles, 2 variantes)</BodyMedium>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-[#4F46E5]">→</span>
                  <BodyMedium>Typography (10+ composants)</BodyMedium>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-[#4F46E5]">→</span>
                  <BodyMedium>Divider (2 variantes)</BodyMedium>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-[#4F46E5]">→</span>
                  <BodyMedium>Quote (avec attribution)</BodyMedium>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-[#4F46E5]">→</span>
                  <BodyMedium>Cards (3 types)</BodyMedium>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-[#4F46E5]">→</span>
                  <BodyMedium>SlideLayout & Headers</BodyMedium>
                </li>
              </ul>
            </div>

            <div className="bg-white p-[40px] rounded-lg border border-gray-200">
              <Heading2 className="mb-4">Palette de couleurs</Heading2>
              <ul className="space-y-2">
                <li className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded bg-[#1E1C1B]" />
                  <BodyMedium>Primary Black: #1E1C1B</BodyMedium>
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded bg-[#4F46E5]" />
                  <BodyMedium>Accent: #4F46E5</BodyMedium>
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded bg-[#8A8A8A]" />
                  <BodyMedium>Gray: #8A8A8A</BodyMedium>
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded bg-[#F2F2F2]" />
                  <BodyMedium>Light Gray: #F2F2F2</BodyMedium>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </div>
    </>
  );
}
