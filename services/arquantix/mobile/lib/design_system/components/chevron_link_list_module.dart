import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'kalai_icon.dart';

class ChevronLinkListItem {
  const ChevronLinkListItem({
    required this.title,
    required this.onTap,
    this.leadingIcon,
    this.leadingBackgroundColor,
    this.leadingIconColor,
  });

  final String title;
  final VoidCallback onTap;
  final IconData? leadingIcon;
  final Color? leadingBackgroundColor;
  final Color? leadingIconColor;
}

/// Module blanc DS avec liste de liens cliquables et caret de redirection.
/// Icône de gauche optionnelle par ligne.
class ChevronLinkListModule extends StatelessWidget {
  const ChevronLinkListModule({
    super.key,
    required this.items,
  });

  final List<ChevronLinkListItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          for (int i = 0; i < items.length; i++) ...[
            Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: items[i].onTap,
                borderRadius: BorderRadius.circular(14),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.lg,
                    vertical: AppSpacing.md,
                  ),
                  child: Row(
                    children: [
                      if (items[i].leadingIcon != null) ...[
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: items[i].leadingBackgroundColor ?? AppColors.navBarActivePill,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Icon(
                            items[i].leadingIcon,
                            color: items[i].leadingIconColor ?? AppColors.textPrimary,
                            size: 20,
                          ),
                        ),
                        const SizedBox(width: AppSpacing.md),
                      ],
                      Expanded(
                        child: Text(
                          items[i].title,
                          style: AppTypography.titleSmall.copyWith(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w500,
                            height: 1.2,
                          ),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      const KalaiIcon(
                        KalaiIcons.chevronRight,
                        color: Color(0xFFD1D5DB),
                        size: 24,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ]
        ],
      ),
    );
  }
}
