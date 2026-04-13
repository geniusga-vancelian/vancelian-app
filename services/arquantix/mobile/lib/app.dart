import 'package:flutter/material.dart';

import 'l10n/app_localizations.dart';
import 'core/app_nav_routes.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/presentation/screens/welcome_landing_screen.dart';
import 'features/markets/presentation/screens/crypto_detail_screen.dart';
import 'features/markets/presentation/widgets/top_crypto_assets_module.dart';
import 'features/security/passcode/presentation/screens/passcode_setup_screen.dart';
import 'features/security/passcode/presentation/screens/secure_gate_screen.dart';
import 'features/splash/presentation/screens/splash_screen.dart';

/// Point d'entrée UI : splash (logo) puis dashboard.
class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Arquantix News',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      localeListResolutionCallback: (locales, supported) {
        if (locales == null || locales.isEmpty) return const Locale('en');
        for (final l in locales) {
          if (l.languageCode == 'fr') return const Locale('fr');
          if (l.languageCode == 'en') return const Locale('en');
        }
        return const Locale('en');
      },
      home: const AppLaunchRoot(),
      routes: {
        AppNavRoutes.welcome: (_) => const WelcomeLandingScreen(),
        AppNavRoutes.passcodeSetupBootstrap: (_) => const PasscodeSetupScreen(
              onSuccessCompletion:
                  PasscodeSetupOnSuccess.continueToAppSecureGate,
            ),
        AppNavRoutes.secureGate: (_) => const SecureGateScreen(),
        AppNavRoutes.secureGatePostAuth: (_) =>
            const SecureGateScreen(forceUnlock: true),
      },
      onGenerateRoute: (settings) {
        final name = settings.name ?? '';
        final uri = Uri.tryParse(name);
        if (uri != null &&
            uri.pathSegments.length == 2 &&
            uri.pathSegments.first == 'crypto') {
          final slug = uri.pathSegments[1].trim().toLowerCase();
          final fromArgs = settings.arguments;
          final asset = fromArgs is CryptoAssetItem
              ? fromArgs
              : CryptoDetailScreen.assetFromSlug(slug);
          return MaterialPageRoute<void>(
            builder: (_) => CryptoDetailScreen(asset: asset),
            settings: settings,
          );
        }
        return null;
      },
    );
  }
}
