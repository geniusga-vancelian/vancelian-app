import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildLanguageHintsFromScan,
  decideShortHeaderAction,
  scanPageLanguage,
  scanPageLanguageDeep,
  type PageSectionInput,
} from '@/lib/admin/pageCheckLanguage'
import type {
  BatchClassifyOutcome,
  BatchLanguageRefiner,
} from '@/lib/i18n/llm/batchClassifyLanguages'

const LONG_FR =
  'Ce paragraphe est rédigé entièrement en français pour permettre une détection fiable par trigrammes. ' +
  'Il décrit un contenu marketing sans mélange avec d’autres langues dans ce bloc précis.'

const LONG_EN =
  'This paragraph is written entirely in English to allow reliable trigram-based detection. ' +
  'It describes marketing content without mixing other languages in this specific block.'

describe('scanPageLanguage — pages CMS', () => {
  it('scanne hero + faq + cta avec target=en (texte EN propre → OK)', () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-hero',
        key: 'hero',
        order: 1,
        data: {
          title: LONG_EN,
          subtitle: LONG_EN,
        },
      },
      {
        id: 'sec-faq',
        key: 'faq',
        order: 2,
        data: {
          title: LONG_EN,
          items: [
            { question: LONG_EN, answerMarkdown: LONG_EN },
            { question: LONG_EN, answerMarkdown: LONG_EN },
          ],
        },
      },
      {
        id: 'sec-cta',
        key: 'cta',
        order: 3,
        data: {
          title: LONG_EN,
          description: LONG_EN, // Markdown selon heuristique cta
          primaryButtonText: 'Get started',
        },
      },
    ]

    const r = scanPageLanguage(
      sections,
      { title: LONG_EN, description: LONG_EN },
      'en',
    )

    assert.ok(r.entries.length >= 8, `entries=${r.entries.length}`)
    // PageI18n title + description scannés
    assert.ok(r.entries.some((e) => e.path === 'pageI18n.title'))
    assert.ok(r.entries.some((e) => e.path === 'pageI18n.description'))
    // Expansion des items[] de la faq
    assert.ok(r.entries.some((e) => e.path === 'data.items[0].question'))
    assert.ok(r.entries.some((e) => e.path === 'data.items[1].answerMarkdown'))
    // Détection markdown sur faq.items[].answerMarkdown
    const md = r.entries.find((e) => e.path === 'data.items[0].answerMarkdown')
    assert.equal(md?.textKind, 'markdown')
    // Détection markdown sur cta.description (heuristique)
    const ctaDesc = r.entries.find(
      (e) => e.sectionKey === 'cta' && e.path === 'data.description',
    )
    assert.equal(ctaDesc?.textKind, 'markdown')
    // Tout est en EN → OK majoritaire
    assert.ok(r.summary.ok > 0)
  })

  it('détecte WRONG_LANGUAGE quand un champ FR existe dans une page cible EN', () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-hero',
        key: 'hero',
        order: 1,
        data: {
          title: LONG_FR, // FR dans une cible EN → WRONG_LANGUAGE
          subtitle: LONG_EN,
        },
      },
    ]
    const r = scanPageLanguage(
      sections,
      { title: null, description: null },
      'en',
    )

    const wrong = r.entries.find(
      (e) => e.sectionKey === 'hero' && e.path === 'data.title',
    )
    assert.equal(wrong?.status, 'WRONG_LANGUAGE')
    assert.equal(wrong?.detectedLocale, 'fr')
    assert.equal(wrong?.autoFixEligible, true)
    assert.equal(r.summary.byStatus.WRONG_LANGUAGE, 1)
  })

  it('section sans politique i18n est ignorée et listée dans summary', () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-x',
        key: 'totally_unknown_key_v1', // pas dans SECTION_I18N_POLICIES
        order: 1,
        data: { title: LONG_EN },
      },
    ]
    const r = scanPageLanguage(
      sections,
      { title: null, description: null },
      'en',
    )
    assert.equal(r.entries.length, 0)
    assert.equal(r.summary.sectionsMissingPolicy.length, 1)
    assert.equal(r.summary.sectionsMissingPolicy[0]!.sectionKey, 'totally_unknown_key_v1')
  })

  it('section notTranslatable (header) est silencieusement ignorée', () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-h',
        key: 'header',
        order: 1,
        data: { title: LONG_EN },
      },
    ]
    const r = scanPageLanguage(
      sections,
      { title: null, description: null },
      'en',
    )
    assert.equal(r.entries.length, 0)
    assert.equal(r.summary.sectionsMissingPolicy.length, 0)
  })

  it('PageI18n vide n’ajoute pas d’entrée MISSING (cohérence Vault)', () => {
    const r = scanPageLanguage([], { title: null, description: null }, 'en')
    assert.equal(r.entries.length, 0)
    assert.equal(r.summary.totalFields, 0)
  })

  it('couvre les nouveaux paths de la policy (tags[], viewAllButtonText, items[].location)', () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-hero',
        key: 'hero_secondary',
        order: 1,
        data: {
          title: LONG_EN,
          // `tags[]` : array de strings, c'est exactement le cas qui était
          // silencieusement ignoré avant le helper d'expansion partagé.
          tags: [LONG_EN, LONG_FR],
          sidebarText: LONG_EN,
        },
      },
      {
        id: 'sec-projects',
        key: 'project_grid',
        order: 2,
        data: {
          title: LONG_EN,
          viewAllButtonText: LONG_EN,
          items: [
            {
              title: LONG_EN,
              location: LONG_FR,
              description: LONG_EN,
              tags: [LONG_EN, LONG_FR],
            },
          ],
        },
      },
      {
        id: 'sec-cta-extra',
        key: 'cta',
        order: 3,
        data: {
          title: LONG_EN,
          eyebrow: LONG_EN,
          primaryButtonText: LONG_EN,
          secondaryButtonText: LONG_EN,
        },
      },
      {
        id: 'sec-media',
        key: 'media_text',
        order: 4,
        data: {
          title: LONG_EN,
          description: LONG_EN,
        },
      },
    ]
    const r = scanPageLanguage(
      sections,
      { title: null, description: null },
      'en',
    )

    const paths = r.entries.map((e) => `${e.sectionKey ?? 'page'}::${e.path}`)

    // hero_secondary
    assert.ok(paths.includes('hero_secondary::data.tags[0]'), 'tags[0] manquant')
    assert.ok(paths.includes('hero_secondary::data.tags[1]'), 'tags[1] manquant')
    assert.ok(paths.includes('hero_secondary::data.sidebarText'), 'sidebarText manquant')

    // project_grid
    assert.ok(paths.includes('project_grid::data.viewAllButtonText'))
    assert.ok(paths.includes('project_grid::data.items[0].title'))
    assert.ok(paths.includes('project_grid::data.items[0].description'))
    assert.ok(paths.includes('project_grid::data.items[0].location'))
    assert.ok(paths.includes('project_grid::data.items[0].tags[0]'))
    assert.ok(paths.includes('project_grid::data.items[0].tags[1]'))

    // cta (2ᵉ instance pour couvrir eyebrow + boutons)
    assert.ok(paths.includes('cta::data.eyebrow'))
    assert.ok(paths.includes('cta::data.primaryButtonText'))
    assert.ok(paths.includes('cta::data.secondaryButtonText'))

    // media_text : `imageMediaAlt` est exclu (source = médiathèque, hors scan section)
    assert.ok(paths.includes('media_text::data.title'))
    assert.ok(!paths.includes('media_text::data.imageMediaAlt'))

    // Détection mixte : `items[0].location` est en FR sur cible EN
    const wrongLocation = r.entries.find(
      (e) =>
        e.sectionKey === 'project_grid' && e.path === 'data.items[0].location',
    )
    assert.equal(wrongLocation?.status, 'WRONG_LANGUAGE')
  })

  /**
   * Garde-fou : tous les surtitres / labels de bandeau exposés au CMS doivent
   * être effectivement vus par le scan de langue (et donc, par construction,
   * par l'auto-traduction qui partage la même policy + le même expander).
   *
   * Si un nouveau surtitre est ajouté à un module mais oublié dans
   * `SECTION_I18N_POLICIES`, ce test casse — on évite alors qu'un surtitre
   * « invisible » côté pipeline i18n soit publié sur le site.
   */
  it('couvre tous les surtitres / labels de bandeau (eyebrow / label / kicker)', () => {
    const cases: Array<{
      sectionKey: string
      field: 'eyebrow' | 'label' | 'kicker'
    }> = [
      { sectionKey: 'how_it_works', field: 'label' },
      { sectionKey: 'key_figures', field: 'eyebrow' },
      { sectionKey: 'cta', field: 'eyebrow' },
      { sectionKey: 'testimonials', field: 'eyebrow' },
      { sectionKey: 'figma_stats_grid', field: 'eyebrow' },
      { sectionKey: 'figma_testimonial_cards', field: 'eyebrow' },
      { sectionKey: 'company_map', field: 'eyebrow' },
      { sectionKey: 'project_grid', field: 'eyebrow' },
      { sectionKey: 'blog_hero', field: 'eyebrow' },
      { sectionKey: 'faq', field: 'eyebrow' },
      { sectionKey: 'media_text', field: 'eyebrow' },
      { sectionKey: 'help_hero_v1', field: 'kicker' },
    ]

    const sections: PageSectionInput[] = cases.map((c, idx) => ({
      id: `sec-${c.sectionKey}`,
      key: c.sectionKey,
      order: idx + 1,
      data: { [c.field]: LONG_FR },
    }))

    const r = scanPageLanguage(
      sections,
      { title: null, description: null },
      'en',
    )

    for (const c of cases) {
      const entry = r.entries.find(
        (e) => e.sectionKey === c.sectionKey && e.path === `data.${c.field}`,
      )
      assert.ok(
        entry,
        `Surtitre manquant dans le scan : ${c.sectionKey}.${c.field}\n` +
          `→ Ajouter le champ dans SECTION_I18N_POLICIES (sectionI18nPolicy.ts).`,
      )
      assert.equal(
        entry?.status,
        'WRONG_LANGUAGE',
        `Le surtitre ${c.sectionKey}.${c.field} (FR) devrait être détecté WRONG_LANGUAGE sur cible EN`,
      )
      assert.equal(
        entry?.autoFixEligible,
        true,
        `Le surtitre ${c.sectionKey}.${c.field} doit être éligible à l'auto-correction`,
      )
    }
  })

  /**
   * Garde-fou ciblé sur les surtitres / titres COURTS (< ~24 caractères).
   *
   * Le détecteur de langue (`classifyTextForTargetLocale`) refuse de
   * classer un texte aussi court et renvoie `NEEDS_REVIEW`. Avant
   * l'introduction de `decideShortHeaderAction` dans `apply`, ces champs
   * (« Management Team », « Nos dirigeants », « ÉQUIPE »…) tombaient dans
   * un trou noir : ni `WRONG_LANGUAGE`, ni auto-traduits.
   *
   * Aujourd'hui la décision dépend de la langue détectée par best-effort
   * sur le texte court :
   *   - si la langue détectée diffère de la cible → autoFixEligible=true
   *   - si la langue détectée === cible → autoFixEligible=false (déjà bon)
   *
   * Ce test vérifie les DEUX cas pour éviter une régression.
   */
  it('marque les en-têtes COURTS comme autoFixEligible UNIQUEMENT quand la langue détectée diffère de la cible', () => {
    // En-têtes courts en FR sur cible EN → doivent être éligibles.
    // (NB : `description` n'est PAS un short-header path → exclu du test ici,
    // il sera classé via le pipeline standard quand il dépasse ~24 chars.)
    const sectionsToFix: PageSectionInput[] = [
      {
        id: 'sec-figma-test',
        key: 'figma_testimonial_cards',
        order: 1,
        data: {
          eyebrow: 'TÉMOIGNAGES', // accents FR → fr
          title: 'Notre équipe', // accent FR → fr
        },
      },
      {
        id: 'sec-how',
        key: 'how_it_works',
        order: 2,
        data: {
          label: 'Comment ça marche', // mots FR
          title: 'Nos étapes', // accent FR
        },
      },
    ]

    const rFix = scanPageLanguage(
      sectionsToFix,
      { title: null, description: null },
      'en',
    )

    for (const e of rFix.entries) {
      assert.equal(
        e.status,
        'NEEDS_REVIEW',
        `${e.sectionKey}.${e.path} (court) doit rester NEEDS_REVIEW (franc trop court).`,
      )
      assert.equal(
        e.autoFixEligible,
        true,
        `${e.sectionKey}.${e.path} (« ${e.valueExcerpt} » FR sur cible EN) ` +
          `doit être autoFixEligible (decideShortHeaderAction → translate fr→en).`,
      )
    }

    // En-têtes courts en EN sur cible EN → NE doivent PAS être éligibles
    // (déjà dans la bonne langue — ne pas envoyer EN→EN à OpenAI).
    const sectionsAlreadyOk: PageSectionInput[] = [
      {
        id: 'sec-cta',
        key: 'cta',
        order: 1,
        data: {
          eyebrow: 'OUR TEAM',
          title: 'Get started today',
          primaryButtonText: 'Learn more',
        },
      },
    ]
    const rOk = scanPageLanguage(
      sectionsAlreadyOk,
      { title: null, description: null },
      'en',
    )
    for (const e of rOk.entries) {
      assert.equal(
        e.autoFixEligible,
        false,
        `${e.sectionKey}.${e.path} (« ${e.valueExcerpt} » EN déjà sur cible EN) ` +
          `ne doit PAS être autoFixEligible (sinon translate EN→EN risque de produire du FR).`,
      )
    }
  })

  /**
   * Symétrique du test précédent : quand on cible la locale par défaut (FR),
   * on n'a aucune autre locale source utilisable comme référence — on doit
   * donc PAS marquer le champ comme autoFixEligible. C'est important pour
   * éviter de réécrire un texte source en lui-même (« texte court FR » →
   * traduit FR→FR via OpenAI = bruit éditorial inutile).
   */
  it('NE marque PAS les en-têtes courts comme autoFixEligible quand target===defaultLocale', () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-figma-test',
        key: 'figma_testimonial_cards',
        order: 1,
        data: { eyebrow: 'ÉQUIPE', title: 'Équipe dirigeante' },
      },
    ]
    const r = scanPageLanguage(sections, { title: null, description: null }, 'fr')
    const eyebrowEntry = r.entries.find((e) => e.path === 'data.eyebrow')
    const titleEntry = r.entries.find((e) => e.path === 'data.title')
    assert.equal(eyebrowEntry?.autoFixEligible, false)
    assert.equal(titleEntry?.autoFixEligible, false)
  })

  /**
   * Garde-fou « 3 champs d'en-tête » sur les modules uniformisés.
   *
   * Pour chacun des modules listés, on vérifie que le trio
   * Surtitre + Titre + Description est effectivement scanné quand les
   * champs sont remplis. Le mapping data peut utiliser des alias legacy
   * (`how_it_works.label` = surtitre, `how_it_works.subtitle` = description,
   * `faq.subtitle` = ancien titre — conservé en compat lecture) ; on teste
   * ici les chemins data RÉELS qui doivent être traduisibles.
   *
   * Si quelqu'un retire l'un de ces paths de la policy ou du ground truth,
   * ce test casse — c'est l'effet recherché (uniformisation des 9 modules
   * Surtitre/Titre/Description).
   */
  it('couvre le trio Surtitre/Titre/Description pour les modules uniformisés', () => {
    const cases: Array<{
      sectionKey: string
      eyebrowField: string
      titleField: string
      descriptionField: string
    }> = [
      // Modules au schéma natif eyebrow / title / description.
      { sectionKey: 'cta', eyebrowField: 'eyebrow', titleField: 'title', descriptionField: 'description' },
      { sectionKey: 'project_grid', eyebrowField: 'eyebrow', titleField: 'title', descriptionField: 'description' },
      { sectionKey: 'figma_stats_grid', eyebrowField: 'eyebrow', titleField: 'title', descriptionField: 'description' },
      { sectionKey: 'figma_testimonial_cards', eyebrowField: 'eyebrow', titleField: 'title', descriptionField: 'description' },
      { sectionKey: 'media_text', eyebrowField: 'eyebrow', titleField: 'title', descriptionField: 'description' },
      { sectionKey: 'testimonials', eyebrowField: 'eyebrow', titleField: 'title', descriptionField: 'description' },
      // FAQ : nouveau schéma — `title` (canonique) + `description`.
      { sectionKey: 'faq', eyebrowField: 'eyebrow', titleField: 'title', descriptionField: 'description' },
      // how_it_works : alias legacy — `label` (surtitre) + `subtitle` (description).
      { sectionKey: 'how_it_works', eyebrowField: 'label', titleField: 'title', descriptionField: 'subtitle' },
    ]

    const sections: PageSectionInput[] = cases.map((c, idx) => ({
      id: `sec-${c.sectionKey}-trio`,
      key: c.sectionKey,
      order: idx + 1,
      data: {
        [c.eyebrowField]: LONG_FR,
        [c.titleField]: LONG_FR,
        [c.descriptionField]: LONG_FR,
      },
    }))

    const r = scanPageLanguage(sections, { title: null, description: null }, 'en')

    for (const c of cases) {
      for (const [label, field] of [
        ['surtitre', c.eyebrowField],
        ['titre', c.titleField],
        ['description', c.descriptionField],
      ] as const) {
        const entry = r.entries.find(
          (e) => e.sectionKey === c.sectionKey && e.path === `data.${field}`,
        )
        assert.ok(
          entry,
          `Trio incomplet — ${c.sectionKey}.${field} (${label}) absent du scan.\n` +
            `→ Vérifier SECTION_I18N_POLICIES['${c.sectionKey}'] (et le ground truth).`,
        )
        assert.equal(
          entry?.status,
          'WRONG_LANGUAGE',
          `${c.sectionKey}.${field} (FR sur cible EN) doit être détecté WRONG_LANGUAGE.`,
        )
        assert.equal(
          entry?.autoFixEligible,
          true,
          `${c.sectionKey}.${field} doit être auto-corrigeable (uniformisation 3 champs).`,
        )
      }
    }
  })

  /**
   * Garde-fou Bug 1 — « Court EN sur cible FR doit être détecté + corrigé »
   *
   * Avant ce lot, l'éligibilité best-effort sur les en-têtes courts dépendait
   * uniquement de `defaultLocale !== targetLocale`. Conséquence : sur la page
   * FR (locale par défaut), un eyebrow / title / label resté en anglais
   * (« Get Started », « Our Team », …) n'était JAMAIS marqué autoFixEligible
   * et passait sous le radar.
   *
   * Aujourd'hui, `decideShortHeaderAction` détecte la langue du texte court
   * (franc minLength:0 + heuristique accents) et déclare le champ éligible
   * dès que la langue détectée diffère de la cible — y compris sur la cible
   * FR.
   */
  it('Bug 1 — court EN sur cible FR : autoFixEligible=true (≠ ancien comportement)', () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-cta',
        key: 'cta',
        order: 1,
        data: {
          // « Our Team » contient le mot EN_HINT « our »
          eyebrow: 'Our Team',
          // « Get started today » : mots EN reconnus
          title: 'Get started today',
          // « Learn more » : mots EN reconnus
          primaryButtonText: 'Learn more',
        },
      },
    ]
    const r = scanPageLanguage(
      sections,
      { title: null, description: null },
      'fr',
    )

    const eyebrow = r.entries.find((e) => e.path === 'data.eyebrow')
    const title = r.entries.find((e) => e.path === 'data.title')
    assert.ok(eyebrow, 'eyebrow doit être scanné')
    assert.ok(title, 'title doit être scanné')
    // Statut : court → NEEDS_REVIEW (le détecteur strict reste prudent), mais
    // l'éligibilité est portée par decideShortHeaderAction qui détecte EN.
    assert.equal(
      eyebrow?.autoFixEligible,
      true,
      `eyebrow="${eyebrow?.valueExcerpt}" : avant ce lot, sur cible FR (=defaultLocale) tout court NEEDS_REVIEW était skippé. ` +
        `Aujourd'hui decideShortHeaderAction détecte la langue (« en ») et autorise translate en→fr.`,
    )
    assert.equal(title?.autoFixEligible, true)
  })

  /**
   * Garde-fou Bug 2 — « Court EN sur cible EN ne doit JAMAIS être touché »
   *
   * Avant ce lot, sur la cible EN, l'apply considérait aveuglément
   * `sourceLocale = defaultLocale (fr)` pour tout court NEEDS_REVIEW. Résultat :
   * il envoyait à OpenAI « ce texte EN est en FR, traduis-le en EN » →
   * sortie aléatoire, parfois carrément en français.
   *
   * Aujourd'hui, `decideShortHeaderAction` détecte que le texte est déjà en
   * EN et retourne `skip:already_in_target` → l'apply n'appelle pas le LLM.
   */
  it('Bug 2 — court EN sur cible EN : skip already_in_target', () => {
    const decision = decideShortHeaderAction('Our Team', 'en')
    assert.equal(
      decision.kind,
      'skip',
      `Avant ce lot, l'apply assumait sourceLocale=fr et envoyait à OpenAI ` +
        `« ce texte EN est en FR, traduis en EN » → sortie aléatoire (souvent FR généré). ` +
        `Aujourd'hui : skip already_in_target.`,
    )
    if (decision.kind === 'skip') {
      assert.equal(decision.reason, 'already_in_target')
    }

    // Et le scan le marque bien NON éligible auto-fix.
    const sections: PageSectionInput[] = [
      {
        id: 'sec-cta',
        key: 'cta',
        order: 1,
        data: {
          eyebrow: 'Our Team',
          title: 'Get started',
        },
      },
    ]
    const r = scanPageLanguage(
      sections,
      { title: null, description: null },
      'en',
    )
    for (const e of r.entries) {
      assert.equal(
        e.autoFixEligible,
        false,
        `${e.path} (« ${e.valueExcerpt} » EN sur cible EN) ne doit pas être autoFixEligible`,
      )
    }
  })

  /**
   * Garde-fou Bug 1 (variante FR détectée) — « Court FR sur cible FR : skip »
   *
   * Sur la page FR, un eyebrow déjà français ne doit pas être touché. La
   * détection d'accents (`éèêëàâ…`) ou de mots FR par franc doit conduire à
   * `skip:already_in_target`.
   */
  it('court FR sur cible FR : skip already_in_target', () => {
    const decision = decideShortHeaderAction('Notre équipe', 'fr')
    assert.equal(decision.kind, 'skip')
    if (decision.kind === 'skip') {
      assert.equal(decision.reason, 'already_in_target')
    }
  })

  /**
   * Garde-fou Bug 1 (variante FR→EN) — « Court FR sur cible EN : translate fr→en »
   *
   * Sur la page EN, un eyebrow resté en français (« TÉMOIGNAGES », « Notre
   * équipe ») doit être traduit FR→EN. C'est le cas standard déjà couvert
   * avant ce lot — le test sert de non-régression.
   */
  it('court FR sur cible EN : translate avec sourceLocale=fr', () => {
    const decision = decideShortHeaderAction('Notre équipe', 'en')
    assert.equal(decision.kind, 'translate')
    if (decision.kind === 'translate') {
      assert.equal(decision.sourceLocale, 'fr')
    }
  })

  /**
   * Garde-fou « ambigu » — texte vraiment indétectable (chiffres / ponctuation)
   *
   * Pour des chaînes qui ne contiennent ni accents FR ni mots reconnus dans
   * notre dictionnaire (ex. « 12345 », « 100% »), franc retombe en `und` et
   * `bestEffortDetectShortLocale` retourne `null`. Comportement attendu :
   *   - cible = defaultLocale (FR) → skip (`undetectable_short_text_on_default_locale`)
   *     pour éviter une réécriture FR→FR aveugle.
   *   - cible ≠ defaultLocale (EN/IT) → translate avec sourceLocale=defaultLocale
   *     (best-effort historique conservé).
   */
  it('court indétectable (chiffres) : skip sur cible=FR, translate sur cible=EN', () => {
    const ambiguous = '12345'

    const onFr = decideShortHeaderAction(ambiguous, 'fr')
    assert.equal(onFr.kind, 'skip')
    if (onFr.kind === 'skip') {
      assert.equal(onFr.reason, 'undetectable_short_text_on_default_locale')
    }

    const onEn = decideShortHeaderAction(ambiguous, 'en')
    assert.equal(onEn.kind, 'translate')
    if (onEn.kind === 'translate') {
      assert.equal(onEn.sourceLocale, 'fr')
    }
  })

  it('respecte l’ordre de la section dans les entrées', () => {
    const LONG_EN_LOCAL =
      'This paragraph is written entirely in English to allow reliable trigram-based detection.'
    const sections: PageSectionInput[] = [
      {
        id: 'sec-a',
        key: 'hero',
        order: 5,
        data: { title: LONG_EN_LOCAL },
      },
      {
        id: 'sec-b',
        key: 'cta',
        order: 1,
        data: { title: LONG_EN_LOCAL },
      },
    ]
    const r = scanPageLanguage(
      sections,
      { title: null, description: null },
      'en',
    )
    const heroEntry = r.entries.find((e) => e.sectionKey === 'hero')
    const ctaEntry = r.entries.find((e) => e.sectionKey === 'cta')
    assert.equal(heroEntry?.sectionIndex, 5)
    assert.equal(ctaEntry?.sectionIndex, 1)
  })
})

