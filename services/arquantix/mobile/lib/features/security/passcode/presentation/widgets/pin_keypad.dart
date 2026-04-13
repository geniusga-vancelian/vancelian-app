import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:google_fonts/google_fonts.dart';

import 'package:arquantix_news/design_system/assets/ds_raster_assets.dart';
import 'package:arquantix_news/design_system/atoms/app_colors.dart';
import 'package:arquantix_news/design_system/atoms/app_spacing.dart';
import '../../data/biometric_auth_service.dart';
import '../../data/passcode_service.dart';

class PinDotsRow extends StatelessWidget {
  const PinDotsRow({super.key, required this.filled});

  final int filled;

  @override
  Widget build(BuildContext context) {
    const n = PasscodeService.pinLength;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(n, (i) {
        final on = i < filled;
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: on ? AppColors.indigo : AppColors.textSecondary.withValues(alpha: 0.2),
              border: Border.all(
                color: AppColors.textSecondary.withValues(alpha: 0.35),
              ),
            ),
          ),
        );
      }),
    );
  }
}

/// Même gabarit que [PinDotsRow] : vague lumineuse sur les pastilles (chargement dashboard).
class PinDotsWaveLoadingRow extends StatefulWidget {
  const PinDotsWaveLoadingRow({super.key});

  @override
  State<PinDotsWaveLoadingRow> createState() => _PinDotsWaveLoadingRowState();
}

class _PinDotsWaveLoadingRowState extends State<PinDotsWaveLoadingRow>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const n = PasscodeService.pinLength;
    const dotSize = 12.0;
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final t = _controller.value;
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(n, (i) {
            final wave = (t * 2 * math.pi) - (i * 2 * math.pi / n);
            final pulse = (math.sin(wave) + 1) / 2;
            final opacity = 0.22 + 0.78 * pulse;
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6),
              child: Opacity(
                opacity: opacity.clamp(0.15, 1.0),
                child: Container(
                  width: dotSize,
                  height: dotSize,
                  decoration: BoxDecoration(
                    color: AppColors.indigo,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: AppColors.textSecondary.withValues(alpha: 0.35),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.indigo.withValues(alpha: 0.35),
                        blurRadius: 5,
                        spreadRadius: 0,
                      ),
                    ],
                  ),
                ),
              ),
            );
          }),
        );
      },
    );
  }
}

class NumericPinKeypad extends StatelessWidget {
  const NumericPinKeypad({
    super.key,
    required this.onDigit,
    required this.onBackspace,
    this.enabled = true,
    this.onBiometric,
    this.biometricIconKind,
    this.biometricEnabled = true,
  });

  final void Function(String d) onDigit;
  final VoidCallback onBackspace;
  final bool enabled;

  /// Si non null avec [biometricIconKind], affiche l’icône à gauche du « 0 ».
  final VoidCallback? onBiometric;
  final BiometricKeypadIconKind? biometricIconKind;
  final bool biometricEnabled;

  static const double _keySize = 76;

  @override
  Widget build(BuildContext context) {
    final digitStyle = GoogleFonts.inter(
      fontSize: 28,
      fontWeight: FontWeight.w500,
      height: 1,
      color: enabled
          ? AppColors.textPrimary
          : AppColors.textSecondary.withValues(alpha: 0.4),
    );

    Widget digitKey(String d) {
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: enabled ? () => onDigit(d) : null,
          customBorder: const CircleBorder(),
          child: Ink(
            width: _keySize,
            height: _keySize,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.textPrimary.withValues(alpha: 0.06),
            ),
            child: Center(
              child: Text(d, style: digitStyle),
            ),
          ),
        ),
      );
    }

    Widget backspaceKey() {
      final backColor = enabled
          ? AppColors.textPrimary
          : AppColors.textSecondary.withValues(alpha: 0.4);
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: enabled ? onBackspace : null,
          customBorder: const CircleBorder(),
          child: SizedBox(
            width: _keySize,
            height: _keySize,
            child: Center(
              child: SvgPicture.asset(
                DsRasterAssets.keypadBackspace,
                width: 28,
                height: 28,
                fit: BoxFit.contain,
                colorFilter: ColorFilter.mode(backColor, BlendMode.srcIn),
              ),
            ),
          ),
        ),
      );
    }

    Widget biometricKey() {
      final kind = biometricIconKind;
      final show = onBiometric != null && kind != null;
      if (!show) {
        return const SizedBox(width: _keySize, height: _keySize);
      }
      final bioOk = enabled && biometricEnabled;
      final semanticLabel = kind == BiometricKeypadIconKind.face
          ? 'Déverrouiller avec Face ID'
          : 'Déverrouiller avec empreinte';
      final iconColor = bioOk
          ? AppColors.textPrimary
          : AppColors.textSecondary.withValues(alpha: 0.4);
      // Même gabarit que backspaceKey : pas de disque (contrairement aux touches chiffres).
      final Widget iconChild = kind == BiometricKeypadIconKind.face
          ? SvgPicture.asset(
              DsRasterAssets.faceIdSymbol,
              width: 40,
              height: 40,
              fit: BoxFit.contain,
              colorFilter: ColorFilter.mode(iconColor, BlendMode.srcIn),
            )
          : Icon(
              Icons.fingerprint_rounded,
              size: 44,
              color: iconColor,
            );
      return Semantics(
        button: true,
        label: semanticLabel,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: bioOk ? onBiometric : null,
            customBorder: const CircleBorder(),
            child: SizedBox(
              width: _keySize,
              height: _keySize,
              child: Center(child: iconChild),
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final row in [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
          ])
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: row.map(digitKey).toList(),
              ),
            ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              biometricKey(),
              digitKey('0'),
              backspaceKey(),
            ],
          ),
        ],
      ),
    );
  }
}
