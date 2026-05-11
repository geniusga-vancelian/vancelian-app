/**
 * Modèle d'architecture affiché dans l'admin (assistance multi-agents).
 * Aligné sur `services/assistance/agents/*` et `prompts/*.md`.
 *
 * Les chemins `promptFile` sont relatifs à `api/services/assistance/prompts/`.
 */

export type AgentArchKind =
  | 'orchestrator'
  | 'dispatcher'
  | 'expert'
  | 'subagent'
  | 'internal'
  | 'memory'

export type AgentArchPromptRef = {
  /** Chemin relatif sous `prompts/` */
  file: string
  /** Rôle du fichier pour l'UI */
  label: string
}

export type AgentArchitectureNode = {
  id: string
  title: string
  description: string
  kind: AgentArchKind
  /** Fichiers markdown sources du comportement */
  prompts: AgentArchPromptRef[]
  /**
   * Branches / tools / options pertinentes (texte admin, pas un schéma OpenAI).
   */
  routingOrChoices: string[]
  children?: AgentArchitectureNode[]
}

/** Fragment injecté automatiquement pour les agents listés côté `prompt_builder`. */
export const RESPONSE_FRAMEWORK_FILE = '_response_framework.md'

export const RESPONSE_FRAMEWORK_AGENTS_LABEL =
  'default, advisor, product, market, trust, compliance.registration, compliance.transactional, compliance.general, compliance.remediation'

const frameworkAppend: AgentArchPromptRef = {
  file: RESPONSE_FRAMEWORK_FILE,
  label: 'Auto-injecté en fin de system prompt (Response Framework v4)',
}

function withFramework(
  base: AgentArchPromptRef[],
  agentInWhitelist: boolean
): AgentArchPromptRef[] {
  if (!agentInWhitelist) return base
  return [...base, frameworkAppend]
}

