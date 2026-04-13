import Link from 'next/link'

type AnswerSection =
  | { type: 'p'; text: string }
  | { type: 'ul'; items: string[] }

type QATone =
  | 'red'
  | 'emerald'
  | 'cyan'
  | 'violet'
  | 'amber'
  | 'orange'
  | 'rose'
  | 'slate'

type QAEntry = {
  id: string
  numLabel: string
  emoji: string
  tone?: QATone
  question: string
  tags?: string[]
  answerIntro?: string
  sections: AnswerSection[]
  footerNote?: string
}

const TONE_LABEL: Record<QATone, string> = {
  red: 'text-red-700/90',
  emerald: 'text-emerald-800',
  cyan: 'text-cyan-900',
  violet: 'text-violet-800',
  amber: 'text-amber-900',
  orange: 'text-orange-900',
  rose: 'text-rose-800',
  slate: 'text-slate-700',
}

const TONE_NAV_HOVER =
  'hover:border-emerald-400 hover:bg-emerald-50 hover:text-emerald-950'

const ENTRIES_DIFFICILES: QAEntry[] = [
  {
    id: 'q-1',
    numLabel: '1',
    emoji: '🔴',
    question: 'Est-ce qu’on va tous être licenciés ?',
    sections: [
      {
        type: 'p',
        text: 'Oui. Dans le cadre de la procédure qui va être ouverte, l’ensemble des contrats de travail seront rompus rapidement après l’ouverture.',
      },
      {
        type: 'p',
        text: 'C’est une décision extrêmement difficile, mais elle s’impose à nous aujourd’hui.',
      },
    ],
  },
  {
    id: 'q-2',
    numLabel: '2',
    emoji: '🔴',
    question: 'Quand exactement ?',
    sections: [
      {
        type: 'p',
        text: 'Une fois la procédure ouverte, les licenciements interviennent généralement dans un délai de quelques jours.',
      },
      {
        type: 'p',
        text: 'Nous vous accompagnerons à chaque étape pour que tout soit le plus clair possible.',
      },
    ],
  },
  {
    id: 'q-3',
    numLabel: '3',
    emoji: '🔴',
    question: 'Est-ce qu’on va être payés ?',
    sections: [
      {
        type: 'p',
        text: 'Oui. Les salaires, congés payés et certaines indemnités sont pris en charge par un organisme dédié, l’AGS.',
      },
      {
        type: 'p',
        text: 'Les paiements interviennent généralement rapidement après l’ouverture de la procédure.',
      },
    ],
  },
  {
    id: 'q-4',
    numLabel: '4',
    emoji: '🔴',
    question: 'Et nos primes ?',
    sections: [
      { type: 'p', text: 'Cela dépend de leur nature et de leur période.' },
      {
        type: 'p',
        text: 'Les éléments récents peuvent être pris en charge dans certaines conditions. Les éléments plus anciens sont intégrés au passif de la société.',
      },
      {
        type: 'p',
        text: 'Nous allons vérifier chaque situation individuellement pour vous donner une réponse précise.',
      },
    ],
  },
  {
    id: 'q-5',
    numLabel: '5',
    emoji: '🔴',
    question: 'Pourquoi vous ne nous avez pas dit plus tôt ?',
    tags: ['Très sensible'],
    sections: [
      { type: 'p', text: 'C’est une question légitime.' },
      {
        type: 'p',
        text: 'Pendant des mois, nous avons essayé de résoudre la situation sans en arriver là.',
      },
      {
        type: 'p',
        text: 'Nous étions engagés dans des démarches confidentielles, notamment des procédures de conciliation, qui ne permettaient pas une communication large. Et surtout, nous avons sincèrement cru jusqu’au bout que nous pouvions éviter cette issue.',
      },
    ],
  },
  {
    id: 'q-6',
    numLabel: '6',
    emoji: '🔴',
    question: 'Qu’est-ce qui s’est passé concrètement ?',
    answerIntro: 'Réponse (clé, cadrée)',
    sections: [
      { type: 'p', text: 'Plusieurs facteurs.' },
      {
        type: 'p',
        text: 'Une pression forte sur notre trésorerie, un environnement concurrentiel exigeant, et surtout des ressources attendues qui ne sont pas arrivées.',
      },
      {
        type: 'p',
        text: 'Nous avons tenu le plus longtemps possible, mais à un moment donné, l’équilibre n’était plus tenable.',
      },
    ],
    footerNote: 'Ne pas partir en attaque frontale État ici.',
  },
  {
    id: 'q-7',
    numLabel: '7',
    emoji: '🔴',
    question: 'C’est la faute de qui ?',
    tags: ['Piège absolu'],
    sections: [
      { type: 'p', text: 'Ce n’est pas une question de faute individuelle.' },
      {
        type: 'p',
        text: 'C’est une combinaison de facteurs économiques, administratifs et de timing.',
      },
      {
        type: 'p',
        text: 'En tant que dirigeant, j’assume la responsabilité de la situation.',
      },
    ],
  },
  {
    id: 'q-8',
    numLabel: '8',
    emoji: '🔴',
    question: 'Est-ce que vous auriez pu faire autrement ?',
    sections: [
      {
        type: 'p',
        text: 'Nous avons utilisé tous les leviers disponibles : réduction des coûts, recherche de financement, développement commercial, procédures juridiques.',
      },
      {
        type: 'p',
        text: 'Avec le recul, on peut toujours se poser des questions. Mais je peux vous dire sincèrement que nous nous sommes battus jusqu’au bout.',
      },
    ],
  },
  {
    id: 'q-9',
    numLabel: '9',
    emoji: '🔴',
    question: 'Pourquoi ne pas avoir levé plus d’argent ?',
    sections: [
      {
        type: 'p',
        text: 'Nous avons levé des fonds et structuré l’entreprise pour tenir dans la durée.',
      },
      {
        type: 'p',
        text: 'Mais lever à nouveau dans un contexte dégradé, avec des incertitudes fortes, est extrêmement complexe.',
      },
      {
        type: 'p',
        text: 'Nous avons exploré ces pistes, sans succès suffisant dans les délais.',
      },
    ],
  },
  {
    id: 'q-10',
    numLabel: '10',
    emoji: '🔴',
    question: 'Est-ce que l’entreprise aurait pu être sauvée ?',
    sections: [
      {
        type: 'p',
        text: 'Oui, avec plus de temps et des ressources supplémentaires, il y avait une trajectoire possible.',
      },
      {
        type: 'p',
        text: 'Mais aujourd’hui, ces conditions ne sont plus réunies.',
      },
    ],
  },
  {
    id: 'q-11',
    numLabel: '11',
    emoji: '🔴',
    question: 'Qu’est-ce qu’on devient maintenant ?',
    sections: [
      { type: 'p', text: 'À court terme :' },
      {
        type: 'ul',
        items: [
          'accompagnement dans la procédure',
          'prise en charge des droits',
        ],
      },
      { type: 'p', text: 'Ensuite :' },
      {
        type: 'ul',
        items: [
          'possibilité de dispositifs comme le CSP',
          'de notre côté, nous allons faire le maximum pour vous accompagner dans la suite',
        ],
      },
    ],
  },
  {
    id: 'q-12',
    numLabel: '12',
    emoji: '🔴',
    question: 'Est-ce que vous allez nous aider à retrouver du travail ?',
    tags: ['Important humainement'],
    sections: [
      { type: 'p', text: 'Oui.' },
      {
        type: 'p',
        text: 'Personnellement, je m’engage à vous aider : recommandations, mise en relation, valorisation de votre travail.',
      },
      { type: 'p', text: 'Vous êtes une équipe de grande qualité.' },
    ],
  },
  {
    id: 'q-13',
    numLabel: '13',
    emoji: '🔴',
    question: 'Est-ce qu’il y aura des reprises ou transferts ?',
    sections: [
      {
        type: 'p',
        text: 'Certaines options sont à l’étude, mais rien n’est garanti à ce stade.',
      },
      {
        type: 'p',
        text: 'Si des opportunités concrètes se présentent, nous vous en informerons immédiatement.',
      },
    ],
  },
  {
    id: 'q-14',
    numLabel: '14',
    emoji: '🔴',
    question: 'Pourquoi Automata France continue et pas nous ?',
    tags: ['Très sensible'],
    sections: [
      {
        type: 'p',
        text: 'Ce sont des structures juridiques différentes, avec des situations financières et réglementaires distinctes.',
      },
      {
        type: 'p',
        text: 'Les décisions se prennent société par société.',
      },
    ],
  },
  {
    id: 'q-15',
    numLabel: '15',
    emoji: '🔴',
    question: 'Pourquoi vous êtes à Dubaï ?',
    sections: [
      {
        type: 'p',
        text: 'J’y étais pour développer l’activité commerciale et trouver des relais de croissance pour soutenir l’entreprise.',
      },
      {
        type: 'p',
        text: 'L’objectif était justement de créer des opportunités pour l’équipe.',
      },
    ],
  },
  {
    id: 'q-16',
    numLabel: '16',
    emoji: '🔴',
    question: 'Qu’est-ce qu’on doit faire maintenant ?',
    sections: [
      { type: 'p', text: 'À court terme :' },
      {
        type: 'ul',
        items: [
          'assister aux réunions',
          'suivre les communications',
          'participer à la désignation du représentant des salariés',
        ],
      },
      {
        type: 'p',
        text: 'Nous allons vous guider étape par étape.',
      },
    ],
  },
  {
    id: 'q-bonus',
    numLabel: 'Bonus',
    emoji: '🧠',
    question: 'Si quelqu’un craque / colère',
    tags: ['Réponse type'],
    sections: [
      {
        type: 'p',
        text: 'Je comprends votre réaction.',
      },
      {
        type: 'p',
        text: 'La situation est extrêmement difficile et injuste pour beaucoup d’entre vous.',
      },
      {
        type: 'p',
        text: 'On va prendre le temps de répondre à toutes les questions, une par une.',
      },
    ],
  },
]

