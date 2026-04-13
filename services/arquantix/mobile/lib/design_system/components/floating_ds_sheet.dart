import 'dart:async';

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'bottom_sheet_container.dart';
import 'sheet_title_bar.dart';

/// Feuille flottante DS : même gabarit que le succès swap / [Modale]
/// (backdrop, slide depuis le bas, [BottomSheetContainer] + [SheetTitleBar]),
/// **sans** icône de succès ni bloc montant — corps libre via [buildBody].
///
/// [buildBody] reçoit [pop] : appeler `pop(valeur)` ou `pop()` pour fermer avec résultat.
Future<T?> showFloatingDsSheet<T>({
  required BuildContext context,
  required String title,
  String? description,
  required List<Widget> Function(void Function([T? result]) pop) buildBody,
}) {
  final overlayState = Overlay.of(context);
  final completer = Completer<T?>();
  late OverlayEntry entry;
  var removed = false;

  void finish(T? result) {
    if (removed) return;
    removed = true;
    entry.remove();
    if (!completer.isCompleted) {
      completer.complete(result);
    }
  }

  entry = OverlayEntry(
    builder: (ctx) => _FloatingDsSheetHost<T>(
      title: title,
      description: description,
      buildBody: buildBody,
      onDismissed: finish,
    ),
  );
  overlayState.insert(entry);
  return completer.future;
}

class _FloatingDsSheetHost<T> extends StatefulWidget {
  const _FloatingDsSheetHost({
    super.key,
    required this.title,
    this.description,
    required this.buildBody,
    required this.onDismissed,
  });

  final String title;
  final String? description;
  final List<Widget> Function(void Function([T? result]) pop) buildBody;
  final void Function(T? result) onDismissed;

  @override
  State<_FloatingDsSheetHost<T>> createState() => _FloatingDsSheetHostState<T>();
}

class _FloatingDsSheetHostState<T> extends State<_FloatingDsSheetHost<T>>
    with SingleTickerProviderStateMixin {
  late final AnimationController _sheetCtrl;
  late final Animation<double> _backdropOpacity;
  late final Animation<Offset> _slideUp;
  bool _isClosing = false;

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

  Future<void> _popWithResult([T? result]) async {
    await animateDismiss();
    if (!mounted) return;
    widget.onDismissed(result);
  }

  void _requestPop([T? result]) {
    if (_isClosing) return;
    _isClosing = true;
    unawaited(_popWithResult(result));
  }

  @override
  Widget build(BuildContext context) {
    final desc = (widget.description ?? '').trim();
    final bodyChildren = <Widget>[
      if (desc.isNotEmpty)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text(
              desc,
              style: AppTypography.paragraph.copyWith(
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ),
        ),
      ...widget.buildBody(_requestPop),
    ];

    return Material(
      color: Colors.transparent,
      child: Stack(
        children: [
          Positioned.fill(
            child: FadeTransition(
              opacity: _backdropOpacity,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => _requestPop(null),
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
                    onTap: () => _requestPop(null),
                  ),
                ),
                children: bodyChildren,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
