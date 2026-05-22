import { MockMyAccountWidget } from '@/components/admin/flutter-preview/mocks/MyAccountWidget'
import { MockExclusiveOffersWidget } from '@/components/admin/flutter-preview/mocks/ExclusiveOffersWidget'
import { MockBlogALaUneCard } from '@/components/admin/flutter-preview/mocks/BlogALaUneCard'
import { MockMarketingCardSlider } from '@/components/admin/flutter-preview/mocks/MarketingCardSlider'
import { MockTableInformationModule } from '@/components/admin/flutter-preview/mocks/TableInformationModule'
import { MockFaqModule } from '@/components/admin/flutter-preview/mocks/FaqModule'
import { MockSavingVaultsWidget } from '@/components/admin/flutter-preview/mocks/SavingVaultsWidget'
import { MockTransactionList } from '@/components/admin/flutter-preview/mocks/TransactionListItem'

import { registerPreview } from '../registry'

/// Modules isolés (rendus sans navbar dans `PreviewCanvas kind="module"`).
/// Les ids correspondent aux nœuds `kind: 'module'` de `APP_ARBORESCENCE`
/// (cf. `src/app/admin/flutter/page.tsx`).

// Dashboard widgets
registerPreview('dashboard-widget-account', MockMyAccountWidget, 'module')
registerPreview('dashboard-widget-exclusive', MockExclusiveOffersWidget, 'module')
registerPreview('dashboard-widget-news', MockBlogALaUneCard, 'module')
registerPreview('dashboard-widget-news-analysis', MockBlogALaUneCard, 'module')

// Offers widgets
registerPreview('offers-widget-saving-vaults', MockSavingVaultsWidget, 'module')
registerPreview('offers-exclusive', MockExclusiveOffersWidget, 'module')

// Homepage modules
registerPreview('news-a-la-une', MockBlogALaUneCard, 'module')
registerPreview('offers-carousel', MockExclusiveOffersWidget, 'module')

// Compte Euro modules
registerPreview('euro-account-marketing', MockMarketingCardSlider, 'module')
registerPreview('euro-account-transactions', MockTransactionList, 'module')

// Page projet modules
registerPreview('module-table-info', MockTableInformationModule, 'module')
registerPreview('module-faq', MockFaqModule, 'module')

export {}
