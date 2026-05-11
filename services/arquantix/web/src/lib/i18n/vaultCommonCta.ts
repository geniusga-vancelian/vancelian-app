/**
 * Libellés CTA / UI mutualisés pour le rendu public des modules Vault (web).
 * Convention : préférer une prop CMS par module quand le libellé est du contenu ;
 * sinon utiliser ces clés stables avec `vaultCommonCta(locale, key)`.
 *
 * Locales alignées sur `config/locales` : fr, en, it.
 */
import type { Locale } from '@/config/locales'
import { buildCommonCtaLookup } from '@/lib/i18n/commonCtaRegistry'

const FR = {
  download: 'Télécharger',
  learn_more: 'En savoir plus',
  invest: 'Investir',
  view_details: 'Voir le détail',
  read_more: 'Lire la suite',
  get_started: 'Commencer',
  open_document: 'Ouvrir le document',
  contact_us: 'Nous contacter',
  map: 'Carte',
  watch_video: 'Lire la vidéo',
  watch_video_youtube: 'Lire la vidéo YouTube',
  video_iframe_fallback: 'Vidéo YouTube',
  map_embed_invalid:
    "Impossible d'afficher la carte : URL d'intégration invalide (attendu : /maps/embed ou output=embed).",
  virtual_tour: 'Visite panoramique',
  virtual_tour_embed_invalid:
    "Impossible d'afficher la visite virtuelle : URL invalide (attendu : lien https vers le viewer).",
  funding_funded: 'Financé',
  funding_rate: 'Taux',
  funding_total: 'Total',
  vault_no_content: 'Aucun contenu pour le moment.',
} as const

export type VaultCommonCtaKey = keyof typeof FR

const EN = {
  download: 'Download',
  learn_more: 'Learn more',
  invest: 'Invest',
  view_details: 'View details',
  read_more: 'Read more',
  get_started: 'Get started',
  open_document: 'Open document',
  contact_us: 'Contact us',
  map: 'Map',
  watch_video: 'Watch video',
  watch_video_youtube: 'Watch YouTube video',
  video_iframe_fallback: 'YouTube video',
  map_embed_invalid:
    'Unable to display the map: invalid embed URL (expected: /maps/embed or output=embed).',
  virtual_tour: 'Virtual tour',
  virtual_tour_embed_invalid:
    'Unable to display the virtual tour: invalid URL (expected: https link to the viewer).',
  funding_funded: 'Funded',
  funding_rate: 'Rate',
  funding_total: 'Total',
  vault_no_content: 'No content available yet.',
} as const

const IT = {
  download: 'Scarica',
  learn_more: 'Scopri di più',
  invest: 'Investi',
  view_details: 'Vedi dettagli',
  read_more: 'Leggi di più',
  get_started: 'Inizia',
  open_document: 'Apri documento',
  contact_us: 'Contattaci',
  map: 'Mappa',
  watch_video: 'Guarda il video',
  watch_video_youtube: 'Guarda il video su YouTube',
  video_iframe_fallback: 'Video YouTube',
  map_embed_invalid:
    'Impossibile mostrare la mappa: URL di incorporamento non valido (atteso: /maps/embed o output=embed).',
  virtual_tour: 'Tour virtuale',
  virtual_tour_embed_invalid:
    'Impossibile mostrare la visita virtuale: URL non valido (atteso: link https al viewer).',
  funding_funded: 'Finanziato',
  funding_rate: 'Tasso',
  funding_total: 'Totale',
  vault_no_content: 'Nessun contenuto disponibile.',
} as const

type CtaTable = Record<VaultCommonCtaKey, string>

const BY_LOCALE: Record<Locale, CtaTable> = {
  fr: FR as unknown as CtaTable,
  en: EN as unknown as CtaTable,
  it: IT as unknown as CtaTable,
}

export const VAULT_COMMON_CTA_KEYS = [
  'download',
  'learn_more',
  'invest',
  'view_details',
  'read_more',
  'get_started',
  'open_document',
  'contact_us',
  'map',
  'watch_video',
  'watch_video_youtube',
  'video_iframe_fallback',
  'map_embed_invalid',
  'virtual_tour',
  'virtual_tour_embed_invalid',
  'funding_funded',
  'funding_rate',
  'funding_total',
  'vault_no_content',
] as const satisfies readonly VaultCommonCtaKey[]

export const vaultCommonCta = buildCommonCtaLookup<typeof FR>({
  fr: FR,
  byLocale: BY_LOCALE,
})