export const AGENT_ARCHITECTURE_TREE: AgentArchitectureNode[] = [
  {
    id: 'router',
    title: 'Router LLM',
    kind: 'orchestrator',
    description:
      'Premier cerveau du tour : function-calling OpenAI. Ne parle pas au client ; choisit un expert ou demande une clarification / recentrage.',
    prompts: [{ file: 'router_system.md', label: 'Prompt système routeur' }],
    routingOrChoices: [
      'Tool `route_to` → agent expert (compliance, advisor, product, market, trust, default) avec confidence + reasoning.',
      'Tool `ask_clarification` → QCM (prompt + options avec agent_hint) si le sujet Vancelian est flou ou ambigu entre agents.',
      'Tool `redirect_off_topic` → bridge + options si le message est hors périmètre patrimonial / Vancelian.',
      'Hot-path court (code) : conserve parfois le dernier expert sans appel LLM si message très court + expert récent (cf. router_hot_path).',
    ],
    children: [
      {
        id: 'default',
        title: 'Agent default',
        kind: 'expert',
        description:
          'Généraliste lorsque aucun expert ne s’impose ; culture web, app, sujets non couverts.',
        prompts: withFramework(
          [{ file: 'default_system.md', label: 'Prompt système' }],
          true
        ),
        routingOrChoices: [
          'Tooling limité — pas de widgets compliants ; renvoie vers experts si besoin.',
        ],
      },
      {
        id: 'advisor',
        title: 'Conseil placement',
        kind: 'expert',
        description: 'Allocation, pédagogie personnalisée, scénarios — pas de promesse de rendement.',
        prompts: withFramework(
          [{ file: 'advisor_system.md', label: 'Prompt système' }],
          true
        ),
        routingOrChoices: [
          'Peut appeler `show_instrument_card`, `show_featured_articles`, `consult_specialist`, `handoff_to_agent`, etc.',
        ],
      },
      {
        id: 'product',
        title: 'Produits Vancelian',
        kind: 'expert',
        description:
          'Source de vérité produits via wiki Markdown (`read_wiki_page`) ; peut enchaîner un pipeline Slack-like en interne.',
        prompts: withFramework(
          [
            { file: 'product_system.md', label: 'Prompt système' },
            {
              file: 'product_pipeline_input_guardrail.md',
              label: 'Pipeline — garde entrée (classifieur JSON)',
            },
            {
              file: 'product_pipeline_pass1.md',
              label: 'Pipeline — retrieval chemins wiki',
            },
            {
              file: 'product_pipeline_output_judge.md',
              label: 'Pipeline — juge sortie (PASS/REWRITE/BLOCK)',
            },
          ],
          true
        ),
        routingOrChoices: [
          'Widgets : bundles, instruments, FAQ produit selon tools enregistrés.',
          '`consult_specialist` peut être invoqué par d’autres agents vers ce module.',
        ],
      },
      {
        id: 'market',
        title: 'Veille marché',
        kind: 'expert',
        description: 'Macro, actu, articles — ton analytique.',
        prompts: withFramework(
          [{ file: 'market_system.md', label: 'Prompt système' }],
          true
        ),
        routingOrChoices: [
          '`show_featured_articles` et lecture marché selon registry.',
        ],
      },
      {
        id: 'trust',
        title: 'Confiance & sécurité',
        kind: 'expert',
        description: 'Régulation, custody, infra — wiki catégorie trust-security.',
        prompts: withFramework(
          [{ file: 'trust_system.md', label: 'Prompt système' }],
          true
        ),
        routingOrChoices: [
          'Pas commercial ; peut être la cible de `consult_specialist` depuis advisor / compliance.',
        ],
      },
      {
        id: 'compliance',
        title: 'Assistance compte (dispatcher)',
        kind: 'dispatcher',
        description:
          'Entry point `compliance` : premier tour appelle `diagnose_compliance_topic` puis le runtime bascule vers un sous-agent.',
        prompts: [{ file: 'compliance_system.md', label: 'Prompt dispatcher' }],
        routingOrChoices: [
          '`diagnose_compliance_topic` → sous-agent registration | remediation | transactional | general.',
          'Les sous-agents `compliance.*` peuvent appeler `handoff_to_agent` (sauf transactional, terminal) selon registry.',
        ],
        children: [
          {
            id: 'compliance.registration',
            title: 'Sous-agent Registration',
            kind: 'subagent',
            description: 'KYC / onboarding / reprise inscription.',
            prompts: withFramework(
              [{ file: 'compliance_registration_system.md', label: 'Prompt système' }],
              true
            ),
            routingOrChoices: [
              'Tools onboarding : progression, resume, deposit CTA selon SPEC.',
            ],
          },
          {
            id: 'compliance.remediation',
            title: 'Sous-agent Remediation',
            kind: 'subagent',
            description: 'Documents rejetés, demandes AML, mises à jour dossier.',
            prompts: withFramework(
              [{ file: 'compliance_remediation_system.md', label: 'Prompt système' }],
              true
            ),
            routingOrChoices: [
              'Peut transférer vers transactional si aucun blocage compliance.',
            ],
          },
          {
            id: 'compliance.transactional',
            title: 'Sous-agent Transactional',
            kind: 'subagent',
            description: 'État des dépôts / retraits / listes — cartes UI `transaction_detail`.',
            prompts: withFramework(
              [{ file: 'compliance_transactional_system.md', label: 'Prompt système' }],
              true
            ),
            routingOrChoices: [
              'Souvent terminaux : carte auto-suffisante après `read_transaction_detail`.',
            ],
          },
          {
            id: 'compliance.general',
            title: 'Sous-agent General',
            kind: 'subagent',
            description: 'Fallback compte : lectures L0 agrégées (état KYC, transactions…).',
            prompts: withFramework(
              [{ file: 'compliance_general_system.md', label: 'Prompt système' }],
              true
            ),
            routingOrChoices: [
              'Peut consulter `trust` ou `product` via `consult_specialist` selon purpose.',
            ],
          },
        ],
      },
    ],
  },
  {
    id: 'cross-runtime',
    title: 'Transversal runtime',
    kind: 'internal',
    description:
      'Mécanismes hors « un fichier prompt » mais structurants pour le parcours client.',
    prompts: [],
    routingOrChoices: [
      '`consult_specialist` : sous-boucle isolée avec `recent_turns=[]` ; cible principale product ou trust.',
      '`handoff_to_agent` : changement d’agent mid-tour (prompt + tools rechargés).',
      '`ask_user_question` : QCM cliquable (options + agent_hint + deep_link éventuel).',
      '`auto_qcm` (Lot 7) : promotion liste → choices si listing détecté + garde-fous (`conversation_continuity.decide_auto_qcm`).',
      '`compound_user_turn` / enrichissement dernier tour user pour follow-ups laconic (code `conversation_continuity` + memory_state).',
    ],
    children: [
      {
        id: 'summarizer',
        title: 'Summarizer mémoire long-terme',
        kind: 'memory',
        description:
          'Tâche backend : compression JSON (`summary`, `facts`) — pas de réponse directe utilisateur.',
        prompts: [{ file: 'summarizer_system.md', label: 'Prompt système' }],
        routingOrChoices: [
          'Réponse uniquement JSON ; pas dans la whitelist Response Framework.',
        ],
      },
    ],
  },
]

export function flattenArchitecture(
  nodes: AgentArchitectureNode[],
  acc: AgentArchitectureNode[] = []
): AgentArchitectureNode[] {
  for (const n of nodes) {
    acc.push(n)
    if (n.children?.length) {
      flattenArchitecture(n.children, acc)
    }
  }
  return acc
}
