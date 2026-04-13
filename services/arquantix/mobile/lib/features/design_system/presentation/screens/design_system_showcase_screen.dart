import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../../security/passcode/presentation/screens/passcode_setup_screen.dart';

/// Visibilité du design system : atomes, composants et boutons à la suite.
class DesignSystemShowcaseScreen extends StatelessWidget {
  const DesignSystemShowcaseScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            0,
            AppSpacing.xl,
            0,
            AppSpacing.s24,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const AppPageTitle('Design system'),
              const SizedBox(height: AppSpacing.xxl),
              _Section('Sécurité — Code PIN & biométrie', const _SecurityPinSection()),

              // ══════════════════════════════════════════════
              // ░░░  ATOMES  ░░░
              // ══════════════════════════════════════════════
              _Section('Typography — Page', _buildTypoPageSection()),
              _Section('Typography — Amount', _buildTypoAmountSection()),
              _Section('Typography — Section & Item', _buildTypoSectionItemSection()),
              _Section('Typography — Body', _buildTypoBodySection()),
              _Section('Typography — Body SM', _buildTypoBodySmSection()),
              _Section('Typography — Label', _buildTypoLabelSection()),
              _Section('Couleurs — Base', _buildColorsBaseSection()),
              _Section('Couleurs — Gray scale', _buildColorsGraySection()),
              _Section('Couleurs — Dark theme', _buildColorsDarkThemeSection()),
              _Section('Couleurs — Semantic aliases', _buildColorsSemanticSection()),
              _Section('Couleurs — Semantic Figma', _buildColorsSemanticFigmaSection()),
              _Section('Spacing', _buildSpacingSection()),
              _Section('Radius', _buildRadiusSection()),
              _Section('Shadow', _buildShadowSection()),
              _Section('Motion', _buildMotionSection()),

              // ══════════════════════════════════════════════
              // ░░░  BOUTONS  ░░░
              // ══════════════════════════════════════════════
              _Section('Boutons — AppPrimaryButton', _buildPrimaryButtonSection()),
              _Section('Boutons — AppSmallButton', _buildSmallButtonSection()),
              _Section('Boutons — AppBackButton', _buildBackButtonSection()),
              _Section('Boutons — CircleButton', _buildCircleButtonSection()),

              // ══════════════════════════════════════════════
              // ░░░  NOTIFICATIONS  ░░░
              // ══════════════════════════════════════════════
              _Section('Notifications — Snackbar', _buildSnackbarSection()),
              _Section('Notifications — Toast', _buildToastSection()),

              // ══════════════════════════════════════════════
              // ░░░  CRYPTO  ░░░
              // ══════════════════════════════════════════════
              _Section('Crypto — CryptoAvatar', _buildCryptoAvatarSection()),
              _Section('Crypto — CryptoExchangeWidget', _buildCryptoExchangeSection()),
              _Section('Crypto — AmountDisplay', _buildAmountDisplaySection()),

              // ══════════════════════════════════════════════
              // ░░░  COMPOSANTS  ░░░
              // ══════════════════════════════════════════════
              _Section('Composants — Titres', _buildTitlesSection()),
              _Section('Composants — MetadataItem', _buildMetadataItemSection()),
              _Section('Composants — Chips', _buildChipsSection()),
              _Section('Composants — GlassBadge', _buildGlassBadgeSection()),
              _Section('Composants — AppTabBar', _TabBarDemo()),
              _Section('Composants — Settings / ListItem', _SettingsShowcaseDemo()),
              _Section(
                'Composants — FormRadioRow (liste single)',
                _buildFormRadioRowDsSection(),
              ),
              _Section(
                'Composants — FormCheckboxRow (liste multi)',
                _buildFormCheckboxRowDsSection(),
              ),

              // ── Cards / Blog (Figma NewsCard, Tag, ReadingTime) ──
              _Section(
                'Composants — DsNewsTag & DsNewsReadingTime',
                _buildNewsTagReadingTimeSection(),
              ),
              _Section('Composants — NewsCard', _buildNewsCardSection()),
              _Section('Composants — BasketCard', _buildBasketCardSection()),
              _Section('Composants — ListCard', _buildListCardSection()),
              _Section('Composants — TransactionListCard', _buildTransactionListCardSection()),
              _Section('Composants — PropertyCard', _buildPropertyCardSection()),
              _Section('Composants — InvestmentCard', _buildInvestmentCardSection()),

              // ── Marketing ──
              _Section('Composants — Marketing Card', _buildMarketingCardsSection()),
              _Section('Composants — Marketing Card Portrait', _buildMarketingCardPortraitSection()),
              _Section('Composants — Marketing Cards (carousel)', _buildMarketingCardsCarouselSection()),
              _Section('Composants — Marketing Cards (sliding)', _buildMarketingCardsSlidingSection()),

              // ── Blog / News ──
              _Section('Composants — Blog A la une', _buildBlogALaUneSection()),
              _Section('Composants — Vidéos (VideoBlockArticleModule)', _buildVideoBlockArticleSection()),
              _Section('Composants — Blog News', _buildBlogNewsSection()),
              _Section('Composants — News Module', _buildNewsCardModuleSection()),

              // ── Bottom Sheet ──
              _Section('Composants — Bottom Sheet', _buildBottomSheetSection()),

              // ── Module validation Figma (ZIP Design Systeme) ──
              _Section(
                'Composants — Module validation (Figma)',
                _buildValidationModuleSection(),
              ),
              _Section(
                'Composants — Permission / Access (Figma ZIP 4)',
                _buildPermissionAccessSection(),
              ),
              _Section(
                'Composants — Address selector (Figma ZIP 5)',
                _buildAddressSelectorZip5Section(),
              ),

              // ── Charts / Stats ──
              _Section('Composants — Module Gain', _buildModuleGainSection()),

              // ── Article ──
              _Section('Composants — Article Components', _buildArticleComponentsSection()),

              // ── Offers ──
              _Section('Composants — Exclusive Offer', _buildExclusiveOfferSection()),
              _Section('Composants — Featured Offer Card', _buildFeaturedOfferCardSection(context)),

              // ── Categories ──
              _Section('Composants — Categories tab', _buildCategoriesTabSection()),

              // ── Transaction Steps ──
              _Section('Composants — Transaction Steps', _buildTransactionStepsSection()),

              // ══════════════════════════════════════════════
              // ░░░  FORM INPUTS  ░░░
              // ══════════════════════════════════════════════
              _Section('Forms — SearchInput', _SearchInputDemo()),
              _Section('Forms — TextInput', _TextInputDemo()),
              _Section('Forms — PasswordStrength', _buildPasswordStrengthSection()),
              _Section('Forms — RadioButton', _RadioButtonDemo()),
              _Section('Forms — Checkbox', _CheckboxDemo()),
              _Section('Forms — Tag', _buildTagSection()),
              _Section('Forms — Textarea', _TextareaDemo()),
              _Section('Forms — OTP Input', _OtpInputDemo()),
              _Section('Forms — Slider', _SliderDemo()),
              _Section('Forms — PhoneInput', _PhoneInputDemo()),
              _Section('Forms — DateInput', _DateInputDemo()),

              // ══════════════════════════════════════════════
              // ░░░  FEEDBACK  ░░░
              // ══════════════════════════════════════════════
              _Section('Lists — SheetListItem', _buildSheetListItemSection()),
              _Section('Feedback — Alert', _buildAlertSection()),
              _Section('Feedback — DsSuccessIcon', _buildDsSuccessIconSection()),
              _Section('Feedback — ProgressBar', _ProgressBarDemo()),
              _Section('Feedback — Skeleton', _buildSkeletonSection()),

