import { resolveSectionI18nPolicy } from './src/lib/sections/sectionI18nPolicy.ts'
import { scanPageLanguage } from './src/lib/admin/pageCheckLanguage.ts'

const sectionKey = 'figma_testimonial_cards'
const data = {
  eyebrow: 'TÉMOIGNAGES',
  title: 'Ils nous font confiance',
  description: 'Avis de nos clients.',
  cardsPerRow: 1,
  items: [{ author: 'Marie', role: 'Investisseur', content: 'Super service.' }],
}

console.log('--- policy ---')
console.log(JSON.stringify(resolveSectionI18nPolicy(sectionKey), null, 2))

console.log('\n--- scan target=en (texte FR) ---')
const scan = await scanPageLanguage({
  page: { id: 'p1', slug: 'home', template: 'homepage' },
  sections: [{ key: sectionKey, data }],
  pageI18n: [],
  targetLocale: 'en',
})
console.log('summary:', scan.summary)
const eyebrowFinding = scan.findings.filter((f) => f.path === 'eyebrow' || f.path === 'eyebrow.0' || f.path?.endsWith('eyebrow'))
console.log('eyebrow findings:', JSON.stringify(eyebrowFinding, null, 2))

console.log('\n--- scan instance "figma_testimonial_cards_2" (canonisation) ---')
const scan2 = await scanPageLanguage({
  page: { id: 'p1', slug: 'home', template: 'homepage' },
  sections: [{ key: 'figma_testimonial_cards_2', data }],
  pageI18n: [],
  targetLocale: 'en',
})
console.log('summary:', scan2.summary)
console.log('paths scanned:', scan2.findings.map((f) => f.path))
