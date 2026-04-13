import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/components/app_primary_button.dart';
import '../../../../design_system/components/ds_success_icon.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';
import '../../../../design_system/components/list_card.dart';
import '../../../../design_system/components/setup_progress_card.dart';
import '../../../../core/profile_identity_coordinator.dart';
import '../../../../l10n/app_localizations.dart';
import '../../../profile/data/mobile_app_profile.dart';
import '../../analytics/activation_journey_funnel_events.dart';
import '../../domain/activation_journey_models.dart';
import '../activation_stage_ui_helpers.dart';

/// Lignes non terminées : même destination que le CTA ([effectiveActivationPrimaryRoute]).
VoidCallback? _activationRowTap({
  required ActivationJourneyStage stage,
  required ActivationJourney journey,
  required MobileAppProfile? profile,
  required void Function(String route) onTargetRoute,
}) {
  if (isActivationStageCompleted(stage, profile)) {
    return null;
  }
  final r = effectiveActivationPrimaryRoute(journey, profile)?.trim() ?? '';
  if (r.isEmpty) {
    return null;
  }
  return () => onTargetRoute(r);
}

/// Enveloppe le module : émet [ActivationJourneyFunnelEvents.stepViewed] quand l’étape « next » change.
class ActivationJourneyExposure extends StatefulWidget {
  const ActivationJourneyExposure({
    super.key,
    required this.journey,
    required this.child,
  });

  final ActivationJourney journey;
  final Widget child;

  @override
  State<ActivationJourneyExposure> createState() =>
      _ActivationJourneyExposureState();
}

class _ActivationJourneyExposureState extends State<ActivationJourneyExposure> {
  String? _lastEmittedKey;

  String? _nextStepKey(ActivationJourney j) {
    for (final s in j.stages) {
      if (s.isNextStep) return s.key;
    }
    return activationStepKeyForTargetRoute(j.primaryCtaTargetRoute ?? '');
  }

  void _emitIfNeeded() {
    final k = _nextStepKey(widget.journey);
    if (k != null && k != _lastEmittedKey) {
      _lastEmittedKey = k;
      ActivationJourneyFunnelEvents.stepViewed(stepKey: k);
    }
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _emitIfNeeded();
    });
  }

  @override
  void didUpdateWidget(covariant ActivationJourneyExposure oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.journey.weightedProgressPercent !=
            widget.journey.weightedProgressPercent ||
        oldWidget.journey.primaryCtaTargetRoute !=
            widget.journey.primaryCtaTargetRoute ||
        oldWidget.journey.stages.length != widget.journey.stages.length) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _emitIfNeeded();
      });
    }
  }

  @override
  Widget build(BuildContext context) => widget.child;
}

