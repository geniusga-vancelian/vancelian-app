import 'package:flutter/material.dart';

import '../../login/presentation/login_phone_screen.dart';

/// Compatibilité : ouvre directement le flux connexion mobile-first (téléphone).
///
/// L’accueil marketing unifié est [WelcomeLandingScreen] (Login0).
class ApiSessionLoginScreen extends StatelessWidget {
  const ApiSessionLoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const LoginPhoneScreen();
  }
}
