'use client'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

export function VaultMarkdownBottomModuleEditor({ content, onPatch }: Props) {
  const markdown = typeof content.markdown === 'string' ? content.markdown : ''
  return (
    <div className="mt-2 space-y-2 border-t border-gray-100 pt-3">
      <label className="block text-xs font-medium text-gray-700">Markdown (mentions, liens)</label>
      <textarea
        value={markdown}
        onChange={(e) => onPatch({ markdown: e.target.value })}
        rows={8}
        className="w-full rounded-md border px-2 py-1.5 font-mono text-xs"
        placeholder="Texte légal… [Conditions](https://…)"
      />
    </div>
  )
}
