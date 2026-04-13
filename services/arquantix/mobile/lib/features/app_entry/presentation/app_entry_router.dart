import 'package:flutter/material.dart';

import '../../auth/presentation/screens/welcome_landing_screen.dart';
import '../../security/passcode/presentation/screens/passcode_setup_screen.dart';
import '../application/app_entry_bootstrap.dart';
import '../domain/app_entry_destination.dart';

/// Routeur maître (tests / usages ponctuels) : une seule transition vers l’écran cible.
class AppEntryRouter extends StatefulWidget {
  const AppEntryRouter({
    super.key,
    this.resolveDestinationOverride,
  });

  /// Tests : court-circuite [AppEntryBootstrap.resolveInitialRootWidget].
  final Future<AppEntryDestination> Function()? resolveDestinationOverride;

  @override
  State<AppEntryRouter> createState() => _AppEntryRouterState();
}

class _AppEntryRouterState extends State<AppEntryRouter> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _go());
  }

  Future<void> _go() async {
    final Widget next;
    if (widget.resolveDestinationOverride != null) {
      final dest = await widget.resolveDestinationOverride!();
      if (!mounted) return;
      next = switch (dest) {
        AppEntryDestination.login0 => const WelcomeLandingScreen(),
        AppEntryDestination.passcodeSetup => const PasscodeSetupScreen(
            onSuccessCompletion: PasscodeSetupOnSuccess.continueToAppSecureGate,
          ),
        AppEntryDestination.secureGate =>
          await AppEntryBootstrap.resolveInitialRootWidget(),
      };
    } else {
      next = await AppEntryBootstrap.resolveInitialRootWidget();
    }
    if (!mounted) return;

    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(builder: (_) => next),
    );
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(strokeWidth: 2.5),
        ),
      ),
    );
  }
}
