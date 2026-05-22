/**
 * Seed du chapitre "component DS flutter" et du composant marketing_cards.
 * Préférer : `npm run db:seed:dashboard-builder` ou import depuis `seed.ts`.
 * Exécution directe : npx tsx prisma/seed-ds-components.ts
 */
import { pathToFileURL } from 'node:url'

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const marketingCardsSchema = {
  type: 'widget',
  key: 'marketing_cards_landscape',
  title: 'À la une',
  layout: 'landscape',
  mode: 'sliding',
  items: [
    {
      imageUrl: 'https://picsum.photos/600/400?random=1',
      redirectUrl: 'https://example.com/1',
      title: 'Revolut People',
      description:
        "Gérez vos employés de A à Z sur une seule et même interface. Tout centralisé, tout simplifié.",
      logoLabel: 'R',
    },
    {
      imageUrl: 'https://picsum.photos/600/400?random=2',
      redirectUrl: 'https://example.com/2',
      title: 'Équipes & productivité',
      description:
        "Productivité et suivi en temps réel. Une seule interface pour toute l'équipe.",
      logoLabel: 'A',
    },
  ],
} as const

const myAccountWidgetSchema = {
  type: 'widget',
  key: 'my_account',
  title: 'My account',
  widgetType: 'account_summary_widget',
  source: 'accounts',
  display: {
    module: 'WalletsModule',
    variant: 'default',
  },
} as const

const exclusiveOffersWidgetSchema = {
  type: 'widget',
  key: 'exclusive_offers',
  title: 'Exclusive offers',
  widgetType: 'exclusive_offers_list_widget',
  source: 'projects',
  filter: { status: 'published', visibility: 'exclusive' },
  orderBy: 'publishedAt_desc',
  display: {
    module: 'ExclusiveOffersCarousel',
    variant: 'default',
  },
} as const

const newsALaUneWidgetSchema = {
  type: 'widget',
  key: 'news_a_la_une',
  title: 'News Blog à la Une',
  widgetType: 'news_list_widget',
  source: 'news',
  filter: { status: 'published' },
  orderBy: 'publishedAt_desc',
  limit: 10,
  display: {
    module: 'BlogALaUne',
    variant: 'default',
  },
} as const

const newsAnalysisWidgetSchema = {
  type: 'widget',
  key: 'news_analysis',
  title: 'Analyses',
  widgetType: 'news_list_widget',
  source: 'news',
  filter: { status: 'published', articleType: 'ANALYSIS' },
  orderBy: 'publishedAt_desc',
  limit: 10,
  display: {
    module: 'BlogALaUne',
    variant: 'default',
  },
} as const

const transactionLatest10WidgetSchema = {
  type: 'widget',
  key: 'transaction_latest10',
  title: 'Transaction latest 10',
  widgetType: 'transaction_latest10_widget',
  source: 'mock_transactions',
  walletId: 0,
  limit: 10,
  display: {
    module: 'TransactionLatest10Module',
    variant: 'default',
  },
} as const

const marketingCardsSmallCarouselWidgetSchema = {
  type: 'widget',
  key: 'marketing_cards_small_carousel',
  title: 'Marketing cards small carousel',
  widgetType: 'marketing_cards_small_carousel_widget',
  display: {
    module: 'MarketingCardsSmallCarouselModule',
    variant: 'small',
  },
  config: {
    showDots: true,
    items: [
      {
        title: 'Investir mon argent',
        description: 'Découvrir les opportunités d\'investissement Vancelian',
        icon: 'trending_up_rounded',
        iconBackgroundColor: '#2E7D32',
        redirectUrl: 'https://example.com/invest',
      },
      {
        title: 'Faire mon premier Dépôt dans l\'application',
        description: 'Consulter l\'IBAN de dépôt',
        icon: 'savings_rounded',
        iconBackgroundColor: '#FB8C00',
        redirectUrl: 'https://example.com/deposit',
      },
    ],
  },
} as const

const widgetTableInformationSchema = {
  type: 'widget',
  key: 'widget_table_information',
  title: 'Widget Table Information',
  widgetType: 'table_information_widget',
  display: {
    module: 'TableInformationModule',
    variant: 'default',
  },
  config: {
    titleOptional: true,
    rows: [
      { label: 'Transaction ID', source: 'transactionId' },
      { label: 'Devise', source: 'currency', fallback: 'EUR' },
      { label: 'Pays', source: 'country', fallback: 'Netherlands' },
      { label: 'Carte utilisée', source: 'cardMasked', fallback: '•••• 4621' },
      { label: 'Montant débité', source: 'amount' },
    ],
  },
} as const

