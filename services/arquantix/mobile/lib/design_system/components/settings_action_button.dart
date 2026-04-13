import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Small action button with label + icon, used inside [SettingsListItem].
///
/// Figma specs:
/// - Text: 12px bold, indigo (#6155F5)
/// - Icon: 16×16, stroke indigo
/// - Gap: 4px between label and icon
enum SettingsActionType { copy, edit, info, help }

class SettingsActionButton extends StatelessWidget {
  const SettingsActionButton({
    super.key,
    required this.label,
    this.icon,
    this.actionType,
    this.onTap,
    this.color,
  });

  final String label;
  final IconData? icon;
  final SettingsActionType? actionType;
  final VoidCallback? onTap;
  final Color? color;

  IconData get _resolvedIcon {
    if (icon != null) return icon!;
    return switch (actionType) {
      SettingsActionType.copy => Icons.copy_rounded,
      SettingsActionType.edit => Icons.edit_rounded,
      SettingsActionType.info => Icons.info_outline_rounded,
      SettingsActionType.help => Icons.help_outline_rounded,
      null => Icons.arrow_forward_rounded,
    };
  }

  @override
  Widget build(BuildContext context) {
    final c = color ?? AppColors.indigo;

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: AppTypography.itemSupportingBd.copyWith(color: c),
          ),
          const SizedBox(width: 4),
          Icon(_resolvedIcon, size: 16, color: c),
        ],
      ),
    );
  }
}
