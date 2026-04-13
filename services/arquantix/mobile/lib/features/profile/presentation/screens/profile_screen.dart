import 'package:flutter/material.dart';

import '../../../../core/app_info_service.dart';
import '../../../../core/currency_preference.dart';
import '../../../../core/profile_identity_coordinator.dart';
import '../../../../core/profile_leading_preference.dart';
import '../../../../core/secure_api_config.dart';
import '../../data/mobile_app_profile.dart';
import '../../../../design_system/design_system.dart';
import '../../../help/presentation/screens/help_center_screen.dart';
import '../../../notifications/presentation/screens/notification_center_screen.dart';
import '../../../registration/screens/registration_flow_launcher_screen.dart';
import '../../../security/login/presentation/login_phone_screen.dart';
import '../../../security/passkeys/presentation/passkey_management_screen.dart';
import '../../../search/presentation/screens/search_screen.dart';
import 'account_info_screen.dart';
import 'notification_settings_screen.dart';
import 'security_screen.dart';

/// Page profil utilisateur (accessible depuis le header de l'accueil).
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final CurrencyPreference _pref = CurrencyPreference.instance;
  bool _updating = false;
  bool _emailNotifications = false;
  bool _loadingAccount = true;
  MobileAppProfile? _account;

  @override
  void initState() {
    super.initState();
    _loadAccountSummary();
  }

  Future<void> _loadAccountSummary() async {
    final p = await ProfileIdentityCoordinator.instance.loadAccountProfile(
      debugTag: 'ProfileScreen',
    );
    if (!mounted) return;
    setState(() {
      _account = p;
      _loadingAccount = false;
    });
  }

  Future<void> _onCurrencyChanged(ReferenceCurrency value) async {
    if (value == _pref.currency || _updating) return;
    setState(() => _updating = true);
    await _pref.update(value);
    if (mounted) setState(() => _updating = false);
  }

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Profil',
      content: [
        _buildProfileHeader(),
        const SizedBox(height: AppSpacing.xxl),
        _buildCurrencyCard(),
        const SizedBox(height: AppSpacing.xxl),
        _buildPreferencesCard(),
        const SizedBox(height: AppSpacing.xxl),
        _buildSupportCard(),
        const SizedBox(height: AppSpacing.xxl),
        _buildDevToolsCard(),
        const SizedBox(height: AppSpacing.xxl),
        _buildLegalCard(),
        const SizedBox(height: AppSpacing.xxl),
      ],
    );
  }

  String _monCompteSubtitle() {
    if (_loadingAccount) return 'Chargement…';
    final a = _account;
    if (a == null) return 'Gérer mon profil';
    final d = a.displayEmailOrNull;
    if (d != null && d.isNotEmpty) return d;
    return 'Gérer mon profil';
  }

  Widget _buildProfileHeader() {
    return ListenableBuilder(
      listenable: ProfileLeadingPreference.instance,
      builder: (context, _) {
        final initials = ProfileLeadingPreference.instance.initials;
        return SettingsCard(
          children: [
            SettingsListItem(
              leading: IconContainer(
                size: IconContainerSize.lg,
                borderRadius: 100,
                backgroundColor: const Color(0xFFE5E5EA),
                child: Text(
                  initials,
                  style: AppTypography.itemSupporting.copyWith(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                    color: const Color(0xFF3C3C43),
                  ),
                ),
              ),
              title: 'Mon compte',
              subtitle: _monCompteSubtitle(),
              showChevron: true,
              onTap: () => _push(const AccountInfoScreen()),
            ),
          ],
        );
      },
    );
  }

  Widget _buildCurrencyCard() {
    final current = _pref.currency;
    return SettingsCard(
      sectionTitle: 'Devise de référence',
      children: [
        Text(
          'Les prix et valorisations seront affichés dans la devise choisie.',
          style: AppTypography.itemSupporting
              .copyWith(color: const Color(0xFF8E8E93)),
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            Expanded(
              child: _CurrencyChoiceChip(
                label: 'EUR (€)',
                selected: current == ReferenceCurrency.eur,
                onTap: () => _onCurrencyChanged(ReferenceCurrency.eur),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: _CurrencyChoiceChip(
                label: 'USD (\$)',
                selected: current == ReferenceCurrency.usd,
                onTap: () => _onCurrencyChanged(ReferenceCurrency.usd),
              ),
            ),
          ],
        ),
        if (_updating)
          const Padding(
            padding: EdgeInsets.only(top: AppSpacing.sm),
            child: Center(
              child: SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildPreferencesCard() {
    return SettingsCard(
      sectionTitle: 'Paramètres',
      children: [
        SettingsListItem(
          leading: const Icon(
            Icons.shield_outlined,
            size: 24,
            color: AppColors.textPrimary,
          ),
          title: 'Sécurité',
          subtitle: 'Méthodes de connexion, appareils',
          showChevron: true,
          onTap: () => _push(const SecurityScreen()),
        ),
        SettingsListItem(
          leading: const Icon(
            Icons.notifications_outlined,
            size: 24,
            color: AppColors.textPrimary,
          ),
          title: 'Notifications',
          subtitle: 'Toutes les alertes sur cet appareil',
          showChevron: true,
          onTap: () => _push(const NotificationSettingsScreen()),
        ),
        SettingsListItem(
          title: 'Notifications email',
          subtitle: 'Newsletters & rapports',
          trailing: AppToggleSwitch(
            value: _emailNotifications,
            onChanged: (v) => setState(() => _emailNotifications = v),
          ),
        ),
      ],
    );
  }

  Widget _buildSupportCard() {
    return SettingsCard(
      sectionTitle: 'Support',
      children: [
        SettingsListItem(
          leading: const Icon(
            Icons.help_outline_rounded,
            size: 24,
            color: AppColors.textPrimary,
          ),
          title: 'Centre d\'aide',
          showChevron: true,
          onTap: () => _push(const HelpCenterScreen()),
        ),
        SettingsListItem(
          leading: const Icon(
            Icons.forum_outlined,
            size: 24,
            color: AppColors.textPrimary,
          ),
          title: 'Assistance sur mesure',
          showChevron: true,
          onTap: () => _push(const SearchScreen()),
        ),
        SettingsListItem(
          leading: const Icon(
            Icons.notifications_none_rounded,
            size: 24,
            color: AppColors.textPrimary,
          ),
          title: 'Boîte de réception',
          showChevron: true,
          onTap: () => _push(const NotificationCenterScreen()),
        ),
      ],
    );
  }

  Widget _buildDevToolsCard() {
    return SettingsCard(
      sectionTitle: 'Développement',
      children: [
        SettingsListItem(
          leading: const Icon(
            Icons.science_outlined,
            size: 24,
            color: AppColors.indigo,
          ),
          title: 'Parcours d’inscription',
          subtitle: 'Reprendre ou suivre votre dossier (données réelles)',
          showChevron: true,
          onTap: () => _push(const RegistrationFlowLauncherScreen()),
        ),
      ],
    );
  }

  Widget _buildLegalCard() {
    return SettingsCard(
      sectionTitle: 'Informations',
      children: [
        SettingsListItem(
          leading: const Icon(Icons.description_outlined, size: 24, color: AppColors.textPrimary),
          title: 'Conditions générales',
          showChevron: true,
          onTap: () {},
        ),
        SettingsListItem(
          leading: const Icon(Icons.privacy_tip_outlined, size: 24, color: AppColors.textPrimary),
          title: 'Politique de confidentialité',
          showChevron: true,
          onTap: () {},
        ),
        if (SecureApiConfig.hasAuthBackend) ...[
          SettingsListItem(
            leading: const Icon(Icons.login_rounded, size: 24, color: AppColors.textPrimary),
            title: 'Connexion compte',
            subtitle: 'Mobile, e-mail, code ou passkey',
            showChevron: true,
            onTap: () => _push(const LoginPhoneScreen()),
          ),
          SettingsListItem(
            leading: const Icon(Icons.key_outlined, size: 24, color: AppColors.textPrimary),
            title: 'Passkeys',
            subtitle: 'Ajouter, lister, révoquer',
            showChevron: true,
            onTap: () => _push(const PasskeyManagementScreen()),
          ),
        ],
        SettingsListItem(
          title: 'Version',
          value: AppInfoService.fullVersion,
        ),
      ],
    );
  }

  void _push(Widget screen) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => screen),
    );
  }
}

class _CurrencyChoiceChip extends StatelessWidget {
  const _CurrencyChoiceChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: AppMotion.base,
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
        decoration: BoxDecoration(
          color: selected ? AppColors.textPrimary : AppColors.pageBackground,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected
                ? AppColors.textPrimary
                : AppColors.textSecondary.withValues(alpha: 0.2),
            width: 1.5,
          ),
        ),
        child: Center(
          child: Text(
            label,
            style: AppTypography.bodyEmphasized.copyWith(
              fontSize: 15,
              color: selected ? Colors.white : AppColors.textPrimary,
            ),
          ),
        ),
      ),
    );
  }
}