              const SizedBox(height: AppSpacing.xxl * 2),
            ],
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  TYPOGRAPHY  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildTypoPageSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Header Primary', style: AppTypography.headerPrimary),
        const SizedBox(height: AppSpacing.sm),
        Text('Header Appbar', style: AppTypography.headerAppbar),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'page/headerTertiary',
          style: AppTypography.itemSupporting.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          'Bitcoin',
          style: AppTypography.headerTertiary.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text('Display', style: AppTypography.display),
        const SizedBox(height: AppSpacing.sm),
        Text('NavBar Label', style: AppTypography.navBarLabel),
      ],
    );
  }

  Widget _buildTypoAmountSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'amount/primary',
          style: AppTypography.itemSupporting.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          '12,345.67',
          style: AppTypography.amountPrimary.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text('Amount Secondary', style: AppTypography.amountSecondary),
        const SizedBox(height: AppSpacing.xs),
        Text('Amount Tertiary', style: AppTypography.amountTertiary),
      ],
    );
  }

  Widget _buildTypoSectionItemSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Article title (22px Bold)', style: AppTypography.articleTitle),
        const SizedBox(height: AppSpacing.sm),
        Text('Section title (20px Bold)', style: AppTypography.sectionTitle),
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Item Primary', style: AppTypography.itemPrimary),
                  Text(
                    'Item Supporting (14px Regular, lh 18, -0.08)',
                    style: AppTypography.itemSupporting,
                  ),
                ],
              ),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Item Secondary', style: AppTypography.itemSecondary),
                  Text(
                    'Item Supporting Bd (14px Semibold, lh 18, -0.08)',
                    style: AppTypography.itemSupportingBd,
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildTypoBodySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Body Regular', style: AppTypography.bodyRegular),
        Text('Body Emphasized', style: AppTypography.bodyEmphasized),
        Text('Body Italic', style: AppTypography.bodyItalic),
        Text('Body Emphasized Italic', style: AppTypography.bodyEmphasizedItalic),
      ],
    );
  }

  Widget _buildTypoBodySmSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('BodySM Regular', style: AppTypography.bodySmRegular),
        Text('BodySM Emphasized', style: AppTypography.bodySmEmphasized),
        Text('BodySM Italic', style: AppTypography.bodySmItalic),
        Text('BodySM Emphasized Italic', style: AppTypography.bodySmEmphasizedItalic),
      ],
    );
  }

  Widget _buildTypoLabelSection() {
    return Wrap(
      spacing: AppSpacing.md,
      runSpacing: AppSpacing.xs,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Label Regular', style: AppTypography.labelRegular),
            Text('Label Emphasized', style: AppTypography.labelEmphasized),
            Text('Label tag (puces catégorie)', style: AppTypography.labelTagEmphasized),
            Text('item/supportingBD', style: AppTypography.supportingBd),
            Text(
              'item/supportingBD (puces perf., pnum)',
              style: AppTypography.supportingBdPerformanceChip.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
            Text('Label Italic', style: AppTypography.labelItalic),
            Text('Label Emph. Italic', style: AppTypography.labelEmphasizedItalic),
          ],
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  COLORS  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildColorsBaseSection() {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: const [
        _ColorSwatch('red', AppColors.red),
        _ColorSwatch('mint', AppColors.mint),
        _ColorSwatch('orange', AppColors.orange),
        _ColorSwatch('yellow', AppColors.yellow),
        _ColorSwatch('green', AppColors.green),
        _ColorSwatch('teal', AppColors.teal),
        _ColorSwatch('cyan', AppColors.cyan),
        _ColorSwatch('blue', AppColors.blue),
        _ColorSwatch('indigo', AppColors.indigo),
        _ColorSwatch('purple', AppColors.purple),
        _ColorSwatch('pink', AppColors.pink),
        _ColorSwatch('brown', AppColors.brown),
      ],
    );
  }

  Widget _buildColorsGraySection() {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: const [
        _ColorSwatch('black', AppColors.black),
        _ColorSwatch('gray6', AppColors.gray6),
        _ColorSwatch('gray5', AppColors.gray5),
        _ColorSwatch('gray4', AppColors.gray4),
        _ColorSwatch('gray3', AppColors.gray3),
        _ColorSwatch('gray2', AppColors.gray2),
        _ColorSwatch('gray', AppColors.gray),
        _ColorSwatch('white', AppColors.white),
      ],
    );
  }

  Widget _buildColorsDarkThemeSection() {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: const [
        _ColorSwatch('bgPrimary', AppColors.darkBgPrimary),
        _ColorSwatch('bgSecondary', AppColors.darkBgSecondary),
        _ColorSwatch('txtPrimary', AppColors.darkTextPrimary),
        _ColorSwatch('txtMuted', AppColors.darkTextMuted),
        _ColorSwatch('sepOpaque', AppColors.darkSeparatorOpaque),
        _ColorSwatch('opacity60', AppColors.darkOpacity60),
        _ColorSwatch('opacity30', AppColors.darkOpacity30),
        _ColorSwatch('opacity18', AppColors.darkOpacity18),
      ],
    );
  }

  Widget _buildColorsSemanticSection() {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: const [
        _ColorSwatch('textPrim', AppColors.textPrimary),
        _ColorSwatch('accent', AppColors.accent),
        _ColorSwatch('textSec', AppColors.textSecondary),
        _ColorSwatch('textMuted', AppColors.textMuted),
        _ColorSwatch('pageBg', AppColors.pageBackground),
        _ColorSwatch('cardBg', AppColors.cardBackground),
        _ColorSwatch('border', AppColors.border),
        _ColorSwatch('error', AppColors.errorText),
      ],
    );
  }

  Widget _buildColorsSemanticFigmaSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: const [
            _ColorSwatchPair('Neutral', AppColors.semanticNeutral, null),
            _ColorSwatchPair('Active', AppColors.semanticActive, AppColors.semanticActiveLight),
            _ColorSwatchPair('Info', AppColors.semanticInfo, AppColors.semanticInfoLight),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: const [
            _ColorSwatchPair('Warning', AppColors.semanticWarning, AppColors.semanticWarningLight),
            _ColorSwatchPair('Danger', AppColors.semanticDanger, AppColors.semanticDangerLight),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: const [
            _ColorSwatchPair('Positive', AppColors.semanticPositive, AppColors.semanticPositiveLight),
            _ColorSwatchPair('Negative', AppColors.semanticNegative, AppColors.semanticNegativeLight),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: const [
            _ColorSwatch('disabledBg', AppColors.buttonDisabledBg),
            _ColorSwatch('disabledFg', AppColors.buttonDisabledFg),
            _ColorSwatchPair('Accent', AppColors.accent, AppColors.accentLight),
          ],
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  SPACING  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildSpacingSection() {
    const entries = <MapEntry<String, double>>[
      MapEntry('s0', AppSpacing.s0),
      MapEntry('s1', AppSpacing.s1),
      MapEntry('s2', AppSpacing.s2),
      MapEntry('s3', AppSpacing.s3),
      MapEntry('s4', AppSpacing.s4),
      MapEntry('s5', AppSpacing.s5),
      MapEntry('s6', AppSpacing.s6),
      MapEntry('s7', AppSpacing.s7),
      MapEntry('s8', AppSpacing.s8),
      MapEntry('s10', AppSpacing.s10),
      MapEntry('s12', AppSpacing.s12),
      MapEntry('s16', AppSpacing.s16),
      MapEntry('s20', AppSpacing.s20),
      MapEntry('s24', AppSpacing.s24),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final e in entries)
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(
              children: [
                SizedBox(
                  width: 44,
                  child: Text(e.key, style: AppTypography.itemSupporting),
                ),
                Container(
                  height: 12,
                  width: e.value.clamp(2, 200),
                  decoration: BoxDecoration(
                    color: AppColors.indigo.withValues(alpha: 0.6),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 8),
                Text('${e.value.toInt()}px', style: AppTypography.itemSupporting),
              ],
            ),
          ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  RADIUS  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildRadiusSection() {
    const entries = <MapEntry<String, double>>[
      MapEntry('none', AppRadius.none),
      MapEntry('xs', AppRadius.xs),
      MapEntry('sm', AppRadius.sm),
      MapEntry('md', AppRadius.md),
      MapEntry('lg', AppRadius.lg),
      MapEntry('xl', AppRadius.xl),
      MapEntry('2xl', AppRadius.xxl),
    ];
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: [
        for (final e in entries)
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: AppColors.indigo.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(e.value),
                  border: Border.all(color: AppColors.indigo.withValues(alpha: 0.4)),
                ),
              ),
              const SizedBox(height: 4),
              Text(e.key, style: AppTypography.itemSupporting),
              Text('${e.value.toInt()}', style: AppTypography.labelRegular),
            ],
          ),
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: AppColors.indigo.withValues(alpha: 0.15),
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.indigo.withValues(alpha: 0.4)),
              ),
            ),
            const SizedBox(height: 4),
            Text('full', style: AppTypography.itemSupporting),
          ],
        ),
      ],
    );
  }

  Widget _buildShadowSection() {
    return Center(
      child: Container(
        width: 160,
        height: 80,
        decoration: BoxDecoration(
          color: AppColors.cardBackground,
          borderRadius: BorderRadius.circular(AppRadius.md),
          boxShadow: AppShadow.defaultShadowList,
        ),
        alignment: Alignment.center,
        child: Text('default', style: AppTypography.itemPrimary),
      ),
    );
  }

  Widget _buildMotionSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _TokenChip('fast: ${AppMotion.fast.inMilliseconds}ms'),
        const SizedBox(height: AppSpacing.xs),
        _TokenChip('base: ${AppMotion.base.inMilliseconds}ms'),
        const SizedBox(height: AppSpacing.xs),
        _TokenChip('slow: ${AppMotion.slow.inMilliseconds}ms'),
        const SizedBox(height: AppSpacing.sm),
        Text('easing: standard (ease-in-out)', style: AppTypography.itemSupporting),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  BUTTONS  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildPrimaryButtonSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Medium (48px) — Figma Access : primary #6155F5, secondary blanc + texte noir',
          style: AppTypography.itemSupporting,
        ),
        const SizedBox(height: AppSpacing.sm),
        AppPrimaryButton(label: 'Primary', onPressed: () {}),
        const SizedBox(height: AppSpacing.sm),
        AppPrimaryButton(
          label: 'Not Now (secondary)',
          variant: AppPrimaryButtonVariant.secondary,
          onPressed: () {},
        ),
        const SizedBox(height: AppSpacing.sm),
        AppPrimaryButton(label: 'Black', variant: AppPrimaryButtonVariant.black, onPressed: () {}),
        const SizedBox(height: AppSpacing.sm),
        AppPrimaryButton(label: 'Gray', variant: AppPrimaryButtonVariant.gray, onPressed: () {}),
        const SizedBox(height: AppSpacing.sm),
        AppPrimaryButton(label: 'Ghost', variant: AppPrimaryButtonVariant.ghost, onPressed: () {}),
        const SizedBox(height: AppSpacing.sm),
        const AppPrimaryButton(label: 'Disabled', variant: AppPrimaryButtonVariant.disabled),
        const SizedBox(height: AppSpacing.xl),
        Text('Small — Figma sm (36px)', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppPrimaryButton(label: 'Primary Small', size: AppPrimaryButtonSize.small, onPressed: () {}),
        const SizedBox(height: AppSpacing.sm),
        AppPrimaryButton(
          label: 'Black Small',
          size: AppPrimaryButtonSize.small,
          variant: AppPrimaryButtonVariant.black,
          onPressed: () {},
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('Large — Figma lg (56px)', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppPrimaryButton(label: 'Primary Large', size: AppPrimaryButtonSize.large, onPressed: () {}),
        const SizedBox(height: AppSpacing.xl),
        Text('Shrink wrap', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: [
            AppPrimaryButton(label: 'Primary', shrinkWrap: true, onPressed: () {}),
            AppPrimaryButton(
              label: 'Secondary',
              shrinkWrap: true,
              variant: AppPrimaryButtonVariant.secondary,
              onPressed: () {},
            ),
            AppPrimaryButton(label: 'Black', shrinkWrap: true, variant: AppPrimaryButtonVariant.black, onPressed: () {}),
            AppPrimaryButton(label: 'Ghost', shrinkWrap: true, variant: AppPrimaryButtonVariant.ghost, onPressed: () {}),
          ],
        ),
      ],
    );
  }

  Widget _buildSmallButtonSection() {
    return Wrap(
      spacing: AppSpacing.md,
      runSpacing: AppSpacing.md,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        AppSmallButton(label: 'Primary', onPressed: () {}),
        AppSmallButton(label: 'Black', variant: AppSmallButtonVariant.black, onPressed: () {}),
        AppSmallButton(label: 'Gray', variant: AppSmallButtonVariant.gray, onPressed: () {}),
        AppSmallButton(label: 'Warning', variant: AppSmallButtonVariant.warning, onPressed: () {}),
        const AppSmallButton(label: 'Disabled', variant: AppSmallButtonVariant.disabled),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  SNACKBAR SECTION  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildSnackbarSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Light', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppSnackbar(
          text: 'Action effectuée avec succès',
          action: AppSnackbarAction.chevron,
          onActionTap: () {},
        ),
        const SizedBox(height: AppSpacing.md),
        AppSnackbar(
          text: 'Notification avec fermeture',
          action: AppSnackbarAction.close,
          onActionTap: () {},
        ),
        const SizedBox(height: AppSpacing.md),
        AppSnackbar(
          text: 'Avec bouton CTA',
          actionButton: AppSmallButton(label: 'CTA', onPressed: () {}),
        ),
        const SizedBox(height: AppSpacing.md),
        AppSnackbar(
          text: 'Avec icône et CTA',
          icon: const Icon(Icons.info_outline_rounded, size: 24, color: Color(0xFF6155F5)),
          actionButton: AppSmallButton(label: 'CTA', onPressed: () {}),
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('Dark', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppSnackbar(
          text: 'Action effectuée avec succès',
          variant: AppSnackbarVariant.dark,
          action: AppSnackbarAction.chevron,
          onActionTap: () {},
        ),
        const SizedBox(height: AppSpacing.md),
        AppSnackbar(
          text: 'Avec bouton CTA',
          variant: AppSnackbarVariant.dark,
          actionButton: AppSmallButton(label: 'CTA', onPressed: () {}),
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('Warning', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppSnackbar(
          text: 'Attention requise',
          variant: AppSnackbarVariant.warning,
          action: AppSnackbarAction.chevron,
          onActionTap: () {},
        ),
        const SizedBox(height: AppSpacing.md),
        AppSnackbar(
          text: 'Avec bouton CTA',
          variant: AppSnackbarVariant.warning,
          actionButton: AppSmallButton(label: 'CTA', variant: AppSmallButtonVariant.warning, onPressed: () {}),
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  TOAST SECTION  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildToastSection() {
    const infoIcon = Icon(Icons.info_outline_rounded, size: 24, color: Color(0xFF6155F5));
    const warningInfoIcon = Icon(Icons.info_outline_rounded, size: 24, color: Color(0xFFFFF4E9));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Light — Horizontal', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppToast(
          title: 'Opération réussie',
          subtitle: 'Votre transaction a été confirmée.',
          icon: infoIcon,
          actionButton: AppSmallButton(label: 'CTA', onPressed: () {}),
        ),
        const SizedBox(height: AppSpacing.md),
        Text('Light — Vertical', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppToast(
          title: 'Opération réussie',
          subtitle: 'Votre transaction a été confirmée.',
          layout: AppToastLayout.vertical,
          icon: infoIcon,
          actionButton: AppSmallButton(label: 'Long Call to Action', onPressed: () {}),
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('Dark — Horizontal', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppToast(
          title: 'Mise à jour disponible',
          subtitle: 'Une nouvelle version est prête.',
          variant: AppToastVariant.dark,
          icon: infoIcon,
          actionButton: AppSmallButton(label: 'CTA', onPressed: () {}),
        ),
        const SizedBox(height: AppSpacing.md),
        Text('Dark — Vertical', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppToast(
          title: 'Mise à jour disponible',
          subtitle: 'Une nouvelle version est prête.',
          variant: AppToastVariant.dark,
          layout: AppToastLayout.vertical,
          icon: infoIcon,
          actionButton: AppSmallButton(label: 'Long Call to Action', onPressed: () {}),
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('Warning — Horizontal', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppToast(
          title: 'Attention requise',
          subtitle: 'Vérifiez vos paramètres de sécurité.',
          variant: AppToastVariant.warning,
          icon: warningInfoIcon,
          actionButton: AppSmallButton(label: 'CTA', variant: AppSmallButtonVariant.warning, onPressed: () {}),
        ),
        const SizedBox(height: AppSpacing.md),
        Text('Warning — Vertical', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppToast(
          title: 'Attention requise',
          subtitle: 'Vérifiez vos paramètres de sécurité.',
          variant: AppToastVariant.warning,
          layout: AppToastLayout.vertical,
          icon: warningInfoIcon,
          actionButton: AppSmallButton(label: 'Long Call to Action', variant: AppSmallButtonVariant.warning, onPressed: () {}),
        ),
      ],
    );
  }

  Widget _buildBackButtonSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('White (shadow)', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            AppBackButton(onPressed: () {}),
            const SizedBox(width: AppSpacing.s4),
            AppBackButton(icon: Icons.more_horiz_rounded, onPressed: () {}),
            const SizedBox(width: AppSpacing.s4),
            AppBackButton(icon: Icons.close_rounded, size: 32, onPressed: () {}),
          ],
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('Glass + Glass Dark', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        Container(
          padding: const EdgeInsets.all(AppSpacing.s6),
          decoration: BoxDecoration(
            color: AppColors.gray6,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              AppBackButton(
                icon: Icons.arrow_back_ios_new_rounded,
                variant: AppBackButtonVariant.glass,
                onPressed: () {},
              ),
              const SizedBox(width: AppSpacing.s4),
              AppBackButton(
                icon: Icons.more_horiz_rounded,
                variant: AppBackButtonVariant.glassDark,
                onPressed: () {},
              ),
              const SizedBox(width: AppSpacing.s4),
              AppBackButton(
                icon: Icons.close_rounded,
                size: 32,
                variant: AppBackButtonVariant.glassDark,
                onPressed: () {},
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildCircleButtonSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Glass (fond sombre)', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        Container(
          decoration: BoxDecoration(
            color: AppColors.gray6,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.s6),
          child: CircleButtonRow(
            items: [
              CircleButtonItem(icon: Icons.trending_up_rounded, label: 'Investir', isPrimary: true),
              const CircleButtonItem(icon: Icons.description_outlined, label: 'Brochure'),
              const CircleButtonItem(icon: Icons.photo_library_outlined, label: 'Photos'),
              const CircleButtonItem(icon: Icons.videocam_outlined, label: 'Vidéos'),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('White + Info (fond clair)', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            CircleButton(
              icon: const Icon(Icons.add_rounded, size: 24, color: AppColors.black),
              label: 'White',
              variant: CircleButtonVariant.white,
            ),
            CircleButton(
              icon: const Icon(Icons.add_rounded, size: 24, color: AppColors.white),
              label: 'Info',
              variant: CircleButtonVariant.info,
            ),
            CircleButton(
              icon: const Icon(Icons.add_rounded, size: 18, color: AppColors.black),
              label: 'Small',
              variant: CircleButtonVariant.white,
              buttonSize: CircleButtonSize.small,
            ),
            CircleButton(
              icon: const Icon(Icons.add_rounded, size: 18, color: AppColors.white),
              label: 'Small Info',
              variant: CircleButtonVariant.info,
              buttonSize: CircleButtonSize.small,
            ),
          ],
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  COMPONENTS  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildTitlesSection() {
    return const Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppPageTitle('Page title'),
        SizedBox(height: AppSpacing.md),
        AppSectionTitle('Section title'),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  CRYPTO  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildCryptoAvatarSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Sizes & Shapes', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            const CryptoAvatar(
              ticker: 'ETH',
              size: CryptoAvatarSize.small,
            ),
            const SizedBox(width: AppSpacing.md),
            const CryptoAvatar(
              ticker: 'BTC',
              size: CryptoAvatarSize.medium,
            ),
            const SizedBox(width: AppSpacing.md),
            const CryptoAvatar(
              ticker: 'SOL',
              size: CryptoAvatarSize.large,
            ),
            const SizedBox(width: AppSpacing.md),
            const CryptoAvatar(
              ticker: 'XRP',
              size: CryptoAvatarSize.large,
              shape: CryptoAvatarShape.rounded,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Défaut : cercles (small 24 · medium 36 · large 40) — dernier : variante carré arrondi',
          style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
        ),
      ],
    );
  }

  Widget _buildCryptoExchangeSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Center(
          child: CryptoExchangeWidget(
            fromTicker: 'ETH',
            toTicker: 'BTC',
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Text('Capsule 123×48 — 2 avatars + icône échange',
            style: AppTypography.meta.copyWith(color: AppColors.textSecondary)),
      ],
    );
  }

  Widget _buildAmountDisplaySection() {
    return const Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AmountDisplay(
          amount: '00.00000 BTC',
          subtitle: 'Achat de 0,0016 BTC au prix de 10 ETH',
          subtext: '(= 100 EUR)',
        ),
        SizedBox(height: AppSpacing.xxl),
        AmountDisplay(
          amount: '1 250,00 €',
          subtitle: 'Solde disponible',
        ),
      ],
    );
  }

  Widget _buildMetadataItemSection() {
    return const Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppMetadataItem(
          icon: Icons.calendar_today_rounded,
          text: "Date d'analyse : 11 février 2026",
        ),
        SizedBox(height: AppSpacing.md),
        AppMetadataItem(
          icon: Icons.access_time_rounded,
          text: 'Unité de temps : Daily (journalier)',
        ),
        SizedBox(height: AppSpacing.md),
        AppMetadataItem(
          icon: Icons.category_rounded,
          text: 'Catégorie : Crypto',
          iconColor: AppColors.semanticWarning,
        ),
      ],
    );
  }

  Widget _buildChipsSection() {
    return Row(
      children: [
        AppFilterChip(label: 'Tous', selected: true, onTap: () {}),
        AppFilterChip(label: 'Catégorie', selected: false, onTap: () {}),
      ],
    );
  }

  Widget _buildGlassBadgeSection() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s6),
      decoration: BoxDecoration(
        color: AppColors.gray6,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Wrap(
        spacing: AppSpacing.s2,
        runSpacing: AppSpacing.s2,
        children: [
          GlassBadge(text: 'Immobilier', opacity: GlassBadgeOpacity.medium),
          GlassBadge(text: 'Rate 11.24%', opacity: GlassBadgeOpacity.medium),
          GlassBadge(text: 'Light (0.3)', opacity: GlassBadgeOpacity.light),
        ],
      ),
    );
  }

  Widget _buildFormRadioRowDsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Interactif — tap une ligne (sélection unique, état actif)',
          style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.sm),
        const _DsFormRadioRowInteractiveDemo(),
      ],
    );
  }

  Widget _buildFormCheckboxRowDsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Interactif — tap pour cocher / décocher (plusieurs lignes)',
          style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.sm),
        const _DsFormCheckboxRowInteractiveDemo(),
      ],
    );
  }

  Widget _buildNewsTagReadingTimeSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Tags (Figma) — point rouge par défaut, couleur optionnelle',
          style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.sm),
        const Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            DsNewsTag(label: 'Category'),
            DsNewsTag(label: 'Category'),
            DsNewsTag(label: 'Category'),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Temps de lecture — horloge indigo + 13px gris',
          style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.sm),
        const DsNewsReadingTime(label: '5 minutes'),
      ],
    );
  }

  Widget _buildNewsCardSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        NewsCard(
          imageUrl: 'https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800',
          title: 'Huit pays européens intéressés par la «dissuasion avancée» française',
          readTimeMinutes: 3,
          tags: const [
            NewsCardTag('Category'),
            NewsCardTag('Category'),
            NewsCardTag('Category'),
          ],
          onTap: () {},
        ),
        const SizedBox(height: AppSpacing.lg),
        NewsCard(
          imageUrl: 'https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=800',
          title: 'Bitcoin dépasse les 100 000 \$ pour la première fois',
          readTimeMinutes: 5,
          badgeLabel: 'Crypto',
          onTap: () {},
        ),
        const SizedBox(height: AppSpacing.lg),
        NewsRowCard(
          title: 'Exemple carte news en ligne',
          coverUrl: '',
          readingTime: 3,
          onTap: () {},
        ),
      ],
    );
  }

  Widget _buildBasketCardSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        BasketCard(
          name: 'Panier Diversifié',
          percentage: '+15.42%',
          percentagePositive: true,
          avatars: const [
            CryptoAvatarData(ticker: 'BTC'),
            CryptoAvatarData(ticker: 'ETH'),
            CryptoAvatarData(ticker: 'SOL'),
            CryptoAvatarData(ticker: 'XRP'),
          ],
          remainingAvatarCount: 3,
          onInvest: () {},
        ),
        const SizedBox(height: AppSpacing.lg),
        BasketCard(
          name: 'Stablecoins',
          percentage: '-2.18%',
          percentagePositive: false,
          avatars: const [
            CryptoAvatarData(ticker: 'BTC'),
            CryptoAvatarData(ticker: 'ETH'),
          ],
          remainingAvatarCount: 0,
          onInvest: () {},
        ),
      ],
    );
  }

  Widget _buildListCardSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ListCard(
          icon: const IconContainer(
            child: Icon(Icons.currency_bitcoin, size: 17, color: Color(0xFF8E8E93)),
          ),
          title: 'Panier Crypto',
          description: 'Cum saepe multa, tum memini domi in hemicyclio sedentem',
          onTap: () {},
        ),
        const SizedBox(height: AppSpacing.md),
        ListCard(
          icon: IconContainer(
            backgroundColor: const Color(0xFFE5F5FF),
            child: Container(width: 16, height: 16, decoration: const BoxDecoration(color: AppColors.blue, shape: BoxShape.circle)),
          ),
          title: 'Sans chevron',
          description: 'Cette carte n\'a pas de flèche à droite',
          showChevron: false,
        ),
        const SizedBox(height: AppSpacing.md),
        ListCard(
          icon: IconContainer(
            size: IconContainerSize.lg,
            backgroundColor: const Color(0xFFE5FFE5),
            child: Container(width: 24, height: 24, decoration: const BoxDecoration(color: AppColors.green, shape: BoxShape.circle)),
          ),
          title: 'Grande icône',
          description: 'Avec un container d\'icône plus grand',
          onTap: () {},
        ),
      ],
    );
  }

  Widget _buildTransactionListCardSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TransactionListCard(
          items: [
            TransactionListItemData(
              icon: Icons.storefront_rounded,
              iconColor: const Color(0xFF8E8E93),
              avatarBackgroundColor: const Color(0xFFE5E5EA),
              badgeStatus: TransactionBadgeStatus.pending,
              title: 'To Starbuck coffee',
              subtitle: '29 Feb, 20:37 · Merchant',
              amount: '€27.19',
              amountPrefix: '-',
              onTap: () {},
            ),
            TransactionListItemData(
              initial: 'M',
              iconColor: const Color(0xFF8E8E93),
              avatarBackgroundColor: const Color(0xFFE5E5EA),
              badgeStatus: TransactionBadgeStatus.completed,
              title: 'To Marc L.',
              subtitle: '29 Feb, 20:37',
              amount: '€27.19',
              amountPrefix: '-',
              onTap: () {},
            ),
            TransactionListItemData(
              icon: Icons.arrow_downward_rounded,
              iconColor: Colors.white,
              avatarBackgroundColor: const Color(0xFF22C55E),
              badgeStatus: TransactionBadgeStatus.completed,
              title: 'Virement entrant',
              subtitle: '28 Feb, 14:12 · SEPA',
              amount: '€1 250.00',
              amountPrefix: '+',
              amountColor: const Color(0xFF22C55E),
              onTap: () {},
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('Swap Crypto (avec onTap + pressed state)',
            style: AppTypography.bodySmall.copyWith(color: AppColors.textMuted)),
        const SizedBox(height: AppSpacing.sm),
        TransactionListCard(
          items: [
            TransactionListItemData(
              leadingWidget: _buildOverlappingAvatars('ETH', 'BTC'),
              title: 'ETH → BTC',
              subtitle: '25 mars 2026 · 14:37',
              amount: '-0.15 ETH',
              secondaryAmount: '+ 0.12 BTC',
              secondaryAmountColor: AppColors.green,
              onTap: () {},
            ),
            TransactionListItemData(
              leadingWidget: _buildOverlappingAvatars('BTC', 'EUR'),
              title: 'BTC → EUR',
              subtitle: '24 mars 2026 · 10:22',
              amount: '-0.05 BTC',
              secondaryAmount: '+ 2 980,00 €',
              secondaryAmountColor: AppColors.green,
              onTap: () {},
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xl),
        TransactionListCard(
          items: [
            TransactionListItemData(
              icon: Icons.euro_rounded,
              iconColor: Colors.white,
              avatarBackgroundColor: AppColors.blue,
              badgeStatus: TransactionBadgeStatus.completed,
              title: 'Euro Account',
              subtitle: 'Consider investing!',
              subtitleIcon: Icons.arrow_circle_right_outlined,
              amount: '00.00 €',
              showChevron: true,
              onTap: () {},
            ),
            TransactionListItemData(
              icon: Icons.trending_up_rounded,
              iconColor: Colors.white,
              avatarBackgroundColor: AppColors.green,
              badgeStatus: TransactionBadgeStatus.completed,
              title: 'Projets d\'épargne',
              subtitle: 'Open your first project!',
              subtitleIcon: Icons.arrow_circle_right_outlined,
              amount: '00.00 €',
              secondaryAmount: '▲ 20.26%',
              secondaryAmountColor: AppColors.green,
              showChevron: true,
              onTap: () {},
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPropertyCardSection() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: SizedBox(
        height: 520,
        child: PropertyCard(
          backgroundImageUrl: 'https://picsum.photos/800/1200?random=99',
          title: 'Niseko Mori Lodge',
          description:
              'Investissement locatif premium au coeur de la station de ski japonaise.',
          category: 'Immobilier',
          rate: 'Rate 11.24%',
          onInvest: () {},
          onBrochure: () {},
          onPhotos: () {},
          onVideos: () {},
          onBackPress: () {},
          onMenuPress: () {},
        ),
      ),
    );
  }

  Widget _buildInvestmentCardSection() {
    return InvestmentCard(
      imageUrl: 'https://picsum.photos/800/500?random=42',
      category: 'Immobilier',
      status: 'En cours',
      title: 'Nom de l\'offre',
      description:
          'Cum saepe multa, tum memini domi in hemicyclio sedentem',
      amount: '11 612 394 €',
      investorsCount: 43,
      progressLabel: 'Financement total',
      progressValue: '11M €',
      progress: 0.6,
      onInvest: () {},
      onFavorite: () {},
    );
  }

  Widget _buildMarketingCardsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MarketingCard(
          imageUrl: '',
          title: 'Small, sans bouton',
          size: MarketingCardSize.small,
        ),
        const SizedBox(height: AppSpacing.lg),
        MarketingCard(
          imageUrl: '',
          title: 'Medium avec bouton',
          label: 'Catégorie',
          buttonLabel: 'Action',
          onButtonTap: () {},
          size: MarketingCardSize.medium,
        ),
        const SizedBox(height: AppSpacing.lg),
        MarketingCard(
          imageUrl: '',
          title: 'Large avec bouton. Texte sur plusieurs lignes si besoin.',
          label: 'Real-time collaboration',
          buttonLabel: 'Essayer gratuitement',
          onButtonTap: () {},
          size: MarketingCardSize.large,
        ),
      ],
    );
  }

  Widget _buildMarketingCardPortraitSection() {
    return MarktingCardLargePortrait(
      imageAssetPath: 'assets/marketing_card_large_portrait.png',
      title: 'Fluidifiez vos\nprocessus de travail',
      onTap: () {},
    );
  }

  Widget _buildMarketingCardsCarouselSection() {
    final items = [
      MarketingCardsCarouselItem(
        imageUrl: 'https://picsum.photos/400/500?random=10',
        title: 'Réalisez vos projets avec nos experts',
        label: 'Services',
        logoLabel: 'R',
        buttonLabel: 'Découvrir',
        onButtonTap: () {},
      ),
      MarketingCardsCarouselItem(
        imageUrl: 'https://picsum.photos/400/500?random=11',
        title: 'Collaboration en temps réel',
        logoLabel: 'C',
        buttonLabel: 'Essayer gratuitement',
        onButtonTap: () {},
      ),
      MarketingCardsCarouselItem(
        imageUrl: 'https://picsum.photos/400/500?random=12',
        title: 'Formation sur mesure',
        label: 'Prochainement',
        logoLabel: 'F',
      ),
    ];
    return MarketingCardsCarousel(
      title: 'À la une',
      items: items,
    );
  }

  Widget _buildMarketingCardsSlidingSection() {
    final items = [
      MarketingCardsCarouselItem(
        imageUrl: 'https://picsum.photos/600/400?random=1',
        title: 'Revolut People',
        description: 'Gérez vos employés de A à Z sur une seule et même interface.',
        logoLabel: 'R',
      ),
      MarketingCardsCarouselItem(
        imageUrl: 'https://picsum.photos/600/400?random=2',
        title: 'Équipes & productivité',
        description: 'Productivité et suivi en temps réel.',
        logoLabel: 'A',
      ),
      MarketingCardsCarouselItem(
        imageUrl: 'https://picsum.photos/600/400?random=3',
        title: 'Collaboration temps réel',
        description: 'Une seule interface pour toute l\'équipe.',
        logoLabel: 'C',
      ),
    ];
    return MarketingCardsSlidingModule(
      title: 'À la une',
      items: items,
    );
  }

  Widget _buildBlogALaUneSection() {
    final items = [
      BlogALaUneItem(
        title: 'Premier article à la une : stratégie d\'investissement 2025',
        coverUrl:
            'https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800',
        readingTime: 5,
        onTap: () {},
        tags: const [
          NewsCardTag('Category'),
          NewsCardTag('Category'),
          NewsCardTag('Category'),
        ],
      ),
      BlogALaUneItem(
        title: 'Deuxième article — tendances marchés',
        coverUrl: '',
        readingTime: 8,
        onTap: () {},
        tag: 'Crypto',
      ),
      BlogALaUneItem(
        title: 'Troisième article à la une',
        coverUrl: '',
        readingTime: 3,
        onTap: () {},
      ),
    ];
    return BlogALaUne(
      title: 'A la une',
      onTitleTap: () {},
      items: items,
    );
  }

  Widget _buildVideoBlockArticleSection() {
    // Même sliding page à page que « Marketing cards (sliding) » (PageView).
    return VideoBlockArticleModule(
      title: 'Vidéos',
      items: [
        VideoBlockArticleItemData(
          title: 'Présentation du programme (vidéo)',
          posterUrl:
              'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800',
          videoUrl: 'https://www.youtube.com/watch?v=M7lc1UVf-VE',
          dateLabel: '7 avril 2026',
          onTap: () {},
        ),
        VideoBlockArticleItemData(
          title: 'Second focus vidéo',
          posterUrl:
              'https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?w=800',
          videoUrl: 'https://www.youtube.com/watch?v=M7lc1UVf-VE',
          dateLabel: '1 mars 2026',
          onTap: () {},
        ),
      ],
    );
  }

  Widget _buildBlogNewsSection() {
    final items = [
      BlogNewsItem(
        title: 'Premier article news : tendances marchés 2025',
        coverUrl: '',
        readingTime: 5,
        onTap: () {},
      ),
      BlogNewsItem(
        title: 'Deuxième article — crypto et régulation',
        coverUrl: '',
        readingTime: 8,
        onTap: () {},
      ),
      BlogNewsItem(
        title: 'Troisième article news',
        coverUrl: '',
        readingTime: 3,
        onTap: () {},
      ),
    ];
    return BlogNews(
      title: 'All news',
      items: items,
    );
  }

  Widget _buildNewsCardModuleSection() {
    final items = [
      NewsTransactionsListItem(
        title: 'Bitcoin repasse les 70 000\$ sur fond de flux ETF spot en hausse',
        dateLabel: '11 mars',
        authorName: 'Arquantix Research Desk',
        tags: ['Crypto'],
      ),
      NewsTransactionsListItem(
        title: 'Ethereum: l\'adoption des couches L2 accelere cote entreprises',
        dateLabel: '10 mars',
        authorName: 'Arquantix Research Desk',
        tags: ['Crypto'],
      ),
      NewsTransactionsListItem(
        title: 'Marché immobilier : les taux se stabilisent en Europe',
        dateLabel: '8 mars',
        authorName: 'Gael ITIER',
        tags: ['Real estate'],
      ),
    ];
    return NewsTransactionsListModule(
      title: 'Latest News',
      description: 'Retrouvez les dernieres actualites marche et crypto.',
      items: items,
    );
  }

  Widget _buildBottomSheetSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Grabber', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        Container(
          color: AppColors.pageBackground,
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: const Center(child: Grabber()),
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('SheetTitleBar', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.lg),
          ),
          child: SheetTitleBar(
            title: 'Title',
            leadingButton: SheetCircleButton.leading(onTap: () {}),
            trailingButton: SheetCircleButton.trailing(
              icon: Icons.check_rounded,
              onTap: () {},
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('BottomSheetContainer', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        BottomSheetContainer(
          toolbar: SheetTitleBar(
            title: 'Title',
            leadingButton: SheetCircleButton.leading(onTap: () {}),
            trailingButton: SheetCircleButton.trailing(
              icon: Icons.check_rounded,
              onTap: () {},
            ),
          ),
          children: [
            Text(
              'Achat effectué',
              textAlign: TextAlign.center,
              style: AppTypography.sectionTitle2.copyWith(
                color: const Color(0xFF8E8E93),
              ),
            ),
            Column(
              children: [
                Text(
                  '+0,0016 BTC',
                  textAlign: TextAlign.center,
                  style: AppTypography.heroAmount.copyWith(
                    fontSize: 34,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'au prix de 100 €',
                  textAlign: TextAlign.center,
                  style: AppTypography.bodyEmphasized,
                ),
              ],
            ),
            Center(
              child: FractionallySizedBox(
                widthFactor: 0.75,
                child: AppPrimaryButton(
                  label: 'Back to Bitcoin wallet',
                  variant: AppPrimaryButtonVariant.gray,
                  onPressed: () {},
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Composants du ZIP « Extraire composants pour Design Systeme » :
  /// [DsStepperAvatar], [DsMessageCard], [DsValidationResultBody].
  Widget _buildValidationModuleSection() {
    Widget stepperCell(String label, Widget stepper) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          stepper,
          const SizedBox(height: AppSpacing.xs),
          Text(label, style: AppTypography.itemSupporting),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'StepperAvatar : piste #E5E5EA + arc coloré ; erreur = croix #FF2D55 (Figma, sans disque plein).',
          style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
        ),
        const SizedBox(height: AppSpacing.lg),
        Wrap(
          spacing: AppSpacing.xl,
          runSpacing: AppSpacing.lg,
          crossAxisAlignment: WrapCrossAlignment.end,
          children: [
            stepperCell(
              'error',
              const DsStepperAvatar(
                status: DsStepperAvatarStatus.error,
                progress: 72,
              ),
            ),
            stepperCell(
              'success',
              const DsStepperAvatar(
                status: DsStepperAvatarStatus.success,
                progress: 100,
              ),
            ),
            stepperCell(
              'warning',
              const DsStepperAvatar(
                status: DsStepperAvatarStatus.warning,
                progress: 55,
              ),
            ),
            stepperCell(
              'info',
              const DsStepperAvatar(
                status: DsStepperAvatarStatus.info,
                progress: 40,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('MessageCard', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const DsMessageCard(
          title: 'Something went wrong with your transaction. Please try again.',
          caption: 'Recap line (caption)',
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('ValidationResultBody (ex. erreur numéro — inscription)', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        DecoratedBox(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.lg),
          ),
          child: const Padding(
            padding: EdgeInsets.symmetric(vertical: AppSpacing.xl),
            child: DsValidationResultBody(
              status: DsStepperAvatarStatus.error,
              progress: 100,
              headline: 'Check your number',
              messageTitle: 'Please enter a valid mobile number.',
            ),
          ),
        ),
      ],
    );
  }

  /// Écran type inscription : Face ID + notifications (ZIP Design System 4).
  Widget _buildPermissionAccessSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'DsIosStatusBarPlaceholder, DsPermissionHero (+ symbole Face ID SVG), DsPermissionPromptLayout. '
          'Titres = [AppTypography.headerPrimary], corps = [AppTypography.bodyRegular] + textMuted.',
          style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
        ),
        const SizedBox(height: AppSpacing.lg),
        ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          child: ColoredBox(
            color: AppColors.iosChromeBackground,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 620),
              child: SingleChildScrollView(
                child: DsPermissionPromptLayout(
                  showStatusBar: true,
                  title: 'Log in \nwith a single look',
                  body: 'Use Face ID to quickly log in \nto your account',
                  primaryButton: AppPrimaryButton(
                    label: 'Enable Face ID',
                    onPressed: () {},
                  ),
                  secondaryButton: AppPrimaryButton(
                    label: 'Not Now',
                    variant: AppPrimaryButtonVariant.secondary,
                    onPressed: () {},
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('Notifications — même layout, [symbol] personnalisé', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          child: ColoredBox(
            color: AppColors.iosChromeBackground,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 600),
              child: SingleChildScrollView(
                child: DsPermissionPromptLayout(
                  showStatusBar: true,
                  title: 'Restez informé',
                  body:
                      'Autorisez les notifications pour recevoir les alertes importantes sur votre compte.',
                  hero: const DsPermissionHero(
                    symbol: Icon(
                      Icons.notifications_active_outlined,
                      size: 64,
                      color: AppColors.indigo,
                    ),
                    symbolSize: 72,
                  ),
                  primaryButton: AppPrimaryButton(
                    label: 'Activer les notifications',
                    onPressed: () {},
                  ),
                  secondaryButton: AppPrimaryButton(
                    label: 'Pas maintenant',
                    variant: AppPrimaryButtonVariant.secondary,
                    onPressed: () {},
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  /// Sélecteur d’adresses : [DsAddressSelector], [DsAddressListItem] (ZIP 5).
  Widget _buildAddressSelectorZip5Section() {
    const demoAddresses = [
      DsAddressEntry(
        id: 'a1',
        title: '123 Avenue de la Paix',
        subtitle: '12345, Paris, France',
      ),
      DsAddressEntry(
        id: 'a2',
        title: '123 Avenue de la Paix',
        subtitle: '12345, Paris, France',
      ),
      DsAddressEntry(
        id: 'a3',
        title: '123 Avenue de la Paix',
        subtitle: '12345, Paris, France',
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Fond #F2F2F7, rayon 16, espacement 24 entre lignes ; lien indigo + '
          '[AppSmallButton] « Manual input » ; lignes = [DsAddressListItem].',
          style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
        ),
        const SizedBox(height: AppSpacing.lg),
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 343),
            child: DsAddressSelector(
              addresses: demoAddresses,
              onAddressSelect: (_) {},
              onManualInput: () {},
              onAddressNotHere: () {},
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('Ligne isolée (sans chevron)', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const DsAddressListItem(
          title: '45 Rue de Rivoli',
          subtitle: '75001 Paris, France',
          showChevron: false,
        ),
      ],
    );
  }

  Widget _buildModuleGainSection() {
    final weekData = [
      const BarChartData(label: 'Lun', value: 4.82),
      const BarChartData(label: 'Mar', value: 4.83),
      const BarChartData(label: 'Mer', value: 4.825),
      const BarChartData(label: 'Jeu', value: 4.83),
      const BarChartData(label: 'Ven', value: 4.84),
      const BarChartData(label: 'Sam', value: 4.85),
      const BarChartData(label: 'Dim', value: 4.845),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('BarChartModule', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        Container(
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
              colors: [Color(0xFF6B5DFF), Color(0xFF3B82F6)],
            ),
            borderRadius: BorderRadius.circular(AppRadius.lg),
          ),
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: BarChartModule(
            data: weekData,
            barColor: Colors.white,
            labelColor: Colors.white,
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('StatCard', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        StatCard(
          amount: '+125,00 €',
          amountColor: AppColors.indigo,
          period: 'ce mois',
          description: 'Augmentation de vos gains par rapport au mois précédent.',
          backgroundColor: AppColors.indigo,
          icon: const Icon(Icons.trending_up, size: 20, color: Color(0xFF636366)),
          chartWidget: BarChartModule(
            data: const [
              BarChartData(label: 'Lun', value: 120),
              BarChartData(label: 'Mar', value: 135),
              BarChartData(label: 'Mer', value: 125),
              BarChartData(label: 'Jeu', value: 140),
              BarChartData(label: 'Ven', value: 150),
            ],
            barColor: Colors.white,
            labelColor: Colors.white,
            showYLegend: false,
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('ModuleGain', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        ModuleGain(
          title: 'Module Gain',
          actionText: 'See more',
          onAction: () {},
          chartData: weekData,
          amount: '+34,59 €',
          period: 'cette semaine',
          description: 'Lorem ipsum dolor sit amet consectetur adipiscing elit.',
          amountColor: AppColors.green,
          backgroundColor: AppColors.green,
        ),
      ],
    );
  }

  Widget _buildArticleComponentsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('CategoryBadge', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            color: AppColors.gray6,
            borderRadius: BorderRadius.circular(AppRadius.lg),
          ),
          child: const Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              CategoryBadge(label: 'Economie', dotColor: Color(0xFFFF383C)),
              CategoryBadge(label: 'Crypto', dotColor: Color(0xFFFF8D28)),
              CategoryBadge(label: 'Banque', dotColor: Color(0xFF0088FF)),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Text('SurfaceTag (même enveloppe, contenu libre)', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            color: AppColors.gray6,
            borderRadius: BorderRadius.circular(AppRadius.lg),
          ),
          child: Wrap(
            spacing: AppSpacing.s2,
            runSpacing: AppSpacing.sm,
            children: [
              SurfaceTag(
                child: Text(
                  '-341,99 €',
                  style: AppTypography.supportingBdPerformanceChip.copyWith(
                    color: AppColors.semanticNegative,
                  ),
                ),
              ),
              SurfaceTag(
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    const MarketTrendCaret(
                      up: false,
                      color: AppColors.semanticNegative,
                    ),
                    const SizedBox(width: AppSpacing.s1),
                    Text(
                      '-0,56 %',
                      style: AppTypography.supportingBdPerformanceChip.copyWith(
                        color: AppColors.semanticNegative,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('ArticleQuoteBlock', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const ArticleQuoteBlock(
          quote: 'Si Trump doit envoyer des troupes au sol, il ne s\'en relèvera jamais.',
          author: 'Romuald Sciora, politologue.',
          asCard: true,
        ),
        const SizedBox(height: AppSpacing.md),
        const ArticleQuoteBlock(
          quote: 'Si Trump doit envoyer des troupes au sol.',
          author: 'Romuald Sciora.',
          asCard: false,
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('ArticleDocumentCard', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const ArticleDocumentCard(
          title: 'Titre du document',
          subtitle: 'PDF - 3.4Mo',
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('ArticleAuthorRow', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const ArticleAuthorRow(
          name: 'Nom de l\'auteur',
          subtitle: 'Date de l\'article',
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('ArticleImageBlock', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        ArticleImageBlock(
          imageUrl: '',
          caption: 'Légende, Copyright de l\'image',
          height: 140,
        ),
        const SizedBox(height: AppSpacing.md),
        Text('ArticleImageBlock (avec bordure)', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        ArticleImageBlock(
          imageUrl: '',
          caption: 'Graphique XRP/USDC — Scénario privilégié',
          height: 140,
          borderColor: ArticleImageBlock.borderMedium,
        ),
        const SizedBox(height: AppSpacing.md),
        Text('ArticleImageBlock (aspect ratio + bordure)', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        ArticleImageBlock(
          imageUrl: '',
          caption: 'Performance relative (XRP/BTC)',
          aspectRatio: 343 / 193,
          borderColor: ArticleImageBlock.borderLight,
        ),
        const SizedBox(height: AppSpacing.xxl),
        Text('ArticleVideoBlock', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        ArticleVideoBlock(
          thumbnailUrl: '',
          onPlay: () {},
          height: 140,
        ),
      ],
    );
  }

  Widget _buildExclusiveOfferSection() {
    final items = [
      const ExclusiveOfferCarouselItem(
        imageUrl: '',
        category: 'Real estate',
        title: 'Club deal résidentiel Lyon — opération regroupement locatif en zone tendue',
        progress: 0.65,
        raisedAmount: '813 700',
        investorsCount: 43,
        annualizedReturnPercent: 10.86,
        targetDurationMonths: 24,
        isLiked: false,
      ),
      const ExclusiveOfferCarouselItem(
        imageUrl: '',
        category: 'Energy',
        title: 'Fonds vert énergies renouvelables',
        progress: 0.44,
        raisedAmount: '450 000',
        investorsCount: 28,
        annualizedReturnPercent: 8.5,
        targetDurationMonths: 36,
        isLiked: false,
      ),
    ];
    return ExclusiveOffersCarousel(
      title: 'Exclusive Offers',
      onTitleTap: () {},
      withDescription: false,
      items: items,
    );
  }

  Widget _buildFeaturedOfferCardSection(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final cardWidth = (screenWidth - AppSpacing.xl * 2 - AppSpacing.md) / 1.05;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: cardWidth,
          child: FeaturedOfferCard(
            imageUrl: '',
            category: 'Energy',
            title: 'Hearst mining',
            description: 'Cum saepe multa, tum memini domi in hemicyclio sedentem',
            actionLabel: 'Investir',
            onTap: () {},
            showProgressBlock: true,
            progress: 0.65,
            raisedAmount: '813 700',
            investorsCount: 43,
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        SizedBox(
          width: cardWidth,
          child: FeaturedOfferCard(
            imageUrl: '',
            category: 'Crypto',
            title: 'Bundle DeFi',
            performancePercent: 2.45,
            actionLabel: 'Voir',
            onTap: () {},
            showProgressBlock: false,
          ),
        ),
      ],
    );
  }

  Widget _buildCategoriesTabSection() {
    return _CategoriesTabDemo();
  }

  Widget _buildOverlappingAvatars(String from, String to) {
    return TransactionSwapAvatar(
      fromTicker: from,
      toTicker: to,
    );
  }

  Widget _buildPasswordStrengthSection() {
    return const Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Strong'),
        SizedBox(height: AppSpacing.sm),
        PasswordStrengthIndicator(strength: PasswordStrength.strong),
        SizedBox(height: AppSpacing.lg),
        Text('Medium'),
        SizedBox(height: AppSpacing.sm),
        PasswordStrengthIndicator(strength: PasswordStrength.medium),
        SizedBox(height: AppSpacing.lg),
        Text('Weak'),
        SizedBox(height: AppSpacing.sm),
        PasswordStrengthIndicator(strength: PasswordStrength.weak),
        SizedBox(height: AppSpacing.lg),
        Text('None'),
        SizedBox(height: AppSpacing.sm),
        PasswordStrengthIndicator(strength: PasswordStrength.none),
      ],
    );
  }

  Widget _buildTagSection() {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: const [
        AppTag(label: 'Article', variant: AppTagVariant.article),
        AppTag(label: 'Breaking', variant: AppTagVariant.article, showDot: true),
        AppTag(label: '+2.45%', variant: AppTagVariant.performance, trend: AppTagTrend.up),
        AppTag(label: '-1.23%', variant: AppTagVariant.performance, trend: AppTagTrend.down),
        AppTag(label: 'Catégorie', variant: AppTagVariant.semantic),
        AppTag(label: 'Add', variant: AppTagVariant.semantic, showIcon: true),
        AppTag(label: 'Photo', variant: AppTagVariant.image),
      ],
    );
  }

  Widget _buildTransactionStepsSection() {
    return TransactionStepsModule(
      title: 'Détail de votre achat',
      steps: [
        TransactionStepItem(
          number: 1,
          title: 'Analyse de prix',
          primaryText: 'BTC → EUR | Price: 60 000,00 €',
          secondaryText:
              'Prix estimé par analyse des meilleures offres du marché',
          state: TransactionStepState.completed,
        ),
        TransactionStepItem(
          number: 2,
          title: 'Conversion estimée',
          primaryText: '120 € → 0,0019458 BTC',
          secondaryText:
              'Montant estimé par rapport au prix du marché',
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// ░░░  PRIVATE HELPER WIDGETS  ░░░
// ═══════════════════════════════════════════════════════════════════════════════

/// Accès à l’écran de configuration du code 6 chiffres (Keychain / Keystore).
class _SecurityPinSection extends StatelessWidget {
  const _SecurityPinSection();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
      child: Align(
        alignment: Alignment.centerLeft,
        child: AppPrimaryButton(
          label: 'Configurer le code d’accès',
          onPressed: () {
            Navigator.of(context).push<void>(
              MaterialPageRoute<void>(
                builder: (_) => const PasscodeSetupScreen(),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final Widget child;

  const _Section(this.title, this.child);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(
        left: AppSpacing.lg,
        right: AppSpacing.lg,
        bottom: AppSpacing.xxl,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: AppTypography.headerAppbar.copyWith(color: AppColors.indigo),
          ),
          const SizedBox(height: AppSpacing.md),
          child,
        ],
      ),
    );
  }
}

class _TokenChip extends StatelessWidget {
  final String label;

  const _TokenChip(this.label);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: AppColors.textSecondary.withValues(alpha: 0.3)),
      ),
      child: Text(label, style: AppTypography.itemSupporting),
    );
  }
}

class _ColorSwatch extends StatelessWidget {
  final String name;
  final Color color;

  const _ColorSwatch(this.name, this.color);

  @override
  Widget build(BuildContext context) {
    final isLight = color.computeLuminance() > 0.7;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(AppRadius.sm),
            border: Border.all(color: isLight ? Colors.grey.shade300 : Colors.transparent),
          ),
        ),
        const SizedBox(height: 4),
        Text(name, style: AppTypography.labelRegular),
      ],
    );
  }
}

class _ColorSwatchPair extends StatelessWidget {
  final String name;
  final Color primary;
  final Color? light;

  const _ColorSwatchPair(this.name, this.primary, this.light);

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: primary,
                shape: BoxShape.circle,
              ),
            ),
            if (light != null) ...[
              const SizedBox(width: 4),
              Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  color: light,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.grey.shade300),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 4),
        Text(name, style: AppTypography.labelRegular),
      ],
    );
  }
}

class _TabBarDemo extends StatefulWidget {
  @override
  State<_TabBarDemo> createState() => _TabBarDemoState();
}

class _TabBarDemoState extends State<_TabBarDemo> {
  int _selected = 0;

  static const _items = [
    AppTabBarItemData(icon: Icons.home_rounded, label: 'Accueil'),
    AppTabBarItemData(icon: Icons.trending_up_rounded, label: 'Investir'),
    AppTabBarItemData(icon: Icons.currency_bitcoin, label: 'Markets'),
    AppTabBarItemData(icon: Icons.radio_rounded, label: 'Design'),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF2C2C2E), Color(0xFF1C1C1E)],
        ),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      clipBehavior: Clip.antiAlias,
      padding: const EdgeInsets.only(top: AppSpacing.xl),
      child: AppTabBar(
        items: _items,
        selectedIndex: _selected,
        onTap: (i) => setState(() => _selected = i),
        actionIcon: Icons.search_rounded,
        onActionTap: () {},
      ),
    );
  }
}

class _SettingsShowcaseDemo extends StatefulWidget {
  @override
  State<_SettingsShowcaseDemo> createState() => _SettingsShowcaseDemoState();
}

class _SettingsShowcaseDemoState extends State<_SettingsShowcaseDemo> {
  bool _toggle1 = true;
  bool _toggle2 = false;
  bool _toggle3 = true;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('AppToggleSwitch', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            AppToggleSwitch(value: _toggle1, onChanged: (v) => setState(() => _toggle1 = v)),
            const SizedBox(width: AppSpacing.lg),
            AppToggleSwitch(value: _toggle2, onChanged: (v) => setState(() => _toggle2 = v)),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('SettingsActionButton', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            SettingsActionButton(label: 'Copy', actionType: SettingsActionType.copy, onTap: () {}),
            const SizedBox(width: AppSpacing.xxl),
            SettingsActionButton(label: 'Edit', actionType: SettingsActionType.edit, onTap: () {}),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('Variante 1 — Avatar + Value + Chevron', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        SettingsCard(
          children: [
            SettingsListItem(
              leading: const IconContainer(
                child: Icon(Icons.person_rounded, size: 16, color: Color(0xFF8E8E93)),
              ),
              title: 'Mon compte',
              subtitle: 'john@example.com',
              value: 'Actif',
              showChevron: true,
              onTap: () {},
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('Variante 2 — Plusieurs items avec avatar', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        SettingsCard(
          children: [
            SettingsListItem(
              leading: const IconContainer(
                child: Icon(Icons.account_circle_rounded, size: 16, color: Color(0xFF8E8E93)),
              ),
              title: 'Profil utilisateur',
              subtitle: 'Informations personnelles',
              value: 'Complété',
              showChevron: true,
            ),
            SettingsListItem(
              leading: const IconContainer(
                child: Icon(Icons.security_rounded, size: 16, color: Color(0xFF8E8E93)),
              ),
              title: 'Sécurité',
              subtitle: '2FA activé',
              value: 'Actif',
              showChevron: true,
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('Variante 3 — Description longue', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const SettingsCard(
          children: [
            SettingsListItem(
              leading: IconContainer(
                child: Icon(Icons.info_outline_rounded, size: 16, color: Color(0xFF8E8E93)),
              ),
              title: 'Informations légales',
              description: 'Proinde concepta rabie saeviore, quam desperatio incendebat et fames.',
            ),
            SettingsListItem(
              leading: IconContainer(
                child: Icon(Icons.policy_rounded, size: 16, color: Color(0xFF8E8E93)),
              ),
              title: 'Politique de confidentialité',
              description: 'Proinde concepta rabie saeviore, quam desperatio incendebat et fames.',
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('Variante 5 — Icône 24px + Value', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const SettingsCard(
          children: [
            SettingsListItem(
              leading: Icon(Icons.language_rounded, size: 24),
              title: 'Langue',
              value: 'Français',
              showChevron: true,
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('Variante 7 — Value + Sous-valeur', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const SettingsCard(
          children: [
            SettingsListItem(
              title: 'Frais de gestion',
              value: '1.5%',
              valueSubtext: 'annuel',
              showChevron: true,
            ),
            SettingsListItem(
              title: 'Abonnement',
              value: '9.99 €',
              valueSubtext: 'mensuel',
              showChevron: true,
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('Variante 8 — Toggle', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        SettingsCard(
          children: [
            SettingsListItem(
              title: 'Mode sombre',
              trailing: AppToggleSwitch(value: _toggle1, onChanged: (v) => setState(() => _toggle1 = v)),
            ),
            SettingsListItem(
              title: 'Notifications push',
              trailing: AppToggleSwitch(value: _toggle2, onChanged: (v) => setState(() => _toggle2 = v)),
            ),
            SettingsListItem(
              title: 'Données biométriques',
              trailing: AppToggleSwitch(value: _toggle3, onChanged: (v) => setState(() => _toggle3 = v)),
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('Variante 10 — Action Button', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        SettingsCard(
          children: [
            SettingsListItem(
              leading: const Icon(Icons.info_outline_rounded, size: 16, color: Color(0xFFAEAEB2)),
              title: 'Adresse du portefeuille',
              trailing: SettingsActionButton(label: 'Copy', actionType: SettingsActionType.copy, onTap: () {}),
            ),
            SettingsListItem(
              leading: const Icon(Icons.help_outline_rounded, size: 16, color: Color(0xFFAEAEB2)),
              title: 'Référence client',
              trailing: SettingsActionButton(label: 'Copy', actionType: SettingsActionType.copy, onTap: () {}),
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('Variante 13 — Section Title + Table', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const SettingsCard(
          sectionTitle: 'Title Section',
          footer: SettingsTableFooter(label: 'Item', value: 'Item 1'),
          children: [
            SettingsTableRow(label: 'Item', value: 'Item 1'),
            SettingsTableRow(label: 'Item', value: 'Item 1'),
            SettingsTableRow(label: 'Item', value: 'Item 1'),
          ],
        ),

        const SizedBox(height: AppSpacing.xxl),

        Text('Variante 14 — Avatar cercle', style: AppTypography.itemPrimary),
        const SizedBox(height: AppSpacing.sm),
        const SettingsCard(
          children: [
            SettingsListItem(
              leading: IconContainer(
                borderRadius: 100,
                child: Icon(Icons.person_rounded, size: 16, color: Color(0xFF8E8E93)),
              ),
              title: 'Utilisateur 1',
            ),
            SettingsListItem(
              leading: IconContainer(
                borderRadius: 100,
                child: Icon(Icons.person_rounded, size: 16, color: Color(0xFF8E8E93)),
              ),
              title: 'Utilisateur 2',
            ),
          ],
        ),
      ],
    );
  }
}

class _SearchInputDemo extends StatefulWidget {
  @override
  State<_SearchInputDemo> createState() => _SearchInputDemoState();
}

class _SearchInputDemoState extends State<_SearchInputDemo> {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('White variant', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppSearchInput(
          placeholder: 'Rechercher',
          variant: AppSearchInputVariant.white,
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Gray variant', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppSearchInput(
          placeholder: 'Rechercher',
          variant: AppSearchInputVariant.gray,
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Focused variant (auto-border)', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppSearchInput(
          placeholder: 'Rechercher',
          variant: AppSearchInputVariant.focused,
          onChanged: (_) => setState(() {}),
        ),
      ],
    );
  }
}

class _TextInputDemo extends StatefulWidget {
  @override
  State<_TextInputDemo> createState() => _TextInputDemoState();
}

class _TextInputDemoState extends State<_TextInputDemo> {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Default', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppTextInput(
          label: 'Email',
          showEmailIcon: true,
          showClearButton: true,
          description: 'Entrez votre adresse email professionnelle',
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Password with toggle', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        const AppTextInput(
          label: 'Password',
          obscureText: true,
          showPasswordToggle: true,
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Error state', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        const AppTextInput(
          label: 'Email',
          error: 'Adresse email invalide',
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('Placeholder variant', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        const AppTextInput(
          label: 'Search or enter a value…',
          variant: AppTextInputVariant.placeholder,
          showClearButton: true,
        ),
      ],
    );
  }
}

class _PhoneInputDemo extends StatefulWidget {
  @override
  State<_PhoneInputDemo> createState() => _PhoneInputDemoState();
}

class _PhoneInputDemoState extends State<_PhoneInputDemo> {
  String _country = 'FR';

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Default (FR)', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppPhoneInput(
          label: 'Phone number',
          countryCode: _country,
          onCountryChanged: (v) => setState(() => _country = v),
          onPhoneChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('With error', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        const AppPhoneInput(
          label: 'Phone number',
          countryCode: 'US',
          error: 'Invalid phone number',
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Disabled', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        const AppPhoneInput(
          label: 'Phone number',
          countryCode: 'GB',
          enabled: false,
        ),
      ],
    );
  }
}

class _DateInputDemo extends StatefulWidget {
  @override
  State<_DateInputDemo> createState() => _DateInputDemoState();
}

class _DateInputDemoState extends State<_DateInputDemo> {
  DateTime? _dateValue;
  DateTime? _birthDateValue;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Default', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppDateInput(
          label: 'Date',
          value: _dateValue,
          onChanged: (v) => setState(() => _dateValue = v),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Date of Birth (future dates blocked)',
            style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        AppDateInput(
          label: 'Date of Birth',
          value: _birthDateValue,
          isBirthDate: true,
          required: true,
          onChanged: (v) => setState(() => _birthDateValue = v),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('With error', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        const AppDateInput(
          label: 'Date',
          error: 'This field is required',
          onChanged: _noOp,
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Disabled', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        const AppDateInput(
          label: 'Date',
          enabled: false,
          onChanged: _noOp,
        ),
      ],
    );
  }

  static void _noOp(DateTime? _) {}
}

class _RadioButtonDemo extends StatefulWidget {
  @override
  State<_RadioButtonDemo> createState() => _RadioButtonDemoState();
}

class _RadioButtonDemoState extends State<_RadioButtonDemo> {
  int _selected = 0;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppRadioButton(
          checked: _selected == 0,
          label: 'Option 1 (selected)',
          onChanged: (_) => setState(() => _selected = 0),
        ),
        const SizedBox(height: AppSpacing.md),
        AppRadioButton(
          checked: _selected == 1,
          label: 'Option 2',
          onChanged: (_) => setState(() => _selected = 1),
        ),
        const SizedBox(height: AppSpacing.md),
        const AppRadioButton(
          checked: false,
          disabled: true,
          label: 'Disabled',
        ),
        const SizedBox(height: AppSpacing.md),
        const AppRadioButton(
          checked: true,
          disabled: true,
          label: 'Disabled + Checked',
        ),
      ],
    );
  }
}

class _CheckboxDemo extends StatefulWidget {
  @override
  State<_CheckboxDemo> createState() => _CheckboxDemoState();
}

class _CheckboxDemoState extends State<_CheckboxDemo> {
  bool _c1 = true;
  bool _c2 = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppCheckbox(
          checked: _c1,
          label: 'Checked',
          onChanged: (v) => setState(() => _c1 = v),
        ),
        const SizedBox(height: AppSpacing.md),
        AppCheckbox(
          checked: _c2,
          label: 'Unchecked',
          onChanged: (v) => setState(() => _c2 = v),
        ),
        const SizedBox(height: AppSpacing.md),
        const AppCheckbox(
          checked: false,
          disabled: true,
          label: 'Disabled',
        ),
        const SizedBox(height: AppSpacing.md),
        const AppCheckbox(
          checked: true,
          disabled: true,
          label: 'Disabled + Checked',
        ),
        const SizedBox(height: AppSpacing.xl),
        Text('With rich description', style: AppTypography.itemSupporting),
        const SizedBox(height: AppSpacing.sm),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
          ),
          child: AppCheckbox(
            checked: _c1,
            label: 'I confirm I have read, understood and agree to be bound by:',
            description:
                '[Terms and Conditions](https://example.com/terms), '
                '[Best execution policy](https://example.com/policy), '
                '[Customer privacy notice](https://example.com/privacy). '
                'By confirming, I also agree to receive these documents as website links',
            onChanged: (v) => setState(() => _c1 = v),
          ),
        ),
      ],
    );
  }
}

class _CategoriesTabDemo extends StatefulWidget {
  @override
  State<_CategoriesTabDemo> createState() => _CategoriesTabDemoState();
}

class _CategoriesTabDemoState extends State<_CategoriesTabDemo> {
  int _selectedIndex = 0;

  static const List<CategoriesTabItem> _items = [
    CategoriesTabItem(
      imageUrl: '',
      title: 'Chefs privés',
      description: 'Prochainement',
    ),
    CategoriesTabItem(
      imageUrl: '',
      title: 'Photographie',
      description: '5 services disponibles',
    ),
    CategoriesTabItem(
      imageUrl: '',
      title: 'Massage',
      description: 'Prochainement',
    ),
    CategoriesTabItem(
      imageUrl: '',
      title: 'Bien-être',
      description: '3 services',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return CategoriesTab(
      title: 'Catégories',
      items: _items,
      selectedIndex: _selectedIndex,
      onSelected: (index) => setState(() => _selectedIndex = index),
    );
  }
}

// ══════════════════════════════════════════════════════════════════
// ░░░  NEW DS COMPONENTS — DEMOS  ░░░
// ══════════════════════════════════════════════════════════════════

class _TextareaDemo extends StatefulWidget {
  @override
  State<_TextareaDemo> createState() => _TextareaDemoState();
}

class _TextareaDemoState extends State<_TextareaDemo> {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        AppTextarea(
          label: 'Message',
          placeholder: 'Écrivez votre message ici…',
          description: '0 / 500 caractères',
        ),
        const SizedBox(height: AppSpacing.md),
        AppTextarea(
          label: 'Avec erreur',
          placeholder: 'Champ requis',
          error: 'Ce champ est obligatoire',
        ),
      ],
    );
  }
}

class _OtpInputDemo extends StatefulWidget {
  @override
  State<_OtpInputDemo> createState() => _OtpInputDemoState();
}

class _OtpInputDemoState extends State<_OtpInputDemo> {
  String _code = '';

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        AppOtpInput(
          length: 6,
          autofocus: false,
          onChanged: (v) => setState(() => _code = v),
          onCompleted: (_) {},
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Code saisi : $_code',
          style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.lg),
        AppOtpInput(
          length: 4,
          autofocus: false,
          hasError: true,
          errorMessage: 'Code invalide',
        ),
      ],
    );
  }
}

class _SliderDemo extends StatefulWidget {
  @override
  State<_SliderDemo> createState() => _SliderDemoState();
}

class _SliderDemoState extends State<_SliderDemo> {
  double _value = 0.4;
  double _discrete = 50;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Continu : ${(_value * 100).toInt()}%',
            style: AppTypography.labelRegular),
        AppSlider(
          value: _value,
          onChanged: (v) => setState(() => _value = v),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Discret : ${_discrete.toInt()}',
            style: AppTypography.labelRegular),
        AppSlider(
          value: _discrete,
          min: 0,
          max: 100,
          divisions: 10,
          label: '${_discrete.toInt()}',
          onChanged: (v) => setState(() => _discrete = v),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Désactivé', style: AppTypography.labelRegular),
        AppSlider(
          value: 0.6,
          onChanged: null,
          enabled: false,
        ),
      ],
    );
  }
}

Widget _buildAlertSection() {
  return Column(
    children: [
      const AppAlert(
        variant: AppAlertVariant.info,
        title: 'Information',
        description: 'Votre compte a été vérifié avec succès.',
      ),
      const SizedBox(height: AppSpacing.md),
      const AppAlert(
        variant: AppAlertVariant.warning,
        title: 'Attention',
        description: 'Votre session expire dans 5 minutes.',
      ),
      const SizedBox(height: AppSpacing.md),
      const AppAlert(
        variant: AppAlertVariant.error,
        title: 'Erreur',
        description: 'Impossible de traiter votre demande.',
      ),
      const SizedBox(height: AppSpacing.md),
      const AppAlert(
        variant: AppAlertVariant.success,
        title: 'Succès',
        description: 'Votre transaction a été confirmée.',
      ),
    ],
  );
}

Widget _buildDsSuccessIconSection() {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Pastille [semanticPositive] + check blanc — tailles 16 / 20 / 24 px.',
        style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
      ),
      const SizedBox(height: AppSpacing.lg),
      Row(
        children: [
          const DsSuccessIcon(size: 16),
          const SizedBox(width: AppSpacing.md),
          const DsSuccessIcon(size: 20),
          const SizedBox(width: AppSpacing.md),
          const DsSuccessIcon(size: 24),
          const SizedBox(width: AppSpacing.lg),
          Text('À côté du texte', style: AppTypography.itemPrimary),
          const SizedBox(width: AppSpacing.sm),
          const DsSuccessIcon(),
        ],
      ),
    ],
  );
}

class _ProgressBarDemo extends StatefulWidget {
  @override
  State<_ProgressBarDemo> createState() => _ProgressBarDemoState();
}

class _ProgressBarDemoState extends State<_ProgressBarDemo> {
  double _progress = 0.65;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Déterminée : ${(_progress * 100).toInt()}%',
            style: AppTypography.labelRegular),
        const SizedBox(height: AppSpacing.sm),
        AppProgressBar(value: _progress),
        const SizedBox(height: AppSpacing.sm),
        AppSlider(
          value: _progress,
          onChanged: (v) => setState(() => _progress = v),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Indéterminée', style: AppTypography.labelRegular),
        const SizedBox(height: AppSpacing.sm),
        const AppProgressBar(),
        const SizedBox(height: AppSpacing.lg),
        Text('Personnalisée (vert, 10px)',
            style: AppTypography.labelRegular),
        const SizedBox(height: AppSpacing.sm),
        AppProgressBar(
          value: 0.8,
          height: 10,
          color: AppColors.semanticPositive,
          backgroundColor: AppColors.semanticPositiveLight,
        ),
      ],
    );
  }
}

Widget _buildSkeletonSection() {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const AppSkeleton(width: 200, height: 14),
      const SizedBox(height: AppSpacing.md),
      const AppSkeleton(width: 140, height: 14),
      const SizedBox(height: AppSpacing.lg),
      Row(
        children: const [
          AppSkeleton(width: 48, height: 48, borderRadius: 9999),
          SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppSkeleton(height: 14),
                SizedBox(height: AppSpacing.sm),
                AppSkeleton(width: 120, height: 12),
              ],
            ),
          ),
        ],
      ),
      const SizedBox(height: AppSpacing.lg),
      const AppSkeleton(height: 160),
    ],
  );
}

Widget _buildSheetListItemSection() {
  return Column(
    children: [
      AppSheetListItem(
        title: 'France',
        subtitle: '+33',
        leading: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: AppColors.indigo.withValues(alpha: 0.1),
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: const Text('🇫🇷', style: TextStyle(fontSize: 20)),
        ),
        selected: true,
      ),
      const SizedBox(height: AppSpacing.sm),
      AppSheetListItem(
        title: 'United States',
        subtitle: '+1',
        leading: Container(
          width: 36,
          height: 36,
          decoration: const BoxDecoration(
            color: Color(0xFFF2F2F7),
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: const Text('🇺🇸', style: TextStyle(fontSize: 20)),
        ),
      ),
      const SizedBox(height: AppSpacing.sm),
      const AppSheetListItem(
        title: 'Option sans icône',
        subtitle: 'Description courte',
        showChevron: false,
      ),
      const SizedBox(height: AppSpacing.sm),
      const AppSheetListItem(
        title: 'Option sélectionnée',
        selected: true,
        showChevron: false,
      ),
    ],
  );
}

// ─── Démonstrations interactives FormRadioRow / FormCheckboxRow (design system) ───

Widget _dsWhiteSelectionModule({required List<Widget> children}) {
  return Container(
    width: double.infinity,
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.06),
          blurRadius: 12,
          offset: const Offset(0, 4),
        ),
      ],
    ),
    child: ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.all(kSelectionModuleInnerPadding),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: children,
        ),
      ),
    ),
  );
}

class _DsFormRadioRowInteractiveDemo extends StatefulWidget {
  const _DsFormRadioRowInteractiveDemo();

  @override
  State<_DsFormRadioRowInteractiveDemo> createState() =>
      _DsFormRadioRowInteractiveDemoState();
}

class _DsFormRadioRowInteractiveDemoState
    extends State<_DsFormRadioRowInteractiveDemo> {
  static const _labels = [
    'Employed',
    'Self-employed',
    'Student',
    'Unemployed',
    'Retired',
  ];

  int _selectedIndex = 1;

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[];
    for (var i = 0; i < _labels.length; i++) {
      if (i > 0) {
        rows.add(const SizedBox(height: kSelectionRowSpacing));
      }
      rows.add(
        FormRadioRow(
          label: _labels[i],
          selected: _selectedIndex == i,
          onSelect: () => setState(() => _selectedIndex = i),
        ),
      );
    }
    return _dsWhiteSelectionModule(children: rows);
  }
}

class _DsFormCheckboxRowInteractiveDemo extends StatefulWidget {
  const _DsFormCheckboxRowInteractiveDemo();

  @override
  State<_DsFormCheckboxRowInteractiveDemo> createState() =>
      _DsFormCheckboxRowInteractiveDemoState();
}

class _DsFormCheckboxRowInteractiveDemoState
    extends State<_DsFormCheckboxRowInteractiveDemo> {
  static const _labels = [
    'Salary',
    'Business income',
    'Investment income',
    'Savings',
  ];

  final Set<int> _checked = {0, 1};

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[];
    for (var i = 0; i < _labels.length; i++) {
      if (i > 0) {
        rows.add(const SizedBox(height: kSelectionRowSpacing));
      }
      rows.add(
        FormCheckboxRow(
          label: _labels[i],
          checked: _checked.contains(i),
          onToggle: () {
            setState(() {
              if (_checked.contains(i)) {
                _checked.remove(i);
              } else {
                _checked.add(i);
              }
            });
          },
        ),
      );
    }
    return _dsWhiteSelectionModule(children: rows);
  }
}
