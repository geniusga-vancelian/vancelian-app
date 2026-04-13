import 'dart:async';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';

import '../../../../../core/app_warmup_service.dart';
import '../../../../../design_system/atoms/app_spacing.dart';
import 'brand_hero_intro_config.dart';
import 'hero_intro_motion.dart';
import 'hero_intro_video_fill.dart';
import 'splash_brand_logo.dart';

/// Un seul écran — pas de route secondaire pour la transition splash → hero.
///
/// Stack : [fond] → [média opacité : image ou vidéo] → [voile noir opacité] → [logo] → [UI].
class BrandHeroIntroPage extends StatefulWidget {
  const BrandHeroIntroPage({
    super.key,
    required this.config,
    required this.bottom,
    this.leading,
    this.trailing,
    this.systemUiOverlayStyle,
  });

  final BrandHeroIntroConfig config;
  final Widget bottom;
  final Widget? leading;
  final Widget? trailing;
  final SystemUiOverlayStyle? systemUiOverlayStyle;

  @override
  State<BrandHeroIntroPage> createState() => _BrandHeroIntroPageState();
}

class _BrandHeroIntroPageState extends State<BrandHeroIntroPage>
    with TickerProviderStateMixin {
  /// Timeline unique : logo (0–50 %) → média (image/vidéo) fade + phase 2 du voile (50–100 %).
  late final AnimationController _introMasterController;
  late final AnimationController _controlsFadeController;

  late final Animation<double> _logoT;
  late final Animation<double> _mediaOpacity;
  late final Animation<double> _controlsOpacity;

  Timer? _splashTimer;
  Timer? _controlsDelayTimer;

  bool _minSplashElapsed = false;
  bool _mediaReady = false;
  VideoPlayerController? _videoController;
  /// Animation du logo (indépendante du chargement média image/vidéo).
  bool _logoTransitionStarted = false;

  /// Tap pour skip : désactivé dès que le fondu des boutons démarre.
  bool _skipIntroTapActive = true;

  bool _controlsDelayScheduled = false;

  bool _useHeroChromeOverlay = false;

  BrandHeroIntroConfig get _c => widget.config;

  @override
  void initState() {
    super.initState();
    _introMasterController = AnimationController(
      vsync: this,
      duration: HeroIntroMotion.introMasterDuration,
    );
    _controlsFadeController = AnimationController(
      vsync: this,
      duration: HeroIntroMotion.controlsFadeIn,
    );

    _logoT = CurvedAnimation(
      parent: _introMasterController,
      curve: Interval(
        0,
        HeroIntroMotion.logoMoveEndFraction,
        curve: HeroIntroMotion.logoCurve,
      ),
    );
    _mediaOpacity = CurvedAnimation(
      parent: _introMasterController,
      curve: Interval(
        HeroIntroMotion.imageFadeStartFraction,
        HeroIntroMotion.imageFadeEndFraction,
        curve: HeroIntroMotion.imageFadeCurve,
      ),
    );
    _controlsOpacity = CurvedAnimation(
      parent: _controlsFadeController,
      curve: HeroIntroMotion.controlsCurve,
    );

    _introMasterController.addListener(_onIntroMasterTick);

    if (_c.skipIntro) {
      SchedulerBinding.instance.addPostFrameCallback((_) => _applySkipIntro());
    } else if (_c.bootstrapPending) {
      // Attente session : pas de média / timers.
    } else {
      _startIntroAfterSplash();
      _scheduleAppWarmupIfNeeded();
    }
  }

  /// Polices / drapeaux / Keychain pendant l’anim logo (non bloquant, idempotent).
  void _scheduleAppWarmupIfNeeded() {
    if (_c.skipIntro) return;
    if (_c.bootstrapPending) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      unawaited(AppWarmupService.instance.scheduleDuringIntro(context));
    });
  }

  double get _effectiveMediaOpacity =>
      _mediaReady ? _mediaOpacity.value : 0.0;

  void _syncMediaOverlayStyle() {
    final useHero = _effectiveMediaOpacity > 0.2 ||
        _introMasterController.value > HeroIntroMotion.imageFadeStartFraction;
    if (useHero != _useHeroChromeOverlay) {
      setState(() => _useHeroChromeOverlay = useHero);
    }
  }

  void _onIntroMasterTick() {
    _syncMediaOverlayStyle();
    if (_controlsDelayScheduled) return;
    if (_introMasterController.value < HeroIntroMotion.logoMoveEndFraction) {
      return;
    }
    _controlsDelayScheduled = true;
    _controlsDelayTimer?.cancel();
    _controlsDelayTimer = Timer(HeroIntroMotion.controlsDelayAfterLogo, () {
      if (!mounted) return;
      _skipIntroTapActive = false;
      _controlsFadeController.forward();
    });
  }

  void _startIntroAfterSplash() {
    if (_c.skipIntro) return;
    final instantSplashHold = _c.skipSplashHoldAfterColdLaunch ||
        HeroIntroMotion.splashHold == Duration.zero;
    if (instantSplashHold) {
      _minSplashElapsed = true;
    } else {
      _splashTimer = Timer(HeroIntroMotion.splashHold, () {
        if (!mounted) return;
        setState(() => _minSplashElapsed = true);
        _tryStartLogoTransition();
      });
    }
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!_c.pendingMediaResolution) {
        _prepareMedia();
      }
      if (instantSplashHold) {
        _tryStartLogoTransition();
      }
    });
  }

  void _applySkipIntro() {
    _minSplashElapsed = true;
    _mediaReady = true;
    _logoTransitionStarted = true;
    _controlsDelayScheduled = true;
    _skipIntroTapActive = false;
    _introMasterController.value = 1;
    _controlsFadeController.value = 1;
  }

  Future<void> _prepareMedia() async {
    if (_c.pendingMediaResolution) return;
    if (_c.bootstrapPending) return;
    if (_c.useHeroVideoLayer) {
      await _prepareVideo();
    } else if (_c.hasStaticImage) {
      await _precacheStaticImage();
    } else {
      _setMediaReady();
    }
  }

  Future<void> _prepareVideo() async {
    final c = _c;
    final asset = c.heroVideoAssetPath?.trim();
    final url = c.networkHeroVideoUrl?.trim();
    VideoPlayerController? created;
    try {
      if (asset != null && asset.isNotEmpty) {
        created = VideoPlayerController.asset(asset);
      } else if (url != null && url.isNotEmpty) {
        created = VideoPlayerController.networkUrl(Uri.parse(url));
      } else {
        _setMediaReady();
        return;
      }
      await created.initialize();
      if (!mounted) {
        await created.dispose();
        return;
      }
      await created.setLooping(true);
      await created.setVolume(0);
      await created.play();
      setState(() => _videoController = created);
      _setMediaReady();
    } catch (_) {
      await created?.dispose();
      if (mounted) {
        setState(() => _videoController = null);
      }
      _setMediaReady();
    }
  }

  Future<void> _precacheStaticImage() async {
    final c = _c;
    try {
      if (c.imageAssetPath != null && c.imageAssetPath!.trim().isNotEmpty) {
        await precacheImage(
          AssetImage(c.imageAssetPath!.trim()),
          context,
        );
      } else if (c.networkImageUrl != null &&
          c.networkImageUrl!.trim().isNotEmpty) {
        // Ne pas attendre le réseau pour débloquer _mediaReady : sinon le fondu
        // image et les timings restent coincés derrière precacheImage (jank / image « absente »).
        if (mounted) _setMediaReady();
        try {
          await precacheImage(
            CachedNetworkImageProvider(c.networkImageUrl!.trim()),
            context,
          ).timeout(const Duration(seconds: 5));
        } catch (_) {}
        return;
      }
    } catch (_) {
      // L’image affichera l’erreur si besoin.
    }
    if (mounted) _setMediaReady();
  }

  void _setMediaReady() {
    if (_mediaReady) return;
    _mediaReady = true;
    if (mounted) setState(() {});
    _tryStartLogoTransition();
  }

  @override
  void didUpdateWidget(covariant BrandHeroIntroPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.config.bootstrapPending && !widget.config.bootstrapPending) {
      if (!_c.skipIntro) {
        _startIntroAfterSplash();
        _scheduleAppWarmupIfNeeded();
      }
    }
    if (oldWidget.config.pendingMediaResolution &&
        !widget.config.pendingMediaResolution) {
      _prepareMedia();
    }
    if (_logoTransitionStarted) {
      if (oldWidget.config.networkImageUrl != widget.config.networkImageUrl) {
        setState(() {});
      }
      return;
    }
    if (oldWidget.config.networkImageUrl != widget.config.networkImageUrl ||
        oldWidget.config.imageAssetPath != widget.config.imageAssetPath ||
        oldWidget.config.useHeroVideo != widget.config.useHeroVideo ||
        oldWidget.config.heroVideoAssetPath != widget.config.heroVideoAssetPath ||
        oldWidget.config.networkHeroVideoUrl != widget.config.networkHeroVideoUrl) {
      _videoController?.dispose();
      _videoController = null;
      _mediaReady = false;
      if (!widget.config.pendingMediaResolution) {
        _prepareMedia();
      }
    }
  }

  void _tryStartLogoTransition() {
    if (_c.skipIntro) return;
    if (_c.bootstrapPending) return;
    if (_logoTransitionStarted) return;
    if (!_minSplashElapsed) return;
    _logoTransitionStarted = true;
    _introMasterController.forward();
  }

  void _skipToEnd() {
    if (!_c.skipIntroOnTap) return;
    if (_c.skipIntro) return;
    if (_controlsFadeController.value > 0) return;
    _splashTimer?.cancel();
    _controlsDelayTimer?.cancel();
    _controlsDelayScheduled = true;
    _skipIntroTapActive = false;
    _minSplashElapsed = true;
    _mediaReady = true;
    _logoTransitionStarted = true;
    _introMasterController.value = 1;
    _controlsFadeController.value = 1;
    setState(() {});
  }

  @override
  void dispose() {
    _splashTimer?.cancel();
    _controlsDelayTimer?.cancel();
    _introMasterController.removeListener(_onIntroMasterTick);
    _introMasterController.dispose();
    _controlsFadeController.dispose();
    _videoController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final heroOverlay = widget.systemUiOverlayStyle ??
        SystemUiOverlayStyle.light.copyWith(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.light,
        );
    final splashOverlay = SystemUiOverlayStyle.dark.copyWith(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    );

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: _useHeroChromeOverlay ? heroOverlay : splashOverlay,
      child: Scaffold(
        backgroundColor: _c.splashBackgroundColor,
        extendBodyBehindAppBar: true,
        body: LayoutBuilder(
          builder: (context, constraints) {
            final screenW = MediaQuery.sizeOf(context).width;
            // Même fraction 0,5 × largeur que LaunchScreen iOS — sans arrondi DPR pour
            // éviter tout écart de taille / position au premier frame (continuité avec le splash natif).
            final logoW = _c.logoLayoutWidth(screenW);
            final logoH = logoW / HeroIntroMotion.logoSvgViewBoxAspect;
            final screenH = MediaQuery.sizeOf(context).height;
            final padTop = MediaQuery.paddingOf(context).top;
            // Aligné sur LaunchScreen.storyboard : centre vertical de la vue plein écran
            // (pas seulement la zone « body » sous la safe area).
            final startCenterY = screenH / 2;
            final endCenterY = padTop +
                HeroIntroMotion.logoFinalOffsetBelowSafeTop +
                logoH / 2;
            final dyTotal = endCenterY - startCenterY;
            final shrinkTop =
                constraints.maxHeight < screenH - 0.5;

            return Stack(
              fit: StackFit.expand,
              clipBehavior: Clip.none,
              children: [
                ColoredBox(color: _c.splashBackgroundColor),
                if (!_c.bootstrapPending) ...[
                  RepaintBoundary(
                    child: _buildHeroMediaLayer(),
                  ),
                  _buildBlackDimLayer(),
                ],
                _buildLogoLayer(
                  dyTotal: dyTotal,
                  logoWidthLogical: logoW,
                  screenHeight: screenH,
                  logoLayerTop: shrinkTop ? -padTop : 0.0,
                ),
                if (_c.skipIntroOnTap && _skipIntroTapActive)
                  Positioned.fill(
                    child: GestureDetector(
                      behavior: HitTestBehavior.translucent,
                      onTap: _skipToEnd,
                    ),
                  ),
                _buildChromeAlways(context),
              ],
            );
          },
        ),
      ),
    );
  }

  /// Même enveloppe d’opacité que l’image : [_mediaOpacity] / contrôleur maître.
  Widget _buildHeroMediaLayer() {
    return AnimatedBuilder(
      animation: _introMasterController,
      builder: (context, _) {
        return Opacity(
          opacity: _effectiveMediaOpacity,
          child: Stack(
            fit: StackFit.expand,
            children: [
              if (_c.posterAssetPath != null &&
                  _c.posterAssetPath!.trim().isNotEmpty)
                Image.asset(
                  _c.posterAssetPath!.trim(),
                  fit: BoxFit.cover,
                ),
              if (_c.useHeroVideoLayer &&
                  _videoController != null &&
                  _videoController!.value.isInitialized)
                Positioned.fill(
                  child: HeroIntroVideoFill(controller: _videoController!),
                )
              else ...[
                if (_c.imageAssetPath != null &&
                    _c.imageAssetPath!.trim().isNotEmpty)
                  Image.asset(
                    _c.imageAssetPath!.trim(),
                    fit: BoxFit.cover,
                    width: double.infinity,
                    height: double.infinity,
                  )
                else if (_c.networkImageUrl != null &&
                    _c.networkImageUrl!.trim().isNotEmpty)
                  CachedNetworkImage(
                    imageUrl: _c.networkImageUrl!.trim(),
                    fit: BoxFit.cover,
                    width: double.infinity,
                    height: double.infinity,
                    fadeInDuration: Duration.zero,
                    fadeOutDuration: Duration.zero,
                    placeholder: (_, __) => const SizedBox.shrink(),
                    errorWidget: (_, __, ___) => const SizedBox.shrink(),
                  ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildBlackDimLayer() {
    if (_c.heroDimOverlayMaxOpacity <= 0) {
      return const SizedBox.shrink();
    }
    return AnimatedBuilder(
      animation: _introMasterController,
      builder: (context, _) {
        final a = HeroIntroMotion.accordionDimOpacityScaled(
          _introMasterController.value,
          _c.heroDimOverlayMaxOpacity,
        );
        return IgnorePointer(
          child: ColoredBox(
            color: Color.fromRGBO(0, 0, 0, a),
          ),
        );
      },
    );
  }

  Widget _buildLogoLayer({
    required double dyTotal,
    required double logoWidthLogical,
    required double screenHeight,
    required double logoLayerTop,
  }) {
    return AnimatedBuilder(
      animation: _logoT,
      builder: (context, _) {
        final t = _logoT.value;
        final splashC = _c.logoColorSplash ?? const Color(0xFF000000);
        final heroC = _c.logoColorHero;
        final color = Color.lerp(splashC, heroC, t)!;

        return Positioned(
          left: 0,
          right: 0,
          top: logoLayerTop,
          height: screenHeight,
          child: Center(
            child: Transform.translate(
              offset: Offset(0, dyTotal * t),
              child: SplashBrandLogo(
                assetPath: _c.logoAssetPath,
                logoWidth: logoWidthLogical,
                color: color,
              ),
            ),
          ),
        );
      },
    );
  }

  /// Toujours dans l’arbre (opacité 0 au départ) pour éviter un gros [setState] qui recrée la pile.
  Widget _buildChromeAlways(BuildContext context) {
    return ListenableBuilder(
      listenable: _controlsFadeController,
      builder: (context, _) {
        final hidden = _controlsFadeController.value < 0.001;
        return Positioned.fill(
          child: IgnorePointer(
            ignoring: hidden,
            child: FadeTransition(
              opacity: _controlsOpacity,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  SafeArea(
                    bottom: false,
                    child: Padding(
                      padding:
                          const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          widget.leading ?? const SizedBox.shrink(),
                          const Spacer(),
                          if (widget.trailing != null) widget.trailing!,
                        ],
                      ),
                    ),
                  ),
                  SafeArea(
                    top: false,
                    child: Align(
                      alignment: Alignment.bottomCenter,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(
                          AppSpacing.lg,
                          0,
                          AppSpacing.lg,
                          AppSpacing.lg,
                        ),
                        child: widget.bottom,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
