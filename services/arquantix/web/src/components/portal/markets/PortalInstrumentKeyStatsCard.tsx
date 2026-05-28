'use client'

type Stat = {
  key: string
  value: string
}

type Props = {
  stats: Stat[]
}

/** Statistiques clés sidebar — handoff `.ast-sidecard`. */
export function PortalInstrumentKeyStatsCard({ stats }: Props) {
  if (stats.length === 0) return null

  return (
    <div className="ast-sidecard">
      <div className="ast-sidecard__eyebrow">Statistiques</div>
      <div className="ast-sidecard__rows">
        {stats.map((stat) => (
          <div className="ast-kv" key={stat.key}>
            <span className="ast-kv__k">{stat.key}</span>
            <span className="ast-kv__v v-tnum">{stat.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
