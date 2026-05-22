/**
 * Map `nodeId → label humain` extraite de `APP_ARBORESCENCE` (cf.
 * `src/app/admin/flutter/page.tsx`). Sert au `NotImplementedPlaceholder` rendu
 * dans l'iframe : pas d'accès à l'arborescence côté admin → on duplique les
 * labels ici (à resync si l'arborescence évolue).
 */
export const NODE_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  'dashboard-navbar': 'Navbar (top)',
  'dashboard-header': 'Header: Balance + Line chart + Buttons',
  'dashboard-body': 'Body content',
  'dashboard-widget-account': 'Widget: My account',
  'dashboard-widget-exclusive': 'Widget: Exclusive offers',
  'dashboard-widget-news': 'Widget: News à la Une',
  'dashboard-widget-news-analysis': 'Widget: News Analyses',

  offers: 'Offers',
  'offers-widget-saving-vaults': 'Widget: Saving Vaults',
  'offers-categories': 'Module: catégories d’investissement',
  'offers-exclusive': 'Module: top exclusive offers',

  'all-transactions': 'All transactions',
  'all-transactions-header': 'Header: back + title centered',
  'all-transactions-tabs': 'Tabs: months (filter)',
  'all-transactions-body': 'Body: transactions list',

  'euro-account': 'Compte Euro',
  'euro-account-navbar': 'Navbar Euro',
  'euro-account-header': 'Header Euro',
  'euro-account-body': 'Body Euro',
  'euro-account-marketing': 'Widget: Marketing cards',
  'euro-account-transactions': 'Module: Transactions latest 10',

  'transaction-detail': 'Transaction details',
  'transaction-detail-header': 'Header transaction',
  'transaction-detail-identity': 'Identity transaction',
  'transaction-detail-actions': 'Actions transaction',
  'transaction-detail-details-card': 'Details card',
  'transaction-detail-recap': 'Recap',

  home: 'Homepage',
  'news-a-la-une': 'Module blog_a_la_une',
  'offers-carousel': 'Module offres exclusives',

  projet: 'Page projet',
  'projet-modules': 'Sous-page: modules projet',
  'module-table-info': 'Widget: Table information',
  'module-competitive-advantages': 'Widget: Competitive advantages',
  'module-steps-date': 'Widget: Steps date',
  'module-faq': 'FAQ',
  'module-allocation': 'Portfolio allocation',
  'module-project-news': 'Project news',

  article: 'Page article / blog',
  'article-body': 'Sous-page: contenu article',
  'article-media': 'Bloc media',
}

export function getNodeLabel(nodeId: string): string {
  return NODE_LABELS[nodeId] ?? nodeId
}

/// Détermine si le rendu doit être en `page` (full canvas) ou `module` (isolé).
/// Convention : tout id commençant par `…widget-…`, `module-…` ou contenant
/// `-widget-` est traité comme module isolé. Sinon : page complète.
export function inferCanvasKind(nodeId: string): 'page' | 'module' {
  if (nodeId.startsWith('module-')) return 'module'
  if (nodeId.includes('-widget-')) return 'module'
  if (nodeId === 'news-a-la-une' || nodeId === 'offers-carousel') return 'module'
  if (nodeId === 'article-media') return 'module'
  return 'page'
}
