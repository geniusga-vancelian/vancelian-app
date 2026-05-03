import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import '../atoms/kalai_icons.dart';
import 'amount_display.dart';
import 'dot_spinner.dart';
import 'kalai_icon.dart';

/// Unified page layout for all confirmation / preview screens.
///
/// Provides a shared structure:
/// 1. Header (back button + centered title + optional trailing)
/// 2. Scrollable hero + body content
/// 3. Fixed bottom bar with blur backdrop + CTA
///
/// Used by Buy, Swap, Exclusive Offer, and Bundle confirmation screens.
class WealthubConfirmationPageLayout extends StatelessWidget {
  const WealthubConfirmationPageLayout({
    super.key,
    required this.headline,
    required this.heroAmount,
    required this.ctaLabel,
    required this.onConfirm,
    this.onBack,
    this.executing = false,
    this.executingLabel = 'Vérification…',
    this.directionIndicator,
    this.approximateValue,
    this.subtitle,
    this.priceLine,
    this.eurApproxValue,
    this.bodyChildren = const [],
    this.loading = false,
    this.errorMessage,
    this.onRetry,
  });

  /// Back button callback. Defaults to `Navigator.pop`.
  final VoidCallback? onBack;

  /// Whether the confirm action is in progress.
  final bool executing;

  // ── Hero Section ──

  /// Widget displayed between header and headline (e.g. logo direction row).
  final Widget? directionIndicator;

  /// Primary label above the hero amount (e.g. "Vous êtes sur le point d'acheter").
  final String headline;

  /// Large amount (e.g. "0.03267973 BTC").
  final String heroAmount;

  /// Approximate value below hero (e.g. "≈ 2 000,00 €"). Hidden if null.
  final String? approximateValue;

  /// Subtitle below approximate value (e.g. "dans l'offre exclusive…").
  final String? subtitle;

  /// Price context line below amount (e.g. "au prix de 10 ETH").
  final String? priceLine;

  /// Approximate EUR value displayed between parentheses in gray
  /// (e.g. "(= 100 EUR)").
  final String? eurApproxValue;

  // ── Body ──

  /// Screen-specific content: steps module, allocation breakdown, legal footer, etc.
  final List<Widget> bodyChildren;

  // ── Bottom Bar ──

  /// CTA button label.
  final String ctaLabel;

  /// Called when CTA is tapped.
  final VoidCallback? onConfirm;

  /// Label shown during execution.
  final String executingLabel;

  // ── Loading / Error ──

  /// Show a centered spinner.
  final bool loading;

  /// Show a centered error view. If null, body is shown.
  final String? errorMessage;

  /// Retry callback for the error view.
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: SafeArea(
        child: Column(
          children: [
            _Header(
              onBack: onBack ?? () => Navigator.of(context).pop(),
              enabled: !executing,
            ),
            if (loading)
              const Expanded(child: _LoadingView())
            else if (errorMessage != null)
              Expanded(child: _ErrorView(message: errorMessage!, onRetry: onRetry))
            else
              Expanded(
                child: Stack(
                  children: [
                    Positioned.fill(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (directionIndicator != null) ...[
                              const SizedBox(height: 24),
                              Center(child: directionIndicator!),
                              const SizedBox(height: 20),
                            ] else
                              const SizedBox(height: 32),
                            Text(
                              headline,
                              textAlign: TextAlign.center,
                              style: AppTypography.titleLarge.copyWith(
                                color: AppColors.textPrimary,
                                fontWeight: FontWeight.w700,
                                height: 1.35,
                              ),
                            ),
                            const SizedBox(height: 8),
                      AmountDisplay(
                        amount: heroAmount,
                        subtitle: priceLine ?? approximateValue ?? '',
                        subtext: eurApproxValue ?? subtitle,
                      ),
                            const SizedBox(height: 40),
                            ...bodyChildren,
                            const SizedBox(height: 100),
                          ],
                        ),
                      ),
                    ),
                    Positioned(
                      left: 0,
                      right: 0,
                      bottom: 0,
                      child: _BottomBar(
                        ctaLabel: ctaLabel,
                        executingLabel: executingLabel,
                        executing: executing,
                        onConfirm: onConfirm,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Backward-compatible alias.
typedef ConfirmationPageLayout = WealthubConfirmationPageLayout;

// ── Header ──────────────────────────────────────────────────────────────────

class _Header extends StatelessWidget {
  const _Header({required this.onBack, this.enabled = true});

  final VoidCallback onBack;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.sm,
      ),
      child: SizedBox(
        height: kToolbarHeight,
        child: Row(
          children: [
            _BackDisk(onTap: enabled ? onBack : () {}),
            const Spacer(),
            Text(
              'Confirmation',
              style: AppTypography.titleMedium.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            const Spacer(),
            const SizedBox(width: 36),
          ],
        ),
      ),
    );
  }
}

class _BackDisk extends StatelessWidget {
  const _BackDisk({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        customBorder: const CircleBorder(),
        child: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.cardBackground,
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.06),
                blurRadius: 4,
                offset: const Offset(0, 1),
              ),
            ],
          ),
          alignment: Alignment.center,
          child: const KalaiIcon(KalaiIcons.arrowLeft,
              size: 20, color: AppColors.textPrimary),
        ),
      ),
    );
  }
}