const ENTRIES_AGS: QAEntry[] = [
  {
    id: 'ags-1',
    numLabel: 'A1',
    emoji: '💰',
    tone: 'emerald',
    question: 'Comment ça se passe pour mon salaire avec l’AGS ?',
    tags: ['Paiement rapide après ouverture (aligné doc)'],
    sections: [
      {
        type: 'p',
        text: 'L’AGS (Assurance Garantie des Salaires) prend en charge :',
      },
      {
        type: 'ul',
        items: [
          'les salaires impayés',
          'les congés payés',
          'les indemnités de licenciement',
        ],
      },
      {
        type: 'p',
        text: 'Elle intervient après l’ouverture de la procédure, et les paiements arrivent généralement rapidement, en quelques jours.',
      },
    ],
  },
  {
    id: 'ags-2',
    numLabel: 'A2',
    emoji: '💰',
    tone: 'emerald',
    question: 'Est-ce que je vais toucher 100% de mon salaire ?',
    tags: ['Plafonds légaux élevés — souvent ≈ 77k€ max selon les cas'],
    sections: [
      {
        type: 'p',
        text: 'Oui, les salaires dus sont pris en charge à 100% dans la limite de plafonds légaux.',
      },
      {
        type: 'p',
        text: 'Ces plafonds sont élevés (plusieurs dizaines de milliers d’euros), donc dans la grande majorité des cas, les salariés sont intégralement couverts.',
      },
    ],
  },
  {
    id: 'ags-3',
    numLabel: 'A3',
    emoji: '💰',
    tone: 'emerald',
    question: 'Pendant combien de temps l’AGS me paie ?',
    sections: [
      {
        type: 'p',
        text: 'L’AGS ne paie pas « dans le temps » comme un salaire mensuel.',
      },
      {
        type: 'p',
        text: 'Elle règle :',
      },
      {
        type: 'ul',
        items: [
          'les sommes dues avant la procédure',
          'et celles liées au licenciement',
        ],
      },
      {
        type: 'p',
        text: 'Ensuite, on bascule vers les dispositifs classiques : chômage ou CSP.',
      },
    ],
  },
  {
    id: 'ags-4',
    numLabel: 'A4',
    emoji: '🧾',
    tone: 'cyan',
    question: 'C’est quoi le CSP ?',
    answerIntro: 'Réponse (important)',
    sections: [
      {
        type: 'p',
        text: 'Le CSP (Contrat de Sécurisation Professionnelle) est un dispositif proposé dans ce type de situation.',
      },
      {
        type: 'p',
        text: 'Il permet :',
      },
      {
        type: 'ul',
        items: [
          'un accompagnement renforcé pour retrouver un emploi',
          'une indemnisation proche du salaire',
        ],
      },
      {
        type: 'p',
        text: 'C’est souvent la meilleure option.',
      },
    ],
  },
  {
    id: 'ags-5',
    numLabel: 'A5',
    emoji: '💰',
    tone: 'emerald',
    question: 'Combien je vais toucher avec le CSP ?',
    sections: [
      {
        type: 'p',
        text: 'En CSP :',
      },
      {
        type: 'ul',
        items: [
          'environ 75% du salaire brut (ce qui est proche du net)',
          'pendant 12 mois maximum',
        ],
      },
      {
        type: 'p',
        text: 'C’est plus avantageux que le chômage classique.',
      },
    ],
  },
  {
    id: 'ags-6',
    numLabel: 'A6',
    emoji: '💰',
    tone: 'emerald',
    question: 'Et si je refuse le CSP ?',
    sections: [
      {
        type: 'p',
        text: 'Dans ce cas, vous passez au chômage classique :',
      },
      {
        type: 'ul',
        items: [
          'environ 57% du brut',
          'durée variable selon votre ancienneté',
        ],
      },
      {
        type: 'p',
        text: 'Donc en général, le CSP est recommandé.',
      },
    ],
  },
  {
    id: 'ags-7',
    numLabel: 'A7',
    emoji: '👤',
    tone: 'violet',
    question: 'Cas 1 : salarié < 1 an d’ancienneté',
    tags: [
      'Même avec peu d’ancienneté, vous êtes bien protégés sur la transition',
    ],
    sections: [
      {
        type: 'p',
        text: 'Pas ou peu d’indemnité de licenciement.',
      },
      {
        type: 'p',
        text: 'L’AGS couvre :',
      },
      {
        type: 'ul',
        items: ['salaires dus', 'congés payés'],
      },
      {
        type: 'p',
        text: 'Ensuite :',
      },
      {
        type: 'ul',
        items: [
          'CSP possible (fortement recommandé)',
          'sinon chômage classique',
        ],
      },
    ],
  },
  {
    id: 'ags-8',
    numLabel: 'A8',
    emoji: '👤',
    tone: 'violet',
    question: 'Cas 2 : salarié > 2 ans d’ancienneté',
    tags: [
      'Situation globalement sécurisée financièrement à court terme',
    ],
    sections: [
      {
        type: 'p',
        text: 'Indemnité de licenciement légale en plus.',
      },
      {
        type: 'p',
        text: 'L’AGS prend en charge :',
      },
      {
        type: 'ul',
        items: ['salaires', 'congés', 'indemnités'],
      },
      {
        type: 'p',
        text: 'Ensuite : CSP → ~75% du salaire pendant 12 mois.',
      },
    ],
  },
  {
    id: 'ags-9',
    numLabel: 'A9',
    emoji: '👤',
    tone: 'violet',
    question: 'Cas 3 : salarié senior / salaire élevé',
    sections: [
      {
        type: 'p',
        text: 'Les montants sont plafonnés par l’AGS.',
      },
      {
        type: 'p',
        text: 'Mais les plafonds sont suffisamment élevés pour couvrir la grande majorité des cas.',
      },
      {
        type: 'p',
        text: 'Nous vérifierons chaque situation individuellement.',
      },
    ],
  },
  {
    id: 'ags-10',
    numLabel: 'A10',
    emoji: '🧠',
    tone: 'amber',
    question: 'Est-ce que je vais avoir un trou de revenu ?',
    sections: [
      {
        type: 'p',
        text: 'Normalement non.',
      },
      {
        type: 'p',
        text: 'L’AGS intervient rapidement, puis les dispositifs comme le CSP prennent le relais.',
      },
      {
        type: 'p',
        text: 'L’objectif est justement d’éviter toute rupture brutale de revenus.',
      },
    ],
  },
  {
    id: 'ags-11',
    numLabel: 'A11',
    emoji: '📅',
    tone: 'orange',
    question: 'Quand est-ce que je vais toucher l’argent ?',
    sections: [
      {
        type: 'p',
        text: 'Généralement :',
      },
      {
        type: 'ul',
        items: [
          'AGS : quelques jours après l’ouverture',
          'CSP / chômage : dans la continuité',
        ],
      },
      {
        type: 'p',
        text: 'Nous vous accompagnerons pour que tout se fasse rapidement.',
      },
    ],
  },
  {
    id: 'ags-12',
    numLabel: 'A12',
    emoji: '📑',
    tone: 'slate',
    question: 'Qu’est-ce que je dois faire concrètement ?',
    sections: [
      {
        type: 'ul',
        items: [
          'Participer aux réunions',
          'Fournir les documents si demandés',
          'Étudier l’option CSP',
        ],
      },
      {
        type: 'p',
        text: 'Et surtout : ne pas rester seul — on est là pour vous accompagner.',
      },
    ],
  },
  {
    id: 'ags-13',
    numLabel: 'A13',
    emoji: '⚠️',
    tone: 'rose',
    question: 'Est-ce qu’il y a un risque de ne pas être payé ?',
    sections: [
      {
        type: 'p',
        text: 'Non, le système est justement conçu pour protéger les salariés dans ce type de situation.',
      },
      {
        type: 'p',
        text: 'Les créances salariales sont une priorité absolue.',
      },
    ],
  },
  {
    id: 'ags-14',
    numLabel: 'A14',
    emoji: '🧠',
    tone: 'amber',
    question: 'Et mes congés payés ?',
    sections: [
      {
        type: 'p',
        text: 'Ils sont pris en charge par l’AGS comme le reste des éléments de rémunération.',
      },
    ],
  },
  {
    id: 'ags-15',
    numLabel: 'A15',
    emoji: '💬',
    tone: 'slate',
    question: 'Et mes bonus / variables ?',
    sections: [
      {
        type: 'p',
        text: 'Ça dépend :',
      },
      {
        type: 'ul',
        items: [
          'si c’est récent → souvent pris en charge',
          'si c’est ancien → inscrit au passif',
        ],
      },
      {
        type: 'p',
        text: 'On analysera au cas par cas.',
      },
    ],
  },
]

