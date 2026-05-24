import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../../../core/config.dart' as app_config;
import '../../../../core/jank_trace.dart';
import '../../../../core/navigation/auth_slide_route.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/components/app_primary_button.dart';
import '../../../security/login/presentation/login_email_fallback_screen.dart';
import '../../../security/login/presentation/login_phone_screen.dart';
import '../widgets/brand_hero_intro/brand_hero_intro.dart';

/// Login0 : intro splash → hero (vidéo par défaut [Config.kLogin0DefaultHeroVideoUrl], repli image) + CTA.
/// Connexion → [LoginPhoneScreen] ; inscription → même écran en mode inscription.
class WelcomeLandingScreen extends StatefulWidget {
  const WelcomeLandingScreen({
    super.key,
    this.seamlessFromColdLaunch = false,
    this.bootstrapPending = false,
  });

  /// Après [AppLaunchRoot] : même fond / logo — enchaînement sans attente artificielle longue.
  final bool seamlessFromColdLaunch;

  /// `true` tant que la session est en cours de résolution (logo seul, pas de média).
  final bool bootstrapPending;

  @override
  State<WelcomeLandingScreen> createState() => _WelcomeLandingScreenState();
}

class _WelcomeLandingScreenState extends State<WelcomeLandingScreen> {
  String? _heroUrl;

  /// Vidéo d’intro depuis le BFF (`/api/mobile/flutter/welcome` → `heroVideoUrl`), alignée sur Admin Media.
  String? _bffHeroVideoUrl;

  @override
  void initState() {
    super.initState();
    final direct = app_config.Config.welcomeHeroDirectUrl;
    final login0 = app_config.Config.login0HeroBackgroundUrl;
    if (direct != null) {
      _heroUrl = direct;
    } else if (login0 != null && login0.isNotEmpty) {
      _heroUrl = login0;
    } else {
      _heroUrl = app_config.Config.kLogin0DefaultHeroImageUrl;
    }
    _resolveHeroUrl();
  }

  /// Ordre : [WELCOME_HERO_DIRECT_URL] → [LOGIN0_HERO_BACKGROUND_URL] → BFF
  /// `heroImageUrl` → défaut [Config.kLogin0DefaultHeroImageUrl].
  Future<void> _resolveHeroUrl() async {
    final direct = app_config.Config.welcomeHeroDirectUrl;
    if (direct != null) return;
    final login0 = app_config.Config.login0HeroBackgroundUrl;
    if (login0 != null && login0.isNotEmpty) return;

    try {
      final uri = Uri.parse(app_config.Config.welcomeConfigUrl);
      final res = await http.get(uri).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final map = jsonDecode(res.body) as Map<String, dynamic>;
        final url = map['heroImageUrl'] as String?;
        final videoUrl = map['heroVideoUrl'] as String?;
        if (mounted) {
          setState(() {
            if (url != null && url.trim().isNotEmpty) {
              _heroUrl = url.trim();
            }
            if (videoUrl != null && videoUrl.trim().isNotEmpty) {
              _bffHeroVideoUrl = videoUrl.trim();
            }
          });
        }
      }
    } catch (_) {
      // BFF injoignable : conserver le défaut Login0 défini dans initState.
    }
  }

  Color _splashLogoColor() => const Color(0xFF000000);

  Future<void> _onLogin(BuildContext context) async {
    JankTrace.tap('login');
    await Navigator.of(context).push<bool>(
      authSlideRoute<bool>((_) => const LoginEmailFallbackScreen()),
    );
  }

  void _onSignUp(BuildContext context) {
    JankTrace.tap('register');
    Navigator.of(context).push<void>(
      authSlideRoute<void>(
        (_) => const LoginEmailFallbackScreen(signUpMode: true),
      ),
    );
  }

  /// URL vidéo réseau : dart-define → BFF → [Config.kLogin0DefaultHeroVideoUrl].
  String? get _effectiveNetworkHeroVideoUrl {
    final fromDefine = app_config.Config.login0HeroVideoUrl;
    if (fromDefine != null && fromDefine.isNotEmpty) return fromDefine;
    if (_bffHeroVideoUrl != null && _bffHeroVideoUrl!.isNotEmpty) {
      return _bffHeroVideoUrl;
    }
    final fallback = app_config.Config.kLogin0DefaultHeroVideoUrl.trim();
    return fallback.isEmpty ? null : fallback;
  }

  bool get _useHeroVideoLayer {
    if (app_config.Config.login0UseHeroVideo) return true;
    if (app_config.Config.kLogin0DefaultHeroVideoUrl.trim().isNotEmpty) {
      return true;
    }
    return _bffHeroVideoUrl != null && _bffHeroVideoUrl!.isNotEmpty;
  }

  @override
  Widget build(BuildContext context) {
    return BrandHeroIntroPage(
      config: BrandHeroIntroConfig(
        bootstrapPending: widget.bootstrapPending,
        pendingMediaResolution: false,
        networkImageUrl: _heroUrl,
        useHeroVideo: _useHeroVideoLayer,
        heroVideoAssetPath: app_config.Config.login0HeroVideoAssetPath,
        networkHeroVideoUrl: _effectiveNetworkHeroVideoUrl,
        splashBackgroundColor: Colors.white,
        skipSplashHoldAfterColdLaunch: widget.seamlessFromColdLaunch,
        logoColorSplash: _splashLogoColor(),
        logoColorHero: Colors.white,
      ),
      bottom: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          AppPrimaryButton(
            label: 'Créer un compte',
            variant: AppPrimaryButtonVariant.primary,
            size: AppPrimaryButtonSize.large,
            onPressed: () => _onSignUp(context),
          ),
          const SizedBox(height: AppSpacing.md),
          AppPrimaryButton(
            label: 'Me connecter',
            variant: AppPrimaryButtonVariant.secondary,
            size: AppPrimaryButtonSize.large,
            onPressed: () => _onLogin(context),
          ),
        ],
      ),
    );
  }
}