const competitiveAdvantagesWidgetSchema = {
  type: 'widget',
  key: 'competitive_advantages',
  title: 'Competitive advantages',
  widgetType: 'competitive_advantages_widget',
  display: {
    module: 'CompetitiveAdvantagesModule',
    variant: 'default',
  },
  config: {
    titleOptional: true,
    title: 'Why Dubai? Why now?',
    rows: [
      {
        icon: 'assignment_turned_in_rounded',
        iconBackgroundColor: '#1E88E5',
        title: 'Une croissance immobilière exceptionnelle :',
        description:
          'Le marché de Dubaï affiche une progression record de +20,7% en 2024, portée par une demande internationale soutenue et une expansion remarquable du segment ultra-luxe (+35 %).',
      },
      {
        icon: 'favorite_rounded',
        iconBackgroundColor: '#E91E63',
        title: 'L\'attractivité fiscale de Dubaï renforce la rentabilité du projet :',
        description:
          'Une fiscalité avantageuse sur les plus-values immobilières qui se traduit par un rendement plus compétitif pour chaque investisseur.',
      },
      {
        icon: 'trending_up_rounded',
        iconBackgroundColor: '#43A047',
        title: 'Un afflux massif de capitaux internationaux',
        description:
          'Porté par un cadre réglementaire stable et attractif : le nombre de résidents fortunés à Dubaï a progressé de +78% en cinq ans, soutenant la croissance continue du marché immobilier premium.',
      },
      {
        icon: 'apartment_rounded',
        iconBackgroundColor: '#7E57C2',
        title: 'Une vision stratégique long terme :',
        description:
          'Le plan Dubaï 2040 prévoit des investissements majeurs dans les infrastructures et l\'amélioration continue de la qualité de vie, consolidant l\'attractivité de la ville comme hub mondial d\'investissement.',
      },
    ],
  },
} as const

const stepsDateWidgetSchema = {
  type: 'widget',
  key: 'steps_date',
  title: 'Steps date',
  widgetType: 'steps_date_widget',
  display: {
    module: 'StepsModuleWidget',
    variant: 'project_milestones',
  },
  config: {
    title: 'Project milestones',
    source: 'project_milestone_articles',
    orderBy: 'publishedAt_asc',
    dynamicItems: true,
  },
} as const

const descriptionWidgetSchema = {
  type: 'widget',
  key: 'description',
  title: 'Description',
  widgetType: 'description_widget',
  display: {
    module: 'DescriptionModule',
    variant: 'default',
  },
  config: {
    source: 'project.description',
    linksSource: 'project.description_links',
    showTitle: false,
  },
} as const

const howItWorksWidgetSchema = {
  type: 'widget',
  key: 'how_it_works',
  title: 'How it works',
  widgetType: 'how_it_works_widget',
  display: {
    module: 'DescriptionModule',
    variant: 'default',
  },
  config: {
    source: 'project.how_it_works',
    showTitle: true,
  },
} as const

const projectNewsWidgetSchema = {
  type: 'widget',
  key: 'project_news',
  title: 'Project news',
  widgetType: 'project_news_widget',
  display: {
    module: 'BlogALaUne',
    variant: 'project',
  },
  config: {
    source: 'project_articles',
    title: 'News about this project',
  },
} as const

const helpSearchWidgetSchema = {
  type: 'widget',
  key: 'help_search',
  title: 'Help search',
  widgetType: 'help_search_widget',
  display: {
    module: 'HelpSearchModule',
    variant: 'default',
  },
  config: {
    source: '/api/help/search',
    minChars: 2,
    debounceMs: 300,
    placeholder: 'Search in FAQ...',
    showSuggestions: true,
  },
} as const

const helpCategoriesWidgetSchema = {
  type: 'widget',
  key: 'help_categories',
  title: 'Help categories',
  widgetType: 'help_categories_widget',
  display: {
    module: 'HelpCategoriesModule',
    variant: 'chips',
  },
  config: {
    source: '/api/help/collections',
    showCounts: true,
    mode: 'filter',
  },
} as const

