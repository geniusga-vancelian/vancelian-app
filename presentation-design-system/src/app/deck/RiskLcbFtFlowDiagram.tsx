/**
 * Schéma logique : critères → points → risk score → décisions LCB-FT.
 * Réutilise la palette indigo du design system (#4F46E5).
 */
export function RiskLcbFtFlowDiagram({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 920 520"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Schéma : critères LCB-FT, cumul des points, risk score et décisions"
    >
      <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#4F46E5" />
        </marker>
        <linearGradient id="boxGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4F46E5" stopOpacity="0.12" />
          <stop offset="100%" stopColor="#4F46E5" stopOpacity="0.04" />
        </linearGradient>
      </defs>

      <rect x="0" y="0" width="920" height="520" rx="16" fill="#fafafa" stroke="#e5e5e5" />

      <g fontFamily="Geist, system-ui, sans-serif">
        <rect x="40" y="200" width="200" height="120" rx="12" fill="url(#boxGrad)" stroke="#4F46E5" strokeWidth="2" />
        <text x="140" y="235" textAnchor="middle" fill="#1e1c1b" fontSize="15" fontWeight="700">
          Critères LCB-FT
        </text>
        <text x="140" y="258" textAnchor="middle" fill="#5c5c5c" fontSize="12">
          Identité, pays, listes,
        </text>
        <text x="140" y="275" textAnchor="middle" fill="#5c5c5c" fontSize="12">
          secteur, revenus, PEP…
        </text>
        <text x="140" y="300" textAnchor="middle" fill="#4F46E5" fontSize="11" fontWeight="600">
          (grille Excel)
        </text>

        <line x1="240" y1="260" x2="300" y2="260" stroke="#4F46E5" strokeWidth="2" markerEnd="url(#arrowhead)" />

        <rect x="300" y="200" width="200" height="120" rx="12" fill="url(#boxGrad)" stroke="#4F46E5" strokeWidth="2" />
        <text x="400" y="240" textAnchor="middle" fill="#1e1c1b" fontSize="15" fontWeight="700">
          Points par critère
        </text>
        <text x="400" y="265" textAnchor="middle" fill="#5c5c5c" fontSize="12">
          Barème gravité
        </text>
        <text x="400" y="285" textAnchor="middle" fill="#5c5c5c" fontSize="11">
          (faible → inacceptable)
        </text>

        <line x1="500" y1="260" x2="560" y2="260" stroke="#4F46E5" strokeWidth="2" markerEnd="url(#arrowhead)" />

        <rect x="560" y="185" width="200" height="150" rx="12" fill="#4F46E5" fillOpacity="0.95" stroke="#312e81" strokeWidth="2" />
        <text x="660" y="235" textAnchor="middle" fill="white" fontSize="16" fontWeight="700">
          Risk score global
        </text>
        <text x="660" y="260" textAnchor="middle" fill="white" fontSize="12" opacity="0.95">
          Somme des points
        </text>
        <text x="660" y="285" textAnchor="middle" fill="white" fontSize="11" opacity="0.9">
          Seuils : 0-499 / 500-799 /
        </text>
        <text x="660" y="302" textAnchor="middle" fill="white" fontSize="11" opacity="0.9">
          800-1799 / ≥ 1800
        </text>

        <text x="460" y="95" textAnchor="middle" fill="#1e1c1b" fontSize="18" fontWeight="700">
          Chaîne décisionnelle LCB-FT
        </text>
        <text x="460" y="118" textAnchor="middle" fill="#6b6b6b" fontSize="13">
          D’après la cartographie risques (classification qualitative, nov. 2025)
        </text>

        <rect x="80" y="380" width="200" height="88" rx="10" fill="#fee2e2" stroke="#dc2626" strokeWidth="1.5" />
        <text x="180" y="412" textAnchor="middle" fill="#991b1b" fontSize="13" fontWeight="700">
          Refus / rupture
        </text>
        <text x="180" y="432" textAnchor="middle" fill="#7f1d1d" fontSize="11">
          Score ≥ 1800 ou critères
        </text>
        <text x="180" y="448" textAnchor="middle" fill="#7f1d1d" fontSize="11">
          réglementaires bloquants
        </text>

        <rect x="360" y="380" width="200" height="88" rx="10" fill="#fef3c7" stroke="#d97706" strokeWidth="1.5" />
        <text x="460" y="412" textAnchor="middle" fill="#92400e" fontSize="13" fontWeight="700">
          Vigilance renforcée
        </text>
        <text x="460" y="432" textAnchor="middle" fill="#78350f" fontSize="11">
          PPE, listes, ambiguïtés…
        </text>
        <text x="460" y="448" textAnchor="middle" fill="#78350f" fontSize="11">
          Escalade analyse N2
        </text>

        <rect x="640" y="380" width="200" height="88" rx="10" fill="#dcfce7" stroke="#16a34a" strokeWidth="1.5" />
        <text x="740" y="412" textAnchor="middle" fill="#166534" fontSize="13" fontWeight="700">
          Vigilance standard
        </text>
        <text x="740" y="432" textAnchor="middle" fill="#14532d" fontSize="11">
          Dossier complet, pays
        </text>
        <text x="740" y="448" textAnchor="middle" fill="#14532d" fontSize="11">
          & profil maîtrisés
        </text>

        <line x1="660" y1="335" x2="180" y2="380" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowhead)" />
        <line x1="660" y1="335" x2="460" y2="380" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowhead)" />
        <line x1="660" y1="335" x2="740" y2="380" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowhead)" />
      </g>
    </svg>
  );
}
