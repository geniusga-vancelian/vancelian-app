'use client'

import type { ReactNode } from 'react'

import { ArticleStepsModuleEditor } from '@/components/admin/ArticleStepsModuleEditor'
import { VaultBlogStyleModuleEditor } from '@/components/admin/VaultBlogStyleModuleEditor'
import { VaultDocumentsListModuleEditor } from '@/components/admin/VaultDocumentsListModuleEditor'
import { VaultKeyInformationModuleEditor } from '@/components/admin/VaultKeyInformationModuleEditor'
import { VaultLocalisationModuleEditor } from '@/components/admin/VaultLocalisationModuleEditor'
import { VaultMediaCarouselModuleEditor } from '@/components/admin/VaultMediaCarouselModuleEditor'
import { VaultVideoBlockArticleModuleEditor } from '@/components/admin/VaultVideoBlockArticleModuleEditor'
import { VaultVirtualVisualizationModuleEditor } from '@/components/admin/VaultVirtualVisualizationModuleEditor'
import { VaultAllocationModuleEditor } from '@/components/admin/vault-modules/VaultAllocationModuleEditor'
import { VaultCompetitiveAdvantagesModuleEditor } from '@/components/admin/vault-modules/VaultCompetitiveAdvantagesModuleEditor'
import { VaultFaqAccordionModuleEditor } from '@/components/admin/vault-modules/VaultFaqAccordionModuleEditor'
import { VaultFundingModuleEditor } from '@/components/admin/vault-modules/VaultFundingModuleEditor'
import { VaultMarkdownBottomModuleEditor } from '@/components/admin/vault-modules/VaultMarkdownBottomModuleEditor'
import { VaultMarketingModulesEditor } from '@/components/admin/vault-modules/VaultMarketingModulesEditor'
import { VaultSimpleMarkdownModuleEditor } from '@/components/admin/vault-modules/VaultSimpleMarkdownModuleEditor'
import { VaultTagsModuleEditor } from '@/components/admin/vault-modules/VaultTagsModuleEditor'
import { VaultTitlePageModuleEditor } from '@/components/admin/vault-modules/VaultTitlePageModuleEditor'
import {
  VaultBlogALaUneModuleEditor,
  VaultPerformanceChartModuleEditor,
  VaultTransactionLatestModuleEditor,
} from '@/components/admin/vault-modules/VaultTinyMetricsEditors'

export type VaultStructuredModuleEditorProps = {
  /** Clé stable pour réinitialiser le textarea JSON lorsque le JSON brut est utilisé */
  moduleId: string
  moduleType: string
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
  /** Remplace tout le content (édition JSON brut) */
  onReplaceContentJson: (raw: string) => void
}

/** Édition avancée — dernier recours ou types tiers */
function VaultJsonFallback({
  moduleId,
  moduleType,
  content,
  onReplaceContentJson,
  extraHints,
}: {
  moduleId: string
  moduleType: string
  content: Record<string, unknown>
  onReplaceContentJson: (raw: string) => void
  extraHints?: ReactNode
}) {
  return (
    <>
      <textarea
        key={moduleId}
        defaultValue={JSON.stringify(content, null, 2)}
        onBlur={(e) => onReplaceContentJson(e.target.value)}
        className="w-full min-h-[160px] p-2 border rounded-md font-mono text-xs"
      />
      <p className="text-xs text-gray-500 mt-1">
        Édition avancée (JSON). Quitte le champ pour appliquer — type&nbsp;:{' '}
        <span className="font-mono text-gray-700">{moduleType}</span>
      </p>
      {extraHints}
    </>
  )
}

/**
 * Formulaire Vault / bundle par type de module ; aligné sur {@link VAULT_MODULE_DEFINITIONS}.
 */
export function VaultStructuredModuleEditor(props: VaultStructuredModuleEditorProps) {
  const { moduleId, moduleType, content, onPatch, onReplaceContentJson } = props

  switch (moduleType) {
    case 'TitlePage':
      return <VaultTitlePageModuleEditor content={content} onPatch={onPatch} />
    case 'TagsModule':
      return <VaultTagsModuleEditor content={content} onPatch={onPatch} />
    case 'FundingModule':
      return <VaultFundingModuleEditor content={content} onPatch={onPatch} />
    case 'SimpleMarkdownContentModule':
      return <VaultSimpleMarkdownModuleEditor content={content} onPatch={onPatch} />

    case 'HEADING':
    case 'PARAGRAPH':
    case 'QUOTE':
    case 'BULLET_LIST':
    case 'NUMBERED_LIST':
      return (
        <VaultBlogStyleModuleEditor
          moduleType={
            moduleType as 'HEADING' | 'PARAGRAPH' | 'QUOTE' | 'BULLET_LIST' | 'NUMBERED_LIST'
          }
          content={content}
          onPatch={onPatch}
        />
      )

    case 'CompetitiveAdvantagesModule':
      return <VaultCompetitiveAdvantagesModuleEditor content={content} onPatch={onPatch} />
    case 'FaqAccordionModule':
      return <VaultFaqAccordionModuleEditor content={content} onPatch={onPatch} />
    case 'ContentBasDePageSansModuleBlanc':
      return <VaultMarkdownBottomModuleEditor content={content} onPatch={onPatch} />

    case 'MarktingCardLargePortrait':
    case 'MarketingCardsSmallCarouselModule':
    case 'MarketingCardsSmallSlidingCarrousel_Portrait':
    case 'MarketingCardsSmallSlidingCarrousel_Paysage':
      return <VaultMarketingModulesEditor moduleType={moduleType} content={content} onPatch={onPatch} />

    case 'TransactionLatest10Module':
      return <VaultTransactionLatestModuleEditor content={content} onPatch={onPatch} />
    case 'BlogALaUne':
      return <VaultBlogALaUneModuleEditor content={content} onPatch={onPatch} />
    case 'AllocationModule':
      return <VaultAllocationModuleEditor content={content} onPatch={onPatch} />

    case 'KeyInformationModule':
      return <VaultKeyInformationModuleEditor content={content} onPatch={onPatch} />
    case 'MediaImageCarouselModule':
      return <VaultMediaCarouselModuleEditor content={content} onPatch={onPatch} />
    case 'DocumentsListModule':
      return <VaultDocumentsListModuleEditor content={content} onPatch={onPatch} />
    case 'PerformanceChart':
      return <VaultPerformanceChartModuleEditor content={content} onPatch={onPatch} />
    case 'StepsModule':
      return <ArticleStepsModuleEditor content={content} onPatch={onPatch} />
    case 'VideoBlockArticleModule':
      return <VaultVideoBlockArticleModuleEditor content={content} onPatch={onPatch} />
    case 'LocalisationModule':
      return <VaultLocalisationModuleEditor content={content} onPatch={onPatch} />
    case 'VirtualVisualizationModule':
      return <VaultVirtualVisualizationModuleEditor content={content} onPatch={onPatch} />

    default:
      return (
        <VaultJsonFallback
          moduleId={moduleId}
          moduleType={moduleType}
          content={content}
          onReplaceContentJson={onReplaceContentJson}
        />
      )
  }
}
