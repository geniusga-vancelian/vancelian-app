import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:google_fonts/google_fonts.dart';

import '../assets/ds_raster_assets.dart';
import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import '../atoms/kalai_icons.dart';
import 'kalai_icon.dart';

/// Symbole Face ID (SVG Figma) — teinte [AppColors.indigo].
class DsFaceIdSymbol extends StatelessWidget {
  const DsFaceIdSymbol({super.key, this.size = 70});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SvgPicture.asset(
      DsRasterAssets.faceIdSymbol,
      width: size,
      height: size,
      fit: BoxFit.contain,
      colorFilter: const ColorFilter.mode(AppColors.indigo, BlendMode.srcIn),
    );
  }
}

/// Zone héros 190px : cadre blanc arrondi + ombre violette, symbole centré.
///
/// Pour les **notifications** (ou autre visuel), passez [symbol] (ex. grande [Image]
/// ou [Icon]) à la place du Face ID par défaut.
class DsPermissionHero extends StatelessWidget {
  const DsPermissionHero({
    super.key,
    this.symbol,
    this.heroHeight = 190,
    this.bezelSize = 151,
    this.symbolSize = 70,
  });

  final Widget? symbol;
  final double heroHeight;
  final double bezelSize;
  final double symbolSize;

  static const BoxShadow _bezelShadow = BoxShadow(
    color: Color(0x336155F5),
    offset: Offset(0, 12),
    blurRadius: 70,
  );

  @override
  Widget build(BuildContext context) {
    final effective = symbol ?? DsFaceIdSymbol(size: symbolSize);
    return ClipRect(
      child: SizedBox(
        height: heroHeight,
        width: double.infinity,
        child: Stack(
          clipBehavior: Clip.none,
          alignment: Alignment.topCenter,
          children: [
            Positioned(
              top: 10,
              child: Container(
                width: bezelSize,
                height: bezelSize,
                decoration: BoxDecoration(
                  color: AppColors.white,
                  borderRadius: BorderRadius.circular(32),
                  boxShadow: const [_bezelShadow],
                ),
              ),
            ),
            Positioned(
              top: 50.5,
              child: SizedBox(
                width: symbolSize,
                height: symbolSize,
                child: effective,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Barre de statut décorative type iOS (ZIP `StatusBar.tsx`) — démo / maquettes DS.
class DsIosStatusBarPlaceholder extends StatelessWidget {
  const DsIosStatusBarPlaceholder({super.key, this.time = '9:41'});

  final String time;

  @override
  Widget build(BuildContext context) {
    final timeStyle = GoogleFonts.inter(
      fontSize: 17,
      fontWeight: FontWeight.w600,
      height: 22 / 17,
      color: AppColors.black,
    );
    return Container(
      width: double.infinity,
      color: AppColors.iosChromeBackground,
      child: Align(
        alignment: Alignment.center,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 375),
          child: SizedBox(
            height: 54,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Row(
                children: [
                  SizedBox(
                    width: 98,
                    child: Text(time, textAlign: TextAlign.center, style: timeStyle),
                  ),
                  const Spacer(),
                  const KalaiIcon(KalaiIcons.signal, size: 18, color: AppColors.black),
                  const SizedBox(width: 6),
                  const KalaiIcon(KalaiIcons.wifi, size: 18, color: AppColors.black),
                  const SizedBox(width: 6),
                  const KalaiIcon(KalaiIcons.battery, size: 22, color: AppColors.black),
                  const SizedBox(width: 8),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Gabarit type écran permission : héros, titre, corps, deux actions en bas.
///
/// - [showStatusBar] : **false** par défaut — la barre décorative Figma (9:41) ne doit pas
///   se superposer à la vraie status bar sur device.
/// - Avec une hauteur **bornée** (écran plein) : bloc héros + textes **centrés verticalement**
///   dans la zone disponible ; boutons **collés en bas** (safe area gérée par le parent).
/// - Avec contrainte **non bornée** (ex. dans un [CustomScrollView]) : colonne intrinsèque,
///   [minContentHeight] évite un bloc trop plat.
///
/// Réutilise [AppTypography.headerPrimary] et [AppTypography.bodyRegular] (pas de doublon typo).
class DsPermissionPromptLayout extends StatelessWidget {
  const DsPermissionPromptLayout({
    super.key,
    required this.title,
    required this.body,
    required this.primaryButton,
    required this.secondaryButton,
    this.hero,
    this.showStatusBar = false,
    this.minContentHeight = 280,
  });

  final String title;
  final String body;
  final Widget primaryButton;
  final Widget secondaryButton;
  final Widget? hero;
  final bool showStatusBar;
  final double minContentHeight;

  Widget _buildTextBlock() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        hero ?? const DsPermissionHero(),
        const SizedBox(height: AppSpacing.sm),
        Text(
          title,
          textAlign: TextAlign.center,
          style: AppTypography.headerPrimary,
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          body,
          textAlign: TextAlign.center,
          style: AppTypography.bodyRegular.copyWith(
            color: AppColors.textMuted,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.paddingOf(context).bottom;

    return LayoutBuilder(
      builder: (context, constraints) {
        final maxH = constraints.maxHeight;
        final bounded = maxH.isFinite;

        final buttons = Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            primaryButton,
            const SizedBox(height: AppSpacing.sm),
            secondaryButton,
          ],
        );

        if (!bounded) {
          return ColoredBox(
            color: AppColors.iosChromeBackground,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.pageEdge,
                0,
                AppSpacing.pageEdge,
                AppSpacing.xl,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (showStatusBar) const DsIosStatusBarPlaceholder(),
                  ConstrainedBox(
                    constraints: BoxConstraints(minHeight: minContentHeight),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [_buildTextBlock()],
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xxl),
                  buttons,
                ],
              ),
            ),
          );
        }

        return ColoredBox(
          color: AppColors.iosChromeBackground,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.pageEdge,
              0,
              AppSpacing.pageEdge,
              0,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (showStatusBar) const DsIosStatusBarPlaceholder(),
                Expanded(
                  child: Center(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                      child: _buildTextBlock(),
                    ),
                  ),
                ),
                Padding(
                  padding: EdgeInsets.only(
                    top: AppSpacing.md,
                    bottom: AppSpacing.lg + bottomInset,
                  ),
                  child: buttons,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
