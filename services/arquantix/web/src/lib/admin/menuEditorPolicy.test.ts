import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  computeMenuEditorPolicy,
  selectMenuNameToDisplay,
} from '@/lib/admin/menuEditorPolicy'

/* -------------------------------------------------------------------------- */
/* computeMenuEditorPolicy — invariant central de l'alignement Footer ↔ Menu */
/* -------------------------------------------------------------------------- */

describe('computeMenuEditorPolicy — alignement Footer ↔ Menu', () => {
  it('locale active = locale par défaut → structure éditable, copie inutile', () => {
    const p = computeMenuEditorPolicy('fr', 'fr')
    assert.equal(p.isStructureLocked, false)
    assert.equal(p.canCopyFromDefault, false, 'copier vers FR depuis FR n\'a aucun sens')
    assert.equal(p.copyTarget, 'fr')
    assert.equal(p.languageCheckLocale, 'fr')
  })

  it('locale active ≠ locale par défaut → structure verrouillée + copie disponible', () => {
    const p = computeMenuEditorPolicy('en', 'fr')
    assert.equal(p.isStructureLocked, true)
    assert.equal(p.canCopyFromDefault, true)
    assert.equal(p.copyTarget, 'en', 'copy cible toujours = activeLocale (alignement Footer)')
    assert.equal(p.languageCheckLocale, 'en', 'scan + apply suit toujours activeLocale')
  })

  it('IT comme locale active → idem EN, structure verrouillée et copie pertinente', () => {
    const p = computeMenuEditorPolicy('it', 'fr')
    assert.equal(p.isStructureLocked, true)
    assert.equal(p.canCopyFromDefault, true)
    assert.equal(p.copyTarget, 'it')
    assert.equal(p.languageCheckLocale, 'it')
  })

  it('cas limite : si la locale par défaut n\'est pas FR (futur changement de produit), la règle reste relative', () => {
    const p = computeMenuEditorPolicy('fr', 'en')
    assert.equal(p.isStructureLocked, true, 'FR devient une locale traduite quand defaultLocale=EN')
    assert.equal(p.canCopyFromDefault, true)
    assert.equal(p.copyTarget, 'fr')
  })

  it('un seul concept de locale : copyTarget === languageCheckLocale === activeLocale', () => {
    for (const active of ['fr', 'en', 'it'] as const) {
      const p = computeMenuEditorPolicy(active, 'fr')
      assert.equal(p.copyTarget, p.activeLocale)
      assert.equal(p.languageCheckLocale, p.activeLocale)
    }
  })
})

/* -------------------------------------------------------------------------- */
/* selectMenuNameToDisplay — affichage par locale active                      */
/* -------------------------------------------------------------------------- */

describe('selectMenuNameToDisplay — input « Menu Name » selon la locale active', () => {
  it('locale par défaut → édite la base (`nameBase`)', () => {
    const v = selectMenuNameToDisplay({
      activeLocale: 'fr',
      defaultLocale: 'fr',
      nameBase: 'Menu principal',
      resolvedName: 'Menu principal',
    })
    assert.equal(v, 'Menu principal')
  })

  it('locale par défaut + nameBase vide → fallback resolvedName (cohérence Prisma create)', () => {
    const v = selectMenuNameToDisplay({
      activeLocale: 'fr',
      defaultLocale: 'fr',
      nameBase: '',
      resolvedName: 'Primary',
    })
    assert.equal(v, 'Primary')
  })

  it('locale ≠ par défaut → affiche la valeur résolue (lecture seule côté UI)', () => {
    const v = selectMenuNameToDisplay({
      activeLocale: 'en',
      defaultLocale: 'fr',
      nameBase: 'Menu principal',
      resolvedName: 'Main menu',
    })
    assert.equal(v, 'Main menu', 'EN doit afficher la traduction EN, pas le nameBase FR')
  })

  it('locale ≠ par défaut + pas de traduction → resolvedName = fallback serveur (FR)', () => {
    // Le serveur applique resolveLabelWithFallback : si MenuI18n[en] absent,
    // resolvedName retombe sur defaultLocale puis nameBase. L'input affiche
    // donc la valeur fallback en lecture seule, signalant à l'opérateur
    // qu'aucune traduction EN n'existe encore (input verrouillé, badge UI).
    const v = selectMenuNameToDisplay({
      activeLocale: 'en',
      defaultLocale: 'fr',
      nameBase: 'Menu principal',
      resolvedName: 'Menu principal',
    })
    assert.equal(v, 'Menu principal')
  })
})

/* -------------------------------------------------------------------------- */
/* Garantie d'alignement strict avec le pattern Footer                         */
/* -------------------------------------------------------------------------- */

describe('Garantie d\'alignement strict avec SiteFooterEditor', () => {
  it('aucun « languageCheckLocale » indépendant : un seul activeLocale gouverne tout', () => {
    // Sur Footer (cf. SiteFooterEditor.tsx), `activeLocale` pilote :
    //   - la copie « Copier depuis FR » (handleCopyFromDefault)
    //   - LanguageCheckActions (activeLocale={activeLocale})
    // Aucun sélecteur « Locale cible » indépendant. Cette propriété doit
    // tenir aussi pour le Menu : `copyTarget` et `languageCheckLocale` sont
    // dérivés exclusivement d'`activeLocale`, jamais d'un état séparé.
    const p = computeMenuEditorPolicy('en', 'fr')
    assert.equal(
      p.copyTarget,
      p.languageCheckLocale,
      'copyTarget et languageCheckLocale doivent suivre la même source',
    )
    assert.equal(
      p.copyTarget,
      p.activeLocale,
      'copyTarget doit être strictement = activeLocale',
    )
  })

  it('isStructureLocked et canCopyFromDefault sont strictement équivalents (même condition)', () => {
    // Côté Footer : pas de notion de « structure verrouillée » car tous les
    // champs Footer sont localisés. Pour Menu (relationnel), on ajoute le
    // verrouillage de la structure mais sa condition de déclenchement est
    // exactement la même que celle qui rend le bouton « Copier depuis FR »
    // pertinent : on ne peut pas avoir l'un sans l'autre.
    for (const active of ['fr', 'en', 'it'] as const) {
      const p = computeMenuEditorPolicy(active, 'fr')
      assert.equal(p.isStructureLocked, p.canCopyFromDefault)
    }
  })
})
