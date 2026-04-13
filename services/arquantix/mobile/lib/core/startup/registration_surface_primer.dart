import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../design_system/atoms/app_colors.dart';
import '../../design_system/components/app_text_input.dart';
import '../ui/form_selection_rows.dart';

/// Peint **une fois** hors écran les surfaces les plus coûteuses au premier contact
/// dans le flux d’inscription : [FormRadioRow] (GestureDetector + radio custom) et
/// [AppTextInput] (TextField + labels animés + plusieurs tailles Inter).
///
/// Complète [FirstFrameInteractionPrimer] (feuille DS) sans dupliquer tout un écran.
class RegistrationSurfacePrimer {
  RegistrationSurfacePrimer._();

  static bool _done = false;

  static Future<void> prime(BuildContext context) => _primeImpl(context, 0);

  static Future<void> _primeImpl(BuildContext context, int overlayAttempt) async {
    if (_done) return;
    if (kIsWeb) {
      _done = true;
      return;
    }
    if (!context.mounted) return;
    final overlay = Overlay.maybeOf(context, rootOverlay: true);
    if (overlay == null) {
      if (overlayAttempt < 6 && context.mounted) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          unawaited(_primeImpl(context, overlayAttempt + 1));
        });
      }
      return;
    }

    final width = MediaQuery.sizeOf(context).width;

    late OverlayEntry entry;
    entry = OverlayEntry(
      builder: (_) => Positioned(
        left: -8000,
        top: 0,
        child: IgnorePointer(
          child: Opacity(
            opacity: 0,
            child: RepaintBoundary(
              child: SizedBox(
                width: width,
                height: 720,
                child: Material(
                  color: AppColors.pageBackground,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Gabarit proche de SelectableSingleList + FormRadioRow
                        DecoratedBox(
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.06),
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(2),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                FormRadioRow(
                                  label: ' ',
                                  selected: true,
                                  onSelect: () {},
                                ),
                                const SizedBox(height: 2),
                                FormRadioRow(
                                  label: ' ',
                                  selected: false,
                                  onSelect: () {},
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        const AppTextInput(label: ' '),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );

    overlay.insert(entry);
    await Future<void>.delayed(Duration.zero);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      entry.remove();
    });
    _done = true;
  }
}
