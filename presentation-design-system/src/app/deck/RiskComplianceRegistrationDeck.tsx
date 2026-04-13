import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { BodyLarge } from '../components/design-system/Typography';
import { Caption } from '../components/design-system';
import { TitleSlide } from '../components/slide-templates/TitleSlide';
import { TwoColumnSlide } from '../components/slide-templates/TwoColumnSlide';
import { RoadmapSlide } from '../components/slide-templates/RoadmapSlide';
import { ThreeKeyElementsSlide } from '../components/slide-templates/ThreeKeyElementsSlide';
import { MetricsSlide } from '../components/slide-templates/MetricsSlide';
import { FeatureGridSlide } from '../components/slide-templates/FeatureGridSlide';
import { ComparisonSlide } from '../components/slide-templates/ComparisonSlide';
import { ChecklistPanelSlide } from '../components/slide-templates/ChecklistPanelSlide';
import { RiskLcbFtFlowDiagram } from './RiskLcbFtFlowDiagram';

const FOOTER = 'Document interne — Conformité Vancelian';
const TOTAL_SLIDES = 12;

function renderRiskComplianceSlide(index: number) {
  switch (index) {
    case 0:
      return (
        <TitleSlide
          label="Conformité & onboarding"
          title="Registration et cartographie des risques LCB-FT"
          subtitle="Aligner le parcours client avec le référentiel groupe (classification Automata France · nov. 2025) et les attentes PSAN."
          footerText={FOOTER}
        />
      );
    case 1:
      return (
        <TwoColumnSlide
          label="Sources"
          title="Complémentarité PDF registration et grille Excel LCB-FT"
          subtitle={
            <span className="font-['Geist:Regular',sans-serif] text-[28px] text-[#1e1c1b]">
              Une lecture métier (parcours) et une lecture risque (critères & scores).
            </span>
          }
          sections={[
            {
              title: 'Vue « parcours » (PDF équipe)',
              content: (
                <BodyLarge className="text-[18px] leading-[1.45] text-[#5c5c5c]">
                  Cinq blocs successifs : identification, coordonnées, résidence, profil financier, profil
                  investisseur & adéquation. Chaque bloc explique <strong>ce qui est demandé</strong> et{' '}
                  <strong>pourquoi Vancelian le demande</strong> (finalité conformité + sécurité).
                </BodyLarge>
              ),
            },
            {
              title: 'Vue « risque » (Excel LCB-FT)',
              content: (
                <BodyLarge className="text-[18px] leading-[1.45] text-[#5c5c5c]">
                  Axes client PP / PM : connexion, identité, pays, nationalité, listes, PPE, secteur,
                  revenus, patrimoine, forme juridique… Chaque critère porte une <strong>gravité</strong>, des{' '}
                  <strong>points</strong> et alimente le <strong>risk score</strong> global.
                </BodyLarge>
              ),
            },
          ]}
          rightContent={
            <div className="flex h-full w-full flex-col items-center justify-center gap-4 bg-[#f8fafc] px-8">
              <RiskLcbFtFlowDiagram className="max-h-[min(440px,85%)] w-full max-w-[720px]" />
              <p className="max-w-md text-center text-[14px] leading-snug text-[#64748b]">
                Le schéma résume la chaîne décisionnelle ; le détail des critères reste dans la grille
                opérationnelle.
              </p>
            </div>
          }
          footerText={FOOTER}
        />
      );
    case 2:
      return (
        <RoadmapSlide
          label="Parcours client"
          title="Les cinq blocs du registration Vancelian"
          subtitle="Structure alignée sur le support PDF « Registration chez Vancelian »."
          roadmapItems={[
            {
              phase: 'Bloc 1',
              quarter: 'KYC',
              title: 'Identification personnelle',
              items: [
                'État civil, document officiel, vérification biométrique',
                'Objectif : identité réelle avant ouverture du parcours investissement',
              ],
              status: 'completed',
            },
            {
              phase: 'Bloc 2',
              quarter: 'Sécurité',
              title: 'Coordonnées & communication',
              items: [
                'E-mail, mobile, validation des canaux',
                'Sécurisation du compte et traçabilité des échanges',
              ],
              status: 'completed',
            },
            {
              phase: 'Bloc 3',
              quarter: 'Geo',
              title: 'Résidence & rattachement réglementaire',
              items: [
                'Adresse, fiscalité, restrictions pays & éligibilité marché',
                'Cadre de distribution piloté par la résidence',
              ],
              status: 'in-progress',
            },
            {
              phase: 'Bloc 4',
              quarter: 'Profil',
              title: 'Profil financier',
              items: [
                'Situation pro, capacité financière, cohérence des flux',
                'Base économique avant exposition aux produits',
              ],
              status: 'planned',
            },
            {
              phase: 'Bloc 5',
              quarter: 'MiFID',
              title: 'Profil investisseur & adéquation',
              items: [
                'Objectifs, appétence au risque, connaissances financières',
                'Justifie l’adéquation des offres au-delà du KYC « entrée »',
              ],
              status: 'planned',
            },
          ]}
          footerText={FOOTER}
        />
      );
    case 3:
      return (
        <ThreeKeyElementsSlide
          label="Méthodologie LCB-FT"
          title="Comment la cartographie structure notre vigilance"
          subtitle="Synthèse de l’onglet Introduction du référentiel Excel."
          layout="3-column"
          elements={[
            {
              title: 'Identification',
              tagline: 'Sources & typologies',
              body: 'Risques identifiés à partir de l’expérience opérationnelle, de la veille réglementaire et de l’analyse des services (fiat & crypto).',
            },
            {
              title: 'Classification',
              tagline: 'Axes & critères',
              body: 'Classement par origines (client, produit, canal, géographie…) avec critères homogènes : gravité, points, code couleur.',
            },
            {
              title: 'Décision',
              tagline: 'Risk score',
              body: 'Cumul des points → note globale. Elle oriente entrée en relation, vigilance standard ou renforcée, alerte, refus ou rupture.',
            },
          ]}
          conclusion="Le score n’est pas une probabilité : c’est un outil qualitatif de pilotage, à actualiser quand le contexte évolue."
          confidentialText={FOOTER}
        />
      );
    case 4:
      return (
        <MetricsSlide
          label="Barème global"
          title="Seuils de risque agrégé (risk score)"
          subtitle="Fourchette indicative issue du référentiel — à calibrer avec Compliance."
          layout="4-column"
          metrics={[
            { value: '0 – 499', label: 'Risque faible', description: 'Suivi standard' },
            { value: '500 – 799', label: 'Risque modéré', description: 'Vigilance adaptée' },
            { value: '800 – 1799', label: 'Risque élevé', description: 'Mesures renforcées' },
            { value: '≥ 1800', label: 'Refus / rupture', description: 'Hors critères acceptables' },
          ]}
          footerText={FOOTER}
        />
      );
    case 5:
      return (
        <MetricsSlide
          label="Gravité unitaire"
          title="Points cumulés par niveau de gravité d’un critère"
          layout="3x2"
          metrics={[
            { value: '0', label: 'Faible', description: 'Point de départ barème' },
            { value: '100', label: 'Modéré', trend: 'neutral' },
            { value: '200', label: 'Élevé', trend: 'up', trendValue: '+' },
            { value: '800', label: 'Très élevé', trend: 'up', trendValue: '++' },
            { value: '1800', label: 'Inacceptable', trend: 'up', trendValue: 'stop' },
          ]}
          footerText={FOOTER}
        />
      );
    case 6:
      return (
        <TwoColumnSlide
          label="Axe client personne physique"
          title="Où le registration croise la grille risque"
          sections={[
            {
              title: 'Identité & connexion',
              content: (
                <BodyLarge className="text-[17px] leading-[1.45] text-[#5c5c5c]">
                  VPN bloqué, cohérence IP / pays, pièces valides, virement d’activation, US persons,
                  identification des BE — bascule entre <strong>refus</strong>, <strong>EDD</strong> ou{' '}
                  <strong>parcours standard</strong>.
                </BodyLarge>
              ),
            },
            {
              title: 'Géographie & listes',
              content: (
                <BodyLarge className="text-[17px] leading-[1.45] text-[#5c5c5c]">
                  Pays prohibés, hors EEE, listes GAFI / UE, pays à risque interne, nationalité & naissance,
                  gels, OFAC, PPE, adverse media, TRACFIN / soupçons.
                </BodyLarge>
              ),
            },
            {
              title: 'Économie & comportement',
              content: (
                <BodyLarge className="text-[17px] leading-[1.45] text-[#5c5c5c]">
                  Capacité (âge, tutelle), ancienneté relation, profession, secteur NACE, fourchettes de
                  revenus & patrimoine, sources et origine des fonds.
                </BodyLarge>
              ),
            },
          ]}
          rightContent={
            <div className="flex h-full w-full flex-col justify-center bg-[#f1f5f9] px-6 py-10">
              <RiskLcbFtFlowDiagram className="h-auto w-full" />
            </div>
          }
          footerText={FOOTER}
        />
      );
    case 7:
      return (
        <FeatureGridSlide
          label="Hotspots sectoriels"
          title="Secteurs typiquement classés à risque élevé (PP)"
          subtitle="Extraits représentatifs — la grille complète demeure dans l’Excel métier."
          columns={3}
          features={[
            {
              title: 'Services sur crypto-actifs',
              description:
                'Anonymat relatif, flux transfrontaliers, plateformes non régulées : vigilance renforcée sur l’origine des fonds et la cohérence avec le profil déclaré.',
            },
            {
              title: 'Immobilier & BTP',
              description:
                'Montants élevés, espèces, intermédiaires, SCI : risque de blanchiment via montages et sous/surévaluation.',
            },
            {
              title: 'Défense, énergie fossile, luxe & art',
              description:
                'Corruption, circuits opaques, export : combinaison géographie + contreparties sensibles.',
            },
            {
              title: 'Droit, comptabilité, armement',
              description:
                'Professions et industries à potentiel d’abus pour structurer ou dissimuler des flux.',
            },
            {
              title: 'Hôtellerie, restauration, transport, casinos',
              description:
                'Espèces, international, anonymat client : typologies classiques de placement de liquidités.',
            },
            {
              title: 'Jeux d’argent',
              description:
                'Mouvements rapides de fonds et usage d’espèces : un des niveaux de vigilance les plus élevés du référentiel.',
            },
          ]}
          footerText={FOOTER}
        />
      );
    case 8:
      return (
        <ComparisonSlide
          label="Lecture croisée"
          title="Parcours, facteurs LCB-FT et décisions"
          subtitle="Relier l’expérience utilisateur aux obligations réglementaires."
          columns={[
            {
              title: 'Ce que voit le client',
              variant: 'default',
              items: [
                { label: 'Étapes 1-3', value: 'Identité, contact, pays' },
                { label: 'Étapes 4-5', value: 'Moyens, objectifs, adéquation' },
                { label: 'Attendu', value: 'Parcours fluide si dossier cohérent' },
              ],
            },
            {
              title: 'Ce que voit Compliance',
              variant: 'highlight',
              items: [
                { label: 'Scores & listes', value: 'Points cumulés + hits réglementaires', highlight: true },
                { label: 'EDD / N2', value: 'PPE, ambiguïtés, médias défavorables', highlight: true },
                { label: 'Traçabilité', value: 'Justification des décisions d’entrée', highlight: true },
              ],
            },
            {
              title: 'Sorties possibles',
              variant: 'default',
              items: [
                { label: 'Standard', value: 'Suivi périodique' },
                { label: 'Renforcé', value: 'Sources complémentaires, validation hiérarchique' },
                { label: 'Bloquant', value: 'Refus, sortie de relation, déclaration si requis' },
              ],
            },
          ]}
          footerText={FOOTER}
        />
      );
    case 9:
      return (
        <ChecklistPanelSlide
          label="Points de vigilance"
          title="Limites du document source"
          subtitle="Extraits de l’onglet Introduction — à rappeler en comité risque."
          items={[
            {
              title: 'Nature qualitative',
              text: 'La classification est qualitative au 14/11/2025 : ce n’est ni une mesure probabiliste ni une cartographie chiffrée de scénarios.',
            },
            {
              title: 'Évolutions permanentes',
              text: 'Services, typologies de blanchiment / FT et textes évoluent : la grille doit être révisée quand le contexte interne ou externe change.',
            },
            {
              title: 'Accès restreint',
              text: 'Document tenu par le Département Conformité ; diffusion aux fonctions habilitées (juridique, FinCrime, audit).',
            },
            {
              title: 'Alignement Vancelian',
              text: 'Les mentions « Automata France » du référentiel désignent la base méthodo groupe : l’implémentation produit et les seuils effectifs restent validés par Compliance Vancelian.',
            },
          ]}
        />
      );
    case 10:
      return (
        <TwoColumnSlide
          label="Cadre réglementaire"
          title="Pourquoi cette exigence de fond"
          quote={{
            text: (
              <span className="text-[20px] leading-[1.45]">
                En tant que PSAN enregistré par l’AMF, nous appliquons les obligations LCB-FT du cadre français
                et européen : connaissance de la clientèle, surveillance des transactions et gouvernance des
                risques.
              </span>
            ),
            attribution: 'Synthèse — Introduction référentiel LCB-FT',
            role: 'Base légale & culture compliance',
          }}
          sections={[
            {
              title: 'Lien avec le registration',
              content: (
                <BodyLarge className="text-[18px] leading-[1.45] text-[#5c5c5c]">
                  Chaque écran du parcours alimente des données qui servent à la fois au <strong>service client</strong>{' '}
                  et aux <strong>contrôles AML</strong> : même source de vérité, double lecture métier / risque.
                </BodyLarge>
              ),
            },
          ]}
          rightContent={
            <div className="flex h-full w-full flex-col justify-center gap-6 bg-gradient-to-br from-[#eef2ff] to-white px-14">
              <div className="rounded-2xl border border-[#c7d2fe] bg-white/90 p-8 shadow-sm">
                <p className="text-[15px] font-semibold uppercase tracking-wider text-[#4F46E5]">
                  Personnes morales
                </p>
                <BodyLarge className="mt-3 text-[17px] leading-[1.5] text-[#374151]">
                  L’Excel détaille un axe PM distinct (KYB, formes juridiques, ancienneté société, BE dans les
                  PTHR, scoring via « internal checking business account »). Prévoir un module équivalent dans
                  les formations internes.
                </BodyLarge>
              </div>
              <div className="rounded-2xl border border-dashed border-[#94a3b8] bg-white/60 p-6">
                <p className="text-[14px] text-[#64748b]">
                  Prochaine itération possible : slide dédiée « formes juridiques & scores » en s’appuyant sur
                  l’onglet Axe 1 — PM du fichier source.
                </p>
              </div>
            </div>
          }
          footerText={FOOTER}
        />
      );
    case 11:
      return (
        <TitleSlide
          label="Suite"
          title="Prochaines étapes suggérées"
          subtitle="Atelier Compliance × Produit : calage des seuils, traduction des critères dans l’app, et boucle de retour FinCrime sur les nouveaux parcours."
          footerText={FOOTER}
        />
      );
    default:
      return null;
  }
}