const helpArticleListWidgetSchema = {
  type: 'widget',
  key: 'help_article_list',
  title: 'Help article list',
  widgetType: 'help_article_list_widget',
  display: {
    module: 'HelpArticleListModule',
    variant: 'rows',
  },
  config: {
    source: '/api/help/search',
    emptyStateTitle: 'No result found',
    emptyStateDescription: 'Try another keyword or category',
    itemAction: 'open_help_article',
  },
} as const

const faqAccordionWidgetSchema = {
  type: 'widget',
  key: 'faq_accordion',
  title: 'FAQ accordion',
  widgetType: 'faq_accordion_widget',
  display: {
    module: 'FaqAccordionModule',
    variant: 'default',
  },
  config: {
    source: 'help_articles',
    titleField: 'question',
    contentField: 'answer',
    allowMultiExpanded: false,
    showReadMoreLink: true,
  },
} as const

const helpCollectionListWidgetSchema = {
  type: 'widget',
  key: 'help_collection_list',
  title: 'Help collection list',
  widgetType: 'help_collection_list_widget',
  display: {
    module: 'HelpCircleListModule',
    variant: 'revolut_home',
  },
  config: {
    source: '/api/help/collections',
    itemIconMode: 'from_slug',
    itemAction: 'open_help_collection',
  },
} as const

const helpChevronListWidgetSchema = {
  type: 'widget',
  key: 'help_chevron_list',
  title: 'Help chevron list',
  widgetType: 'help_chevron_list_widget',
  display: {
    module: 'HelpChevronListModule',
    variant: 'revolut_list',
  },
  config: {
    source: 'dynamic',
    itemAction: 'open_next_level',
    showCardContainer: true,
  },
} as const

const helpArticleReaderWidgetSchema = {
  type: 'widget',
  key: 'help_article_reader',
  title: 'Help article reader',
  widgetType: 'help_article_reader_widget',
  display: {
    module: 'HelpArticleReaderModule',
    variant: 'revolut_reader',
  },
  config: {
    source: 'help_article_detail',
    supportsBlocks: ['HEADING', 'PARAGRAPH', 'QUOTE', 'BULLET_LIST', 'IMAGE', 'DOCUMENT'],
  },
} as const

const modaleComponentSchema = {
  type: 'component',
  key: 'modale',
  title: 'Modale',
  widgetType: 'modal_component',
  display: {
    module: 'Modale',
    variant: 'bottom_sheet',
  },
  config: {
    icon: {
      enabled: true,
      icon: 'info_outline',
      circleColor: '#000000',
      iconColor: '#FFFFFF',
      size: 64,
    },
    title: {
      required: true,
      value: 'Complétez votre numéro fiscal',
    },
    description: {
      enabled: true,
      value:
        "Afin de respecter les nouvelles obligations réglementaires (DAC8), nous devons collecter votre Numéro d'Identification Fiscal (NIF).",
      textAlign: 'center',
    },
    rows: [
      { label: 'Par virement bancaire', action: 'deposit_virement', showChevron: true },
      { label: 'Par carte bancaire', action: 'deposit_card', showChevron: true },
      { label: 'Par transfert crypto', action: 'deposit_crypto', showChevron: true },
    ],
    buttons: {
      primary: {
        enabled: true,
        label: 'Mettre à jour mon compte',
        action: 'primary_action',
      },
      secondary: {
        enabled: true,
        label: 'Annuler',
        action: 'close_modal',
      },
    },
  },
} as const

const donutsChartBigSchema = {
  type: 'component',
  key: 'donuts_chart_big',
  title: 'Donuts chart (big)',
  widgetType: 'donuts_chart_widget',
  layout: 'top_donut_bottom_legend',
  maxItems: 12,
  items: [
    { label: 'Energy', percentage: 38.2, colorHex: '#374151' },
    { label: 'Real estate', percentage: 28.5, colorHex: '#6B7280' },
    { label: 'Crypto', percentage: 15.0, colorHex: '#9CA3AF' },
    { label: 'Stablecoins', percentage: 10.3, colorHex: '#D1D5DB' },
    { label: 'Equity', percentage: 5.7, colorHex: '#E5E7EB' },
    { label: 'Others', percentage: 2.3, colorHex: '#CBD5E1' },
  ],
} as const

