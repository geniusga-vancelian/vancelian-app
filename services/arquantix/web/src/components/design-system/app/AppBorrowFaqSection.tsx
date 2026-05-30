'use client'

import { useState } from 'react'

const FAQ_ITEMS = [
  {
    q: "Qu'est-ce qu'une avance de liquidité ?",
    a: 'Vous empruntez des USDC en mettant votre Bitcoin ou votre Ethereum en garantie sur Morpho. Vous recevez les fonds sur votre wallet sans vendre vos cryptos, qui restent les vôtres.',
  },
  {
    q: 'Comment se rembourse mon emprunt ?',
    a: "La crypto mise en gage génère un intérêt qui rembourse petit à petit la somme empruntée. Votre dette diminue d'elle-même au fil du temps. Vous pouvez aussi rembourser tout ou partie quand vous le souhaitez, sans frais.",
  },
  {
    q: 'Que se passe-t-il si le cours de ma garantie baisse ?',
    a: "Si la valeur de votre garantie chute trop, une partie est automatiquement vendue pour rembourser l'emprunt : c'est la liquidation. Une alerte vous est envoyée bien avant ce seuil pour vous laisser réagir.",
  },
  {
    q: 'Y a-t-il des frais ?',
    a: "Vancelian ne prélève aucun frais d'ouverture. Les seuls coûts sont le taux d'intérêt variable du marché Morpho et les frais de réseau (gas).",
  },
  {
    q: "Qu'est-ce que Morpho ?",
    a: "Morpho est un protocole de prêt décentralisé, européen et audité, utilisé par des institutions. C'est lui qui sécurise votre garantie et votre emprunt, indépendamment de Vancelian.",
  },
] as const

function BorrowFaqRow({
  question,
  answer,
  open,
  onToggle,
}: {
  question: string
  answer: string
  open: boolean
  onToggle: () => void
}) {
  if (open) {
    return (
      <div className="faq__row is-open" onClick={onToggle} onKeyDown={undefined} role="button" tabIndex={0}>
        <div className="faq__head">
          <h3 className="faq__title">{question}</h3>
          <span className="faq__toggle" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14" />
            </svg>
          </span>
        </div>
        <p className="faq__body">{answer}</p>
      </div>
    )
  }

  return (
    <div className="faq__row" onClick={onToggle} onKeyDown={undefined} role="button" tabIndex={0}>
      <h3 className="faq__title">{question}</h3>
      <span className="faq__toggle" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </span>
    </div>
  )
}

/** FAQ emprunts — handoff `BorrowFaq` (`.ofd-section` · `.faq`). */
export function AppBorrowFaqSection() {
  const [openIndex, setOpenIndex] = useState(0)

  return (
    <section className="ofd-section">
      <header className="ofd-section__head">
        <h2 className="ofd-section__title">Questions fréquentes</h2>
      </header>
      <div className="faq">
        {FAQ_ITEMS.map((item, index) => (
          <BorrowFaqRow
            key={item.q}
            question={item.q}
            answer={item.a}
            open={openIndex === index}
            onToggle={() => setOpenIndex(openIndex === index ? -1 : index)}
          />
        ))}
      </div>
    </section>
  )
}
