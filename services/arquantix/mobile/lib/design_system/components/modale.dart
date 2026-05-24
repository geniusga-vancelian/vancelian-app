import 'dart:async';

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import '../atoms/kalai_icons.dart';
import 'app_primary_button.dart';
import 'bottom_sheet_container.dart';
import 'kalai_icon.dart';
import 'sheet_title_bar.dart';

class ModaleIconConfig {
  final IconData icon;
  final Color iconColor;
  final Color circleColor;
  final double size;

  const ModaleIconConfig({
    required this.icon,
    this.iconColor = Colors.white,
    this.circleColor = Colors.black,
    this.size = 64,
  });
}

class ModaleListRow {
  final String label;
  final VoidCallback? onTap;
  final bool showChevron;

  const ModaleListRow({
    required this.label,
    this.onTap,
    this.showChevron = true,
  });
}

class ModaleButtonConfig {
  final String label;
  final VoidCallback? onTap;
  /// Si fourni, exécuté **avant** fermeture de la feuille (ex. persister des données).
  final Future<void> Function()? onTapAsync;
  final bool closeOnTap;

  /// Surcharge la variante DS du bouton (par défaut : `primary` pour le primaire,
  /// `gray` pour le secondaire).
  final AppPrimaryButtonVariant? variant;

  /// Icône / widget affiché **après** le libellé (chevron pour une action de redirection).
  final Widget? trailing;

  /// Surcharge la couleur du texte / contour (ex. ghost noir).
  final Color? foregroundColor;

  const ModaleButtonConfig({
    required this.label,
    this.onTap,
    this.onTapAsync,
    this.closeOnTap = true,
    this.variant,
    this.trailing,
    this.foregroundColor,
  });
}

/// Paramètres pour afficher une [Modale] (feuille flottante DS).
class ModaleParams {
  final String title;
  final String? description;
  final Widget? content;
  final ModaleIconConfig? icon;
  final List<ModaleListRow> rows;
  final ModaleButtonConfig? primaryButton;
  final ModaleButtonConfig? secondaryButton;

  const ModaleParams({
    required this.title,
    this.description,
    this.content,
    this.icon,
    this.rows = const [],
    this.primaryButton,
    this.secondaryButton,
  });
}

/// Hôte overlay : même gabarit que [TransactionErrorOverlay] (marges latérales,
/// hauteur au contenu, [BottomSheetContainer] + [SheetTitleBar] avec croix).
class _ModaleOverlayHost extends StatefulWidget {
  const _ModaleOverlayHost({
    required this.params,
    required this.onRemoveEntry,
  });

  final ModaleParams params;
  final VoidCallback onRemoveEntry;

  @override
  State<_ModaleOverlayHost> createState() => _ModaleOverlayHostState();
}

