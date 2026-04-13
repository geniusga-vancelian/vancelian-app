import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

// ─────────────────────────────────────────────────────────────────────────────
// TransactionBadgeStatus
// ─────────────────────────────────────────────────────────────────────────────

enum TransactionBadgeStatus { pending, completed, cancelled }

// ─────────────────────────────────────────────────────────────────────────────
// TransactionStatusBadge
// ─────────────────────────────────────────────────────────────────────────────

/// Petit badge circulaire superposé sur l'avatar pour indiquer le statut.
class TransactionStatusBadge extends StatelessWidget {
  const TransactionStatusBadge({super.key, required this.status});

  final TransactionBadgeStatus status;

  static const double _size = 20;
  static const double _borderWidth = 2;
  static const double _iconSize = 12;

  @override
  Widget build(BuildContext context) {
    final Color bgColor;
    final IconData iconData;

    switch (status) {
      case TransactionBadgeStatus.completed:
        bgColor = const Color(0xFF0088FF);
        iconData = Icons.check;
      case TransactionBadgeStatus.pending:
        bgColor = const Color(0xFFAEAEB2);
        iconData = Icons.access_time;
      case TransactionBadgeStatus.cancelled:
        bgColor = const Color(0xFFDC2626);
        iconData = Icons.close;
    }

    return Container(
      width: _size,
      height: _size,
      decoration: BoxDecoration(
        color: bgColor,
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.white, width: _borderWidth),
      ),
      child: Center(
        child: Icon(iconData, size: _iconSize, color: AppColors.white),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// TransactionListItemData
// ─────────────────────────────────────────────────────────────────────────────

/// Données pour un item de [TransactionListCard].
///
/// Deux modes pour le leading :
///   1. Avatar par défaut (36×36 **cercle**, aligné [CryptoAvatar] medium) via [icon]/[initial]/[imageUrl].
///   2. Widget custom via [leadingWidget] (ex. deux CryptoAvatar superposés).
class TransactionListItemData {
  const TransactionListItemData({
    this.icon,
    this.initial,
    this.imageUrl,
    this.iconColor = const Color(0xFF8E8E93),
    this.avatarBackgroundColor = const Color(0xFFE5E5EA),
    this.badgeStatus,
    this.leadingWidget,
    required this.title,
    required this.subtitle,
    required this.amount,
    this.amountPrefix,
    this.amountColor,
    this.secondaryAmount,
    this.secondaryAmountColor,
    this.showChevron = false,
    this.subtitleIcon,
    this.trailingWidget,
    this.onTap,
  }) : assert(
            leadingWidget != null ||
                icon != null ||
                initial != null ||
                imageUrl != null,
            'Provide leadingWidget, icon, initial, or imageUrl');

  /// Custom leading widget (replaces the default avatar).
  final Widget? leadingWidget;

  final IconData? icon;
  final String? initial;
  final String? imageUrl;
  final Color iconColor;
  final Color avatarBackgroundColor;
  final TransactionBadgeStatus? badgeStatus;
  final String title;
  final String subtitle;
  final IconData? subtitleIcon;
  final String amount;
  final String? amountPrefix;
  final Color? amountColor;
  final String? secondaryAmount;
  final Color? secondaryAmountColor;
  final bool showChevron;
  final Widget? trailingWidget;
  final VoidCallback? onTap;
}

// ─────────────────────────────────────────────────────────────────────────────
// TransactionListCard
// ─────────────────────────────────────────────────────────────────────────────

/// Carte blanche regroupant une liste de transactions (Figma spec).
///
/// Layout logic:
///   - Outer container: 8px padding (gap between card edge and pressed bg).
///   - Each row: 8px inner padding (content inset within pressed highlight).
///   - Effective card-edge to content: 8 + 8 = 16px.
///   - Items separated only by their own vertical padding (no extra gap).
///   - Pressed state: accentLight background, 16px radius, no border.
class TransactionListCard extends StatelessWidget {
  const TransactionListCard({
    super.key,
    required this.items,
    this.showShadow = true,
    this.embedded = false,
    this.itemSpacing,
  });

  final List<TransactionListItemData> items;
  final bool showShadow;
  final double? itemSpacing;

  /// When true, renders only the list of items without the outer container.
  final bool embedded;

  static const double _outerPadding = 2;
  static const double _itemPadH = 14;
  static const double _itemPadV = 14;
  static const double _borderRadius = 16;
  static const double _avatarSize = 36;
  /// Cercle complet (DS) — était r10 (carré arrondi).
  static const double _avatarRadius = _avatarSize / 2;
  static const double _avatarIconSize = 20;

  static const Color _pressedColor = AppColors.accentLight;
  static const double _pressedRadius = 16;

  static TextStyle get _titleStyle =>
      AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary);

  static const TextStyle _subtitleStyle = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    letterSpacing: -0.08,
    height: 16 / 13,
    color: AppColors.textMuted,
  );

  static const TextStyle _amountStyle = TextStyle(
    fontSize: 15,
    fontWeight: FontWeight.w400,
    letterSpacing: -0.23,
    height: 20 / 15,
    color: AppColors.textPrimary,
  );

  static const TextStyle _secondaryAmountStyle = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    letterSpacing: -0.08,
    height: 16 / 13,
  );

