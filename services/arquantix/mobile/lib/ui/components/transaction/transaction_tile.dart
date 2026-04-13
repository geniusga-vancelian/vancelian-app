import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_typography.dart';
import 'transaction_avatar.dart';

/// Revolut-style list / transaction row: leading avatar, title/subtitle, optional right text and chevron.
///
/// Variants:
/// - Account category tile: [showChevron] true, no right text (link row).
/// - Asset / transaction tile: [rightPrimary] and optional [rightSecondary] (e.g. amount + delta).
///
/// Layout: min height 64px (48px in dense), 16px horizontal padding; leading avatar, expanded center text,
/// optional right-aligned primary/secondary, optional trailing chevron. All text single-line with ellipsis.
///
/// USAGE EXAMPLES (see comments below):
///
/// 1) Category row (Cash / Savings / Invest / Crypto):
/// ```dart
/// TransactionTile(
///   avatar: TransactionAvatar(icon: Icons.savings, backgroundColor: Colors.orange),
///   title: 'Savings',
///   subtitle: 'Earn interest',
///   showChevron: true,
///   onTap: () {},
/// )
/// ```
///
/// 2) Asset row (Bitcoin / Ether style):
/// ```dart
/// TransactionTile(
///   avatar: TransactionAvatar(icon: Icons.currency_bitcoin, backgroundColor: Colors.orange),
///   title: 'Bitcoin',
///   subtitle: '1.21244566 BTC',
///   rightPrimary: '£9,440.64',
///   rightSecondary: '▲ 1.86%',
///   rightSecondaryColor: AppColors.positive,
///   onTap: () {},
/// )
/// ```
///
/// 3) Simple transaction row with only rightPrimary:
/// ```dart
/// TransactionTile(
///   avatar: TransactionAvatar(icon: Icons.shopping_bag, backgroundColor: Colors.blue),
///   title: 'Amazon',
///   subtitle: 'Yesterday',
///   rightPrimary: '-£42.10',
/// )
/// ```
class TransactionTile extends StatefulWidget {
  const TransactionTile({
    super.key,
    required this.avatar,
    required this.title,
    this.subtitle,
    this.rightPrimary,
    this.rightSecondary,
    this.rightSecondaryColor,
    this.showChevron = false,
    this.onTap,
    this.dense = false,
    this.isEnabled = true,
    this.semanticLabel,
    this.titleMaxLines = 1,
    this.subtitleMaxLines = 1,
    this.alignTop = false,
  });

  /// Leading widget (use [TransactionAvatar] for standard icon disk).
  final Widget avatar;

  /// Main title (ellipsis au-delà de [titleMaxLines] lignes).
  final String title;

  /// Optional subtitle below title (ellipsis au-delà de [subtitleMaxLines] lignes).
  final String? subtitle;

  /// Nombre max de lignes pour le titre (défaut 1).
  final int titleMaxLines;
  /// Nombre max de lignes pour le sous-titre (défaut 1).
  final int subtitleMaxLines;

  /// Optional right-side primary text (e.g. amount). Right-aligned, single line.
  final String? rightPrimary;

  /// Optional right-side secondary text (e.g. %, date, status). Right-aligned, single line.
  final String? rightSecondary;

  /// Color for [rightSecondary] (e.g. [AppColors.positive] / [AppColors.negative]). Defaults to [AppColors.textSecondary].
  final Color? rightSecondaryColor;

  /// Show trailing chevron (e.g. for category / link rows).
  final bool showChevron;

  /// Tap callback. When non-null and [isEnabled], légère réduction d’échelle au toucher puis invoque.
  final VoidCallback? onTap;

  /// Smaller vertical padding and typical use with 40px leading (e.g. [TransactionAvatar.sizeDense]).
  final bool dense;

  /// When false, reduces opacity and [onTap] is not called.
  final bool isEnabled;

  /// Override for semantics. Defaults to "$title, $subtitle, $rightPrimary".
  final String? semanticLabel;

  /// Aligne verticalement le contenu en haut (utile pour cartes avec texte multi-lignes).
  final bool alignTop;

