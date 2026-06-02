'use client'

import { useState } from 'react'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { TransactionTechnicalDetailsRow } from '@/components/portal/transaction/types'

type Props = {
  rows: TransactionTechnicalDetailsRow[]
  title?: string
}

/** Panneau repliable — hash, contrat, réseau (canon R4.5-A.1). */
export function TransactionTechnicalDetails({
  rows,
  title = 'Détails techniques',
}: Props) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        className={`inv-tech-toggle${open ? ' is-open' : ''}`}
        onClick={() => setOpen((v) => !v)}
      >
        {title}
        <span className="inv-tech-toggle__arrow" aria-hidden="true">
          <KalaiIcon name="chevron-down" size={16} />
        </span>
      </button>
      {open ? (
        <div className="inv-tech">
          {rows.map((row) => (
            <div className="inv-tech__row" key={row.label}>
              <span className="inv-tech__k">{row.label}</span>
              <span className="inv-tech__v">{row.value}</span>
            </div>
          ))}
        </div>
      ) : null}
    </>
  )
}