const donutsChartSmallSchema = {
  type: 'component',
  key: 'donuts_chart_small',
  title: 'Donuts chart (small)',
  widgetType: 'donuts_chart_widget',
  layout: 'left_donut_right_legend',
  maxItems: 4,
  items: [
    { label: 'Energy', percentage: 38, colorHex: '#374151' },
    { label: 'Real estate', percentage: 29, colorHex: '#6B7280' },
    { label: 'Crypto', percentage: 18, colorHex: '#9CA3AF' },
    { label: 'Stablecoins', percentage: 15, colorHex: '#D1D5DB' },
  ],
} as const

const dashboardLayoutSchema = {
  type: 'layout',
  name: 'Dashboard principal',
  doc: 'DashboardScrollTemplate',
  structure: {
    navbar: {
      position: 'top',
      fixed: true,
      left: ['profile'],
      right: ['statistics', 'notifications'],
    },
    header: {
      position: 'below_navbar',
      elements: ['balance', 'line_chart', 'action_buttons'],
      background: {
        type: 'image',
        imageUrl:
          'https://arquantix-media.c5bf9aa04c0f3a5c13ba03e78ac187d0.r2.cloudflarestorage.com/media/1772795246268-gxbcp2l3z2o.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=14dedfe39e6b51571fd87b414f348c50%2F20260306%2Fauto%2Fs3%2Faws4_request&X-Amz-Date=20260306T110727Z&X-Amz-Expires=3600&X-Amz-Signature=5c875d7ddb81a209cf495e4b19bbb51586865aa98c9f4992a1b5511f2cccc3e9&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject',
        fit: 'cover',
        overlay: { color: '#0D1B2A', opacity: 0.32 },
      },
      balance: {
        source: 'wallet_summary',
        fields: ['totalBalance', 'dailyChange', 'currency'],
      },
      line_chart: {
        source: 'portfolio_history',
        timeframeOptions: ['1D', '1W', '1M', '1Y'],
      },
      action_buttons: ['deposit', 'withdraw', 'transfer', 'more'],
    },
    body: {
      scrollable: true,
      widgets: [
        {
          key: 'my_account',
          title: 'My account',
          type: 'account_summary_widget',
          source: 'accounts',
        },
        {
          key: 'exclusive_offers',
          title: 'Exclusive offers',
          type: 'exclusive_offers_list_widget',
          source: 'projects',
          filter: { status: 'published', visibility: 'exclusive' },
          orderBy: 'publishedAt_desc',
        },
        {
          key: 'top10news_widget',
          title: 'Vancelian News',
          type: 'widget_builder_widget',
          widgetSlug: 'top10news',
        },
        {
          key: 'transaction_latest10',
          title: 'Latest transactions',
          type: 'transaction_latest10_widget',
          source: 'mock_transactions',
          walletId: 0,
          limit: 10,
        },
        {
          key: 'news_a_la_une',
          title: 'News à la Une',
          type: 'news_list_widget',
          source: 'news',
          filter: { status: 'published' },
          orderBy: 'publishedAt_desc',
          limit: 10,
        },
        {
          key: 'news_analysis',
          title: 'Analyses',
          type: 'news_list_widget',
          source: 'news',
          filter: { status: 'published', articleType: 'ANALYSIS' },
          orderBy: 'publishedAt_desc',
          limit: 10,
        },
      ],
    },
  },
  flutterPath: 'lib/features/dashboard/presentation/screens/dashboard_screen.dart',
} as const

