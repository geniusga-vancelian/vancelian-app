/** Généré depuis ui_kits/vancelian-app/index.html — ne pas éditer à la main. */
export type AppDsShowcaseItem = {
  title: string
  file: string
  height: number
  openHref?: string
}

export type AppDsShowcaseSection = {
  id: string
  num: string
  title: string
  count?: string
  items: AppDsShowcaseItem[]
}

export const APP_DS_SHOWCASE_SECTIONS: AppDsShowcaseSection[] = [
  {
    "id": "brand",
    "num": "01",
    "title": "Brand",
    "count": "2 assets",
    "items": [
      {
        "title": "Logo lockups",
        "file": "22-logos.html",
        "height": 280,
        "openHref": "preview/22-logos.html"
      },
      {
        "title": "Iconography — Kalai line set",
        "file": "23-iconography.html",
        "height": 640,
        "openHref": "preview/23-iconography.html"
      }
    ]
  },
  {
    "id": "colors",
    "num": "02",
    "title": "Colors",
    "count": "3 assets",
    "items": [
      {
        "title": "Triade — terracotta · vert anglais · bleu de Prusse",
        "file": "01-colors-triade.html",
        "height": 280
      },
      {
        "title": "Backgrounds — paper, warm, dark",
        "file": "02-colors-bg.html",
        "height": 280
      },
      {
        "title": "Foregrounds — anthracite scale",
        "file": "03-colors-fg.html",
        "height": 280
      }
    ]
  },
  {
    "id": "type",
    "num": "03",
    "title": "Type",
    "count": "3 assets",
    "items": [
      {
        "title": "Display, section, title — Newsreader + Inter SemiBold",
        "file": "04-type-display.html",
        "height": 320
      },
      {
        "title": "Body, caption, eyebrow — Regular + SemiBold",
        "file": "05-type-body.html",
        "height": 380
      },
      {
        "title": "Amounts — Inter SemiBold + tabular-nums",
        "file": "06-type-amount.html",
        "height": 280
      }
    ]
  },
  {
    "id": "spacing",
    "num": "04",
    "title": "Spacing & surfaces",
    "count": "3 assets",
    "items": [
      {
        "title": "Spacing scale — 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64",
        "file": "07-spacing.html",
        "height": 260
      },
      {
        "title": "Radius — 4 / 6 / 8 / 12 / 24 / pill",
        "file": "08-radius.html",
        "height": 260
      },
      {
        "title": "Elevation — flat · subtle · medium (border always)",
        "file": "09-elevation.html",
        "height": 280
      }
    ]
  },
  {
    "id": "simple",
    "num": "05",
    "title": "Simple — atomic primitives",
    "count": "18 assets",
    "items": [
      {
        "title": "Buttons — primary sizes (32 / 40 / 52)",
        "file": "10-buttons-primary.html",
        "height": 340,
        "openHref": "preview/10-buttons-primary.html"
      },
      {
        "title": "Buttons — variants (primary · secondary · ghost · link · destructive · icons)",
        "file": "11-buttons-variants.html",
        "height": 320,
        "openHref": "preview/11-buttons-variants.html"
      },
      {
        "title": "Circle FAB — dark / white / terracotta",
        "file": "12-fab.html",
        "height": 280,
        "openHref": "preview/12-fab.html"
      },
      {
        "title": "Toggle · Radio · Checkbox",
        "file": "13-controls.html",
        "height": 320,
        "openHref": "preview/13-controls.html"
      },
      {
        "title": "Inputs — anatomy + states (default / filled / focus / disabled / error)",
        "file": "14-inputs.html",
        "height": 900,
        "openHref": "preview/14-inputs.html"
      },
      {
        "title": "Tags · chips · badges (tinted · inverted · category · numeric)",
        "file": "15-tags.html",
        "height": 500,
        "openHref": "preview/15-tags.html"
      },
      {
        "title": "Avatars — initials / photo / icon · 6 sizes · status + stack",
        "file": "16-avatars.html",
        "height": 760,
        "openHref": "preview/16-avatars.html"
      },
      {
        "title": "Avatar — exchange paire (crypto/fiat)",
        "file": "41-avatar-exchange.html",
        "height": 940,
        "openHref": "preview/41-avatar-exchange.html"
      },
      {
        "title": "Amount display — value + currency + MAX + sub",
        "file": "43-amount-display.html",
        "height": 1340,
        "openHref": "preview/43-amount-display.html"
      },
      {
        "title": "Selection chips (tinted · inverted · category · emoji)",
        "file": "50-selection-chips.html",
        "height": 780,
        "openHref": "preview/50-selection-chips.html"
      },
      {
        "title": "Variant picker — swatches pill",
        "file": "52-variant-picker.html",
        "height": 640,
        "openHref": "preview/52-variant-picker.html"
      },
      {
        "title": "Suggested chips — horizontal quick-actions",
        "file": "58-suggested-chips.html",
        "height": 420,
        "openHref": "preview/58-suggested-chips.html"
      },
      {
        "title": "Onboarding indicators — progress dots & steps",
        "file": "62-onboarding-indicators.html",
        "height": 420,
        "openHref": "preview/62-onboarding-indicators.html"
      },
      {
        "title": "OTP input — 4 / 6 digit code (default · filled · error)",
        "file": "70-otp-input.html",
        "height": 560,
        "openHref": "preview/70-otp-input.html"
      },
      {
        "title": "Slider · range — value scrub + dual handles",
        "file": "75-slider-range.html",
        "height": 720,
        "openHref": "preview/75-slider-range.html"
      },
      {
        "title": "Dropdown · select — closed / open / multi-select",
        "file": "77-dropdown-select.html",
        "height": 820,
        "openHref": "preview/77-dropdown-select.html"
      },
      {
        "title": "Pagination — pages, chevrons, load-more",
        "file": "78-pagination.html",
        "height": 640,
        "openHref": "preview/78-pagination.html"
      },
      {
        "title": "Date picker — month grid + range",
        "file": "80-date-picker.html",
        "height": 1140,
        "openHref": "preview/80-date-picker.html"
      }
    ]
  },
  {
    "id": "ui",
    "num": "06",
    "title": "UI — page chrome & navigation",
    "count": "11 assets",
    "items": [
      {
        "title": "Top app bar — 8 états (basic · sheet · stepper · welcome · asset · hero)",
        "file": "40-topappbar.html",
        "height": 1340,
        "openHref": "preview/40-topappbar.html"
      },
      {
        "title": "Bottom tab bar — iOS-26 floating glass capsule",
        "file": "21-tabbar.html",
        "height": 380,
        "openHref": "preview/21-tabbar.html"
      },
      {
        "title": "Segmented · pagination dots",
        "file": "20-segmented-dots.html",
        "height": 320,
        "openHref": "preview/20-segmented-dots.html"
      },
      {
        "title": "Account picker row — colored avatar + balance + chevron",
        "file": "44-account-picker.html",
        "height": 640,
        "openHref": "preview/44-account-picker.html"
      },
      {
        "title": "Action bar — leading icon + CTA pill",
        "file": "45-action-bar.html",
        "height": 700,
        "openHref": "preview/45-action-bar.html"
      },
      {
        "title": "CTA stack — primary + secondary 56px",
        "file": "55-cta-stack.html",
        "height": 940,
        "openHref": "preview/55-cta-stack.html"
      },
      {
        "title": "Chat composer — input + mic + send",
        "file": "57-chat-composer.html",
        "height": 400,
        "openHref": "preview/57-chat-composer.html"
      },
      {
        "title": "Detail page header — crypto / bundle / euro / hero / article",
        "file": "64-detail-header.html",
        "height": 2400,
        "openHref": "preview/64-detail-header.html"
      },
      {
        "title": "Section title — eyebrow + title + actions (sizes & variants)",
        "file": "68-section-title.html",
        "height": 1480,
        "openHref": "preview/68-section-title.html"
      },
      {
        "title": "Bottom sheet — handle · content · action stack",
        "file": "69-bottom-sheet.html",
        "height": 780,
        "openHref": "preview/69-bottom-sheet.html"
      },
      {
        "title": "Coach mark · tooltip — onboarding hints (anchored)",
        "file": "86-coach-mark-tooltip.html",
        "height": 900,
        "openHref": "preview/86-coach-mark-tooltip.html"
      }
    ]
  },
  {
    "id": "cards",
    "num": "07",
    "title": "Cards",
    "count": "46 assets",
    "items": [
      {
        "title": "List items — transactions (asset rows + indicators)",
        "file": "17-list-transactions.html",
        "height": 640,
        "openHref": "preview/17-list-transactions.html"
      },
      {
        "title": "Semantic banners — success · warning (safran) · info · error · neutral",
        "file": "18-banners.html",
        "height": 500,
        "openHref": "preview/18-banners.html"
      },
      {
        "title": "Balance card — dashboard hero (dark + light)",
        "file": "19-balance-card.html",
        "height": 1280,
        "openHref": "preview/19-balance-card.html"
      },
      {
        "title": "Card — offre exclusive (square + marketing banner)",
        "file": "24-card-offre-exclusive.html",
        "height": 1080,
        "openHref": "preview/24-card-offre-exclusive.html"
      },
      {
        "title": "Card — nouveauté",
        "file": "25-card-nouveaute.html",
        "height": 320,
        "openHref": "preview/25-card-nouveaute.html"
      },
      {
        "title": "Cards — Flash Info & Actu (decks horizontaux)",
        "file": "26-cards-flash-actu.html",
        "height": 900,
        "openHref": "preview/26-cards-flash-actu.html"
      },
      {
        "title": "Card — funding (status + investors)",
        "file": "31-card-funding.html",
        "height": 700,
        "openHref": "preview/31-card-funding.html"
      },
      {
        "title": "Card — AI tip (warm card · IA recommendation)",
        "file": "32-card-ai-tip.html",
        "height": 260,
        "openHref": "preview/32-card-ai-tip.html"
      },
      {
        "title": "Card — metrics list (default + icons + separators)",
        "file": "33-card-data-list.html",
        "height": 980,
        "openHref": "preview/33-card-data-list.html"
      },
      {
        "title": "Card — step \"How it works\"",
        "file": "34-card-step-how.html",
        "height": 380,
        "openHref": "preview/34-card-step-how.html"
      },
      {
        "title": "Card — pillars (icon rows)",
        "file": "35-card-icon-rows.html",
        "height": 700,
        "openHref": "preview/35-card-icon-rows.html"
      },
      {
        "title": "Card — property overview (long-form text card)",
        "file": "36-card-property-overview.html",
        "height": 600,
        "openHref": "preview/36-card-property-overview.html"
      },
      {
        "title": "Card — exit window (closed · open · terms)",
        "file": "37-card-exit-window.html",
        "height": 780,
        "openHref": "preview/37-card-exit-window.html"
      },
      {
        "title": "Card — document (PDF) — action-row shell + CTA",
        "file": "38-card-document.html",
        "height": 780,
        "openHref": "preview/38-card-document.html"
      },
      {
        "title": "Card — action row family (chevron / text / button / toggle / check / radio)",
        "file": "39-card-action-row.html",
        "height": 1180,
        "openHref": "preview/39-card-action-row.html"
      },
      {
        "title": "Card — conversion analysis (numbered steps connected)",
        "file": "42-card-conversion-analysis.html",
        "height": 420,
        "openHref": "preview/42-card-conversion-analysis.html"
      },
      {
        "title": "Validation sheet — processing / success / error",
        "file": "47-validation-sheet.html",
        "height": 1660,
        "openHref": "preview/47-validation-sheet.html"
      },
      {
        "title": "List — flag picker (chevron / radio / checkbox)",
        "file": "49-list-flag-picker.html",
        "height": 980,
        "openHref": "preview/49-list-flag-picker.html"
      },
      {
        "title": "Chat — message bubbles (user / AI / rich)",
        "file": "56-chat-bubble.html",
        "height": 1240,
        "openHref": "preview/56-chat-bubble.html"
      },
      {
        "title": "Chart module — line + candle variants",
        "file": "66-chart-module.html",
        "height": 900,
        "openHref": "preview/66-chart-module.html"
      },
      {
        "title": "Card — FAQ row (collapsed · expanded)",
        "file": "27-card-faq.html",
        "height": 420,
        "openHref": "preview/27-card-faq.html"
      },
      {
        "title": "Card — stepper (numbered multi-step)",
        "file": "28-card-stepper.html",
        "height": 640,
        "openHref": "preview/28-card-stepper.html"
      },
      {
        "title": "Card — map embed (location preview)",
        "file": "29-card-googlemap.html",
        "height": 600,
        "openHref": "preview/29-card-googlemap.html"
      },
      {
        "title": "Image carousel — pagination dots + arrows",
        "file": "30-image-carousel.html",
        "height": 460,
        "openHref": "preview/30-image-carousel.html"
      },
      {
        "title": "Credit card visual — virtual / physical / dark",
        "file": "51-credit-card-visual.html",
        "height": 1100,
        "openHref": "preview/51-credit-card-visual.html"
      },
      {
        "title": "Auth provider stack — Apple / Google / mail buttons",
        "file": "59-auth-provider-stack.html",
        "height": 680,
        "openHref": "preview/59-auth-provider-stack.html"
      },
      {
        "title": "Crypto grid item — sparkline tile",
        "file": "60-crypto-grid-item.html",
        "height": 520,
        "openHref": "preview/60-crypto-grid-item.html"
      },
      {
        "title": "AI prompt cards — quick suggestions",
        "file": "61-prompt-cards.html",
        "height": 700,
        "openHref": "preview/61-prompt-cards.html"
      },
      {
        "title": "Search results — query input + hits list",
        "file": "63-search-result-list.html",
        "height": 820,
        "openHref": "preview/63-search-result-list.html"
      },
      {
        "title": "Card — account summary (multi-currency)",
        "file": "67-card-account.html",
        "height": 720,
        "openHref": "preview/67-card-account.html"
      },
      {
        "title": "Toast · snackbar — neutral / success / warning / error",
        "file": "73-toast-snackbar.html",
        "height": 780,
        "openHref": "preview/73-toast-snackbar.html"
      },
      {
        "title": "Confirmation dialog — destructive · neutral · info",
        "file": "74-confirmation-dialog.html",
        "height": 720,
        "openHref": "preview/74-confirmation-dialog.html"
      },
      {
        "title": "Receipt — transaction detail (status + breakdown)",
        "file": "81-receipt-detail.html",
        "height": 1080,
        "openHref": "preview/81-receipt-detail.html"
      },
      {
        "title": "Settings — list rows (label / sublabel / control)",
        "file": "83-settings-list-row.html",
        "height": 900,
        "openHref": "preview/83-settings-list-row.html"
      },
      {
        "title": "Help advisor — talk to your conseiller",
        "file": "87-help-advisor-card.html",
        "height": 860,
        "openHref": "preview/87-help-advisor-card.html"
      },
      {
        "title": "Document upload — empty · uploading · uploaded · error",
        "file": "88-document-upload.html",
        "height": 1120,
        "openHref": "preview/88-document-upload.html"
      },
      {
        "title": "Bar chart — daily gains (week / month / year)",
        "file": "89-bar-chart.html",
        "height": 1320,
        "openHref": "preview/89-bar-chart.html"
      },
      {
        "title": "Order book — bid / ask ladder",
        "file": "90-order-book.html",
        "height": 820,
        "openHref": "preview/90-order-book.html"
      },
      {
        "title": "Allocation donut — portfolio split",
        "file": "91-allocation-donut.html",
        "height": 680,
        "openHref": "preview/91-allocation-donut.html"
      },
      {
        "title": "Budget progress — usage bar + threshold",
        "file": "92-budget-progress.html",
        "height": 900,
        "openHref": "preview/92-budget-progress.html"
      },
      {
        "title": "Beneficiary list — saved transfers (chevron · star)",
        "file": "93-beneficiary-list.html",
        "height": 1040,
        "openHref": "preview/93-beneficiary-list.html"
      },
      {
        "title": "IBAN block — copy / share / mask",
        "file": "94-iban-block.html",
        "height": 860,
        "openHref": "preview/94-iban-block.html"
      },
      {
        "title": "QR code — receive / share variants",
        "file": "95-qr-code.html",
        "height": 1100,
        "openHref": "preview/95-qr-code.html"
      },
      {
        "title": "Card management — settings rows (freeze / limit / pin)",
        "file": "96-card-management.html",
        "height": 1100,
        "openHref": "preview/96-card-management.html"
      },
      {
        "title": "Referral — share code + rewards",
        "file": "97-referral-card.html",
        "height": 620,
        "openHref": "preview/97-referral-card.html"
      },
      {
        "title": "Notifications — grouped list (today · earlier)",
        "file": "98-notification-list.html",
        "height": 1240,
        "openHref": "preview/98-notification-list.html"
      }
    ]
  },
  {
    "id": "misc",
    "num": "08",
    "title": "Misc — heroes, illustrations, forms",
    "count": "8 assets",
    "items": [
      {
        "title": "Numpad — iOS-style (T9 + plain)",
        "file": "46-numpad-ios.html",
        "height": 960,
        "openHref": "preview/46-numpad-ios.html"
      },
      {
        "title": "Form question block — eyebrow + title + description",
        "file": "48-form-question-block.html",
        "height": 640,
        "openHref": "preview/48-form-question-block.html"
      },
      {
        "title": "Notification illustration (permission gate hero)",
        "file": "53-notification-illustration.html",
        "height": 960,
        "openHref": "preview/53-notification-illustration.html"
      },
      {
        "title": "Onboarding hero — Inter Bold + Newsreader Italic",
        "file": "54-onboarding-hero.html",
        "height": 1140,
        "openHref": "preview/54-onboarding-hero.html"
      },
      {
        "title": "Article blocks — paragraph · quote · image · video · key/value · author · docs",
        "file": "65-article-blocks.html",
        "height": 2400,
        "openHref": "preview/65-article-blocks.html"
      },
      {
        "title": "Empty state — illustration + title + CTA",
        "file": "71-empty-state.html",
        "height": 640,
        "openHref": "preview/71-empty-state.html"
      },
      {
        "title": "Skeleton loading — list / card / detail placeholders",
        "file": "72-skeleton-loading.html",
        "height": 720,
        "openHref": "preview/72-skeleton-loading.html"
      },
      {
        "title": "Success · failure screen — fullbleed result state",
        "file": "84-success-failure-screen.html",
        "height": 940,
        "openHref": "preview/84-success-failure-screen.html"
      }
    ]
  }
] as const

export const APP_DS_SHOWCASE_VERSION = 'v2.1 · 26 mai 2026' as const
