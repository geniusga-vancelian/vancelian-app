import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';

/// List item for bottom-sheet selection lists.
///
/// Figma spec (zip extract 7):
///   - Padding: 16px
///   - Gap icon↔text: 12px
///   - Title: Inter SemiBold 15px, tracking -0.23, black
///   - Subtitle: Inter Regular 13px, tracking -0.08, #8E8E93
///   - Selected: bg #EFEEFE, radius 16px, border 2px white
///   - Trailing: chevron-right 16×16, #C7C7CC
class AppSheetListItem extends StatelessWidget {
  const AppSheetListItem({
    super.key,
    required this.title,
    this.subtitle,
    this.leading,
    this.trailing,
    this.selected = false,
    this.showChevron = true,
    this.onTap,
  });

  final String title;
  final String? subtitle;
  final Widget? leading;
  final Widget? trailing;
  final bool selected;
  final bool showChevron;
  final VoidCallback? onTap;

  static const _selectedBg = Color(0xFFEFEEFE);
  static const _chevronColor = Color(0xFFC7C7CC);

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final titleStyle = textTheme.titleSmall?.copyWith(
          fontSize: 15,
          fontWeight: FontWeight.w600,
          height: 20 / 15,
          letterSpacing: -0.23,
          color: Colors.black,
        ) ??
        const TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w600,
          height: 20 / 15,
          letterSpacing: -0.23,
          color: Colors.black,
        );
    final subtitleStyle = textTheme.bodySmall?.copyWith(
          fontSize: 13,
          fontWeight: FontWeight.w400,
          height: 16 / 13,
          letterSpacing: -0.08,
          color: AppColors.gray,
        ) ??
        const TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w400,
          height: 16 / 13,
          letterSpacing: -0.08,
          color: AppColors.gray,
        );

    return AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      curve: Curves.easeInOut,
      decoration: BoxDecoration(
        color: selected ? _selectedBg : Colors.transparent,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(
          color: selected ? Colors.white : Colors.transparent,
          width: 2,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          splashColor: _selectedBg,
          highlightColor: _selectedBg.withValues(alpha: 0.5),
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Row(
              children: [
                if (leading != null) ...[
                  leading!,
                  const SizedBox(width: AppSpacing.md),
                ],
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        title,
                        style: titleStyle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (subtitle != null && subtitle!.isNotEmpty)
                        Text(
                          subtitle!,
                          style: subtitleStyle,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                ),
                if (trailing != null) ...[
                  const SizedBox(width: AppSpacing.sm),
                  trailing!,
                ],
                if (showChevron) ...[
                  const SizedBox(width: AppSpacing.sm),
                  const Icon(
                    Icons.chevron_right_rounded,
                    size: 16,
                    color: _chevronColor,
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
