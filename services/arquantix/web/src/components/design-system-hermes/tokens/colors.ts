/**
 * Design System "Hermès" — Tokens couleurs
 *
 * Source : extraction depuis https://www.hermes.com/fr/fr/
 * (bundle Angular `main.03131fe7703be59e.js`, palette `JSON.parse('…')` qui
 * expose `miscellanousColors`, `darkColors`, `beigeColors`).
 *
 * Convention de nommage : on conserve les noms d'origine du SDK Hermès
 * (`color-beige-level-N`, `color-dark-level-N`, `color-white`, etc.) pour
 * rester traçable avec leur SCSS.
 *
 * Hermès utilise une palette extrêmement réduite — l'identité repose sur :
 *   - une échelle « beige » (du `papyrus` à l'écru profond) pour les surfaces,
 *   - une échelle « dark » (5 gris) pour le texte et les surfaces sombres,
 *   - deux accents sémantiques (`Rouge H` pour erreur, vert pour validation),
 *   - le contraste pur noir / blanc pour les CTAs.
 */

export type HermesColorToken = {
  /** Nom canonique tel qu'exposé par le SDK Hermès (sans `--`). */
  name: string
  /** Valeur CSS exacte. */
  value: string
  /** Étiquette courte humaine. */
  label: string
  /** Description optionnelle (rôle, usage). */
  description?: string
}

export type HermesColorGroup = {
  id: string
  title: string
  description?: string
  tokens: HermesColorToken[]
}

/* -------------------------------------------------------------------------- */
/*  BEIGE — palette papier / surfaces principales                              */
/* -------------------------------------------------------------------------- */

export const beigeColors: HermesColorGroup = {
  id: 'beige',
  title: 'Beige',
  description:
    'Échelle papyrus / ivoire qui sert de fond principal sur hermes.com. ' +
    'Chaque niveau ajoute une touche d’ocre. La quasi-totalité du site est ' +
    'rendue sur `beige-level-2` (#fcf7f1).',
  tokens: [
    {
      name: 'color-beige-level-1',
      value: '#fffcf7',
      label: 'Beige 01 — Papyrus',
      description: 'Le plus clair. Utilisé pour des cartes posées sur `beige-2`.',
    },
    {
      name: 'color-beige-level-2',
      value: '#fcf7f1',
      label: 'Beige 02 — Ivoire',
      description: 'Fond global du site (page background par défaut).',
    },
    {
      name: 'color-beige-level-3',
      value: '#f6f1eb',
      label: 'Beige 03 — Sable',
      description: 'Surfaces secondaires : modules, séparateurs, sliders.',
    },
    {
      name: 'color-beige-level-4',
      value: '#e2d8ce',
      label: 'Beige 04 — Écru',
      description: 'Le plus profond : bordures et états hover/disabled.',
    },
  ],
}

/* -------------------------------------------------------------------------- */
/*  DARK — échelle de gris pour le texte et les surfaces sombres              */
/* -------------------------------------------------------------------------- */

export const darkColors: HermesColorGroup = {
  id: 'dark',
  title: 'Dark (gris)',
  description:
    'Cinq niveaux d’encre noire utilisés pour le texte et les surfaces sombres. ' +
    'Niveau 5 (`#2e2d2d`) est le « presque-noir » qui sert pour le corps de texte ' +
    'éditorial. Le pur `#000` est réservé aux CTAs.',
  tokens: [
    {
      name: 'color-dark-level-1',
      value: '#f5f5f5',
      label: 'Dark 01 — Brouillard',
      description: 'Fond clair neutre, séparateurs.',
    },
    {
      name: 'color-dark-level-2',
      value: '#cbcbcb',
      label: 'Dark 02 — Acier clair',
      description: 'Bordures d’input, divisers.',
    },
    {
      name: 'color-dark-level-3',
      value: '#919191',
      label: 'Dark 03 — Ardoise',
      description: 'Texte secondaire, placeholders.',
    },
    {
      name: 'color-dark-level-4',
      value: '#696969',
      label: 'Dark 04 — Graphite',
      description: 'Texte tertiaire, légendes, métadonnées.',
    },
    {
      name: 'color-dark-level-5',
      value: '#2e2d2d',
      label: 'Dark 05 — Encre',
      description: 'Texte courant éditorial (presque noir).',
    },
  ],
}

