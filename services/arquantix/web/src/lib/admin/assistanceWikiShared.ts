/**
 * Constantes / types du wiki MD partagés client + serveur (sans fs).
 */

export const WIKI_FAQ_CATEGORIES = [
  'savings',
  'exclusive-offers',
  'crypto',
  'aktio',
  'memberships',
  'account',
  'transfers-cards',
  'legal-compliance',
  'company',
  'business',
  'affiliate-partner',
  'b2b-agent',
  'trust-security',
  'other',
] as const

export const WIKI_NON_FAQ_DIRS = ['concepts', 'entities', 'policies'] as const

export type WikiTreeNode = {
  name: string
  path: string
  type: 'dir' | 'file'
  children?: WikiTreeNode[]
}
