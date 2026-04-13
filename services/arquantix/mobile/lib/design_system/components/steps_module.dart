import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_section_title.dart';
import 'content_card_compact.dart';
import 'step_item.dart';

/// Largeur de la colonne timeline (bloc date 3 lignes + ligne verticale).
const double _timelineColumnWidth = 44;

/// Espacement vertical entre deux étapes (sous la card).
const double _stepBottomPadding = 18;

/// Largeur de la ligne verticale du chemin.
const double _timelineLineWidth = 2;

/// Module "Steps" (Itinerary / Étapes) : liste verticale d’étapes avec timeline à gauche et cartes plates à droite.
class StepsModuleWidget extends StatelessWidget {
  const StepsModuleWidget({
    required this.title,
    required this.steps,
    super.key,
    this.subtitle,
    this.rightLabel,
    this.onStepTap,
    this.horizontalMargin,
  });

  /// Titre du module (ex. "Itinerary").
  final String title;

  /// Sous-titre ou résumé optionnel sous le titre.
  final String? subtitle;

  /// Info à droite du header (ex. "5 Places").
  final String? rightLabel;

  /// Liste des étapes.
  final List<StepItem> steps;

  /// Callback au tap sur une card (index 0-based).
  final void Function(int index)? onStepTap;

  /// Marge horizontale (null = utiliser la constante du dashboard).
  final double? horizontalMargin;

  static const double _defaultHorizontalMargin = 16;

  /// Crée un [StepsModuleWidget] à partir d’un JSON (chargement dynamique de modules).
  /// Structure attendue : { "type": "steps", "title": "...", "rightLabel"?:"...", "items": [...] }
  static StepsModuleWidget? fromJson(dynamic json, {void Function(int index)? onStepTap}) {
    if (json is! Map<String, dynamic>) return null;
    if (json['type'] != 'steps') return null;
    final title = json['title'] as String?;
    if (title == null || title.isEmpty) return null;
    final items = StepItem.listFromJson(json['items']);
    return StepsModuleWidget(
      title: title,
      steps: items,
      rightLabel: json['rightLabel'] as String?,
      subtitle: json['subtitle'] as String?,
      onStepTap: onStepTap,
    );
  }

  @override
  Widget build(BuildContext context) {
    final margin = horizontalMargin ?? _defaultHorizontalMargin;
    if (steps.isEmpty) {
      return Padding(
        padding: EdgeInsets.symmetric(horizontal: margin),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildHeader(context),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'No steps yet',
              style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
      );
    }

    final stepRows = steps.asMap().entries.map((entry) {
      final index = entry.key;
      final step = entry.value;
      final resolvedIndex = step.index ?? (index + 1);
      final isLast = index == steps.length - 1;
      return _StepRow(
        step: step.withIndex(resolvedIndex),
        isLast: isLast,
        onTap: onStepTap != null ? () => onStepTap!(index) : null,
      );
    }).toList();

    return Padding(
      padding: EdgeInsets.symmetric(horizontal: margin),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildHeader(context),
          const SizedBox(height: AppSpacing.lg),
          Stack(
            children: [
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                width: _timelineColumnWidth,
                child: Center(
                  child: Container(
                    width: _timelineLineWidth,
                    color: AppColors.border,
                    height: double.infinity,
                  ),
                ),
              ),
              Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: stepRows,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              AppSectionTitle(title),
              if (subtitle != null && subtitle!.trim().isNotEmpty) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  subtitle!,
                  style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
        if (rightLabel != null && rightLabel!.trim().isNotEmpty) ...[
          const SizedBox(width: AppSpacing.md),
          Text(
            rightLabel!,
            style: AppTypography.meta,
          ),
        ],
      ],
    );
  }
}

/// Parse une date type "15 mars 2025" en (jour, mois abrégé, année). Retourne null si format invalide.
({String day, String month, String year})? _parseDateToDayMonthYear(String? dateStr) {
  if (dateStr == null || dateStr.trim().isEmpty) return null;
  final parts = dateStr.trim().split(RegExp(r'\s+'));
  if (parts.length < 3) return null;
  final day = parts[0];
  final monthRaw = parts[1];
  final year = parts[2];
  if (day.isEmpty || monthRaw.isEmpty || year.isEmpty) return null;
  final monthAbbr = monthRaw.length >= 3
      ? '${monthRaw[0].toUpperCase()}${monthRaw.substring(1, 3).toLowerCase()}'
      : monthRaw;
  return (day: day, month: monthAbbr, year: year);
}

/// Une ligne : timeline (bloc date 3 lignes + ligne) + card compacte.
class _StepRow extends StatelessWidget {
  const _StepRow({
    required this.step,
    required this.isLast,
    this.onTap,
  });

  final StepItem step;
  final bool isLast;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
          SizedBox(
            width: _timelineColumnWidth,
            child: Center(child: _StepDateBlock(step: step)),
          ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(left: 6),
                  child: ContentCardCompact(
                    dateLabel: null,
                    title: step.title,
                    description: step.description,
                    tags: step.tags,
                    imageUrl: step.imageUrl,
                    alwaysShowImageArea: true,
                    onTap: onTap,
                  ),
                ),
              ),
            ],
          ),
        ),
        if (!isLast) const SizedBox(height: _stepBottomPadding),
      ],
    );
  }
}

/// Bloc date 3 lignes : Jour (agrandi + gras), Mois (plus grand, majuscules), Année (comme le jour).
/// Centré horizontalement sur la ligne et verticalement avec la carte.
class _StepDateBlock extends StatelessWidget {
  const _StepDateBlock({required this.step});

  final StepItem step;

  static const double _lineHeight = 1.2;

  @override
  Widget build(BuildContext context) {
    final parsed = _parseDateToDayMonthYear(step.date);
    final day = parsed?.day ?? step.dayLabel ?? '-';
    final month = (parsed?.month ?? '-').toUpperCase();
    final year = parsed?.year ?? '-';

    final dayStyle = AppTypography.titleSmall.copyWith(
      color: AppColors.textSecondary,
      height: _lineHeight,
      fontWeight: FontWeight.w700,
    );
    final monthStyle = AppTypography.titleSmall.copyWith(
      color: AppColors.textSecondary,
      height: _lineHeight,
      fontWeight: FontWeight.w600,
    );
    final yearStyle = AppTypography.bodySmall.copyWith(
      color: AppColors.textSecondary,
      height: _lineHeight,
    );

    return Column(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(day, style: dayStyle, maxLines: 1, overflow: TextOverflow.ellipsis),
        Text(month, style: monthStyle, maxLines: 1, overflow: TextOverflow.ellipsis),
        Text(year, style: yearStyle, maxLines: 1, overflow: TextOverflow.ellipsis),
      ],
    );
  }
}

