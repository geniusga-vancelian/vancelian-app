import 'dart:async';

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_typography.dart';
import 'app_primary_button.dart';
import 'bottom_sheet_container.dart';
import 'sheet_title_bar.dart';

/// Full-screen overlay with animated backdrop + floating success sheet.
/// Tap sur la zone grise (backdrop) déclenche [onClose] comme une modale classique.
///
/// Designed to sit above the [Navigator] via an [OverlayEntry] so the
/// background screen can pop while the overlay remains visible on top.
///
/// Uses [BottomSheetContainer] + [SheetTitleBar] from the DS.
///
/// Use [showTransactionSuccessOverlay] for the standard timing flow.
class TransactionSuccessOverlay extends StatefulWidget {
  const TransactionSuccessOverlay({
    super.key,
    required this.title,
    required this.amount,
    required this.subtitle,
    this.detail,
    this.caption,
    this.onClose,
    this.leadingAction,
    this.trailingAction,
    this.buttonLabel = 'Close',
  });

  final String title;
  final String amount;
  final String subtitle;
  final String? detail;

  /// Optional caption displayed above the amount (e.g. "Achat effectué").
  /// Figma spec: 17px, w600, #8E8E93.
  final String? caption;

  final VoidCallback? onClose;

  /// Circle button on the left of the [SheetTitleBar].
  final Widget? leadingAction;

  /// Circle button on the right of the [SheetTitleBar].
  final Widget? trailingAction;

  /// Label for the bottom action button.
  final String buttonLabel;

  @override
  State<TransactionSuccessOverlay> createState() =>
      TransactionSuccessOverlayState();
}

