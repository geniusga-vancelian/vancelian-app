import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import 'authentication_methods_screen.dart';
import 'devices_placeholder_screen.dart';

/// Hub Sécurité (profil) — navigation vers méthodes de connexion et appareils.
class SecurityScreen extends StatelessWidget {
  const SecurityScreen({super.key});

  void _push(BuildContext context, Widget screen) {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(builder: (_) => screen),
    );
  }

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Sécurité',
      content: [
        const SizedBox(height: AppSpacing.md),
        const AppSectionTitle('Mon compte'),
        const SizedBox(height: AppSpacing.md),
        SettingsCard(
          children: [
            SettingsListItem(
              leading: const Icon(
                Icons.password_outlined,
                size: 24,
                color: AppColors.textPrimary,
              ),
              title: 'Méthodes de connexion',
              subtitle: 'Face ID, code, et plus',
              showChevron: true,
              onTap: () => _push(context, const AuthenticationMethodsScreen()),
            ),
            SettingsListItem(
              leading: const Icon(
                Icons.smartphone_outlined,
                size: 24,
                color: AppColors.textPrimary,
              ),
              title: 'Appareils',
              subtitle: 'Sessions et appareils connectés',
              showChevron: true,
              onTap: () => _push(context, const DevicesPlaceholderScreen()),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xxl),
        const AppSectionTitle('Compte Business'),
        const SizedBox(height: AppSpacing.md),
        const SettingsCard(
          children: [
            SettingsListItem(
              leading: Icon(
                Icons.business_outlined,
                size: 24,
                color: AppColors.textPrimary,
              ),
              title: 'Espace professionnel',
              subtitle: 'Facturation, membres, rôles — bientôt disponible',
              showChevron: false,
            ),
          ],
        ),
      ],
    );
  }
}
