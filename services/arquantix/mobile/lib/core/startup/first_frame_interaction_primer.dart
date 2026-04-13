import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Un **seul** passage : peint hors écran des gabarits proches des feuilles DS
/// ([BottomSheetContainer] : rayons 32/60) + [Material] + [ClipRRect], sans
/// dupliquer d’écran métier (pas de [LoginPhoneScreen], pas de Keychain).
///
/// Insère une [OverlayEntry] transparente, la retire au frame suivant.
class FirstFrameInteractionPrimer {
  FirstFrameInteractionPrimer._();

  static bool _done = false;

  static Future<void> prime(BuildContext context) async {
    if (_done) return;
    if (kIsWeb) {
      _done = true;
      return;
    }
    if (!context.mounted) return;
    final overlay = Overlay.maybeOf(context, rootOverlay: true);
    if (overlay == null) {
      _done = true;
      return;
    }

    final width = MediaQuery.sizeOf(context).width;
    final bodyLarge =
        Theme.of(context).textTheme.bodyLarge ?? const TextStyle(fontSize: 17);

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
                height: 640,
                child: Material(
                  color: Colors.transparent,
                  child: Align(
                    alignment: Alignment.bottomCenter,
                    child: ClipRRect(
                      borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(32),
                        topRight: Radius.circular(32),
                        bottomLeft: Radius.circular(60),
                        bottomRight: Radius.circular(60),
                      ),
                      child: ColoredBox(
                        color: Colors.white,
                        child: SizedBox(
                          width: width,
                          height: 360,
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const SizedBox(height: 12),
                              // Grabber-like bar (cf. DS)
                              Center(
                                child: Container(
                                  width: 40,
                                  height: 4,
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFE5E5EA),
                                    borderRadius: BorderRadius.circular(2),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 24),
                              Text(' ', style: bodyLarge),
                            ],
                          ),
                        ),
                      ),
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