const euroAccountLayoutSchema = {
  type: 'layout',
  name: 'Compte Euro',
  doc: 'EuroAccountTemplate',
  structure: {
    navbar: {
      position: 'top',
      fixed: true,
      left: ['back_button'],
      right: ['statistics', 'notifications'],
    },
    header: {
      position: 'below_navbar',
      background: {
        type: 'image',
        imageUrl: 'media/1774374454390-c4ghm1rvq2v.png',
        fit: 'cover',
        color: '#0D1B2A',
      },
      balance: {
        title: 'Euro',
        amount: '146\u202f715,82 €',
        asset: {
          symbol: '€',
          backgroundColor: '#1E88E5',
        },
        iban: {
          show: true,
          label: 'IBAN: FR76 1234 5678 90…',
          redirectUrl: 'https://example.com/iban',
        },
      },
      performance: {
        show: false,
      },
      line_chart: {
        show: false,
      },
      action_buttons: [
        { key: 'deposit', label: 'Déposer', icon: 'add_rounded', redirectUrl: 'https://example.com/deposit' },
        { key: 'withdraw', label: 'Retirer', icon: 'remove_rounded', redirectUrl: 'https://example.com/withdraw' },
        { key: 'iban', label: 'IBAN', icon: 'account_balance_rounded', redirectUrl: 'https://example.com/iban' },
        { key: 'statements', label: 'Relevés', icon: 'description_rounded', redirectUrl: 'https://example.com/statements' },
      ],
    },
    body: {
      modules: ['marketing_cards_small_carousel', 'transaction_latest10'],
      marketingCardsSmallCarousel: {
        key: 'marketing_cards_small_carousel',
        type: 'marketing_cards_small_carousel_widget',
        showDots: true,
        items: [
          {
            title: 'Investir mon argent',
            description: 'Découvrir les opportunités d\'investissement Vancelian',
            icon: 'trending_up_rounded',
            iconBackgroundColor: '#2E7D32',
            redirectUrl: 'https://example.com/invest',
          },
          {
            title: 'Faire mon premier Dépôt dans l\'application',
            description: 'Consulter l\'IBAN de dépôt',
            icon: 'savings_rounded',
            iconBackgroundColor: '#FB8C00',
            redirectUrl: 'https://example.com/deposit',
          },
        ],
      },
      transactionLatest10: {
        title: 'Transactions',
        walletId: 1,
        limit: 10,
      },
    },
  },
  flutterPath: 'lib/features/wallet/presentation/screens/compte_euro_screen.dart',
} as const

const allTransactionsLayoutSchema = {
  type: 'layout',
  name: 'All transactions',
  doc: 'AllTransactionsTemplate',
  structure: {
    header: {
      position: 'top',
      fixed: false,
      module: 'AppTopNavBar',
      left: ['back_button'],
      center: { title: 'All transactions' },
    },
    tabs: {
      position: 'below_header',
      source: 'transaction_months',
      mode: 'filter',
      appearance: {
        backgroundBlur: {
          enabled: true,
          sigmaX: 14,
          sigmaY: 14,
          tintColor: '#FFFFFF',
          tintOpacity: 0.55,
          borderColor: '#FFFFFF',
          borderOpacity: 0.35,
          borderRadius: 16,
          paddingVertical: 10,
          paddingHorizontal: 12,
        },
      },
      behavior: {
        singleSelect: true,
        default: 'current_month',
      },
    },
    body: {
      scrollable: true,
      source: 'transactions',
      groupedBy: 'day',
      filterBySelectedTab: true,
      itemType: 'transaction_row',
      itemAction: 'open_transaction_detail',
    },
  },
  flutterPath: 'lib/features/wallet/presentation/screens/transaction_list_screen.dart',
} as const

const transactionDetailLayoutSchema = {
  type: 'layout',
  name: 'Transaction details',
  doc: 'TransactionDetailTemplate',
  structure: {
    header: {
      position: 'top',
      fixed: false,
      left: ['back_button'],
      center: { title: 'Transaction details' },
    },
    body: {
      sections: {
        identity: {
          showAvatar: true,
          showMerchant: true,
          showDateTime: true,
          showCategory: true,
        },
        actions: {
          showStatus: true,
          showStatementButton: true,
        },
        detailsCard: {
          widget: {
            key: 'widget_table_information',
            type: 'table_information_widget',
            title: '',
            rows: [
              { label: 'Transaction ID', source: 'transactionId' },
              { label: 'Devise', source: 'currency', fallback: 'EUR' },
              { label: 'Pays', source: 'country', fallback: 'Netherlands' },
              { label: 'Carte utilisée', source: 'cardMasked', fallback: '•••• 4621' },
              { label: 'Montant débité', source: 'amount' },
            ],
          },
        },
        recap: {
          title: 'Transaction',
          showTile: true,
        },
      },
    },
  },
  flutterPath: 'lib/features/wallet/presentation/screens/transaction_screen.dart',
} as const

