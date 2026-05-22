import { PreviewCanvas } from '@/components/admin/flutter-preview/PreviewCanvas'
import { NotImplementedPlaceholder } from '@/components/admin/flutter-preview/NotImplementedPlaceholder'
import { getPreviewEntry } from '@/lib/admin/flutter-preview/registry'
import {
  getNodeLabel,
  inferCanvasKind,
} from '@/lib/admin/flutter-preview/nodeLabels'

/// Charge l'enregistrement effectif des composants — l'import provoque
/// l'exécution des `registerPreview(...)` de chaque composant mock.
import '@/lib/admin/flutter-preview/registry.entries'

/**
 * Route iframe : `/admin/flutter/preview/[nodeId]`.
 *
 * - Lit le `nodeId` de l'URL et regarde le composant correspondant dans le
 *   `previewRegistry`.
 * - Si trouvé : rend dans un `PreviewCanvas` avec `kind` adapté (page/module).
 * - Sinon : `NotImplementedPlaceholder` clair côté UX.
 *
 * Cette page est consommée **uniquement** dans une iframe (cf.
 * `DeviceFrame`). Le layout admin parent saute la sidebar quand le path
 * commence par `/admin/flutter/preview` (cf. `app/admin/layout.tsx`).
 */
export default function FlutterPreviewNodePage({
  params,
}: {
  params: { nodeId: string }
}) {
  const nodeId = params.nodeId
  const entry = getPreviewEntry(nodeId)
  const label = getNodeLabel(nodeId)
  const canvasKind = entry?.canvasKind ?? inferCanvasKind(nodeId)

  if (!entry) {
    return (
      <PreviewCanvas kind="module">
        <NotImplementedPlaceholder label={label} />
      </PreviewCanvas>
    )
  }

  const Component = entry.Component
  return (
    <PreviewCanvas kind={canvasKind}>
      <Component />
    </PreviewCanvas>
  )
}