export default function RiskComplianceRegistrationDeck() {
  const [index, setIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => {
      const w = el.clientWidth;
      const pad = 32;
      setScale(Math.min(1, Math.max(0.2, (w - pad) / 1920)));
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const go = useCallback(
    (delta: number) => {
      setIndex((i) => Math.max(0, Math.min(TOTAL_SLIDES - 1, i + delta)));
    },
    [],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
        e.preventDefault();
        go(1);
      }
      if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault();
        go(-1);
      }
      if (e.key === 'Home') {
        e.preventDefault();
        setIndex(0);
      }
      if (e.key === 'End') {
        e.preventDefault();
        setIndex(TOTAL_SLIDES - 1);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go]);

  const slide = renderRiskComplianceSlide(index);

  return (
    <div className="flex min-h-screen flex-col bg-[#e5e5e5]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-300 bg-white px-6 py-3">
        <Caption className="text-[#1e1c1b]">
          Registration · risques LCB-FT — slide {index + 1} / {TOTAL_SLIDES} (flèches, espace, Début / Fin)
        </Caption>
        <div className="flex flex-wrap items-center gap-3">
          <Link to="/" className="text-sm font-medium text-[#4F46E5] hover:underline">
            Registration deck (vue simple)
          </Link>
          <Link to="/templates" className="text-sm font-medium text-[#4F46E5] hover:underline">
            Galerie templates
          </Link>
          <Link to="/presentations" className="text-sm font-medium text-[#4F46E5] hover:underline">
            API présentations
          </Link>
        </div>
      </header>

      <main ref={containerRef} className="flex flex-1 justify-center overflow-auto px-4 py-8">
        <div
          className="relative shrink-0 overflow-hidden rounded-sm shadow-lg"
          style={{ width: 1920 * scale, height: 1080 * scale }}
        >
          <div
            className="absolute left-0 top-0 origin-top-left"
            style={{ width: 1920, height: 1080, transform: `scale(${scale})` }}
          >
            {slide}
          </div>
        </div>
      </main>

      <footer className="border-t border-gray-300 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-center gap-4">
          <button
            type="button"
            onClick={() => go(-1)}
            disabled={index <= 0}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-[#1e1c1b] disabled:opacity-40"
          >
            Précédent
          </button>
          <div className="flex flex-wrap justify-center gap-2">
            {Array.from({ length: TOTAL_SLIDES }, (_, j) => (
              <button
                key={j}
                type="button"
                onClick={() => setIndex(j)}
                className={`h-2.5 w-2.5 rounded-full transition-colors ${
                  j === index ? 'bg-[#4F46E5]' : 'bg-gray-300 hover:bg-gray-400'
                }`}
                aria-label={`Slide ${j + 1}`}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={() => go(1)}
            disabled={index >= TOTAL_SLIDES - 1}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-[#1e1c1b] disabled:opacity-40"
          >
            Suivant
          </button>
        </div>
      </footer>
    </div>
  );
}
