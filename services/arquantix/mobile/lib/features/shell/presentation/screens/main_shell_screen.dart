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
import '../../data/app_shell_service.dart';
import '../../../cms_page/presentation/screens/cms_page_screen.dart';

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

  /// Le bouton « Search » reste un **action button** distinct (hors tab bar).
  /// Son index logique synthétique vaut `tabs.length` : il est calculé à la
  /// volée dans `build` depuis l'état `AppShellService` courant.

  /// Construit la `Widget` correspondant à un tab CMS résolu. Pour cette V1,
  /// seules les `native_tab` connues sont câblées : tout autre `target` est
  /// rendu comme une page placeholder visible (pas de crash) — le mapping CMS
  /// → page sera étendu au jalon 3 (pages d'app pilotées CMS).
  Widget _pageForTab(AppShellTab tab) {
    final target = tab.target;
    if (target is NativeTabTarget) {
      switch (target.value) {
        case 'home':
          return const HomeScreen();
        case 'offers':
          return const OffersScreen();
        case 'markets':
          return const MarketsScreen();
        case 'design_system':
          return const DesignSystemShowcaseScreen();
      }
    }
    if (target is CmsPageTarget) {
      return CmsPageScreen(slug: target.slug);
    }
    /// `external_url` ne peut pas vivre dans la tab bar (il faut sortir de l'app
    /// ou ouvrir un browser embedded) — placeholder explicite pour l'instant.
    return _UnsupportedTabPlaceholder(label: tab.label);
  }

  List<Widget> _buildPages(List<AppShellTab> tabs) {
    return [
      for (final tab in tabs) _pageForTab(tab),
      SearchScreen(onBack: () => setState(() => _selectedIndex = 0)),
    ];
  }

  void _onItemTapped(int index) {
    setState(() => _selectedIndex = index);
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance
        .addPostFrameCallback((_) => _maybeOfferPushReloginOnboarding());
    /// Bootstrap silencieux du shell distant — fallback compilé garanti.
    AppShellService.instance.bootstrap();
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
    return ListenableBuilder(
      listenable: AppShellService.instance,
      builder: (context, _) {
        final tabs = AppShellService.instance.tabs;
        final searchIndex = tabs.length;
        /// Si la liste de tabs distante a réduit (ex. admin a désactivé un tab
        /// pendant la session), on borne l'index sélectionné pour éviter un
        /// crash de l'`IndexedStack`.
        if (_selectedIndex > searchIndex) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) setState(() => _selectedIndex = 0);
          });
        }
        final tabItems =
            tabs.map((t) => t.toTabBarItem()).toList(growable: false);
        final showNav = _selectedIndex != searchIndex;

        return Scaffold(
          body: Stack(
            children: [
              Positioned.fill(
                child: IndexedStack(
                  index: _selectedIndex.clamp(0, searchIndex).toInt(),
                  children: _buildPages(tabs),
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
                          items: tabItems,
                          selectedIndex:
                              _selectedIndex.clamp(0, tabItems.length - 1).toInt(),
                          onTap: _onItemTapped,
                          actionIcon: Icons.search_rounded,
                          onActionTap: () => _onItemTapped(searchIndex),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}

/// Placeholder rendu si une `target` CMS n'est pas encore mappée côté Dart
/// (ex. `cms_page` créée par l'admin avant le runtime CMS pages — jalon 3).
class _UnsupportedTabPlaceholder extends StatelessWidget {
  const _UnsupportedTabPlaceholder({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.construction_rounded, size: 48),
                const SizedBox(height: 12),
                Text(
                  '$label — bientôt disponible',
                  style: AppTypography.bodyRegular,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
