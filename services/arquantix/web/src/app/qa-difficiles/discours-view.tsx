import type { ReactNode } from 'react'

const SPEECH_TOC: { id: string; label: string }[] = [
  { id: 'd-intro', label: 'Intro' },
  { id: 'd-contexte', label: 'Contexte' },
  { id: 'd-point-cle', label: 'Point clé' },
  { id: 'd-reconnaissance', label: 'Reconnaissance' },
  { id: 'd-realite', label: 'Réalité' },
  { id: 'd-suite', label: 'Ce qui va se passer' },
  { id: 'd-delegue', label: 'Délégué' },
  { id: 'd-humain', label: 'Posture' },
  { id: 'd-conclusion', label: 'Conclusion' },
  { id: 'd-transition', label: '→ Q&R' },
  { id: 'd-oral', label: 'Q&R oral' },
]

const ORAL_QA: {
  id: string
  q: string
  blocks: string[]
  bullets?: string[]
  afterBullets?: string[]
}[] = [
  {
    id: 'd-o1',
    q: 'Est-ce qu’on va être licenciés ?',
    blocks: [
      'Oui.',
      'Dans le cadre de la procédure, les contrats seront rompus rapidement après l’ouverture.',
    ],
  },
  {
    id: 'd-o2',
    q: 'Est-ce qu’on va être payés ?',
    blocks: [
      'Oui.',
      'Les salaires, congés et indemnités sont pris en charge par l’AGS.',
      'Les paiements arrivent généralement rapidement.',
    ],
  },
  {
    id: 'd-o3',
    q: 'Qu’est-ce qu’on doit faire maintenant ?',
    blocks: ['À court terme :'],
    bullets: [
      'participer aux réunions',
      'participer à l’élection du délégué',
      'suivre les communications',
    ],
    afterBullets: ['On va vous guider étape par étape.'],
  },
  {
    id: 'd-o4',
    q: 'Pourquoi on n’a pas été informés plus tôt ?',
    blocks: [
      'Nous étions engagés dans des démarches confidentielles pour tenter de sauver l’entreprise.',
      'Et nous avons sincèrement cru jusqu’au bout que c’était possible.',
    ],
  },
  {
    id: 'd-o5',
    q: 'Est-ce que vous allez nous aider ?',
    blocks: [
      'Oui.',
      'Personnellement, je m’engage à vous aider : recommandations, mise en relation, accompagnement.',
    ],
  },
  {
    id: 'd-o6',
    q: 'C’est quoi le rôle du délégué exactement ?',
    blocks: [
      'Vérifier que tout ce qui vous est dû est correctement pris en compte : salaires, congés, indemnités.',
      'C’est une protection importante pour vous.',
    ],
  },
  {
    id: 'd-o7',
    q: 'Est-ce que je vais avoir un revenu après ?',
    blocks: [
      'Oui.',
      'Il y a des dispositifs comme le CSP qui permettent de garder un niveau de revenu proche du salaire pendant un certain temps.',
    ],
  },
]

function Prose({ children }: { children: ReactNode }) {
  return (
    <div className="space-y-3 text-[13px] leading-relaxed text-neutral-800">
      {children}
    </div>
  )
}