/* -------------------------------------------------------------------------- */
/*  MISC — pure neutre + sémantique                                            */
/* -------------------------------------------------------------------------- */

export const miscColors: HermesColorGroup = {
  id: 'misc',
  title: 'Neutres & sémantiques',
  description:
    'Couleurs absolues (noir, blanc) et accents sémantiques. ' +
    'Le `Rouge H` (#9d2a1e) sert exclusivement aux erreurs ; ' +
    'le vert ne sert qu’aux validations de formulaire.',
  tokens: [
    {
      name: 'color-white',
      value: '#fff',
      label: 'White',
      description: 'Pur blanc, surfaces de cartes premium et fond modal.',
    },
    {
      name: 'color-black',
      value: '#000',
      label: 'Black',
      description: 'CTAs primaires, header bar, texte renforcé.',
    },
    {
      name: 'color-error',
      value: '#9d2a1e',
      label: 'Error — Rouge H',
      description: 'Rouge brique iconique. Réservé aux messages d’erreur.',
    },
    {
      name: 'color-validation',
      value: '#34784a',
      label: 'Validation',
      description: 'Vert utilisé pour valider un champ ou confirmer une action.',
    },
  ],
}

/* -------------------------------------------------------------------------- */
/*  EXTENDED — couleurs observées dans le bundle (voile, alpha, dérivés)      */
/* -------------------------------------------------------------------------- */

export const extendedColors: HermesColorGroup = {
  id: 'extended',
  title: 'Étendues (alpha & dérivés)',
  description:
    'Couleurs présentes dans le runtime hermes.com mais hors palette officielle ' +
    'des tokens : voiles transparents pour les overlays, beiges intermédiaires ' +
    'utilisés sur les sliders et les modales.',
  tokens: [
    {
      name: 'overlay-dark-30',
      value: '#0000004d',
      label: 'Overlay 30%',
      description: 'Voile noir 30 % (modales, lightbox).',
    },
    {
      name: 'overlay-dark-80',
      value: '#000000cc',
      label: 'Overlay 80%',
      description: 'Voile noir intense (vidéos plein écran).',
    },
    {
      name: 'overlay-white-90',
      value: '#ffffffe6',
      label: 'Overlay blanc 90%',
      description: 'Bandeau blanc semi-opaque (header sur image).',
    },
    {
      name: 'beige-veil-73',
      value: '#fcf7f1ba',
      label: 'Voile beige 73%',
      description: 'Beige translucide posé sur images (mises en avant).',
    },
    {
      name: 'beige-veil-70',
      value: '#fcf7f1b3',
      label: 'Voile beige 70%',
      description: 'Variante plus douce du voile beige.',
    },
    {
      name: 'sand-mid',
      value: '#ddd3c6',
      label: 'Sable médian',
      description: 'Intermédiaire entre `beige-3` et `beige-4` (cartes).',
    },
    {
      name: 'sand-deep',
      value: '#d0c2b0',
      label: 'Sable profond',
      description: 'Bordures renforcées sur fonds beiges.',
    },
    {
      name: 'beige-veil-shadow',
      value: '#f6f1eb99',
      label: 'Voile sable 60%',
      description: 'Ombre teintée sur surfaces sable.',
    },
  ],
}

/* -------------------------------------------------------------------------- */
/*  EXPORT                                                                    */
/* -------------------------------------------------------------------------- */

/** Tous les groupes, dans l’ordre d’affichage de la page de visualisation. */
export const hermesColorGroups: HermesColorGroup[] = [
  beigeColors,
  darkColors,
  miscColors,
  extendedColors,
]