const exclusiveOfferDetailLayoutSchema = {
  type: 'layout',
  name: 'Page projet (offre exclusive)',
  doc: 'ExclusiveOfferDetailScreen',
  structure: {
    navbar: {
      position: 'top',
      fixed: true,
      left: ['back_button'],
      right: ['favorite'],
    },
    image: { ratio: '60%', area: 'top' },
    header: {
      module: 'ProjectHeroHeader',
      topNav: {
        leading: 'back',
        actions: ['favorite'],
        fixed: true,
      },
      categoryBadge: {
        show: true,
        icon: 'category_rounded',
      },
      cta: {
        primaryButton: {
          label: 'Investir',
          action: 'invest',
        },
        secondaryButtons: ['documents', 'gallery', 'teaser'],
      },
    },
    body: {
      modules: [
        'widget_table_information',
        'description',
        'how_it_works',
        'competitive_advantages',
        'steps_date',
        'faq',
        'project_news',
        'vault_documents_list',
        'vault_virtual_visualization',
        'vault_related_news',
        'video_block_article',
      ],
      description: {
        key: 'description',
        type: 'description_widget',
        source: 'project.description',
        linksSource: 'project.description_links',
        showTitle: true,
      },
      howItWorks: {
        key: 'how_it_works',
        type: 'how_it_works_widget',
        source: 'project.how_it_works',
        title: 'How it works',
      },
      tableInformation: {
        key: 'widget_table_information',
        type: 'table_information_widget',
        source: 'project.key_information',
        title: 'Informations clés',
        rows: [],
      },
      competitiveAdvantages: {
        key: 'competitive_advantages',
        type: 'competitive_advantages_widget',
        source: 'project.competitive_advantages',
      },
      stepsDate: {
        key: 'steps_date',
        type: 'steps_date_widget',
        title: 'Project milestones',
        source: 'project_milestone_articles',
        orderBy: 'publishedAt_asc',
      },
      faq: {
        key: 'faq',
        type: 'faq_accordion_widget',
        source: 'project.faq',
        title: 'FAQ',
        readMoreLabel: 'Voir toutes les FAQ de ce projet',
      },
      projectNews: {
        key: 'project_news',
        type: 'project_news_widget',
        source: 'project_articles',
        title: 'News about this project',
      },
      vaultRelatedNews: {
        key: 'vault_related_news',
        type: 'vault_related_news_widget',
        source: 'article_links.vault + module BlogALaUne',
        title: '',
      },
      videoBlockArticle: {
        key: 'video_block_article',
        type: 'video_block_article_widget',
        source: 'vault.VideoBlockArticleModule',
        title: 'Vidéos',
      },
      vaultDocumentsList: {
        key: 'vault_documents_list',
        type: 'vault_documents_list_widget',
        source: 'vault.DocumentsListModule',
        title: '',
      },
      vaultVirtualVisualization: {
        key: 'vault_virtual_visualization',
        type: 'vault_virtual_visualization_widget',
        source: 'vault.VirtualVisualizationModule',
        title: '',
      },
    },
  },
  flutterPath: 'lib/features/offers/presentation/screens/exclusive_offer_detail_screen.dart',
} as const