class TransactionSuccessOverlayState extends State<TransactionSuccessOverlay>
    with TickerProviderStateMixin {
  static const _overlayDuration = Duration(milliseconds: 3500);

  late final AnimationController _sheetCtrl;
  late final Animation<double> _backdropOpacity;
  late final Animation<Offset> _slideUp;
  late final AnimationController _progressCtrl;

  @override
  void initState() {
    super.initState();
    _sheetCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
      reverseDuration: const Duration(milliseconds: 350),
    );
    _backdropOpacity =
        CurvedAnimation(parent: _sheetCtrl, curve: Curves.easeOut);
    _slideUp = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _sheetCtrl, curve: Curves.easeOutCubic));

    _progressCtrl =
        AnimationController(vsync: this, duration: _overlayDuration);

    _sheetCtrl.forward();
    _progressCtrl.forward();
  }

  /// Animate the sheet slide-down + backdrop fade-out before removal.
  Future<void> animateDismiss() async {
    await _sheetCtrl.reverse();
  }

  @override
  void dispose() {
    _sheetCtrl.dispose();
    _progressCtrl.dispose();
    super.dispose();
  }

  // ── Figma caption style: 17px / w600 / #8E8E93 ──

  static const _captionStyle = TextStyle(
    fontFamily: 'Inter',
    fontSize: 17,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.43,
    height: 22 / 17,
    color: Color(0xFF8E8E93),
  );

  // ── Build ──

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Stack(
        children: [
          Positioned.fill(
            child: FadeTransition(
              opacity: _backdropOpacity,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: widget.onClose,
                child: ColoredBox(
                  color: Colors.black.withValues(alpha: 0.5),
                ),
              ),
            ),
          ),
          Positioned(
            left: kFloatingSheetHorizontalInset,
            right: kFloatingSheetHorizontalInset,
            bottom: kFloatingSheetBottomInset,
            child: SlideTransition(
              position: _slideUp,
              child: _buildSheet(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSheet() {
    return BottomSheetContainer(
      toolbar: SheetTitleBar(
        title: widget.title,
        leadingButton: widget.leadingAction ??
            SheetCircleButton.leading(onTap: widget.onClose),
        trailingButton: widget.trailingAction,
      ),
      children: [
        if (widget.caption != null)
          Text(
            widget.caption!,
            textAlign: TextAlign.center,
            style: _captionStyle,
          ),
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              widget.amount,
              textAlign: TextAlign.center,
              style: AppTypography.heroAmount.copyWith(
                fontSize: 34,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              widget.subtitle,
              textAlign: TextAlign.center,
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textPrimary,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (widget.detail != null) ...[
              const SizedBox(height: 2),
              Text(
                widget.detail!,
                textAlign: TextAlign.center,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textPrimary,
                  fontSize: 13,
                ),
              ),
            ],
          ],
        ),
        FractionallySizedBox(
          widthFactor: 0.75,
          child: AppPrimaryButton(
            label: widget.buttonLabel,
            variant: AppPrimaryButtonVariant.gray,
            onPressed: widget.onClose,
          ),
        ),
      ],
    );
  }
}

/// Shows a [TransactionSuccessOverlay] with the standard timing flow:
///
/// 1. Overlay appears (slide-up + backdrop fade-in)
/// 2. After [initialDelay] (1s), the confirmation screen pops via [onNavigateAway]
///    or the default `Navigator.pop(true)`.
/// 3. After [dismissDelay] (2.5s), the overlay auto-dismisses
///
/// Use [onNavigateAway] to redirect to a specific screen instead of just
/// popping back through the flow stack. The callback receives the
/// [NavigatorState] so it can `popUntil` + `push` the target destination.
Future<void> showTransactionSuccessOverlay({
  required BuildContext context,
  required String title,
  required String amount,
  required String subtitle,
  String? detail,
  String? caption,
  String buttonLabel = 'Close',
  Duration initialDelay = const Duration(milliseconds: 1000),
  Duration dismissDelay = const Duration(milliseconds: 2500),
  void Function(NavigatorState nav)? onNavigateAway,
}) async {
  final overlay = Overlay.of(context);
  final nav = Navigator.of(context);
  final overlayKey = GlobalKey<TransactionSuccessOverlayState>();

  late final OverlayEntry entry;
  entry = OverlayEntry(
    builder: (_) => TransactionSuccessOverlay(
      key: overlayKey,
      title: title,
      amount: amount,
      subtitle: subtitle,
      detail: detail,
      caption: caption,
      buttonLabel: buttonLabel,
      onClose: () async {
        await overlayKey.currentState?.animateDismiss();
        entry.remove();
      },
    ),
  );
  overlay.insert(entry);

  await Future.delayed(initialDelay);

  if (onNavigateAway != null) {
    onNavigateAway(nav);
  } else if (nav.mounted) {
    nav.pop(true);
  }

  await Future.delayed(dismissDelay);
  await overlayKey.currentState?.animateDismiss();
  entry.remove();
}

// ── Floating error sheet (même gabarit que le succès trade / achat crypto) ──

/// Overlay feuille flottante + backdrop, comme [TransactionSuccessOverlay],
/// avec icône d’erreur centrale (cercle rouge + croix). Fermeture : bouton, croix,
/// ou tap sur le fond gris ([onClose]).
class TransactionErrorOverlay extends StatefulWidget {
  const TransactionErrorOverlay({
    super.key,
    required this.title,
    required this.message,
    required this.onClose,
    this.buttonLabel = 'Got it',
  });

  final String title;
  final String message;
  final VoidCallback onClose;
  final String buttonLabel;

  @override
  State<TransactionErrorOverlay> createState() =>
      TransactionErrorOverlayState();
}

class TransactionErrorOverlayState extends State<TransactionErrorOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _sheetCtrl;
  late final Animation<double> _backdropOpacity;
  late final Animation<Offset> _slideUp;

  @override
  void initState() {
    super.initState();
    _sheetCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
      reverseDuration: const Duration(milliseconds: 350),
    );
    _backdropOpacity =
        CurvedAnimation(parent: _sheetCtrl, curve: Curves.easeOut);
    _slideUp = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _sheetCtrl, curve: Curves.easeOutCubic));
    _sheetCtrl.forward();
  }

  Future<void> animateDismiss() async {
    await _sheetCtrl.reverse();
  }

  @override
  void dispose() {
    _sheetCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Stack(
        children: [
          Positioned.fill(
            child: FadeTransition(
              opacity: _backdropOpacity,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: widget.onClose,
                child: ColoredBox(
                  color: Colors.black.withValues(alpha: 0.5),
                ),
              ),
            ),
          ),
          Positioned(
            left: kFloatingSheetHorizontalInset,
            right: kFloatingSheetHorizontalInset,
            bottom: kFloatingSheetBottomInset,
            child: SlideTransition(
              position: _slideUp,
              child: BottomSheetContainer(
                toolbar: SheetTitleBar(
                  title: widget.title,
                  leadingButton: SheetCircleButton.leading(
                    onTap: widget.onClose,
                  ),
                ),
                children: [
                  Center(
                    child: Container(
                      width: 64,
                      height: 64,
                      decoration: const BoxDecoration(
                        color: AppColors.semanticDanger,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.close_rounded,
                        color: Colors.white,
                        size: 36,
                      ),
                    ),
                  ),
                  Text(
                    widget.message,
                    textAlign: TextAlign.center,
                    style: AppTypography.meta.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  FractionallySizedBox(
                    widthFactor: 0.75,
                    child: AppPrimaryButton(
                      label: widget.buttonLabel,
                      variant: AppPrimaryButtonVariant.gray,
                      onPressed: widget.onClose,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Affiche la même feuille flottante que le succès d’achat / trade ; fermeture au tap
/// (croix, bouton, ou backdrop gris), sans navigation automatique.
Future<void> showTransactionErrorOverlay({
  required BuildContext context,
  required String title,
  required String message,
  String buttonLabel = 'Got it',
}) {
  final completer = Completer<void>();
  final overlayState = Overlay.of(context);
  final overlayKey = GlobalKey<TransactionErrorOverlayState>();
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
    builder: (_) => TransactionErrorOverlay(
      key: overlayKey,
      title: title,
      message: message,
      buttonLabel: buttonLabel,
      onClose: () => closeAndRemove(),
    ),
  );
  overlayState.insert(entry);
  return completer.future;
}
