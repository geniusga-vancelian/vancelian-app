import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/chat_api.dart';

/// Cognitive Bot v4 — Lot 7 V1.1 (2026-05-05). Footer cliquable rendu
/// SOUS la bulle texte assistant quand le serveur a annexé un payload
/// `auto_qcm` au tour (cf. ``service.stream_assistant_turn`` →
/// `done.auto_qcm` + `message_payload.auto_qcm`).
///
/// Distinct de [`_buildChoicesBubble`] côté `search_screen.dart` :
///
///   * `choices` (router QCM) → REMPLACE la bulle texte. Pas de markdown.
///     Bulle blanche dédiée.
///   * `auto_qcm` (post-process listing) → COMPLÈTE la bulle texte. La
///     bulle markdown reste affichée (le LLM y a écrit son explication
///     + sa liste). Le footer ajoute juste des boutons cliquables EN
///     BAS pour shortcut le clic sur une option, sans casser le flow
///     freeform — l'utilisateur peut toujours répondre par texte libre.
///
/// Le widget est stateless. L'état (option sélectionnée) vit dans le
/// `_ChatMessage` parent. Le tap est délégué via [onOptionTapped].
class AutoQcmFooter extends StatelessWidget {
  const AutoQcmFooter({
    super.key,
    required this.payload,
    required this.onOptionTapped,
    this.selectedOptionId,
    this.maxBubbleWidth,
  });

  /// Payload émis par le serveur. Voir [AssistanceAutoQcmPayload].
  final AssistanceAutoQcmPayload payload;

  /// Callback déclenché au tap sur une option. Le caller envoie
  /// typiquement un nouveau tour avec `text=option.label` + `agentHint`.
  final void Function(AssistanceChoiceOption option) onOptionTapped;

  /// Si non-null, l'option correspondante est mise en avant et toutes
  /// les autres deviennent atténuées et non cliquables (mode
  /// **consommé**). Symétrique du QCM router.
  final String? selectedOptionId;

  /// Largeur max imposée par le parent (souvent
  /// `MediaQuery.sizeOf(ctx).width * 0.92` pour matcher la bulle texte).
  /// Si `null`, le widget ne contraint pas et prend la largeur naturelle.
  final double? maxBubbleWidth;

  bool get _isConsumed => selectedOptionId != null;

  @override
  Widget build(BuildContext context) {
    if (payload.options.isEmpty) {
      return const SizedBox.shrink();
    }

    final headerText = payload.prompt.trim().isEmpty
        ? 'Tu peux choisir directement :'
        : payload.prompt.trim();

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Mini-libellé d'introduction. Volontairement plus discret que
        // dans `_buildChoicesBubble` (paragraphe meta, pas paragraph)
        // car le contexte (la liste) a déjà été dit dans la bulle texte
        // au-dessus — on ne veut pas répéter visuellement.
        Padding(
          padding: const EdgeInsets.only(
            left: AppSpacing.sm,
            right: AppSpacing.sm,
            bottom: AppSpacing.sm,
          ),
          child: Text(
            headerText,
            style: AppTypography.meta.copyWith(
              color: AppColors.textMuted,
              fontStyle: FontStyle.italic,
            ),
          ),
        ),
        // Boutons cliquables, un par option. Layout vertical pour
        // garder la lisibilité sur tous les longs labels (cap 7 côté
        // serveur, mais on ne fait pas confiance et on reflow proprement
        // si jamais).
        for (final option in payload.options)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.xs),
            child: _AutoQcmButton(
              option: option,
              isConsumed: _isConsumed,
              isSelected:
                  _isConsumed && option.id == selectedOptionId,
              onTap: _isConsumed ? null : () => onOptionTapped(option),
            ),
          ),
      ],
    );

    final width = maxBubbleWidth;
    if (width == null) return content;
    return ConstrainedBox(
      constraints: BoxConstraints(maxWidth: width),
      child: content,
    );
  }
}


/// Bouton individuel. Plus discret que `_buildChoiceButton` du
/// `search_screen.dart` (qui est utilisé pour les QCM router pleins).
/// Volontairement style outlined uniforme (pas de wash indigo) pour
/// que le footer s'intègre visuellement comme **complément** d'une
/// bulle texte, pas comme un module à part.
class _AutoQcmButton extends StatelessWidget {
  const _AutoQcmButton({
    required this.option,
    required this.isConsumed,
    required this.isSelected,
    required this.onTap,
  });

  final AssistanceChoiceOption option;
  final bool isConsumed;
  final bool isSelected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final Color borderColor;
    final Color textColor;
    final Color iconColor;
    final FontWeight textWeight;
    final IconData iconData;

    if (isSelected) {
      borderColor = AppColors.textPrimary;
      textColor = AppColors.textPrimary;
      iconColor = AppColors.textPrimary;
      textWeight = FontWeight.w600;
      iconData = Icons.check_rounded;
    } else if (isConsumed) {
      borderColor = AppColors.textMuted.withValues(alpha: 0.25);
      textColor = AppColors.textMuted;
      iconColor = AppColors.textMuted;
      textWeight = FontWeight.w400;
      iconData = Icons.arrow_forward_ios;
    } else {
      borderColor = AppColors.textMuted.withValues(alpha: 0.4);
      textColor = AppColors.textPrimary;
      iconColor = AppColors.textPrimary;
      textWeight = FontWeight.w500;
      iconData = Icons.arrow_forward_ios;
    }

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(AppRadius.bubble),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.bubble),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.sm,
          ),
          decoration: BoxDecoration(
            color: Colors.transparent,
            border: Border.all(color: borderColor, width: 1),
            borderRadius: BorderRadius.circular(AppRadius.bubble),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  option.label,
                  style: AppTypography.paragraph.copyWith(
                    color: textColor,
                    fontWeight: textWeight,
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Icon(iconData, size: 14, color: iconColor),
            ],
          ),
        ),
      ),
    );
  }
}
