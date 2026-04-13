import 'dart:async';

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_primary_button.dart';
import 'bottom_sheet_container.dart';

/// Bulle centrée + fond assombri, **fade-in rapide** (pas de slide depuis le bas).
///
/// Gabarit proche des feuilles [Modale] / [TransactionErrorOverlay] : même backdrop,
/// [AppTypography.modalTitle], [AppPrimaryButton], marges [kFloatingSheetHorizontalInset].
///
/// Usage : erreurs courtes (ex. OTP incorrect) sans [SnackBar].
class CenterBubbleOverlay extends StatefulWidget {
  const CenterBubbleOverlay({
    super.key,
    required this.title,
    required this.message,
    required this.onClose,
    this.primaryLabel = 'OK',
    this.secondaryLabel,
    this.onSecondary,
  });

  final String title;
  final String message;
  final VoidCallback onClose;
  final String primaryLabel;
  final String? secondaryLabel;
  final VoidCallback? onSecondary;

  @override
  State<CenterBubbleOverlay> createState() => CenterBubbleOverlayState();
}

class CenterBubbleOverlayState extends State<CenterBubbleOverlay>
    with SingleTickerProviderStateMixin {
  static const Duration _fadeIn = Duration(milliseconds: 200);
  static const Duration _fadeOut = Duration(milliseconds: 160);

  /// Rayon proche des feuilles DS (32px haut) / ref. bulle centrée.
  static const double _bubbleRadius = 28;

  late final AnimationController _ctrl;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: _fadeIn,
      reverseDuration: _fadeOut,
    );
    _opacity = CurvedAnimation(parent: _ctrl, curve: Curves.easeOut);
    _ctrl.forward();
  }

  Future<void> animateDismiss() async {
    await _ctrl.reverse();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Positioned.fill(
            child: FadeTransition(
              opacity: _opacity,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: widget.onClose,
                child: ColoredBox(
                  color: Colors.black.withValues(alpha: 0.5),
                ),
              ),
            ),
          ),
          FadeTransition(
            opacity: _opacity,
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: kFloatingSheetHorizontalInset + AppSpacing.sm,
              ),
              child: Material(
                color: AppColors.cardBackground,
                elevation: 8,
                shadowColor: Colors.black26,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(_bubbleRadius),
                ),
                clipBehavior: Clip.antiAlias,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpacing.lg,
                    AppSpacing.xl,
                    AppSpacing.lg,
                    AppSpacing.lg,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        widget.title,
                        textAlign: TextAlign.center,
                        style: AppTypography.modalTitle.copyWith(
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        widget.message,
                        textAlign: TextAlign.center,
                        style: AppTypography.meta.copyWith(
                          color: AppColors.textSecondary,
                          height: 22 / 15,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xl),
                      AppPrimaryButton(
                        label: widget.primaryLabel,
                        size: AppPrimaryButtonSize.large,
                        onPressed: widget.onClose,
                      ),
                      if (widget.secondaryLabel != null &&
                          widget.secondaryLabel!.isNotEmpty &&
                          widget.onSecondary != null) ...[
                        const SizedBox(height: AppSpacing.sm),
                        AppPrimaryButton(
                          label: widget.secondaryLabel!,
                          variant: AppPrimaryButtonVariant.ghost,
                          size: AppPrimaryButtonSize.medium,
                          onPressed: () {
                            widget.onSecondary!();
                            widget.onClose();
                          },
                        ),
                      ],
                    ],
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

/// Affiche une bulle centrée (fade rapide). Fermeture : [primaryLabel], secondaire, ou tap fond.
Future<void> showCenterBubbleOverlay({
  required BuildContext context,
  required String title,
  required String message,
  String primaryLabel = 'OK',
  String? secondaryLabel,
  VoidCallback? onSecondary,
}) {
  final completer = Completer<void>();
  final overlayState = Overlay.of(context);
  final overlayKey = GlobalKey<CenterBubbleOverlayState>();
  late final OverlayEntry entry;
  var didRemove = false;

  Future<void> closeAndRemove() async {
    if (didRemove) return;
    didRemove = true;
    await overlayKey.currentState?.animateDismiss();
    entry.remove();
    if (!completer.isCompleted) {
      completer.complete();
    }
  }

  entry = OverlayEntry(
    builder: (_) => CenterBubbleOverlay(
      key: overlayKey,
      title: title,
      message: message,
      primaryLabel: primaryLabel,
      secondaryLabel: secondaryLabel,
      onSecondary: onSecondary,
      onClose: () {
        closeAndRemove();
      },
    ),
  );
  overlayState.insert(entry);
  return completer.future;
}