export async function seedDsComponents(db: PrismaClient = prisma) {
  const chapter = await db.dsComponentChapter.upsert({
    where: { slug: 'component_ds_flutter' },
    update: {},
    create: {
      name: 'component DS flutter',
      slug: 'component_ds_flutter',
      order: 0,
    },
  })
  console.log('Chapter:', chapter.slug, chapter.id)

  const component = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'marketing_cards',
      },
    },
    update: { schemaJson: marketingCardsSchema },
    create: {
      chapterId: chapter.id,
      slug: 'marketing_cards',
      name: 'Marketing cards',
      schemaJson: marketingCardsSchema,
    },
  })
  console.log('Component:', component.slug, component.id)

  const myAccountWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'my_account',
      },
    },
    update: { schemaJson: myAccountWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'my_account',
      name: 'My account',
      schemaJson: myAccountWidgetSchema,
    },
  })
  console.log('Component:', myAccountWidget.slug, myAccountWidget.id)

  const exclusiveOffersWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'exclusive_offers',
      },
    },
    update: { schemaJson: exclusiveOffersWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'exclusive_offers',
      name: 'Exclusive offers',
      schemaJson: exclusiveOffersWidgetSchema,
    },
  })
  console.log('Component:', exclusiveOffersWidget.slug, exclusiveOffersWidget.id)

  const newsALaUneWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'news_a_la_une',
      },
    },
    update: { schemaJson: newsALaUneWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'news_a_la_une',
      name: 'News Blog à la Une',
      schemaJson: newsALaUneWidgetSchema,
    },
  })
  console.log('Component:', newsALaUneWidget.slug, newsALaUneWidget.id)

  const newsAnalysisWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'news_analysis',
      },
    },
    update: { schemaJson: newsAnalysisWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'news_analysis',
      name: 'News Analyses',
      schemaJson: newsAnalysisWidgetSchema,
    },
  })
  console.log('Component:', newsAnalysisWidget.slug, newsAnalysisWidget.id)

  const transactionLatest10Widget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'transaction_latest10',
      },
    },
    update: { schemaJson: transactionLatest10WidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'transaction_latest10',
      name: 'Transaction latest 10',
      schemaJson: transactionLatest10WidgetSchema,
    },
  })
  console.log('Component:', transactionLatest10Widget.slug, transactionLatest10Widget.id)

  const marketingCardsSmallCarouselWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'marketing_cards_small_carousel',
      },
    },
    update: { schemaJson: marketingCardsSmallCarouselWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'marketing_cards_small_carousel',
      name: 'Marketing cards small carousel',
      schemaJson: marketingCardsSmallCarouselWidgetSchema,
    },
  })
  console.log('Component:', marketingCardsSmallCarouselWidget.slug, marketingCardsSmallCarouselWidget.id)

  const widgetTableInformation = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'widget_table_information',
      },
    },
    update: { schemaJson: widgetTableInformationSchema },
    create: {
      chapterId: chapter.id,
      slug: 'widget_table_information',
      name: 'Widget Table Information',
      schemaJson: widgetTableInformationSchema,
    },
  })
  console.log('Component:', widgetTableInformation.slug, widgetTableInformation.id)

  const competitiveAdvantagesWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'competitive_advantages',
      },
    },
    update: { schemaJson: competitiveAdvantagesWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'competitive_advantages',
      name: 'Competitive advantages',
      schemaJson: competitiveAdvantagesWidgetSchema,
    },
  })
  console.log('Component:', competitiveAdvantagesWidget.slug, competitiveAdvantagesWidget.id)

  const stepsDateWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'steps_date',
      },
    },
    update: { schemaJson: stepsDateWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'steps_date',
      name: 'Steps date',
      schemaJson: stepsDateWidgetSchema,
    },
  })
  console.log('Component:', stepsDateWidget.slug, stepsDateWidget.id)

  const descriptionWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'description',
      },
    },
    update: { schemaJson: descriptionWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'description',
      name: 'Description',
      schemaJson: descriptionWidgetSchema,
    },
  })
  console.log('Component:', descriptionWidget.slug, descriptionWidget.id)

  const howItWorksWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'how_it_works',
      },
    },
    update: { schemaJson: howItWorksWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'how_it_works',
      name: 'How it works',
      schemaJson: howItWorksWidgetSchema,
    },
  })
  console.log('Component:', howItWorksWidget.slug, howItWorksWidget.id)

  const projectNewsWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'project_news',
      },
    },
    update: { schemaJson: projectNewsWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'project_news',
      name: 'Project news',
      schemaJson: projectNewsWidgetSchema,
    },
  })
  console.log('Component:', projectNewsWidget.slug, projectNewsWidget.id)

  const helpSearchWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'help_search',
      },
    },
    update: { schemaJson: helpSearchWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'help_search',
      name: 'Help search',
      schemaJson: helpSearchWidgetSchema,
    },
  })
  console.log('Component:', helpSearchWidget.slug, helpSearchWidget.id)

  const helpCategoriesWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'help_categories',
      },
    },
    update: { schemaJson: helpCategoriesWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'help_categories',
      name: 'Help categories',
      schemaJson: helpCategoriesWidgetSchema,
    },
  })
  console.log('Component:', helpCategoriesWidget.slug, helpCategoriesWidget.id)

  const helpArticleListWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'help_article_list',
      },
    },
    update: { schemaJson: helpArticleListWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'help_article_list',
      name: 'Help article list',
      schemaJson: helpArticleListWidgetSchema,
    },
  })
  console.log('Component:', helpArticleListWidget.slug, helpArticleListWidget.id)

  const faqAccordionWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'faq_accordion',
      },
    },
    update: { schemaJson: faqAccordionWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'faq_accordion',
      name: 'FAQ accordion',
      schemaJson: faqAccordionWidgetSchema,
    },
  })
  console.log('Component:', faqAccordionWidget.slug, faqAccordionWidget.id)

  const helpCollectionListWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'help_collection_list',
      },
    },
    update: { schemaJson: helpCollectionListWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'help_collection_list',
      name: 'Help collection list',
      schemaJson: helpCollectionListWidgetSchema,
    },
  })
  console.log('Component:', helpCollectionListWidget.slug, helpCollectionListWidget.id)

  const helpChevronListWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'help_chevron_list',
      },
    },
    update: { schemaJson: helpChevronListWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'help_chevron_list',
      name: 'Help chevron list',
      schemaJson: helpChevronListWidgetSchema,
    },
  })
  console.log('Component:', helpChevronListWidget.slug, helpChevronListWidget.id)

  const helpArticleReaderWidget = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'help_article_reader',
      },
    },
    update: { schemaJson: helpArticleReaderWidgetSchema },
    create: {
      chapterId: chapter.id,
      slug: 'help_article_reader',
      name: 'Help article reader',
      schemaJson: helpArticleReaderWidgetSchema,
    },
  })
  console.log('Component:', helpArticleReaderWidget.slug, helpArticleReaderWidget.id)

  const modaleComponent = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'modale',
      },
    },
    update: { schemaJson: modaleComponentSchema },
    create: {
      chapterId: chapter.id,
      slug: 'modale',
      name: 'Modale',
      schemaJson: modaleComponentSchema,
    },
  })
  console.log('Component:', modaleComponent.slug, modaleComponent.id)

  const donutsChartBig = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'donuts_chart_big',
      },
    },
    update: { schemaJson: donutsChartBigSchema },
    create: {
      chapterId: chapter.id,
      slug: 'donuts_chart_big',
      name: 'Donuts chart big',
      schemaJson: donutsChartBigSchema,
    },
  })
  console.log('Component:', donutsChartBig.slug, donutsChartBig.id)

  const donutsChartSmall = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'donuts_chart_small',
      },
    },
    update: { schemaJson: donutsChartSmallSchema },
    create: {
      chapterId: chapter.id,
      slug: 'donuts_chart_small',
      name: 'Donuts chart small',
      schemaJson: donutsChartSmallSchema,
    },
  })
  console.log('Component:', donutsChartSmall.slug, donutsChartSmall.id)

  const dashboardLayout = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'dashboard_layout',
      },
    },
    update: { schemaJson: dashboardLayoutSchema },
    create: {
      chapterId: chapter.id,
      slug: 'dashboard_layout',
      name: 'Dashboard layout',
      schemaJson: dashboardLayoutSchema,
    },
  })
  console.log('Component:', dashboardLayout.slug, dashboardLayout.id)

  const euroAccountLayout = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'euro_account_layout',
      },
    },
    update: { schemaJson: euroAccountLayoutSchema },
    create: {
      chapterId: chapter.id,
      slug: 'euro_account_layout',
      name: 'Euro account layout',
      schemaJson: euroAccountLayoutSchema,
    },
  })
  console.log('Component:', euroAccountLayout.slug, euroAccountLayout.id)

  const allTransactionsLayout = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'all_transactions_layout',
      },
    },
    update: { schemaJson: allTransactionsLayoutSchema },
    create: {
      chapterId: chapter.id,
      slug: 'all_transactions_layout',
      name: 'All transactions layout',
      schemaJson: allTransactionsLayoutSchema,
    },
  })
  console.log('Component:', allTransactionsLayout.slug, allTransactionsLayout.id)

  const transactionDetailLayout = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'transaction_detail_layout',
      },
    },
    update: { schemaJson: transactionDetailLayoutSchema },
    create: {
      chapterId: chapter.id,
      slug: 'transaction_detail_layout',
      name: 'Transaction detail layout',
      schemaJson: transactionDetailLayoutSchema,
    },
  })
  console.log('Component:', transactionDetailLayout.slug, transactionDetailLayout.id)

  const exclusiveOfferDetailLayout = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'exclusive_offer_detail_layout',
      },
    },
    update: { schemaJson: exclusiveOfferDetailLayoutSchema },
    create: {
      chapterId: chapter.id,
      slug: 'exclusive_offer_detail_layout',
      name: 'Exclusive offer detail layout',
      schemaJson: exclusiveOfferDetailLayoutSchema,
    },
  })
  console.log('Component:', exclusiveOfferDetailLayout.slug, exclusiveOfferDetailLayout.id)
}

function isExecutedAsCliScript(): boolean {
  const entry = process.argv[1]
  if (!entry) return false
  try {
    return import.meta.url === pathToFileURL(entry).href
  } catch {
    return false
  }
}

if (isExecutedAsCliScript()) {
  seedDsComponents()
    .then(() => prisma.$disconnect())
    .catch((e) => {
      console.error(e)
      prisma.$disconnect()
      process.exit(1)
    })
}
