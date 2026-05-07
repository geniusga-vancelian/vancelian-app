import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';

/// Liste des comptes source d'investissement (assistant CAL).
class InvestSourceAccountListEmbed extends StatelessWidget {
  const InvestSourceAccountListEmbed({super.key, required this.embed});

  final AssistanceEmbed embed;

  @override
  Widget build(BuildContext context) {
    final title = (embed.data['title'] as String?)?.trim();
    final disclaimer = (embed.data['disclaimer'] as String?)?.trim();
    final rawItems = embed.data['items'];
    final items = rawItems is List
        ? rawItems.whereType<Map<String, dynamic>>().toList()
        : <Map<String, dynamic>>[];

    return Container(
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
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (title != null && title.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Text(
                  title,
                  style: AppTypography.titleMedium.copyWith(
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
            ],
            ...items.map((row) => _AccountRow(data: row)),
            if (disclaimer != null && disclaimer.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: Text(
                  disclaimer,
                  style: AppTypography.meta.copyWith(
                    color: AppColors.textMuted,
                    height: 1.35,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _AccountRow extends StatelessWidget {
  const _AccountRow({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final label = (data['label'] as String?) ?? '';
    final balanceDisplay =
        (data['balance_display'] as String?) ?? '${data['balance'] ?? ''}';
    final cur = (data['currency'] as String?) ?? '';
    final deepLink = data['deep_link'] as String?;
    final disabled = data['disabled'] == true;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: disabled || deepLink == null || deepLink.isEmpty
            ? null
            : () async {
                await AssistanceDeepLinkResolver.resolve(context, deepLink);
              },
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: AppTypography.bodyLarge.copyWith(
                        fontWeight: FontWeight.w600,
                        color: disabled
                            ? AppColors.textMuted
                            : AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '$balanceDisplay ${cur.isNotEmpty ? cur : ''}'.trim(),
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              if (disabled)
                Text(
                  'Bientôt',
                  style: AppTypography.meta.copyWith(color: AppColors.textMuted),
                )
              else
                const Icon(
                  Icons.chevron_right_rounded,
                  color: AppColors.textSecondary,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
