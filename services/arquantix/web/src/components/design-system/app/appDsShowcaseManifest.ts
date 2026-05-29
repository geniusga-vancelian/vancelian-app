/** Généré depuis ui_kits/vancelian-app/index.html — ne pas éditer à la main. */
export type AppDsShowcaseItem = {
  title: string
  file: string
  height: number
  openHref?: string
  desc?: string
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
        "title": "Amounts — Inter SemiBold + tabular-nums · échelle .v-amount-*",
        "file": "06-type-amount.html",
        "height": 480
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
    "count": "48 assets",
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
        "title": "Card — product basket (panier crypto · coffre flex · avenir)",
        "file": "76-card-product-basket.html",
        "height": 920,
        "openHref": "preview/76-card-product-basket.html"
      },
      {
        "title": "News — stacked list (segmented filters + category chips)",
        "file": "79-news-stacked-list.html",
        "height": 1100,
        "openHref": "preview/79-news-stacked-list.html"
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
  },
  {
    "id": "app-primitives",
    "num": "09",
    "title": "App product — shared primitives",
    "count": "7 assets · Webapp3",
    "items": [
      {
        "title": "Icon — Kalai CSS mask (currentColor tint)",
        "file": "99-icon.html",
        "height": 200,
        "openHref": "preview/99-icon.html"
      },
      {
        "title": "Eyebrow — default · sm · tagged",
        "file": "100-eyebrow.html",
        "height": 220,
        "openHref": "preview/100-eyebrow.html"
      },
      {
        "title": "Account dot — typed avatar + Kalai glyph slot",
        "file": "101-account-dot.html",
        "height": 200,
        "openHref": "preview/101-account-dot.html"
      },
      {
        "title": "Asset chip — sélecteur actif (dot + label + chevron)",
        "file": "102-asset-chip.html",
        "height": 240,
        "openHref": "preview/102-asset-chip.html"
      },
      {
        "title": "Side panel — drawer droite + scrim",
        "file": "103-side-panel.html",
        "height": 380,
        "openHref": "preview/103-side-panel.html"
      },
      {
        "title": "Money phrase — signature éditoriale revenu",
        "file": "104-money-phrase.html",
        "height": 220,
        "openHref": "preview/104-money-phrase.html"
      },
      {
        "title": "Perf chart — multi-plage SVG inline",
        "file": "105-perf-chart.html",
        "height": 420,
        "openHref": "preview/105-perf-chart.html"
      }
    ]
  },
  {
    "id": "app-shell",
    "num": "10",
    "title": "App product — shell",
    "count": "6 assets · Webapp3",
    "items": [
      {
        "title": "Top nav produit — wallet · réseau · search · profil",
        "file": "106-app-topnav.html",
        "height": 120,
        "openHref": "preview/106-app-topnav.html"
      },
      {
        "title": "Mobile tab bar — 5 onglets · safe area",
        "file": "107-mobile-tab-bar.html",
        "height": 120,
        "openHref": "preview/107-mobile-tab-bar.html"
      },
      {
        "title": "Mobile chain bar — wallet + réseau (≤960px)",
        "file": "108-mobile-chain-bar.html",
        "height": 120,
        "openHref": "preview/108-mobile-chain-bar.html"
      },
      {
        "title": "Pill dropdown — déclencheur + panneau .dd",
        "file": "109-pill-dropdown.html",
        "height": 320,
        "openHref": "preview/109-pill-dropdown.html"
      },
      {
        "title": "Search overlay — plein écran · résultats groupés",
        "file": "110-search-overlay.html",
        "height": 420,
        "openHref": "preview/110-search-overlay.html"
      },
      {
        "title": "Footer slim — copyright + liens utiles",
        "file": "111-app-footer-slim.html",
        "height": 120,
        "openHref": "preview/111-app-footer-slim.html"
      }
    ]
  },
  {
    "id": "app-patterns",
    "num": "11",
    "title": "App product — page patterns",
    "count": "7 assets · Webapp3",
    "items": [
      {
        "title": "Section head — titre canonique + voir tout",
        "file": "112-section-head-product.html",
        "height": 220,
        "openHref": "preview/112-section-head-product.html"
      },
      {
        "title": "Balance card produit — solde héro Newsreader",
        "file": "113-balance-card-product.html",
        "height": 420,
        "openHref": "preview/113-balance-card-product.html"
      },
      {
        "title": "Accounts list — .v-card--list + .acc-row",
        "file": "114-accounts-list.html",
        "height": 360,
        "openHref": "preview/114-accounts-list.html"
      },
      {
        "title": "News section — grille actu cards",
        "file": "115-news-section-product.html",
        "height": 520,
        "openHref": "preview/115-news-section-product.html"
      },
      {
        "title": "Advisor card — portrait · banner · multi-channel",
        "file": "116-advisor-card-product.html",
        "height": 520,
        "openHref": "preview/116-advisor-card-product.html"
      },
      {
        "title": "Featured card — offre du mois full bleed",
        "file": "117-featured-card.html",
        "height": 400,
        "openHref": "preview/117-featured-card.html"
      },
      {
        "title": "Support card — sidebar compacte",
        "file": "118-support-card.html",
        "height": 280,
        "openHref": "preview/118-support-card.html"
      }
    ]
  },
  {
    "id": "w4-foundations",
    "num": "12",
    "title": "Webapp4 — Fondations",
    "count": "8 composants · Webapp4",
    "items": [
      {
        "title": "Couleurs",
        "file": "119-colors.html",
        "height": 520,
        "openHref": "preview/119-colors.html",
        "desc": "Triade terracotta · vert anglais · bleu de Prusse"
      },
      {
        "title": "Typographie",
        "file": "120-typography.html",
        "height": 480,
        "openHref": "preview/120-typography.html",
        "desc": "Inter + Newsreader · optical sizes"
      },
      {
        "title": "Espacement",
        "file": "121-spacing.html",
        "height": 360,
        "openHref": "preview/121-spacing.html",
        "desc": "Échelle 4·8·12·16·24·32·48·64"
      },
      {
        "title": "Rayons",
        "file": "122-radii.html",
        "height": 320,
        "openHref": "preview/122-radii.html",
        "desc": "4 · 6 · 8 · 12 · 24 · pill"
      },
      {
        "title": "Élévations",
        "file": "123-elevation.html",
        "height": 280,
        "openHref": "preview/123-elevation.html",
        "desc": "flat · subtle · medium"
      },
      {
        "title": "Motion",
        "file": "124-motion.html",
        "height": 280,
        "openHref": "preview/124-motion.html",
        "desc": "120 / 200 / 320 ms · ease-out"
      },
      {
        "title": "Iconographie",
        "file": "125-iconography.html",
        "height": 640,
        "openHref": "preview/125-iconography.html",
        "desc": "Kalai — 45 icônes webapp"
      },
      {
        "title": "Logo",
        "file": "126-logo.html",
        "height": 280,
        "openHref": "preview/126-logo.html",
        "desc": "Lockups noir / blanc"
      }
    ]
  },
  {
    "id": "w4-primitives",
    "num": "13",
    "title": "Webapp4 — Primitives",
    "count": "12 composants · Webapp4",
    "items": [
      {
        "title": "Button",
        "file": "127-button.html",
        "height": 420,
        "openHref": "preview/127-button.html",
        "desc": "7 variantes × 3 tailles"
      },
      {
        "title": "Icon Button",
        "file": "128-icon-button.html",
        "height": 240,
        "openHref": "preview/128-icon-button.html",
        "desc": "40 px circulaire · topnav"
      },
      {
        "title": "FAB",
        "file": "129-fab.html",
        "height": 280,
        "openHref": "preview/129-fab.html",
        "desc": "48/56 px · dark / terra / white"
      },
      {
        "title": "Avatar",
        "file": "130-avatar.html",
        "height": 480,
        "openHref": "preview/130-avatar.html",
        "desc": "Initiales · icône · photo"
      },
      {
        "title": "Avatar Exchange",
        "file": "131-avatar-exchange.html",
        "height": 320,
        "openHref": "preview/131-avatar-exchange.html",
        "desc": "Paire source + résultat"
      },
      {
        "title": "Icon",
        "file": "132-icon.html",
        "height": 360,
        "openHref": "preview/132-icon.html",
        "desc": "Mask CSS Kalai · currentColor"
      },
      {
        "title": "Eyebrow",
        "file": "133-eyebrow.html",
        "height": 220,
        "openHref": "preview/133-eyebrow.html",
        "desc": "UPPERCASE · sm · tagged"
      },
      {
        "title": "Tag",
        "file": "134-tag.html",
        "height": 320,
        "openHref": "preview/134-tag.html",
        "desc": "Status success / warning / info / error"
      },
      {
        "title": "Card",
        "file": "135-card.html",
        "height": 360,
        "openHref": "preview/135-card.html",
        "desc": ".v-card · warm · grey · list"
      },
      {
        "title": "Amount",
        "file": "136-amount.html",
        "height": 360,
        "openHref": "preview/136-amount.html",
        "desc": "hero / lg / md / sm · tnum"
      },
      {
        "title": "Network Dot",
        "file": "137-net-dot.html",
        "height": 200,
        "openHref": "preview/137-net-dot.html",
        "desc": "Base / Ethereum / Solana"
      },
      {
        "title": "Segmented",
        "file": "138-segmented.html",
        "height": 240,
        "openHref": "preview/138-segmented.html",
        "desc": "Plages 24h / 1S / 1M / 1A / Max"
      }
    ]
  },
  {
    "id": "w4-app-shell",
    "num": "14",
    "title": "Webapp4 — App shell",
    "count": "8 composants · Webapp4",
    "items": [
      {
        "title": "Top Nav",
        "file": "139-topnav.html",
        "height": 120,
        "openHref": "preview/139-topnav.html",
        "desc": "Logo · nav · wallet · réseau · search"
      },
      {
        "title": "Mobile Tab Bar",
        "file": "140-mobile-tab-bar.html",
        "height": 120,
        "openHref": "preview/140-mobile-tab-bar.html",
        "desc": "5 onglets · safe area"
      },
      {
        "title": "Mobile Chain Bar",
        "file": "141-mobile-chain-bar.html",
        "height": 120,
        "openHref": "preview/141-mobile-chain-bar.html",
        "desc": "Wallet + réseau ≤960px"
      },
      {
        "title": "Pill Dropdown",
        "file": "142-pill-dropdown.html",
        "height": 360,
        "openHref": "preview/142-pill-dropdown.html",
        "desc": "Déclencheur pill + panneau .dd"
      },
      {
        "title": "Dropdown Menu",
        "file": "143-dropdown-menu.html",
        "height": 360,
        "openHref": "preview/143-dropdown-menu.html",
        "desc": "Panneau .dd · sections · items"
      },
      {
        "title": "Search Overlay",
        "file": "144-search-overlay.html",
        "height": 480,
        "openHref": "preview/144-search-overlay.html",
        "desc": "Plein écran · résultats groupés"
      },
      {
        "title": "Footer Slim",
        "file": "145-footer-slim.html",
        "height": 120,
        "openHref": "preview/145-footer-slim.html",
        "desc": "Copyright + liens utiles"
      },
      {
        "title": "Side Panel",
        "file": "146-side-panel.html",
        "height": 400,
        "openHref": "preview/146-side-panel.html",
        "desc": "Drawer droit + scrim"
      }
    ]
  },
  {
    "id": "w4-patterns",
    "num": "15",
    "title": "Webapp4 — Patterns",
    "count": "13 composants · Webapp4",
    "items": [
      {
        "title": "Section Head",
        "file": "147-section-head.html",
        "height": 320,
        "openHref": "preview/147-section-head.html",
        "desc": "Titre + count + voir tout · lg/md/sm"
      },
      {
        "title": "Account Dot",
        "file": "148-account-dot.html",
        "height": 240,
        "openHref": "preview/148-account-dot.html",
        "desc": "Avatar typé compte"
      },
      {
        "title": "Asset Chip",
        "file": "149-asset-chip.html",
        "height": 280,
        "openHref": "preview/149-asset-chip.html",
        "desc": "Dot + label + chevron"
      },
      {
        "title": "Money Phrase",
        "file": "150-money-phrase.html",
        "height": 200,
        "openHref": "preview/150-money-phrase.html",
        "desc": "Phrase éditoriale + montant vert"
      },
      {
        "title": "Perf Chart",
        "file": "151-perf-chart.html",
        "height": 420,
        "openHref": "preview/151-perf-chart.html",
        "desc": "Graphique multi-plage SVG"
      },
      {
        "title": "Balance Card",
        "file": "152-balance-card.html",
        "height": 480,
        "openHref": "preview/152-balance-card.html",
        "desc": "Solde héro Newsreader · home produit"
      },
      {
        "title": "Accounts List",
        "file": "153-accounts-list.html",
        "height": 480,
        "openHref": "preview/153-accounts-list.html",
        "desc": ".v-card--list + .acc-row"
      },
      {
        "title": "News Section",
        "file": "154-news-section.html",
        "height": 520,
        "openHref": "preview/154-news-section.html",
        "desc": "Grille actu cards"
      },
      {
        "title": "Featured Card",
        "file": "155-featured-card.html",
        "height": 400,
        "openHref": "preview/155-featured-card.html",
        "desc": "Offre du mois full bleed"
      },
      {
        "title": "Advisor — Portrait",
        "file": "156-advisor-portrait.html",
        "height": 360,
        "openHref": "preview/156-advisor-portrait.html",
        "desc": "Photo + nom + CTA"
      },
      {
        "title": "Advisor — Banner",
        "file": "157-advisor-banner.html",
        "height": 360,
        "openHref": "preview/157-advisor-banner.html",
        "desc": "Bannière photo + headline"
      },
      {
        "title": "Advisor — Multi-channel",
        "file": "158-advisor-multichannel.html",
        "height": 400,
        "openHref": "preview/158-advisor-multichannel.html",
        "desc": "Téléphone · mail · chat"
      },
      {
        "title": "Support Card",
        "file": "159-support-card.html",
        "height": 280,
        "openHref": "preview/159-support-card.html",
        "desc": "Sidebar compacte"
      }
    ]
  },
  {
    "id": "w-full",
    "num": "16",
    "title": "Webapp-full — Patterns produit",
    "count": "6 composants · Webapp-full (mai 2026)",
    "items": [
      {
        "title": "Account dot — variante safran",
        "file": "160-avatar-safran.html",
        "height": 200,
        "openHref": "preview/160-avatar-safran.html",
        "desc": "Cryptos · Managed Portfolio = blue · safran"
      },
      {
        "title": "Borrow CTA — avance de liquidité",
        "file": "161-borrow-cta.html",
        "height": 320,
        "openHref": "preview/161-borrow-cta.html",
        "desc": "Carte CTA page Emprunts · powered by Morpho"
      },
      {
        "title": "Loan card — emprunt actif",
        "file": "162-loan-card.html",
        "height": 480,
        "openHref": "preview/162-loan-card.html",
        "desc": "Carte cliquable · stats · barre d’utilisation"
      },
      {
        "title": "Mobile sticky bar — .mstick",
        "file": "163-mobile-sticky-bar.html",
        "height": 120,
        "openHref": "preview/163-mobile-sticky-bar.html",
        "desc": "CTA fixe au-dessus du tab bar · gain % + bouton"
      },
      {
        "title": "Borrow explainer — 3 points",
        "file": "164-borrow-explainer.html",
        "height": 420,
        "openHref": "preview/164-borrow-explainer.html",
        "desc": "Garantie · intérêt · remboursement libre"
      },
      {
        "title": "Actu card — zoom photo au survol",
        "file": "165-actu-photo-zoom.html",
        "height": 360,
        "openHref": "preview/165-actu-photo-zoom.html",
        "desc": "Image scale 1.05 · chip texte fixe"
      }
    ]
  }
] as const

export const APP_DS_SHOWCASE_VERSION = 'v2.5 · 29 mai 2026 · 114 + 41 Webapp4 + 6 Webapp-full' as const
