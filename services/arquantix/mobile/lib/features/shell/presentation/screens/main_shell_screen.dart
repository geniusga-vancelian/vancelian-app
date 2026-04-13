import 'dart:developer' as developer;

import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../../app_entry/application/post_auth_navigation_flags.dart';
import '../../../profile/application/security_preferences_coordinator.dart';
import '../../../home/presentation/screens/home_screen.dart';
import '../../../markets/presentation/screens/markets_screen.dart';
import '../../../offers/presentation/screens/offers_screen.dart';
import '../../../design_system/presentation/screens/design_system_showcase_screen.dart';
import '../../../search/presentation/screens/search_screen.dart';
import '../../../security/local_access/biometric_policy_service.dart';
import '../../../security/local_access/local_relock_engine.dart';
import '../../../security/onboarding/push_notifications_onboarding_screen.dart';
import '../../../security/passcode/data/passcode_service.dart';
import '../../../security/passcode/data/session_service.dart';
import '../../../security/passcode/domain/secure_access_config.dart';
import '../../../security/passcode/presentation/screens/passcode_unlock_screen.dart';

/// Shell principal : contenu + AppTabBar flottant (glassmorphism, sliding pill).
/// Le contenu s'étend SOUS la barre pour que la transparence/blur affiche le contenu.
class MainShellScreen extends StatefulWidget {
  const MainShellScreen({super.key});

  @override
  State<MainShellScreen> createState() => _MainShellScreenState();
}

class _MainShellScreenState extends State<MainShellScreen>
    with WidgetsBindingObserver {
  int _selectedIndex = 0;
  DateTime? _pausedAt;
  bool _resumeUnlockOpen = false;

  static const int _searchIndex = 4;

  static const _tabItems = [
    AppTabBarItemData(icon: Icons.home_rounded, label: 'Accueil'),
    AppTabBarItemData(icon: Icons.trending_up_rounded, label: 'Investir'),
    AppTabBarItemData(icon: Icons.currency_bitcoin, label: 'Markets'),
    AppTabBarItemData(icon: Icons.radio_rounded, label: 'Design'),
  ];

  List<Widget> _buildPages() => [
        const HomeScreen(),
        const OffersScreen(),
        const MarketsScreen(),
        const DesignSystemShowcaseScreen(),
        SearchScreen(onBack: () => setState(() => _selectedIndex = 0)),
      ];

  void _onItemTapped(int index) {
    setState(() => _selectedIndex = index);
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance
        .addPostFrameCallback((_) => _maybeOfferPushReloginOnboarding());
  }

  /// Re-prompt unique : skip inscription → première montée du shell **hors** fin de parcours inscription.
  Future<void> _maybeOfferPushReloginOnboarding() async {
    if (!mounted) return;
    if (PostAuthNavigationFlags.suppressNextMainShellPushReloginPrompt) {
      PostAuthNavigationFlags.suppressNextMainShellPushReloginPrompt = false;
      return;
    }
    await PasscodeService.instance.init();
    final s = await PasscodeService.instance.getPushOnboardingPromptState();
    if (!SecurityPreferencesCoordinator.shouldOfferReloginPushOnboarding(s)) {
      return;
    }
    if (!mounted) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        fullscreenDialog: true,
        builder: (_) => const PushNotificationsOnboardingScreen(
          kind: PushNotificationsOnboardingKind.reloginReprompt,
        ),
      ),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (!SecureAccessConfig.enableResumeRelock) return;
    if (state == AppLifecycleState.paused) {
      _pausedAt = DateTime.now();
    }
    if (state == AppLifecycleState.resumed) {
      _maybeRequireResumeUnlock();
    }
  }

  Future<void> _maybeRequireResumeUnlock() async {
    final paused = _pausedAt;
    _pausedAt = null;
    if (paused == null || _resumeUnlockOpen || !mounted) return;
    await PasscodeService.instance.init();
    if (!PasscodeService.instance.isPasscodeConfigured) return;
    final now = DateTime.now();
    final snapshot = await SessionService.instance.readSecuritySnapshot();
    final needRelock = await BiometricPolicyService.instance.shouldRelockNow(
      lastActiveAt: paused,
      riskContext: snapshot,
      appLifecycleContext: const AppLifecycleSecurityContext(
        isReturningFromBackground: true,
      ),
      now: now,
    );
    if (!needRelock) return;
    _resumeUnlockOpen = true;
    developer.log(
      'auth.app.relocked',
      name: 'arquantix.security',
    );
    if (!mounted) {
      _resumeUnlockOpen = false;
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        fullscreenDialog: true,
        builder: (_) => const PasscodeUnlockScreen(popOnSuccess: true),
      ),
    );
    _resumeUnlockOpen = false;
  }

  @override
  Widget build(BuildContext context) {
    final showNav = _selectedIndex != _searchIndex;

    return Scaffold(
      body: Stack(
        children: [
          Positioned.fill(
            child: IndexedStack(
              index: _selectedIndex,
              children: _buildPages(),
            ),
          ),
          if (showNav)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      AppColors.pageBackground.withValues(alpha: 0.0),
                      AppColors.pageBackground.withValues(alpha: 1.0),
                    ],
                  ),
                ),
                child: Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.pageEdge),
                  child: SafeArea(
                    top: false,
                    child: AppTabBar(
                      items: _tabItems,
                      selectedIndex: _selectedIndex,
                      onTap: _onItemTapped,
                      actionIcon: Icons.search_rounded,
                      onActionTap: () => _onItemTapped(_searchIndex),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
