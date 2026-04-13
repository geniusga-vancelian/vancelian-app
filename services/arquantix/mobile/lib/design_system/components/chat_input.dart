import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Input type ChatGPT : fond gris léger, placeholder gris moyen, police paragraphe.
class ChatInput extends StatelessWidget {
  const ChatInput({
    super.key,
    required this.controller,
    this.hintText = 'Poser une question',
    this.maxLines = 4,
    this.minLines = 1,
    this.textInputAction = TextInputAction.send,
    this.onSubmitted,
    this.onChanged,
  });

  final TextEditingController controller;
  final String hintText;
  final int maxLines;
  final int minLines;
  final TextInputAction textInputAction;
  final void Function(String)? onSubmitted;
  final void Function(String)? onChanged;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      decoration: InputDecoration(
        hintText: hintText,
        hintStyle: AppTypography.chatBody.copyWith(color: AppColors.chatInputHint),
        filled: true,
        fillColor: AppColors.chatInputBg,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.navBarPill),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.navBarPill),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.navBarPill),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
      ),
      style: AppTypography.chatBody,
      maxLines: maxLines,
      minLines: minLines,
      textInputAction: textInputAction,
      onSubmitted: onSubmitted,
      onChanged: onChanged,
    );
  }
}
