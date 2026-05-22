import { typo, typoStyle, colors, spacing } from '@/lib/admin/flutter-preview/tokens'

/**
 * Placeholder rendu dans l'iframe pour les nœuds d'arborescence non encore
 * couverts par un mock dédié dans le `registry`. Doit rester visuellement
 * neutre (admin-friendly) mais cohérent avec le DS Flutter (couleurs, typo).
 */
export function NotImplementedPlaceholder({
  label,
  hint,
}: {
  label: string
  hint?: string
}) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: spacing.s4,
        padding: spacing.s8,
        minHeight: '100%',
        textAlign: 'center',
        color: colors.textPrimary,
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: 16,
          backgroundColor: colors.placeholderBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: colors.placeholderIcon,
          ...typoStyle(typo.amountSecondary),
        }}
      >
        ?
      </div>
      <div style={{ ...typoStyle(typo.headerSecondary) }}>{label}</div>
      <div
        style={{
          ...typoStyle(typo.bodySmRegular),
          color: colors.textSecondary,
          maxWidth: 260,
        }}
      >
        {hint ?? 'Aperçu détaillé à venir. Le nœud reste navigable côté arborescence.'}
      </div>
    </div>
  )
}