  @override
  Widget build(BuildContext context) {
    final gap = itemSpacing ?? 0.0;

    final content = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int i = 0; i < items.length; i++) ...[
          _TransactionListItem(
            data: items[i],
            titleStyle: _titleStyle,
            subtitleStyle: _subtitleStyle,
            amountStyle: _amountStyle,
            secondaryAmountStyle: _secondaryAmountStyle,
            avatarSize: _avatarSize,
            avatarRadius: _avatarRadius,
            avatarIconSize: _avatarIconSize,
          ),
          if (i < items.length - 1 && gap > 0) SizedBox(height: gap),
        ],
      ],
    );

    if (embedded) return content;

    return Container(
      padding: const EdgeInsets.all(_outerPadding),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(_borderRadius),
        boxShadow: showShadow ? AppShadow.defaultShadowList : null,
      ),
      child: content,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// _TransactionListItem — single row with pressed state
// ─────────────────────────────────────────────────────────────────────────────

class _TransactionListItem extends StatefulWidget {
  const _TransactionListItem({
    required this.data,
    required this.titleStyle,
    required this.subtitleStyle,
    required this.amountStyle,
    required this.secondaryAmountStyle,
    required this.avatarSize,
    required this.avatarRadius,
    required this.avatarIconSize,
  });

  final TransactionListItemData data;
  final TextStyle titleStyle;
  final TextStyle subtitleStyle;
  final TextStyle amountStyle;
  final TextStyle secondaryAmountStyle;
  final double avatarSize;
  final double avatarRadius;
  final double avatarIconSize;

  @override
  State<_TransactionListItem> createState() => _TransactionListItemState();
}

class _TransactionListItemState extends State<_TransactionListItem> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final item = widget.data;
    final hasTap = item.onTap != null;

    final row = DecoratedBox(
      decoration: BoxDecoration(
        color: _isPressed
            ? TransactionListCard._pressedColor
            : Colors.transparent,
        borderRadius:
            BorderRadius.circular(TransactionListCard._pressedRadius),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: TransactionListCard._itemPadH,
          vertical: TransactionListCard._itemPadV,
        ),
        child: Row(
          children: [
            _buildLeading(item),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    item.title,
                    style: widget.titleStyle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  _buildSubtitle(item),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${item.amountPrefix ?? ''}${item.amount}',
                  style: item.amountColor != null
                      ? widget.amountStyle.copyWith(color: item.amountColor)
                      : widget.amountStyle,
                ),
                if (item.secondaryAmount != null)
                  Text(
                    item.secondaryAmount!,
                    style: widget.secondaryAmountStyle.copyWith(
                      color:
                          item.secondaryAmountColor ?? AppColors.textMuted,
                    ),
                  ),
              ],
            ),
            if (item.trailingWidget != null) ...[
              const SizedBox(width: 8),
              item.trailingWidget!,
            ] else if (item.showChevron) ...[
              const SizedBox(width: 8),
              const Icon(
                Icons.chevron_right_rounded,
                size: 20,
                color: AppColors.textMuted,
              ),
            ],
          ],
        ),
      ),
    );

    if (!hasTap) return row;

    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) {
        setState(() => _isPressed = false);
        item.onTap?.call();
      },
      onTapCancel: () => setState(() => _isPressed = false),
      behavior: HitTestBehavior.opaque,
      child: row,
    );
  }

  Widget _buildLeading(TransactionListItemData item) {
    if (item.leadingWidget != null) return item.leadingWidget!;
    return _buildAvatar(item);
  }

  Widget _buildSubtitle(TransactionListItemData item) {
    if (item.subtitleIcon != null) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(item.subtitleIcon, size: 14, color: AppColors.textMuted),
          const SizedBox(width: 4),
          Flexible(
            child: Text(
              item.subtitle,
              style: widget.subtitleStyle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      );
    }
    return Text(
      item.subtitle,
      style: widget.subtitleStyle,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
    );
  }

  Widget _buildAvatar(TransactionListItemData item) {
    Widget avatarContent;

    if (item.imageUrl != null && item.imageUrl!.isNotEmpty) {
      avatarContent = Container(
        width: widget.avatarSize,
        height: widget.avatarSize,
        decoration: BoxDecoration(
          color: item.avatarBackgroundColor,
          shape: BoxShape.circle,
        ),
        child: ClipOval(
          child: Image.network(
            item.imageUrl!,
            width: widget.avatarSize,
            height: widget.avatarSize,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Center(
              child: _buildIconOrInitial(item),
            ),
          ),
        ),
      );
    } else {
      avatarContent = Container(
        width: widget.avatarSize,
        height: widget.avatarSize,
        decoration: BoxDecoration(
          color: item.avatarBackgroundColor,
          shape: BoxShape.circle,
        ),
        child: Center(child: _buildIconOrInitial(item)),
      );
    }

    if (item.badgeStatus == null) return avatarContent;

    return SizedBox(
      width: widget.avatarSize,
      height: widget.avatarSize,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          avatarContent,
          Positioned(
            right: -6,
            bottom: -4,
            child: TransactionStatusBadge(status: item.badgeStatus!),
          ),
        ],
      ),
    );
  }

  Widget _buildIconOrInitial(TransactionListItemData item) {
    if (item.icon != null) {
      return Icon(item.icon, size: widget.avatarIconSize, color: item.iconColor);
    }
    return Text(
      (item.initial ?? '?').characters.first.toUpperCase(),
      style: TextStyle(
        fontSize: 15,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.23,
        height: 20 / 15,
        color: item.iconColor,
      ),
    );
  }
}