export function DiscoursView() {
  return (
    <div className="text-neutral-900">
      <header className="sticky top-14 z-30 border-b border-neutral-200/80 bg-neutral-50/95 px-3 py-2 backdrop-blur supports-[backdrop-filter]:bg-neutral-50/80">
        <div className="mx-auto max-w-3xl">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
            Navigation
          </p>
          <nav
            className="mt-1 flex flex-wrap gap-1"
            aria-label="Sections du discours"
          >
            {SPEECH_TOC.map((t) => (
              <a
                key={t.id}
                href={`#${t.id}`}
                className="rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-neutral-700 shadow-sm transition hover:border-neutral-400 hover:bg-neutral-50"
              >
                {t.label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <article className="mx-auto max-w-3xl px-3 py-5 pb-12">
        <h1
          id="d-intro"
          className="scroll-mt-36 text-lg font-bold tracking-tight text-neutral-900 sm:text-xl"
        >
          🎤 Discours collaborateurs (version finale)
        </h1>

        <Prose>
          <p>Bonjour à toutes et à tous,</p>
          <p>Merci d’être présents aujourd’hui.</p>
          <p>
            Je vais être très direct avec vous, parce que vous méritez la
            vérité.
          </p>
          <p>
            Nous sommes aujourd’hui contraints d’envisager l’ouverture imminente
            d’une procédure judiciaire concernant Automata AI.
          </p>
          <p>
            C’est extrêmement difficile à dire, et encore plus difficile à
            vivre.
          </p>
        </Prose>

        <hr className="my-8 border-neutral-200" />

        <section id="d-contexte" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            🧠 Contexte
          </h2>
          <Prose>
            <p>
              Depuis des mois — et même des années — nous nous battons pour
              éviter cette situation.
            </p>
            <p>Nous avons utilisé tous les leviers possibles :</p>
            <ul className="list-disc space-y-1 pl-5 marker:text-neutral-400">
              <li>réduction des coûts</li>
              <li>procédures de conciliation</li>
              <li>recherche de financements</li>
              <li>développement commercial, notamment à l’international</li>
            </ul>
            <p>
              Nous avons tenu beaucoup plus longtemps que ce que la situation
              aurait normalement permis.
            </p>
          </Prose>
        </section>

        <hr className="my-8 border-neutral-200" />

        <section id="d-point-cle" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            💥 Point clé
          </h2>
          <Prose>
            <p>
              Une partie importante de notre équilibre reposait sur des
              financements attendus, notamment le Crédit Impôt Recherche.
            </p>
            <p>Nous l’avons obtenu en 2022.</p>
            <p>
              Mais ceux de 2023, 2024, et aujourd’hui 2025 — représentant plus
              d’un million d’euros — n’ont jamais été versés.
            </p>
            <p>
              Malgré de nombreuses relances, contrôles, échanges… nous n’avons
              pas obtenu ces ressources.
            </p>
            <p>Et sans ces moyens, nous ne pouvions plus continuer.</p>
          </Prose>
        </section>

        <hr className="my-8 border-neutral-200" />

        <section id="d-reconnaissance" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            ❤️ Reconnaissance
          </h2>
          <Prose>
            <p>Avant tout, je veux vous dire merci.</p>
            <p>Vous avez été une équipe exceptionnelle.</p>
            <p>
              Peu de turnover, beaucoup d’engagement, une vraie cohésion.
            </p>
            <p>
              Vous avez construit quelque chose de réel, de solide, de
              technologiquement avancé.
            </p>
            <p>Et ça, personne ne pourra vous l’enlever.</p>
          </Prose>
        </section>

        <hr className="my-8 border-neutral-200" />

        <section id="d-realite" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            ⚖️ Réalité
          </h2>
          <Prose>
            <p>Aujourd’hui, la situation ne nous permet plus de continuer.</p>
            <p>
              Et en tant que dirigeant, j’assume pleinement cette réalité.
            </p>
          </Prose>
        </section>

        <hr className="my-8 border-neutral-200" />

        <section id="d-suite" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            📄 Ce qui va se passer
          </h2>
          <Prose>
            <p>Dans les prochains jours :</p>
            <ul className="list-disc space-y-1 pl-5 marker:text-neutral-400">
              <li>une procédure judiciaire va être ouverte</li>
              <li>
                les contrats de travail seront rompus rapidement après cette
                ouverture
              </li>
              <li>
                les salaires et indemnités seront pris en charge dans le cadre
                légal
              </li>
            </ul>
            <p>Nous allons vous accompagner à chaque étape.</p>
          </Prose>
        </section>

        <hr className="my-8 border-neutral-200" />

        <section id="d-delegue" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            🗳️ Point important : délégué du personnel
          </h2>
          <Prose>
            <p>
              Dans ce cadre, il y a une étape importante à organiser dès
              maintenant.
            </p>
            <p>Nous devons désigner un délégué du personnel.</p>
            <p className="font-medium text-neutral-900">
              👉 Son rôle est très précis :
            </p>
            <ul className="list-disc space-y-1 pl-5 marker:text-neutral-400">
              <li>représenter les salariés lors de l’audience d’ouverture</li>
              <li>
                vérifier que les salaires, congés payés, indemnités et créances
                sont correctement pris en compte
              </li>
              <li>
                s’assurer qu’il n’y a pas d’erreurs dans les montants dus
              </li>
            </ul>
            <p className="font-medium text-neutral-900">
              👉 Ce n’est pas une élection classique :
            </p>
            <ul className="list-disc space-y-1 pl-5 marker:text-neutral-400">
              <li>il s’agit d’une désignation spécifique à cette procédure</li>
              <li>le vote doit être formalisé</li>
              <li>
                nous allons organiser cela ensemble juste après cette réunion
              </li>
            </ul>
            <p>C’est une étape importante pour garantir vos droits.</p>
          </Prose>
        </section>

        <hr className="my-8 border-neutral-200" />

        <section id="d-humain" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            🤝 Posture humaine
          </h2>
          <Prose>
            <p>Je sais que c’est brutal.</p>
            <p>Je sais que c’est injuste pour beaucoup d’entre vous.</p>
            <p>Et je veux que vous sachiez une chose :</p>
            <p>
              Nous nous sommes battus jusqu’au bout pour éviter ce moment.
            </p>
          </Prose>
        </section>

        <hr className="my-8 border-neutral-200" />

        <section id="d-conclusion" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            💬 Conclusion
          </h2>
          <Prose>
            <p>Ce projet s’arrête aujourd’hui.</p>
            <p>Mais ce que vous avez construit ne disparaît pas.</p>
            <p>Vous avez de la valeur.</p>
            <p>
              Et je serai personnellement impliqué pour vous accompagner dans la
              suite.
            </p>
            <p>Merci pour tout.</p>
            <p>Vraiment.</p>
          </Prose>
        </section>

        <hr className="my-8 border-neutral-200" />

        <section id="d-transition" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            💥 Transition vers Q&amp;A (à dire)
          </h2>
          <Prose>
            <p>
              Je vais maintenant répondre à vos questions avec transparence.
            </p>
            <p>
              Si je ne peux pas répondre sur un point précis, je vous le dirai.
            </p>
          </Prose>
        </section>

        <hr className="my-8 border-neutral-200" />

        <section id="d-oral" className="scroll-mt-36">
          <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600">
            ❓ Q&amp;A clés à intégrer (format oral)
          </h2>
          <p className="mt-2 text-[11px] text-neutral-500">
            Rappels courts — même page, lecture rapide.
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {ORAL_QA.map((item) => (
              <div
                key={item.id}
                id={item.id}
                className="scroll-mt-36 rounded-md border border-neutral-200 bg-white p-3 shadow-sm ring-1 ring-black/[0.03]"
              >
                <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-800">
                  ❓ {item.q}
                </p>
                <div className="mt-2 space-y-1.5 text-[12px] leading-snug text-neutral-700">
                  {item.blocks.map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                  {item.bullets && item.bullets.length > 0 && (
                    <ul className="list-disc space-y-0.5 pl-3.5 marker:text-neutral-400">
                      {item.bullets.map((b, i) => (
                        <li key={i}>{b}</li>
                      ))}
                    </ul>
                  )}
                  {item.afterBullets?.map((line, i) => (
                    <p key={`a-${i}`}>{line}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </article>
    </div>
  )
}
