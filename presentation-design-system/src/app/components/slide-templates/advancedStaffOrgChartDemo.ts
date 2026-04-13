import type { AdvancedStaffOrgChartSlideProps } from './AdvancedStaffOrgChartSlide';

/** Données d’exemple pour la galerie — à dupliquer / adapter pour un deck réel. */
export const advancedStaffOrgChartDemo: AdvancedStaffOrgChartSlideProps = {
  label: 'Vancelian APP',
  title: 'Organigramme — équipe',
  subtitle: 'Gouvernance & départements fonctionnels',
  board: {
    title: 'Board',
    entries: [
      { line: 'A. Dupont', sub: 'Présidente', isNew: true },
      { line: 'M. Bernard', sub: 'Administrateur indépendant' },
      { line: 'L. Chen', sub: 'Investisseur' },
      { line: 'K. Müller', sub: 'Administrateur' },
    ],
  },
  surveillance: {
    title: 'Comité de surveillance',
    entries: [
      { line: 'J. Martin', sub: 'Président' },
      { line: 'S. Nguyên', sub: 'Membre' },
      { line: 'R. Silva', sub: 'Membre' },
      { line: 'T. Weber', sub: 'Membre' },
    ],
  },
  direction: {
    title: 'Direction',
    executives: [
      { name: 'Gaël Itier', role: 'CEO' },
      { name: 'Jean Guillou', role: 'CIO' },
    ],
  },
  operationalCommittee: {
    title: 'Comité de direction opérationnel',
    executives: [
      { name: 'Claire Dubois', role: 'COO' },
      { name: 'Marc Lefèvre', role: 'CFO' },
      { name: 'Sofia Nguyen', role: 'CTO' },
      { name: 'Julien Petit', role: 'CPO' },
    ],
  },
  centerSupport: [
    { title: 'COO', subtitle: 'Operations', colorKey: 'teal' },
    { title: 'RH & Admin', subtitle: 'Support', colorKey: 'gray5' },
  ],
  departmentsSectionTitle: 'Départements fonctionnels',
  departments: [
    {
      id: 'it',
      name: 'IT & Technologie',
      headerColorKey: 'blue',
      headcount: 8,
      lead: { name: 'Alexandre Roy', title: 'Head of Engineering' },
      members: [
        { name: 'N. Kowalski', title: 'Lead Dev', tags: [{ label: 'FR', colorKey: 'indigo' }] },
        { name: 'E. Park', title: 'SRE', tags: [{ label: 'New', colorKey: 'semanticPositive' }] },
        { name: 'O. Hansen', title: 'Developer' },
      ],
    },
    {
      id: 'cyber',
      name: 'Cybersécurité',
      headerColorKey: 'red',
      headcount: 5,
      lead: { name: 'Inès Kaya', title: 'CISO' },
      members: [
        { name: 'T. Weber', title: 'Security Lead', tags: [{ label: 'FR', colorKey: 'purple' }] },
        { name: 'M. Ali', title: 'Analyste SOC' },
      ],
    },
    {
      id: 'product',
      name: 'Produit',
      headerColorKey: 'purple',
      headcount: 6,
      lead: { name: 'Julien Petit', title: 'CPO' },
      members: [
        { name: 'L. Fontaine', title: 'Product Owner', tags: [{ label: 'New', colorKey: 'semanticPositive' }] },
        { name: 'Y. Ito', title: 'Designer' },
      ],
    },
    {
      id: 'mkt',
      name: 'Marketing & Com.',
      headerColorKey: 'pink',
      headcount: 7,
      lead: { name: 'Camille Renard', title: 'CMO' },
      members: [
        { name: 'P. Costa', title: 'Growth', tags: [{ label: 'FR', colorKey: 'indigo' }] },
        { name: 'H. Schmidt', title: 'Content' },
      ],
    },
    {
      id: 'sales',
      name: 'Sales force',
      headerColorKey: 'indigo',
      headcount: 9,
      lead: { name: 'Thomas Blanc', title: 'Chief Revenue Officer' },
      members: [
        { name: 'V. Rossi', title: 'Account Exec.', tags: [{ label: 'UAE', colorKey: 'cyan' }] },
        { name: 'J. Lee', title: 'SDR' },
      ],
    },
    {
      id: 'legal',
      name: 'Legal & Compliance',
      headerColorKey: 'orange',
      headcount: 4,
      lead: { name: 'Amélie Caron', title: 'General Counsel' },
      members: [
        { name: 'F. Meyer', title: 'Compliance Officer' },
        { name: 'G. Novak', title: 'Paralegal', tags: [{ label: 'FZE', colorKey: 'semanticInfo' }] },
      ],
    },
    {
      id: 'finance',
      name: 'Finance',
      headerColorKey: 'green',
      headcount: 5,
      lead: { name: 'Marc Lefèvre', title: 'CFO' },
      members: [
        { name: 'D. Singh', title: 'Contrôleur de gestion' },
        { name: 'I. Popescu', title: 'Trésorerie' },
      ],
    },
    {
      id: 'cs',
      name: 'CS & Support',
      headerColorKey: 'cyan',
      headcount: 6,
      lead: { name: 'Nadia El Amrani', title: 'Head of CX' },
      members: [
        { name: 'S. Brown', title: 'Support L2', tags: [{ label: 'FR', colorKey: 'indigo' }] },
        { name: 'A. Gómez', title: 'Customer Success' },
      ],
    },
  ],
  showFooterLegend: true,
};
