import 'package:flutter/material.dart';

import '../../../app_entry/application/app_entry_bootstrap.dart';
import '../../../auth/presentation/screens/welcome_landing_screen.dart';

/// Racine de lancement : un seul [WelcomeLandingScreen] (clé stable) pour éviter
/// tout clignotement splash → intro.
class AppLaunchRoot extends StatefulWidget {
  const AppLaunchRoot({super.key});

  @override
  State<AppLaunchRoot> createState() => _AppLaunchRootState();
}

class _AppLaunchRootState extends State<AppLaunchRoot> {
  Widget? _resolved;

  @override
  void initState() {
    super.initState();
    _resolve();
  }

  Future<void> _resolve() async {
    final next = await AppEntryBootstrap.resolveInitialRootWidget();
    if (!mounted) return;
    setState(() => _resolved = next);
  }

  @override
  Widget build(BuildContext context) {
    if (_resolved == null) {
      return const WelcomeLandingScreen(
        key: ValueKey('welcome'),
        bootstrapPending: true,
        seamlessFromColdLaunch: true,
      );
    }
    final w = _resolved!;
    if (w is WelcomeLandingScreen) {
      return const WelcomeLandingScreen(
        key: ValueKey('welcome'),
        bootstrapPending: false,
        seamlessFromColdLaunch: true,
      );
    }
    return w;
  }
}
