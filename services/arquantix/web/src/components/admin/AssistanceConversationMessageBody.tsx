import type { ReactNode } from 'react'
import { VAULT_PARAGRAPH_BODY_READING_TYPO } from '@/components/design-system'
import { cn } from '@/lib/utils'

/**
 * Corps texte des messages dans la vue admin « conversation assistance » :
 * même typo éditoriale que le bloc CMS PARAGRAPH ({@link VAULT_PARAGRAPH_BODY_READING_TYPO}), sans dupliquer les classes dans une route.
 */
export function AssistanceConversationMessageBody({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn(VAULT_PARAGRAPH_BODY_READING_TYPO, 'whitespace-pre-wrap break-words', className)}>
      {children}
    </div>
  )
}