// ── Bottom Bar ──────────────────────────────────────────────────────────────

/// Diameter of the info circle on the left side of the bottom bar.
const double _kInfoDiskSize = 48;

class _BottomBar extends StatelessWidget {
  const _BottomBar({
    required this.ctaLabel,
    required this.executingLabel,
    required this.executing,
    required this.onConfirm,
  });

  final String ctaLabel;
  final String executingLabel;
  final bool executing;
  final VoidCallback? onConfirm;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            AppColors.pageBackground.withValues(alpha: 0.0),
            AppColors.pageBackground.withValues(alpha: 0.3),
            AppColors.pageBackground.withValues(alpha: 1.0),
          ],
          stops: const [0.0, 0.15, 1.0],
        ),
      ),
      child: Padding(
        padding: EdgeInsets.only(
          left: AppSpacing.lg,
          right: AppSpacing.lg,
          bottom: MediaQuery.of(context).viewPadding.bottom > 0 ? 8 : 16,
          top: 20,
        ),
        child: Row(
          children: [
            Container(
              width: _kInfoDiskSize,
              height: _kInfoDiskSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.cardBackground,
                boxShadow: [
                  BoxShadow(
                    color: AppColors.textPrimary.withValues(alpha: 0.06),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              alignment: Alignment.center,
              child: const KalaiIcon(KalaiIcons.info,
                  size: 22, color: AppColors.textSecondary),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: SizedBox(
                height: _kInfoDiskSize,
                child: FilledButton(
                  onPressed: executing ? null : onConfirm,
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.indigo,
                    foregroundColor: Colors.white,
                    disabledBackgroundColor: AppColors.indigo,
                    disabledForegroundColor: Colors.white,
                    shape: const StadiumBorder(),
                    elevation: 4,
                    shadowColor: AppColors.indigo.withValues(alpha: 0.35),
                  ),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    switchInCurve: Curves.easeOut,
                    switchOutCurve: Curves.easeIn,
                    child: executing
                        ? const SizedBox(
                            key: ValueKey('loader'),
                            width: 20,
                            height: 20,
                            child: DotSpinner(
                              size: 20,
                              color: Colors.white,
                            ),
                          )
                        : Text(
                            ctaLabel,
                            key: const ValueKey('label'),
                            style: AppTypography.titleMedium.copyWith(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Loading / Error ────────────────────────────────────────────────────────

class _LoadingView extends StatelessWidget {
  const _LoadingView();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: CircularProgressIndicator(
        color: AppColors.indigo,
        strokeWidth: 2,
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.textPrimary,
              ),
              alignment: Alignment.center,
              child: const KalaiIcon(KalaiIcons.clear,
                  size: 32, color: Colors.white),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              message,
              style: AppTypography.sectionTitle,
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: AppSpacing.xxl),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: onRetry,
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.indigo,
                    foregroundColor: Colors.white,
                    shape: const StadiumBorder(),
                  ),
                  child: const Text('Réessayer'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