class _ModaleOverlayHostState extends State<_ModaleOverlayHost>
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

  Future<void> _closeSheet() async {
    await animateDismiss();
    widget.onRemoveEntry();
  }

  Future<void> _onButtonTap(ModaleButtonConfig config) async {
    if (config.closeOnTap) {
      if (config.onTapAsync != null) {
        await config.onTapAsync!();
      }
      await _closeSheet();
      config.onTap?.call();
    } else {
      if (config.onTapAsync != null) {
        await config.onTapAsync!();
      }
      config.onTap?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.params;
    final showTitle = p.title.trim().isNotEmpty;
    final hasDescription = (p.description ?? '').trim().isNotEmpty;
    final hasContent = p.content != null;
    final hasRows = p.rows.isNotEmpty;
    final hasPrimary = p.primaryButton != null;
    final hasSecondary = p.secondaryButton != null;
    final maxScrollH = MediaQuery.sizeOf(context).height * 0.42;

    final bodyChildren = <Widget>[];

    if (p.icon != null) {
      bodyChildren.add(
        Center(
          child: Container(
            width: p.icon!.size,
            height: p.icon!.size,
            decoration: BoxDecoration(
              color: p.icon!.circleColor,
              shape: BoxShape.circle,
            ),
            child: Icon(
              p.icon!.icon,
              color: p.icon!.iconColor,
              size: p.icon!.size * 0.55,
            ),
          ),
        ),
      );
    }

    if (hasContent) {
      bodyChildren.add(
        ConstrainedBox(
          constraints: BoxConstraints(maxHeight: maxScrollH),
          child: SingleChildScrollView(
            physics: const ClampingScrollPhysics(),
            child: p.content!,
          ),
        ),
      );
    }

    if (hasDescription) {
      bodyChildren.add(
        Text(
          p.description!.trim(),
          textAlign: TextAlign.center,
          style: AppTypography.meta.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      );
    }

    if (hasRows) {
      bodyChildren.add(
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: p.rows
              .map(
                (row) => Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: row.onTap == null
                        ? null
                        : () async {
                            await _closeSheet();
                            row.onTap!();
                          },
                    borderRadius: BorderRadius.circular(8),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              row.label,
                              style: AppTypography.titleSmall.copyWith(
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                          if (row.showChevron)
                            const KalaiIcon(
                              KalaiIcons.chevronRight,
                              size: 16,
                              color: AppColors.textSecondary,
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
        ),
      );
    }

    if (hasPrimary && hasSecondary) {
      bodyChildren.add(
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            FractionallySizedBox(
              widthFactor: 0.75,
              child: AppPrimaryButton(
                label: p.primaryButton!.label,
                variant: p.primaryButton!.variant ??
                    AppPrimaryButtonVariant.primary,
                shrinkWrap: true,
                trailing: p.primaryButton!.trailing,
                foregroundColor: p.primaryButton!.foregroundColor,
                onPressed: () => _onButtonTap(p.primaryButton!),
              ),
            ),
            const SizedBox(height: AppSpacing.s2),
            FractionallySizedBox(
              widthFactor: 0.75,
              child: AppPrimaryButton(
                label: p.secondaryButton!.label,
                variant: p.secondaryButton!.variant ??
                    AppPrimaryButtonVariant.gray,
                shrinkWrap: true,
                trailing: p.secondaryButton!.trailing,
                foregroundColor: p.secondaryButton!.foregroundColor,
                onPressed: () => _onButtonTap(p.secondaryButton!),
              ),
            ),
          ],
        ),
      );
    } else if (hasPrimary) {
      bodyChildren.add(
        FractionallySizedBox(
          widthFactor: 0.75,
          child: AppPrimaryButton(
            label: p.primaryButton!.label,
            variant: p.primaryButton!.variant ??
                AppPrimaryButtonVariant.gray,
            shrinkWrap: true,
            trailing: p.primaryButton!.trailing,
            foregroundColor: p.primaryButton!.foregroundColor,
            onPressed: () => _onButtonTap(p.primaryButton!),
          ),
        ),
      );
    } else if (hasSecondary) {
      bodyChildren.add(
        FractionallySizedBox(
          widthFactor: 0.75,
          child: AppPrimaryButton(
            label: p.secondaryButton!.label,
            variant:
                p.secondaryButton!.variant ?? AppPrimaryButtonVariant.gray,
            shrinkWrap: true,
            trailing: p.secondaryButton!.trailing,
            foregroundColor: p.secondaryButton!.foregroundColor,
            onPressed: () => _onButtonTap(p.secondaryButton!),
          ),
        ),
      );
    }

    return Material(
      color: Colors.transparent,
      child: Stack(
        children: [
          Positioned.fill(
            child: FadeTransition(
              opacity: _backdropOpacity,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: _closeSheet,
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
                  title: showTitle ? p.title.trim() : '',
                  leadingButton: SheetCircleButton.leading(
                    onTap: _closeSheet,
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

/// Modale du design system : feuille **flottante** (non full-width), hauteur au
/// contenu, poignée + barre avec croix comme l’erreur OTP / succès trade.
///
/// Ne plus utiliser `showModalBottomSheet` plein écran pour les nouveaux écrans.
class Modale {
  Modale._();

  static Future<T?> show<T>(BuildContext context, ModaleParams params) {
    final overlayState = Overlay.of(context);
    final completer = Completer<T?>();
    late OverlayEntry entry;
    var removed = false;

    void finish() {
      if (removed) return;
      removed = true;
      entry.remove();
      if (!completer.isCompleted) {
        completer.complete(null);
      }
    }

    entry = OverlayEntry(
      builder: (_) => _ModaleOverlayHost(
        params: params,
        onRemoveEntry: finish,
      ),
    );
    overlayState.insert(entry);
    return completer.future;
  }
}
