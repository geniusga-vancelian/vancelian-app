import type { ComponentType } from 'react'

/**
 * Registry `nodeId → Composant React` pour la preview DS Flutter.
 *
 * Chaque entrée associe l'`id` d'un nœud de `APP_ARBORESCENCE` (cf.
 * `src/app/admin/flutter/page.tsx`) à un composant React qui rend ce
 * nœud (page complète ou module isolé) en mock HTML/CSS.
 *
 * Les nœuds non couverts retombent côté route preview sur un
 * `<NotImplementedPlaceholder>` propre — aucun crash ni layout cassé.
 *
 * **Convention** : un node `kind: 'page'` rend une page entière (avec
 * topnav et scroll), un node `kind: 'module'` rend uniquement le module
 * isolé. Les sous-pages techniques (kind: 'subpage') ne sont en général
 * pas mockées en V1.
 */
export type PreviewNodeMeta = {
  /// Étiquette utilisée pour `NotImplementedPlaceholder` quand le composant
  /// n'est pas encore implémenté (matche le label de l'arborescence).
  label: string
}

export type PreviewEntry = {
  Component: ComponentType
  /// Permet d'override le `kind` par défaut du `PreviewCanvas` ; sinon on
  /// se fie à la convention page/module (cf. registerEntry).
  canvasKind?: 'page' | 'module'
}

export const previewRegistry: Record<string, PreviewEntry> = {}

/// Helper pour enregistrer une entrée (utilisé dans `registry.entries.ts`).
export function registerPreview(
  id: string,
  Component: ComponentType,
  canvasKind?: 'page' | 'module',
): void {
  previewRegistry[id] = { Component, canvasKind }
}

export function getPreviewEntry(nodeId: string): PreviewEntry | null {
  return previewRegistry[nodeId] ?? null
}