  static const double _horizontalPadding = 16;
  static const double _verticalPaddingDefault = 10;
  static const double _verticalPaddingDense = 8;
  static const double _minHeightDefault = 64;
  static const double _minHeightDense = 56;
  static const double _gapLeadingCenter = 12;
  static const double _gapRightChevron = 8;

  @override
  State<TransactionTile> createState() => _TransactionTileState();
}

class _TransactionTileState extends State<TransactionTile> {
  @override
  Widget build(BuildContext context) {
    final verticalPadding = widget.dense ? TransactionTile._verticalPaddingDense : TransactionTile._verticalPaddingDefault;
    final minHeight = widget.dense ? TransactionTile._minHeightDense : TransactionTile._minHeightDefault;
    final content = Row(
      crossAxisAlignment: widget.alignTop ? CrossAxisAlignment.start : CrossAxisAlignment.center,
      children: [
        widget.avatar,
        const SizedBox(width: TransactionTile._gapLeadingCenter),
        Expanded(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: widget.alignTop ? MainAxisAlignment.start : MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.title,
                style: AppTypography.tileTitle.copyWith(color: AppColors.textPrimary),
                maxLines: widget.titleMaxLines,
                overflow: TextOverflow.ellipsis,
              ),
              if (widget.subtitle != null && widget.subtitle!.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text(
                  widget.subtitle!,
                  style: AppTypography.tileSubtitle.copyWith(color: AppColors.textSecondary),
                  maxLines: widget.subtitleMaxLines,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
        if (widget.rightPrimary != null || widget.rightSecondary != null) ...[
          const SizedBox(width: 8),
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisAlignment: widget.alignTop ? MainAxisAlignment.start : MainAxisAlignment.center,
            children: [
              if (widget.rightPrimary != null && widget.rightPrimary!.isNotEmpty)
                Text(
                  widget.rightPrimary!,
                  style: AppTypography.tileRightPrimary.copyWith(color: AppColors.textPrimary),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              if (widget.rightSecondary != null && widget.rightSecondary!.isNotEmpty) ...[
                if (widget.rightPrimary != null && widget.rightPrimary!.isNotEmpty) const SizedBox(height: 2),
                Text(
                  widget.rightSecondary!,
                  style: AppTypography.tileRightSecondary.copyWith(
                    color: widget.rightSecondaryColor ?? AppColors.textSecondary,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ],
        if (widget.showChevron) ...[
          const SizedBox(width: TransactionTile._gapRightChevron),
          Icon(
            Icons.chevron_right,
            color: AppColors.chevronGrey,
            size: 24,
          ),
        ],
      ],
    );

    final constrained = ConstrainedBox(
      constraints: BoxConstraints(minHeight: minHeight),
      child: Padding(
        padding: EdgeInsets.symmetric(
          horizontal: TransactionTile._horizontalPadding,
          vertical: verticalPadding,
        ),
        child: content,
      ),
    );

    final semantic = widget.semanticLabel ?? _defaultSemanticLabel();
    final semanticChild = Semantics(
      label: semantic,
      button: widget.onTap != null && widget.isEnabled,
      hint: widget.onTap != null && widget.isEnabled ? 'Appuyer pour ouvrir' : null,
      enabled: widget.isEnabled,
      child: constrained,
    );

    if (widget.onTap != null && widget.isEnabled) {
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: widget.onTap,
          child: SizedBox(
            width: double.infinity,
            child: semanticChild,
          ),
        ),
      );
    }

    if (!widget.isEnabled) {
      return Opacity(
        opacity: 0.5,
        child: semanticChild,
      );
    }

    return semanticChild;
  }

  String _defaultSemanticLabel() {
    final parts = <String>[widget.title];
    if (widget.subtitle != null && widget.subtitle!.isNotEmpty) parts.add(widget.subtitle!);
    if (widget.rightPrimary != null && widget.rightPrimary!.isNotEmpty) parts.add(widget.rightPrimary!);
    return parts.join(', ');
  }
}