/// Bandeau discret lorsque le parcours est terminé (`show_module` false, `activation_complete` true).
class ActivationJourneyCompletionStrip extends StatelessWidget {
  const ActivationJourneyCompletionStrip({
    super.key,
    required this.message,
  });

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: BoxDecoration(
        color: const Color(0xFFE8F5E9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF34C759).withValues(alpha: 0.35)),
      ),
      child: Row(
        children: [
          const Icon(Icons.check_circle_rounded, color: Color(0xFF34C759), size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: GoogleFonts.inter(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Taille [DsSuccessIcon] pour les lignes terminées — palier DS sous 32 (défaut 16).
const double _kActivationRowSuccessIconSize = 24;

/// Module Home activation — étapes réussies en « disabled » + [DsSuccessIcon] ; à venir bien visibles.
class ActivationJourneyHomeModule extends StatelessWidget {
  const ActivationJourneyHomeModule({
    super.key,
    required this.journey,
    required this.onTargetRoute,
    /// Si true : uniquement la liste d’étapes (titre / CTA déjà dans le header Home).
    this.compact = false,
  });

  final ActivationJourney journey;
  final void Function(String targetRoute) onTargetRoute;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final profile = ProfileIdentityCoordinator.instance.cachedProfile;
    final primaryLabel = journey.primaryCtaLabel;
    final effectiveRoute = effectiveActivationPrimaryRoute(journey, profile);
    final l10n = AppLocalizations.of(context);

    final headline = journey.headline.trim().isNotEmpty
        ? journey.headline.trim()
        : (l10n?.activationJourneyHeadline ?? 'Finish setting up');
    final description = journey.heroSubtitle.trim().isNotEmpty
        ? journey.heroSubtitle.trim()
        : (l10n?.activationJourneySubtitle ??
            'The new era on investment in a few steps');

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(
              24,
              28,
              24,
              journey.stages.isEmpty ? 28 : 20,
            ),
            child: Column(
              children: [
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 400),
                  switchInCurve: Curves.easeOutCubic,
                  switchOutCurve: Curves.easeInCubic,
                  child: Padding(
                    key: ValueKey<String>(
                      '${compact ? 'c-' : 'f-'}'
                      '${effectiveRoute ?? ''}-'
                      '${primaryLabel ?? ''}-'
                      '${journey.weightedProgressPercent}',
                    ),
                    padding: EdgeInsets.zero,
                    child: compact
                        ? Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              ProgressRingPercent(
                                percent: journey.weightedProgressPercent,
                              ),
                              const SizedBox(height: 20),
                              Text(
                                headline,
                                textAlign: TextAlign.center,
                                style: GoogleFonts.inter(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.26,
                                  height: 28 / 22,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                description,
                                textAlign: TextAlign.center,
                                style: GoogleFonts.inter(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w400,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              if (journey.stages.isEmpty)
                                const SizedBox(height: 8),
                            ],
                          )
                        : Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              ProgressRingPercent(
                                percent: journey.weightedProgressPercent,
                              ),
                              const SizedBox(height: 20),
                              Text(
                                headline,
                                textAlign: TextAlign.center,
                                style: GoogleFonts.inter(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.26,
                                  height: 28 / 22,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                description,
                                textAlign: TextAlign.center,
                                style: GoogleFonts.inter(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w400,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              if (primaryLabel != null &&
                                  primaryLabel.isNotEmpty) ...[
                                const SizedBox(height: 16),
                                AppPrimaryButton(
                                  label: primaryLabel,
                                  onPressed: effectiveRoute != null &&
                                          effectiveRoute.isNotEmpty
                                      ? () => onTargetRoute(effectiveRoute)
                                      : null,
                                  shrinkWrap: true,
                                ),
                              ],
                            ],
                          ),
                  ),
                ),
              ],
            ),
          ),
          if (journey.stages.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.s4,
                0,
                AppSpacing.s4,
                16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (var i = 0; i < journey.stages.length; i++) ...[
                    if (i > 0) const SizedBox(height: AppSpacing.md),
                    _ActivationJourneyStepRow(
                      journey: journey,
                      stage: journey.stages[i],
                      profile: profile,
                      onTargetRoute: onTargetRoute,
                    ),
                  ],
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _ActivationJourneyStepRow extends StatelessWidget {
  const _ActivationJourneyStepRow({
    required this.journey,
    required this.stage,
    required this.profile,
    required this.onTargetRoute,
  });

  final ActivationJourney journey;
  final ActivationJourneyStage stage;
  final MobileAppProfile? profile;
  final void Function(String route) onTargetRoute;

  @override
  Widget build(BuildContext context) {
    final completed = isActivationStageCompleted(stage, profile);
    final tap = _activationRowTap(
      stage: stage,
      journey: journey,
      profile: profile,
      onTargetRoute: onTargetRoute,
    );

    final titleStyle = AppTypography.itemPrimary.copyWith(
      color: completed
          ? AppColors.textPrimary.withValues(alpha: 0.42)
          : AppColors.textPrimary,
    );
    final subtitleStyle = AppTypography.itemSupporting.copyWith(
      color: completed
          ? const Color(0xFF8E8E93).withValues(alpha: 0.45)
          : const Color(0xFF8E8E93),
    );

    final row = GestureDetector(
      onTap: tap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            SizedBox(
              width: 32,
              height: 32,
              child: Center(
                child: _LeadingForUxStatus(stage: stage, profile: profile),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    stage.title,
                    style: titleStyle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (stage.subtitle.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(
                      stage.subtitle,
                      style: subtitleStyle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
            if (tap != null) ...[
              const SizedBox(width: 8),
              const ChevronRight(size: 12, color: Color(0xFFC7C7CC)),
            ],
          ],
        ),
      ),
    );

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 340),
      switchInCurve: Curves.easeOutBack,
      switchOutCurve: Curves.easeIn,
      child: KeyedSubtree(
        key: ValueKey<String>(
          '${stage.key}-${stage.uxStatus.name}-'
          '${isActivationStageCompleted(stage, profile)}',
        ),
        child: row,
      ),
    );
  }
}

class _LeadingForUxStatus extends StatelessWidget {
  const _LeadingForUxStatus({
    required this.stage,
    required this.profile,
  });

  final ActivationJourneyStage stage;
  final MobileAppProfile? profile;

  IconData _semanticIcon() {
    switch (stage.key) {
      case 'account_verification':
        return Icons.verified_user_outlined;
      case 'first_deposit':
        return Icons.savings_outlined;
      case 'first_investment':
        return Icons.show_chart_rounded;
      default:
        return Icons.flag_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isActivationStageCompleted(stage, profile)) {
      return const DsSuccessIcon(size: _kActivationRowSuccessIconSize);
    }
    final s = stage.uxStatus;
    switch (s) {
      case ActivationStageUxStatus.completed:
        return const DsSuccessIcon(size: _kActivationRowSuccessIconSize);
      case ActivationStageUxStatus.inProgress:
      case ActivationStageUxStatus.available:
        return Icon(
          _semanticIcon(),
          size: 26,
          color: AppColors.indigo,
        );
      case ActivationStageUxStatus.locked:
        return Icon(
          _semanticIcon(),
          size: 26,
          color: AppColors.gray2,
        );
    }
  }
}