/* -------------------------------------------------------------------------- */
/* Deep scan (raffinage LLM batché) — anti-régression bouton « Vérifier »     */
/* -------------------------------------------------------------------------- */

/**
 * Helper : fabrique un refiner mock qui répond avec une langue fixe pour
 * les textes correspondants. Tout texte non listé est rendu en `und`.
 */
function makeStaticRefiner(
  mapping: Record<string, { locale: 'fr' | 'en' | 'it' | 'und'; confidence: number }>,
  options?: { tokensPerCall?: number; throwOnce?: boolean },
): BatchLanguageRefiner {
  let alreadyThrown = false
  return async (items): Promise<BatchClassifyOutcome> => {
    if (options?.throwOnce && !alreadyThrown) {
      alreadyThrown = true
      throw new Error('mock refiner forced failure')
    }
    return {
      results: items.map((it) => {
        const m = mapping[it.text]
        return m
          ? { id: it.id, locale: m.locale, confidence: m.confidence }
          : { id: it.id, locale: 'und' as const, confidence: 0 }
      }),
      tokensUsedApprox: options?.tokensPerCall ?? 100,
      hadError: false,
      callCount: 1,
    }
  }
}

describe('scanPageLanguageDeep — affinage LLM batché', () => {
  it('reclassifie un eyebrow court EN sur cible FR via le LLM (statut → WRONG_LANGUAGE)', async () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-cta',
        key: 'cta',
        order: 1,
        data: {
          // Texte vraiment court, sans accent ni mot-clé reconnu par le
          // dictionnaire heuristique → l'heuristique locale dirait
          // NEEDS_REVIEW. Le LLM doit trancher EN.
          eyebrow: 'AAA',
        },
      },
    ]

    const refiner = makeStaticRefiner({
      AAA: { locale: 'en', confidence: 0.9 },
    })

    const r = await scanPageLanguageDeep(
      sections,
      { title: null, description: null },
      'fr',
      { refiner },
    )

    const eyebrow = r.entries.find((e) => e.path === 'data.eyebrow')
    assert.ok(eyebrow, 'eyebrow doit être scanné')
    assert.equal(
      eyebrow?.status,
      'WRONG_LANGUAGE',
      'eyebrow EN sur cible FR doit devenir WRONG_LANGUAGE après affinage LLM',
    )
    assert.equal(eyebrow?.detectedLocale, 'en')
    assert.equal(eyebrow?.autoFixEligible, true)
    assert.equal(r.llmRefinement.attempted, 1)
    assert.equal(r.llmRefinement.refined, 1)
    assert.equal(r.llmRefinement.callCount, 1)
    assert.equal(r.llmRefinement.hadError, false)
    // Le résumé doit refléter la nouvelle classification (1 WRONG_LANGUAGE).
    assert.equal(r.summary.byStatus.WRONG_LANGUAGE, 1)
    assert.equal(r.summary.byStatus.NEEDS_REVIEW, 0)
    assert.equal(r.summary.needsAttention, 1)
  })

  it('quand le refiner throw, retombe sur le scan local sans crash (hadError=true)', async () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-cta',
        key: 'cta',
        order: 1,
        data: { eyebrow: 'AAA' },
      },
    ]
    const refiner: BatchLanguageRefiner = async () => {
      throw new Error('boom')
    }

    const r = await scanPageLanguageDeep(
      sections,
      { title: null, description: null },
      'fr',
      { refiner },
    )

    const eyebrow = r.entries.find((e) => e.path === 'data.eyebrow')
    assert.ok(eyebrow, 'eyebrow doit être scanné quand même')
    // Statut local préservé (NEEDS_REVIEW car court indétectable).
    assert.equal(eyebrow?.status, 'NEEDS_REVIEW')
    assert.equal(r.llmRefinement.hadError, true)
    assert.equal(r.llmRefinement.refined, 0)
  })

  it('quand aucun champ n\'est ambigu, n\'appelle PAS le LLM (callCount=0)', async () => {
    const LONG_EN =
      'This paragraph is written entirely in English to allow reliable trigram-based detection. ' +
      'It describes marketing content without mixing other languages in this specific block.'
    const sections: PageSectionInput[] = [
      {
        id: 'sec-faq',
        key: 'faq',
        order: 1,
        data: {
          title: LONG_EN,
          description: LONG_EN,
        },
      },
    ]
    let callCount = 0
    const refiner: BatchLanguageRefiner = async () => {
      callCount += 1
      return { results: [], tokensUsedApprox: 0, hadError: false, callCount: 1 }
    }

    const r = await scanPageLanguageDeep(
      sections,
      { title: null, description: null },
      'en',
      { refiner },
    )

    assert.equal(callCount, 0, 'le refiner ne doit pas être appelé sans candidat')
    assert.equal(r.llmRefinement.attempted, 0)
    assert.equal(r.llmRefinement.refined, 0)
    assert.equal(r.llmRefinement.callCount, 0)
  })

  it('propage la décision LLM aux duplicats du même texte (eyebrow partagé)', async () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-cta-1',
        key: 'cta',
        order: 1,
        data: { eyebrow: 'AAA' },
      },
      {
        id: 'sec-cta-2',
        key: 'cta',
        order: 2,
        data: { eyebrow: 'AAA' },
      },
    ]
    const refiner = makeStaticRefiner({
      AAA: { locale: 'en', confidence: 0.95 },
    })

    const r = await scanPageLanguageDeep(
      sections,
      { title: null, description: null },
      'fr',
      { refiner },
    )

    const entries = r.entries.filter((e) => e.path === 'data.eyebrow')
    assert.equal(entries.length, 2)
    for (const e of entries) {
      assert.equal(
        e.status,
        'WRONG_LANGUAGE',
        'le LLM ne doit envoyer le texte qu\'une fois mais propager à tous les duplicats',
      )
      assert.equal(e.detectedLocale, 'en')
    }
    // Mesure la déduplication : 2 entries pour 1 seul texte unique.
    assert.equal(r.llmRefinement.attempted, 1)
    assert.equal(r.llmRefinement.refined, 2, 'refined inclut la propagation aux duplicats')
  })

  it('couverture exhaustive — tous les modules de l\'audit utilisateur sont scannés', async () => {
    // Liste explicite demandée par l'audit. Chaque module doit produire
    // au moins une entrée dans le scan deep (sinon → trou de policy).
    const sections: PageSectionInput[] = [
      { id: 'sec-1', key: 'hero', order: 1, data: { title: 'Bienvenue chez Arquantix', subtitle: 'Une promesse claire' } },
      { id: 'sec-2', key: 'figma_stats_grid', order: 2, data: { eyebrow: 'CHIFFRES', title: 'Notre impact', stats: [{ value: '120', label: 'Projets' }] } },
      { id: 'sec-3', key: 'projects', order: 3, data: { eyebrow: 'NOS PROJETS', title: 'Réalisations', items: [{ title: 'Projet A', description: 'Description', location: 'Paris', tags: ['immobilier'] }] } },
      { id: 'sec-4', key: 'how_it_works', order: 4, data: { label: 'Méthode', title: 'Comment ça marche', steps: [{ title: 'Étape', description: 'Texte' }] } },
      { id: 'sec-5', key: 'how_it_works_2', order: 5, data: { label: 'Méthode', title: 'Comment ça marche 2', steps: [] } },
      { id: 'sec-6', key: 'media_text', order: 6, data: { eyebrow: 'IMAGE', title: 'Avec une image', description: 'Description' } },
      { id: 'sec-7', key: 'media_text_3', order: 7, data: { eyebrow: 'IMAGE 3', title: 'Variant 3', description: 'Description' } },
      { id: 'sec-8', key: 'testimonials', order: 8, data: { eyebrow: 'AVIS', title: 'Témoignages', items: [{ name: 'A', text: 'Texte', title: 'Rôle' }] } },
      { id: 'sec-9', key: 'faq', order: 9, data: { eyebrow: 'FAQ', title: 'Questions fréquentes', description: 'Description', items: [{ question: 'Q ?', answerMarkdown: 'Réponse longue' }] } },
      { id: 'sec-10', key: 'media_text_2', order: 10, data: { eyebrow: 'IMAGE 2', title: 'Variant 2', description: 'Description' } },
      { id: 'sec-11', key: 'how_it_works_3', order: 11, data: { label: 'Méthode 3', title: 'Comment ça marche 3', steps: [] } },
      { id: 'sec-12', key: 'figma_testimonial_cards', order: 12, data: { eyebrow: 'TÉMOIGNAGES', title: 'Cartes', items: [{ author: 'A', role: 'B', content: 'Texte du témoignage assez long pour franc.' }] } },
      { id: 'sec-13', key: 'cta', order: 13, data: { eyebrow: 'COMMENCER', title: 'Prêt ?', description: 'Description', primaryButtonText: 'Démarrer' } },
    ]

    // Refiner « no-op » : il sera appelé pour les courts ambigus et
    // répondra `und` → l'heuristique locale est conservée.
    const refiner = makeStaticRefiner({})

    const r = await scanPageLanguageDeep(
      sections,
      { title: null, description: null },
      'en',
      { refiner },
    )

    // Chaque module attendu doit avoir au moins 1 entry dans le scan.
    const expected = [
      'hero', 'figma_stats_grid', 'projects', 'how_it_works',
      'how_it_works_2', 'media_text', 'media_text_3', 'testimonials',
      'faq', 'media_text_2', 'how_it_works_3',
      'figma_testimonial_cards', 'cta',
    ]
    for (const key of expected) {
      const hits = r.entries.filter((e) => e.sectionKey === key)
      assert.ok(
        hits.length > 0,
        `Module ${key} : aucun champ scanné. Vérifier SECTION_I18N_POLICIES + alias canonique.`,
      )
    }
    // sectionsScanned doit refléter le total brut (13).
    assert.equal(r.summary.sectionsScanned, sections.length)
    // Aucun module manquant de policy.
    assert.equal(
      r.summary.sectionsMissingPolicy.length,
      0,
      `Modules sans policy : ${r.summary.sectionsMissingPolicy.map((s) => s.sectionKey).join(', ')}`,
    )
  })
})

