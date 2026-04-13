import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'list_card.dart';

/// Highly configurable list-item row for settings / profile screens.
///
/// Covers all Figma variants:
///   - Avatar + title + subtitle + value + chevron
///   - Icon + title + subtitle + value + chevron
///   - Title + description (long text, multi-line)
///   - Title + toggle
///   - Title + action button (Copy/Edit)
///   - Title + value + value-subtext
///   - Compact title (13px) + add/remove icon
///   - Description + link
class SettingsListItem extends StatelessWidget {
  const SettingsListItem({
    super.key,
    required this.title,
    this.subtitle,
    this.description,
    this.leading,
    this.value,
    this.valueSubtext,
    this.valueSubtextColor,
    this.trailing,
    this.showChevron = false,
    this.compact = false,
    this.onTap,
    this.titleMaxLines = 1,
    this.subtitleMaxLines = 1,
    this.descriptionMaxLines = 10,
    this.crossAxisAlignment = CrossAxisAlignment.center,
  });

  final String title;
  final String? subtitle;
  final String? description;
  final Widget? leading;
  final String? value;
  final String? valueSubtext;
  final Color? valueSubtextColor;
  final Widget? trailing;
  final bool showChevron;
  final bool compact;
  final VoidCallback? onTap;
  final int titleMaxLines;
  final int subtitleMaxLines;
  final int descriptionMaxLines;
  final CrossAxisAlignment crossAxisAlignment;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Row(
        crossAxisAlignment: _effectiveAlignment,
        children: [
          if (leading != null) ...[
            leading!,
            SizedBox(width: leading is IconContainer ? 12 : 12),
          ],
          Expanded(child: _buildContent()),
          if (value != null || valueSubtext != null) ...[
            const SizedBox(width: 8),
            _buildValueColumn(),
          ],
          if (trailing != null) ...[
            SizedBox(width: value != null ? 8 : 8),
            trailing!,
          ],
          if (showChevron) ...[
            const SizedBox(width: 8),
            const ChevronRight(size: 12, color: Color(0xFFC7C7CC)),
          ],
        ],
      ),
    );
  }

  CrossAxisAlignment get _effectiveAlignment {
    if (description != null &&
        description!.length > 40 &&
        crossAxisAlignment == CrossAxisAlignment.center) {
      return CrossAxisAlignment.start;
    }
    return crossAxisAlignment;
  }

  Widget _buildContent() {
    final titleStyle = compact
        ? AppTypography.bodySmEmphasized
        : AppTypography.itemPrimary;
    final subtitleStyle =
        AppTypography.itemSupporting.copyWith(color: const Color(0xFF8E8E93));
    final descStyle =
        AppTypography.itemSupporting.copyWith(color: const Color(0xFF8E8E93));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          title,
          style: titleStyle,
          maxLines: titleMaxLines,
          overflow: TextOverflow.ellipsis,
        ),
        if (subtitle != null)
          Text(
            subtitle!,
            style: subtitleStyle,
            maxLines: subtitleMaxLines,
            overflow: TextOverflow.ellipsis,
          ),
        if (description != null)
          Text(
            description!,
            style: descStyle,
            maxLines: descriptionMaxLines,
          ),
      ],
    );
  }

  Widget _buildValueColumn() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (value != null)
          Text(
            value!,
            style: AppTypography.itemSecondary,
          ),
        if (valueSubtext != null)
          Text(
            valueSubtext!,
            style: AppTypography.itemSupporting
                .copyWith(color: valueSubtextColor ?? const Color(0xFF8E8E93)),
          ),
      ],
    );
  }
}
