import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'kalai_icon.dart';

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

  String get _resolvedKalaiAsset {
    return switch (actionType) {
      SettingsActionType.copy => KalaiIcons.clipboard,
      SettingsActionType.edit => KalaiIcons.edit,
      SettingsActionType.info => KalaiIcons.info,
      SettingsActionType.help => KalaiIcons.help,
      null => KalaiIcons.arrowRight,
    };
  }

  @override
  Widget build(BuildContext context) {
    final c = color ?? AppColors.indigo;
    final iconWidget = icon != null
        ? Icon(icon, size: 16, color: c)
        : KalaiIcon(_resolvedKalaiAsset, size: 16, color: c);

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
          iconWidget,
        ],
      ),
    );
  }
}
