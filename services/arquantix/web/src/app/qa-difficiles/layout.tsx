import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Q&A & discours collaborateurs',
  description:
    'Synthèse Q&R (questions difficiles, AGS, CSP), discours de réunion et Q&R format oral.',
}

export default function QaDifficilesLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