describe('buildLanguageHintsFromScan — partage scan→apply', () => {
  it('construit une carte avec les detectedLocale exploitables', async () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-cta',
        key: 'cta',
        order: 1,
        data: { eyebrow: 'AAA' },
      },
    ]
    const refiner = makeStaticRefiner({
      AAA: { locale: 'en', confidence: 0.9 },
    })

    const scan = await scanPageLanguageDeep(
      sections,
      { title: 'Some long English title that franc can detect reliably', description: null },
      'fr',
      { refiner },
    )

    const hints = buildLanguageHintsFromScan(scan)
    // L'eyebrow EN doit être dans la carte sous la clé sectionId::path.
    assert.equal(hints.get('sec-cta::data.eyebrow'), 'en')
    // Le titre PageI18n EN doit aussi y être.
    assert.equal(hints.get('pageI18n.title'), 'en')
  })

  it('ignore les entrées sans detectedLocale (und LLM = pas de hint)', async () => {
    const sections: PageSectionInput[] = [
      {
        id: 'sec-cta',
        key: 'cta',
        order: 1,
        data: { eyebrow: 'XYZ' }, // refiner répond und
      },
    ]
    const refiner = makeStaticRefiner({})

    const scan = await scanPageLanguageDeep(
      sections,
      { title: null, description: null },
      'fr',
      { refiner },
    )
    const hints = buildLanguageHintsFromScan(scan)
    assert.equal(hints.has('sec-cta::data.eyebrow'), false)
  })
})
