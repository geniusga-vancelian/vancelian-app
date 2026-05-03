/**
 * Catalogue des composants MJML disponibles dans `emails/mjml/components/`
 * et `emails/mjml/partials/`.
 *
 * Sert à :
 * - alimenter la galerie admin `/admin/email/components`
 * - donner aux outils (et à l’IA) la liste des partials Mustache utilisables
 *   dans un template (`{{> ComponentName}}`) avec un exemple de variables.
 *
 * Chaque entrée définit :
 * - `id` : nom du fichier sans `.mjml` (clé Mustache)
 * - `kind` :
 *     - `'section'` : composant top-level (à placer directement dans `<mj-body>`)
 *     - `'inline'`  : composant à placer dans `<mj-column>` (boutons, eyebrow…)
 * - `description` : 1 phrase
 * - `vars` : exemple complet (utilisé pour la preview et comme référence de schéma)
 */
export interface EmailComponentEntry {
  id: string
  kind: 'section' | 'inline'
  description: string
  vars: Record<string, unknown>
}

export const EMAIL_COMPONENTS: EmailComponentEntry[] = [
  {
    id: 'HeaderL1',
    kind: 'section',
    description: 'Hero pleine largeur — image de fond + eyebrow + titre + CTA blanc.',
    vars: {
      assetOrigin: 'http://localhost:3001',
      eyebrow: 'Quarterly Letter',
      title: 'The new architecture of private assets.',
      kicker: 'Q2 · 2026 · 6 min read',
      imageUrl:
        'https://images.unsplash.com/photo-1494949360228-4e9bde560065?auto=format&fit=crop&w=1600&q=80',
      cta: { label: 'Read the letter', href: 'https://www.arquantix.com', dark: true },
    },
  },
  {
    id: 'HeaderL2',
    kind: 'section',
    description: 'Header standard — logo noir à gauche, liens nav à droite.',
    vars: {
      assetOrigin: 'http://localhost:3001',
      navLinks: [
        { label: 'Vaults', href: 'https://www.arquantix.com/vaults' },
        { label: 'Letters', href: 'https://www.arquantix.com/letters' },
        { label: 'Sign in', href: 'https://www.arquantix.com/login' },
      ],
    },
  },
  {
    id: 'HeaderL3',
    kind: 'section',
    description: 'Header minimal — logo centré sur fond gris clair.',
    vars: { assetOrigin: 'http://localhost:3001' },
  },
  {
    id: 'Footer',
    kind: 'section',
    description:
      'Footer global — fond noir, logo blanc, tagline, liens sociaux, copyright + désinscription.',
    vars: {
      assetOrigin: 'http://localhost:3001',
      tagline: 'Premium real assets, structured into transparent on-chain vaults.',
      social: [
        { label: 'LinkedIn', href: 'https://www.linkedin.com/company/arquantix' },
        { label: 'X', href: 'https://x.com/arquantix' },
      ],
      copyright: '© 2026 Arquantix SA. All rights reserved.',
      unsubscribeUrl: 'https://www.arquantix.com/unsubscribe',
      unsubscribeLabel: 'Unsubscribe',
      preferencesUrl: 'https://www.arquantix.com/preferences',
      preferencesLabel: 'Preferences',
    },
  },
  {
    id: 'TextBlock',
    kind: 'section',
    description:
      'Bloc texte éditorial — eyebrow optionnel, titre H2, paragraphes, CTA optionnel.',
    vars: {
      eyebrow: 'Letter from the desk',
      heading: 'Real assets, transparent rails.',
      paragraphs: [
        'This quarter, we crossed the threshold most allocators have been watching for years.',
        'Our Vault Builder now composes allocations across gold, emerging credit, private real estate and tokenized treasuries from a single subscription flow.',
      ],
      cta: { label: 'Read more', href: 'https://www.arquantix.com' },
    },
  },
  {
    id: 'Card',
    kind: 'section',
    description: 'Carte simple sur fond gris — eyebrow + titre + body + CTA secondaire.',
    vars: {
      eyebrow: 'Vault · #017',
      title: 'Gold Backed Yield',
      body: 'Physical bullion in LBMA vaults, 4.6% target net yield, quarterly distributions.',
      cta: { label: 'Explore vault', href: 'https://www.arquantix.com/vaults/017' },
    },
  },
  {
    id: 'TwoColumns',
    kind: 'section',
    description: 'Grille 2 colonnes de cartes (idéal pour highlights produits).',
    vars: {
      columns: [
        {
          eyebrow: 'Vault · #017',
          title: 'Gold Backed Yield',
          body: 'Physical bullion in LBMA vaults, 4.6% target net yield, quarterly distributions.',
          cta: { label: 'Explore vault', href: 'https://www.arquantix.com/vaults/017' },
        },
        {
          eyebrow: 'Exclusive Offer',
          title: 'Geneva Prime Residential',
          body: 'Co-investment in a CHF 28M residential asset, 7-year horizon.',
          cta: { label: 'See offer', href: 'https://www.arquantix.com/offers/geneva' },
        },
      ],
    },
  },
  {
    id: 'CTASection',
    kind: 'section',
    description:
      'Bloc CTA premium — variantes claire / sombre via `dark: true`, eyebrow + titre + body + bouton.',
    vars: {
      dark: true,
      eyebrow: 'On-chain Custody',
      title: 'MiCA-ready by design.',
      body: 'Segregated cold storage, weekly reserve attestations and chain-level traceability.',
      cta: { label: 'Read the attestation', href: 'https://www.arquantix.com/custody', dark: true },
    },
  },
  {
    id: 'AlertBox',
    kind: 'section',
    description:
      'Encart d’alerte — variantes warning / danger / info / success via `variant.<key>: true`.',
    vars: {
      variant: { warning: true },
      title: 'Didn’t request this?',
      body: 'If this wasn’t you, ignore this email and consider rotating your password.',
    },
  },
  {
    id: 'OTPCode',
    kind: 'section',
    description: 'Affichage centré d’un code OTP — label + code (mono) + texte d’expiration.',
    vars: {
      label: 'Your one-time code',
      code: '748391',
      expiryText: 'This code expires in 10 minutes.',
    },
  },
  {
    id: 'TransactionSummary',
    kind: 'section',
    description: 'Tableau récapitulatif (label / value) — opérations, métadonnées techniques…',
    vars: {
      title: 'Operation summary',
      rows: [
        { label: 'Reference', value: 'ARQ-2026-04-000247' },
        { label: 'Type', value: 'Subscription' },
        { label: 'Net amount', value: 'USD 24,875.00' },
      ],
    },
  },
  {
    id: 'LegalDisclaimer',
    kind: 'section',
    description: 'Bloc texte de mention légale — petite typo, gris.',
    vars: {
      body:
        'This confirmation is for information only. The legal record of your operation is the signed subscription agreement available in your client space.',
    },
  },
  {
    id: 'Signature',
    kind: 'section',
    description: 'Signature de pied de lettre — closing + nom + rôle.',
    vars: {
      closing: 'Warmly,',
      name: 'The Arquantix desk',
      role: 'Geneva · Singapore · Bali',
    },
  },
  {
    id: 'ProductHighlight',
    kind: 'section',
    description: 'Mise en avant produit — image à gauche + texte à droite + CTA.',
    vars: {
      eyebrow: 'New release',
      title: 'Vault Builder 2.0',
      body: 'Compose multi-asset allocations in seconds, with simulated performance and live custody.',
      imageUrl:
        'https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=1200&q=80',
      cta: { label: 'Try Vault Builder', href: 'https://www.arquantix.com/vault-builder', dark: true },
    },
  },
  {
    id: 'Divider',
    kind: 'section',
    description: 'Trait fin de séparation entre deux sections (auto-padding).',
    vars: {},
  },
  {
    id: 'Spacer',
    kind: 'section',
    description: 'Espacement vertical (par défaut 24 px, configurable via `height`).',
    vars: { height: '32px' },
  },
  {
    id: 'Button',
    kind: 'inline',
    description: 'Bouton principal noir / blanc (avec variante `dark: true` pour fond sombre).',
    vars: { label: 'Read more', href: 'https://www.arquantix.com', align: 'left' },
  },
  {
    id: 'SecondaryButton',
    kind: 'inline',
    description: 'Bouton secondaire (border + transparent), variante `onDark: true`.',
    vars: {
      label: 'Explore vault',
      href: 'https://www.arquantix.com',
      align: 'left',
    },
  },
  {
    id: 'Eyebrow',
    kind: 'inline',
    description: 'Petit chip surtitre (Barlow Semi-Condensed), variante `light: true` pour fond sombre.',
    vars: { label: 'Quarterly Letter', align: 'left' },
  },
]

export const EMAIL_COMPONENT_IDS = EMAIL_COMPONENTS.map((c) => c.id)

export function getEmailComponent(id: string): EmailComponentEntry | null {
  return EMAIL_COMPONENTS.find((c) => c.id === id) ?? null
}
