import 'package:flutter/material.dart';

import '../../../../app_entry/application/app_entry_bootstrap.dart';

/// Après route nommée ou usage historique : une transition vers l’écran effectif (shell / PIN / login).
///
/// [forceUnlock] : comme auparavant, forcer le déverrouillage local après auth serveur.
class SecureGateScreen extends StatefulWidget {
  const SecureGateScreen({super.key, this.forceUnlock = false});

  final bool forceUnlock;

  @override
  State<SecureGateScreen> createState() => _SecureGateScreenState();
}

class _SecureGateScreenState extends State<SecureGateScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _route());
  }

  Future<void> _route() async {
    await AppEntryBootstrap.pushRootReplacingAll(
      context,
      forcePostAuthUnlock: widget.forceUnlock,
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
