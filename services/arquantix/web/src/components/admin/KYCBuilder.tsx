'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FieldSelector } from './FieldSelector'
import { Plus, Trash2, GripVertical, Eye, EyeOff } from 'lucide-react'

interface Condition {
  when: {
    field_slug: string
    operator: 'equals' | 'not_equals' | 'in' | 'not_in' | 'exists' | 'not_exists'
    value: any
  }
  then: Array<{
    action: 'show_block' | 'hide_block' | 'require_field' | 'optional_field' | 'skip_step' | 'goto_step'
    target: string
  }>
}

interface Block {
  block_id: string
  fields: string[]
  layout: 'single_column' | 'two_columns' | 'cards'
  required: boolean
  conditions?: Condition[]
}

interface Step {
  step_id: string
  title_en: string
  description_en?: string
  blocks: Block[]
}

interface KYCBuilderProps {
  steps: Step[]
  onChange: (steps: Step[]) => void
}

export function KYCBuilder({ steps, onChange }: KYCBuilderProps) {
  const [expandedStep, setExpandedStep] = useState<string | null>(steps[0]?.step_id || null)
  const [expandedBlock, setExpandedBlock] = useState<string | null>(null)

  const addStep = () => {
    const newStep: Step = {
      step_id: `step_${Date.now()}`,
      title_en: 'New Step',
      blocks: [],
    }
    onChange([...steps, newStep])
    setExpandedStep(newStep.step_id)
  }

  const updateStep = (stepId: string, updates: Partial<Step>) => {
    onChange(steps.map(s => s.step_id === stepId ? { ...s, ...updates } : s))
  }

  const deleteStep = (stepId: string) => {
    onChange(steps.filter(s => s.step_id !== stepId))
    if (expandedStep === stepId) {
      setExpandedStep(steps.find(s => s.step_id !== stepId)?.step_id || null)
    }
  }

  const addBlock = (stepId: string) => {
    const newBlock: Block = {
      block_id: `block_${Date.now()}`,
      fields: [],
      layout: 'single_column',
      required: true,
    }
    updateStep(stepId, {
      blocks: [...(steps.find(s => s.step_id === stepId)?.blocks || []), newBlock],
    })
    setExpandedBlock(newBlock.block_id)
  }

  const updateBlock = (stepId: string, blockId: string, updates: Partial<Block>) => {
    updateStep(stepId, {
      blocks: (steps.find(s => s.step_id === stepId)?.blocks || []).map(b =>
        b.block_id === blockId ? { ...b, ...updates } : b
      ),
    })
  }

  const deleteBlock = (stepId: string, blockId: string) => {
    updateStep(stepId, {
      blocks: (steps.find(s => s.step_id === stepId)?.blocks || []).filter(b => b.block_id !== blockId),
    })
  }

  const addCondition = (stepId: string, blockId: string) => {
    const newCondition: Condition = {
      when: {
        field_slug: '',
        operator: 'equals',
        value: '',
      },
      then: [],
    }
    const block = steps.find(s => s.step_id === stepId)?.blocks.find(b => b.block_id === blockId)
    updateBlock(stepId, blockId, {
      conditions: [...(block?.conditions || []), newCondition],
    })
  }

  const updateCondition = (stepId: string, blockId: string, index: number, updates: Partial<Condition>) => {
    const block = steps.find(s => s.step_id === stepId)?.blocks.find(b => b.block_id === blockId)
    if (!block) return
    const conditions = [...(block.conditions || [])]
    conditions[index] = { ...conditions[index], ...updates }
    updateBlock(stepId, blockId, { conditions })
  }

  const deleteCondition = (stepId: string, blockId: string, index: number) => {
    const block = steps.find(s => s.step_id === stepId)?.blocks.find(b => b.block_id === blockId)
    if (!block) return
    const conditions = (block.conditions || []).filter((_, i) => i !== index)
    updateBlock(stepId, blockId, { conditions })
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Onboarding Steps</h3>
        <Button onClick={addStep} size="sm">
          <Plus className="w-4 h-4 mr-2" />
          Add Step
        </Button>
      </div>

      {steps.map((step, stepIdx) => (
        <Card key={step.step_id}>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <GripVertical className="w-4 h-4 text-gray-400" />
                  <Input
                    value={step.step_id}
                    onChange={(e) => updateStep(step.step_id, { step_id: e.target.value })}
                    placeholder="Step ID"
                    className="w-40"
                  />
                  <Input
                    value={step.title_en}
                    onChange={(e) => updateStep(step.step_id, { title_en: e.target.value })}
                    placeholder="Step Title"
                    className="flex-1"
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setExpandedStep(expandedStep === step.step_id ? null : step.step_id)}
                  >
                    {expandedStep === step.step_id ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteStep(step.step_id)}
                    className="text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                <Textarea
                  value={step.description_en || ''}
                  onChange={(e) => updateStep(step.step_id, { description_en: e.target.value })}
                  placeholder="Step description (optional)"
                  rows={2}
                />
              </div>
            </div>
          </CardHeader>
          {expandedStep === step.step_id && (
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center">
                <h4 className="font-medium">Blocks</h4>
                <Button onClick={() => addBlock(step.step_id)} size="sm" variant="outline">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Block
                </Button>
              </div>

              {step.blocks.map((block, blockIdx) => (
                <Card key={block.block_id} className="bg-gray-50">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <GripVertical className="w-4 h-4 text-gray-400" />
                          <Input
                            value={block.block_id}
                            onChange={(e) => updateBlock(step.step_id, block.block_id, { block_id: e.target.value })}
                            placeholder="Block ID"
                            className="w-40"
                          />
                          <Select
                            value={block.layout}
                            onValueChange={(value: 'single_column' | 'two_columns' | 'cards') =>
                              updateBlock(step.step_id, block.block_id, { layout: value })
                            }
                          >
                            <SelectTrigger className="w-40">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="single_column">Single Column</SelectItem>
                              <SelectItem value="two_columns">Two Columns</SelectItem>
                              <SelectItem value="cards">Cards</SelectItem>
                            </SelectContent>
                          </Select>
                          <label className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={block.required}
                              onChange={(e) => updateBlock(step.step_id, block.block_id, { required: e.target.checked })}
                            />
                            Required
                          </label>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setExpandedBlock(expandedBlock === block.block_id ? null : block.block_id)}
                          >
                            {expandedBlock === block.block_id ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => deleteBlock(step.step_id, block.block_id)}
                            className="text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  {expandedBlock === block.block_id && (
                    <CardContent className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">Fields</label>
                        <FieldSelector
                          selected={block.fields}
                          onSelect={(slug) => {
                            updateBlock(step.step_id, block.block_id, {
                              fields: [...block.fields, slug],
                            })
                          }}
                          onRemove={(slug) => {
                            updateBlock(step.step_id, block.block_id, {
                              fields: block.fields.filter(f => f !== slug),
                            })
                          }}
                        />
                      </div>

                      <div>
                        <div className="flex justify-between items-center mb-2">
                          <label className="block text-sm font-medium">Conditions</label>
                          <Button onClick={() => addCondition(step.step_id, block.block_id)} size="sm" variant="outline">
                            <Plus className="w-4 h-4 mr-2" />
                            Add Condition
                          </Button>
                        </div>
                        {(block.conditions || []).map((condition, condIdx) => (
                          <Card key={condIdx} className="mb-2 bg-white">
                            <CardContent className="pt-4 space-y-3">
                              <div className="text-sm font-medium">When:</div>
                              <div className="grid grid-cols-3 gap-2">
                                <Input
                                  value={condition.when.field_slug}
                                  onChange={(e) => updateCondition(step.step_id, block.block_id, condIdx, {
                                    when: { ...condition.when, field_slug: e.target.value },
                                  })}
                                  placeholder="Field slug"
                                />
                                <Select
                                  value={condition.when.operator}
                                  onValueChange={(value: any) => updateCondition(step.step_id, block.block_id, condIdx, {
                                    when: { ...condition.when, operator: value },
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
                                  value={typeof condition.when.value === 'string' ? condition.when.value : JSON.stringify(condition.when.value)}
                                  onChange={(e) => {
                                    let value: any = e.target.value
                                    try {
                                      value = JSON.parse(value)
                                    } catch {}
                                    updateCondition(step.step_id, block.block_id, condIdx, {
                                      when: { ...condition.when, value },
                                    })
                                  }}
                                  placeholder="Value"
                                />
                              </div>
                              <div className="text-sm font-medium">Then:</div>
                              <div className="space-y-2">
                                {(condition.then || []).map((action, actionIdx) => (
                                  <div key={actionIdx} className="flex gap-2">
                                    <Select
                                      value={action.action}
                                      onValueChange={(value: any) => {
                                        const then = [...(condition.then || [])]
                                        then[actionIdx] = { ...then[actionIdx], action: value }
                                        updateCondition(step.step_id, block.block_id, condIdx, { then })
                                      }}
                                    >
                                      <SelectTrigger className="w-40">
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="show_block">show_block</SelectItem>
                                        <SelectItem value="hide_block">hide_block</SelectItem>
                                        <SelectItem value="require_field">require_field</SelectItem>
                                        <SelectItem value="optional_field">optional_field</SelectItem>
                                        <SelectItem value="skip_step">skip_step</SelectItem>
                                        <SelectItem value="goto_step">goto_step</SelectItem>
                                      </SelectContent>
                                    </Select>
                                    <Input
                                      value={action.target}
                                      onChange={(e) => {
                                        const then = [...(condition.then || [])]
                                        then[actionIdx] = { ...then[actionIdx], target: e.target.value }
                                        updateCondition(step.step_id, block.block_id, condIdx, { then })
                                      }}
                                      placeholder="Target (block_id, field_slug, or step_id)"
                                      className="flex-1"
                                    />
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => {
                                        const then = (condition.then || []).filter((_, i) => i !== actionIdx)
                                        updateCondition(step.step_id, block.block_id, condIdx, { then })
                                      }}
                                      className="text-red-600"
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </Button>
                                  </div>
                                ))}
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    const then = [
                                      ...(condition.then || []),
                                      { action: 'show_block' as const, target: '' },
                                    ]
                                    updateCondition(step.step_id, block.block_id, condIdx, { then })
                                  }}
                                >
                                  <Plus className="w-4 h-4 mr-2" />
                                  Add Action
                                </Button>
                              </div>
                              <div className="flex justify-end pt-2 border-t">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => deleteCondition(step.step_id, block.block_id, condIdx)}
                                  className="text-red-600"
                                >
                                  <Trash2 className="w-4 h-4" />
                                  Remove Condition
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </CardContent>
                  )}
                </Card>
              ))}
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  )
}
