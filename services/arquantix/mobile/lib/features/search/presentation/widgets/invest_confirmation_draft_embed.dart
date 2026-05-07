import 'package:flutter/material.dart';

import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/components/amount_display.dart';
import '../../../../design_system/design_system.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';

/// Brouillon de confirmation d'investissement (assistant CAL) — aligné sur
/// l'esprit [WealthubConfirmationPageLayout] : titre, montant héros,
/// lignes source/destination, **Confirmer** + **Annuler**.
class InvestConfirmationDraftEmbed extends StatelessWidget {
  const InvestConfirmationDraftEmbed({super.key, required this.embed});

  final AssistanceEmbed embed;

  @override
  Widget build(BuildContext context) {
    final headline =
        (embed.data['headline'] as String?) ?? 'Confirmer ton investissement';
    final hero = (embed.data['hero_amount'] as String?) ?? '—';
    final sourceLine = (embed.data['source_line'] as String?) ?? '';
    final destLine = (embed.data['destination_line'] as String?) ?? '';
    final disclaimer = (embed.data['disclaimer'] as String?)?.trim();
    final confirmLink = embed.data['confirm_deep_link'] as String?;
    final confirmLabel =
        (embed.data['confirm_label'] as String?) ?? 'Confirmer';
    final cancelLabel = (embed.data['cancel_label'] as String?) ?? 'Annuler';

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
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            headline,
            textAlign: TextAlign.center,
            style: AppTypography.titleLarge.copyWith(
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          AmountDisplay(
            amount: hero,
            subtitle: sourceLine.isNotEmpty ? sourceLine : ' ',
            subtext: destLine.isNotEmpty ? destLine : null,
          ),
          if (disclaimer != null && disclaimer.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              disclaimer,
              textAlign: TextAlign.center,
              style: AppTypography.meta.copyWith(
                color: AppColors.textMuted,
                height: 1.35,
              ),
            ),
          ],
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {
                    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
                      SnackBar(
                        content: Text(cancelLabel == 'Annuler'
                            ? 'Demande annulée'
                            : cancelLabel),
                        duration: const Duration(seconds: 2),
                      ),
                    );
                  },
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    foregroundColor: AppColors.textPrimary,
                    side: BorderSide(
                      color: AppColors.textPrimary.withValues(alpha: 0.2),
                    ),
                  ),
                  child: Text(cancelLabel),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: FilledButton(
                  onPressed: confirmLink == null || confirmLink.isEmpty
                      ? null
                      : () async {
                          await AssistanceDeepLinkResolver.resolve(
                            context,
                            confirmLink,
                          );
                        },
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    backgroundColor: AppColors.indigo,
                    foregroundColor: Colors.white,
                  ),
                  child: Text(confirmLabel),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
