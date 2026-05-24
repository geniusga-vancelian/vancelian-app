import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { createMorphoVaultSchema, updateMorphoVaultSchema } from './morphoVaultValidation'

describe('createMorphoVaultSchema', () => {
  it('accepte un vault direct_morpho Base valide', () => {
    const parsed = createMorphoVaultSchema.parse({
      vaultAddress: '0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2',
      integrationMode: 'direct_morpho',
    })
    assert.equal(parsed.integrationMode, 'direct_morpho')
  })

  it('exige privyVaultId en mode privy_earn', () => {
    assert.throws(() =>
      createMorphoVaultSchema.parse({
        vaultAddress: '0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2',
        integrationMode: 'privy_earn',
      }),
    )
  })

  it('rejette une adresse invalide', () => {
    assert.throws(() =>
      createMorphoVaultSchema.parse({
        vaultAddress: 'not-an-address',
        integrationMode: 'direct_morpho',
      }),
    )
  })

  it('rejette une autre chaîne que Base', () => {
    assert.throws(() =>
      createMorphoVaultSchema.parse({
        vaultAddress: '0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2',
        chainId: 1,
        integrationMode: 'direct_morpho',
      }),
    )
  })
})

describe('updateMorphoVaultSchema', () => {
  it('accepte une mise à jour partielle', () => {
    const parsed = updateMorphoVaultSchema.parse({ label: 'Nouveau label', isPublished: true })
    assert.equal(parsed.label, 'Nouveau label')
    assert.equal(parsed.isPublished, true)
  })
})
