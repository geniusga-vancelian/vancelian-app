import { Suspense } from 'react'
import { DiscoursView } from './discours-view'
import { QaDiscoursTabs } from './QaDiscoursTabs'
import { QaSummaryView } from './qa-summary'

export default function QaDifficilesPage() {
  return (
    <Suspense
      fallback={<div className="min-h-screen bg-neutral-100 text-neutral-900" />}
    >
      <QaDiscoursTabs
        qa={<QaSummaryView />}
        discours={<DiscoursView />}
      />
    </Suspense>
  )
}
