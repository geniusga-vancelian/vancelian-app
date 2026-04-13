import 'package:flutter/widgets.dart';

import 'app_warmup_service.dart';

/// Compatibilité : délègue à [AppWarmupService.scheduleDuringIntro].
///
/// Conservé pour les appels existants (LoginPhone secours, tests).
Future<void> scheduleInteractionWarmup(BuildContext context) =>
    AppWarmupService.instance.scheduleDuringIntro(context);
