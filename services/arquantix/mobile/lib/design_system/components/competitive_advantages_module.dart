import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Catégorie sémantique pour une ligne (couleur de fond de la bulle).
/// - content: fond blanc (défaut)
/// - work: jaune (travail)
/// - note: bleu clair (notes informatives)
/// - success: vert clair (succès)
/// - danger: rouge clair (alerte / gravité)
enum CompetitiveAdvantageCategory {
  content,
  work,
  note,
  success,
  danger,
}

class CompetitiveAdvantagesRowData {
  const CompetitiveAdvantagesRowData({
    required this.icon,
    required this.iconBackgroundColor,
    required this.title,
    required this.description,
    this.category = CompetitiveAdvantageCategory.content,
  });

  final IconData icon;
  final Color iconBackgroundColor;
  final String title;
  final String description;
  final CompetitiveAdvantageCategory category;
}

/// Module blanc avec titre optionnel et lignes "avantages competitifs".
class CompetitiveAdvantagesModule extends StatelessWidget {
  const CompetitiveAdvantagesModule({
    super.key,
    this.title,
    required this.rows,
  });

  final String? title;
  final List<CompetitiveAdvantagesRowData> rows;

  static const double _horizontalPadding = 20;
  static const double _verticalPadding = 16;
  static const double _rowSpacing = AppSpacing.lg;
  static const double _iconSize = 24;

  static IconData iconFromKey(String key) {
    switch (key.trim().toLowerCase()) {
      case 'assignment_turned_in_rounded':
        return Icons.assignment_turned_in_rounded;
      case 'favorite_rounded':
        return Icons.favorite_rounded;
      case 'trending_up_rounded':
        return Icons.trending_up_rounded;
      case 'apartment_rounded':
        return Icons.apartment_rounded;
      case 'check_circle_rounded':
        return Icons.check_circle_rounded;
      case 'insights_rounded':
        return Icons.insights_rounded;
      default:
        return Icons.check_circle_rounded;
    }
  }

  static Color colorFromHex(String? raw, {Color fallback = const Color(0xFF1E88E5)}) {
    if (raw == null) return fallback;
    final value = raw.trim();
    if (value.isEmpty) return fallback;
    var hex = value.startsWith('#') ? value.substring(1) : value;
    if (hex.length == 6) hex = 'FF$hex';
    if (hex.length != 8) return fallback;
    final parsed = int.tryParse(hex, radix: 16);
    if (parsed == null) return fallback;
    return Color(parsed);
  }

  static CompetitiveAdvantageCategory categoryFromKey(String? raw) {
    return switch ((raw ?? '').trim().toLowerCase()) {
      'work' => CompetitiveAdvantageCategory.work,
      'note' => CompetitiveAdvantageCategory.note,
      'success' => CompetitiveAdvantageCategory.success,
      'danger' => CompetitiveAdvantageCategory.danger,
      _ => CompetitiveAdvantageCategory.content,
    };
  }

  static Color backgroundColorForCategory(CompetitiveAdvantageCategory cat) {
    return switch (cat) {
      CompetitiveAdvantageCategory.content => AppColors.cardBackground,
      CompetitiveAdvantageCategory.work => const Color(0xFFFEF9C3), // jaune clair
      CompetitiveAdvantageCategory.note => const Color(0xFFDBEAFE), // bleu clair
      CompetitiveAdvantageCategory.success => const Color(0xFFD1FAE5), // vert clair
      CompetitiveAdvantageCategory.danger => const Color(0xFFFEE2E2), // rouge clair
    };
  }

  static List<CompetitiveAdvantagesRowData> rowsFromJson(List<dynamic> rawRows) {
    final out = <CompetitiveAdvantagesRowData>[];
    for (final row in rawRows) {
      if (row is! Map) continue;
      final title = (row['title'] ?? '').toString().trim();
      final description = (row['description'] ?? '').toString().trim();
      if (title.isEmpty || description.isEmpty) continue;
      out.add(
        CompetitiveAdvantagesRowData(
          icon: iconFromKey((row['icon'] ?? '').toString()),
          iconBackgroundColor: colorFromHex(
            (row['iconBackgroundColor'] ?? '').toString(),
            fallback: const Color(0xFF1E88E5),
          ),
          title: title,
          description: description,
          category: categoryFromKey((row['category'] ?? '').toString()),
        ),
      );
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) {
      return const SizedBox.shrink();
    }
    final hasTitle = (title ?? '').trim().isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (hasTitle)
          Padding(
            padding: const EdgeInsets.only(left: 0, bottom: AppSpacing.sm),
            child: Text(
              title!.trim(),
              style: AppTypography.sectionTitle.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        Container(
          width: double.infinity,
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.06),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: _horizontalPadding,
              vertical: _verticalPadding,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                for (int i = 0; i < rows.length; i++) ...[
                  if (i > 0) const SizedBox(height: _rowSpacing),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: _iconSize + AppSpacing.sm,
                        height: _iconSize + AppSpacing.sm,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: rows[i].iconBackgroundColor,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Icon(
                          rows[i].icon,
                          size: _iconSize,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              rows[i].title,
                              style: AppTypography.titleSmall.copyWith(
                                color: AppColors.textPrimary,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.xs),
                            Text(
                              rows[i].description,
                              style: AppTypography.bodyMedium.copyWith(
                                color: AppColors.textPrimary,
                                height: 1.4,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }
}
