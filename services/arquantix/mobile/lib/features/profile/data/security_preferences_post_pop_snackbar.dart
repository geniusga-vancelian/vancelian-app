import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../../design_system/atoms/app_spacing.dart';

/// Snackbar après [Navigator.pop] : exécution post-frame pour fiabilité (route démontée).
void showSecurityPreferencesPostPopSnackBar(
  ScaffoldMessengerState? messenger,
  String message,
) {
  SchedulerBinding.instance.addPostFrameCallback((_) {
    if (messenger == null) return;
    messenger.showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(AppSpacing.md),
      ),
    );
  });
}
