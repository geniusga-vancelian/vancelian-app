import type { ReactNode } from 'react'
import { Container } from '@/components/ui/Container'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
}

/**
 * Conteneur de page portail — réutilise le même `<Container>` DS que le site public
 * (`FaqSection`, modules CMS, footer).
 */
export function PortalPageContainer({ children, className }: Props) {
  return <Container className={cn('py-10 lg:py-16', className)}>{children}</Container>
}