function SectionBody({ sections }: { sections: AnswerSection[] }) {
  return (
    <div className="space-y-1.5 text-[12px] leading-snug text-neutral-700">
      {sections.map((s, i) => {
        if (s.type === 'p') {
          return (
            <p key={i} className="[&:not(:first-child)]:mt-1.5">
              {s.text}
            </p>
          )
        }
        return (
          <ul
            key={i}
            className="list-disc pl-3.5 marker:text-neutral-400 space-y-0.5"
          >
            {s.items.map((item, j) => (
              <li key={j}>{item}</li>
            ))}
          </ul>
        )
      })}
    </div>
  )
}

function QACard({ entry: e }: { entry: QAEntry }) {
  const tone = e.tone ?? 'red'
  const labelClass = TONE_LABEL[tone]

  return (
    <article
      id={e.id}
      className="scroll-mt-28 rounded-md border border-neutral-200/90 bg-white p-2.5 shadow-sm ring-1 ring-black/[0.03] transition-[box-shadow] hover:shadow-md"
    >
      <div className="flex items-start gap-1.5 border-b border-neutral-100 pb-1.5">
        <span className="shrink-0 text-[10px] leading-none" aria-hidden>
          {e.emoji}
        </span>
        <div className="min-w-0 flex-1">
          <p
            className={`text-[10px] font-semibold uppercase tracking-wide ${labelClass}`}
          >
            {e.numLabel === 'Bonus'
              ? '🧠 Bonus'
              : e.numLabel.startsWith('A')
                ? `${e.emoji} ${e.numLabel}`
                : `Q. ${e.numLabel}`}
          </p>
          <h2 className="mt-0.5 text-[12px] font-semibold leading-tight text-neutral-900">
            « {e.question} »
          </h2>
          {e.tags && e.tags.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-0.5">
              {e.tags.map((t) => (
                <span
                  key={t}
                  className="rounded bg-amber-50 px-1 py-0 text-[9px] font-medium text-amber-900 ring-1 ring-amber-200/80"
                >
                  👉 {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="pt-1.5">
        <p className="mb-1 text-[9px] font-bold uppercase tracking-wider text-neutral-500">
          {e.answerIntro ? `${e.answerIntro} :` : 'Réponse :'}
        </p>
        <SectionBody sections={e.sections} />
        {e.footerNote && (
          <p className="mt-1.5 rounded bg-amber-50/90 px-1.5 py-1 text-[9px] font-medium leading-tight text-amber-950 ring-1 ring-amber-200">
            ⚠️ {e.footerNote}
          </p>
        )}
      </div>
    </article>
  )
}

export function QaSummaryView() {
  return (
    <div className="min-h-screen bg-neutral-100 text-neutral-900">
      <header className="sticky top-0 z-20 border-b border-neutral-200/80 bg-neutral-50/95 px-3 py-2 backdrop-blur supports-[backdrop-filter]:bg-neutral-50/80">
        <div className="mx-auto max-w-[1800px]">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h1 className="text-sm font-semibold tracking-tight sm:text-base">
              Q&amp;A — Questions difficiles &amp; AGS / CSP
            </h1>
            <Link
              href="/"
              className="text-[11px] text-neutral-500 underline-offset-2 hover:text-neutral-800 hover:underline"
            >
              Accueil
            </Link>
          </div>
          <p className="mt-0.5 text-[10px] text-neutral-500 sm:text-[11px]">
            Clic sur une pastille pour aller à la carte — deux blocs : RH, puis
            AGS / CSP / cas concrets.
          </p>
          <p className="mt-1.5 text-[9px] font-semibold uppercase tracking-wide text-neutral-400">
            Questions difficiles
          </p>
          <nav
            className="mt-1 flex flex-wrap gap-1"
            aria-label="Accès rapide — questions difficiles"
          >
            {ENTRIES_DIFFICILES.map((e) => (
              <a
                key={e.id}
                href={`#${e.id}`}
                className="inline-flex min-h-[1.5rem] min-w-[1.5rem] items-center justify-center rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-neutral-700 shadow-sm transition hover:border-red-300 hover:bg-red-50 hover:text-red-900"
              >
                {e.numLabel}
              </a>
            ))}
          </nav>
          <p className="mt-2 text-[9px] font-semibold uppercase tracking-wide text-neutral-400">
            AGS, CSP &amp; cas concrets
          </p>
          <nav
            className="mt-1 flex flex-wrap gap-1"
            aria-label="Accès rapide — AGS et CSP"
          >
            {ENTRIES_AGS.map((e) => (
              <a
                key={e.id}
                href={`#${e.id}`}
                className={`inline-flex min-h-[1.5rem] min-w-[1.5rem] items-center justify-center rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-neutral-700 shadow-sm transition ${TONE_NAV_HOVER}`}
              >
                {e.numLabel}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1800px] px-2 py-3 pb-8 sm:px-3">
        <h2 className="mb-2 text-[11px] font-bold uppercase tracking-wide text-neutral-500">
          Questions difficiles
        </h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
          {ENTRIES_DIFFICILES.map((e) => (
            <QACard key={e.id} entry={e} />
          ))}
        </div>

        <h2 className="mb-2 mt-6 text-[11px] font-bold uppercase tracking-wide text-emerald-800/90">
          AGS, CSP &amp; cas concrets
        </h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
          {ENTRIES_AGS.map((e) => (
            <QACard key={e.id} entry={e} />
          ))}
        </div>
      </main>
    </div>
  )
}
