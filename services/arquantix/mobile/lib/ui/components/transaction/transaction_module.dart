import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';

/// Module à fond blanc qui regroupe des lignes de type [TransactionTile].
/// Pas slidable ; padding et margin configurables pour intégration dans la page.
///
/// Exemple :
/// ```dart
/// TransactionModule(
///   children: [
///     TransactionTile(avatar: ..., title: 'Savings', ...),
///     TransactionTile(avatar: ..., title: 'Bitcoin', ...),
///   ],
/// )
/// ```
class TransactionModule extends StatelessWidget {
  const TransactionModule({
    super.key,
    required this.children,
    this.margin,
    this.padding,
    this.borderRadius,
  });

  /// Lignes à afficher (en général des [TransactionTile]).
  final List<Widget> children;

  /// Marge extérieure du module (espace avec le reste de la page).
  final EdgeInsetsGeometry? margin;

  /// Padding intérieur du module (entre le fond blanc et les enfants).
  final EdgeInsetsGeometry? padding;

  /// Rayon des coins du module (double). Par défaut [defaultBorderRadius].
  final double? borderRadius;

  static const EdgeInsets _defaultMargin = EdgeInsets.symmetric(
    horizontal: 16,
    vertical: 12,
  );
  static const EdgeInsets _defaultPadding = EdgeInsets.symmetric(
    horizontal: 0,
    vertical: 8,
  );
  static const double defaultBorderRadius = 12;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin ?? _defaultMargin,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(borderRadius ?? defaultBorderRadius),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius ?? defaultBorderRadius),
        child: Padding(
          padding: padding ?? _defaultPadding,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: children,
          ),
        ),
      ),
    );
  }
}
