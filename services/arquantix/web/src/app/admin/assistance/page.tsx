import { AgentArchitectureExplorer } from '@/components/admin/AgentArchitectureExplorer'

/**
 * Hub admin — architecture du robo-agent (router, experts, sous-agents)
 * et lien vers les fichiers de prompts Markdown.
 */
export default function AdminAssistanceArchitecturePage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Assistance — architecture des agents
        </h1>
        <p className="max-w-3xl text-sm text-slate-600">
          Vue d’ensemble du routeur LLM, des experts et des sous-agents compliance.
          Cliquez un nœud pour les chemins de décision et les boutons « prompts » pour
          ouvrir les fichiers Markdown côté dépôt (lecture via API admin).
        </p>
      </header>
      <AgentArchitectureExplorer />
    </div>
  )
}
