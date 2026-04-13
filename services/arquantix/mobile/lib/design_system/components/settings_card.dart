import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// White card container that groups [SettingsListItem] rows.
///
/// Figma specs:
/// - White bg, borderRadius 16
/// - Padding 16
/// - Gap between children: 24 (default)
/// - Shadow: 0 0 20 -10 rgba(0,0,0,0.12)
class SettingsCard extends StatelessWidget {
  const SettingsCard({
    super.key,
    required this.children,
    this.gap = 24,
    this.padding = const EdgeInsets.all(AppSpacing.s4),
    this.showShadow = true,
    this.showDividers = false,
    this.sectionTitle,
    this.footer,
    this.backgroundColor,
  });

  final List<Widget> children;
  final double gap;
  final EdgeInsets padding;
  final bool showShadow;
  final bool showDividers;
  final String? sectionTitle;
  final Widget? footer;
  final Color? backgroundColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: backgroundColor ?? AppColors.cardBackground,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: showShadow ? AppShadow.defaultShadowList : null,
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: padding,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (sectionTitle != null) ...[
                  SizedBox(
                    height: 32,
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        sectionTitle!,
                        style: AppTypography.sectionTitle,
                      ),
                    ),
                  ),
                  SizedBox(height: gap > 8 ? 8 : gap),
                ],
                ..._buildItems(),
              ],
            ),
          ),
          if (footer != null) footer!,
        ],
      ),
    );
  }

  List<Widget> _buildItems() {
    final items = <Widget>[];
    for (var i = 0; i < children.length; i++) {
      items.add(children[i]);
      if (i < children.length - 1) {
        if (showDividers) {
          items.add(Padding(
            padding: EdgeInsets.symmetric(vertical: gap / 2),
            child: const Divider(
              height: 1,
              color: Color(0xFFE5E5EA),
            ),
          ));
        } else {
          items.add(SizedBox(height: gap));
        }
      }
    }
    return items;
  }
}
