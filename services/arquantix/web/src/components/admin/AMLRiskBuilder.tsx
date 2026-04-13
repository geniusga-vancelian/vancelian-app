'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { FieldSelector } from './FieldSelector'
import { Plus, Trash2, GripVertical, AlertCircle, CheckCircle } from 'lucide-react'

interface AMLRiskCondition {
  field_slug: string
  operator: 'equals' | 'not_equals' | 'in' | 'not_in' | 'exists' | 'not_exists'
  value: any
}

interface AMLRiskEffect {
  add_score: number
  set_flag?: string
  require_action?: string
  stop: boolean
  weight: number
}

interface AMLRiskRule {
  rule_id: string
  description_en: string
  when: AMLRiskCondition
  effect: AMLRiskEffect
}

interface AMLRiskOutputTier {
  tier: 'low' | 'medium' | 'high'
  min: number
  max: number
}

interface AMLRiskOutputs {
  min_score: number
  max_score: number
  tiers: AMLRiskOutputTier[]
}

interface AMLRiskConfig {
  rules: AMLRiskRule[]
  outputs: AMLRiskOutputs
}

interface AMLRiskBuilderProps {
  config: AMLRiskConfig
  onChange: (config: AMLRiskConfig) => void
}

export function AMLRiskBuilder({ config, onChange }: AMLRiskBuilderProps) {
  const [expandedRule, setExpandedRule] = useState<string | null>(null)

  const addRule = () => {
    const newRule: AMLRiskRule = {
      rule_id: `rule_${Date.now()}`,
      description_en: 'New Rule',
      when: {
        field_slug: '',
        operator: 'equals',
        value: '',
      },
      effect: {
        add_score: 0,
        stop: false,
        weight: 1.0,
      },
    }
    onChange({
      ...config,
      rules: [...config.rules, newRule],
    })
    setExpandedRule(newRule.rule_id)
  }

  const updateRule = (ruleId: string, updates: Partial<AMLRiskRule>) => {
    onChange({
      ...config,
      rules: config.rules.map(r => r.rule_id === ruleId ? { ...r, ...updates } : r),
    })
  }

  const deleteRule = (ruleId: string) => {
    onChange({
      ...config,
      rules: config.rules.filter(r => r.rule_id !== ruleId),
    })
  }

  const addTier = () => {
    const newTier: AMLRiskOutputTier = {
      tier: 'low',
      min: 0,
      max: 100,
    }
    onChange({
      ...config,
      outputs: {
        ...config.outputs,
        tiers: [...config.outputs.tiers, newTier],
      },
    })
  }

  const updateTier = (index: number, updates: Partial<AMLRiskOutputTier>) => {
    const tiers = [...config.outputs.tiers]
    tiers[index] = { ...tiers[index], ...updates }
    onChange({
      ...config,
      outputs: {
        ...config.outputs,
        tiers,
      },
    })
  }

  const deleteTier = (index: number) => {
    onChange({
      ...config,
      outputs: {
        ...config.outputs,
        tiers: config.outputs.tiers.filter((_, i) => i !== index),
      },
    })
  }

  const validateTiers = () => {
    const { min_score, max_score, tiers } = config.outputs
    if (tiers.length === 0) return { valid: false, message: 'At least one tier required' }

    const sorted = [...tiers].sort((a, b) => a.min - b.min)

    if (sorted[0].min !== min_score) {
      return { valid: false, message: `First tier must start at min_score (${min_score})` }
    }

    if (sorted[sorted.length - 1].max !== max_score) {
      return { valid: false, message: `Last tier must end at max_score (${max_score})` }
    }

    for (let i = 0; i < sorted.length; i++) {
      const tier = sorted[i]
      if (tier.min > tier.max) {
        return { valid: false, message: `Tier ${tier.tier} has min > max` }
      }

      if (i < sorted.length - 1) {
        const next = sorted[i + 1]
        if (tier.max >= next.min) {
          return { valid: false, message: `Tier ${tier.tier} overlaps with next tier` }
        }
        if (tier.max + 1 !== next.min) {
          return { valid: false, message: `Gap between tier ${tier.tier} and next tier` }
        }
      }
    }

    return { valid: true, message: 'Tiers are valid' }
  }

  const tierValidation = validateTiers()

  return (
    <div className="space-y-6">
      {/* Rules Section */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Rules</h3>
          <Button onClick={addRule} size="sm">
            <Plus className="w-4 h-4 mr-2" />
            Add Rule
          </Button>
        </div>

        <div className="space-y-4">
          {config.rules.map((rule, idx) => (
            <Card key={rule.rule_id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <GripVertical className="w-4 h-4 text-gray-400" />
                      <span className="text-sm font-medium">Rule {idx + 1}</span>
                      <Input
                        value={rule.rule_id}
                        onChange={(e) => updateRule(rule.rule_id, { rule_id: e.target.value })}
                        placeholder="Rule ID"
                        className="w-40"
                      />
                      <Input
                        value={rule.description_en}
                        onChange={(e) => updateRule(rule.rule_id, { description_en: e.target.value })}
                        placeholder="Description"
                        className="flex-1"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setExpandedRule(expandedRule === rule.rule_id ? null : rule.rule_id)}
                      >
                        {expandedRule === rule.rule_id ? 'Collapse' : 'Expand'}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteRule(rule.rule_id)}
                        className="text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardHeader>
              {expandedRule === rule.rule_id && (
                <CardContent className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">When Condition</label>
                    <div className="grid grid-cols-3 gap-2">
                      <Input
                        value={rule.when.field_slug}
                        onChange={(e) => updateRule(rule.rule_id, {
                          when: { ...rule.when, field_slug: e.target.value },
                        })}
                        placeholder="Field slug"
                      />
                      <Select
                        value={rule.when.operator}
                        onValueChange={(value: any) => updateRule(rule.rule_id, {
                          when: { ...rule.when, operator: value },
                        })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="equals">equals</SelectItem>
                          <SelectItem value="not_equals">not_equals</SelectItem>
                          <SelectItem value="in">in</SelectItem>
                          <SelectItem value="not_in">not_in</SelectItem>
                          <SelectItem value="exists">exists</SelectItem>
                          <SelectItem value="not_exists">not_exists</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input
                        value={typeof rule.when.value === 'string' ? rule.when.value : JSON.stringify(rule.when.value)}
                        onChange={(e) => {
                          let value: any = e.target.value
                          try {
                            value = JSON.parse(value)
                          } catch {}
                          updateRule(rule.rule_id, {
                            when: { ...rule.when, value },
                          })
                        }}
                        placeholder="Value"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Effect</label>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs text-gray-600">Add Score</label>
                        <Input
                          type="number"
                          value={rule.effect.add_score}
                          onChange={(e) => updateRule(rule.rule_id, {
                            effect: { ...rule.effect, add_score: parseInt(e.target.value) || 0 },
                          })}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-600">Weight</label>
                        <Input
                          type="number"
                          step="0.1"
                          value={rule.effect.weight}
                          onChange={(e) => updateRule(rule.rule_id, {
                            effect: { ...rule.effect, weight: parseFloat(e.target.value) || 1.0 },
                          })}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-600">Set Flag (optional)</label>
                        <Input
                          value={rule.effect.set_flag || ''}
                          onChange={(e) => updateRule(rule.rule_id, {
                            effect: { ...rule.effect, set_flag: e.target.value || undefined },
                          })}
                          placeholder="Flag name"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-600">Require Action (optional)</label>
                        <Input
                          value={rule.effect.require_action || ''}
                          onChange={(e) => updateRule(rule.rule_id, {
                            effect: { ...rule.effect, require_action: e.target.value || undefined },
                          })}
                          placeholder="Action name"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={rule.effect.stop}
                          onChange={(e) => updateRule(rule.rule_id, {
                            effect: { ...rule.effect, stop: e.target.checked },
                          })}
                        />
                        <label className="text-sm">Stop evaluation after this rule</label>
                      </div>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Outputs Section */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Outputs</h3>
        </div>

        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Min Score</label>
                <Input
                  type="number"
                  value={config.outputs.min_score}
                  onChange={(e) => onChange({
                    ...config,
                    outputs: {
                      ...config.outputs,
                      min_score: parseInt(e.target.value) || 0,
                    },
                  })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Max Score</label>
                <Input
                  type="number"
                  value={config.outputs.max_score}
                  onChange={(e) => onChange({
                    ...config,
                    outputs: {
                      ...config.outputs,
                      max_score: parseInt(e.target.value) || 100,
                    },
                  })}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-sm font-medium">Tiers</label>
                <Button onClick={addTier} size="sm" variant="outline">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Tier
                </Button>
              </div>

              {tierValidation.valid ? (
                <div className="flex items-center gap-2 text-green-600 text-sm mb-2">
                  <CheckCircle className="w-4 h-4" />
                  {tierValidation.message}
                </div>
              ) : (
                <div className="flex items-center gap-2 text-red-600 text-sm mb-2">
                  <AlertCircle className="w-4 h-4" />
                  {tierValidation.message}
                </div>
              )}

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tier</TableHead>
                    <TableHead>Min</TableHead>
                    <TableHead>Max</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {config.outputs.tiers
                    .sort((a, b) => a.min - b.min)
                    .map((tier, idx) => (
                      <TableRow key={idx}>
                        <TableCell>
                          <Select
                            value={tier.tier}
                            onValueChange={(value: 'low' | 'medium' | 'high') => updateTier(idx, { tier: value })}
                          >
                            <SelectTrigger className="w-32">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="low">Low</SelectItem>
                              <SelectItem value="medium">Medium</SelectItem>
                              <SelectItem value="high">High</SelectItem>
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            value={tier.min}
                            onChange={(e) => updateTier(idx, { min: parseInt(e.target.value) || 0 })}
                            className="w-20"
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            value={tier.max}
                            onChange={(e) => updateTier(idx, { max: parseInt(e.target.value) || 0 })}
                            className="w-20"
                          />
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => deleteTier(idx)}
                            className="text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
