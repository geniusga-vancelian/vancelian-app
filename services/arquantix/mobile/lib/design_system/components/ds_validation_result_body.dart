import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_typography.dart';
import 'ds_message_card.dart';
import 'ds_stepper_avatar.dart';

/// Bloc « module validation » Figma : [DsStepperAvatar] + titre 22px coloré + [DsMessageCard].
class DsValidationResultBody extends StatelessWidget {
  const DsValidationResultBody({
    super.key,
    required this.status,
    this.progress = 100,
    required this.headline,
    this.headlineColor,
    this.messageTitle,
    this.messageDescription,
    this.messageDescriptionStyle,
    this.messageCaption,
    this.stepperIcon,
  });

  final DsStepperAvatarStatus status;
  final double progress;
  final String headline;
  final Color? headlineColor;
  final String? messageTitle;
  final String? messageDescription;

  /// Style du [messageDescription] (défaut : petit gris via [DsMessageCard]).
  final TextStyle? messageDescriptionStyle;
  final String? messageCaption;
  final Widget? stepperIcon;

  static const Color _warningFigma = Color(0xFFFF9500);

  Color get _resolvedHeadlineColor =>
      headlineColor ??
      switch (status) {
        DsStepperAvatarStatus.success => AppColors.semanticPositive,
        DsStepperAvatarStatus.error => AppColors.semanticNegative,
        DsStepperAvatarStatus.warning => _warningFigma,
        DsStepperAvatarStatus.info => AppColors.actionPrimaryBlue,
      };

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        DsStepperAvatar(
          status: status,
          progress: progress,
          icon: stepperIcon,
        ),
        const SizedBox(height: 24),
        Text(
          headline,
          textAlign: TextAlign.center,
          style: AppTypography.articleTitle.copyWith(color: _resolvedHeadlineColor),
        ),
        if (messageTitle != null ||
            messageDescription != null ||
            messageCaption != null) ...[
          const SizedBox(height: 24),
          DsMessageCard(
            title: messageTitle,
            description: messageDescription,
            descriptionStyle: messageDescriptionStyle,
            caption: messageCaption,
          ),
        ],
      ],
    );
  }
}
